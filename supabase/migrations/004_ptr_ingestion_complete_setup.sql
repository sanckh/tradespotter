-- Complete PTR Ingestion Setup Migration
-- This migration adds all necessary fields and structures for the PTR ingestion worker

-- Add missing fields to trades table for PTR ingestion
ALTER TABLE public.trades 
ADD COLUMN IF NOT EXISTS row_hash TEXT,
ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'manual',
ADD COLUMN IF NOT EXISTS filing_id TEXT,
ADD COLUMN IF NOT EXISTS notes TEXT;

-- Update existing trades to have a source if they don't already
UPDATE public.trades 
SET source = 'manual' 
WHERE source IS NULL;

-- Make source NOT NULL after setting defaults
ALTER TABLE public.trades 
ALTER COLUMN source SET NOT NULL;

-- Add check constraint for source values
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'check_trades_source' 
        AND table_name = 'trades'
    ) THEN
        ALTER TABLE public.trades 
        ADD CONSTRAINT check_trades_source 
        CHECK (source IN ('manual', 'house_clerk', 'senate_clerk', 'import'));
    END IF;
END $$;

-- Create unique index on row_hash to prevent duplicates (only for non-null values)
CREATE UNIQUE INDEX IF NOT EXISTS idx_trades_row_hash 
ON public.trades(row_hash) 
WHERE row_hash IS NOT NULL;

-- Create performance indexes
CREATE INDEX IF NOT EXISTS idx_trades_source ON public.trades(source);
CREATE INDEX IF NOT EXISTS idx_trades_filing_id ON public.trades(filing_id) WHERE filing_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_trades_disclosure_date ON public.trades(disclosure_date);
CREATE INDEX IF NOT EXISTS idx_trades_asset_type ON public.trades(asset_type);
CREATE INDEX IF NOT EXISTS idx_trades_transaction_type ON public.trades(transaction_type);

-- Create function to generate row_hash (matches Python worker logic)
CREATE OR REPLACE FUNCTION public.generate_trade_row_hash(
    p_source TEXT,
    p_filing_id TEXT,
    p_asset_description TEXT,
    p_ticker TEXT,
    p_transaction_type TEXT,
    p_transaction_date DATE,
    p_amount_range TEXT
) RETURNS TEXT AS $$
BEGIN
    -- Generate SHA256 hash from key fields (same logic as Python worker)
    RETURN encode(
        digest(
            COALESCE(p_source, '') || '|' ||
            COALESCE(p_filing_id, '') || '|' ||
            COALESCE(p_asset_description, '') || '|' ||
            COALESCE(p_ticker, '') || '|' ||
            COALESCE(p_transaction_type, '') || '|' ||
            COALESCE(p_transaction_date::TEXT, '') || '|' ||
            COALESCE(p_amount_range, ''),
            'sha256'
        ),
        'hex'
    );
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Create trigger function to automatically generate row_hash
CREATE OR REPLACE FUNCTION public.update_trade_row_hash()
RETURNS TRIGGER AS $$
BEGIN
    -- Only generate row_hash for automated sources (not manual entries)
    IF NEW.source != 'manual' AND NEW.filing_id IS NOT NULL THEN
        NEW.row_hash = public.generate_trade_row_hash(
            NEW.source,
            NEW.filing_id,
            NEW.asset_description,
            NEW.ticker,
            NEW.transaction_type,
            NEW.transaction_date,
            NEW.amount_range
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update row_hash
DROP TRIGGER IF EXISTS update_trade_row_hash_trigger ON public.trades;
CREATE TRIGGER update_trade_row_hash_trigger
    BEFORE INSERT OR UPDATE ON public.trades
    FOR EACH ROW
    EXECUTE FUNCTION public.update_trade_row_hash();

-- Create storage bucket for PTR PDF files (if not exists)
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'ptr-archive',
    'ptr-archive',
    false,
    52428800, -- 50MB limit
    ARRAY['application/pdf']
)
ON CONFLICT (id) DO NOTHING;

