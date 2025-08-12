from twilio.request_validator import RequestValidator
from fastapi import Request, HTTPException, Depends
from settings import settings
import logging

logger = logging.getLogger(__name__)

validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)

async def validate_twilio_request(request: Request):
    """Validate that the request is actually from Twilio"""
    
    # For local testing without validation
    if "localhost" in settings.BASE_URL or "192.168" in settings.BASE_URL:
        return True
    
    signature = request.headers.get("X-Twilio-Signature", "")
    url = str(request.url)
    
    # Get the raw form data
    body = await request.body()
    form_data = {}
    if body:
        for item in body.decode().split('&'):
            if '=' in item:
                key, value = item.split('=', 1)
                form_data[key] = value
    
    if not validator.validate(url, form_data, signature):
        logger.warning(f"Invalid Twilio signature from {request.client.host}")
        raise HTTPException(status_code=403, detail="Invalid request signature")
    
    return True