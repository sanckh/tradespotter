#!/usr/bin/env python3
"""Test script to verify StateDst parsing logic."""

import asyncio
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.parser.txt_parser import TXTParser

async def test_state_district_parsing():
    """Test the state/district parsing with sample data."""
    
    parser = TXTParser()
    
    # Test cases from the sample data
    test_cases = [
        ("MI13", "MI", "13"),
        ("OR05", "OR", "5"),
        ("TX31", "TX", "31"),
        ("OH15", "OH", "15"),
        ("NC12", "NC", "12"),
        ("FL07", "FL", "7"),
        ("SC02", "SC", "2"),
        ("IL09", "IL", "9"),
        ("CA53", "CA", "53"),
        ("", None, None),
        ("XX", "XX", None),  # State only
        ("AB123", "AB", "123"),  # Non-standard district
    ]
    
    print("Testing StateDst parsing:")
    print("=" * 50)
    
    all_passed = True
    
    for state_district, expected_state, expected_district in test_cases:
        state, district = parser._parse_state_district(state_district)
        
        passed = state == expected_state and district == expected_district
        status = "✓ PASS" if passed else "✗ FAIL"
        
        print(f"{status} | Input: '{state_district}' -> State: '{state}', District: '{district}'")
        
        if not passed:
            print(f"      Expected: State: '{expected_state}', District: '{expected_district}'")
            all_passed = False
    
    print("=" * 50)
    print(f"Overall result: {'All tests passed!' if all_passed else 'Some tests failed!'}")
    
    return all_passed

async def test_full_row_parsing():
    """Test parsing a full row from the sample data."""
    
    parser = TXTParser()
    
    # Sample row from the PTR data
    sample_row = {
        'Prefix': '',
        'Last': 'Hollier',
        'First': 'Adam Jacques Chester Lafayette',
        'Suffix': '',
        'FilingType': 'C',
        'StateDst': 'MI13',
        'Year': '2023',
        'FilingDate': '2/14/2024',
        'DocID': '10056211'
    }
    
    print("\nTesting full row parsing:")
    print("=" * 50)
    
    try:
        parsed = await parser._parse_filing_row(sample_row, 1, 2023)
        
        if parsed:
            print("✓ Row parsed successfully!")
            print(f"  Member Name: {parsed['member_name']}")
            print(f"  State: {parsed['state']}")
            print(f"  District: {parsed['district']}")
            print(f"  Doc ID: {parsed['doc_id']}")
            print(f"  Filing Type: {parsed['filing_type_description']}")
            
            # Verify state/district parsing
            if parsed['state'] == 'MI' and parsed['district'] == '13':
                print("✓ State/District parsing correct!")
                return True
            else:
                print(f"✗ State/District parsing incorrect: {parsed['state']}/{parsed['district']}")
                return False
        else:
            print("✗ Row parsing failed - returned None")
            return False
            
    except Exception as e:
        print(f"✗ Row parsing failed with error: {e}")
        return False

async def main():
    """Run all tests."""
    
    print("PTR StateDst Parsing Test Suite")
    print("=" * 60)
    
    # Test individual parsing function
    test1_passed = await test_state_district_parsing()
    
    # Test full row parsing
    test2_passed = await test_full_row_parsing()
    
    print("\n" + "=" * 60)
    if test1_passed and test2_passed:
        print("🎉 All tests passed! StateDst parsing is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
