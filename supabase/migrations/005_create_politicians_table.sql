-- Migration: Create politicians table for PTR ingestion
-- Description: Creates the politicians table to store congress member data from PTR filings

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Politicians table
CREATE TABLE IF NOT EXISTS politicians (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
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
    
    -- Unique constraint to prevent duplicate disclosures
    CONSTRAINT unique_disclosure UNIQUE (source, report_id)
);

-- Create indexes for disclosures
CREATE INDEX IF NOT EXISTS idx_disclosures_politician_id ON disclosures(politician_id);
CREATE INDEX IF NOT EXISTS idx_disclosures_source ON disclosures(source);
CREATE INDEX IF NOT EXISTS idx_disclosures_report_id ON disclosures(report_id);
CREATE INDEX IF NOT EXISTS idx_disclosures_published_at ON disclosures(politician_id, published_at DESC);
CREATE INDEX IF NOT EXISTS idx_disclosures_filed_date ON disclosures(filed_date);

-- Trades table (created after disclosures table exists)
CREATE TABLE IF NOT EXISTS trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    disclosure_id UUID NOT NULL,
    politician_id UUID NOT NULL,
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

-- Add foreign key constraints after all tables are created
-- Note: Only add constraints if columns exist
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'trades' AND column_name = 'disclosure_id') THEN
        ALTER TABLE trades ADD CONSTRAINT fk_trades_disclosure_id 
            FOREIGN KEY (disclosure_id) REFERENCES disclosures(id) ON DELETE CASCADE;
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'trades' AND column_name = 'politician_id') THEN
        ALTER TABLE trades ADD CONSTRAINT fk_trades_politician_id 
            FOREIGN KEY (politician_id) REFERENCES politicians(id) ON DELETE CASCADE;
    END IF;
END $$;

-- Create indexes for trades (only if columns exist)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'trades' AND column_name = 'disclosure_id') THEN
        CREATE INDEX IF NOT EXISTS idx_trades_disclosure_id ON trades(disclosure_id);
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'trades' AND column_name = 'politician_id') THEN
        CREATE INDEX IF NOT EXISTS idx_trades_politician_id ON trades(politician_id);
        CREATE INDEX IF NOT EXISTS idx_trades_politician_published ON trades(politician_id, published_at DESC);
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'trades' AND column_name = 'ticker') THEN
        CREATE INDEX IF NOT EXISTS idx_trades_ticker ON trades(ticker);
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'trades' AND column_name = 'transaction_date') THEN
        CREATE INDEX IF NOT EXISTS idx_trades_transaction_date ON trades(transaction_date);
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'trades' AND column_name = 'side') THEN
        CREATE INDEX IF NOT EXISTS idx_trades_side ON trades(side);
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'trades' AND column_name = 'row_hash') THEN
        CREATE INDEX IF NOT EXISTS idx_trades_row_hash ON trades(row_hash);
    END IF;
END $$;

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at (only if they don't exist)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_politicians_updated_at') THEN
        CREATE TRIGGER update_politicians_updated_at BEFORE UPDATE ON politicians
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_disclosures_updated_at') THEN
        CREATE TRIGGER update_disclosures_updated_at BEFORE UPDATE ON disclosures
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_trades_updated_at') THEN
        CREATE TRIGGER update_trades_updated_at BEFORE UPDATE ON trades
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;

-- Create a view for trade summaries (useful for API queries)
-- Only create if trades table has the required columns
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'trades' AND column_name = 'politician_id') 
       AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'trades' AND column_name = 'disclosure_id') THEN
        
        EXECUTE '
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
        JOIN disclosures d ON t.disclosure_id = d.id';
        
    END IF;
END $$;

COMMENT ON TABLE politicians IS 'Members of Congress with basic information';
COMMENT ON TABLE disclosures IS 'PTR disclosure filings with metadata and raw data';
COMMENT ON TABLE trades IS 'Individual trade transactions extracted from PTR filings';
COMMENT ON VIEW trade_summaries IS 'Denormalized view of trades with politician and disclosure info';
