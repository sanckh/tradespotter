-- Migration: Create fresh schema with UUID-based tables
-- Description: Creates politicians, disclosures, trades tables and views from scratch using UUIDs

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Drop all existing tables and views if they exist
DROP VIEW IF EXISTS trade_summaries CASCADE;
DROP VIEW IF EXISTS ptr_ingestion_stats CASCADE;
DROP TABLE IF EXISTS trades CASCADE;
DROP TABLE IF EXISTS disclosures CASCADE;
DROP TABLE IF EXISTS politicians CASCADE;
DROP TABLE IF EXISTS user_follows CASCADE;
DROP TABLE IF EXISTS congress_members CASCADE;

-- Politicians table (replaces congress_members)
CREATE TABLE politicians (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name TEXT NOT NULL,
    first_name TEXT,
    last_name TEXT,
    chamber TEXT CHECK (chamber IN ('house', 'senate')),
    state TEXT,
    district TEXT,
    party TEXT,
    bioguide_id TEXT UNIQUE,
    external_ids JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Disclosures table
CREATE TABLE disclosures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    politician_id UUID NOT NULL REFERENCES politicians(id) ON DELETE CASCADE,
    source TEXT NOT NULL DEFAULT 'house_clerk',
    report_id TEXT NOT NULL,
    filed_date TIMESTAMPTZ,
    published_at TIMESTAMPTZ,
    doc_url TEXT,
    raw JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Ensure unique report per politician per source
    UNIQUE(politician_id, source, report_id)
);

-- Trades table
CREATE TABLE trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    disclosure_id UUID NOT NULL REFERENCES disclosures(id) ON DELETE CASCADE,
    politician_id UUID NOT NULL REFERENCES politicians(id) ON DELETE CASCADE,
    transaction_date TIMESTAMPTZ,
    published_at TIMESTAMPTZ,
    ticker TEXT,
    asset_name TEXT NOT NULL,
    side TEXT CHECK (side IN ('buy', 'sell') OR side IS NULL),
    amount_range TEXT,
    notes TEXT,
    row_hash TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- User follows table (for following politicians)
CREATE TABLE user_follows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    politician_id UUID NOT NULL REFERENCES politicians(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Ensure unique follow per user per politician
    UNIQUE(user_id, politician_id)
);

-- Create indexes for politicians
CREATE INDEX idx_politicians_full_name ON politicians(full_name);
CREATE INDEX idx_politicians_chamber ON politicians(chamber);
CREATE INDEX idx_politicians_state ON politicians(state);
CREATE INDEX idx_politicians_bioguide_id ON politicians(bioguide_id);

-- Create indexes for disclosures
CREATE INDEX idx_disclosures_politician_id ON disclosures(politician_id);
CREATE INDEX idx_disclosures_source ON disclosures(source);
CREATE INDEX idx_disclosures_report_id ON disclosures(report_id);
CREATE INDEX idx_disclosures_published_at ON disclosures(politician_id, published_at DESC);
CREATE INDEX idx_disclosures_filed_date ON disclosures(filed_date);

-- Create indexes for trades
CREATE INDEX idx_trades_disclosure_id ON trades(disclosure_id);
CREATE INDEX idx_trades_politician_id ON trades(politician_id);
CREATE INDEX idx_trades_politician_published ON trades(politician_id, published_at DESC);
CREATE INDEX idx_trades_ticker ON trades(ticker);
CREATE INDEX idx_trades_transaction_date ON trades(transaction_date);
CREATE INDEX idx_trades_side ON trades(side);
CREATE INDEX idx_trades_row_hash ON trades(row_hash);

-- Create indexes for user_follows
CREATE INDEX idx_user_follows_user_id ON user_follows(user_id);
CREATE INDEX idx_user_follows_politician_id ON user_follows(politician_id);

-- Create updated_at triggers for all tables
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_politicians_updated_at BEFORE UPDATE ON politicians
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_disclosures_updated_at BEFORE UPDATE ON disclosures
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_trades_updated_at BEFORE UPDATE ON trades
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- PTR Ingestion Stats View
CREATE OR REPLACE VIEW ptr_ingestion_stats AS
SELECT 
    t.politician_id,
    p.full_name as politician_name,
    p.chamber,
    p.state,
    COUNT(DISTINCT d.id) as total_disclosures,
    COUNT(t.id) as total_trades,
    MIN(t.transaction_date) as earliest_trade,
    MAX(t.transaction_date) as latest_trade,
    COUNT(CASE WHEN t.side = 'buy' THEN 1 END) as buy_count,
    COUNT(CASE WHEN t.side = 'sell' THEN 1 END) as sell_count,
    COUNT(DISTINCT t.ticker) as unique_tickers,
    MAX(d.filed_date) as last_filing_date
FROM trades t
JOIN politicians p ON t.politician_id = p.id
LEFT JOIN disclosures d ON t.disclosure_id = d.id
GROUP BY t.politician_id, p.full_name, p.chamber, p.state;

-- Trade Summaries View
CREATE OR REPLACE VIEW trade_summaries AS
SELECT 
    t.id,
    t.politician_id,
    p.full_name as politician_name,
    p.chamber,
    p.state,
    p.party,
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

-- Add comments for documentation
COMMENT ON TABLE politicians IS 'Politicians (House and Senate members) with UUID primary keys';
COMMENT ON TABLE disclosures IS 'Financial disclosure reports filed by politicians';
COMMENT ON TABLE trades IS 'Individual trades extracted from disclosure reports';
COMMENT ON TABLE user_follows IS 'User following relationships for politicians';

COMMENT ON VIEW ptr_ingestion_stats IS 'Aggregated statistics for PTR ingestion by politician';
COMMENT ON VIEW trade_summaries IS 'Detailed view of trades with politician and disclosure information';

-- Verification queries (commented out for production)
/*
-- Verify table structure
SELECT table_name, column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name IN ('politicians', 'disclosures', 'trades', 'user_follows')
ORDER BY table_name, ordinal_position;

-- Verify foreign key constraints
SELECT 
    tc.table_name, 
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