-- Create storage policies for PTR archive bucket
DROP POLICY IF EXISTS "Service role can manage PTR files" ON storage.objects;
CREATE POLICY "Service role can manage PTR files"
ON storage.objects FOR ALL
USING (bucket_id = 'ptr-archive')
WITH CHECK (bucket_id = 'ptr-archive');

-- Create enhanced trade summaries view
DROP VIEW IF EXISTS public.trade_summaries;
CREATE VIEW public.trade_summaries AS
SELECT 
    t.id,
    cm.full_name as member_name,
    cm.first_name,
    cm.last_name,
    cm.state,
    cm.party,
    cm.chamber,
    cm.bioguide_id,
    t.transaction_date,
    t.disclosure_date,
    t.ticker,
    t.asset_description,
    t.asset_type,
    t.transaction_type,
    t.amount_range,
    t.amount_min,
    t.amount_max,
    t.source,
    t.filing_id,
    t.notes,
    t.row_hash,
    t.created_at,
    t.updated_at,
    -- Calculate days between transaction and disclosure
    (t.disclosure_date - t.transaction_date) as disclosure_delay_days,
    -- Format amount range for display
    CASE 
        WHEN t.amount_min IS NOT NULL AND t.amount_max IS NOT NULL THEN
            '$' || to_char(t.amount_min, 'FM999,999,999') || ' - $' || to_char(t.amount_max, 'FM999,999,999')
        ELSE t.amount_range
    END as formatted_amount
FROM public.trades t
JOIN public.congress_members cm ON t.member_id = cm.id
ORDER BY t.transaction_date DESC, t.created_at DESC;

-- Grant permissions on the view
GRANT SELECT ON public.trade_summaries TO authenticated;
GRANT SELECT ON public.trade_summaries TO anon;

-- Create view for PTR ingestion statistics
CREATE OR REPLACE VIEW public.ptr_ingestion_stats AS
SELECT 
    source,
    COUNT(*) as total_trades,
    COUNT(DISTINCT member_id) as unique_members,
    COUNT(DISTINCT filing_id) as unique_filings,
    MIN(transaction_date) as earliest_trade,
    MAX(transaction_date) as latest_trade,
    MIN(created_at) as first_ingested,
    MAX(created_at) as last_ingested,
    COUNT(CASE WHEN transaction_type = 'Purchase' THEN 1 END) as purchases,
    COUNT(CASE WHEN transaction_type = 'Sale' THEN 1 END) as sales,
    COUNT(CASE WHEN transaction_type = 'Exchange' THEN 1 END) as exchanges
FROM public.trades
WHERE source != 'manual'
GROUP BY source
ORDER BY total_trades DESC;

-- Grant permissions on stats view
GRANT SELECT ON public.ptr_ingestion_stats TO authenticated;
GRANT SELECT ON public.ptr_ingestion_stats TO anon;

