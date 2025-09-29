-- Migration: Rename report_id to doc_id and remove unused columns
-- Description: Updates disclosures table to use doc_id instead of report_id, removes doc_url and published_at

-- Rename report_id to doc_id
ALTER TABLE disclosures 
RENAME COLUMN report_id TO doc_id;

-- Drop doc_url column (CASCADE to drop dependent views)
ALTER TABLE disclosures 
DROP COLUMN IF EXISTS doc_url CASCADE;

-- Drop published_at column (CASCADE to drop dependent views)
ALTER TABLE disclosures 
DROP COLUMN IF EXISTS published_at CASCADE;

-- Update unique constraint to use new column name
ALTER TABLE disclosures 
DROP CONSTRAINT IF EXISTS disclosures_politician_id_source_report_id_key;

ALTER TABLE disclosures 
ADD CONSTRAINT disclosures_politician_id_source_doc_id_key 
UNIQUE(politician_id, source, doc_id);

-- Update index to use new column name
DROP INDEX IF EXISTS idx_disclosures_report_id;
CREATE INDEX idx_disclosures_doc_id ON disclosures(doc_id);

-- Add comment
COMMENT ON COLUMN disclosures.doc_id IS 'Document ID from PTR filing (e.g., 40003749)';

-- Verification query (commented out for production)
/*
SELECT column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name = 'disclosures'
ORDER BY ordinal_position;
*/
