from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import logging
import sys
sys.path.append('.')

from routes import uploads, calls
from settings import settings
from database import init_database
import json
from urllib.request import urlopen
from urllib.error import URLError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI(title="POW Reminder MVP", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:800", "http://localhost:8000", "http://127.0.0.1:800", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.include_router(uploads.router)
app.include_router(calls.router)

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "base_url": settings.BASE_URL,
        "call_window_start": settings.CALL_WINDOW_START,
        "call_window_end": settings.CALL_WINDOW_END,
        "timezone": settings.TIMEZONE
    })

@app.get("/healthz")
async def health_check():
    twilio_configured = settings.validate()
    call_window_active = settings.is_within_call_window()
    
    return {
        "status": "healthy",
        "twilio_configured": twilio_configured,
        "call_window_active": call_window_active,
        "settings": {
            "timezone": settings.TIMEZONE,
            "call_window": f"{settings.CALL_WINDOW_START} - {settings.CALL_WINDOW_END}"
        }
    }

@app.on_event("startup")
async def startup_event():
    logging.info("POW Reminder MVP starting up...")
    
    await init_database()
    
    # Auto-start tunnel if needed
    if settings.AUTO_TUNNEL:
        try:
            from auto_tunnel import start_tunnel_service
            logging.info("Starting automatic tunnel service...")
            if start_tunnel_service():
                logging.info("Tunnel service started successfully")
                # Reload settings to get new BASE_URL
                from importlib import reload
                reload(settings)
            else:
                logging.warning("Could not start tunnel service - webhooks will not work")
        except Exception as e:
            logging.warning(f"Tunnel service not available: {e}")
    
    if not settings.validate():
        logging.warning("Twilio configuration incomplete. Please check your .env file")
    else:
        logging.info("Twilio configuration validated successfully")
    logging.info(f"Call window: {settings.CALL_WINDOW_START} - {settings.CALL_WINDOW_END} {settings.TIMEZONE}")
    logging.info(f"Database location: pow_reminder.db")

    # Auto-detect ngrok URL from local API to simplify setup
    try:
        with urlopen('http://127.0.0.1:4040/api/tunnels', timeout=2) as resp:
            data = json.load(resp)
            public_urls = [t.get('public_url') for t in data.get('tunnels', []) if t.get('public_url', '').startswith('https://')]
            if public_urls:
                ngrok_url = public_urls[0]
                if settings.BASE_URL != ngrok_url:
                    old = settings.BASE_URL
                    settings.BASE_URL = ngrok_url
                    logging.info(f"Detected ngrok URL via 4040 API. BASE_URL updated: {old} -> {settings.BASE_URL}")
    except URLError:
        pass
    except Exception as e:
        logging.debug(f"ngrok URL auto-detect skipped: {e}")