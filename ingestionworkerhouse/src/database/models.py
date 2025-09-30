"""Database models for the House PTR Ingestion Worker - Matches 007_create_fresh_schema.sql."""

from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional, Dict, Any
import hashlib
import json
from decimal import Decimal


@dataclass
class Politician:
    """Model for politicians table - stores basic politician info without disclosure data."""
    id: Optional[str] = None  # UUID
    full_name: str = ""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    chamber: str = "house"
    state: Optional[str] = None
    district: Optional[str] = None
    party: Optional[str] = None
    bioguide_id: Optional[str] = None
    external_ids: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insertion."""
        data = {
            "full_name": self.full_name,
            "chamber": self.chamber,
        }
        
        # Only include fields that exist in the current table schema
        # Note: first_name, last_name, party, bioguide_id, external_ids 
        # require migration 010 to be applied first
        if self.state:
            data["state"] = self.state
        if self.district:
            data["district"] = self.district
            
        return data


@dataclass
class Disclosure:
    """Model for disclosures table - stores each filing/disclosure."""
    id: Optional[str] = None  # UUID
    politician_id: str = ""  # UUID reference to politicians
    source: str = "house_clerk"
    doc_id: str = ""  # The DocID from the PTR filing (e.g., 40003749)
    filing_type: Optional[str] = None  # P, A, C, D, O, X
    filed_date: Optional[datetime] = None
    raw: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insertion."""
        data = {
            "politician_id": self.politician_id,
            "source": self.source,
            "doc_id": self.doc_id,
        }
        
        if self.filing_type:
            data["filing_type"] = self.filing_type
        if self.filed_date:
            data["filed_date"] = self.filed_date.isoformat() if isinstance(self.filed_date, datetime) else self.filed_date
        if self.raw:
            data["raw"] = self.raw
            
        return data


@dataclass
class Trade:
    """Model for trades table - stores individual trades from disclosures."""
    id: Optional[str] = None  # UUID
    disclosure_id: str = ""  # UUID reference to disclosures
    politician_id: str = ""  # UUID reference to politicians
    transaction_date: Optional[datetime] = None
    published_at: Optional[datetime] = None
    ticker: Optional[str] = None
    asset_name: str = ""
    side: Optional[str] = None  # 'buy' or 'sell'
    amount_range: Optional[str] = None
    notes: Optional[str] = None
    row_hash: str = ""  # Required for deduplication
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def generate_row_hash(self) -> str:
        """Generate SHA256 hash for idempotency."""
        hash_input = f"{self.disclosure_id}|{self.asset_name}|{self.ticker or ''}|{self.side or ''}|{self.transaction_date}|{self.amount_range or ''}"
        return hashlib.sha256(hash_input.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insertion."""
        data = {
            "disclosure_id": self.disclosure_id,
            "politician_id": self.politician_id,
            "asset_name": self.asset_name,
            "row_hash": self.row_hash or self.generate_row_hash(),
        }
        
        if self.transaction_date:
            data["transaction_date"] = self.transaction_date.isoformat() if isinstance(self.transaction_date, datetime) else self.transaction_date
        if self.published_at:
            data["published_at"] = self.published_at.isoformat() if isinstance(self.published_at, datetime) else self.published_at
        if self.ticker:
            data["ticker"] = self.ticker
        if self.side:
            data["side"] = self.side
        if self.amount_range:
            data["amount_range"] = self.amount_range
        if self.notes:
            data["notes"] = self.notes
            
        return data


@dataclass
class ProcessingMetrics:
    """Model for tracking processing metrics."""
    filings_discovered: int = 0
    filings_processed: int = 0
    pdf_download_failures: int = 0
    parse_failures: int = 0
    trades_inserted: int = 0
    duplicates_skipped: int = 0
    last_successful_run: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/monitoring."""
        return {
            "filings_discovered": self.filings_discovered,
            "filings_processed": self.filings_processed,
            "pdf_download_failures": self.pdf_download_failures,
            "parse_failures": self.parse_failures,
            "trades_inserted": self.trades_inserted,
            "duplicates_skipped": self.duplicates_skipped,
            "last_successful_run": self.last_successful_run.isoformat() if self.last_successful_run else None
        }


@dataclass
class ParsedTradeRow:
    """Model for raw parsed trade data before normalization."""
    owner: Optional[str] = None
    asset_name: str = ""
    ticker: Optional[str] = None
    transaction_type: Optional[str] = None
    transaction_date: Optional[str] = None
    amount_range: Optional[str] = None
    notes: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "owner": self.owner,
            "asset_name": self.asset_name,
            "ticker": self.ticker,
            "transaction_type": self.transaction_type,
            "transaction_date": self.transaction_date,
            "amount_range": self.amount_range,
            "notes": self.notes,
            "raw_data": self.raw_data or {}
        }


# Legacy alias for compatibility
CongressMember = Politician
