from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather, Dial
from typing import Optional, Dict
import logging
from settings import settings
from models import Appointment, AppointmentStatus, appointment_store

logger = logging.getLogger(__name__)

class TwilioService:
    def __init__(self):
        if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
            self.client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        else:
            self.client = None
            logger.warning("Twilio credentials not configured")
    
    def make_call(self, appointment: Appointment, override_window: bool = False) -> Optional[str]:
        if not self.client:
            logger.error("Twilio client not initialized")
            return None
        
        # Call window restriction removed per practice workflow
        
        try:
            # Check if we have a valid PUBLIC webhook URL
            has_valid_webhook = settings.BASE_URL and not any(
                bad in settings.BASE_URL for bad in ["localhost", "127.0.0.1", "192.168."]
            )
            
            if has_valid_webhook:
                logger.info(f"Using webhook mode with BASE_URL: {settings.BASE_URL}")
                # Use webhooks if we have a valid URL
                extra = {}
                if getattr(settings, 'AMD_MODE', 'none') != 'none':
                    extra["machine_detection"] = (
                        "Enable" if settings.AMD_MODE == "enable" else "DetectMessageEnd"
                    )
                    extra["machine_detection_timeout"] = 30
                    # Only use async AMD for simple detection; for DetectMessageEnd we want synchronous
                    if settings.AMD_MODE == "enable":
                        extra["async_amd"] = True
                call = self.client.calls.create(
                    to=appointment.phone,
                    from_=settings.TWILIO_FROM_NUMBER,
                    url=f"{settings.BASE_URL}/twilio/voice",
                    status_callback=f"{settings.BASE_URL}/twilio/status",
                    status_callback_event=['initiated', 'ringing', 'answered', 'completed'],
                    status_callback_method='POST',
                    **extra
                )
            else:
                logger.info(f"Using inline TwiML mode (no webhooks) - BASE_URL: {settings.BASE_URL}")
                # Use inline TwiML (no webhooks needed!)
                response = VoiceResponse()
                if getattr(settings, 'TTS_INITIAL_PAUSE', 0):
                    response.pause(length=int(settings.TTS_INITIAL_PAUSE))
                
                # Include appointment details in inline TwiML
                patient_first_name = appointment.patient_name.split()[0] if appointment.patient_name else "patient"
                date_str = appointment.appointment_date if appointment.appointment_date else "your appointment"
                time_str = appointment.appointment_time
                
                greeting = (
                    f"This is Prisk Orthopaedics calling {patient_first_name} "
                    f"to confirm an appointment that you have on {date_str} at {time_str}. "
                )
                response.say(greeting, voice=settings.TTS_VOICE)
                
                gather = response.gather(num_digits=1, timeout=10)
                gather.say(
                    "Press 1 to confirm. "
                    "Press 2 to speak to our office to reschedule. "
                    "Press 3 to cancel. "
                    "Press 5 to repeat this message. "
                    "Press 9 to stop reminders.",
                    voice=settings.TTS_VOICE
                )
                response.say("We didn't receive your selection. Goodbye.", voice=settings.TTS_VOICE)
                
                call = self.client.calls.create(
                    to=appointment.phone,
                    from_=settings.TWILIO_FROM_NUMBER,
                    twiml=str(response)
                )
            
            appointment_store.map_call_to_appointment(call.sid, appointment.id)
            appointment.call_attempts += 1
            appointment.status = AppointmentStatus.CALLING
            
            logger.info(f"Call initiated: {call.sid} for appointment {appointment.id}")
            return call.sid
        except Exception as e:
            logger.error(f"Error making call: {e}")
            return None
    
    def generate_initial_twiml(self, appointment=None, attempt_num: int = 1) -> str:
        response = VoiceResponse()
        
        logger.info(f"Generating TwiML - BASE_URL: {settings.BASE_URL}, Attempt: {attempt_num}")
        
        # Optional short pause on first attempt
        if attempt_num == 1 and getattr(settings, 'TTS_INITIAL_PAUSE', 0):
            response.pause(length=int(settings.TTS_INITIAL_PAUSE))
        
        # Build the greeting message
        if appointment:
            patient_first_name = appointment.patient_name.split()[0] if appointment.patient_name else "patient"
            date_str = appointment.appointment_date if appointment.appointment_date else "your upcoming appointment"
            time_str = appointment.appointment_time
            
            if attempt_num == 1:
                greeting = (
                    f"This is Prisk Orthopaedics calling {patient_first_name} "
                    f"to confirm an appointment that you have on {date_str} at {time_str}. "
                )
            else:
                greeting = f"Let me repeat that for you {patient_first_name}. "
        else:
            greeting = "This is Prisk Orthopaedics calling to confirm your appointment. "
        
        response.say(greeting, voice=settings.TTS_VOICE, language="en-US")
        
        # Create gather for patient response
        gather_url = f"{settings.BASE_URL}/twilio/gather"
        logger.info(f"Setting gather action URL to: {gather_url}")
        
        gather = Gather(
            num_digits=1,
            action=gather_url,
            method="POST",
            timeout=10,
            finish_on_key="#"
        )
        
        gather.say(
            "Press 1 to confirm. "
            "Press 2 to speak to our office to reschedule. "
            "Press 3 to cancel. "
            "Press 5 to repeat this message. "
            "Press 9 to stop reminders.",
            voice=settings.TTS_VOICE,
            language="en-US"
        )
        
        response.append(gather)
        
        # Fallback behavior if gather doesn't work (only retry once to avoid loops)
        if "localhost" not in settings.BASE_URL and "192.168" not in settings.BASE_URL:
            if attempt_num < 2:
                response.say("I didn't get your response. Let me try again.", voice=settings.TTS_VOICE)
                response.redirect(f"{settings.BASE_URL}/twilio/voice?attempt={attempt_num + 1}", method="POST")
            else:
                response.say("Thank you. Goodbye.", voice=settings.TTS_VOICE)
                response.hangup()
        else:
            response.say("If you need to confirm or cancel, please call us back at 4 1 2, 5 2 5, 7 6 9 2. Thank you.", voice=settings.TTS_VOICE)
            response.hangup()
        
        return str(response)
    
    def handle_gather(self, digits: str, call_sid: str) -> str:
        response = VoiceResponse()
        appointment = appointment_store.get_appointment_by_call_sid(call_sid)
        
        if not appointment:
            response.say("Thank you for calling. Goodbye.", voice=settings.TTS_VOICE)
            response.hangup()
            return str(response)
        
        if digits == "1":
            appointment.status = AppointmentStatus.CONFIRMED
            response.say("Your appointment is confirmed. Thank you!", voice=settings.TTS_VOICE)
            response.hangup()
        
        elif digits == "2":
            appointment.status = AppointmentStatus.RESCHEDULING
            response.say("Please hold while I connect you to our office.", voice=settings.TTS_VOICE)
            dial = Dial(callerId=settings.TWILIO_FROM_NUMBER, answer_on_bridge=True)
            dial.number(settings.JIVE_MAIN_NUMBER)
            response.append(dial)
        
        elif digits == "3":
            appointment.status = AppointmentStatus.CANCELLED
            response.say("Your appointment has been cancelled. Goodbye.", voice=settings.TTS_VOICE)
            response.hangup()
        
        elif digits == "5":
            # Repeat the message by redirecting back to the voice menu as a repeat attempt
            response.say("Let me repeat that.", voice=settings.TTS_VOICE)
            response.redirect(f"{settings.BASE_URL}/twilio/voice?attempt=2", method="POST")
        
        elif digits == "9":
            appointment.status = AppointmentStatus.DO_NOT_CALL
            response.say("We will not call you again about this appointment. Thank you.", voice=settings.TTS_VOICE)
            response.hangup()
        
        else:
            response.say("Invalid selection.", voice=settings.TTS_VOICE)
            response.redirect(f"{settings.BASE_URL}/twilio/voice", method="POST")
        
        return str(response)
    
    def generate_voicemail_twiml(self, appointment=None) -> str:
        response = VoiceResponse()
        
        # Minimal pause then one-shot message and hangup
        response.pause(length=1)
        
        if appointment:
            patient_first_name = appointment.patient_name.split()[0] if appointment.patient_name else "patient"
            date_str = appointment.appointment_date if appointment.appointment_date else "your upcoming appointment"
            time_str = appointment.appointment_time
            
            message = (
                f"This is Prisk Orthopaedics calling to remind you that you have an appointment on {date_str} at {time_str}. "
                f"Please call us at 4 1 2, 5 2 5, 7 6 9 2 if you can make the appointment or need to cancel or reschedule. Goodbye."
            )
        else:
            message = (
                "This is Prisk Orthopaedics calling about your upcoming appointment. "
                "Please call us at 4 1 2, 5 2 5, 7 6 9 2 if you can make the appointment or need to cancel or reschedule. Goodbye."
            )
        
        response.say(message, voice=settings.TTS_VOICE, language="en-US")
        response.hangup()
        
        return str(response)
    
    def handle_status_callback(self, call_sid: str, call_status: str, answered_by: Optional[str] = None) -> None:
        appointment = appointment_store.get_appointment_by_call_sid(call_sid)
        
        if not appointment:
            logger.warning(f"No appointment found for call {call_sid}")
            return
        
        logger.info(f"Call {call_sid} status: {call_status}, answered_by: {answered_by}, current apt status: {appointment.status}")
        # Store raw AnsweredBy for UI insight
        appointment.last_answered_by = answered_by
        
        if call_status == "completed":
            # Only update if status is still "Calling" (not updated by gather)
            if appointment.status == AppointmentStatus.CALLING:
                if answered_by in ["machine_end_beep", "machine_end_silence", "machine_end_other", "machine_start", "fax"]:
                    appointment.status = AppointmentStatus.VOICEMAIL
                    appointment.notes = "Left voicemail"
                    appointment.needs_callback = False
                else:
                    # Human/unknown answered but no button pressed
                    appointment.status = AppointmentStatus.NOT_CONFIRMED
                    if answered_by == "human":
                        appointment.notes = "Answered by human - no selection"
                        appointment.needs_callback = True
                    else:
                        appointment.notes = "Call completed - no response"
                        appointment.needs_callback = False
        
        elif call_status in ["no-answer", "busy"]:
            appointment.status = AppointmentStatus.NOT_CONFIRMED
            appointment.notes = f"Call {call_status}"
            appointment.needs_callback = False
        
        elif call_status in ["failed", "cancelled"]:
            appointment.status = AppointmentStatus.NOT_CONFIRMED
            appointment.notes = f"Call failed: {call_status}"
            appointment.needs_callback = False

        # Notify queue that this call completed so it can advance
        if call_status in ["completed", "no-answer", "busy", "failed", "canceled", "cancelled"]:
            try:
                # Lazy import to avoid circular import at module import time
                from services.call_queue import call_queue  # type: ignore
                call_queue.on_call_finished(call_sid)
            except Exception as e:
                logger.debug(f"CallQueue advance error ignored: {e}")

twilio_service = TwilioService()