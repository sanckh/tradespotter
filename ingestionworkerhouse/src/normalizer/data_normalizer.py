"""Data normalizer for cleaning and standardizing PTR trade data - Updated for existing schema."""

import re
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal
import structlog
from dateutil import parser as date_parser

from ..database.models import ParsedTradeRow, Trade
from ..utils.retry_utils import NonRetryableError

logger = structlog.get_logger()


class DataNormalizer:
    """Normalizes and cleans parsed PTR trade data for existing schema."""
    
    # Transaction type mappings to existing schema
    TRANSACTION_TYPE_MAP = {
        'P': 'Purchase',
        'PURCHASE': 'Purchase',
        'BUY': 'Purchase',
        'BOUGHT': 'Purchase',
        'S': 'Sale',
        'SALE': 'Sale',
        'SELL': 'Sale',
        'SOLD': 'Sale',
        'E': 'Exchange',
        'EXCHANGE': 'Exchange'
    }
    
    # Asset type mappings
    ASSET_TYPE_MAP = {
        'stock': 'Stock',
        'equity': 'Stock',
        'bond': 'Bond',
        'etf': 'ETF',
        'mutual fund': 'Mutual Fund',
        'fund': 'Mutual Fund',
        'option': 'Options',
        'options': 'Options',
        'other': 'Other'
    }
    
    # Standard amount ranges with min/max values
    AMOUNT_RANGES = {
        '$1,001 - $15,000': (1001, 15000),
        '$15,001 - $50,000': (15001, 50000),
        '$50,001 - $100,000': (50001, 100000),
        '$100,001 - $250,000': (100001, 250000),
        '$250,001 - $500,000': (250001, 500000),
        '$500,001 - $1,000,000': (500001, 1000000),
        '$1,000,001 - $5,000,000': (1000001, 5000000),
        '$5,000,001 - $25,000,000': (5000001, 25000000),
        '$25,000,001 - $50,000,000': (25000001, 50000000),
        'Over $50,000,000': (50000001, None)
    }
    
    def __init__(self):
        self.current_filing_id: Optional[str] = None
        
    async def normalize_trades(
        self, 
        parsed_trades: List[ParsedTradeRow], 
        filing_id: str,
        member_id: str,
        disclosure_date: Optional[date] = None
    ) -> Tuple[List[Trade], List[Dict[str, Any]]]:
        """
        Normalize parsed trade data into standardized Trade objects for existing schema.
        
        Args:
            parsed_trades: List of parsed trade rows
            filing_id: Filing identifier
            member_id: Database ID of the congress member (UUID)
            disclosure_date: Date the disclosure was filed
            
        Returns:
            Tuple of (normalized_trades, normalization_errors)
        """
        self.current_filing_id = filing_id
        
        logger.info(
            "Starting trade normalization",
            filing_id=filing_id,
            count=len(parsed_trades)
        )
        
        normalized_trades = []
        errors = []
        
        for i, parsed_trade in enumerate(parsed_trades):
            try:
                normalized_trade = await self._normalize_single_trade(
                    parsed_trade, member_id, filing_id, disclosure_date
                )
                
                if normalized_trade:
                    normalized_trades.append(normalized_trade)
                else:
                    errors.append({
                        'index': i,
                        'error': 'Failed to normalize trade',
                        'raw_data': parsed_trade.to_dict()
                    })
                    
            except Exception as e:
                logger.warning(
                    "Trade normalization failed",
                    filing_id=filing_id,
                    index=i,
                    error=str(e)
                )
                errors.append({
                    'index': i,
                    'error': str(e),
                    'raw_data': parsed_trade.to_dict()
                })
        
        logger.info(
            "Trade normalization completed",
            filing_id=filing_id,
            normalized=len(normalized_trades),
            errors=len(errors)
        )
        
        return normalized_trades, errors
    
    async def _normalize_single_trade(
        self,
        parsed_trade: ParsedTradeRow,
        member_id: str,
        filing_id: str,
        disclosure_date: Optional[date] = None
    ) -> Optional[Trade]:
        """Normalize a single parsed trade row for existing schema."""
        
        # Normalize asset description (required field)
        asset_description = self._normalize_asset_name(parsed_trade.asset_name)
        if not asset_description:
            return None
        
        # Normalize ticker
        ticker = self._normalize_ticker(parsed_trade.ticker)
        
        # Normalize transaction type
        transaction_type = self._normalize_transaction_type(parsed_trade.transaction_type)
        if not transaction_type:
            transaction_type = 'Purchase'  # Default fallback
        
        # Normalize asset type
        asset_type = self._determine_asset_type(asset_description, ticker)
        
        # Normalize transaction date
        transaction_date = self._normalize_date(parsed_trade.transaction_date)
        
        # Normalize amount range and extract min/max
        amount_range = self._normalize_amount_range(parsed_trade.amount_range)
        amount_min, amount_max = self._extract_amount_bounds(amount_range)
        
        # Use disclosure_date or current date as fallback
        if not disclosure_date:
            disclosure_date = date.today()
        
        # Create Trade object for existing schema
        trade = Trade(
            member_id=member_id,
            transaction_date=transaction_date,
            disclosure_date=disclosure_date,
            ticker=ticker,
            asset_description=asset_description,
            asset_type=asset_type,
            transaction_type=transaction_type,
            amount_range=amount_range,
            amount_min=amount_min,
            amount_max=amount_max
        )
        
        # Generate row hash for deduplication
        trade._row_hash = trade.generate_row_hash('house_clerk', filing_id)
        
        return trade
    
    def _normalize_asset_name(self, asset_name: str) -> Optional[str]:
        """Normalize and clean asset description."""
        if not asset_name:
            return None
        
        # Clean up the asset name
        cleaned = str(asset_name).strip()
        
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # Remove common prefixes/suffixes that don't add value
        prefixes_to_remove = [
            r'^(stock of|shares of|equity in)\s+',
            r'^(common stock|preferred stock)\s+',
        ]
        
        for prefix in prefixes_to_remove:
            cleaned = re.sub(prefix, '', cleaned, flags=re.IGNORECASE)
        
        # Capitalize properly
        cleaned = self._title_case_asset_name(cleaned)
        
        # Minimum length check
        if len(cleaned) < 2:
            return None
        
        return cleaned
    
    def _title_case_asset_name(self, name: str) -> str:
        """Apply proper title casing to asset names."""
        # Words that should remain lowercase (unless at start)
        lowercase_words = {
            'and', 'or', 'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through'
        }
        
        words = name.split()
        result = []
        
        for i, word in enumerate(words):
            if i == 0 or word.lower() not in lowercase_words:
                # Capitalize first letter, keep rest as is for acronyms
                if word.isupper() and len(word) > 1:
                    result.append(word)  # Keep acronyms as-is
                else:
                    result.append(word.capitalize())
            else:
                result.append(word.lower())
        
        return ' '.join(result)
    
    def _normalize_ticker(self, ticker: str) -> Optional[str]:
        """Normalize ticker symbol."""
        if not ticker:
            return None
        
        cleaned = str(ticker).strip().upper()
        
        # Remove any non-alphabetic characters
        cleaned = re.sub(r'[^A-Z]', '', cleaned)
        
        # Validate ticker format
        if not re.match(r'^[A-Z]{1,5}$', cleaned):
            return None
        
        return cleaned
    
    def _normalize_transaction_type(self, transaction_type: str) -> Optional[str]:
        """Normalize transaction type to existing schema values."""
        if not transaction_type:
            return None
        
        cleaned = str(transaction_type).strip().upper()
        
        return self.TRANSACTION_TYPE_MAP.get(cleaned)
    
    def _determine_asset_type(self, asset_description: str, ticker: Optional[str]) -> str:
        """Determine asset type from description and ticker."""
        if not asset_description:
            return 'Other'
        
        desc_lower = asset_description.lower()
        
        # Check for specific asset type indicators
        for keyword, asset_type in self.ASSET_TYPE_MAP.items():
            if keyword in desc_lower:
                return asset_type
        
        # If has ticker, likely a stock
        if ticker:
            return 'Stock'
        
        # Check for bond indicators
        if any(word in desc_lower for word in ['bond', 'treasury', 'note', 'bill']):
            return 'Bond'
        
        # Check for fund indicators
        if any(word in desc_lower for word in ['fund', 'etf', 'trust']):
            if 'etf' in desc_lower or 'exchange traded' in desc_lower:
                return 'ETF'
            return 'Mutual Fund'
        
        # Default to Stock if uncertain
        return 'Stock'
    
    def _normalize_date(self, date_str: str) -> Optional[date]:
        """Normalize transaction date string to date object."""
        if not date_str:
            return None
        
        cleaned = str(date_str).strip()
        
        # Common date formats in PTR filings
        date_patterns = [
            r'(\d{1,2})/(\d{1,2})/(\d{4})',  # MM/DD/YYYY
            r'(\d{1,2})/(\d{1,2})/(\d{2})',  # MM/DD/YY
            r'(\d{4})-(\d{1,2})-(\d{1,2})',  # YYYY-MM-DD
            r'(\d{1,2})-(\d{1,2})-(\d{4})',  # MM-DD-YYYY
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, cleaned)
            if match:
                try:
                    if len(match.group(3)) == 2:  # 2-digit year
                        year = int(match.group(3))
                        if year < 50:
                            year += 2000
                        else:
                            year += 1900
                        month = int(match.group(1))
                        day = int(match.group(2))
                    else:  # 4-digit year
                        if pattern.startswith(r'(\d{4})'):  # YYYY-MM-DD
                            year = int(match.group(1))
                            month = int(match.group(2))
                            day = int(match.group(3))
                        else:  # MM/DD/YYYY or MM-DD-YYYY
                            month = int(match.group(1))
                            day = int(match.group(2))
                            year = int(match.group(3))
                    
                    return date(year, month, day)
                    
                except (ValueError, IndexError):
                    continue
        
        # Try using dateutil parser as fallback
        try:
            parsed_date = date_parser.parse(cleaned, fuzzy=True)
            return parsed_date.date()
        except (ValueError, TypeError):
            pass
        
        logger.warning(
            "Failed to parse date",
            filing_id=self.current_filing_id,
            date_string=cleaned
        )
        return None
    
    def _normalize_amount_range(self, amount_str: str) -> Optional[str]:
        """Normalize amount range to standard format."""
        if not amount_str:
            return None
        
        cleaned = str(amount_str).strip()
        
        # Remove extra whitespace and normalize separators
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = re.sub(r'\s*-\s*', ' - ', cleaned)
        
        # Try to match against standard ranges
        for standard_range in self.AMOUNT_RANGES.keys():
            if self._ranges_match(cleaned, standard_range):
                return standard_range
        
        # If no exact match, try to extract and standardize the range
        return self._standardize_amount_range(cleaned)
    
    def _ranges_match(self, input_range: str, standard_range: str) -> bool:
        """Check if an input range matches a standard range."""
        # Extract numbers from both ranges
        input_numbers = re.findall(r'[\d,]+', input_range)
        standard_numbers = re.findall(r'[\d,]+', standard_range)
        
        if len(input_numbers) != len(standard_numbers):
            return False
        
        # Compare the numeric values
        try:
            for inp, std in zip(input_numbers, standard_numbers):
                inp_val = int(inp.replace(',', ''))
                std_val = int(std.replace(',', ''))
                if inp_val != std_val:
                    return False
            return True
        except ValueError:
            return False
    
    def _standardize_amount_range(self, amount_str: str) -> Optional[str]:
        """Attempt to standardize a non-standard amount range."""
        # Extract dollar amounts
        amounts = re.findall(r'\$?[\d,]+', amount_str)
        
        if len(amounts) == 2:
            try:
                # Parse the amounts
                low = int(amounts[0].replace('$', '').replace(',', ''))
                high = int(amounts[1].replace('$', '').replace(',', ''))
                
                # Format in standard way
                low_formatted = f"${low:,}"
                high_formatted = f"${high:,}"
                
                return f"{low_formatted} - {high_formatted}"
                
            except ValueError:
                pass
        elif len(amounts) == 1:
            # Single amount - might be "Over $X" format
            if 'over' in amount_str.lower():
                try:
                    amount = int(amounts[0].replace('$', '').replace(',', ''))
                    return f"Over ${amount:,}"
                except ValueError:
                    pass
        
        # Return original if we can't standardize
        return amount_str
    
    def _extract_amount_bounds(self, amount_range: str) -> Tuple[Optional[Decimal], Optional[Decimal]]:
        """Extract min and max amounts from range string."""
        if not amount_range:
            return None, None
        
        # Check if it's a standard range
        if amount_range in self.AMOUNT_RANGES:
            min_val, max_val = self.AMOUNT_RANGES[amount_range]
            return (Decimal(str(min_val)) if min_val else None, 
                    Decimal(str(max_val)) if max_val else None)
        
        # Try to extract from custom range
        amounts = re.findall(r'[\d,]+', amount_range)
        
        if len(amounts) >= 2:
            try:
                min_val = Decimal(amounts[0].replace(',', ''))
                max_val = Decimal(amounts[1].replace(',', ''))
                return min_val, max_val
            except (ValueError, IndexError):
                pass
        elif len(amounts) == 1:
            try:
                if 'over' in amount_range.lower():
                    min_val = Decimal(amounts[0].replace(',', ''))
                    return min_val, None
                else:
                    # Single amount, treat as exact
                    val = Decimal(amounts[0].replace(',', ''))
                    return val, val
            except ValueError:
                pass
        
        return None, None
    
    def validate_normalized_trades(self, trades: List[Trade]) -> Tuple[List[Trade], List[Dict[str, Any]]]:
        """
        Final validation of normalized trades for existing schema.
        
        Args:
            trades: List of normalized Trade objects
            
        Returns:
            Tuple of (valid_trades, validation_errors)
        """
        valid_trades = []
        errors = []
        
        for i, trade in enumerate(trades):
            validation_error = self._validate_normalized_trade(trade, i)
            
            if validation_error:
                errors.append(validation_error)
            else:
                valid_trades.append(trade)
        
        logger.info(
            "Normalized trade validation completed",
            filing_id=self.current_filing_id,
            total=len(trades),
            valid=len(valid_trades),
            errors=len(errors)
        )
        
        return valid_trades, errors
    
    def _validate_normalized_trade(self, trade: Trade, index: int) -> Optional[Dict[str, Any]]:
        """Validate a single normalized trade against existing schema."""
        errors = []
        
        # Required fields
        if not trade.asset_description:
            errors.append("Asset description is required")
        
        if not trade.member_id:
            errors.append("Member ID is required")
        
        # Validate asset type
        valid_asset_types = ['Stock', 'Bond', 'ETF', 'Mutual Fund', 'Options', 'Other']
        if trade.asset_type not in valid_asset_types:
            errors.append(f"Invalid asset type: {trade.asset_type}")
        
        # Validate transaction type
        valid_transaction_types = ['Purchase', 'Sale', 'Exchange']
        if trade.transaction_type not in valid_transaction_types:
            errors.append(f"Invalid transaction type: {trade.transaction_type}")
        
        # Data quality checks
        if trade.ticker and not re.match(r'^[A-Z]{1,5}$', trade.ticker):
            errors.append(f"Invalid ticker format: {trade.ticker}")
        
        if trade.transaction_date:
            # Check if date is reasonable (not too far in future/past)
            current_year = datetime.now().year
            trade_year = trade.transaction_date.year
            
            if trade_year < 1990 or trade_year > current_year + 1:
                errors.append(f"Transaction date seems unreasonable: {trade.transaction_date}")
        
        if errors:
            return {
                'index': index,
                'trade_data': trade.to_dict(),
                'errors': errors
            }
        
        return None
