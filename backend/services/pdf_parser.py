import re
from typing import List, Dict, Optional
import pdfplumber
from models import Appointment
import logging

logger = logging.getLogger(__name__)

class PracticeFusionParser:
    def __init__(self):
        self.required_columns = ["PATIENT", "TIME", "PROVIDER", "TYPE", "CONFIRMATION"]
    
    def parse_pdf(self, pdf_path: str) -> List[Appointment]:
        appointments = []
        appointment_date = None
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if not text:
                        continue
                    
                    lines = text.split('\n')
                    
                    # Extract the appointment date from header
                    if not appointment_date:
                        for line in lines[:3]:  # Check first 3 lines
                            if "Schedule Confirmation view" in line:
                                # Extract date like "Monday, August, 11, 2025"
                                date_match = re.search(r'Schedule Confirmation view - (.+)', line)
                                if date_match:
                                    appointment_date = date_match.group(1).strip()
                                    logger.info(f"Found appointment date: {appointment_date}")
                                    break
                    
                    page_appointments = self._parse_page_lines(lines, page_num)
                    # Add the date to each appointment
                    for apt in page_appointments:
                        apt.appointment_date = appointment_date
                        logger.info(f"Set appointment date for {apt.patient_name}: {appointment_date}")
                    appointments.extend(page_appointments)
        except Exception as e:
            logger.error(f"Error parsing PDF: {e}")
            raise ValueError(f"Failed to parse PDF: {str(e)}")
        
        return appointments
    
    def _parse_page_lines(self, lines: List[str], page_num: int) -> List[Appointment]:
        appointments = []
        
        # Find header line
        header_idx = None
        for i, line in enumerate(lines):
            if self._is_header_line(line):
                header_idx = i
                break
        
        if header_idx is None:
            return appointments
        
        # Process lines after header
        i = header_idx + 1
        while i < len(lines):
            line = lines[i]
            
            # Skip empty lines and known non-appointment lines
            if not line.strip() or line.strip() == "NOTES" or "https://" in line:
                i += 1
                continue
            
            # Check if this could be an appointment start
            if self._could_be_appointment_start(line):
                # Collect all lines for this appointment
                appointment_lines = [line]
                
                # Look ahead for continuation lines
                j = i + 1
                while j < len(lines):
                    next_line = lines[j]
                    
                    # Stop if we hit an empty line, URL, or another appointment
                    if not next_line.strip() or "https://" in next_line:
                        break
                    
                    # Check if it's another appointment starting
                    if self._could_be_appointment_start(next_line) and self._has_time(next_line):
                        break
                    
                    # Check if it's a continuation (phone, DOB, or confirmation notes)
                    if self._is_continuation_line(next_line):
                        appointment_lines.append(next_line)
                        j += 1
                    else:
                        break
                
                # Try to parse the collected lines as an appointment
                appointment = self._parse_appointment_block(appointment_lines)
                if appointment and appointment.original_confirmation.lower() == "not confirmed":
                    appointments.append(appointment)
                    logger.info(f"Found unconfirmed appointment: {appointment.patient_name} at {appointment.appointment_time}")
                
                i = j
            else:
                i += 1
        
        return appointments
    
    def _is_header_line(self, line: str) -> bool:
        line_upper = line.upper()
        return all(col in line_upper for col in self.required_columns)
    
    def _could_be_appointment_start(self, line: str) -> bool:
        # Check if line has appointment-like content
        has_time = self._has_time(line)
        has_name_start = bool(re.match(r'^[A-Za-z]', line.strip()))
        has_provider = 'Victor Prisk' in line or 'Elizabeth Headlee' in line
        
        return has_time or (has_name_start and (has_provider or len(line) > 20))
    
    def _has_time(self, line: str) -> bool:
        return bool(re.search(r'\d{1,2}:\d{2}\s*[AP]M', line, re.IGNORECASE))
    
    def _is_continuation_line(self, line: str) -> bool:
        # Check if line contains phone, DOB, or confirmation notes
        has_phone = bool(re.search(r'\(\d{3}\)\s*\d{3}-\d{4}', line))
        has_dob = bool(re.search(r'\d{2}/\d{2}/\d{4}', line))
        has_confirmation_note = bool(re.search(r'(Phone|Email):\s*(Automated|Manual)', line, re.IGNORECASE))
        has_timestamp = bool(re.search(r'\d{2}/\d{2}/\d{4}\s*-\s*\d{1,2}:\d{2}\s*[AP]M', line, re.IGNORECASE))
        
        return has_phone or has_dob or has_confirmation_note or has_timestamp
    
    def _parse_appointment_block(self, lines: List[str]) -> Optional[Appointment]:
        try:
            # Combine all lines
            full_text = ' '.join(lines)
            
            # Extract time first (it's the most reliable marker)
            time_match = re.search(r'(\d{1,2}:\d{2}\s*[AP]M)', full_text, re.IGNORECASE)
            if not time_match:
                return None
            
            appointment_time = time_match.group(1)
            
            # Extract phone
            phone_match = re.search(r'\((\d{3})\)\s*(\d{3})-(\d{4})', full_text)
            if not phone_match:
                return None
            
            phone = f"({phone_match.group(1)}) {phone_match.group(2)}-{phone_match.group(3)}"
            
            # Extract confirmation status
            confirm_match = re.search(r'(Not confirmed|Confirmed)', full_text, re.IGNORECASE)
            confirmation_status = confirm_match.group(1) if confirm_match else "Not confirmed"
            
            # Extract provider
            provider_match = re.search(r'(Victor Prisk|Elizabeth Headlee)', full_text)
            provider = provider_match.group(1) if provider_match else "Unknown"
            
            # Extract appointment type
            type_patterns = [
                'Surgery', 'New Patient', 'Follow-Up Visit', 'Established Patient',
                'WC/Auto Follow Up', 'Video Visit', 'Wellness Exam'
            ]
            appointment_type = "Unknown"
            for pattern in type_patterns:
                if re.search(pattern, full_text, re.IGNORECASE):
                    appointment_type = pattern
                    break
            
            # Extract patient name (most complex part)
            # Strategy: Find the time position and take everything before it from the first line
            first_line = lines[0]
            time_pos = first_line.find(time_match.group(1))
            
            if time_pos > 0:
                patient_name = first_line[:time_pos].strip()
            else:
                # Time might be on a different line, look for name pattern
                # Usually name is at the start before any times or providers
                name_match = re.match(r'^([A-Za-z\s\.\-\']+?)(?:\s+\d{1,2}:\d{2}|\s+\()', first_line)
                if name_match:
                    patient_name = name_match.group(1).strip()
                else:
                    # Fallback: take everything before first number or parenthesis
                    name_match = re.match(r'^([A-Za-z\s\.\-\']+)', first_line)
                    patient_name = name_match.group(1).strip() if name_match else "Unknown"
            
            # Clean up patient name
            patient_name = re.sub(r'\s+', ' ', patient_name)  # Remove extra spaces
            patient_name = patient_name.replace('NOTES', '').strip()  # Remove NOTES if it leaked in
            
            # Validate we have minimum required fields
            if patient_name and phone and appointment_time:
                logger.debug(f"Successfully parsed: {patient_name} - {appointment_time} - {confirmation_status}")
                return Appointment(
                    patient_name=patient_name,
                    phone=phone,
                    appointment_time=appointment_time,
                    provider=provider,
                    appointment_type=appointment_type,
                    confirmation_status=confirmation_status
                )
            
        except Exception as e:
            logger.error(f"Error parsing appointment block: {e}")
        
        return None