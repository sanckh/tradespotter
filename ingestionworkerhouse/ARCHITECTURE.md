# PTR Ingestion Worker Architecture

## Overview

The PTR (Periodic Transaction Report) Ingestion Worker is designed to scrape and process financial disclosure data from the House Clerk website. This document explains the corrected database schema and ingestion flow.

## Database Schema (3-Table Design)

### 1. `politicians` Table
Stores basic information about politicians. **Does NOT contain disclosure-specific data.**

**Fields:**
- `id` (UUID, PK) - Unique identifier
- `full_name` (TEXT) - Full name of politician
- `first_name` (TEXT) - First name
- `last_name` (TEXT) - Last name
- `chamber` (TEXT) - 'house' or 'senate'
- `state` (TEXT) - State abbreviation (e.g., 'CA', 'TX')
- `district` (TEXT) - District number (e.g., '1', '23')
- `party` (TEXT) - Political party
- `bioguide_id` (TEXT) - Bioguide identifier
- `external_ids` (JSONB) - Additional external identifiers
- `created_at` (TIMESTAMPTZ)
- `updated_at` (TIMESTAMPTZ)

**Key Points:**
- One record per politician
- No `doc_id` or `filing_date` fields (those belong in disclosures)
- Upserted based on name + state + district

### 2. `disclosures` Table
Stores each financial disclosure filing. **One record per filing per politician.**

**Fields:**
- `id` (UUID, PK) - Unique identifier
- `politician_id` (UUID, FK) - References politicians(id)
- `source` (TEXT) - Data source (e.g., 'house_clerk')
- `doc_id` (TEXT) - The DocID from PTR filing (e.g., 40003749)
- `filing_type` (TEXT) - Type of filing (P, A, C, D, O, X)
- `filed_date` (TIMESTAMPTZ) - Date the disclosure was filed
- `raw` (JSONB) - Raw filing metadata
- `created_at` (TIMESTAMPTZ)
- `updated_at` (TIMESTAMPTZ)

**Key Points:**
- Multiple disclosures per politician (one per filing)
- Unique constraint: `(politician_id, source, doc_id)`
- `doc_id` is the document identifier from the House Clerk system
- `filing_type`: P=PTR, A=Amendment, C=Candidate, D=Disclosure, O=Officer, X=Extension

### 3. `trades` Table
Stores individual trades extracted from disclosure documents.

**Fields:**
- `id` (UUID, PK) - Unique identifier
- `disclosure_id` (UUID, FK) - References disclosures(id)
- `politician_id` (UUID, FK) - References politicians(id) (denormalized for performance)
- `transaction_date` (TIMESTAMPTZ) - Date of the trade
- `published_at` (TIMESTAMPTZ) - When trade was published
- `ticker` (TEXT) - Stock ticker symbol
- `asset_name` (TEXT) - Name of the asset
- `side` (TEXT) - 'buy' or 'sell'
- `amount_range` (TEXT) - Transaction amount range
- `notes` (TEXT) - Additional notes
- `row_hash` (TEXT, UNIQUE) - SHA256 hash for deduplication
- `created_at` (TIMESTAMPTZ)
- `updated_at` (TIMESTAMPTZ)

**Key Points:**
- Multiple trades per disclosure
- `row_hash` ensures no duplicate trades
- Links to both disclosure and politician for efficient queries

## Ingestion Flow

### Phase 1: Bulk TXT File Processing

The House Clerk website provides yearly zip files containing TXT files with filing metadata.

**TXT File Format (Tab-Delimited):**
```
Prefix  Last    First   Suffix  FilingType  StateDst  Year  FilingDate  DocID
        Aaron   Richard D       P           MI04      2025  3/24/2025   40003749
```

**Processing Steps:**

1. **Discovery** (`ptr_discovery.py`)
   - Finds year-based download links (e.g., `/public_disc/financial-pdfs/2023FD.zip`)
   - Downloads zip files for specified year range

2. **Parsing** (`txt_parser.py`)
   - Extracts TXT files from zip
   - Parses tab-delimited data
   - Extracts: Name, State, District, DocID, FilingDate, FilingType

3. **Normalization** (`ingestion_pipeline.py`)
   - Cleans and validates parsed data
   - Separates politician info from disclosure info

4. **Upserting** (`data_upserter.py`)
   - **Step A:** Upsert politician record
     - Insert if new (based on name + state + district)
     - Return existing if already present
     - **Does NOT update with doc_id or filing_date**
   
   - **Step B:** Insert disclosure record
     - Links to politician via `politician_id`
     - Stores `report_id` (DocID) and `filed_date`
     - Unique constraint prevents duplicates
     - Stores raw filing metadata in JSONB field

### Phase 2: Trade Extraction (Future)

After Phase 1 populates politicians and disclosures, Phase 2 will:

1. **Fetch Individual Filings**
   - Use `report_id` and `filed_date` from disclosures table
   - Download actual PDF/HTML disclosure documents

2. **Parse Trade Data**
   - Extract individual trades from documents
   - Parse: ticker, asset name, transaction date, amount, buy/sell

3. **Upsert Trades**
   - Link to both `disclosure_id` and `politician_id`
   - Generate `row_hash` for deduplication
   - Insert trades into trades table

## Why This Design Works

### Problem with Old Design
❌ **Old (Broken):** Politicians table had `doc_id` and `filing_date` columns
- Each new filing would **overwrite** the previous values
- Lost historical filing data
- Couldn't track multiple disclosures per politician

### Solution with New Design
✅ **New (Correct):** Separate disclosures table
- Politicians table: Static info (name, state, district)
- Disclosures table: One row per filing (doc_id, filing_date)
- Trades table: One row per trade, linked to disclosure

### Data Relationships
```
politicians (1) ----< (many) disclosures (1) ----< (many) trades
```

**Example:**
- Politician: "Nancy Pelosi" (CA-11)
  - Disclosure 1: DocID=40001234, Filed=2024-01-15
    - Trade 1: AAPL, Buy, $50K-$100K
    - Trade 2: MSFT, Sell, $15K-$50K
  - Disclosure 2: DocID=40005678, Filed=2024-03-20
    - Trade 3: TSLA, Buy, $1K-$15K
  - Disclosure 3: DocID=40009999, Filed=2024-06-10
    - Trade 4: NVDA, Buy, $100K-$250K

## Key Files Updated

1. **`models.py`** - Updated to match 3-table schema
2. **`connection.py`** - Added `DisclosureRepository`, updated `PoliticianRepository`
3. **`data_upserter.py`** - Separated politician and disclosure upsert logic
4. **`007_create_fresh_schema.sql`** - Already had correct schema (no changes needed)

## Running the Ingestion

```bash
# Run bulk ingestion for specific years
python -m ingestionworkerhouse.main --mode bulk --year-start 2023 --year-end 2023

# This will:
# 1. Download 2023FD.zip
# 2. Parse TXT files
# 3. Upsert politicians (name, state, district)
# 4. Insert disclosures (doc_id, filing_date, politician_id)
```

## Next Steps

After Phase 1 is complete and the database is populated with politicians and disclosures:

1. Build Phase 2 to fetch individual disclosure documents using `report_id`
2. Parse trade data from disclosure documents
3. Insert trades linked to `disclosure_id` and `politician_id`
4. Build frontend to display trades by politician

## Summary

The corrected architecture properly separates concerns:
- **Politicians**: Who they are (static)
- **Disclosures**: What they filed (multiple per politician)
- **Trades**: What they traded (multiple per disclosure)

This prevents data loss and allows proper tracking of all filings and trades over time.
