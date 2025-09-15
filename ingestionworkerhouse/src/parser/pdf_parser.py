"""PDF parser for extracting trade data from PTR filings."""

import re
import io
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import pandas as pd
import pdfplumber
import structlog
from datetime import datetime, date

from ..database.models import ParsedTradeRow
from ..utils.retry_utils import NonRetryableError
from ..utils.logging_config import performance_timer, metrics

logger = structlog.get_logger()


class PDFParser:
    """Parses PTR PDF files to extract trade data using multiple strategies."""
    
    # Common patterns for trade data extraction
    TRANSACTION_PATTERNS = [
        r'(Purchase|Sale|P|S)\s+([A-Z]{1,5})\s+(.+?)\s+(\d{1,2}/\d{1,2}/\d{4})\s+(\$[\d,]+\s*-\s*\$[\d,]+)',
        r'([PS])\s+(.+?)\s+([A-Z]{1,5})?\s+(\d{1,2}/\d{1,2}/\d{4})\s+(\$[\d,]+\s*-\s*\$[\d,]+)',
        r'(.+?)\s+([A-Z]{1,5})\s+(Purchase|Sale|P|S)\s+(\d{1,2}/\d{1,2}/\d{4})\s+(\$[\d,]+\s*-\s*\$[\d,]+)'
    ]
    
    # Amount range patterns
    AMOUNT_PATTERNS = [
        r'\$?([\d,]+)\s*-\s*\$?([\d,]+)',
        r'Over\s+\$?([\d,]+)',
        r'\$?([\d,]+)\s*\+',
        r'\$?([\d,]+)'
    ]
    
    def __init__(self):
        self.current_filing_id: Optional[str] = None
        
    async def parse_pdf_file(
        self, 
        pdf_data: bytes, 
        filing_id: str,
        member_name: str
    ) -> Tuple[List[ParsedTradeRow], List[Dict[str, Any]]]:
        """
        Parse PDF file and extract trade data.
        
        Args:
            pdf_data: Raw PDF bytes
            filing_id: Unique filing identifier
            member_name: Name of congress member
            
        Returns:
            Tuple of (parsed_trades, parsing_errors)
        """
        self.current_filing_id = filing_id
        
        logger.info(
            "Starting PDF parsing",
            filing_id=filing_id,
            member_name=member_name,
            file_size=len(pdf_data)
        )
        
        with performance_timer("pdf_parse.total", {"filing_id": filing_id}):
            try:
                # Parse using multiple strategies
                parsed_trades = []
                errors = []
                
                # Strategy 1: Table extraction
                table_trades, table_errors = await self._parse_with_tables(pdf_data)
                parsed_trades.extend(table_trades)
                errors.extend(table_errors)
                
                # Strategy 2: Text extraction if table parsing didn't find much
                if len(table_trades) < 3:  # Threshold for "not much"
                    text_trades, text_errors = await self._parse_with_text(pdf_data)
                    parsed_trades.extend(text_trades)
                    errors.extend(text_errors)
                
                # Remove duplicates
                unique_trades = self._deduplicate_trades(parsed_trades)
                
                logger.info(
                    "PDF parsing completed",
                    filing_id=filing_id,
                    trades_found=len(unique_trades),
                    errors=len(errors)
                )
                
                metrics.gauge("pdf_parse.trades_extracted", len(unique_trades))
                metrics.increment("pdf_parse.files_processed")
                
                return unique_trades, errors
                
            except Exception as e:
                logger.error(
                    "PDF parsing failed",
                    filing_id=filing_id,
                    error=str(e)
                )
                metrics.increment("pdf_parse.errors")
                raise NonRetryableError(f"PDF parsing failed: {str(e)}")
    
    async def _parse_with_tables(self, pdf_data: bytes) -> Tuple[List[ParsedTradeRow], List[Dict[str, Any]]]:
        """Parse PDF using table extraction."""
        trades = []
        errors = []
        
        try:
            with pdfplumber.open(io.BytesIO(pdf_data)) as pdf:
                logger.debug("Parsing PDF with table extraction", pages=len(pdf.pages))
                
                for page_num, page in enumerate(pdf.pages):
                    try:
                        page_trades, page_errors = await self._parse_page_tables(page, page_num)
                        trades.extend(page_trades)
                        errors.extend(page_errors)
                    except Exception as e:
                        logger.warning(
                            "Page table parsing failed",
                            page=page_num,
                            error=str(e)
                        )
                        errors.append({
                            'page': page_num,
                            'strategy': 'table',
                            'error': str(e)
                        })
                        
        except Exception as e:
            logger.error("Table extraction failed", error=str(e))
            errors.append({
                'strategy': 'table',
                'error': str(e)
            })
        
        return trades, errors
    
    async def _parse_page_tables(self, page, page_num: int) -> Tuple[List[ParsedTradeRow], List[Dict[str, Any]]]:
        """Parse tables from a single PDF page."""
        trades = []
        errors = []
        
        # Extract tables from page
        tables = page.extract_tables()
        
        if not tables:
            return trades, errors
        
        for table_idx, table in enumerate(tables):
            try:
                table_trades = await self._parse_table_data(table, page_num, table_idx)
                trades.extend(table_trades)
            except Exception as e:
                logger.warning(
                    "Table parsing failed",
                    page=page_num,
                    table=table_idx,
                    error=str(e)
                )
                errors.append({
                    'page': page_num,
                    'table': table_idx,
                    'strategy': 'table',
                    'error': str(e)
                })
        
        return trades, errors
    
    async def _parse_table_data(self, table: List[List[str]], page_num: int, table_idx: int) -> List[ParsedTradeRow]:
        """Parse trade data from extracted table."""
        trades = []
        
        if not table or len(table) < 2:
            return trades
        
        # Try to identify header row and data structure
        header_row = None
        data_start_idx = 0
        
        # Look for header indicators
        for i, row in enumerate(table[:3]):  # Check first 3 rows
            if any(self._is_header_cell(cell) for cell in row if cell):
                header_row = i
                data_start_idx = i + 1
                break
        
        if header_row is None:
            # No clear header, assume first row is header
            data_start_idx = 1
        
        # Parse data rows
        for row_idx in range(data_start_idx, len(table)):
            row = table[row_idx]
            
            try:
                trade = await self._parse_table_row(row, page_num, table_idx, row_idx)
                if trade:
                    trades.append(trade)
            except Exception as e:
                logger.debug(
                    "Row parsing failed",
                    page=page_num,
                    table=table_idx,
                    row=row_idx,
                    error=str(e)
                )
                continue
        
        return trades
    
    def _is_header_cell(self, cell: str) -> bool:
        """Check if a cell looks like a header."""
        if not cell:
            return False
        
        cell_lower = cell.lower().strip()
        header_indicators = [
            'transaction', 'asset', 'ticker', 'symbol', 'date', 'amount', 
            'purchase', 'sale', 'security', 'description', 'value'
        ]
        
        return any(indicator in cell_lower for indicator in header_indicators)
    
    async def _parse_table_row(self, row: List[str], page_num: int, table_idx: int, row_idx: int) -> Optional[ParsedTradeRow]:
        """Parse a single table row into trade data."""
        if not row or len(row) < 3:
            return None
        
        # Clean row data
        cleaned_row = [cell.strip() if cell else '' for cell in row]
        
        # Skip empty rows
        if not any(cleaned_row):
            return None
        
        # Try different column arrangements
        trade_data = self._extract_trade_from_row(cleaned_row)
        
        if not trade_data:
            return None
        
        # Create ParsedTradeRow
        return ParsedTradeRow(
            asset_name=trade_data.get('asset_name', ''),
            ticker=trade_data.get('ticker'),
            transaction_type=trade_data.get('transaction_type', ''),
            transaction_date=trade_data.get('transaction_date', ''),
            amount_range=trade_data.get('amount_range', ''),
            notes=trade_data.get('notes', ''),
            raw_text=' | '.join(cleaned_row),
            page_number=page_num,
            extraction_method='table'
        )
    
    def _extract_trade_from_row(self, row: List[str]) -> Optional[Dict[str, Any]]:
        """Extract trade information from a table row."""
        # Common column patterns for PTR forms
        patterns = [
            # Pattern 1: [Asset, Ticker, Type, Date, Amount]
            {
                'asset_name': 0,
                'ticker': 1, 
                'transaction_type': 2,
                'transaction_date': 3,
                'amount_range': 4
            },
            # Pattern 2: [Type, Asset, Ticker, Date, Amount]
            {
                'transaction_type': 0,
                'asset_name': 1,
                'ticker': 2,
                'transaction_date': 3,
                'amount_range': 4
            },
            # Pattern 3: [Asset, Type, Date, Amount] (no ticker)
            {
                'asset_name': 0,
                'transaction_type': 1,
                'transaction_date': 2,
                'amount_range': 3
            }
        ]
        
        for pattern in patterns:
            try:
                trade_data = {}
                valid = True
                
                for field, col_idx in pattern.items():
                    if col_idx < len(row):
                        value = row[col_idx].strip()
                        
                        # Validate field content
                        if field == 'transaction_type' and not self._is_transaction_type(value):
                            if not self._contains_transaction_type(value):
                                valid = False
                                break
                        elif field == 'transaction_date' and not self._is_date_like(value):
                            valid = False
                            break
                        elif field == 'amount_range' and not self._is_amount_like(value):
                            valid = False
                            break
                        
                        trade_data[field] = value
                    else:
                        valid = False
                        break
                
                if valid and self._validate_trade_data(trade_data):
                    return trade_data
                    
            except Exception:
                continue
        
        return None
    
    def _is_transaction_type(self, text: str) -> bool:
        """Check if text looks like a transaction type."""
        if not text:
            return False
        
        text_upper = text.upper().strip()
        return text_upper in ['P', 'S', 'PURCHASE', 'SALE', 'BUY', 'SELL', 'E', 'EXCHANGE']
    
    def _contains_transaction_type(self, text: str) -> bool:
        """Check if text contains transaction type indicators."""
        if not text:
            return False
        
        text_upper = text.upper()
        indicators = ['PURCHASE', 'SALE', 'BUY', 'SELL', 'SOLD', 'BOUGHT']
        return any(indicator in text_upper for indicator in indicators)
    
    def _is_date_like(self, text: str) -> bool:
        """Check if text looks like a date."""
        if not text:
            return False
        
        # Look for date patterns
        date_patterns = [
            r'\d{1,2}/\d{1,2}/\d{4}',
            r'\d{4}-\d{1,2}-\d{1,2}',
            r'\d{1,2}-\d{1,2}-\d{4}'
        ]
        
        return any(re.search(pattern, text) for pattern in date_patterns)
    
    def _is_amount_like(self, text: str) -> bool:
        """Check if text looks like an amount range."""
        if not text:
            return False
        
        # Look for amount patterns
        return any(re.search(pattern, text) for pattern in self.AMOUNT_PATTERNS)
    
    def _validate_trade_data(self, trade_data: Dict[str, Any]) -> bool:
        """Validate extracted trade data."""
        # Must have asset name
        if not trade_data.get('asset_name'):
            return False
        
        # Must have some kind of transaction indicator
        transaction_type = trade_data.get('transaction_type', '')
        if not (self._is_transaction_type(transaction_type) or 
                self._contains_transaction_type(transaction_type)):
            return False
        
        return True
    
    async def _parse_with_text(self, pdf_data: bytes) -> Tuple[List[ParsedTradeRow], List[Dict[str, Any]]]:
        """Parse PDF using text extraction and regex patterns."""
        trades = []
        errors = []
        
        try:
            with pdfplumber.open(io.BytesIO(pdf_data)) as pdf:
                logger.debug("Parsing PDF with text extraction", pages=len(pdf.pages))
                
                for page_num, page in enumerate(pdf.pages):
                    try:
                        page_trades, page_errors = await self._parse_page_text(page, page_num)
                        trades.extend(page_trades)
                        errors.extend(page_errors)
                    except Exception as e:
                        logger.warning(
                            "Page text parsing failed",
                            page=page_num,
                            error=str(e)
                        )
                        errors.append({
                            'page': page_num,
                            'strategy': 'text',
                            'error': str(e)
                        })
                        
        except Exception as e:
            logger.error("Text extraction failed", error=str(e))
            errors.append({
                'strategy': 'text',
                'error': str(e)
            })
        
        return trades, errors
    
    async def _parse_page_text(self, page, page_num: int) -> Tuple[List[ParsedTradeRow], List[Dict[str, Any]]]:
        """Parse text from a single PDF page."""
        trades = []
        errors = []
        
        try:
            # Extract text from page
            text = page.extract_text()
            
            if not text:
                return trades, errors
            
            # Parse text using regex patterns
            text_trades = await self._parse_text_patterns(text, page_num)
            trades.extend(text_trades)
            
        except Exception as e:
            errors.append({
                'page': page_num,
                'strategy': 'text',
                'error': str(e)
            })
        
        return trades, errors
    
    async def _parse_text_patterns(self, text: str, page_num: int) -> List[ParsedTradeRow]:
        """Parse trade data from text using regex patterns."""
        trades = []
        
        # Split text into lines for processing
        lines = text.split('\n')
        
        # Try each transaction pattern
        for pattern in self.TRANSACTION_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            
            for match in matches:
                try:
                    trade = self._create_trade_from_match(match, page_num)
                    if trade:
                        trades.append(trade)
                except Exception as e:
                    logger.debug(
                        "Failed to create trade from regex match",
                        page=page_num,
                        error=str(e)
                    )
                    continue
        
        # Also try line-by-line parsing for structured data
        line_trades = await self._parse_structured_lines(lines, page_num)
        trades.extend(line_trades)
        
        return trades
    
    def _create_trade_from_match(self, match, page_num: int) -> Optional[ParsedTradeRow]:
        """Create ParsedTradeRow from regex match."""
        groups = match.groups()
        
        if len(groups) < 4:
            return None
        
        # Map groups to trade fields (pattern-dependent)
        trade_data = {
            'transaction_type': groups[0],
            'asset_name': groups[2] if len(groups) > 2 else '',
            'ticker': groups[1] if len(groups) > 1 else None,
            'transaction_date': groups[3] if len(groups) > 3 else '',
            'amount_range': groups[4] if len(groups) > 4 else ''
        }
        
        # Clean and validate
        if not self._validate_trade_data(trade_data):
            return None
        
        return ParsedTradeRow(
            asset_name=trade_data['asset_name'],
            ticker=trade_data['ticker'],
            transaction_type=trade_data['transaction_type'],
            transaction_date=trade_data['transaction_date'],
            amount_range=trade_data['amount_range'],
            raw_text=match.group(0),
            page_number=page_num,
            extraction_method='regex'
        )
    
    async def _parse_structured_lines(self, lines: List[str], page_num: int) -> List[ParsedTradeRow]:
        """Parse structured data from text lines."""
        trades = []
        
        # Look for lines that contain trade-like data
        for line_num, line in enumerate(lines):
            line = line.strip()
            
            if not line or len(line) < 10:
                continue
            
            # Check if line contains trade indicators
            if not self._line_contains_trade_data(line):
                continue
            
            try:
                trade = await self._parse_trade_line(line, page_num, line_num)
                if trade:
                    trades.append(trade)
            except Exception as e:
                logger.debug(
                    "Failed to parse trade line",
                    page=page_num,
                    line=line_num,
                    error=str(e)
                )
                continue
        
        return trades
    
    def _line_contains_trade_data(self, line: str) -> bool:
        """Check if a line contains trade-like data."""
        line_upper = line.upper()
        
        # Must contain transaction type
        has_transaction = any(word in line_upper for word in ['PURCHASE', 'SALE', 'BUY', 'SELL', 'P', 'S'])
        
        # Must contain amount-like data
        has_amount = any(re.search(pattern, line) for pattern in self.AMOUNT_PATTERNS)
        
        # Must contain date-like data
        has_date = self._is_date_like(line)
        
        return has_transaction and (has_amount or has_date)
    
    async def _parse_trade_line(self, line: str, page_num: int, line_num: int) -> Optional[ParsedTradeRow]:
        """Parse a single line into trade data."""
        # Split line into potential fields
        fields = re.split(r'\s{2,}|\t', line)  # Split on multiple spaces or tabs
        
        if len(fields) < 3:
            # Try comma or pipe separation
            fields = re.split(r'[,|]', line)
        
        if len(fields) < 3:
            return None
        
        # Extract trade data from fields
        trade_data = self._extract_trade_from_row([f.strip() for f in fields])
        
        if not trade_data:
            return None
        
        return ParsedTradeRow(
            asset_name=trade_data.get('asset_name', ''),
            ticker=trade_data.get('ticker'),
            transaction_type=trade_data.get('transaction_type', ''),
            transaction_date=trade_data.get('transaction_date', ''),
            amount_range=trade_data.get('amount_range', ''),
            raw_text=line,
            page_number=page_num,
            extraction_method='line'
        )
    
    def _deduplicate_trades(self, trades: List[ParsedTradeRow]) -> List[ParsedTradeRow]:
        """Remove duplicate trades based on content similarity."""
        if not trades:
            return trades
        
        unique_trades = []
        seen_hashes = set()
        
        for trade in trades:
            # Create a hash based on key fields
            trade_hash = self._compute_trade_hash(trade)
            
            if trade_hash not in seen_hashes:
                seen_hashes.add(trade_hash)
                unique_trades.append(trade)
        
        duplicates_removed = len(trades) - len(unique_trades)
        if duplicates_removed > 0:
            logger.debug(
                "Removed duplicate trades",
                filing_id=self.current_filing_id,
                duplicates=duplicates_removed
            )
            metrics.increment("pdf_parse.duplicates_removed", duplicates_removed)
        
        return unique_trades
    
    def _compute_trade_hash(self, trade: ParsedTradeRow) -> str:
        """Compute hash for trade deduplication."""
        import hashlib
        
        # Use key fields for hash
        hash_input = f"{trade.asset_name}|{trade.ticker}|{trade.transaction_type}|{trade.transaction_date}|{trade.amount_range}"
        return hashlib.md5(hash_input.encode()).hexdigest()
    
    async def validate_parsed_trades(self, trades: List[ParsedTradeRow]) -> Tuple[List[ParsedTradeRow], List[Dict[str, Any]]]:
        """
        Validate parsed trades for data quality.
        
        Args:
            trades: List of parsed trade rows
            
        Returns:
            Tuple of (valid_trades, validation_errors)
        """
        valid_trades = []
        errors = []
        
        for i, trade in enumerate(trades):
            validation_error = self._validate_parsed_trade(trade, i)
            
            if validation_error:
                errors.append(validation_error)
            else:
                valid_trades.append(trade)
        
        logger.info(
            "Parsed trade validation completed",
            filing_id=self.current_filing_id,
            total=len(trades),
            valid=len(valid_trades),
            errors=len(errors)
        )
        
        return valid_trades, errors
    
    def _validate_parsed_trade(self, trade: ParsedTradeRow, index: int) -> Optional[Dict[str, Any]]:
        """Validate a single parsed trade."""
        errors = []
        
        # Required fields
        if not trade.asset_name or len(trade.asset_name.strip()) < 2:
            errors.append("Asset name is required and must be at least 2 characters")
        
        if not trade.transaction_type:
            errors.append("Transaction type is required")
        
        # Data quality checks
        if trade.ticker and not re.match(r'^[A-Z]{1,5}$', trade.ticker.upper()):
            errors.append(f"Invalid ticker format: {trade.ticker}")
        
        if trade.transaction_date and not self._is_date_like(trade.transaction_date):
            errors.append(f"Invalid date format: {trade.transaction_date}")
        
        if trade.amount_range and not self._is_amount_like(trade.amount_range):
            errors.append(f"Invalid amount format: {trade.amount_range}")
        
        if errors:
            return {
                'index': index,
                'trade_data': trade.to_dict(),
                'errors': errors
            }
        
        return None
