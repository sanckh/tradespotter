-- Migration: Remove doc_id and filing_date from politicians table
-- Description: These fields don't belong on the politicians table - they're disclosure-specific

-- Drop doc_id column if it exists
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'politicians' 
        AND column_name = 'doc_id'
    ) THEN
        ALTER TABLE politicians DROP COLUMN doc_id;
    END IF;
END $$;

-- Drop filing_date column if it exists
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'politicians' 
        AND column_name = 'filing_date'
    ) THEN
        ALTER TABLE politicians DROP COLUMN filing_date;
    END IF;
END $$;

-- Verification query (commented out for production)
/*
SELECT column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name = 'politicians'
ORDER BY ordinal_position;
*/
