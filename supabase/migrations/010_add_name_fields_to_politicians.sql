-- Migration: Add first_name and last_name to politicians table
-- Description: Adds missing name fields that are required by the ingestion worker

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

-- Add party column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'politicians' 
        AND column_name = 'party'
    ) THEN
        ALTER TABLE politicians ADD COLUMN party TEXT;
    END IF;
END $$;

-- Add bioguide_id column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'politicians' 
        AND column_name = 'bioguide_id'
    ) THEN
        ALTER TABLE politicians ADD COLUMN bioguide_id TEXT UNIQUE;
    END IF;
END $$;

-- Add external_ids column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'politicians' 
        AND column_name = 'external_ids'
    ) THEN
        ALTER TABLE politicians ADD COLUMN external_ids JSONB DEFAULT '{}';
    END IF;
END $$;

-- Add updated_at column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'politicians' 
        AND column_name = 'updated_at'
    ) THEN
        ALTER TABLE politicians ADD COLUMN updated_at TIMESTAMPTZ DEFAULT NOW();
    END IF;
END $$;

-- Create or replace the updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Drop trigger if exists and recreate
DROP TRIGGER IF EXISTS update_politicians_updated_at ON politicians;
CREATE TRIGGER update_politicians_updated_at 
    BEFORE UPDATE ON politicians
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Add comments
COMMENT ON COLUMN politicians.first_name IS 'First name of the politician';
COMMENT ON COLUMN politicians.last_name IS 'Last name of the politician';
COMMENT ON COLUMN politicians.party IS 'Political party affiliation';
COMMENT ON COLUMN politicians.bioguide_id IS 'Bioguide identifier';
COMMENT ON COLUMN politicians.external_ids IS 'Additional external identifiers in JSON format';

-- Verification query (commented out for production)
/*
SELECT column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name = 'politicians'
ORDER BY ordinal_position;
*/
