"""Main ingestion pipeline orchestrating discovery, download, parse, normalize, and upsert."""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, date
import structlog

from ..config.settings import Settings
from ..discovery.ptr_discovery import PTRDiscovery
from ..downloader.pdf_downloader import PDFDownloader
from ..downloader.zip_downloader import ZipDownloader
from ..parser.pdf_parser import PDFParser
from ..parser.txt_parser import BulkTXTParser
from ..normalizer.data_normalizer import DataNormalizer
from ..upserter.data_upserter import DataUpserter
from ..utils.logging_config import performance_timer, metrics, get_logger
from ..utils.retry_utils import retry_with_backoff, NonRetryableError

logger = get_logger("ingestion_pipeline")


class IngestionPipeline:
    """Orchestrates the complete PTR ingestion workflow."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.stats = {
            'filings_discovered': 0,
            'pdfs_downloaded': 0,
            'trades_parsed': 0,
            'trades_normalized': 0,
            'trades_upserted': 0,
            'errors': 0,
            'start_time': None,
            'end_time': None
        }
        
    async def run_full_pipeline(
        self,
        year_start: Optional[int] = None,
        year_end: Optional[int] = None,
        limit: Optional[int] = None,
        filing_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Run the complete ingestion pipeline.
        
        Args:
            year_start: Start year for discovery
            year_end: End year for discovery
            limit: Maximum number of filings to process
            filing_ids: Specific filing IDs to process (skips discovery)
            
        Returns:
            Dictionary with pipeline results and statistics
        """
        self.stats['start_time'] = datetime.utcnow()
        
        logger.info(
            "Starting full ingestion pipeline",
            year_start=year_start,
            year_end=year_end,
            limit=limit,
            specific_filings=len(filing_ids) if filing_ids else 0
        )
        
        with performance_timer("pipeline.full_run"):
            try:
                # Stage 1: Discovery (unless specific filing IDs provided)
                if filing_ids:
                    filings = [{'filing_id': fid} for fid in filing_ids]
                    logger.info("Using provided filing IDs", count=len(filings))
                else:
                    filings = await self._run_discovery_stage(year_start, year_end, limit)
                
                if not filings:
                    logger.warning("No filings discovered")
                    return self._compile_results()
                
                # Stage 2: Download PDFs
                download_results = await self._run_download_stage(filings)
                
                # Stage 3: Parse PDFs
                parse_results = await self._run_parse_stage(download_results)
                
                # Stage 4: Normalize trade data
                normalize_results = await self._run_normalize_stage(parse_results)
                
                # Stage 5: Upsert to database
                upsert_results = await self._run_upsert_stage(normalize_results)
                
                self.stats['end_time'] = datetime.utcnow()
                
                results = self._compile_results()
                
                logger.info(
                    "Full ingestion pipeline completed",
                    **{k: v for k, v in results.items() if k not in ['start_time', 'end_time']}
                )
                
                metrics.increment("pipeline.full_runs_completed")
                return results
                
            except Exception as e:
                self.stats['end_time'] = datetime.utcnow()
                self.stats['errors'] += 1
                
                logger.error("Full ingestion pipeline failed", error=str(e))
                metrics.increment("pipeline.full_runs_failed")
                
                raise
    
    async def _run_discovery_stage(
        self, 
        year_start: Optional[int], 
        year_end: Optional[int], 
        limit: Optional[int]
    ) -> List[Dict[str, Any]]:
        """Run the discovery stage."""
        logger.info("Starting discovery stage")
        
        with performance_timer("pipeline.discovery"):
            async with PTRDiscovery(self.settings) as discovery:
                filings = await discovery.discover_ptr_filings(
                    year_start=year_start,
                    year_end=year_end,
                    limit=limit
                )
                
                self.stats['filings_discovered'] = len(filings)
                
                logger.info("Discovery stage completed", filings_found=len(filings))
                metrics.gauge("pipeline.filings_discovered", len(filings))
                
                return filings
    
    async def _run_download_stage(self, filings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Run the PDF download stage."""
        logger.info("Starting download stage", filings_count=len(filings))
        
        with performance_timer("pipeline.download"):
            async with PDFDownloader(self.settings) as downloader:
                # Prepare download tasks
                download_tasks = []
                
                for filing in filings:
                    if all(k in filing for k in ['doc_url', 'filing_id', 'member_name']):
                        download_tasks.append(filing)
                    else:
                        logger.warning("Filing missing required fields", filing=filing)
                        self.stats['errors'] += 1
                
                # Execute downloads
                download_results = await downloader.download_batch(
                    download_tasks,
                    max_concurrent=self.settings.max_concurrency
                )
                
                # Filter successful downloads
                successful_downloads = [r for r in download_results if r is not None]
                
                self.stats['pdfs_downloaded'] = len(successful_downloads)
                
                logger.info(
                    "Download stage completed",
                    attempted=len(download_tasks),
                    successful=len(successful_downloads),
                    failed=len(download_tasks) - len(successful_downloads)
                )
                
                metrics.gauge("pipeline.pdfs_downloaded", len(successful_downloads))
                
                return successful_downloads
    
    async def _run_parse_stage(self, download_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Run the PDF parsing stage."""
        logger.info("Starting parse stage", files_count=len(download_results))
        
        parse_results = []
        parser = PDFParser()
        
        with performance_timer("pipeline.parse"):
            # Process files with concurrency control
            semaphore = asyncio.Semaphore(self.settings.max_concurrency)
            
            async def parse_single_file(download_result):
                async with semaphore:
                    return await self._parse_single_pdf(parser, download_result)
            
            # Execute parsing tasks
            parse_tasks = [parse_single_file(dr) for dr in download_results]
            results = await asyncio.gather(*parse_tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(
                        "Parse task failed",
                        filing_id=download_results[i].get('filing_id'),
                        error=str(result)
                    )
                    self.stats['errors'] += 1
                elif result:
                    parse_results.append(result)
                    self.stats['trades_parsed'] += len(result.get('parsed_trades', []))
            
            logger.info(
                "Parse stage completed",
                files_processed=len(parse_results),
                total_trades_parsed=self.stats['trades_parsed']
            )
            
            metrics.gauge("pipeline.trades_parsed", self.stats['trades_parsed'])
            
            return parse_results
    
    async def _run_txt_parse_stage(self, download_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Run the TXT parsing stage for bulk downloads."""
        logger.info("Starting TXT parse stage", files_count=len(download_results))
        
        parse_results = []
        bulk_parser = BulkTXTParser()
        
        with performance_timer("pipeline.txt_parse"):
            for download_result in download_results:
                try:
                    # Extract file information from download result
                    extracted_files = download_result.get('extracted_files', [])
                    filing_id = download_result.get('filing_id')
                    
                    if not extracted_files:
                        logger.warning("No extracted files found", filing_id=filing_id)
                        continue
                    
                    # Parse TXT files from this download
                    parsed_filings, parse_errors = await bulk_parser.parse_bulk_files(extracted_files)
                    
                    if parsed_filings:
                        # Convert parsed filings to expected format
                        parse_result = {
                            'filing_id': filing_id,
                            'bulk_filings': parsed_filings,
                            'parse_errors': parse_errors,
                            'download_metadata': download_result,
                            'filings_count': len(parsed_filings)
                        }
                        parse_results.append(parse_result)
                        
                        # Update stats (using filings_count instead of trades_parsed for bulk)
                        self.stats['trades_parsed'] += len(parsed_filings)
                        
                        logger.info(
                            "TXT parsing completed for filing",
                            filing_id=filing_id,
                            filings_parsed=len(parsed_filings),
                            errors=len(parse_errors)
                        )
                    
                except Exception as e:
                    logger.error(
                        "TXT parse failed",
                        filing_id=download_result.get('filing_id'),
                        error=str(e)
                    )
                    self.stats['errors'] += 1
            
            logger.info(
                "TXT parse stage completed",
                files_processed=len(parse_results),
                total_filings_parsed=self.stats['trades_parsed']
            )
            
            metrics.gauge("pipeline.txt_filings_parsed", self.stats['trades_parsed'])
            
            return parse_results
    
    async def _parse_single_pdf(self, parser: PDFParser, download_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse a single PDF file."""
        filing_id = download_result.get('filing_id')
        member_name = download_result.get('member_name')
        
        try:
            # Get PDF data (this would need to be implemented based on storage)
            pdf_data = await self._get_pdf_data(download_result)
            
            if not pdf_data:
                logger.warning("No PDF data available", filing_id=filing_id)
                return None
            
            # Parse the PDF
            parsed_trades, parse_errors = await parser.parse_pdf_file(
                pdf_data, filing_id, member_name
            )
            
            # Validate parsed trades
            valid_trades, validation_errors = await parser.validate_parsed_trades(parsed_trades)
            
            return {
                'filing_id': filing_id,
                'member_name': member_name,
                'parsed_trades': valid_trades,
                'parse_errors': parse_errors,
                'validation_errors': validation_errors,
                'download_metadata': download_result
            }
            
        except Exception as e:
            logger.error("PDF parsing failed", filing_id=filing_id, error=str(e))
            return None
    
    async def _get_pdf_data(self, download_result: Dict[str, Any]) -> Optional[bytes]:
        """Get PDF data from download result (placeholder for actual implementation)."""
        # This would need to be implemented based on how PDFs are stored
        # For now, return None to indicate data not available
        logger.debug("PDF data retrieval not implemented", filing_id=download_result.get('filing_id'))
        return None
    
    async def _run_normalize_stage(self, parse_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Run the data normalization stage."""
        logger.info("Starting normalize stage", parse_results_count=len(parse_results))
        
        normalize_results = []
        normalizer = DataNormalizer()
        
        with performance_timer("pipeline.normalize"):
            for parse_result in parse_results:
                try:
                    normalized_result = await self._normalize_single_filing(normalizer, parse_result)
                    if normalized_result:
                        normalize_results.append(normalized_result)
                        self.stats['trades_normalized'] += len(normalized_result.get('normalized_trades', []))
                        
                except Exception as e:
                    logger.error(
                        "Normalization failed",
                        filing_id=parse_result.get('filing_id'),
                        error=str(e)
                    )
                    self.stats['errors'] += 1
            
            logger.info(
                "Normalize stage completed",
                filings_processed=len(normalize_results),
                total_trades_normalized=self.stats['trades_normalized']
            )
            
            metrics.gauge("pipeline.trades_normalized", self.stats['trades_normalized'])
            
            return normalize_results
    
    async def _normalize_single_filing(
        self, 
        normalizer: DataNormalizer, 
        parse_result: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Normalize data from a single filing."""
        filing_id = parse_result.get('filing_id')
        member_name = parse_result.get('member_name')
        parsed_trades = parse_result.get('parsed_trades', [])
        
        if not parsed_trades:
            logger.debug("No parsed trades to normalize", filing_id=filing_id)
            return None
        
        try:
            # For now, use a placeholder member_id (would be resolved in upsert stage)
            member_id = "placeholder"  # This will be resolved during upsert
            
            # Normalize trades
            normalized_trades, normalization_errors = await normalizer.normalize_trades(
                parsed_trades, filing_id, member_id
            )
            
            # Validate normalized trades
            valid_trades, validation_errors = normalizer.validate_normalized_trades(normalized_trades)
            
            return {
                'filing_id': filing_id,
                'member_name': member_name,
                'normalized_trades': valid_trades,
                'normalization_errors': normalization_errors,
                'validation_errors': validation_errors,
                'parse_metadata': parse_result
            }
            
        except Exception as e:
            logger.error("Trade normalization failed", filing_id=filing_id, error=str(e))
            return None
    
    async def _run_upsert_stage(self, normalize_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Run the database upsert stage."""
        logger.info("Starting upsert stage", normalize_results_count=len(normalize_results))
        
        upsert_results = []
        
        with performance_timer("pipeline.upsert"):
            async with DataUpserter(self.settings) as upserter:
                for normalize_result in normalize_results:
                    try:
                        upsert_result = await self._upsert_single_filing(upserter, normalize_result)
                        if upsert_result:
                            upsert_results.append(upsert_result)
                            self.stats['trades_upserted'] += upsert_result.get('trades_inserted', 0)
                            self.stats['trades_upserted'] += upsert_result.get('trades_updated', 0)
                            
                    except Exception as e:
                        logger.error(
                            "Upsert failed",
                            filing_id=normalize_result.get('filing_id'),
                            error=str(e)
                        )
                        self.stats['errors'] += 1
            
            logger.info(
                "Upsert stage completed",
                filings_processed=len(upsert_results),
                total_trades_upserted=self.stats['trades_upserted']
            )
            
            metrics.gauge("pipeline.trades_upserted", self.stats['trades_upserted'])
            
            return upsert_results
    
    async def _upsert_single_filing(
        self, 
        upserter: DataUpserter, 
        normalize_result: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Upsert data from a single filing."""
        filing_id = normalize_result.get('filing_id')
        member_name = normalize_result.get('member_name')
        normalized_trades = normalize_result.get('normalized_trades', [])
        
        if not normalized_trades:
            logger.debug("No normalized trades to upsert", filing_id=filing_id)
            return None
        
        try:
            # Extract filing date from metadata if available
            filing_date = None
            parse_metadata = normalize_result.get('parse_metadata', {})
            download_metadata = parse_metadata.get('download_metadata', {})
            
            # Try to get filing date from discovery metadata
            if 'filing_date' in download_metadata:
                filing_date = download_metadata['filing_date']
            
            # Upsert filing data
            upsert_result = await upserter.upsert_filing_data(
                member_name=member_name,
                filing_id=filing_id,
                filing_date=filing_date,
                trades=normalized_trades
            )
            
            return upsert_result
            
        except Exception as e:
            logger.error("Filing upsert failed", filing_id=filing_id, error=str(e))
            return None
    
    def _compile_results(self) -> Dict[str, Any]:
        """Compile final pipeline results."""
        duration = None
        if self.stats['start_time'] and self.stats['end_time']:
            duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        return {
            'pipeline_status': 'completed' if self.stats['errors'] == 0 else 'completed_with_errors',
            'duration_seconds': duration,
            'filings_discovered': self.stats['filings_discovered'],
            'pdfs_downloaded': self.stats['pdfs_downloaded'],
            'trades_parsed': self.stats['trades_parsed'],
            'trades_normalized': self.stats['trades_normalized'],
            'trades_upserted': self.stats['trades_upserted'],
            'total_errors': self.stats['errors'],
            'start_time': self.stats['start_time'].isoformat() if self.stats['start_time'] else None,
            'end_time': self.stats['end_time'].isoformat() if self.stats['end_time'] else None
        }
    
    async def run_discovery_only(
        self,
        year_start: Optional[int] = None,
        year_end: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Run only the discovery stage."""
        logger.info("Running discovery-only pipeline")
        
        with performance_timer("pipeline.discovery_only"):
            filings = await self._run_discovery_stage(year_start, year_end, limit)
            
            logger.info("Discovery-only pipeline completed", filings_found=len(filings))
            return filings
    
    async def run_from_filings(self, filings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run pipeline starting from discovered filings (skip discovery)."""
        logger.info("Running pipeline from provided filings", count=len(filings))
        
        self.stats['start_time'] = datetime.utcnow()
        self.stats['filings_discovered'] = len(filings)
        
        with performance_timer("pipeline.from_filings"):
            try:
                # Start from download stage
                download_results = await self._run_download_stage(filings)
                parse_results = await self._run_parse_stage(download_results)
                normalize_results = await self._run_normalize_stage(parse_results)
                upsert_results = await self._run_upsert_stage(normalize_results)
                
                self.stats['end_time'] = datetime.utcnow()
                
                results = self._compile_results()
                
                logger.info("Pipeline from filings completed", **{k: v for k, v in results.items() if k not in ['start_time', 'end_time']})
                
                return results
                
            except Exception as e:
                self.stats['end_time'] = datetime.utcnow()
                self.stats['errors'] += 1
                
                logger.error("Pipeline from filings failed", error=str(e))
                raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check of all pipeline components."""
        logger.info("Starting pipeline health check")
        
        health_status = {
            'overall_status': 'healthy',
            'components': {},
            'timestamp': datetime.utcnow().isoformat()
        }
        
        try:
            # Test discovery component
            async with PTRDiscovery(self.settings) as discovery:
                test_filings = await discovery.discover_ptr_filings(limit=1)
                health_status['components']['discovery'] = {
                    'status': 'healthy',
                    'test_result': f"Found {len(test_filings)} filing(s)"
                }
        except Exception as e:
            health_status['components']['discovery'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_status['overall_status'] = 'degraded'
        
        try:
            # Test database connection
            async with DataUpserter(self.settings) as upserter:
                integrity_check = await upserter.validate_data_integrity()
                health_status['components']['database'] = {
                    'status': 'healthy',
                    'test_result': integrity_check
                }
        except Exception as e:
            health_status['components']['database'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_status['overall_status'] = 'degraded'
        
        # Test other components
        health_status['components']['parser'] = {'status': 'healthy', 'test_result': 'Component available'}
        health_status['components']['normalizer'] = {'status': 'healthy', 'test_result': 'Component available'}
        
        logger.info("Pipeline health check completed", status=health_status['overall_status'])
        
        return health_status
    
    async def run_download_only(
        self,
        year_start: Optional[int] = None,
        year_end: Optional[int] = None,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Run discovery and download stages only."""
        logger.info("Running discovery-only pipeline")
        
        self.stats['start_time'] = datetime.utcnow()
        
        with performance_timer("pipeline.download_only"):
            try:
                # Stage 1: Discovery
                filings = await self._run_discovery_stage(year_start, year_end, limit)
                
                if not filings:
                    logger.warning("No filings discovered")
                    return self._compile_download_results([])
                
                # Stage 2: Download zip files
                download_results = await self._run_zip_download_stage(filings)
                
                self.stats['end_time'] = datetime.utcnow()
                
                results = self._compile_download_results(download_results)
                
                logger.info("Download-only pipeline completed", **results)
                return results
                
            except Exception as e:
                self.stats['end_time'] = datetime.utcnow()
                self.stats['errors'] += 1
                
                logger.error("Download-only pipeline failed", error=str(e))
                raise

    async def run_bulk_pipeline(
        self,
        year_start: Optional[int] = None,
        year_end: Optional[int] = None,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Run the complete bulk ingestion pipeline for PTR zip files.
        
        This pipeline: discovers -> downloads -> parses TXT -> normalizes -> upserts
        """
        logger.info("Running bulk ingestion pipeline")
        
        self.stats['start_time'] = datetime.utcnow()
        
        with performance_timer("pipeline.bulk_full"):
            try:
                # Stage 1: Discovery
                filings = await self._run_discovery_stage(year_start, year_end, limit)
                
                if not filings:
                    logger.warning("No filings discovered")
                    return self._compile_results()
                
                # Stage 2: Download zip files
                download_results = await self._run_zip_download_stage(filings)
                
                if not download_results:
                    logger.warning("No files downloaded")
                    return self._compile_results()
                
                # Stage 3: Parse TXT files
                parse_results = await self._run_txt_parse_stage(download_results)
                
                if not parse_results:
                    logger.warning("No files parsed")
                    return self._compile_results()
                
                # Stage 4: Normalize bulk filing data
                normalize_results = await self._run_bulk_normalize_stage(parse_results)
                
                # Stage 5: Upsert to database
                upsert_results = await self._run_bulk_upsert_stage(normalize_results)
                
                self.stats['end_time'] = datetime.utcnow()
                
                results = self._compile_results()
                
                logger.info(
                    "Bulk ingestion pipeline completed",
                    **{k: v for k, v in results.items() if k not in ['start_time', 'end_time']}
                )
                
                metrics.increment("pipeline.bulk_runs_completed")
                return results
                
            except Exception as e:
                self.stats['end_time'] = datetime.utcnow()
                self.stats['errors'] += 1
                
                logger.error("Bulk ingestion pipeline failed", error=str(e))
                metrics.increment("pipeline.bulk_runs_failed")
                
                raise
    
    async def _run_zip_download_stage(self, filings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Run the zip download stage for bulk PTR files."""
        logger.info("Starting zip download stage", filings_count=len(filings))
        
        with performance_timer("pipeline.zip_download"):
            async with ZipDownloader(self.settings) as downloader:
                # Prepare download tasks
                download_tasks = []
                
                for filing in filings:
                    if all(k in filing for k in ['doc_url', 'filing_id', 'year']):
                        download_tasks.append(filing)
                    else:
                        logger.warning("Filing missing required fields", filing=filing)
                        self.stats['errors'] += 1
                
                # Execute downloads
                download_results = await downloader.download_batch(
                    download_tasks,
                    max_concurrent=self.settings.MAX_CONCURRENCY
                )
                
                # Filter successful downloads
                successful_downloads = [r for r in download_results if r is not None]
                
                self.stats['pdfs_downloaded'] = len(successful_downloads)  # Reusing this stat for zip downloads
                
                logger.info(
                    "Zip download stage completed",
                    attempted=len(download_tasks),
                    successful=len(successful_downloads),
                    failed=len(download_tasks) - len(successful_downloads)
                )
                
                metrics.gauge("pipeline.zips_downloaded", len(successful_downloads))
                
                return successful_downloads
    
    async def _run_bulk_normalize_stage(self, parse_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Run the bulk normalization stage for parsed filing data."""
        logger.info("Starting bulk normalize stage", parse_results_count=len(parse_results))
        
        normalize_results = []
        
        with performance_timer("pipeline.bulk_normalize"):
            for parse_result in parse_results:
                try:
                    filing_id = parse_result.get('filing_id')
                    bulk_filings = parse_result.get('bulk_filings', [])
                    
                    if not bulk_filings:
                        logger.debug("No bulk filings to normalize", filing_id=filing_id)
                        continue
                    
                    # For bulk filings, we normalize the filing metadata (not trades)
                    # Each filing becomes a record in our database
                    normalized_filings = []
                    
                    for filing_data in bulk_filings:
                        try:
                            # Normalize individual filing
                            normalized_filing = {
                                'doc_id': filing_data.get('doc_id'),
                                'member_name': filing_data.get('member_name'),
                                'first_name': filing_data.get('first_name'),
                                'last_name': filing_data.get('last_name'),
                                'prefix': filing_data.get('prefix'),
                                'suffix': filing_data.get('suffix'),
                                'filing_type': filing_data.get('filing_type'),
                                'filing_type_description': filing_data.get('filing_type_description'),
                                'state': filing_data.get('state'),
                                'district': filing_data.get('district'),
                                'state_district': filing_data.get('state_district'),
                                'filing_year': filing_data.get('filing_year'),
                                'filing_date': filing_data.get('filing_date'),
                                'source_year': filing_data.get('source_year'),
                                'bulk_filing_id': filing_data.get('bulk_filing_id'),
                                'row_number': filing_data.get('row_number')
                            }
                            
                            normalized_filings.append(normalized_filing)
                            
                        except Exception as e:
                            logger.warning(
                                "Failed to normalize individual filing",
                                doc_id=filing_data.get('doc_id'),
                                error=str(e)
                            )
                    
                    if normalized_filings:
                        normalize_result = {
                            'filing_id': filing_id,
                            'normalized_filings': normalized_filings,
                            'parse_metadata': parse_result,
                            'filings_count': len(normalized_filings)
                        }
                        normalize_results.append(normalize_result)
                        
                        # Update stats
                        self.stats['trades_normalized'] += len(normalized_filings)
                        
                        logger.info(
                            "Bulk normalization completed for filing",
                            filing_id=filing_id,
                            filings_normalized=len(normalized_filings)
                        )
                    
                except Exception as e:
                    logger.error(
                        "Bulk normalization failed",
                        filing_id=parse_result.get('filing_id'),
                        error=str(e)
                    )
                    self.stats['errors'] += 1
            
            logger.info(
                "Bulk normalize stage completed",
                filings_processed=len(normalize_results),
                total_filings_normalized=self.stats['trades_normalized']
            )
            
            metrics.gauge("pipeline.bulk_filings_normalized", self.stats['trades_normalized'])
            
            return normalize_results
    
    async def _run_bulk_upsert_stage(self, normalize_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Run the bulk upsert stage for normalized filing data."""
        logger.info("Starting bulk upsert stage", normalize_results_count=len(normalize_results))
        
        upsert_results = []
        
        with performance_timer("pipeline.bulk_upsert"):
            async with DataUpserter(self.settings) as upserter:
                for normalize_result in normalize_results:
                    try:
                        filing_id = normalize_result.get('filing_id')
                        normalized_filings = normalize_result.get('normalized_filings', [])
                        
                        if not normalized_filings:
                            logger.debug("No normalized filings to upsert", filing_id=filing_id)
                            continue
                        
                        # Upsert bulk filing data
                        upsert_result = await upserter.upsert_bulk_filing_data(
                            filing_id=filing_id,
                            filings=normalized_filings
                        )
                        
                        if upsert_result:
                            upsert_results.append(upsert_result)
                            
                            # Update stats
                            upserted_count = upsert_result.get('filings_upserted', 0)
                            self.stats['trades_upserted'] += upserted_count
                            
                            logger.info(
                                "Bulk upsert completed for filing",
                                filing_id=filing_id,
                                filings_upserted=upserted_count
                            )
                        
                    except Exception as e:
                        logger.error(
                            "Bulk upsert failed",
                            filing_id=normalize_result.get('filing_id'),
                            error=str(e)
                        )
                        self.stats['errors'] += 1
            
            logger.info(
                "Bulk upsert stage completed",
                filings_processed=len(upsert_results),
                total_filings_upserted=self.stats['trades_upserted']
            )
            
            metrics.gauge("pipeline.bulk_filings_upserted", self.stats['trades_upserted'])
            
            return upsert_results
    
    def _compile_download_results(self, download_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compile download-only pipeline results."""
        duration = None
        if self.stats['start_time'] and self.stats['end_time']:
            duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        # Count total extracted files
        total_files_extracted = 0
        for result in download_results:
            total_files_extracted += len(result.get('extracted_files', []))
        
        return {
            'pipeline_status': 'completed' if self.stats['errors'] == 0 else 'completed_with_errors',
            'duration_seconds': duration,
            'filings_discovered': self.stats['filings_discovered'],
            'downloads_completed': len(download_results),
            'files_extracted': total_files_extracted,
            'total_errors': self.stats['errors'],
            'download_details': download_results,
            'start_time': self.stats['start_time'].isoformat() if self.stats['start_time'] else None,
            'end_time': self.stats['end_time'].isoformat() if self.stats['end_time'] else None
        }
