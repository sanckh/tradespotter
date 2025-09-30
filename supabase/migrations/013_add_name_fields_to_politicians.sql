-- Migration: Add name component fields to politicians table
-- Description: Adds prefix, first_name, last_name, and suffix fields to properly store politician names

-- Add prefix column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'politicians' 
        AND column_name = 'prefix'
    ) THEN
        ALTER TABLE politicians ADD COLUMN prefix TEXT;
    END IF;
END $$;

-- Add first_name column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'politicians' 
        AND column_name = 'first_name'
    ) THEN
        ALTER TABLE politicians ADD COLUMN first_name TEXT;
    END IF;
END $$;

-- Add last_name column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'politicians' 
        AND column_name = 'last_name'
    ) THEN
        ALTER TABLE politicians ADD COLUMN last_name TEXT;
    END IF;
END $$;

-- Add suffix column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'politicians' 
        AND column_name = 'suffix'
    ) THEN
        ALTER TABLE politicians ADD COLUMN suffix TEXT;
    END IF;
END $$;

-- Add comments for documentation
COMMENT ON COLUMN politicians.prefix IS 'Name prefix (e.g., Hon., Dr., Mr., Ms.)';
COMMENT ON COLUMN politicians.first_name IS 'First name of the politician';
COMMENT ON COLUMN politicians.last_name IS 'Last name of the politician';
COMMENT ON COLUMN politicians.suffix IS 'Name suffix (e.g., Jr., Sr., III)';

-- Create index on last_name for efficient sorting/searching
CREATE INDEX IF NOT EXISTS idx_politicians_last_name ON politicians(last_name);
CREATE INDEX IF NOT EXISTS idx_politicians_first_name ON politicians(first_name);

-- Verification query (commented out for production)
/*
SELECT column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name = 'politicians'
ORDER BY ordinal_position;
*/
