"""
WhisperScore — SQLAlchemy Models
Defines all database tables.
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Float, Integer, Boolean,
    DateTime, Text, ForeignKey, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from models.database import Base
import enum


def _uuid() -> str:
    return str(uuid.uuid4())


class SessionStatus(str, enum.Enum):
    PENDING = "pending"
    UPLOADING = "uploading"
    ANALYZING = "analyzing"
    COMPLETE = "complete"
    FAILED = "failed"


class EventCategory(str, enum.Enum):
    VOICE = "voice"
    CONTENT = "content"
    PRESENCE = "presence"


class EventSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    POSITIVE = "positive"


# ─────────────────────────────────────────────────────────────────────────────
class Session(Base):
    """
    A user recording session. One session = one presentation attempt.
    Sessions are identified by UUID; no user authentication required in V1.
    """
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=_uuid)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = Column(SAEnum(SessionStatus), default=SessionStatus.PENDING)
    error_message = Column(Text, nullable=True)

    # Relationships
    recording = relationship("Recording", back_populates="session", uselist=False)
    events = relationship("AnalysisEvent", back_populates="session")
    metrics = relationship("Metric", back_populates="session")
    score = relationship("Score", back_populates="session", uselist=False)
    coaching = relationship("CoachingResult", back_populates="session", uselist=False)


# ─────────────────────────────────────────────────────────────────────────────
class Recording(Base):
    """
    Uploaded recording file associated with a session.
    Stores both the original file and extracted audio path.
    """
    __tablename__ = "recordings"

    id = Column(String, primary_key=True, default=_uuid)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False, unique=True)
    original_filename = Column(String, nullable=True)
    file_path = Column(String, nullable=False)       # Path to original video/audio
    audio_path = Column(String, nullable=True)       # Path to extracted WAV audio
    duration_seconds = Column(Float, nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    mime_type = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("Session", back_populates="recording")


# ─────────────────────────────────────────────────────────────────────────────
class AnalysisEvent(Base):
    """
    Timestamped event from any analyzer. This is the central table for
    the interactive timeline. Every analyzer writes to this table.

    The unified event schema ensures the frontend never needs to know
    which analyzer produced an event.
    """
    __tablename__ = "analysis_events"

    id = Column(String, primary_key=True, default=_uuid)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)

    # Core event fields
    timestamp = Column(Float, nullable=False)        # Seconds from recording start
    category = Column(SAEnum(EventCategory), nullable=False)
    metric = Column(String, nullable=False)          # e.g. "pace", "eye_contact"
    score = Column(Float, nullable=True)             # 0–100
    severity = Column(SAEnum(EventSeverity), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)

    # Optional extended data (JSON string)
    extra = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("Session", back_populates="events")


# ─────────────────────────────────────────────────────────────────────────────
class Metric(Base):
    """
    A single numeric metric produced by any analyzer.
    E.g.: average_wpm=142, filler_count=7, eye_contact_pct=68.
    """
    __tablename__ = "metrics"

    id = Column(String, primary_key=True, default=_uuid)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    analyzer = Column(String, nullable=False)        # e.g. "whisper", "librosa"
    name = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String, nullable=True)             # e.g. "wpm", "%", "hz"

    session = relationship("Session", back_populates="metrics")


# ─────────────────────────────────────────────────────────────────────────────
class Score(Base):
    """
    Final aggregated scores for a session.
    One row per session, four score dimensions + overall.
    """
    __tablename__ = "scores"

    id = Column(String, primary_key=True, default=_uuid)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False, unique=True)

    overall = Column(Float, nullable=True)
    content = Column(Float, nullable=True)
    voice = Column(Float, nullable=True)
    presence = Column(Float, nullable=True)

    # Sub-scores (stored as individual columns for easy querying)
    clarity = Column(Float, nullable=True)
    organization = Column(Float, nullable=True)
    persuasiveness = Column(Float, nullable=True)
    speaking_rate = Column(Float, nullable=True)
    filler_score = Column(Float, nullable=True)
    pause_quality = Column(Float, nullable=True)
    pitch_variation = Column(Float, nullable=True)
    eye_contact = Column(Float, nullable=True)
    posture = Column(Float, nullable=True)

    session = relationship("Session", back_populates="score")


# ─────────────────────────────────────────────────────────────────────────────
class CoachingResult(Base):
    """
    LLM-generated coaching for a session.
    """
    __tablename__ = "coaching_results"

    id = Column(String, primary_key=True, default=_uuid)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False, unique=True)

    strengths = Column(Text, nullable=True)          # JSON array
    weaknesses = Column(Text, nullable=True)         # JSON array
    tips = Column(Text, nullable=True)               # JSON array
    improved_excerpt = Column(Text, nullable=True)   # Rewritten paragraph
    raw_transcript = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("Session", back_populates="coaching")
