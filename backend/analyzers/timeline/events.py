"""
WhisperScore — Unified Event Schema
All analyzers return events in this exact format.
The frontend consumes only this schema.
"""
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, Literal
from enum import Enum


class EventCategory(str, Enum):
    VOICE = "voice"
    CONTENT = "content"
    PRESENCE = "presence"


class EventSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    POSITIVE = "positive"


@dataclass
class Event:
    """
    A timestamped event in the presentation timeline.
    Every analyzer emits events in this exact format.

    Example:
        Event(
            timestamp=83.2,
            category=EventCategory.VOICE,
            metric="pace",
            score=42,
            severity=EventSeverity.HIGH,
            title="Speaking Too Fast",
            description="Your speaking rate exceeded 160 WPM.",
        )
    """
    timestamp: float
    category: EventCategory
    metric: str
    severity: EventSeverity
    title: str
    description: str
    score: Optional[float] = None
    extra: Optional[Dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["category"] = self.category.value
        d["severity"] = self.severity.value
        return d


# ─── Helper factory functions ─────────────────────────────────────────────────

def voice_event(
    timestamp: float,
    metric: str,
    title: str,
    description: str,
    severity: EventSeverity,
    score: Optional[float] = None,
    **extra,
) -> Event:
    return Event(
        timestamp=timestamp,
        category=EventCategory.VOICE,
        metric=metric,
        severity=severity,
        title=title,
        description=description,
        score=score,
        extra=extra or {},
    )


def content_event(
    timestamp: float,
    metric: str,
    title: str,
    description: str,
    severity: EventSeverity,
    score: Optional[float] = None,
    **extra,
) -> Event:
    return Event(
        timestamp=timestamp,
        category=EventCategory.CONTENT,
        metric=metric,
        severity=severity,
        title=title,
        description=description,
        score=score,
        extra=extra or {},
    )


def presence_event(
    timestamp: float,
    metric: str,
    title: str,
    description: str,
    severity: EventSeverity,
    score: Optional[float] = None,
    **extra,
) -> Event:
    return Event(
        timestamp=timestamp,
        category=EventCategory.PRESENCE,
        metric=metric,
        severity=severity,
        title=title,
        description=description,
        score=score,
        extra=extra or {},
    )
