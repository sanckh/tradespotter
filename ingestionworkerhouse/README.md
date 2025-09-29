# PTR Ingestion Worker

A comprehensive Python-based ingestion worker that automatically discovers, downloads, parses, normalizes, and stores House of Representatives Periodic Transaction Reports (PTR) trade data into your Supabase database.

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Setup Instructions](#setup-instructions)
- [File Structure](#file-structure)
- [Configuration](#configuration)
- [Usage](#usage)
- [Database Schema](#database-schema)
- [Monitoring & Troubleshooting](#monitoring--troubleshooting)
- [Development](#development)

## 🎯 Overview

The PTR Ingestion Worker is a production-ready system that:

- **Discovers** PTR filings from the House Clerk website
- **Downloads** PDF documents with integrity verification
- **Parses** trade data using multiple extraction strategies
- **Normalizes** data to match your existing schema
- **Deduplicates** trades using SHA256 hashing
- **Stores** everything in your Supabase database
- **Monitors** health and performance with structured logging

### Key Features

- ✅ **Idempotent Operations** - Safe to run multiple times
- ✅ **Automatic Deduplication** - Prevents duplicate trades
- ✅ **Robust Error Handling** - Retry logic with exponential backoff
- ✅ **Performance Optimized** - Concurrent processing with rate limiting
- ✅ **Production Ready** - Structured logging, metrics, health checks
- ✅ **Schema Compatible** - Works with your existing trades table

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Discovery     │───▶│   Downloader    │───▶│     Parser      │
│ (House Clerk)   │    │ (PDF + Storage) │    │ (Multi-strategy)│
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Database      │◀───│   Normalizer    │◀───│   Validation    │
│ (Supabase)      │    │ (Schema Mapping)│    │ (Data Quality)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Components

1. **Discovery Module** (`src/discovery/`)
   - Scrapes House Clerk website for PTR filing URLs
   - Handles pagination and year-based filtering
   - Extracts member names, filing dates, document URLs

2. **Downloader Module** (`src/downloader/`)
   - Downloads PDF files with integrity verification
   - Stores files in Supabase storage bucket
   - Computes SHA256 hashes for file verification

3. **Parser Module** (`src/parser/`)
   - Extracts trade data using multiple strategies:
     - Table extraction with pdfplumber
     - Text extraction with regex patterns
     - Line-by-line parsing for structured data
   - Handles multi-page documents and wrapped cells

4. **Normalizer Module** (`src/normalizer/`)
   - Maps parsed data to your existing schema
   - Standardizes asset names, tickers, transaction types
   - Normalizes date formats and amount ranges
   - Calculates amount min/max from ranges

5. **Upserter Module** (`src/upserter/`)
   - Handles idempotent database operations
   - Creates/updates congress members
   - Upserts trades with deduplication via row_hash
   - Batch processing for performance

6. **Pipeline Orchestrator** (`src/pipeline/`)
   - Coordinates all components in sequence
   - Handles errors and retries
   - Collects metrics and statistics

7. **Task Scheduler** (`src/scheduler/`)
   - Cron-like scheduling for automated runs
   - Health checks and monitoring
   - Exponential backoff on failures

## 📋 Prerequisites

### Required Software
- **Python 3.9+** (3.11 recommended)
- **pip** (Python package manager)
- **Supabase Project** with database and storage

### Required Services
- **Supabase Database** - PostgreSQL with your existing schema
- **Supabase Storage** - For storing PDF files
- **Internet Connection** - To access House Clerk website

## 🚀 Setup Instructions

### Step 1: Run Database Migration

**CRITICAL: Do this first before anything else**

1. Open your Supabase project dashboard
2. Go to **SQL Editor**
3. Copy and paste the entire contents of `supabase/migrations/004_ptr_ingestion_complete_setup.sql`
4. Click **Run** to execute the migration

This migration adds:
- `row_hash`, `source`, `filing_id`, `notes` columns to trades table
- Indexes for performance
- Storage bucket for PDFs
- Deduplication functions
- Monitoring views

### Step 2: Install Dependencies

```bash
cd ingestionworker
pip install -r requirements.txt
```

### Step 3: Configure Environment

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` with your actual Supabase credentials:
```bash
# Supabase Configuration (REQUIRED)
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here

# Storage Configuration
STORAGE_BUCKET=ptr-archive

# Discovery Configuration
HOUSE_YEAR_WINDOW=2023-2025
SCAN_INTERVAL_MIN=360

# Performance Configuration
MAX_CONCURRENCY=5
THROTTLE_MS=1000

# Other settings (optional)
USER_AGENT=PTR-Ingestion-Worker/1.0
LOG_LEVEL=INFO
MAX_RETRIES=3
RETRY_BACKOFF_FACTOR=2.0
HEALTH_CHECK_PORT=8080
```

**How to get Supabase credentials:**
1. Go to your Supabase project dashboard
2. Click **Settings** → **API**
3. Copy the **URL** and **service_role** key (NOT the anon key)

### Step 3: Test the Setup

Run a health check to verify everything is configured correctly:

```bash
python -m src.main --mode health
```

You should see:
```
PTR INGESTION WORKER HEALTH STATUS
====================================
Overall Status: HEALTHY
✓ discovery: healthy
✓ database: healthy
✓ parser: healthy
✓ normalizer: healthy
```

### Step 4: Test Discovery and Downloading

Run discovery only to test the scraping:

```bash
python -m src.main --mode discovery --limit 5
```

This will find 5 recent PTR filings without processing them.

Test the downloader with discovered zip files:

```bash
python -m src.main --mode download --limit 1
```

This will:
1. Discover PTR zip file URLs
2. Download and extract one zip file
3. Show the extracted TXT/XML file structure

### Step 5: Run Full Pipeline (Test)

Process a small number of filings to test the complete pipeline:

```bash
python -m src.main --mode once --limit 3
```

This will:
1. Discover 3 PTR filings
2. Download the PDFs
3. Parse trade data
4. Normalize and store in database

### Step 6: Start Scheduled Mode (Production)

Once testing is successful, start the worker in scheduled mode:

```bash
python -m src.main --mode scheduled
```

This runs continuously, checking for new filings every 6 hours (configurable).

## 📁 File Structure

```
ingestionworker/
├── src/
│   ├── config/
│   │   └── settings.py              # Environment configuration
│   ├── database/
│   │   ├── models.py                # Data models (CongressMember, Trade)
│   │   └── connection.py            # Database repositories
│   ├── discovery/
│   │   └── ptr_discovery.py         # House Clerk website scraping
│   ├── downloader/
│   │   └── pdf_downloader.py        # PDF download and storage
│   ├── parser/
│   │   └── pdf_parser.py            # PDF parsing (tables, text, regex)
│   ├── normalizer/
│   │   └── data_normalizer.py       # Data cleaning and standardization
│   ├── upserter/
│   │   └── data_upserter.py         # Database operations
│   ├── pipeline/
│   │   └── ingestion_pipeline.py    # Main orchestrator
│   ├── scheduler/
│   │   └── task_scheduler.py        # Cron-like scheduling
│   ├── utils/
│   │   ├── logging_config.py        # Structured logging setup
│   │   └── retry_utils.py           # Retry logic and error handling
│   └── main.py                      # Application entry point
├── requirements.txt                 # Python dependencies
├── .env.example                     # Environment template
├── Dockerfile                       # Container configuration
├── docker-compose.yml              # Docker orchestration
└── README.md                        # This file
```

## ⚙️ Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SUPABASE_URL` | ✅ | - | Your Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | ✅ | - | Service role key (NOT anon key) |
| `STORAGE_BUCKET` | ✅ | `ptr-archive` | Supabase storage bucket name |
| `HOUSE_YEAR_WINDOW` | ✅ | `2023-2025` | Year range for discovery |
| `SCAN_INTERVAL_MIN` | ✅ | `360` | Minutes between scheduled runs |
| `MAX_CONCURRENCY` | ❌ | `5` | Max concurrent downloads |
| `THROTTLE_MS` | ❌ | `1000` | Delay between requests (ms) |
| `USER_AGENT` | ❌ | `PTR-Ingestion-Worker/1.0` | HTTP user agent |
| `LOG_LEVEL` | ❌ | `INFO` | Logging level |
| `MAX_RETRIES` | ❌ | `3` | Max retry attempts |
| `RETRY_BACKOFF_FACTOR` | ❌ | `2.0` | Retry delay multiplier |
| `HEALTH_CHECK_PORT` | ❌ | `8080` | Health check HTTP port |

### Performance Tuning

- **MAX_CONCURRENCY**: Higher = faster but more resource usage
- **THROTTLE_MS**: Lower = faster but may trigger rate limiting
- **SCAN_INTERVAL_MIN**: How often to check for new filings
- **HOUSE_YEAR_WINDOW**: Broader range finds more filings but takes longer

## 🎮 Usage

### Command Line Interface

```bash
# Run once and exit
python -m src.main --mode once [--limit N]

# Run continuously (production)
python -m src.main --mode scheduled

# Health check
python -m src.main --mode health

# Discovery only
python -m src.main --mode discovery [--limit N]

# Custom logging
python -m src.main --mode once --log-level DEBUG
```

### Year-by-Year Processing

The ingestion worker now supports processing data one year at a time for more granular control:

```bash
# Process only 2023 data
python -m src.main --mode once --year 2023

# Process only 2024 data
python -m src.main --mode bulk --year 2024

# Process a specific year range
python -m src.main --mode once --year-start 2023 --year-end 2024

# Discover filings for a specific year
python -m src.main --mode discovery --year 2023 --limit 10

# Download files for 2023 only
python -m src.main --mode download --year 2023 --limit 5
```

**Year Processing Options:**
- `--year YYYY`: Process a specific year (sets both start and end to the same year)
- `--year-start YYYY`: Start year for range processing
- `--year-end YYYY`: End year for range processing

**Benefits of Year-by-Year Processing:**
- Reduced memory usage for large datasets
- Better error isolation (failures in one year don't affect others)
- Easier debugging and monitoring
- Incremental processing for historical data backfills
- More predictable resource consumption

### Docker Usage

```bash
# Build image
docker build -t ptr-ingestion-worker .

# Run with environment file
docker run --env-file .env ptr-ingestion-worker --mode once --limit 5

# Run with docker-compose
docker-compose up
```

### Programmatic Usage

```python
from src.pipeline.ingestion_pipeline import IngestionPipeline
from src.config.settings import Settings

# Initialize
settings = Settings()
pipeline = IngestionPipeline(settings)

# Run pipeline
results = await pipeline.run_full_pipeline(limit=10)
print(f"Processed {results['trades_upserted']} trades")
```

## 🗄️ Database Schema

### Tables Modified

The worker integrates with your existing schema and adds these fields to the `trades` table:

```sql
-- New columns added by migration
ALTER TABLE public.trades ADD COLUMN row_hash TEXT;      -- For deduplication
ALTER TABLE public.trades ADD COLUMN source TEXT;       -- Data source tracking
ALTER TABLE public.trades ADD COLUMN filing_id TEXT;    -- Original filing ID
ALTER TABLE public.trades ADD COLUMN notes TEXT;        -- Additional info
```

### Data Flow

1. **Congress Members**: Created/updated by full name matching
2. **Trades**: Inserted with deduplication via `row_hash`
3. **Row Hash**: Generated from `source|filing_id|asset_description|ticker|transaction_type|date|amount`

### Views Created

- `trade_summaries`: Enhanced trade view with member info
- `ptr_ingestion_stats`: Statistics by source

### Functions Created

- `generate_trade_row_hash()`: Consistent hash generation
- `find_duplicate_trades()`: Detect duplicates
- `cleanup_duplicate_trades()`: Remove duplicates

## 📊 Monitoring & Troubleshooting

### Health Checks

```bash
# Check overall health
python -m src.main --mode health

# Check specific component
curl http://localhost:8080/health
```

### Logs

The worker uses structured JSON logging:

```json
{
  "timestamp": "2025-01-09T13:00:00Z",
  "level": "info",
  "message": "PDF parsing completed",
  "filing_id": "abc123",
  "trades_found": 15,
  "duration": 2.3
}
```

### Common Issues

**1. Database Connection Errors**
```
Error: Failed to connect to database
```
- Check `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`
- Verify service role key (not anon key)
- Check network connectivity

**2. Storage Bucket Errors**
```
Error: Bucket 'ptr-archive' not found
```
- Run the database migration first
- Check bucket exists in Supabase Storage
- Verify storage policies

**3. Discovery Errors**
```
Error: HTTP 403: Forbidden
```
- House Clerk website may be blocking requests
- Increase `THROTTLE_MS` to reduce request rate
- Check `USER_AGENT` setting

**4. Parsing Errors**
```
Error: No trades found in PDF
```
- PDF format may have changed
- Check PDF manually for trade data
- Review parser logs for details

### Performance Monitoring

Check ingestion statistics:

```sql
-- View ingestion stats
SELECT * FROM ptr_ingestion_stats;

-- Check recent trades
SELECT * FROM trade_summaries 
WHERE source = 'house_clerk' 
ORDER BY created_at DESC 
LIMIT 10;

-- Find duplicates
SELECT * FROM find_duplicate_trades();
```

### Cleanup Operations

```sql
-- Preview duplicate cleanup (dry run)
SELECT * FROM cleanup_duplicate_trades(true);

-- Actually remove duplicates
SELECT * FROM cleanup_duplicate_trades(false);
```

## 🔧 Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest tests/

# Run with coverage
pytest --cov=src tests/
```

### Code Structure

- **Async/Await**: All I/O operations are asynchronous
- **Type Hints**: Full type annotations for better IDE support
- **Error Handling**: Comprehensive exception handling with retries
- **Logging**: Structured logging with contextual information
- **Configuration**: Environment-based configuration management

### Adding New Sources

To add Senate or other sources:

1. Create new discovery module in `src/discovery/`
2. Add source type to database constraint
3. Update normalizer for source-specific formats
4. Add to pipeline orchestrator

### Extending Functionality

- **New Data Fields**: Add to `Trade` model and migration
- **Custom Parsing**: Extend `PDFParser` with new strategies
- **Additional Validation**: Add rules to `DataNormalizer`
- **New Outputs**: Create additional upserter targets

## 📝 Troubleshooting Checklist

Before running the worker, ensure:

- [ ] Database migration `004_ptr_ingestion_complete_setup.sql` has been executed
- [ ] `.env` file contains valid Supabase URL and service role key
- [ ] `ptr-archive` storage bucket exists and has proper policies
- [ ] Python dependencies are installed (`pip install -r requirements.txt`)
- [ ] Health check passes (`python -m src.main --mode health`)
- [ ] Discovery test works (`python -m src.main --mode discovery --limit 1`)

## 🆘 Support

If you encounter issues:

1. **Check the logs** - All operations are logged with context
2. **Run health check** - Identifies configuration problems
3. **Test components individually** - Use discovery/parse modes
4. **Check database** - Verify migration ran successfully
5. **Review configuration** - Ensure all required env vars are set

The worker is designed to be robust and self-healing, with comprehensive error handling and retry logic. Most issues are configuration-related and can be resolved by following the setup instructions carefully.
