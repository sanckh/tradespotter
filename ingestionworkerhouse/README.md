# PTR Ingestion Worker

Automated ingestion system for House of Representatives Periodic Transaction Reports (PTR). Scrapes, parses, and stores congressional stock trading data into Supabase.

## 🎯 What It Does

The worker processes PTR filings in two phases:

**Phase 1: Bulk Filing Metadata** (Current)
- Downloads yearly zip files from House Clerk website
- Parses tab-delimited TXT files containing filing metadata
- Stores politicians and disclosure records (DocID, filing dates, filing types)

**Phase 2: Individual Trade Extraction** (Future)
- Uses DocIDs to fetch actual disclosure documents
- Parses individual trades from each filing
- Links trades to disclosures and politicians

### Key Features

- ✅ Idempotent operations - safe to run multiple times
- ✅ Automatic deduplication via unique constraints
- ✅ Proper 3-table schema (politicians → disclosures → trades)
- ✅ Structured logging and error handling
- ✅ Year-by-year processing for better control

## 📋 Prerequisites

- Python 3.9+
- Supabase project with database access
- Internet connection

## 🚀 Quick Start

### 1. Apply Database Migrations

Run migrations in order (007 creates the schema, 009 adds filing_type):

```bash
python apply_migrations.py
```

Or manually in Supabase SQL Editor:
- `supabase/migrations/007_create_fresh_schema.sql`
- `supabase/migrations/009_add_filing_type_to_disclosures.sql`

### 2. Install Dependencies

```bash
cd ingestionworkerhouse
pip install -r requirements.txt
```

### 3. Configure Environment

Create `.env` file:

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
HOUSE_YEAR_WINDOW=2023-2025
MAX_CONCURRENCY=5
```

Get credentials from: Supabase Dashboard → Settings → API

### 4. Run the Worker

```bash
# Test with one year
python -m src.main --mode bulk --year 2023

# Process multiple years
python -m src.main --mode bulk --year-start 2023 --year-end 2024
```

## 🎮 Usage

### Bulk Mode (Phase 1 - Current)

Process filing metadata from yearly zip files:

```bash
# Single year
python -m src.main --mode bulk --year 2023

# Year range
python -m src.main --mode bulk --year-start 2023 --year-end 2024

# Discovery only (test)
python -m src.main --mode discovery --year 2023

# Download only (test)
python -m src.main --mode download --year 2023
```

### Health Check

```bash
python -m src.main --mode health
```

### Command Options

- `--mode bulk` - Full pipeline (discover → download → parse → upsert)
- `--mode discovery` - Only find zip file URLs
- `--mode download` - Download and extract zip files
- `--mode health` - Check system status
- `--year YYYY` - Process specific year
- `--year-start YYYY` - Start of year range
- `--year-end YYYY` - End of year range
- `--log-level DEBUG` - Verbose logging

## 📊 Database Schema

See `ARCHITECTURE.md` for detailed schema documentation.

**3-Table Design:**
- `politicians` - Basic politician info (name, state, district)
- `disclosures` - Filing records (report_id, filing_date, filing_type)
- `trades` - Individual trades (linked to disclosures)

**Key Points:**
- Politicians table has NO doc_id or filing_date (prevents data loss)
- Each disclosure is a separate record
- Trades link to both disclosure_id and politician_id

## 🔍 Monitoring

Check ingestion progress:

```sql
-- Count politicians
SELECT COUNT(*) FROM politicians;

-- Count disclosures by year
SELECT 
  EXTRACT(YEAR FROM filed_date) as year,
  filing_type,
  COUNT(*) as count
FROM disclosures
GROUP BY year, filing_type
ORDER BY year DESC;

-- Recent disclosures
SELECT 
  p.full_name,
  d.doc_id,
  d.filing_type,
  d.filed_date
FROM disclosures d
JOIN politicians p ON d.politician_id = p.id
ORDER BY d.filed_date DESC
LIMIT 10;
```

## 📝 Next Steps

**Phase 2 Implementation** (Future):
1. Build document fetcher using `report_id` from disclosures
2. Parse individual trades from disclosure documents
3. Insert trades linked to `disclosure_id` and `politician_id`
4. Build frontend to display trades by politician

For detailed architecture and data flow, see `ARCHITECTURE.md`.
