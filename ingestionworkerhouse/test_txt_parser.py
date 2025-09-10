#!/usr/bin/env python3
"""Test script for the new TXT parser."""

import asyncio
from pathlib import Path
from src.parser.txt_parser import TXTParser, BulkTXTParser

async def test_txt_parser():
    """Test the TXT parser with the downloaded file."""
    
    # Check if we have the extracted TXT file
    txt_file = Path("temp_downloads/ptr_bulk_2023_2023FD.txt")
    
    if not txt_file.exists():
        print(f"TXT file not found: {txt_file}")
        print("Please run 'python -m src.main --mode download --limit 1' first")
        return False
    
    print(f"Testing TXT parser with: {txt_file}")
    print(f"File size: {txt_file.stat().st_size:,} bytes")
    
    # Read the TXT file
    with open(txt_file, 'rb') as f:
        txt_data = f.read()
    
    # Initialize parser
    parser = TXTParser()
    
    # Parse the file
    print("\nParsing TXT file...")
    parsed_filings, errors = await parser.parse_txt_file(
        txt_data, 
        "ptr_bulk_2023", 
        2023
    )
    
    # Display results
    print(f"\n{'='*60}")
    print("PARSING RESULTS")
    print('='*60)
    print(f"Total filings parsed: {len(parsed_filings)}")
    print(f"Parsing errors: {len(errors)}")
    
    if errors:
        print(f"\nFirst 3 errors:")
        for i, error in enumerate(errors[:3]):
            print(f"  {i+1}. Row {error.get('row_number', 'N/A')}: {error.get('error', 'Unknown error')}")
    
    if parsed_filings:
        print(f"\nFirst 5 parsed filings:")
        for i, filing in enumerate(parsed_filings[:5]):
            print(f"  {i+1}. {filing['member_name']} ({filing['filing_type']}) - {filing['doc_id']}")
            print(f"     State/District: {filing['state_district']}, Date: {filing['filing_date']}")
        
        print(f"\nFiling type breakdown:")
        filing_types = {}
        for filing in parsed_filings:
            ft = filing['filing_type_description']
            filing_types[ft] = filing_types.get(ft, 0) + 1
        
        for ft, count in sorted(filing_types.items()):
            print(f"  {ft}: {count}")
        
        print(f"\nSample parsed filing (full details):")
        sample = parsed_filings[0]
        for key, value in sample.items():
            print(f"  {key}: {value}")
    
    print(f"\n{'='*60}")
    
    return len(parsed_filings) > 0

async def test_bulk_parser():
    """Test the bulk parser with extracted files."""
    
    # Simulate extracted files metadata (like from ZipDownloader)
    extracted_files = [
        {
            'file_path': 'temp_downloads/ptr_bulk_2023_2023FD.txt',
            'file_type': 'txt',
            'filing_id': 'ptr_bulk_2023',
            'year': 2023,
            'size': Path('temp_downloads/ptr_bulk_2023_2023FD.txt').stat().st_size if Path('temp_downloads/ptr_bulk_2023_2023FD.txt').exists() else 0
        },
        {
            'file_path': 'temp_downloads/ptr_bulk_2023_2023FD.xml',
            'file_type': 'xml',
            'filing_id': 'ptr_bulk_2023',
            'year': 2023,
            'size': Path('temp_downloads/ptr_bulk_2023_2023FD.xml').stat().st_size if Path('temp_downloads/ptr_bulk_2023_2023FD.xml').exists() else 0
        }
    ]
    
    print(f"\n{'='*60}")
    print("TESTING BULK PARSER")
    print('='*60)
    
    bulk_parser = BulkTXTParser()
    
    all_filings, all_errors = await bulk_parser.parse_bulk_files(extracted_files)
    
    print(f"Bulk parsing results:")
    print(f"  Total filings: {len(all_filings)}")
    print(f"  Total errors: {len(all_errors)}")
    
    return len(all_filings) > 0

async def main():
    """Run all tests."""
    print("PTR TXT Parser Test")
    print("=" * 60)
    
    # Test individual parser
    success1 = await test_txt_parser()
    
    # Test bulk parser
    success2 = await test_bulk_parser()
    
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print('='*60)
    print(f"TXT Parser: {'✓ PASSED' if success1 else '✗ FAILED'}")
    print(f"Bulk Parser: {'✓ PASSED' if success2 else '✗ FAILED'}")
    print(f"Overall: {'✓ ALL TESTS PASSED' if success1 and success2 else '✗ SOME TESTS FAILED'}")

if __name__ == "__main__":
    asyncio.run(main())
