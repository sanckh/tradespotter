"""PDF downloader with file hash computation and Supabase storage."""

import os
import hashlib
import asyncio
from typing import Optional, Dict, Any, List
from pathlib import Path
import aiohttp
import structlog
from supabase import create_client, Client

from ..config.settings import Settings
from ..utils.retry_utils import retry_with_backoff, RetryableError, NonRetryableError
from ..utils.logging_config import performance_timer, metrics

logger = structlog.get_logger()


class PDFDownloader:
    """Downloads PTR PDF files with integrity verification and storage."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.session: Optional[aiohttp.ClientSession] = None
        self.supabase: Optional[Client] = None
        self.temp_dir = Path("temp_downloads")
        self.temp_dir.mkdir(exist_ok=True)
        
    async def __aenter__(self):
        """Async context manager entry."""
        # Setup HTTP session
        connector = aiohttp.TCPConnector(limit=self.settings.max_concurrency)
        timeout = aiohttp.ClientTimeout(total=300)  # 5 minutes for large PDFs
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'User-Agent': self.settings.user_agent,
                'Accept': 'application/pdf,*/*',
            }
        )
        
        # Setup Supabase client
        self.supabase = create_client(
            self.settings.supabase_url,
            self.settings.supabase_service_role_key
        )
        
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
            
        # Clean up temp files
        try:
            for temp_file in self.temp_dir.glob("*.pdf"):
                temp_file.unlink(missing_ok=True)
        except Exception as e:
            logger.warning("Failed to clean temp files", error=str(e))
    
    async def download_and_store_pdf(
        self, 
        doc_url: str, 
        filing_id: str,
        member_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Download PDF and store in Supabase with metadata.
        
        Args:
            doc_url: URL of the PDF document
            filing_id: Unique filing identifier
            member_name: Name of the congress member
            
        Returns:
            Dictionary with file metadata or None if failed
        """
        logger.info(
            "Starting PDF download",
            filing_id=filing_id,
            doc_url=doc_url,
            member_name=member_name
        )
        
        with performance_timer("pdf_download.total", {"filing_id": filing_id}):
            try:
                # Check if already exists in storage
                existing_file = await self._check_existing_file(filing_id)
                if existing_file:
                    logger.info("PDF already exists in storage", filing_id=filing_id)
                    metrics.increment("pdf_download.cache_hits")
                    return existing_file
                
                # Download the PDF
                pdf_data, content_type = await self._download_pdf(doc_url)
                if not pdf_data:
                    return None
                
                # Compute file hash
                file_hash = self._compute_file_hash(pdf_data)
                
                # Generate storage path
                storage_path = self._generate_storage_path(filing_id, member_name)
                
                # Upload to Supabase storage
                storage_result = await self._upload_to_storage(
                    pdf_data, storage_path, content_type
                )
                
                if not storage_result:
                    return None
                
                # Prepare file metadata
                file_metadata = {
                    'filing_id': filing_id,
                    'doc_url': doc_url,
                    'storage_path': storage_path,
                    'file_hash': file_hash,
                    'file_size': len(pdf_data),
                    'content_type': content_type,
                    'member_name': member_name,
                    'bucket': self.settings.storage_bucket
                }
                
                logger.info(
                    "PDF download completed",
                    filing_id=filing_id,
                    file_size=len(pdf_data),
                    file_hash=file_hash[:12]
                )
                
                metrics.increment("pdf_download.success")
                metrics.gauge("pdf_download.file_size", len(pdf_data))
                
                return file_metadata
                
            except Exception as e:
                logger.error(
                    "PDF download failed",
                    filing_id=filing_id,
                    doc_url=doc_url,
                    error=str(e)
                )
                metrics.increment("pdf_download.errors")
                return None
    
    async def _download_pdf(self, doc_url: str) -> tuple[Optional[bytes], Optional[str]]:
        """Download PDF content from URL."""
        
        async def _fetch_pdf():
            async with self.session.get(doc_url) as response:
                # Check response status
                if response.status == 404:
                    raise NonRetryableError(f"PDF not found: {doc_url}")
                elif response.status != 200:
                    raise RetryableError(f"HTTP {response.status}: {response.reason}")
                
                # Check content type
                content_type = response.headers.get('content-type', '').lower()
                if 'pdf' not in content_type and 'application/octet-stream' not in content_type:
                    logger.warning("Unexpected content type", content_type=content_type, url=doc_url)
                
                # Read content
                pdf_data = await response.read()
                
                # Basic PDF validation
                if not pdf_data.startswith(b'%PDF'):
                    raise NonRetryableError("Downloaded content is not a valid PDF")
                
                return pdf_data, content_type
        
        try:
            return await retry_with_backoff(
                _fetch_pdf,
                max_attempts=self.settings.max_retries,
                base_delay=2.0,
                max_delay=30.0
            )
        except Exception as e:
            logger.error("Failed to download PDF", url=doc_url, error=str(e))
            return None, None
    
    def _compute_file_hash(self, pdf_data: bytes) -> str:
        """Compute SHA256 hash of PDF content."""
        return hashlib.sha256(pdf_data).hexdigest()
    
    def _generate_storage_path(self, filing_id: str, member_name: str) -> str:
        """Generate storage path for the PDF file."""
        # Clean member name for file path
        clean_name = "".join(c for c in member_name if c.isalnum() or c in (' ', '-', '_')).strip()
        clean_name = clean_name.replace(' ', '_')
        
        # Create path: year/member_name/filing_id.pdf
        from datetime import datetime
        year = datetime.now().year
        
        return f"ptr_filings/{year}/{clean_name}/{filing_id}.pdf"
    
    async def _upload_to_storage(
        self, 
        pdf_data: bytes, 
        storage_path: str, 
        content_type: str
    ) -> bool:
        """Upload PDF to Supabase storage."""
        try:
            # Upload file to storage bucket
            result = self.supabase.storage.from_(self.settings.storage_bucket).upload(
                path=storage_path,
                file=pdf_data,
                file_options={
                    "content-type": content_type or "application/pdf",
                    "cache-control": "3600"
                }
            )
            
            if hasattr(result, 'error') and result.error:
                # Check if file already exists
                if 'already exists' in str(result.error).lower():
                    logger.info("File already exists in storage", path=storage_path)
                    return True
                else:
                    logger.error("Storage upload failed", error=result.error, path=storage_path)
                    return False
            
            logger.debug("File uploaded to storage", path=storage_path)
            return True
            
        except Exception as e:
            logger.error("Storage upload exception", error=str(e), path=storage_path)
            return False
    
    async def _check_existing_file(self, filing_id: str) -> Optional[Dict[str, Any]]:
        """Check if file already exists in storage."""
        try:
            # List files in storage to find existing file
            result = self.supabase.storage.from_(self.settings.storage_bucket).list(
                path="ptr_filings",
                options={"search": filing_id}
            )
            
            if hasattr(result, 'error') and result.error:
                return None
            
            # Look for matching file
            for file_info in result:
                if filing_id in file_info.get('name', ''):
                    return {
                        'filing_id': filing_id,
                        'storage_path': file_info.get('name'),
                        'file_size': file_info.get('metadata', {}).get('size'),
                        'bucket': self.settings.storage_bucket,
                        'cached': True
                    }
            
            return None
            
        except Exception as e:
            logger.warning("Failed to check existing file", filing_id=filing_id, error=str(e))
            return None
    
    async def get_file_url(self, storage_path: str, expires_in: int = 3600) -> Optional[str]:
        """Get signed URL for accessing stored file."""
        try:
            result = self.supabase.storage.from_(self.settings.storage_bucket).create_signed_url(
                path=storage_path,
                expires_in=expires_in
            )
            
            if hasattr(result, 'error') and result.error:
                logger.error("Failed to create signed URL", error=result.error)
                return None
            
            return result.get('signedURL')
            
        except Exception as e:
            logger.error("Exception creating signed URL", error=str(e))
            return None
    
    async def download_batch(
        self, 
        filings: List[Dict[str, Any]], 
        max_concurrent: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Download multiple PDFs concurrently.
        
        Args:
            filings: List of filing dictionaries with doc_url, filing_id, member_name
            max_concurrent: Maximum concurrent downloads (defaults to settings)
            
        Returns:
            List of successful download results
        """
        if not max_concurrent:
            max_concurrent = self.settings.max_concurrency
        
        logger.info("Starting batch PDF download", count=len(filings))
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def download_with_semaphore(filing):
            async with semaphore:
                return await self.download_and_store_pdf(
                    filing['doc_url'],
                    filing['filing_id'],
                    filing['member_name']
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
            "Batch PDF download completed",
            total=len(filings),
            successful=len(successful_downloads),
            errors=errors
        )
        
        metrics.gauge("pdf_download.batch_success_rate", 
                     len(successful_downloads) / len(filings) if filings else 0)
        
        return successful_downloads
    
    async def verify_file_integrity(self, storage_path: str, expected_hash: str) -> bool:
        """Verify integrity of stored file."""
        try:
            # Download file from storage
            result = self.supabase.storage.from_(self.settings.storage_bucket).download(storage_path)
            
            if hasattr(result, 'error') and result.error:
                return False
            
            # Compute hash of downloaded content
            actual_hash = hashlib.sha256(result).hexdigest()
            
            return actual_hash == expected_hash
            
        except Exception as e:
            logger.error("File integrity verification failed", path=storage_path, error=str(e))
            return False
