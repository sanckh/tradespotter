"""PTR filing discovery module for House Clerk website."""

import re
import asyncio
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, date
from urllib.parse import urljoin, urlparse
import aiohttp
from bs4 import BeautifulSoup
import structlog

from ..config.settings import Settings
from ..utils.retry_utils import retry_with_backoff, RetryableError, NonRetryableError
from ..utils.logging_config import performance_timer, metrics

logger = structlog.get_logger()


class PTRDiscovery:
    """Discovers PTR filing URLs from the House Clerk website."""
    
    BASE_URL = "https://disclosures-clerk.house.gov"
    SEARCH_URL = f"{BASE_URL}/PublicDisclosure/FinancialDisclosure"
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.session: Optional[aiohttp.ClientSession] = None
        self.discovered_urls: Set[str] = set()
        
    async def __aenter__(self):
        """Async context manager entry."""
        connector = aiohttp.TCPConnector(limit=self.settings.MAX_CONCURRENCY)
        timeout = aiohttp.ClientTimeout(total=30)
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'User-Agent': self.settings.USER_AGENT,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def discover_ptr_filings(
        self, 
        year_start: Optional[int] = 2012,
        year_end: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Discover PTR filing URLs for the specified year range.
        
        Args:
            year_start: Start year for discovery (defaults to settings)
            year_end: End year for discovery (defaults to settings)
            limit: Maximum number of filings to discover
            
        Returns:
            List of filing metadata dictionaries
        """
        if not year_start or not year_end:
            year_start, year_end = self._parse_year_window()
        
        logger.info(
            "Starting PTR filing discovery",
            year_start=year_start,
            year_end=year_end,
            limit=limit
        )
        
        all_filings = []
        
        with performance_timer("ptr_discovery.total"):
            for year in range(year_start, year_end + 1):
                try:
                    year_filings = await self._discover_year_filings(year, limit)
                    all_filings.extend(year_filings)
                    
                    logger.info(
                        "Year discovery completed",
                        year=year,
                        filings_found=len(year_filings)
                    )
                    
                    # Apply global limit if specified
                    if limit and len(all_filings) >= limit:
                        all_filings = all_filings[:limit]
                        break
                        
                    # Throttle between years
                    if self.settings.THROTTLE_MS > 0:
                        await asyncio.sleep(self.settings.THROTTLE_MS / 1000.0)
                        
                except Exception as e:
                    logger.error(
                        "Year discovery failed",
                        year=year,
                        error=str(e)
                    )
                    metrics.increment("discovery.year_errors")
                    continue
        
        # Remove duplicates based on URL
        unique_filings = self._deduplicate_filings(all_filings)
        
        logger.info(
            "PTR filing discovery completed",
            total_found=len(unique_filings),
            years_searched=year_end - year_start + 1
        )
        
        metrics.gauge("discovery.filings_found", len(unique_filings))
        return unique_filings
    
    async def _discover_year_filings(self, year: int, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Discover PTR filings for a specific year."""
        filings = []
        page = 1
        
        while True:
            try:
                page_filings = await self._discover_page_filings(year, page)
                
                if not page_filings:
                    # No more filings on this page
                    break
                
                filings.extend(page_filings)
                
                logger.debug(
                    "Page discovery completed",
                    year=year,
                    page=page,
                    filings_on_page=len(page_filings)
                )
                
                # Check if we've hit the limit
                if limit and len(filings) >= limit:
                    filings = filings[:limit]
                    break
                
                page += 1
                
                # Throttle between pages
                if self.settings.THROTTLE_MS > 0:
                    await asyncio.sleep(self.settings.THROTTLE_MS / 1000.0)
                
                # Safety limit on pages
                if page > 100:
                    logger.warning("Hit page limit safety check", year=year, page=page)
                    break
                    
            except Exception as e:
                logger.error(
                    "Page discovery failed",
                    year=year,
                    page=page,
                    error=str(e)
                )
                metrics.increment("discovery.page_errors")
                break
        
        return filings
    
    async def _discover_page_filings(self, year: int, page: int) -> List[Dict[str, Any]]:
        """Discover PTR filings on a specific page."""
        
        async def _fetch_page():
            params = {
                'Year': str(year),
                'FilingType': 'P',  # PTR filings
                'Page': str(page)
            }
            
            async with self.session.get(self.SEARCH_URL, params=params) as response:
                if response.status == 404:
                    return None  # No more pages
                elif response.status != 200:
                    raise RetryableError(f"HTTP {response.status}: {response.reason}")
                
                return await response.text()
        
        # Fetch page with retry
        html_content = await retry_with_backoff(
            _fetch_page,
            max_attempts=self.settings.MAX_RETRIES,
            base_delay=1.0,
            max_delay=10.0
        )
        
        if html_content is None:
            return []  # No more pages
        
        # Parse the HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find filing entries in the results table
        filings = []
        
        # Look for the results table
        results_table = soup.find('table', {'class': 'table'}) or soup.find('table')
        
        if not results_table:
            logger.debug("No results table found", year=year, page=page)
            return []
        
        # Parse table rows
        rows = results_table.find_all('tr')[1:]  # Skip header row
        
        for row in rows:
            try:
                filing = self._parse_filing_row(row, year)
                if filing:
                    filings.append(filing)
            except Exception as e:
                logger.warning(
                    "Failed to parse filing row",
                    year=year,
                    page=page,
                    error=str(e)
                )
                continue
        
        metrics.increment("discovery.pages_processed")
        return filings
    
    def _parse_filing_row(self, row, year: int) -> Optional[Dict[str, Any]]:
        """Parse a single filing row from the results table."""
        cells = row.find_all('td')
        
        if len(cells) < 4:
            return None
        
        try:
            # Extract basic information
            name_cell = cells[0]
            filing_date_cell = cells[1]
            doc_link_cell = cells[2] if len(cells) > 2 else None
            
            # Extract member name
            member_name = name_cell.get_text(strip=True)
            if not member_name:
                return None
            
            # Extract filing date
            filing_date_str = filing_date_cell.get_text(strip=True)
            filing_date = self._parse_date(filing_date_str)
            
            # Extract document URL
            doc_url = None
            if doc_link_cell:
                link = doc_link_cell.find('a')
                if link and link.get('href'):
                    doc_url = urljoin(self.BASE_URL, link['href'])
            
            if not doc_url:
                return None
            
            # Generate a filing ID from the URL
            filing_id = self._extract_filing_id(doc_url)
            
            # Extract additional metadata from URL or page
            report_type = 'PTR'  # Periodic Transaction Report
            
            filing_data = {
                'filing_id': filing_id,
                'member_name': member_name,
                'filing_date': filing_date,
                'doc_url': doc_url,
                'report_type': report_type,
                'year': year,
                'source': 'house_clerk',
                'discovered_at': datetime.utcnow().isoformat()
            }
            
            # Add to discovered URLs set
            self.discovered_urls.add(doc_url)
            
            return filing_data
            
        except Exception as e:
            logger.warning("Failed to parse filing row", error=str(e))
            return None
    
    def _extract_filing_id(self, doc_url: str) -> str:
        """Extract a unique filing ID from the document URL."""
        # Try to extract ID from URL path or query parameters
        parsed_url = urlparse(doc_url)
        
        # Look for ID in query parameters
        if 'id=' in parsed_url.query:
            match = re.search(r'id=([^&]+)', parsed_url.query)
            if match:
                return match.group(1)
        
        # Look for ID in path
        path_parts = parsed_url.path.split('/')
        for part in reversed(path_parts):
            if part and len(part) > 5:  # Likely an ID
                return part
        
        # Fallback: use hash of URL
        import hashlib
        return hashlib.md5(doc_url.encode()).hexdigest()[:12]
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse date string from the filing table."""
        if not date_str:
            return None
        
        # Common date formats
        date_patterns = [
            r'(\d{1,2})/(\d{1,2})/(\d{4})',  # MM/DD/YYYY
            r'(\d{4})-(\d{1,2})-(\d{1,2})',  # YYYY-MM-DD
            r'(\d{1,2})-(\d{1,2})-(\d{4})',  # MM-DD-YYYY
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, date_str.strip())
            if match:
                try:
                    if pattern.startswith(r'(\d{4})'):  # YYYY-MM-DD
                        year = int(match.group(1))
                        month = int(match.group(2))
                        day = int(match.group(3))
                    else:  # MM/DD/YYYY or MM-DD-YYYY
                        month = int(match.group(1))
                        day = int(match.group(2))
                        year = int(match.group(3))
                    
                    return date(year, month, day)
                except ValueError:
                    continue
        
        logger.warning("Failed to parse date", date_string=date_str)
        return None
    
    def _parse_year_window(self) -> tuple[int, int]:
        """Parse year window from settings."""
        year_window = self.settings.HOUSE_YEAR_WINDOW
        
        if '-' in year_window:
            start_str, end_str = year_window.split('-', 1)
            return int(start_str.strip()), int(end_str.strip())
        else:
            # Single year
            year = int(year_window.strip())
            return year, year
    
    def _deduplicate_filings(self, filings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate filings based on URL."""
        seen_urls = set()
        unique_filings = []
        
        for filing in filings:
            url = filing.get('doc_url')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_filings.append(filing)
        
        duplicates_removed = len(filings) - len(unique_filings)
        if duplicates_removed > 0:
            logger.info("Removed duplicate filings", count=duplicates_removed)
            metrics.increment("discovery.duplicates_removed", duplicates_removed)
        
        return unique_filings
    
    async def get_filing_metadata(self, doc_url: str) -> Optional[Dict[str, Any]]:
        """Get additional metadata for a specific filing."""
        try:
            async with self.session.get(doc_url) as response:
                if response.status != 200:
                    return None
                
                html_content = await response.text()
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Extract metadata from the filing page
                metadata = {
                    'doc_url': doc_url,
                    'content_type': response.headers.get('content-type', ''),
                    'content_length': response.headers.get('content-length'),
                    'last_modified': response.headers.get('last-modified'),
                }
                
                # Try to extract additional info from page
                title = soup.find('title')
                if title:
                    metadata['page_title'] = title.get_text(strip=True)
                
                return metadata
                
        except Exception as e:
            logger.warning("Failed to get filing metadata", url=doc_url, error=str(e))
            return None
