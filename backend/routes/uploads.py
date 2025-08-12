from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import os
import shutil
from typing import List, Dict
import logging
from services.pdf_parser import PracticeFusionParser
from models import appointment_store
from settings import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["uploads"])

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    file_path = os.path.join(settings.UPLOAD_DIR, file.filename)

    try:
        # Stream file to disk and enforce size limit
        size = 0
        chunk_size = 1024 * 1024
        with open(file_path, "wb") as buffer:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                size += len(chunk)
                if size > settings.MAX_FILE_SIZE:
                    raise HTTPException(status_code=400, detail="File size exceeds 10MB limit")
                buffer.write(chunk)

        parser = PracticeFusionParser()
        appointments = parser.parse_pdf(file_path)

        appointment_store.clear_all()

        for appointment in appointments:
            appointment_store.add_appointment(appointment)

        os.remove(file_path)

        return JSONResponse(content={
            "success": True,
            "message": f"Successfully parsed {len(appointments)} unconfirmed appointments",
            "appointments_count": len(appointments)
        })

    except ValueError as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"Upload error: {e}")
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail="Failed to process PDF")

@router.get("/appointments")
async def get_appointments() -> List[Dict]:
    appointments = appointment_store.get_all_appointments()
    return [apt.to_dict() for apt in appointments]