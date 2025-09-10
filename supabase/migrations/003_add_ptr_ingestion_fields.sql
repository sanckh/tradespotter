-- Migration to add fields needed for PTR ingestion worker
-- This adds the missing row_hash column and other fields needed for deduplication and tracking

-- Add row_hash column for deduplication (critical for PTR ingestion)
ALTER TABLE public.trades 
ADD COLUMN IF NOT EXISTS row_hash TEXT;

-- Add source tracking fields
ALTER TABLE public.trades 
ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'manual';

-- Add filing/disclosure tracking fields  
ALTER TABLE public.trades 
ADD COLUMN IF NOT EXISTS filing_id TEXT;

-- Add notes field for additional trade information
ALTER TABLE public.trades 
ADD COLUMN IF NOT EXISTS notes TEXT;

-- Create unique index on row_hash to prevent duplicates
CREATE UNIQUE INDEX IF NOT EXISTS idx_trades_row_hash 
ON public.trades(row_hash) 
WHERE row_hash IS NOT NULL;

-- Create index on source for filtering
CREATE INDEX IF NOT EXISTS idx_trades_source 
ON public.trades(source);

-- Create index on filing_id for grouping trades by filing
CREATE INDEX IF NOT EXISTS idx_trades_filing_id 
ON public.trades(filing_id) 
WHERE filing_id IS NOT NULL;

-- Add check constraint for source values
ALTER TABLE public.trades 
ADD CONSTRAINT IF NOT EXISTS check_trades_source 
CHECK (source IN ('manual', 'house_clerk', 'senate_clerk', 'import'));

-- Update existing trades to have a source if they don't already
UPDATE public.trades 
SET source = 'manual' 
WHERE source IS NULL;

-- Make source NOT NULL after setting defaults
ALTER TABLE public.trades 
ALTER COLUMN source SET NOT NULL;

-- Add comment explaining row_hash usage
COMMENT ON COLUMN public.trades.row_hash IS 'SHA256 hash for deduplication based on source, filing_id, asset_description, ticker, transaction_type, transaction_date, amount_range';

-- Add comment explaining source field
COMMENT ON COLUMN public.trades.source IS 'Source of the trade data: manual (user entered), house_clerk (PTR ingestion), senate_clerk (future), import (bulk import)';

-- Add comment explaining filing_id
COMMENT ON COLUMN public.trades.filing_id IS 'Identifier of the original filing/disclosure document (for automated ingestion)';

-- Create function to generate row_hash for existing trades
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

-- Create trigger function to automatically generate row_hash on insert/update
CREATE OR REPLACE FUNCTION public.update_trade_row_hash()
RETURNS TRIGGER AS $$
BEGIN
    -- Only generate row_hash for automated sources (not manual entries)
    IF NEW.source != 'manual' THEN
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
CREATE TRIGGER update_trade_row_hash_trigger
    BEFORE INSERT OR UPDATE ON public.trades
    FOR EACH ROW
    EXECUTE FUNCTION public.update_trade_row_hash();

-- Create view for trade summaries (useful for reporting)
CREATE OR REPLACE VIEW public.trade_summaries AS
SELECT 
    cm.full_name as member_name,
    cm.state,
    cm.party,
    cm.chamber,
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
    t.created_at
FROM public.trades t
JOIN public.congress_members cm ON t.member_id = cm.id
ORDER BY t.transaction_date DESC, t.created_at DESC;

-- Grant appropriate permissions on the view
GRANT SELECT ON public.trade_summaries TO authenticated;
GRANT SELECT ON public.trade_summaries TO anon;

-- Create RLS policy for the view (inherits from underlying tables)
ALTER VIEW public.trade_summaries SET (security_invoker = true);
