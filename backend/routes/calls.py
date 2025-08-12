from fastapi import APIRouter, HTTPException, Form, Response, Query
from fastapi.responses import JSONResponse
from twilio.twiml.voice_response import VoiceResponse
from typing import Optional
from pydantic import BaseModel
import logging
from services.twilio_client import twilio_service
from models import appointment_store, AppointmentStatus
from settings import settings

class CallRequest(BaseModel):
    override_window: bool = False

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/api/call/{appointment_id}")
async def initiate_call(appointment_id: str, request: CallRequest = CallRequest()):
    override = request.override_window
    logger.info(f"Call request: appointment_id={appointment_id}, override_window={override}")
    
    if not settings.validate():
        raise HTTPException(status_code=500, detail="Twilio configuration incomplete. Please check your .env file.")
    
    # Check call window unless override is enabled
    if not override and not settings.is_within_call_window():
        logger.info(f"Outside call window and override not enabled")
        raise HTTPException(
            status_code=400,
            detail=f"Calls can only be made between {settings.CALL_WINDOW_START} and {settings.CALL_WINDOW_END}. Check 'Override call window' to call anyway."
        )
    
    appointment = appointment_store.get_appointment(appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    if appointment.status in [AppointmentStatus.CONFIRMED, AppointmentStatus.CANCELLED, AppointmentStatus.DO_NOT_CALL]:
        raise HTTPException(status_code=400, detail=f"Cannot call appointment with status: {appointment.status}")
    
    try:
        call_sid = twilio_service.make_call(appointment, override_window=override)
        
        if call_sid:
            message = "Call initiated successfully."
            if override:
                message += " (Override active - calling outside normal hours)"
            return JSONResponse(content={
                "success": True,
                "call_sid": call_sid,
                "message": message
            })
        else:
            raise HTTPException(status_code=500, detail="Failed to initiate call. Check Twilio configuration and phone number verification.")
    except Exception as e:
        logger.error(f"Call initiation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Call failed: {str(e)}")

@router.post("/twilio/voice")
async def handle_voice(
    CallSid: str = Form(None),
    From: str = Form(None),
    To: str = Form(None),
    CallStatus: str = Form(None),
    AnsweredBy: Optional[str] = Form(None),
    attempt: Optional[str] = Form(None)
):
    try:
        logger.info(f"Voice webhook: CallSid={CallSid}, Status={CallStatus}, AnsweredBy={AnsweredBy}, Attempt={attempt}")
        
        # Check if this is a repeat attempt
        attempt_num = int(attempt) if attempt else 1
        
        # Map the call to appointment immediately when voice webhook is called
        appointment = appointment_store.get_appointment_by_call_sid(CallSid)
        
        if AnsweredBy in ["machine_end_beep", "machine_end_silence", "machine_end_other", "machine_start", "fax"]:
            # Detected voicemail: play a concise one-shot voicemail message and hang up
            twiml = twilio_service.generate_voicemail_twiml(appointment)
        elif attempt_num > 3:
            # After 3 attempts, hang up
            response = VoiceResponse()
            response.say("We'll try again later. Goodbye.", voice="alice")
            response.hangup()
            twiml = str(response)
        else:
            twiml = twilio_service.generate_initial_twiml(appointment, attempt_num)
        
        return Response(content=twiml, media_type="application/xml")
    except Exception as e:
        logger.error(f"Error in voice webhook: {str(e)}")
        # Return a simple TwiML response on error
        response = VoiceResponse()
        response.say("We're experiencing technical difficulties. Please call us directly at 4 1 2, 5 2 5, 7 6 9 2.", voice="alice")
        response.hangup()
        return Response(content=str(response), media_type="application/xml")

@router.post("/twilio/gather")
async def handle_gather(
    Digits: str = Form(None),
    CallSid: str = Form(...),
    From: str = Form(None),
    To: str = Form(None)
):
    logger.info(f"Gather webhook called: CallSid={CallSid}, Digits='{Digits}'")
    
    # Handle case where no digits were pressed
    if not Digits or Digits == "":
        logger.info("No digits received, redirecting to voice menu")
        # Redirect back to voice menu for another attempt
        response = VoiceResponse()
        response.redirect(f"{settings.BASE_URL}/twilio/voice?attempt=2", method="POST")
        twiml = str(response)
    else:
        logger.info(f"Processing digit: {Digits}")
        twiml = twilio_service.handle_gather(Digits, CallSid)
    
    return Response(content=twiml, media_type="application/xml")

@router.post("/twilio/status")
async def handle_status(
    CallSid: str = Form(...),
    CallStatus: str = Form(...),
    AnsweredBy: Optional[str] = Form(None),
    From: str = Form(None),
    To: str = Form(None),
    CallDuration: Optional[str] = Form(None)
):
    logger.info(f"Status webhook: CallSid={CallSid}, Status={CallStatus}, AnsweredBy={AnsweredBy}")
    
    twilio_service.handle_status_callback(CallSid, CallStatus, AnsweredBy)
    
    return Response(content="", status_code=200)

@router.post("/twilio/dial-status")
async def handle_dial_status(
    DialCallStatus: str = Form(...),
    CallSid: str = Form(...),
    DialCallSid: Optional[str] = Form(None)
):
    logger.info(f"Dial status: CallSid={CallSid}, DialStatus={DialCallStatus}")
    
    response = VoiceResponse()
    
    if DialCallStatus != "completed":
        response.say(
            "We were unable to connect you at this time. "
            "Please call our office directly. Goodbye.",
            voice="alice"
        )
    
    response.hangup()
    
    return Response(content=str(response), media_type="application/xml")