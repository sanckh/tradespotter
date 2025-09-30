"""Data upserter for idempotent upsert of politicians, disclosures, and trades - Matches 007_create_fresh_schema.sql."""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date
import structlog
from supabase import create_client, Client

from ..config.settings import Settings
from ..database.models import Politician, Disclosure, Trade
from ..database.connection import DatabaseConnection, PoliticianRepository, DisclosureRepository, TradeRepository
from ..utils.retry_utils import retry_with_backoff, RetryableError
from ..utils.logging_config import performance_timer, metrics

logger = structlog.get_logger()


class DataUpserter:
    """Handles idempotent upsert of politicians, disclosures, and trades with deduplication."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.db_connection: Optional[DatabaseConnection] = None
        self.politician_repo: Optional[PoliticianRepository] = None
        self.disclosure_repo: Optional[DisclosureRepository] = None
        self.trade_repo: Optional[TradeRepository] = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.db_connection = DatabaseConnection()
        self.db_connection.connect()  # Not async
        
        self.politician_repo = PoliticianRepository(self.db_connection)
        self.disclosure_repo = DisclosureRepository(self.db_connection)
        self.trade_repo = TradeRepository(self.db_connection)
        
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.db_connection:
            self.db_connection.close()  # Not async
    
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

    async def upsert_bulk_filing_data(
        self,
        filing_id: str,
        filings: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Upsert bulk PTR filing metadata to database.
        
        Args:
            filing_id: Bulk filing identifier
            filings: List of normalized filing dictionaries
            
        Returns:
            Dictionary with upsert results and statistics
        """
        logger.info(
            "Starting bulk filing data upsert",
            filing_id=filing_id,
            filings_count=len(filings)
        )
        
        with performance_timer("data_upsert.bulk_filings", {"filing_id": filing_id}):
            try:
                results = {
                    'filing_id': filing_id,
                    'filings_processed': 0,
                    'filings_upserted': 0,
                    'members_created': 0,
                    'errors': 0,
                    'processing_time': datetime.utcnow().isoformat()
                }
                
                # Process filings in batches
                batch_size = 100
                for i in range(0, len(filings), batch_size):
                    batch = filings[i:i + batch_size]
                    
                    batch_results = await self._process_filing_batch(batch, filing_id)
                    
                    # Aggregate results
                    results['filings_processed'] += batch_results['processed']
                    results['filings_upserted'] += batch_results['upserted']
                    results['members_created'] += batch_results['members_created']
                    results['errors'] += batch_results['errors']
                
                logger.info(
                    "Bulk filing data upsert completed",
                    filing_id=filing_id,
                    **{k: v for k, v in results.items() if k not in ['filing_id', 'processing_time']}
                )
                
                metrics.increment("data_upsert.bulk_filings_processed")
                metrics.gauge("data_upsert.filings_per_bulk", len(filings))
                
                return results
                
            except Exception as e:
                logger.error(
                    "Bulk filing data upsert failed",
                    filing_id=filing_id,
                    error=str(e)
                )
                metrics.increment("data_upsert.bulk_filing_errors")
                raise

    async def _process_filing_batch(
        self, 
        filings: List[Dict[str, Any]], 
        filing_id: str
    ) -> Dict[str, int]:
        """Process a batch of filing records."""
        results = {
            'processed': 0,
            'upserted': 0,
            'members_created': 0,
            'errors': 0
        }
        
        for filing_data in filings:
            try:
                # Extract member information
                member_name = filing_data.get('member_name')
                state = filing_data.get('state')
                district = filing_data.get('district')
                
                if not member_name:
                    logger.warning("Missing member name", filing_data=filing_data)
                    results['errors'] += 1
                    continue
                
                # Step 1: Upsert politician (basic info only, no doc_id/filing_date)
                politician = await self._upsert_politician(member_name, state, district, filing_data)
                if not politician:
                    logger.warning("Failed to upsert politician", member_name=member_name)
                    results['errors'] += 1
                    continue
                
                # Step 2: Create disclosure record for this filing
                disclosure = await self._upsert_disclosure(politician['id'], filing_data)
                if disclosure:
                    logger.debug("Created disclosure record", disclosure_id=disclosure['id'])
                    results['members_created'] += 1
                
                results['processed'] += 1
                results['upserted'] += 1
                
                logger.debug(
                    "Filing processed successfully",
                    doc_id=filing_data.get('doc_id'),
                    member_name=member_name,
                    politician_id=politician['id'],
                    disclosure_id=disclosure['id'] if disclosure else None
                )
                
            except Exception as e:
                logger.warning(
                    "Filing processing failed",
                    filing_data=filing_data,
                    error=str(e)
                )
                results['errors'] += 1
        
        return results
    
    async def _upsert_politician(
        self,
        member_name: str,
        state: Optional[str],
        district: Optional[str],
        filing_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Upsert politician record (basic info only, no disclosure data)."""
        try:
            # Build politician data - only include fields that exist in current schema
            politician_data = {
                'full_name': member_name,
                'chamber': 'house',
            }
            
            # Add optional fields that exist in current table
            if state:
                politician_data['state'] = state
            if district:
                politician_data['district'] = district
            
            # Note: first_name, last_name, party, bioguide_id, external_ids
            # are stored in the model but not inserted until migration 010 is applied
            
            # Upsert politician
            politician = await self.politician_repo.upsert(politician_data)
            return politician
            
        except Exception as e:
            logger.error("Failed to upsert politician", member_name=member_name, error=str(e))
            return None
    
    async def _upsert_disclosure(
        self,
        politician_id: str,
        filing_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Create a disclosure record for PTR filing."""
        try:
            doc_id = filing_data.get('doc_id')
            filing_date = filing_data.get('filing_date')
            filing_type = filing_data.get('filing_type')
            
            if not doc_id:
                logger.warning("Missing doc_id for disclosure", filing_data=filing_data)
                return None
            
            # Build disclosure data
            disclosure_data = {
                'politician_id': politician_id,
                'source': 'house_clerk',
                'doc_id': doc_id,
            }
            
            # Add filing_type if present
            if filing_type:
                disclosure_data['filing_type'] = filing_type
            
            if filing_date:
                # Convert date to datetime if needed, then to ISO string
                if isinstance(filing_date, date) and not isinstance(filing_date, datetime):
                    filing_date = datetime.combine(filing_date, datetime.min.time())
                # Convert datetime to ISO format string for Supabase
                disclosure_data['filed_date'] = filing_date.isoformat() if isinstance(filing_date, datetime) else filing_date
            
            # Store raw filing data (including filing_type_description)
            disclosure_data['raw'] = {
                'filing_type_description': filing_data.get('filing_type_description'),
                'state_district': filing_data.get('state_district'),
                'filing_year': filing_data.get('filing_year'),
                'source_year': filing_data.get('source_year'),
                'bulk_filing_id': filing_data.get('bulk_filing_id'),
                'row_number': filing_data.get('row_number')
            }
            
            # Upsert disclosure (will skip if already exists)
            disclosure = await self.disclosure_repo.upsert(disclosure_data)
            return disclosure
            
        except Exception as e:
            logger.error("Failed to create disclosure", politician_id=politician_id, error=str(e))
            return None
    
    async def _upsert_congress_member(self, member_name: str) -> Optional[Politician]:
        """Upsert congress member by name."""
        
        async def _perform_upsert():
            # Try to find existing politician by name
            existing_politician_dict = await self.politician_repo.find_by_name(member_name)
            
            if existing_politician_dict:
                # Convert dict to Politician object
                existing_politician = Politician(
                    id=existing_politician_dict.get('id'),
                    full_name=existing_politician_dict.get('full_name'),
                    first_name=existing_politician_dict.get('first_name'),
                    last_name=existing_politician_dict.get('last_name'),
                    chamber=existing_politician_dict.get('chamber'),
                    state=existing_politician_dict.get('state'),
                    district=existing_politician_dict.get('district'),
                    party=existing_politician_dict.get('party'),
                    bioguide_id=existing_politician_dict.get('bioguide_id'),
                    external_ids=existing_politician_dict.get('external_ids'),
                    created_at=existing_politician_dict.get('created_at'),
                    updated_at=existing_politician_dict.get('updated_at')
                )
                logger.debug("Found existing politician", politician_id=existing_politician.id, name=member_name)
                return existing_politician
            
            # Create new politician
            new_politician = Politician(
                full_name=member_name,
                chamber='house',  # PTR filings are House-specific
            )
            
            created_politician_dict = await self.politician_repo.create(new_politician.to_dict())
            
            if created_politician_dict:
                # Convert dict back to Politician object
                created_politician = Politician(
                    id=created_politician_dict.get('id'),
                    full_name=created_politician_dict.get('full_name'),
                    first_name=created_politician_dict.get('first_name'),
                    last_name=created_politician_dict.get('last_name'),
                    chamber=created_politician_dict.get('chamber'),
                    state=created_politician_dict.get('state'),
                    district=created_politician_dict.get('district'),
                    party=created_politician_dict.get('party'),
                    bioguide_id=created_politician_dict.get('bioguide_id'),
                    external_ids=created_politician_dict.get('external_ids'),
                    created_at=created_politician_dict.get('created_at'),
                    updated_at=created_politician_dict.get('updated_at')
                )
                logger.info("Created new politician", politician_id=created_politician.id, name=member_name)
                metrics.increment("data_upsert.members_created")
                return created_politician
            
            return None
        
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
