import pdfplumber
import sys
import os

def debug_pdf(pdf_path):
    print(f"\n=== Debugging PDF: {pdf_path} ===\n")
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                print(f"\n--- Page {page_num} ---")
                
                # Extract raw text
                text = page.extract_text()
                if text:
                    print("RAW TEXT (first 2000 chars):")
                    print(text[:2000])
                    print("\n" + "="*50)
                    
                    # Show lines
                    lines = text.split('\n')
                    print(f"\nTOTAL LINES: {len(lines)}")
                    print("\nFIRST 20 LINES:")
                    for i, line in enumerate(lines[:20], 1):
                        print(f"{i:3}: {line}")
                    
                    # Look for key patterns
                    print("\n" + "="*50)
                    print("PATTERN SEARCH:")
                    
                    # Check for headers
                    for line in lines:
                        if 'PATIENT' in line.upper() and 'CONFIRMATION' in line.upper():
                            print(f"HEADER FOUND: {line}")
                            break
                    
                    # Check for "Not confirmed"
                    not_confirmed_count = 0
                    for i, line in enumerate(lines):
                        if 'not confirmed' in line.lower():
                            not_confirmed_count += 1
                            print(f"'Not confirmed' found on line {i+1}: {line}")
                            # Show context
                            if i > 0:
                                print(f"  Previous line: {lines[i-1]}")
                            if i < len(lines) - 1:
                                print(f"  Next line: {lines[i+1]}")
                    
                    print(f"\nTotal 'Not confirmed' occurrences: {not_confirmed_count}")
                    
                    # Look for phone patterns
                    import re
                    phone_pattern = r'\(\d{3}\)\s*\d{3}-\d{4}'
                    phones_found = re.findall(phone_pattern, text)
                    print(f"\nPhone numbers found: {phones_found[:5]}")  # First 5
                    
                    # Look for time patterns
                    time_pattern = r'\d{1,2}:\d{2}\s*[AP]M'
                    times_found = re.findall(time_pattern, text, re.IGNORECASE)
                    print(f"Times found: {times_found[:5]}")  # First 5
                    
                else:
                    print("No text extracted from this page")
                    
    except Exception as e:
        print(f"Error reading PDF: {e}")

if __name__ == "__main__":
    # Test with the uploaded PDF
    pdf_path = "../uploads/confirmation2.pdf"
    
    if not os.path.exists(pdf_path):
        pdf_path = "uploads/confirmation2.pdf"
    
    if not os.path.exists(pdf_path):
        print("Please provide the path to confirmation2.pdf")
        pdf_path = input("Enter PDF path: ").strip()
    
    if os.path.exists(pdf_path):
        debug_pdf(pdf_path)
    else:
        print(f"File not found: {pdf_path}")