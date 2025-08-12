import os
from datetime import datetime
from sqlalchemy import create_engine, Column, String, DateTime, Integer, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import logging

logger = logging.getLogger(__name__)

DATABASE_PATH = "pow_reminder.db"
DATABASE_URL = f"sqlite+aiosqlite:///{DATABASE_PATH}"

Base = declarative_base()

class AppointmentRecord(Base):
    __tablename__ = "appointments"
    
    id = Column(String, primary_key=True)
    patient_name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    appointment_time = Column(String, nullable=False)
    provider = Column(String, nullable=False)
    appointment_type = Column(String, nullable=False)
    status = Column(String, nullable=False)
    original_confirmation = Column(String)
    call_sid = Column(String)
    last_called = Column(DateTime)
    call_attempts = Column(Integer, default=0)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    upload_batch_id = Column(String)

class CallHistory(Base):
    __tablename__ = "call_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    appointment_id = Column(String, nullable=False)
    call_sid = Column(String)
    patient_name = Column(String)
    phone = Column(String)
    call_time = Column(DateTime, default=datetime.utcnow)
    call_status = Column(String)
    call_result = Column(String)
    duration_seconds = Column(Integer)
    key_pressed = Column(String)
    notes = Column(Text)

class UploadHistory(Base):
    __tablename__ = "upload_history"
    
    id = Column(String, primary_key=True)
    filename = Column(String, nullable=False)
    upload_time = Column(DateTime, default=datetime.utcnow)
    appointments_found = Column(Integer, default=0)
    unconfirmed_count = Column(Integer, default=0)
    uploaded_by = Column(String, default="Staff")

engine = None
AsyncSessionLocal = None

async def init_database():
    global engine, AsyncSessionLocal
    
    engine = create_async_engine(DATABASE_URL, echo=False)
    AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info(f"Database initialized at {DATABASE_PATH}")

async def get_session():
    async with AsyncSessionLocal() as session:
        yield session

class DatabaseService:
    @staticmethod
    async def save_appointment(session: AsyncSession, appointment_dict: dict):
        record = AppointmentRecord(**appointment_dict)
        session.add(record)
        await session.commit()
        return record
    
    @staticmethod
    async def get_appointment(session: AsyncSession, appointment_id: str):
        result = await session.get(AppointmentRecord, appointment_id)
        return result
    
    @staticmethod
    async def update_appointment_status(session: AsyncSession, appointment_id: str, status: str, notes: str = None):
        appointment = await session.get(AppointmentRecord, appointment_id)
        if appointment:
            appointment.status = status
            appointment.updated_at = datetime.utcnow()
            if notes:
                appointment.notes = notes
            await session.commit()
            return True
        return False
    
    @staticmethod
    async def log_call(session: AsyncSession, call_data: dict):
        call_record = CallHistory(**call_data)
        session.add(call_record)
        await session.commit()
        return call_record
    
    @staticmethod
    async def get_todays_appointments(session: AsyncSession):
        from sqlalchemy import select, and_, cast, Date
        from datetime import date
        
        today = date.today()
        stmt = select(AppointmentRecord).where(
            cast(AppointmentRecord.created_at, Date) == today
        )
        result = await session.execute(stmt)
        return result.scalars().all()
    
    @staticmethod
    async def get_call_history(session: AsyncSession, appointment_id: str = None):
        from sqlalchemy import select
        
        if appointment_id:
            stmt = select(CallHistory).where(CallHistory.appointment_id == appointment_id)
        else:
            stmt = select(CallHistory).order_by(CallHistory.call_time.desc()).limit(100)
        
        result = await session.execute(stmt)
        return result.scalars().all()
    
    @staticmethod
    async def save_upload_history(session: AsyncSession, upload_data: dict):
        upload_record = UploadHistory(**upload_data)
        session.add(upload_record)
        await session.commit()
        return upload_record

db_service = DatabaseService()