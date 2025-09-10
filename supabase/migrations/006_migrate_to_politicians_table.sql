-- Migration: Migrate from congress_members to politicians table with UUID support
-- Description: Updates existing tables to use politicians table with UUID IDs and drops congress_members

-- First, let's check what tables exist and their structure
-- This migration assumes: trades, user_follows, trade_summaries exist with member_id/member_name references

-- Step 1: Modify politicians table to use UUID instead of BIGSERIAL
-- Step 1: Drop foreign key constraints that reference congress_members and politicians
-- This allows us to safely modify the politicians table structure
ALTER TABLE trades DROP CONSTRAINT IF EXISTS trades_member_id_fkey;
ALTER TABLE user_follows DROP CONSTRAINT IF EXISTS user_follows_member_id_fkey;
ALTER TABLE user_follows DROP CONSTRAINT IF EXISTS fk_user_follows_politician_id;

-- Now we can safely modify the politicians table
ALTER TABLE politicians DROP CONSTRAINT IF EXISTS politicians_pkey CASCADE;
ALTER TABLE politicians DROP COLUMN IF EXISTS id CASCADE;
ALTER TABLE politicians ADD COLUMN id UUID PRIMARY KEY DEFAULT gen_random_uuid();

-- Step 2: Drop dependent views first before modifying tables
DROP VIEW IF EXISTS trade_summaries;
DROP VIEW IF EXISTS ptr_ingestion_stats;

-- Step 3: Update trades table structure (no data to preserve)
-- Drop old member_id column and add politician_id, fix disclosure_id type
ALTER TABLE trades DROP COLUMN IF EXISTS member_id;
ALTER TABLE trades ADD COLUMN IF NOT EXISTS politician_id UUID;

-- Since disclosure_id is already UUID, we don't need to change its type
-- Just ensure any old constraints are dropped
ALTER TABLE trades DROP CONSTRAINT IF EXISTS trades_disclosure_id_fkey;
ALTER TABLE trades DROP CONSTRAINT IF EXISTS fk_trades_disclosure_id;

-- Step 3: Update user_follows table structure (no data to preserve)  
-- Drop old member_id column and add politician_id
ALTER TABLE user_follows DROP COLUMN IF EXISTS member_id;
ALTER TABLE user_follows ADD COLUMN IF NOT EXISTS politician_id UUID;

-- Step 4: Recreate ptr_ingestion_stats view with politician_id
CREATE OR REPLACE VIEW ptr_ingestion_stats AS
SELECT 
    t.politician_id,
    p.full_name as politician_name,
    COUNT(*) as total_trades,
    COUNT(DISTINCT DATE(t.transaction_date)) as trading_days,
    MIN(t.transaction_date) as first_trade_date,
    MAX(t.transaction_date) as last_trade_date
FROM trades t
JOIN politicians p ON t.politician_id = p.id
GROUP BY t.politician_id, p.full_name;

-- Step 5: Recreate trade_summaries view to use politician_name instead of member_name

-- Recreate trade_summaries view with politician_name and disclosure information
CREATE OR REPLACE VIEW trade_summaries AS
SELECT 
    t.id,
    t.politician_id,
    p.full_name as politician_name,  -- Changed from member_name
    p.state,
    p.party,
    t.ticker,
    t.asset_description,  -- Changed from asset_name to asset_description
    t.asset_type,
    t.transaction_type,   -- Changed from side to transaction_type
    t.amount_range,
    t.transaction_date,
    t.disclosure_date,    -- Changed from published_at to disclosure_date
    d.report_id,
    d.doc_url,
    d.filed_date
FROM trades t
JOIN politicians p ON t.politician_id = p.id
LEFT JOIN disclosures d ON t.disclosure_id = d.id;

-- Step 6: Update foreign key constraints
-- Add foreign key constraint for trades.politician_id
ALTER TABLE trades DROP CONSTRAINT IF EXISTS fk_trades_politician_id;
ALTER TABLE trades ADD CONSTRAINT fk_trades_politician_id 
    FOREIGN KEY (politician_id) REFERENCES politicians(id) ON DELETE CASCADE;

-- Add foreign key constraint for trades.disclosure_id
ALTER TABLE trades DROP CONSTRAINT IF EXISTS fk_trades_disclosure_id;
ALTER TABLE trades ADD CONSTRAINT fk_trades_disclosure_id 
    FOREIGN KEY (disclosure_id) REFERENCES disclosures(id) ON DELETE CASCADE;

-- Add foreign key constraint for user_follows.politician_id  
ALTER TABLE user_follows DROP CONSTRAINT IF EXISTS fk_user_follows_politician_id;
ALTER TABLE user_follows ADD CONSTRAINT fk_user_follows_politician_id 
    FOREIGN KEY (politician_id) REFERENCES politicians(id) ON DELETE CASCADE;

-- Step 7: Update disclosures table to use UUID for politician_id
ALTER TABLE disclosures DROP CONSTRAINT IF EXISTS fk_disclosures_politician_id;
ALTER TABLE disclosures DROP COLUMN IF EXISTS politician_id;
ALTER TABLE disclosures ADD COLUMN politician_id UUID;

-- Add foreign key constraint for disclosures.politician_id
ALTER TABLE disclosures ADD CONSTRAINT fk_disclosures_politician_id 
    FOREIGN KEY (politician_id) REFERENCES politicians(id) ON DELETE CASCADE;

-- Step 8: Update indexes for new UUID columns
DROP INDEX IF EXISTS idx_trades_politician_id;
DROP INDEX IF EXISTS idx_trades_politician_published;
DROP INDEX IF EXISTS idx_user_follows_politician_id;
DROP INDEX IF EXISTS idx_disclosures_politician_id;

CREATE INDEX idx_trades_politician_id ON trades(politician_id);
CREATE INDEX idx_trades_disclosure_id ON trades(disclosure_id);
CREATE INDEX idx_trades_politician_disclosure ON trades(politician_id, disclosure_date DESC);
CREATE INDEX idx_user_follows_politician_id ON user_follows(politician_id);
CREATE INDEX idx_disclosures_politician_id ON disclosures(politician_id);

-- Step 9: Drop congress_members table (no data to preserve)
DROP TABLE IF EXISTS congress_members CASCADE;

-- Step 10: Add comments for documentation
COMMENT ON TABLE politicians IS 'Members of Congress with UUID primary keys (migrated from congress_members)';
COMMENT ON COLUMN trades.politician_id IS 'UUID reference to politicians table (migrated from member_id)';
COMMENT ON COLUMN user_follows.politician_id IS 'UUID reference to politicians table (migrated from member_id)';
COMMENT ON COLUMN disclosures.politician_id IS 'UUID reference to politicians table';
COMMENT ON VIEW trade_summaries IS 'Denormalized view with politician_name (migrated from member_name)';

-- Step 11: Verify migration results
-- These queries can be run manually to verify the migration
/*
-- Check politicians table structure
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'politicians' 
ORDER BY ordinal_position;

-- Check trades table structure  
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'trades' 
ORDER BY ordinal_position;

-- Check user_follows table structure
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'user_follows' 
ORDER BY ordinal_position;

-- Check trade_summaries view
SELECT * FROM trade_summaries LIMIT 5;

-- Check foreign key constraints
SELECT 
    tc.table_name, 
    tc.constraint_name, 
    tc.constraint_type,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name 
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY' 
    AND tc.table_name IN ('trades', 'user_follows', 'disclosures');
*/
