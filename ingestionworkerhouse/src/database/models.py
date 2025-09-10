"""Database models for the House PTR Ingestion Worker - Updated for existing schema."""

from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional, Dict, Any
import hashlib
import json
from decimal import Decimal


@dataclass
class CongressMember:
    """Model for congress_members table."""
    id: Optional[str] = None  # UUID
    full_name: str = ""
    chamber: str = "house"
    state: Optional[str] = None
    party: Optional[str] = None
    external_ids: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insertion."""
        return {
            "full_name": self.full_name,
            "chamber": self.chamber,
            "state": self.state,
            "party": self.party,
            "external_ids": self.external_ids or {},
            "created_at": self.created_at or datetime.utcnow()
        }


@dataclass
class Trade:
    """Model for trades table - Updated to match existing schema."""
    id: Optional[str] = None  # UUID
    member_id: str = ""  # UUID reference to congress_members
    transaction_date: Optional[date] = None
    disclosure_date: Optional[date] = None
    ticker: Optional[str] = None
    asset_description: str = ""
    asset_type: str = "Stock"
    transaction_type: str = "Purchase"  # Purchase, Sale, Exchange
    amount_range: str = ""
    amount_min: Optional[Decimal] = None
    amount_max: Optional[Decimal] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # For deduplication - we'll compute this from the existing fields
    _row_hash: Optional[str] = None

    def generate_row_hash(self, source: str = "house_clerk", report_id: str = "") -> str:
        """Generate SHA256 hash for idempotency using existing fields."""
        # Use available fields to create a unique hash
        hash_input = f"{source}|{report_id}|{self.asset_description}|{self.ticker or ''}|{self.transaction_type}|{self.transaction_date}|{self.amount_range}"
        return hashlib.sha256(hash_input.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insertion."""
        return {
            "member_id": self.member_id,
            "transaction_date": self.transaction_date,
            "disclosure_date": self.disclosure_date,
            "ticker": self.ticker,
            "asset_description": self.asset_description,
            "asset_type": self.asset_type,
            "transaction_type": self.transaction_type,
            "amount_range": self.amount_range,
            "amount_min": self.amount_min,
            "amount_max": self.amount_max,
            "created_at": self.created_at or datetime.utcnow(),
            "updated_at": self.updated_at or datetime.utcnow()
        }


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


# Legacy models for compatibility
@dataclass
class Politician:
    """Legacy model - maps to CongressMember."""
    id: Optional[str] = None
    full_name: str = ""
    chamber: str = "house"
    state: Optional[str] = None
    party: Optional[str] = None
    external_ids: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insertion."""
        return {
            "full_name": self.full_name,
            "chamber": self.chamber,
            "state": self.state,
            "party": self.party,
            "external_ids": self.external_ids or {},
            "created_at": self.created_at or datetime.utcnow()
        }


@dataclass
class Disclosure:
    """Model for tracking disclosure metadata - stored in congress_members or separate tracking."""
    id: Optional[str] = None
    member_id: str = ""
    source: str = "house_clerk"
    report_id: str = ""
    filed_date: Optional[datetime] = None
    published_at: Optional[datetime] = None
    doc_url: str = ""
    raw: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insertion."""
        return {
            "member_id": self.member_id,
            "source": self.source,
            "report_id": self.report_id,
            "filed_date": self.filed_date,
            "published_at": self.published_at,
            "doc_url": self.doc_url,
            "raw": self.raw or {},
            "created_at": self.created_at or datetime.utcnow()
        }
