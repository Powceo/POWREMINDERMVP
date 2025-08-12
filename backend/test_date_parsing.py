import pdfplumber
import re

def test_date_extraction(pdf_path):
    print(f"\nTesting date extraction from: {pdf_path}\n")
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text()
            if not text:
                continue
            
            lines = text.split('\n')
            
            print(f"=== Page {page_num} ===")
            print("First 5 lines:")
            for i, line in enumerate(lines[:5], 1):
                print(f"  {i}: {line}")
            
            # Look for the Schedule Confirmation view line
            appointment_date = None
            for line in lines[:5]:  # Check first 5 lines
                if "Schedule Confirmation view" in line:
                    print(f"\nFound header line: {line}")
                    # Extract date like "Monday, August, 11, 2025"
                    date_match = re.search(r'Schedule Confirmation view - (.+)', line)
                    if date_match:
                        appointment_date = date_match.group(1).strip()
                        print(f"Extracted date: {appointment_date}")
                    break
            
            if not appointment_date:
                print("No date found in header!")
            
            break  # Just check first page

if __name__ == "__main__":
    import os
    
    # Test with the sample PDFs
    pdfs = [
        r"C:\Users\VictorPrisk\pow-reminder-mvp\samples\pf_schedule_sample.pdf",
        r"C:\Users\VictorPrisk\pow-reminder-mvp\samples\Confirmation2.pdf"
    ]
    
    for pdf_path in pdfs:
        if os.path.exists(pdf_path):
            test_date_extraction(pdf_path)
        else:
            print(f"File not found: {pdf_path}")