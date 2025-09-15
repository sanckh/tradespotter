-- Migration: Create PTR ingestion tables
-- Description: Creates politicians, disclosures, and trades tables for House PTR data

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Politicians table
CREATE TABLE IF NOT EXISTS politicians (
    id BIGSERIAL PRIMARY KEY,
    full_name TEXT NOT NULL,
    chamber TEXT NOT NULL DEFAULT 'house',
    state TEXT,
    party TEXT,
    external_ids JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for politicians
CREATE INDEX IF NOT EXISTS idx_politicians_full_name ON politicians(full_name);
CREATE INDEX IF NOT EXISTS idx_politicians_chamber ON politicians(chamber);
CREATE INDEX IF NOT EXISTS idx_politicians_state ON politicians(state);

-- Disclosures table
CREATE TABLE IF NOT EXISTS disclosures (
    id BIGSERIAL PRIMARY KEY,
    politician_id BIGINT NOT NULL REFERENCES politicians(id) ON DELETE CASCADE,
    source TEXT NOT NULL DEFAULT 'house_clerk',
    report_id TEXT NOT NULL,
    filed_date TIMESTAMPTZ,
    published_at TIMESTAMPTZ,
    doc_url TEXT,
    raw JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Unique constraint to prevent duplicate disclosures
    CONSTRAINT unique_disclosure UNIQUE (source, report_id)
);

-- Create indexes for disclosures
CREATE INDEX IF NOT EXISTS idx_disclosures_politician_id ON disclosures(politician_id);
CREATE INDEX IF NOT EXISTS idx_disclosures_source ON disclosures(source);
CREATE INDEX IF NOT EXISTS idx_disclosures_report_id ON disclosures(report_id);
CREATE INDEX IF NOT EXISTS idx_disclosures_published_at ON disclosures(politician_id, published_at DESC);
CREATE INDEX IF NOT EXISTS idx_disclosures_filed_date ON disclosures(filed_date);

-- Trades table
CREATE TABLE IF NOT EXISTS trades (
    id BIGSERIAL PRIMARY KEY,
    disclosure_id BIGINT NOT NULL REFERENCES disclosures(id) ON DELETE CASCADE,
    politician_id BIGINT NOT NULL REFERENCES politicians(id) ON DELETE CASCADE,
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

-- Create indexes for trades
CREATE INDEX IF NOT EXISTS idx_trades_disclosure_id ON trades(disclosure_id);
CREATE INDEX IF NOT EXISTS idx_trades_politician_id ON trades(politician_id);
CREATE INDEX IF NOT EXISTS idx_trades_politician_published ON trades(politician_id, published_at DESC);
CREATE INDEX IF NOT EXISTS idx_trades_ticker ON trades(ticker);
CREATE INDEX IF NOT EXISTS idx_trades_transaction_date ON trades(transaction_date);
CREATE INDEX IF NOT EXISTS idx_trades_side ON trades(side);
CREATE INDEX IF NOT EXISTS idx_trades_row_hash ON trades(row_hash);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_politicians_updated_at BEFORE UPDATE ON politicians
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_disclosures_updated_at BEFORE UPDATE ON disclosures
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_trades_updated_at BEFORE UPDATE ON trades
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create RLS policies (optional - enable if you want row-level security)
-- ALTER TABLE politicians ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE disclosures ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE trades ENABLE ROW LEVEL SECURITY;

-- Create service role policies (uncomment if RLS is enabled)
-- CREATE POLICY "Service role can manage politicians" ON politicians
--     FOR ALL USING (auth.role() = 'service_role');

-- CREATE POLICY "Service role can manage disclosures" ON disclosures
--     FOR ALL USING (auth.role() = 'service_role');

-- CREATE POLICY "Service role can manage trades" ON trades
--     FOR ALL USING (auth.role() = 'service_role');

-- Insert sample data for testing (optional)
-- INSERT INTO politicians (full_name, chamber, state, party) VALUES
-- ('John Doe', 'house', 'CA', 'Democratic'),
-- ('Jane Smith', 'house', 'TX', 'Republican')
-- ON CONFLICT (full_name) DO NOTHING;

-- Create a view for trade summaries (useful for API queries)
CREATE OR REPLACE VIEW trade_summaries AS
SELECT 
    t.id,
    t.politician_id,
    p.full_name as politician_name,
    p.state,
    p.party,
    t.ticker,
    t.asset_name,
    t.side,
    t.amount_range,
    t.transaction_date,
    t.published_at,
    d.report_id,
    d.doc_url
FROM trades t
JOIN politicians p ON t.politician_id = p.id
JOIN disclosures d ON t.disclosure_id = d.id;

-- Grant permissions to authenticated users for the view
-- GRANT SELECT ON trade_summaries TO authenticated;

COMMENT ON TABLE politicians IS 'Members of Congress with basic information';
COMMENT ON TABLE disclosures IS 'PTR disclosure filings with metadata and raw data';
COMMENT ON TABLE trades IS 'Individual trade transactions extracted from PTR filings';
COMMENT ON VIEW trade_summaries IS 'Denormalized view of trades with politician and disclosure info';
