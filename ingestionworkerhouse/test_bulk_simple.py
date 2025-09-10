#!/usr/bin/env python3
"""Simple test of bulk TXT parsing without full pipeline."""

import asyncio
from pathlib import Path
from src.parser.txt_parser import TXTParser

async def test_simple_parsing():
    """Test TXT parsing with the downloaded file."""
    
    # Check if we have the extracted TXT file
    txt_file = Path("temp_downloads/ptr_bulk_2023_2023FD.txt")
    
    if not txt_file.exists():
        print(f"TXT file not found: {txt_file}")
        return False
    
    print(f"Testing simple TXT parsing with: {txt_file}")
    
    # Read the TXT file
    with open(txt_file, 'rb') as f:
        txt_data = f.read()
    
    # Initialize parser
    parser = TXTParser()
    
    # Parse the file
    print("Parsing TXT file...")
    parsed_filings, errors = await parser.parse_txt_file(
        txt_data, 
        "ptr_bulk_2023", 
        2023
    )
    
    print(f"Parsed {len(parsed_filings)} filings with {len(errors)} errors")
    
    if parsed_filings:
        print("First 3 filings:")
        for i, filing in enumerate(parsed_filings[:3]):
            print(f"  {i+1}. {filing['member_name']} - {filing['filing_type_description']}")
    
    return len(parsed_filings) > 0

if __name__ == "__main__":
    asyncio.run(test_simple_parsing())
