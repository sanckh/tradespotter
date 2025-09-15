-- Migration: Update politicians table structure
-- Description: Remove party, external_ids, first_name, last_name, bioguide_id columns and add doc_id column

-- First, drop views that depend on columns we're removing
DROP VIEW IF EXISTS trade_summaries;

-- Remove columns from politicians table
ALTER TABLE politicians 
DROP COLUMN IF EXISTS party,
DROP COLUMN IF EXISTS external_ids,
DROP COLUMN IF EXISTS first_name,
DROP COLUMN IF EXISTS last_name,
DROP COLUMN IF EXISTS bioguide_id;

-- Add new columns
ALTER TABLE politicians 
ADD COLUMN doc_id TEXT,
ADD COLUMN filing_date TIMESTAMPTZ;

-- Drop existing indexes that reference removed columns
DROP INDEX IF EXISTS idx_politicians_bioguide_id;

-- Create indexes for the new columns
CREATE INDEX idx_politicians_doc_id ON politicians(doc_id);
CREATE INDEX idx_politicians_filing_date ON politicians(filing_date);

-- Recreate the trade_summaries view without the party column

CREATE OR REPLACE VIEW trade_summaries AS
SELECT 
    t.id,
    t.politician_id,
    p.full_name as politician_name,
    p.chamber,
    p.state,
    t.transaction_date,
    t.published_at,
    t.ticker,
    t.asset_name,
    t.side,
    t.amount_range,
    t.notes,
    d.report_id,
    d.filed_date,
    d.doc_url
FROM trades t
JOIN politicians p ON t.politician_id = p.id
JOIN disclosures d ON t.disclosure_id = d.id;

-- Add comments for the new columns
COMMENT ON COLUMN politicians.doc_id IS 'Document ID from PTR filing data';
COMMENT ON COLUMN politicians.filing_date IS 'Date when the PTR filing was submitted';

-- Verification query (commented out for production)
/*
-- Verify the updated table structure
SELECT column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name = 'politicians'
ORDER BY ordinal_position;
*/
