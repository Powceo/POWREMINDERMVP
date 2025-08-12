import pdfplumber
import re
import os

def analyze_pdf_structure(pdf_path):
    print(f"\n=== Analyzing PDF Structure: {pdf_path} ===\n")
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                print(f"\n--- Page {page_num} ---")
                
                text = page.extract_text()
                if not text:
                    print("No text extracted")
                    continue
                
                lines = text.split('\n')
                print(f"Total lines: {len(lines)}\n")
                
                # Find header line
                header_idx = None
                for i, line in enumerate(lines):
                    if 'PATIENT' in line and 'TIME' in line and 'CONFIRMATION' in line:
                        header_idx = i
                        print(f"HEADER at line {i}: {line}\n")
                        break
                
                if header_idx is None:
                    print("No header found")
                    continue
                
                # Analyze each potential appointment block
                print("APPOINTMENT BLOCKS:\n")
                print("-" * 80)
                
                i = header_idx + 1
                block_num = 0
                
                while i < len(lines):
                    line = lines[i]
                    
                    # Skip empty lines
                    if not line.strip():
                        i += 1
                        continue
                    
                    # Check if this looks like an appointment start
                    has_time = bool(re.search(r'\d{1,2}:\d{2}\s*[AP]M', line, re.IGNORECASE))
                    has_name_pattern = bool(re.match(r'^[A-Za-z]', line))  # Starts with letter
                    
                    if has_time or (has_name_pattern and i > header_idx):
                        block_num += 1
                        print(f"\nBLOCK {block_num}:")
                        
                        # Collect lines for this appointment
                        block_lines = [line]
                        
                        # Check next lines for continuation
                        j = i + 1
                        while j < len(lines):
                            next_line = lines[j]
                            
                            # Stop if we hit another appointment or empty line
                            if not next_line.strip():
                                break
                            if re.search(r'\d{1,2}:\d{2}\s*[AP]M', next_line) and j > i:
                                break
                            if 'https://' in next_line:
                                break
                            
                            # Check if it's a continuation (has phone, DOB, or confirmation notes)
                            has_phone = bool(re.search(r'\(\d{3}\)\s*\d{3}-\d{4}', next_line))
                            has_dob = bool(re.search(r'\d{2}/\d{2}/\d{4}', next_line))
                            has_confirmation_note = 'Phone:' in next_line or 'Email:' in next_line
                            
                            if has_phone or has_dob or has_confirmation_note:
                                block_lines.append(next_line)
                                j += 1
                            else:
                                # Check if it might be a name continuation
                                if re.match(r'^[A-Z][a-z]', next_line) and len(next_line) < 50:
                                    block_lines.append(next_line)
                                    j += 1
                                else:
                                    break
                        
                        # Display the block
                        for idx, bl in enumerate(block_lines):
                            print(f"  Line {idx+1}: {bl}")
                        
                        # Parse the block
                        full_text = ' '.join(block_lines)
                        print(f"\n  Combined: {full_text}")
                        
                        # Extract key fields
                        time_match = re.search(r'(\d{1,2}:\d{2}\s*[AP]M)', full_text, re.IGNORECASE)
                        phone_match = re.search(r'\((\d{3})\)\s*(\d{3})-(\d{4})', full_text)
                        confirm_match = re.search(r'(Not confirmed|Confirmed)', full_text, re.IGNORECASE)
                        
                        print(f"\n  Extracted:")
                        print(f"    Time: {time_match.group(1) if time_match else 'NOT FOUND'}")
                        print(f"    Phone: {phone_match.group(0) if phone_match else 'NOT FOUND'}")
                        print(f"    Status: {confirm_match.group(1) if confirm_match else 'NOT FOUND'}")
                        
                        # Extract patient name (tricky part)
                        if time_match:
                            time_pos = full_text.find(time_match.group(1))
                            name_part = full_text[:time_pos].strip()
                            # Remove any headers that leaked in
                            name_part = re.sub(r'(NOTES|CONFIRMATION|UPDATED).*', '', name_part).strip()
                            print(f"    Name: {name_part if name_part else 'NOT FOUND'}")
                        
                        print("-" * 80)
                        
                        i = j
                    else:
                        i += 1
                        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Test both PDFs
    pdfs = [
        r"C:\Users\VictorPrisk\pow-reminder-mvp\samples\pf_schedule_sample.pdf",
        r"C:\Users\VictorPrisk\pow-reminder-mvp\samples\Confirmation2.pdf"
    ]
    
    for pdf_path in pdfs:
        if os.path.exists(pdf_path):
            analyze_pdf_structure(pdf_path)
        else:
            print(f"File not found: {pdf_path}")