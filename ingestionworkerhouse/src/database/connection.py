"""Database connection utilities for Supabase/Postgres - Matches 007_create_fresh_schema.sql."""

import asyncio
from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from supabase import create_client, Client
import structlog

from ..config.settings import settings

logger = structlog.get_logger()


class DatabaseConnection:
    """Database connection manager for Supabase/Postgres operations."""
    
    def __init__(self):
        self.supabase: Optional[Client] = None
        self.pg_conn = None
        
    def connect(self):
        """Initialize database connections."""
        try:
            # Initialize Supabase client
            self.supabase = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_ROLE_KEY
            )
            
            # Test connection
            result = self.supabase.table("politicians").select("id").limit(1).execute()
            logger.info("Database connection established", service="supabase")
            
        except Exception as e:
            logger.error("Failed to connect to database", error=str(e))
            raise
    
    def get_supabase_client(self) -> Client:
        """Get Supabase client instance."""
        if not self.supabase:
            self.connect()
        return self.supabase
    
    async def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute raw SQL query with parameters."""
        try:
            # For complex queries, we might need direct PostgreSQL connection
            # This is a placeholder for direct SQL execution if needed
            client = self.get_supabase_client()
            # Note: Supabase Python client doesn't support raw SQL directly
            # For complex queries, we'd need to use the REST API or direct psycopg2
            logger.warning("Raw SQL execution not implemented in this version")
            return []
            
        except Exception as e:
            logger.error("Query execution failed", query=query, error=str(e))
            raise
    
    def close(self):
        """Close database connections."""
        if self.pg_conn:
            self.pg_conn.close()
        logger.info("Database connections closed")


class PoliticianRepository:
    """Repository for politicians table operations."""
    
    def __init__(self, db: DatabaseConnection):
        self.db = db
    
    async def find_by_name(self, full_name: str) -> Optional[Dict[str, Any]]:
        """Find politician by full name."""
        try:
            client = self.db.get_supabase_client()
            result = client.table("politicians").select("*").eq("full_name", full_name).execute()
            
            if result.data:
                return result.data[0]
            return None
            
        except Exception as e:
            logger.error("Failed to find politician", name=full_name, error=str(e))
            raise
    
    async def find_by_name_state_district(self, full_name: str, state: str, district: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Find politician by name, state, and district for more accurate matching."""
        try:
            client = self.db.get_supabase_client()
            query = client.table("politicians").select("*").eq("full_name", full_name).eq("state", state)
            
            if district:
                query = query.eq("district", district)
            
            result = query.execute()
            
            if result.data:
                return result.data[0]
            return None
            
        except Exception as e:
            logger.error("Failed to find politician", name=full_name, state=state, district=district, error=str(e))
            raise
    
    async def upsert(self, politician_data: Dict[str, Any]) -> Dict[str, Any]:
        """Upsert politician record (insert or update if exists)."""
        try:
            client = self.db.get_supabase_client()
            
            # Try to find existing politician first
            existing = await self.find_by_name_state_district(
                politician_data["full_name"],
                politician_data.get("state"),
                politician_data.get("district")
            )
            
            if existing:
                # Update existing record if needed
                logger.info("Politician already exists", politician_id=existing["id"])
                return existing
            
            # Create new politician
            result = client.table("politicians").insert(politician_data).execute()
            
            if result.data:
                logger.info("Politician created", politician_id=result.data[0]["id"])
                return result.data[0]
            
            raise Exception("Failed to upsert politician")
            
        except Exception as e:
            logger.error("Failed to upsert politician", data=politician_data, error=str(e))
            raise
    
    async def create(self, politician_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new politician record."""
        try:
            client = self.db.get_supabase_client()
            result = client.table("politicians").insert(politician_data).execute()
            
            if result.data:
                logger.info("Politician created", politician_id=result.data[0]["id"])
                return result.data[0]
            
            raise Exception("Failed to create politician")
            
        except Exception as e:
            logger.error("Failed to create politician", data=politician_data, error=str(e))
            raise


class DisclosureRepository:
    """Repository for disclosures table operations."""
    
    def __init__(self, db: DatabaseConnection):
        self.db = db
    
    async def find_by_doc_id(self, politician_id: str, doc_id: str) -> Optional[Dict[str, Any]]:
        """Find disclosure by politician_id and doc_id."""
        try:
            client = self.db.get_supabase_client()
            result = client.table("disclosures").select("*").eq("politician_id", politician_id).eq("doc_id", doc_id).execute()
            
            if result.data:
                return result.data[0]
            return None
            
        except Exception as e:
            logger.error("Failed to find disclosure", politician_id=politician_id, doc_id=doc_id, error=str(e))
            raise
    
    async def upsert(self, disclosure_data: Dict[str, Any]) -> Dict[str, Any]:
        """Upsert disclosure record (insert or return existing)."""
        try:
            # Check if disclosure already exists
            existing = await self.find_by_doc_id(
                disclosure_data["politician_id"],
                disclosure_data["doc_id"]
            )
            
            if existing:
                logger.info("Disclosure already exists", disclosure_id=existing["id"])
                return existing
            
            # Create new disclosure
            return await self.create(disclosure_data)
            
        except Exception as e:
            logger.error("Failed to upsert disclosure", data=disclosure_data, error=str(e))
            raise
    
    async def create(self, disclosure_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new disclosure record."""
        try:
            client = self.db.get_supabase_client()
            result = client.table("disclosures").insert(disclosure_data).execute()
            
            if result.data:
                logger.info("Disclosure created", disclosure_id=result.data[0]["id"])
                return result.data[0]
            
            raise Exception("Failed to create disclosure")
            
        except Exception as e:
            logger.error("Failed to create disclosure", data=disclosure_data, error=str(e))
            raise


class TradeRepository:
    """Repository for trades table operations."""
    
    def __init__(self, db: DatabaseConnection):
        self.db = db
    
    async def find_by_row_hash(self, row_hash: str) -> Optional[Dict[str, Any]]:
        """Find trade by row_hash for deduplication."""
        try:
            client = self.db.get_supabase_client()
            result = client.table("trades").select("*").eq("row_hash", row_hash).execute()
            
            if result.data:
                return result.data[0]
            return None
            
        except Exception as e:
            logger.error("Failed to find trade by hash", row_hash=row_hash, error=str(e))
            raise
    
    async def create_batch(self, trades_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create multiple trade records in batch."""
        try:
            client = self.db.get_supabase_client()
            
            # Filter out trades that already exist (by row_hash)
            new_trades = []
            for trade in trades_data:
                existing = await self.find_by_row_hash(trade["row_hash"])
                if not existing:
                    new_trades.append(trade)
            
            if not new_trades:
                logger.info("All trades already exist, skipping insert")
                return []
            
            result = client.table("trades").insert(new_trades).execute()
            
            if result.data:
                logger.info("Trades created", count=len(result.data), duplicates_skipped=len(trades_data) - len(new_trades))
                return result.data
            
            raise Exception("Failed to create trades")
            
        except Exception as e:
            logger.error("Failed to create trades batch", count=len(trades_data), error=str(e))
            raise
    
    async def create(self, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create single trade record."""
        try:
            # Check if trade already exists
            existing = await self.find_by_row_hash(trade_data["row_hash"])
            if existing:
                logger.info("Trade already exists", trade_id=existing["id"])
                return existing
            
            client = self.db.get_supabase_client()
            result = client.table("trades").insert(trade_data).execute()
            
            if result.data:
                logger.info("Trade created", trade_id=result.data[0]["id"])
                return result.data[0]
            
            raise Exception("Failed to create trade")
            
        except Exception as e:
            logger.error("Failed to create trade", data=trade_data, error=str(e))
            raise


# Legacy alias for compatibility
CongressMemberRepository = PoliticianRepository


# Global database instance
db_connection = DatabaseConnection()
