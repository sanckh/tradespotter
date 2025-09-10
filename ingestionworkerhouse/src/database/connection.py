"""Database connection utilities for Supabase/Postgres - Updated for existing schema."""

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
            result = self.supabase.table("congress_members").select("id").limit(1).execute()
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


class CongressMemberRepository:
    """Repository for congress_members operations."""
    
    def __init__(self, db: DatabaseConnection):
        self.db = db
    
    async def find_by_name(self, full_name: str) -> Optional[Dict[str, Any]]:
        """Find congress member by full name."""
        try:
            client = self.db.get_supabase_client()
            result = client.table("congress_members").select("*").eq("full_name", full_name).execute()
            
            if result.data:
                return result.data[0]
            return None
            
        except Exception as e:
            logger.error("Failed to find congress member", name=full_name, error=str(e))
            raise
    
    async def create(self, member_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new congress member record."""
        try:
            client = self.db.get_supabase_client()
            result = client.table("congress_members").insert(member_data).execute()
            
            if result.data:
                logger.info("Congress member created", member_id=result.data[0]["id"])
                return result.data[0]
            
            raise Exception("Failed to create congress member")
            
        except Exception as e:
            logger.error("Failed to create congress member", data=member_data, error=str(e))
            raise


class TradeRepository:
    """Repository for trade operations - Updated for existing schema."""
    
    def __init__(self, db: DatabaseConnection):
        self.db = db
    
    async def find_duplicate_trade(self, trade_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find duplicate trade based on key fields."""
        try:
            client = self.db.get_supabase_client()
            
            # Check for duplicates using key fields
            result = client.table("trades").select("*").match({
                "member_id": trade_data["member_id"],
                "transaction_date": trade_data["transaction_date"],
                "ticker": trade_data.get("ticker"),
                "asset_description": trade_data["asset_description"],
                "transaction_type": trade_data["transaction_type"],
                "amount_range": trade_data["amount_range"]
            }).execute()
            
            if result.data:
                return result.data[0]
            return None
            
        except Exception as e:
            logger.error("Failed to check for duplicate trade", error=str(e))
            raise
    
    async def create_batch(self, trades_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create multiple trade records in batch."""
        try:
            client = self.db.get_supabase_client()
            result = client.table("trades").insert(trades_data).execute()
            
            if result.data:
                logger.info("Trades created", count=len(result.data))
                return result.data
            
            raise Exception("Failed to create trades")
            
        except Exception as e:
            logger.error("Failed to create trades batch", count=len(trades_data), error=str(e))
            raise
    
    async def create(self, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create single trade record."""
        try:
            client = self.db.get_supabase_client()
            result = client.table("trades").insert(trade_data).execute()
            
            if result.data:
                logger.info("Trade created", trade_id=result.data[0]["id"])
                return result.data[0]
            
            raise Exception("Failed to create trade")
            
        except Exception as e:
            logger.error("Failed to create trade", data=trade_data, error=str(e))
            raise


# Legacy repositories for compatibility
class PoliticianRepository:
    """Legacy repository - maps to CongressMemberRepository."""
    
    def __init__(self, db: DatabaseConnection):
        self.congress_member_repo = CongressMemberRepository(db)
    
    async def find_by_name(self, full_name: str) -> Optional[Dict[str, Any]]:
        """Find politician by full name."""
        return await self.congress_member_repo.find_by_name(full_name)
    
    async def create(self, politician_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new politician record."""
        return await self.congress_member_repo.create(politician_data)


class DisclosureRepository:
    """Repository for disclosure tracking - uses external_ids in congress_members."""
    
    def __init__(self, db: DatabaseConnection):
        self.db = db
        self.congress_member_repo = CongressMemberRepository(db)
    
    async def find_by_report_id(self, source: str, report_id: str) -> Optional[Dict[str, Any]]:
        """Find disclosure by source and report_id in congress_members external_ids."""
        try:
            client = self.db.get_supabase_client()
            
            # Search for congress member with this report_id in external_ids
            result = client.table("congress_members").select("*").execute()
            
            for member in result.data or []:
                external_ids = member.get("external_ids", {})
                processed_reports = external_ids.get("processed_reports", [])
                
                for report in processed_reports:
                    if report.get("source") == source and report.get("report_id") == report_id:
                        return {
                            "id": f"{member['id']}_{report_id}",
                            "member_id": member["id"],
                            "source": source,
                            "report_id": report_id,
                            **report
                        }
            
            return None
            
        except Exception as e:
            logger.error("Failed to find disclosure", source=source, report_id=report_id, error=str(e))
            raise
    
    async def create(self, disclosure_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new disclosure record by updating congress_member external_ids."""
        try:
            member_id = disclosure_data["member_id"]
            client = self.db.get_supabase_client()
            
            # Get current member data
            member_result = client.table("congress_members").select("*").eq("id", member_id).execute()
            
            if not member_result.data:
                raise Exception(f"Congress member not found: {member_id}")
            
            member = member_result.data[0]
            external_ids = member.get("external_ids", {})
            processed_reports = external_ids.get("processed_reports", [])
            
            # Add new report
            new_report = {
                "source": disclosure_data["source"],
                "report_id": disclosure_data["report_id"],
                "filed_date": disclosure_data.get("filed_date").isoformat() if disclosure_data.get("filed_date") else None,
                "published_at": disclosure_data.get("published_at").isoformat() if disclosure_data.get("published_at") else None,
                "doc_url": disclosure_data.get("doc_url", ""),
                "raw": disclosure_data.get("raw", {}),
                "created_at": disclosure_data.get("created_at").isoformat() if disclosure_data.get("created_at") else None
            }
            
            processed_reports.append(new_report)
            external_ids["processed_reports"] = processed_reports
            
            # Update member
            update_result = client.table("congress_members").update({
                "external_ids": external_ids
            }).eq("id", member_id).execute()
            
            if update_result.data:
                logger.info("Disclosure created", member_id=member_id, report_id=disclosure_data["report_id"])
                return {
                    "id": f"{member_id}_{disclosure_data['report_id']}",
                    **disclosure_data
                }
            
            raise Exception("Failed to create disclosure")
            
        except Exception as e:
            logger.error("Failed to create disclosure", data=disclosure_data, error=str(e))
            raise
    
    async def update_raw_data(self, disclosure_id: str, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update raw data for existing disclosure."""
        # For amended filings, we would update the external_ids
        logger.info("Disclosure raw data update requested", disclosure_id=disclosure_id)
        # Implementation would update the specific report in external_ids
        return {"id": disclosure_id, "raw": raw_data}


# Global database instance
db_connection = DatabaseConnection()