-- Create function to find duplicate trades by row_hash
CREATE OR REPLACE FUNCTION public.find_duplicate_trades()
RETURNS TABLE(
    row_hash TEXT,
    duplicate_count BIGINT,
    trade_ids UUID[]
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        t.row_hash,
        COUNT(*) as duplicate_count,
        ARRAY_AGG(t.id) as trade_ids
    FROM public.trades t
    WHERE t.row_hash IS NOT NULL
    GROUP BY t.row_hash
    HAVING COUNT(*) > 1
    ORDER BY COUNT(*) DESC;
END;
$$ LANGUAGE plpgsql;

-- Create function to clean up duplicate trades (keeps first occurrence)
CREATE OR REPLACE FUNCTION public.cleanup_duplicate_trades(dry_run BOOLEAN DEFAULT true)
RETURNS TABLE(
    action TEXT,
    row_hash TEXT,
    duplicates_found INTEGER,
    duplicates_removed INTEGER
) AS $$
DECLARE
    duplicate_record RECORD;
    ids_to_delete UUID[];
    deleted_count INTEGER := 0;
    total_found INTEGER := 0;
BEGIN
    -- Find all duplicates
    FOR duplicate_record IN 
        SELECT t.row_hash, COUNT(*) as cnt, ARRAY_AGG(t.id ORDER BY t.created_at) as all_ids
        FROM public.trades t
        WHERE t.row_hash IS NOT NULL
        GROUP BY t.row_hash
        HAVING COUNT(*) > 1
    LOOP
        total_found := total_found + duplicate_record.cnt - 1; -- Don't count the one we keep
        
        -- Get IDs to delete (all except the first one)
        ids_to_delete := duplicate_record.all_ids[2:];
        
        IF NOT dry_run THEN
            -- Delete the duplicates
            DELETE FROM public.trades WHERE id = ANY(ids_to_delete);
            deleted_count := deleted_count + array_length(ids_to_delete, 1);
        END IF;
        
        RETURN QUERY SELECT 
            CASE WHEN dry_run THEN 'WOULD DELETE' ELSE 'DELETED' END,
            duplicate_record.row_hash,
            duplicate_record.cnt::INTEGER - 1,
            CASE WHEN dry_run THEN 0 ELSE array_length(ids_to_delete, 1) END;
    END LOOP;
    
    -- Summary row
    RETURN QUERY SELECT 
        CASE WHEN dry_run THEN 'DRY RUN SUMMARY' ELSE 'CLEANUP SUMMARY' END,
        ''::TEXT,
        total_found,
        deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Add helpful comments
COMMENT ON COLUMN public.trades.row_hash IS 'SHA256 hash for deduplication based on source, filing_id, asset_description, ticker, transaction_type, transaction_date, amount_range';
COMMENT ON COLUMN public.trades.source IS 'Source of the trade data: manual (user entered), house_clerk (PTR ingestion), senate_clerk (future), import (bulk import)';
COMMENT ON COLUMN public.trades.filing_id IS 'Identifier of the original filing/disclosure document (for automated ingestion)';
COMMENT ON COLUMN public.trades.notes IS 'Additional notes or information from the original filing';

COMMENT ON VIEW public.trade_summaries IS 'Enhanced view of trades with member information and calculated fields';
COMMENT ON VIEW public.ptr_ingestion_stats IS 'Statistics about PTR ingestion by source';

COMMENT ON FUNCTION public.generate_trade_row_hash IS 'Generates consistent SHA256 hash for trade deduplication (matches Python worker logic)';
COMMENT ON FUNCTION public.find_duplicate_trades IS 'Finds trades with duplicate row_hash values';
COMMENT ON FUNCTION public.cleanup_duplicate_trades IS 'Removes duplicate trades, keeping the first occurrence (use dry_run=true to preview)';

-- Create indexes for congress_members if they don't exist
CREATE INDEX IF NOT EXISTS idx_congress_members_full_name ON public.congress_members(full_name);
CREATE INDEX IF NOT EXISTS idx_congress_members_state ON public.congress_members(state);
CREATE INDEX IF NOT EXISTS idx_congress_members_party ON public.congress_members(party);
CREATE INDEX IF NOT EXISTS idx_congress_members_chamber ON public.congress_members(chamber);
CREATE INDEX IF NOT EXISTS idx_congress_members_bioguide_id ON public.congress_members(bioguide_id);

-- Final summary
DO $$
BEGIN
    RAISE NOTICE 'PTR Ingestion Setup Complete!';
    RAISE NOTICE '- Added row_hash, source, filing_id, notes columns to trades table';
    RAISE NOTICE '- Created indexes for performance';
    RAISE NOTICE '- Set up automatic row_hash generation';
    RAISE NOTICE '- Created ptr-archive storage bucket';
    RAISE NOTICE '- Added trade_summaries and ptr_ingestion_stats views';
    RAISE NOTICE '- Added duplicate detection and cleanup functions';
    RAISE NOTICE '- Ready for PTR ingestion worker!';
END $$;
