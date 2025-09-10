"""Data upserter for idempotent upsert of congress members and trades - Updated for existing schema."""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date
import structlog
from supabase import create_client, Client

from ..config.settings import Settings
from ..database.models import CongressMember, Trade
from ..database.connection import DatabaseConnection, CongressMemberRepository, TradeRepository
from ..utils.retry_utils import retry_with_backoff, RetryableError
from ..utils.logging_config import performance_timer, metrics

logger = structlog.get_logger()


class DataUpserter:
    """Handles idempotent upsert of congress members and trades with deduplication."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.db_connection: Optional[DatabaseConnection] = None
        self.member_repo: Optional[CongressMemberRepository] = None
        self.trade_repo: Optional[TradeRepository] = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.db_connection = DatabaseConnection(self.settings)
        await self.db_connection.connect()
        
        self.member_repo = CongressMemberRepository(self.db_connection)
        self.trade_repo = TradeRepository(self.db_connection)
        
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.db_connection:
            await self.db_connection.close()
    
    async def upsert_filing_data(
        self,
        member_name: str,
        filing_id: str,
        filing_date: Optional[date],
        trades: List[Trade]
    ) -> Dict[str, Any]:
        """
        Upsert complete filing data including member and trades.
        
        Args:
            member_name: Name of congress member
            filing_id: Unique filing identifier
            filing_date: Date the filing was submitted
            trades: List of normalized Trade objects
            
        Returns:
            Dictionary with upsert results and statistics
        """
        logger.info(
            "Starting filing data upsert",
            filing_id=filing_id,
            member_name=member_name,
            trades_count=len(trades)
        )
        
        with performance_timer("data_upsert.total", {"filing_id": filing_id}):
            try:
                # Step 1: Upsert congress member
                member = await self._upsert_congress_member(member_name)
                if not member:
                    raise Exception(f"Failed to upsert congress member: {member_name}")
                
                # Step 2: Update trades with member_id
                for trade in trades:
                    trade.member_id = member.id
                    if not trade.disclosure_date and filing_date:
                        trade.disclosure_date = filing_date
                
                # Step 3: Upsert trades with deduplication
                trade_results = await self._upsert_trades_batch(trades, filing_id)
                
                # Compile results
                results = {
                    'filing_id': filing_id,
                    'member_id': member.id,
                    'member_name': member_name,
                    'trades_processed': len(trades),
                    'trades_inserted': trade_results['inserted'],
                    'trades_updated': trade_results['updated'],
                    'trades_skipped': trade_results['skipped'],
                    'errors': trade_results['errors'],
                    'processing_time': datetime.utcnow().isoformat()
                }
                
                logger.info(
                    "Filing data upsert completed",
                    filing_id=filing_id,
                    **{k: v for k, v in results.items() if k not in ['filing_id', 'processing_time']}
                )
                
                metrics.increment("data_upsert.filings_processed")
                metrics.gauge("data_upsert.trades_per_filing", len(trades))
                
                return results
                
            except Exception as e:
                logger.error(
                    "Filing data upsert failed",
                    filing_id=filing_id,
                    member_name=member_name,
                    error=str(e)
                )
                metrics.increment("data_upsert.filing_errors")
                raise
    
    async def _upsert_congress_member(self, member_name: str) -> Optional[CongressMember]:
        """Upsert congress member by name."""
        
        async def _perform_upsert():
            # Try to find existing member by name
            existing_member = await self.member_repo.find_by_name(member_name)
            
            if existing_member:
                logger.debug("Found existing congress member", member_id=existing_member.id, name=member_name)
                return existing_member
            
            # Create new member
            new_member = CongressMember(
                full_name=member_name,
                chamber='House',  # PTR filings are House-specific
                state=None,  # Will be updated when we have more data
                party=None,  # Will be updated when we have more data
                bioguide_id=None,
                thomas_id=None,
                govtrack_id=None
            )
            
            created_member = await self.member_repo.create(new_member)
            
            if created_member:
                logger.info("Created new congress member", member_id=created_member.id, name=member_name)
                metrics.increment("data_upsert.members_created")
            
            return created_member
        
        try:
            return await retry_with_backoff(
                _perform_upsert,
                max_attempts=self.settings.max_retries,
                base_delay=1.0,
                max_delay=10.0
            )
        except Exception as e:
            logger.error("Failed to upsert congress member", name=member_name, error=str(e))
            return None
    
    async def _upsert_trades_batch(
        self, 
        trades: List[Trade], 
        filing_id: str
    ) -> Dict[str, int]:
        """Upsert trades in batches with deduplication."""
        
        results = {
            'inserted': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0
        }
        
        if not trades:
            return results
        
        # Process trades in batches
        batch_size = 50  # Reasonable batch size for database operations
        
        for i in range(0, len(trades), batch_size):
            batch = trades[i:i + batch_size]
            
            try:
                batch_results = await self._process_trade_batch(batch, filing_id)
                
                # Aggregate results
                for key in results:
                    results[key] += batch_results.get(key, 0)
                
                logger.debug(
                    "Trade batch processed",
                    filing_id=filing_id,
                    batch_start=i,
                    batch_size=len(batch),
                    **batch_results
                )
                
            except Exception as e:
                logger.error(
                    "Trade batch processing failed",
                    filing_id=filing_id,
                    batch_start=i,
                    batch_size=len(batch),
                    error=str(e)
                )
                results['errors'] += len(batch)
        
        return results
    
    async def _process_trade_batch(self, trades: List[Trade], filing_id: str) -> Dict[str, int]:
        """Process a single batch of trades."""
        results = {
            'inserted': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0
        }
        
        # Check for existing trades by row_hash
        existing_hashes = await self._get_existing_trade_hashes([t._row_hash for t in trades if t._row_hash])
        
        for trade in trades:
            try:
                if not trade._row_hash:
                    # Generate row hash if missing
                    trade._row_hash = trade.generate_row_hash('house_clerk', filing_id)
                
                if trade._row_hash in existing_hashes:
                    # Trade already exists, check if update needed
                    existing_trade = await self.trade_repo.find_by_hash(trade._row_hash)
                    
                    if existing_trade and self._trade_needs_update(existing_trade, trade):
                        updated_trade = await self.trade_repo.update(existing_trade.id, trade)
                        if updated_trade:
                            results['updated'] += 1
                        else:
                            results['errors'] += 1
                    else:
                        results['skipped'] += 1
                else:
                    # New trade, insert it
                    created_trade = await self.trade_repo.create(trade)
                    if created_trade:
                        results['inserted'] += 1
                        existing_hashes.add(trade._row_hash)  # Add to set for this batch
                    else:
                        results['errors'] += 1
                        
            except Exception as e:
                logger.warning(
                    "Individual trade processing failed",
                    filing_id=filing_id,
                    trade_hash=getattr(trade, '_row_hash', 'unknown')[:12],
                    error=str(e)
                )
                results['errors'] += 1
        
        return results
    
    async def _get_existing_trade_hashes(self, row_hashes: List[str]) -> set:
        """Get set of existing row hashes from database."""
        if not row_hashes:
            return set()
        
        try:
            existing_trades = await self.trade_repo.find_by_hashes(row_hashes)
            return {trade.row_hash for trade in existing_trades if trade.row_hash}
        except Exception as e:
            logger.warning("Failed to get existing trade hashes", error=str(e))
            return set()
    
    def _trade_needs_update(self, existing_trade: Trade, new_trade: Trade) -> bool:
        """Check if an existing trade needs to be updated."""
        # Compare key fields that might change
        fields_to_compare = [
            'asset_description', 'ticker', 'asset_type', 'transaction_type',
            'amount_range', 'amount_min', 'amount_max', 'transaction_date'
        ]
        
        for field in fields_to_compare:
            existing_value = getattr(existing_trade, field, None)
            new_value = getattr(new_trade, field, None)
            
            if existing_value != new_value:
                return True
        
        return False
    
    async def upsert_trades_only(
        self, 
        trades: List[Trade], 
        filing_id: str
    ) -> Dict[str, Any]:
        """
        Upsert only trades (assumes congress members already exist).
        
        Args:
            trades: List of Trade objects with member_id already set
            filing_id: Filing identifier for logging
            
        Returns:
            Dictionary with upsert results
        """
        logger.info(
            "Starting trades-only upsert",
            filing_id=filing_id,
            trades_count=len(trades)
        )
        
        with performance_timer("data_upsert.trades_only", {"filing_id": filing_id}):
            try:
                trade_results = await self._upsert_trades_batch(trades, filing_id)
                
                results = {
                    'filing_id': filing_id,
                    'trades_processed': len(trades),
                    **trade_results,
                    'processing_time': datetime.utcnow().isoformat()
                }
                
                logger.info(
                    "Trades-only upsert completed",
                    filing_id=filing_id,
                    **{k: v for k, v in trade_results.items()}
                )
                
                return results
                
            except Exception as e:
                logger.error(
                    "Trades-only upsert failed",
                    filing_id=filing_id,
                    error=str(e)
                )
                raise
    
    async def get_upsert_statistics(self, filing_ids: List[str]) -> Dict[str, Any]:
        """Get statistics for recent upsert operations."""
        try:
            stats = {
                'total_filings': len(filing_ids),
                'total_trades': 0,
                'unique_members': 0,
                'date_range': None
            }
            
            if not filing_ids:
                return stats
            
            # Get trade counts by filing
            for filing_id in filing_ids:
                # This would require additional repository methods
                # For now, return basic stats
                pass
            
            return stats
            
        except Exception as e:
            logger.error("Failed to get upsert statistics", error=str(e))
            return {'error': str(e)}
    
    async def cleanup_duplicate_trades(self, dry_run: bool = True) -> Dict[str, Any]:
        """
        Clean up duplicate trades based on row_hash.
        
        Args:
            dry_run: If True, only report what would be deleted
            
        Returns:
            Dictionary with cleanup results
        """
        logger.info("Starting duplicate trade cleanup", dry_run=dry_run)
        
        try:
            # Find duplicate trades
            duplicates = await self.trade_repo.find_duplicates()
            
            if not duplicates:
                logger.info("No duplicate trades found")
                return {'duplicates_found': 0, 'duplicates_removed': 0}
            
            logger.info("Found duplicate trades", count=len(duplicates))
            
            if dry_run:
                return {
                    'duplicates_found': len(duplicates),
                    'duplicates_removed': 0,
                    'dry_run': True,
                    'duplicate_hashes': [d.get('row_hash', '')[:12] for d in duplicates[:10]]  # Sample
                }
            
            # Remove duplicates (keep the first occurrence)
            removed_count = 0
            for duplicate_group in duplicates:
                try:
                    # Remove all but the first trade in each duplicate group
                    trade_ids = duplicate_group.get('trade_ids', [])
                    if len(trade_ids) > 1:
                        for trade_id in trade_ids[1:]:  # Keep first, remove rest
                            success = await self.trade_repo.delete(trade_id)
                            if success:
                                removed_count += 1
                except Exception as e:
                    logger.warning("Failed to remove duplicate trade", error=str(e))
                    continue
            
            logger.info("Duplicate cleanup completed", removed=removed_count)
            
            return {
                'duplicates_found': len(duplicates),
                'duplicates_removed': removed_count,
                'dry_run': False
            }
            
        except Exception as e:
            logger.error("Duplicate cleanup failed", error=str(e))
            return {'error': str(e)}
    
    async def validate_data_integrity(self) -> Dict[str, Any]:
        """Validate data integrity across congress members and trades."""
        try:
            validation_results = {
                'total_members': 0,
                'total_trades': 0,
                'orphaned_trades': 0,
                'missing_required_fields': 0,
                'invalid_dates': 0,
                'duplicate_hashes': 0
            }
            
            # Get basic counts
            validation_results['total_members'] = await self.member_repo.count()
            validation_results['total_trades'] = await self.trade_repo.count()
            
            # Check for orphaned trades (trades without valid member_id)
            orphaned_trades = await self.trade_repo.find_orphaned()
            validation_results['orphaned_trades'] = len(orphaned_trades)
            
            # Check for missing required fields
            invalid_trades = await self.trade_repo.find_invalid()
            validation_results['missing_required_fields'] = len(invalid_trades)
            
            # Check for duplicate row hashes
            duplicates = await self.trade_repo.find_duplicates()
            validation_results['duplicate_hashes'] = len(duplicates)
            
            logger.info("Data integrity validation completed", **validation_results)
            
            return validation_results
            
        except Exception as e:
            logger.error("Data integrity validation failed", error=str(e))
            return {'error': str(e)}
    
    async def bulk_update_member_info(
        self, 
        member_updates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Bulk update congress member information.
        
        Args:
            member_updates: List of dicts with member_id and fields to update
            
        Returns:
            Dictionary with update results
        """
        logger.info("Starting bulk member info update", count=len(member_updates))
        
        results = {
            'processed': 0,
            'updated': 0,
            'errors': 0,
            'not_found': 0
        }
        
        for update_data in member_updates:
            try:
                member_id = update_data.get('member_id')
                if not member_id:
                    results['errors'] += 1
                    continue
                
                # Get existing member
                existing_member = await self.member_repo.find_by_id(member_id)
                if not existing_member:
                    results['not_found'] += 1
                    continue
                
                # Update fields
                updated_fields = {k: v for k, v in update_data.items() if k != 'member_id'}
                
                if updated_fields:
                    success = await self.member_repo.update(member_id, updated_fields)
                    if success:
                        results['updated'] += 1
                    else:
                        results['errors'] += 1
                
                results['processed'] += 1
                
            except Exception as e:
                logger.warning("Member update failed", update_data=update_data, error=str(e))
                results['errors'] += 1
        
        logger.info("Bulk member info update completed", **results)
        return results
