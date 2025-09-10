#!/usr/bin/env python3
"""Examine TXT vs XML formats from PTR zip files to decide which to parse."""

import requests
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

def examine_ptr_formats():
    """Download and examine both TXT and XML formats from a PTR zip file."""
    
    # Use 2023 as it should be complete and stable
    test_url = "https://disclosures-clerk.house.gov/public_disc/financial-pdfs/2023FD.zip"
    
    print(f"Downloading and examining PTR formats from: {test_url}")
    
    try:
        # Download the zip file
        response = requests.get(test_url)
        response.raise_for_status()
        
        # Save to temp file
        temp_zip = Path("temp_format_analysis.zip")
        
        with open(temp_zip, 'wb') as f:
            f.write(response.content)
        
        # Extract and examine both formats
        with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
            file_list = zip_ref.namelist()
            print(f"Files in zip: {file_list}")
            
            txt_file = None
            xml_file = None
            
            # Find TXT and XML files
            for filename in file_list:
                if filename.endswith('.txt'):
                    txt_file = filename
                elif filename.endswith('.xml'):
                    xml_file = filename
            
            print(f"\nTXT file: {txt_file}")
            print(f"XML file: {xml_file}")
            
            # Examine TXT format
            if txt_file:
                print(f"\n{'='*60}")
                print("TXT FORMAT ANALYSIS")
                print('='*60)
                
                txt_content = zip_ref.read(txt_file).decode('utf-8', errors='ignore')
                txt_lines = txt_content.split('\n')
                
                print(f"Total lines: {len(txt_lines)}")
                print(f"File size: {len(txt_content):,} characters")
                
                print(f"\nFirst 20 lines:")
                for i, line in enumerate(txt_lines[:20]):
                    print(f"{i+1:3d}: {line}")
                
                print(f"\nLast 10 lines:")
                for i, line in enumerate(txt_lines[-10:], len(txt_lines)-10):
                    print(f"{i+1:3d}: {line}")
                
                # Look for patterns
                print(f"\nPattern analysis:")
                tab_separated = sum(1 for line in txt_lines if '\t' in line)
                comma_separated = sum(1 for line in txt_lines if ',' in line)
                pipe_separated = sum(1 for line in txt_lines if '|' in line)
                
                print(f"Lines with tabs: {tab_separated}")
                print(f"Lines with commas: {comma_separated}")
                print(f"Lines with pipes: {pipe_separated}")
                
                # Sample a few middle lines to see structure
                print(f"\nSample middle lines (around line {len(txt_lines)//2}):")
                start_idx = max(0, len(txt_lines)//2 - 3)
                end_idx = min(len(txt_lines), len(txt_lines)//2 + 3)
                for i in range(start_idx, end_idx):
                    if i < len(txt_lines):
                        print(f"{i+1:3d}: {txt_lines[i]}")
            
            # Examine XML format
            if xml_file:
                print(f"\n{'='*60}")
                print("XML FORMAT ANALYSIS")
                print('='*60)
                
                xml_content = zip_ref.read(xml_file).decode('utf-8', errors='ignore')
                
                print(f"File size: {len(xml_content):,} characters")
                
                try:
                    # Parse XML
                    root = ET.fromstring(xml_content)
                    
                    print(f"Root element: {root.tag}")
                    print(f"Root attributes: {root.attrib}")
                    
                    # Count child elements
                    children = list(root)
                    print(f"Direct children: {len(children)}")
                    
                    if children:
                        print(f"\nChild element types:")
                        child_types = {}
                        for child in children:
                            child_types[child.tag] = child_types.get(child.tag, 0) + 1
                        
                        for tag, count in child_types.items():
                            print(f"  {tag}: {count}")
                        
                        # Examine first few children
                        print(f"\nFirst 3 child elements:")
                        for i, child in enumerate(children[:3]):
                            print(f"  {i+1}. {child.tag}")
                            print(f"     Attributes: {child.attrib}")
                            if child.text and child.text.strip():
                                print(f"     Text: {child.text.strip()[:100]}...")
                            
                            # Show child's children
                            grandchildren = list(child)
                            if grandchildren:
                                print(f"     Sub-elements: {[gc.tag for gc in grandchildren[:5]]}")
                    
                    # Show raw XML structure (first 1000 chars)
                    print(f"\nRaw XML structure (first 1000 chars):")
                    print(xml_content[:1000])
                    
                except ET.ParseError as e:
                    print(f"XML parsing error: {e}")
                    print(f"Raw XML content (first 1000 chars):")
                    print(xml_content[:1000])
        
        # Clean up
        temp_zip.unlink()
        
        print(f"\n{'='*60}")
        print("FORMAT COMPARISON SUMMARY")
        print('='*60)
        print("TXT Format:")
        print("  + Simple text format, easy to parse with basic string operations")
        print("  + Smaller file size typically")
        print("  - May require custom parsing logic")
        print("  - Less structured, harder to validate")
        
        print("\nXML Format:")
        print("  + Structured data with validation")
        print("  + Standard parsing libraries available")
        print("  + Self-documenting with element names")
        print("  - Larger file size")
        print("  - More complex parsing")
        
        print(f"\nRecommendation will depend on the actual structure observed above.")
        
        return True
        
    except Exception as e:
        print(f"Error during format analysis: {e}")
        return False

if __name__ == "__main__":
    success = examine_ptr_formats()
    print(f"\nAnalysis {'completed' if success else 'failed'}")
