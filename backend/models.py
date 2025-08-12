from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum
import uuid
import asyncio
from database import db_service, get_session

class AppointmentStatus(str, Enum):
    NOT_CONFIRMED = "Not Confirmed"
    CONFIRMED = "Confirmed"
    CANCELLED = "Cancelled"
    DO_NOT_CALL = "Do Not Call"
    CALLING = "Calling"
    VOICEMAIL = "Voicemail/No Answer"
    RESCHEDULING = "Rescheduling"

class CallStatus(str, Enum):
    QUEUED = "queued"
    INITIATED = "initiated"
    RINGING = "ringing"
    IN_PROGRESS = "in-progress"
    COMPLETED = "completed"
    NO_ANSWER = "no-answer"
    BUSY = "busy"
    FAILED = "failed"
    CANCELLED = "cancelled"

class Appointment:
    def __init__(
        self,
        patient_name: str,
        phone: str,
        appointment_time: str,
        provider: str,
        appointment_type: str,
        confirmation_status: str = "Not Confirmed",
        appointment_id: Optional[str] = None
    ):
        self.id = appointment_id or str(uuid.uuid4())
        self.patient_name = patient_name
        self.phone = self._clean_phone(phone)
        self.appointment_time = appointment_time
        self.appointment_date: Optional[str] = None  # Will be set by parser
        self.provider = provider
        self.appointment_type = appointment_type
        self.status = AppointmentStatus.NOT_CONFIRMED
        self.original_confirmation = confirmation_status
        self.call_sid: Optional[str] = None
        self.last_called: Optional[datetime] = None
        self.call_attempts: int = 0
        self.notes: str = ""
        self.last_answered_by: Optional[str] = None
        self.needs_callback: bool = False
    
    def _clean_phone(self, phone: str) -> str:
        cleaned = ''.join(filter(str.isdigit, phone))
        if len(cleaned) == 10:
            cleaned = '1' + cleaned
        return '+' + cleaned if cleaned else ''
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "patient_name": self.patient_name,
            "phone": self.phone,
            "appointment_time": self.appointment_time,
            "appointment_date": self.appointment_date,
            "provider": self.provider,
            "appointment_type": self.appointment_type,
            "status": self.status,
            "original_confirmation": self.original_confirmation,
            "call_sid": self.call_sid,
            "last_called": self.last_called.isoformat() if self.last_called else None,
            "call_attempts": self.call_attempts,
            "notes": self.notes,
            "last_answered_by": self.last_answered_by,
            "needs_callback": self.needs_callback
        }

class AppointmentStore:
    def __init__(self):
        self.appointments: Dict[str, Appointment] = {}
        self.call_to_appointment: Dict[str, str] = {}
    
    def add_appointment(self, appointment: Appointment) -> None:
        self.appointments[appointment.id] = appointment
    
    def get_appointment(self, appointment_id: str) -> Optional[Appointment]:
        return self.appointments.get(appointment_id)
    
    def get_appointment_by_call_sid(self, call_sid: str) -> Optional[Appointment]:
        appointment_id = self.call_to_appointment.get(call_sid)
        if appointment_id:
            return self.appointments.get(appointment_id)
        return None
    
    def update_appointment_status(self, appointment_id: str, status: AppointmentStatus) -> bool:
        if appointment_id in self.appointments:
            self.appointments[appointment_id].status = status
            return True
        return False
    
    def map_call_to_appointment(self, call_sid: str, appointment_id: str) -> None:
        self.call_to_appointment[call_sid] = appointment_id
        if appointment_id in self.appointments:
            self.appointments[appointment_id].call_sid = call_sid
    
    def get_all_appointments(self) -> List[Appointment]:
        return list(self.appointments.values())
    
    def clear_all(self) -> None:
        self.appointments.clear()
        self.call_to_appointment.clear()

appointment_store = AppointmentStore()