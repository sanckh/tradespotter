"""TXT parser for extracting PTR data from bulk tab-delimited files."""

import csv
import io
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import structlog

from ..database.models import ParsedTradeRow
from ..utils.logging_config import performance_timer, metrics

logger = structlog.get_logger()


class TXTParser:
    """Parses PTR TXT files from bulk downloads to extract filing metadata."""
    
    # Expected TXT file columns
    EXPECTED_COLUMNS = [
        'Prefix', 'Last', 'First', 'Suffix', 'FilingType', 
        'StateDst', 'Year', 'FilingDate', 'DocID'
    ]
    
    # Filing type mappings
    FILING_TYPE_MAP = {
        'A': 'Amendment',
        'C': 'Candidate',
        'D': 'Disclosure',
        'O': 'Officer',
        'P': 'Periodic Transaction Report',
        'X': 'Extension'
    }
    
    def __init__(self):
        self.current_filing_id: Optional[str] = None
        
    async def parse_txt_file(
        self, 
        txt_data: bytes, 
        filing_id: str,
        year: int
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Parse TXT file and extract PTR filing metadata.
        
        Args:
            txt_data: Raw TXT bytes
            filing_id: Unique filing identifier
            year: Year of the filings
            
        Returns:
            Tuple of (parsed_filings, errors)
        """
        self.current_filing_id = filing_id
        
        logger.info(
            "Starting TXT parsing",
            filing_id=filing_id,
            year=year,
            size_bytes=len(txt_data)
        )
        
        with performance_timer("txt_parse.total", {"filing_id": filing_id}):
            try:
                # Decode TXT content
                txt_content = txt_data.decode('utf-8', errors='replace')
                
                # Parse tab-delimited content
                parsed_filings, errors = await self._parse_tab_delimited(
                    txt_content, filing_id, year
                )
                
                logger.info(
                    "TXT parsing completed",
                    filing_id=filing_id,
                    filings_parsed=len(parsed_filings),
                    errors=len(errors)
                )
                
                metrics.increment("txt_parse.success")
                metrics.gauge("txt_parse.filings_count", len(parsed_filings))
                metrics.gauge("txt_parse.errors_count", len(errors))
                
                return parsed_filings, errors
                
            except Exception as e:
                logger.error(
                    "TXT parsing failed",
                    filing_id=filing_id,
                    error=str(e)
                )
                metrics.increment("txt_parse.errors")
                return [], [{"error": str(e), "filing_id": filing_id}]
    
    async def _parse_tab_delimited(
        self, 
        txt_content: str, 
        filing_id: str, 
        year: int
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Parse tab-delimited TXT content."""
        
        parsed_filings = []
        errors = []
        
        try:
            # Use CSV reader with tab delimiter
            csv_reader = csv.DictReader(
                io.StringIO(txt_content), 
                delimiter='\t'
            )
            
            # Validate headers
            if not csv_reader.fieldnames:
                raise ValueError("No headers found in TXT file")
            
            # Check for expected columns
            missing_columns = set(self.EXPECTED_COLUMNS) - set(csv_reader.fieldnames)
            if missing_columns:
                logger.warning(
                    "Missing expected columns",
                    missing=list(missing_columns),
                    found=list(csv_reader.fieldnames)
                )
            
            row_count = 0
            for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 (after header)
                row_count += 1
                
                try:
                    # Parse individual row
                    parsed_filing = await self._parse_filing_row(row, row_num, year)
                    if parsed_filing:
                        parsed_filings.append(parsed_filing)
                        
                except Exception as e:
                    error_info = {
                        "error": str(e),
                        "row_number": row_num,
                        "filing_id": filing_id,
                        "raw_row": row
                    }
                    errors.append(error_info)
                    logger.warning(
                        "Failed to parse row",
                        row_number=row_num,
                        error=str(e)
                    )
            
            logger.info(
                "Tab-delimited parsing completed",
                total_rows=row_count,
                successful=len(parsed_filings),
                errors=len(errors)
            )
            
        except Exception as e:
            logger.error("Failed to parse tab-delimited content", error=str(e))
            errors.append({
                "error": f"Tab parsing failed: {str(e)}",
                "filing_id": filing_id
            })
        
        return parsed_filings, errors
    
    async def _parse_filing_row(
        self, 
        row: Dict[str, str], 
        row_num: int, 
        year: int
    ) -> Optional[Dict[str, Any]]:
        """Parse individual filing row."""
        
        try:
            # Extract and clean fields
            prefix = row.get('Prefix', '').strip()
            last_name = row.get('Last', '').strip()
            first_name = row.get('First', '').strip()
            suffix = row.get('Suffix', '').strip()
            filing_type = row.get('FilingType', '').strip()
            state_district = row.get('StateDst', '').strip()
            filing_year = row.get('Year', '').strip()
            filing_date = row.get('FilingDate', '').strip()
            doc_id = row.get('DocID', '').strip()
            
            # Validate required fields
            if not last_name or not first_name or not doc_id:
                logger.warning(
                    "Missing required fields",
                    row_number=row_num,
                    last_name=bool(last_name),
                    first_name=bool(first_name),
                    doc_id=bool(doc_id)
                )
                return None
            
            # Build full name
            name_parts = [prefix, first_name, last_name, suffix]
            full_name = ' '.join(part for part in name_parts if part).strip()
            
            # Parse filing date
            parsed_date = None
            if filing_date:
                try:
                    parsed_date = datetime.strptime(filing_date, '%m/%d/%Y').date()
                except ValueError:
                    logger.warning(
                        "Invalid date format",
                        row_number=row_num,
                        filing_date=filing_date
                    )
            
            # Map filing type
            filing_type_description = self.FILING_TYPE_MAP.get(
                filing_type, 
                filing_type
            )
            
            # Create parsed filing record
            parsed_filing = {
                'doc_id': doc_id,
                'member_name': full_name,
                'first_name': first_name,
                'last_name': last_name,
                'prefix': prefix or None,
                'suffix': suffix or None,
                'filing_type': filing_type,
                'filing_type_description': filing_type_description,
                'state_district': state_district or None,
                'filing_year': int(filing_year) if filing_year.isdigit() else year,
                'filing_date': parsed_date,
                'raw_filing_date': filing_date,
                'row_number': row_num,
                'source_year': year,
                'bulk_filing_id': self.current_filing_id
            }
            
            return parsed_filing
            
        except Exception as e:
            logger.error(
                "Failed to parse filing row",
                row_number=row_num,
                error=str(e),
                row_data=row
            )
            raise
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        if not text:
            return ""
        
        # Remove extra whitespace and normalize
        cleaned = ' '.join(text.split())
        
        # Remove common artifacts
        cleaned = cleaned.replace('\x00', '')  # Null bytes
        cleaned = cleaned.replace('\ufffd', '')  # Replacement characters
        
        return cleaned.strip()


class BulkTXTParser:
    """Handles parsing of multiple TXT files from bulk downloads."""
    
    def __init__(self):
        self.txt_parser = TXTParser()
    
    async def parse_bulk_files(
        self, 
        extracted_files: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Parse multiple TXT files from bulk download.
        
        Args:
            extracted_files: List of extracted file metadata from ZipDownloader
            
        Returns:
            Tuple of (all_parsed_filings, all_errors)
        """
        all_parsed_filings = []
        all_errors = []
        
        # Filter for TXT files only
        txt_files = [
            file_info for file_info in extracted_files 
            if file_info.get('file_type') == 'txt'
        ]
        
        logger.info(
            "Starting bulk TXT parsing",
            total_files=len(extracted_files),
            txt_files=len(txt_files)
        )
        
        for file_info in txt_files:
            try:
                file_path = file_info.get('file_path')
                filing_id = file_info.get('filing_id', 'unknown')
                year = file_info.get('year', 2023)
                
                if not file_path:
                    logger.warning("Missing file path", file_info=file_info)
                    continue
                
                # Read TXT file content
                with open(file_path, 'rb') as f:
                    txt_data = f.read()
                
                # Parse TXT file
                parsed_filings, errors = await self.txt_parser.parse_txt_file(
                    txt_data, filing_id, year
                )
                
                all_parsed_filings.extend(parsed_filings)
                all_errors.extend(errors)
                
            except Exception as e:
                logger.error(
                    "Failed to process TXT file",
                    file_info=file_info,
                    error=str(e)
                )
                all_errors.append({
                    "error": f"File processing failed: {str(e)}",
                    "file_info": file_info
                })
        
        logger.info(
            "Bulk TXT parsing completed",
            total_filings=len(all_parsed_filings),
            total_errors=len(all_errors)
        )
        
        return all_parsed_filings, all_errors
