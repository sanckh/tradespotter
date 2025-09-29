-- Migration: Add filing_type to disclosures table
-- Description: Adds filing_type field with enum for PTR filing type classification

-- Create enum for filing types
CREATE TYPE filing_type_enum AS ENUM (
    'P',  -- Periodic Transaction Report (PTR)
    'A',  -- Amendment
    'C',  -- Candidate
    'D',  -- Disclosure
    'O',  -- Officer
    'X'   -- Extension
);

-- Add filing_type column to disclosures table
ALTER TABLE disclosures 
ADD COLUMN filing_type TEXT;

-- Add comment for documentation
COMMENT ON COLUMN disclosures.filing_type IS 'Type of filing: P=PTR, A=Amendment, C=Candidate, D=Disclosure, O=Officer, X=Extension';

-- Create index for efficient querying by filing type
CREATE INDEX idx_disclosures_filing_type ON disclosures(filing_type);

-- Optional: Add check constraint to ensure valid filing types
ALTER TABLE disclosures
ADD CONSTRAINT check_filing_type 
CHECK (filing_type IS NULL OR filing_type IN ('P', 'A', 'C', 'D', 'O', 'X', 'W'));

-- Verification query (commented out for production)
/*
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'disclosures' 
  AND column_name = 'filing_type';
*/

-- ============================================================================
-- UPDATE SCRIPT: Add 'W' filing type to constraint
-- Run this separately if you already ran the migration above
-- ============================================================================

-- Drop the existing constraint first
ALTER TABLE disclosures DROP CONSTRAINT check_filing_type;

-- Add new constraint with 'W' (Withdrawal) included
ALTER TABLE disclosures
ADD CONSTRAINT check_filing_type 
CHECK (filing_type IS NULL OR filing_type IN ('P', 'A', 'C', 'D', 'O', 'X', 'W'));

-- Update comment to include W
COMMENT ON COLUMN disclosures.filing_type IS 'Type of filing: P=PTR, A=Amendment, C=Candidate, D=Disclosure, O=Officer, X=Extension, W=Withdrawal';
