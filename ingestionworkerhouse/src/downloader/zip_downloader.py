"""Zip file downloader for PTR bulk downloads."""

import os
import hashlib
import asyncio
import zipfile
from typing import Optional, Dict, Any, List
from pathlib import Path
import aiohttp
import structlog
from datetime import datetime

from ..config.settings import Settings
from ..utils.retry_utils import retry_with_backoff, RetryableError, NonRetryableError
from ..utils.logging_config import performance_timer, metrics

logger = structlog.get_logger()


class ZipDownloader:
    """Downloads PTR zip files and extracts their contents."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.session: Optional[aiohttp.ClientSession] = None
        self.temp_dir = Path("temp_downloads")
        self.temp_dir.mkdir(exist_ok=True)
        
    async def __aenter__(self):
        """Async context manager entry."""
        # Setup HTTP session
        connector = aiohttp.TCPConnector(limit=self.settings.MAX_CONCURRENCY)
        timeout = aiohttp.ClientTimeout(total=600)  # 10 minutes for large zip files
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'User-Agent': self.settings.USER_AGENT,
                'Accept': 'application/zip,application/x-zip-compressed,*/*',
            }
        )
        
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
            
        # Clean up only zip files, keep extracted TXT/XML for parsing
        try:
            for temp_file in self.temp_dir.glob("*.zip"):
                temp_file.unlink(missing_ok=True)
            # Note: Keep TXT/XML files for parsing stage
            # They will be cleaned up later by the pipeline
        except Exception as e:
            logger.warning("Failed to clean temp files", error=str(e))
    
    async def download_and_extract_zip(
        self, 
        doc_url: str, 
        filing_id: str,
        year: int
    ) -> Optional[Dict[str, Any]]:
        """
        Download zip file and extract its contents.
        
        Args:
            doc_url: URL of the zip file
            filing_id: Unique filing identifier
            year: Year of the filings
            
        Returns:
            Dictionary with extracted file metadata or None if failed
        """
        logger.info(
            "Starting zip download",
            filing_id=filing_id,
            doc_url=doc_url,
            year=year
        )
        
        with performance_timer("zip_download.total", {"filing_id": filing_id}):
            try:
                # Check if already processed
                existing_data = await self._check_existing_data(filing_id)
                if existing_data:
                    logger.info("Zip already processed", filing_id=filing_id)
                    metrics.increment("zip_download.cache_hits")
                    return existing_data
                
                # Download the zip file
                zip_data, content_type = await self._download_zip(doc_url)
                if not zip_data:
                    return None
                
                # Extract and process contents
                extracted_files = await self._extract_zip_contents(zip_data, filing_id, year)
                if not extracted_files:
                    return None
                
                # Compute file hash
                file_hash = self._compute_file_hash(zip_data)
                
                # Prepare metadata
                download_metadata = {
                    'filing_id': filing_id,
                    'doc_url': doc_url,
                    'year': year,
                    'file_hash': file_hash,
                    'zip_size': len(zip_data),
                    'content_type': content_type,
                    'extracted_files': extracted_files,
                    'download_timestamp': datetime.utcnow().isoformat(),
                    'is_bulk_download': True
                }
                
                logger.info(
                    "Zip download completed",
                    filing_id=filing_id,
                    zip_size=len(zip_data),
                    extracted_count=len(extracted_files),
                    file_hash=file_hash[:12]
                )
                
                metrics.increment("zip_download.success")
                metrics.gauge("zip_download.file_size", len(zip_data))
                metrics.gauge("zip_download.extracted_files", len(extracted_files))
                
                return download_metadata
                
            except Exception as e:
                logger.error(
                    "Zip download failed",
                    filing_id=filing_id,
                    doc_url=doc_url,
                    error=str(e)
                )
                metrics.increment("zip_download.errors")
                return None
    
    async def _download_zip(self, doc_url: str) -> tuple[Optional[bytes], Optional[str]]:
        """Download zip content from URL."""
        
        async def _fetch_zip():
            async with self.session.get(doc_url) as response:
                # Check response status
                if response.status == 404:
                    raise NonRetryableError(f"Zip file not found: {doc_url}")
                elif response.status != 200:
                    raise RetryableError(f"HTTP {response.status}: {response.reason}")
                
                # Check content type
                content_type = response.headers.get('content-type', '').lower()
                if 'zip' not in content_type and 'application/octet-stream' not in content_type:
                    logger.warning("Unexpected content type", content_type=content_type, url=doc_url)
                
                # Read content
                zip_data = await response.read()
                
                # Basic zip validation
                if not zip_data.startswith(b'PK'):
                    raise NonRetryableError("Downloaded content is not a valid zip file")
                
                return zip_data, content_type
        
        try:
            return await retry_with_backoff(
                _fetch_zip,
                max_attempts=self.settings.MAX_RETRIES,
                base_delay=2.0,
                max_delay=30.0
            )
        except Exception as e:
            logger.error("Failed to download zip", url=doc_url, error=str(e))
            return None, None
    
    async def _extract_zip_contents(
        self, 
        zip_data: bytes, 
        filing_id: str, 
        year: int
    ) -> List[Dict[str, Any]]:
        """Extract and process zip file contents."""
        
        extracted_files = []
        temp_zip_path = self.temp_dir / f"{filing_id}.zip"
        
        try:
            # Save zip to temp file
            with open(temp_zip_path, 'wb') as f:
                f.write(zip_data)
            
            # Extract contents
            with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                
                logger.info(
                    "Extracting zip contents",
                    filing_id=filing_id,
                    file_count=len(file_list)
                )
                
                for filename in file_list:
                    try:
                        # Extract file content
                        file_content = zip_ref.read(filename)
                        file_info = zip_ref.getinfo(filename)
                        
                        # Determine file type
                        file_path = Path(filename)
                        file_type = self._determine_file_type(file_path.suffix, file_content)
                        
                        # Save extracted file temporarily for processing
                        temp_file_path = self.temp_dir / f"{filing_id}_{file_path.name}"
                        with open(temp_file_path, 'wb') as f:
                            f.write(file_content)
                        
                        file_metadata = {
                            'filename': filename,
                            'file_type': file_type,
                            'file_size': len(file_content),
                            'compressed_size': file_info.compress_size,
                            'file_hash': hashlib.sha256(file_content).hexdigest(),
                            'temp_path': str(temp_file_path),
                            'file_path': str(temp_file_path),  # Add file_path for parser compatibility
                            'filing_id': filing_id,
                            'year': year,
                            'extracted_from': filing_id
                        }
                        
                        extracted_files.append(file_metadata)
                        
                        logger.debug(
                            "Extracted file",
                            filename=filename,
                            file_type=file_type,
                            size=len(file_content)
                        )
                        
                    except Exception as e:
                        logger.warning(
                            "Failed to extract file",
                            filename=filename,
                            error=str(e)
                        )
                        continue
            
            return extracted_files
            
        except Exception as e:
            logger.error("Failed to extract zip contents", error=str(e))
            return []
        
        finally:
            # Clean up temp zip file
            if temp_zip_path.exists():
                temp_zip_path.unlink(missing_ok=True)
    
    def _determine_file_type(self, extension: str, content: bytes) -> str:
        """Determine the type of extracted file."""
        extension = extension.lower()
        
        if extension == '.xml':
            return 'xml'
        elif extension == '.txt':
            return 'txt'
        elif extension == '.pdf':
            return 'pdf'
        elif content.startswith(b'<?xml'):
            return 'xml'
        elif content.startswith(b'%PDF'):
            return 'pdf'
        else:
            # Try to decode as text
            try:
                content.decode('utf-8')
                return 'txt'
            except UnicodeDecodeError:
                return 'binary'
    
    def _compute_file_hash(self, zip_data: bytes) -> str:
        """Compute SHA256 hash of zip content."""
        return hashlib.sha256(zip_data).hexdigest()
    
    async def _check_existing_data(self, filing_id: str) -> Optional[Dict[str, Any]]:
        """Check if zip has already been processed."""
        # For now, we'll implement a simple file-based check
        # In a real system, this would check a database
        
        processed_marker = self.temp_dir / f"{filing_id}.processed"
        if processed_marker.exists():
            try:
                import json
                with open(processed_marker, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        
        return None
    
    async def download_batch(
        self, 
        filings: List[Dict[str, Any]], 
        max_concurrent: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Download multiple zip files concurrently.
        
        Args:
            filings: List of filing dictionaries with doc_url, filing_id, year
            max_concurrent: Maximum concurrent downloads (defaults to settings)
            
        Returns:
            List of successful download results
        """
        if not max_concurrent:
            max_concurrent = self.settings.MAX_CONCURRENCY
        
        logger.info("Starting batch zip download", count=len(filings))
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def download_with_semaphore(filing):
            async with semaphore:
                return await self.download_and_extract_zip(
                    filing['doc_url'],
                    filing['filing_id'],
                    filing['year']
                )
        
        # Execute downloads concurrently
        tasks = [download_with_semaphore(filing) for filing in filings]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful results
        successful_downloads = []
        errors = 0
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    "Batch download task failed",
                    filing_id=filings[i].get('filing_id'),
                    error=str(result)
                )
                errors += 1
            elif result:
                successful_downloads.append(result)
        
        logger.info(
            "Batch zip download completed",
            total=len(filings),
            successful=len(successful_downloads),
            errors=errors
        )
        
        metrics.gauge("zip_download.batch_success_rate", 
                     len(successful_downloads) / len(filings) if filings else 0)
        
        return successful_downloads
