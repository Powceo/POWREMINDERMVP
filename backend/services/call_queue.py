import logging
from typing import List, Optional, Dict

from models import appointment_store, Appointment, AppointmentStatus
from settings import settings
from twilio.rest import Client
from services.twilio_client import TwilioService


logger = logging.getLogger(__name__)


class CallQueue:
    def __init__(self) -> None:
        self._queue: List[str] = []
        self._override_window: bool = False
        self._current_call_sid: Optional[str] = None
        self._current_appointment_id: Optional[str] = None
        self._active: bool = False
        self._cancelled: bool = False
        self._done: List[str] = []
        self._errors: Dict[str, str] = {}

    def start_batch(self, appointment_ids: List[str], override_window: bool = False) -> Dict:
        # Filter out invalid or non-callable appointments
        valid_ids: List[str] = []
        for apt_id in appointment_ids:
            apt = appointment_store.get_appointment(apt_id)
            if not apt:
                continue
            if apt.status in [
                AppointmentStatus.CONFIRMED,
                AppointmentStatus.CANCELLED,
                AppointmentStatus.DO_NOT_CALL,
                AppointmentStatus.CALLING,
            ]:
                continue
            valid_ids.append(apt_id)

        self._queue = valid_ids
        self._override_window = override_window
        self._done = []
        self._errors = {}
        self._cancelled = False
        self._active = len(self._queue) > 0
        self._current_call_sid = None
        self._current_appointment_id = None

        logger.info(f"CallQueue: starting batch with {len(self._queue)} appointments; override={override_window}")
        if self._active:
            self._start_next()

        return self.get_status()

    def get_status(self) -> Dict:
        return {
            "active": self._active,
            "cancelled": self._cancelled,
            "current_appointment_id": self._current_appointment_id,
            "queued_count": len(self._queue),
            "done_count": len(self._done),
            "error_count": len(self._errors),
            "errors": self._errors,
        }

    def cancel(self) -> Dict:
        self._cancelled = True
        self._queue.clear()
        logger.info("CallQueue: batch cancelled")
        return self.get_status()

    def on_call_finished(self, call_sid: str) -> None:
        if not self._active:
            return
        if self._current_call_sid != call_sid:
            return
        # Mark done and advance
        if self._current_appointment_id:
            self._done.append(self._current_appointment_id)
        self._current_call_sid = None
        self._current_appointment_id = None
        self._start_next()

    def _start_next(self) -> None:
        if self._cancelled:
            self._active = False
            return
        if not self._queue:
            logger.info("CallQueue: batch complete")
            self._active = False
            return
        next_id = self._queue.pop(0)
        apt: Optional[Appointment] = appointment_store.get_appointment(next_id)
        if not apt:
            self._errors[next_id] = "Appointment not found"
            self._start_next()
            return
        logger.info(f"CallQueue: calling appointment {next_id} for {apt.patient_name}")
        try:
            # Create a fresh TwilioService (avoids circular import at module level)
            service = TwilioService()
            call_sid = service.make_call(apt, override_window=self._override_window)
            if not call_sid:
                self._errors[next_id] = "Failed to initiate call"
                self._start_next()
                return
            self._current_call_sid = call_sid
            self._current_appointment_id = next_id
        except Exception as e:
            self._errors[next_id] = str(e)
            self._start_next()


call_queue = CallQueue()


