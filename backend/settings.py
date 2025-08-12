import os
from typing import Optional
from dotenv import load_dotenv
from datetime import datetime, time
import pytz
from pathlib import Path

# Load .env from the backend directory
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"Loaded .env from: {env_path}")
else:
    print(f"WARNING: .env file not found at: {env_path}")
    print(f"Current working directory: {os.getcwd()}")

class Settings:
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_FROM_NUMBER: str = os.getenv("TWILIO_FROM_NUMBER", "")
    JIVE_MAIN_NUMBER: str = os.getenv("JIVE_MAIN_NUMBER", "")
    BASE_URL: str = os.getenv("BASE_URL", "http://localhost:8000")
    TIMEZONE: str = os.getenv("TIMEZONE", "America/New_York")
    CALL_WINDOW_START: str = os.getenv("CALL_WINDOW_START", "10:00")
    CALL_WINDOW_END: str = os.getenv("CALL_WINDOW_END", "15:00")
    AUTO_TUNNEL: bool = os.getenv("AUTO_TUNNEL", "false").lower() == "true"
    # Text-to-Speech voice (Twilio <Say> voice). Examples: "alice" (standard), "Polly.Joanna", "Polly.Matthew"
    TTS_VOICE: str = os.getenv("TTS_VOICE", "alice")
    # Optional initial pause before greeting (seconds)
    TTS_INITIAL_PAUSE: int = int(os.getenv("TTS_INITIAL_PAUSE", "0"))
    # Answering Machine Detection mode: "none" | "enable" | "detect_message_end"
    AMD_MODE: str = os.getenv("AMD_MODE", "none").lower()
    
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    @classmethod
    def is_within_call_window(cls) -> bool:
        tz = pytz.timezone(cls.TIMEZONE)
        now = datetime.now(tz)
        
        start_time = datetime.strptime(cls.CALL_WINDOW_START, "%H:%M").time()
        end_time = datetime.strptime(cls.CALL_WINDOW_END, "%H:%M").time()
        current_time = now.time()
        
        if start_time <= end_time:
            return start_time <= current_time <= end_time
        else:
            return current_time >= start_time or current_time <= end_time
    
    @classmethod
    def validate(cls) -> bool:
        required = [
            cls.TWILIO_ACCOUNT_SID,
            cls.TWILIO_AUTH_TOKEN,
            cls.TWILIO_FROM_NUMBER,
            cls.JIVE_MAIN_NUMBER,
            cls.BASE_URL
        ]
        
        # Debug output
        print(f"Validating Twilio config:")
        print(f"  TWILIO_ACCOUNT_SID: {'SET' if cls.TWILIO_ACCOUNT_SID else 'MISSING'} (length: {len(cls.TWILIO_ACCOUNT_SID)})")
        print(f"  TWILIO_AUTH_TOKEN: {'SET' if cls.TWILIO_AUTH_TOKEN else 'MISSING'} (length: {len(cls.TWILIO_AUTH_TOKEN)})")
        print(f"  TWILIO_FROM_NUMBER: {cls.TWILIO_FROM_NUMBER if cls.TWILIO_FROM_NUMBER else 'MISSING'}")
        print(f"  JIVE_MAIN_NUMBER: {cls.JIVE_MAIN_NUMBER if cls.JIVE_MAIN_NUMBER else 'MISSING'}")
        print(f"  BASE_URL: {cls.BASE_URL if cls.BASE_URL else 'MISSING'}")
        
        return all(required)

settings = Settings()