"""
WhisperScore — Pydantic Schemas
API request/response validation models.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


# ─── Enums ───────────────────────────────────────────────────────────────────

class SessionStatus(str, Enum):
    PENDING = "pending"
    UPLOADING = "uploading"
    ANALYZING = "analyzing"
    COMPLETE = "complete"
    FAILED = "failed"


class EventCategory(str, Enum):
    VOICE = "voice"
    CONTENT = "content"
    PRESENCE = "presence"


class EventSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    POSITIVE = "positive"


# ─── Event Schema ────────────────────────────────────────────────────────────

class TimelineEvent(BaseModel):
    """
    Unified timestamped event. Every analyzer produces this exact format.
    The frontend consumes only this schema — no analyzer-specific logic.
    """
    timestamp: float = Field(..., description="Seconds from recording start")
    category: EventCategory
    metric: str = Field(..., description="e.g. 'pace', 'eye_contact', 'clarity'")
    score: Optional[float] = Field(None, ge=0, le=100)
    severity: EventSeverity
    title: str
    description: str
    extra: Optional[Dict[str, Any]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": 83.2,
                "category": "voice",
                "metric": "pace",
                "score": 42,
                "severity": "high",
                "title": "Speaking Too Fast",
                "description": "Your speaking rate exceeded the recommended range.",
            }
        }


# ─── Scores ──────────────────────────────────────────────────────────────────

class ScoreBreakdown(BaseModel):
    overall: float = Field(..., ge=0, le=100)
    content: float = Field(..., ge=0, le=100)
    voice: float = Field(..., ge=0, le=100)
    presence: float = Field(..., ge=0, le=100)

    # Sub-scores
    clarity: Optional[float] = None
    organization: Optional[float] = None
    persuasiveness: Optional[float] = None
    speaking_rate: Optional[float] = None
    filler_score: Optional[float] = None
    pause_quality: Optional[float] = None
    pitch_variation: Optional[float] = None
    eye_contact: Optional[float] = None
    posture: Optional[float] = None


# ─── Metrics ─────────────────────────────────────────────────────────────────

class MetricItem(BaseModel):
    analyzer: str
    name: str
    value: float
    unit: Optional[str] = None


class VoiceMetrics(BaseModel):
    average_wpm: Optional[float] = None
    filler_count: Optional[int] = None
    filler_words: Optional[List[str]] = None
    pause_count: Optional[int] = None
    long_pause_count: Optional[int] = None
    speaking_duration_seconds: Optional[float] = None
    silence_duration_seconds: Optional[float] = None
    avg_pitch_hz: Optional[float] = None
    pitch_variation: Optional[float] = None
    jitter: Optional[float] = None
    shimmer: Optional[float] = None
    hnr: Optional[float] = None
    avg_loudness_db: Optional[float] = None


class PresenceMetrics(BaseModel):
    eye_contact_percentage: Optional[float] = None
    avg_blink_rate: Optional[float] = None
    head_pose_forward_pct: Optional[float] = None
    posture_score: Optional[float] = None


class ContentMetrics(BaseModel):
    word_count: Optional[int] = None
    sentence_count: Optional[int] = None
    transcript: Optional[str] = None


# ─── Coaching ────────────────────────────────────────────────────────────────

class CoachingResult(BaseModel):
    strengths: List[str] = []
    weaknesses: List[str] = []
    tips: List[str] = []
    improved_excerpt: Optional[str] = None
    summary: Optional[str] = None


# ─── Session ─────────────────────────────────────────────────────────────────

class SessionCreate(BaseModel):
    pass  # No inputs needed — session created server-side


class SessionResponse(BaseModel):
    id: str
    status: SessionStatus
    created_at: datetime

    class Config:
        from_attributes = True


class SessionStatusResponse(BaseModel):
    id: str
    status: SessionStatus
    error_message: Optional[str] = None
    progress_pct: Optional[int] = None


# ─── Analysis Results ────────────────────────────────────────────────────────

class AnalysisResults(BaseModel):
    """
    Full results returned to the frontend after analysis completes.
    This is the primary API response consumed by the Results page.
    """
    session_id: str
    status: SessionStatus
    duration_seconds: Optional[float] = None

    # Core results
    scores: Optional[ScoreBreakdown] = None
    events: List[TimelineEvent] = []
    voice_metrics: Optional[VoiceMetrics] = None
    presence_metrics: Optional[PresenceMetrics] = None
    content_metrics: Optional[ContentMetrics] = None
    coaching: Optional[CoachingResult] = None

    # Timeline summary (top events sorted by severity)
    top_events: List[TimelineEvent] = []

    class Config:
        from_attributes = True
