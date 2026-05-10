"""
Database models and session management.
"""

from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean,
    DateTime, Float, Text, ForeignKey, JSON
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker, relationship

from config.settings import DATABASE_URL


engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class Trigger(Base):
    """Represents a configured trigger/monitor."""

    __tablename__ = "triggers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    trigger_type = Column(String(50), nullable=False)
    enabled = Column(Boolean, default=True)
    threshold_seconds = Column(Integer, nullable=False)
    last_activity = Column(DateTime, default=datetime.utcnow)
    last_check = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default="ok")  # ok, warning, failed
    config = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    events = relationship("TriggerEvent", back_populates="trigger")


class TriggerEvent(Base):
    """Log of trigger state changes and activities."""

    __tablename__ = "trigger_events"

    id = Column(Integer, primary_key=True, index=True)
    trigger_id = Column(Integer, ForeignKey("triggers.id"), nullable=False)
    event_type = Column(String(50), nullable=False)  # activity, warning, failure, reset
    message = Column(Text)
    event_metadata = Column(JSON, default=dict)   # renamed from 'metadata' (reserved in SQLAlchemy)
    created_at = Column(DateTime, default=datetime.utcnow)

    trigger = relationship("Trigger", back_populates="events")


class Contact(Base):
    """Emergency contacts to notify."""

    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255))
    phone = Column(String(50))
    webhook_url = Column(String(500))
    priority = Column(Integer, default=1)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Payload(Base):
    """Data or messages to release when switch fires."""

    __tablename__ = "payloads"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    payload_type = Column(String(50), nullable=False)  # message, file, credentials
    content_encrypted = Column(Text)
    recipients = Column(JSON, default=list)
    released = Column(Boolean, default=False)
    released_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class SystemState(Base):
    """Global system state tracking."""

    __tablename__ = "system_state"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Get database session (context manager / dependency)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
