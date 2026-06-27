"""
WhisperScore — Analysis Routes
POST /api/sessions/{id}/upload   — upload recording
POST /api/sessions/{id}/analyze  — trigger analysis
GET  /api/sessions/{id}/results  — get full results
GET  /api/demo                   — get demo results
"""
import json
import logging
import os
import shutil
import threading
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, BackgroundTasks
from sqlalchemy.orm import Session

from models.database import get_db
from models.session import (
    Session as SessionModel, Recording, AnalysisEvent,
    Metric, Score as ScoreModel, CoachingResult as CoachingModel,
    SessionStatus, EventCategory, EventSeverity,
)
from schemas.analysis import AnalysisResults, ScoreBreakdown, TimelineEvent
from core.config import settings
from core.pipeline import pipeline

router = APIRouter(prefix="/api", tags=["analysis"])
logger = logging.getLogger(__name__)


# ─── Upload ───────────────────────────────────────────────────────────────────

@router.post("/sessions/{session_id}/upload")
async def upload_recording(
    session_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload a video or audio recording for a session."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Validate file size
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    session_dir = settings.UPLOAD_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    ext = Path(file.filename).suffix if file.filename else ".webm"
    file_path = session_dir / f"recording{ext}"

    size = 0
    with open(file_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):  # 1 MB chunks
            size += len(chunk)
            if size > max_bytes:
                raise HTTPException(status_code=413, detail="File too large")
            f.write(chunk)

    # Persist recording record
    recording = Recording(
        session_id=session_id,
        original_filename=file.filename,
        file_path=str(file_path),
        file_size_bytes=size,
        mime_type=file.content_type,
    )
    db.add(recording)
    session.status = SessionStatus.UPLOADING
    db.commit()

    return {"message": "Upload complete", "file_path": str(file_path)}


# ─── Analyze ──────────────────────────────────────────────────────────────────

def _run_analysis(session_id: str, video_path: str, session_dir: str):
    """Background thread function that runs the full pipeline."""
    from models.database import SessionLocal
    db = SessionLocal()
    try:
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        session.status = SessionStatus.ANALYZING
        db.commit()

        result = pipeline.run(video_path=video_path, session_dir=session_dir)

        # ── Persist events ────────────────────────────────────────────────
        for e in result["events"]:
            event = AnalysisEvent(
                session_id=session_id,
                timestamp=e["timestamp"],
                category=EventCategory(e["category"]),
                metric=e["metric"],
                score=e.get("score"),
                severity=EventSeverity(e["severity"]),
                title=e["title"],
                description=e["description"],
                extra=json.dumps(e.get("extra", {})),
            )
            db.add(event)

        # ── Persist metrics ───────────────────────────────────────────────
        scores = result["scores"]
        score_row = ScoreModel(
            session_id=session_id,
            overall=scores.get("overall"),
            content=scores.get("content"),
            voice=scores.get("voice"),
            presence=scores.get("presence"),
            clarity=scores.get("clarity"),
            organization=scores.get("organization"),
            persuasiveness=scores.get("persuasiveness"),
            speaking_rate=scores.get("speaking_rate"),
            filler_score=scores.get("filler_score"),
            pause_quality=scores.get("pause_quality"),
            pitch_variation=scores.get("pitch_variation"),
            eye_contact=scores.get("eye_contact"),
            posture=scores.get("posture"),
        )
        db.add(score_row)

        # ── Persist coaching ──────────────────────────────────────────────
        coaching = result.get("coaching", {})
        coaching_row = CoachingModel(
            session_id=session_id,
            strengths=json.dumps(coaching.get("strengths", [])),
            weaknesses=json.dumps(coaching.get("weaknesses", [])),
            tips=json.dumps(coaching.get("tips", [])),
            improved_excerpt=coaching.get("improved_excerpt", ""),
            raw_transcript=result["metrics"]["content"].get("transcript", ""),
        )
        db.add(coaching_row)

        # ── Update recording duration ─────────────────────────────────────
        recording = db.query(Recording).filter(Recording.session_id == session_id).first()
        if recording:
            recording.duration_seconds = result.get("duration_seconds")
            recording.audio_path = result.get("audio_path")

        session.status = SessionStatus.COMPLETE
        db.commit()
        logger.info(f"Analysis complete for session: {session_id}")

    except Exception as e:
        logger.error(f"Analysis failed for {session_id}: {e}", exc_info=True)
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if session:
            session.status = SessionStatus.FAILED
            session.error_message = str(e)
            db.commit()
    finally:
        db.close()


@router.post("/sessions/{session_id}/analyze")
def trigger_analysis(
    session_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Trigger background analysis for an uploaded recording."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    recording = db.query(Recording).filter(Recording.session_id == session_id).first()
    if not recording:
        raise HTTPException(status_code=400, detail="No recording uploaded for this session")

    session_dir = str(settings.UPLOAD_DIR / session_id)
    background_tasks.add_task(
        _run_analysis,
        session_id=session_id,
        video_path=recording.file_path,
        session_dir=session_dir,
    )

    return {"message": "Analysis started", "session_id": session_id}


# ─── Results ──────────────────────────────────────────────────────────────────

@router.get("/sessions/{session_id}/results")
def get_results(session_id: str, db: Session = Depends(get_db)):
    """Get full analysis results for a session."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status == SessionStatus.FAILED:
        raise HTTPException(status_code=500, detail=session.error_message or "Analysis failed")

    if session.status not in (SessionStatus.COMPLETE,):
        return {
            "session_id": session_id,
            "status": session.status,
            "scores": None,
            "events": [],
        }

    # Fetch all data
    events = db.query(AnalysisEvent).filter(
        AnalysisEvent.session_id == session_id
    ).order_by(AnalysisEvent.timestamp).all()

    score = db.query(ScoreModel).filter(ScoreModel.session_id == session_id).first()
    coaching = db.query(CoachingModel).filter(CoachingModel.session_id == session_id).first()
    recording = db.query(Recording).filter(Recording.session_id == session_id).first()

    events_list = [
        {
            "timestamp": e.timestamp,
            "category": e.category.value,
            "metric": e.metric,
            "score": e.score,
            "severity": e.severity.value,
            "title": e.title,
            "description": e.description,
        }
        for e in events
    ]

    scores_dict = None
    if score:
        scores_dict = {
            "overall": score.overall,
            "content": score.content,
            "voice": score.voice,
            "presence": score.presence,
            "clarity": score.clarity,
            "organization": score.organization,
            "persuasiveness": score.persuasiveness,
            "speaking_rate": score.speaking_rate,
            "filler_score": score.filler_score,
            "pause_quality": score.pause_quality,
            "pitch_variation": score.pitch_variation,
            "eye_contact": score.eye_contact,
            "posture": score.posture,
        }

    coaching_dict = None
    if coaching:
        coaching_dict = {
            "strengths": json.loads(coaching.strengths or "[]"),
            "weaknesses": json.loads(coaching.weaknesses or "[]"),
            "tips": json.loads(coaching.tips or "[]"),
            "improved_excerpt": coaching.improved_excerpt or "",
            "summary": "",
            "transcript": coaching.raw_transcript or "",
        }

    return {
        "session_id": session_id,
        "status": session.status,
        "duration_seconds": recording.duration_seconds if recording else None,
        "scores": scores_dict,
        "events": events_list,
        "coaching": coaching_dict,
    }


# ─── Demo ─────────────────────────────────────────────────────────────────────

@router.get("/demo")
def get_demo():
    """
    Returns pre-computed demo analysis results.
    The UI is fully functional without running the ML pipeline.
    """
    demo_path = Path(__file__).parent.parent.parent / "demo_data.json"
    if demo_path.exists():
        with open(demo_path) as f:
            return json.load(f)
    return _generate_demo_data()


def _generate_demo_data() -> dict:
    """Generate a realistic demo analysis in-memory."""
    events = [
        {"timestamp": 4.0, "category": "voice", "metric": "pace", "score": 88, "severity": "positive", "title": "Strong Opening Pace", "description": "You started at a confident 135 WPM — clear and engaging for your audience."},
        {"timestamp": 18.5, "category": "voice", "metric": "fillers", "score": 55, "severity": "medium", "title": "Filler Words Detected", "description": 'Detected "um" and "uh" here. Replace with a confident pause or rephrase.'},
        {"timestamp": 34.0, "category": "presence", "metric": "eye_contact", "score": 82, "severity": "positive", "title": "Strong Eye Contact", "description": "Great eye contact here — you appear confident and engaged."},
        {"timestamp": 43.2, "category": "voice", "metric": "pace", "score": 38, "severity": "high", "title": "Speaking Too Fast", "description": "You spoke at ~178 WPM in this segment. Aim for 120–150 WPM for clarity."},
        {"timestamp": 58.0, "category": "content", "metric": "organization", "score": 72, "severity": "medium", "title": "Weak Transition", "description": "The transition between your main points lacked a clear signpost. Use phrases like 'Moving to my next point...'"},
        {"timestamp": 71.5, "category": "presence", "metric": "eye_contact", "score": 25, "severity": "high", "title": "Lost Eye Contact", "description": "You were looking away from the camera here. Maintain eye contact to build trust."},
        {"timestamp": 83.2, "category": "voice", "metric": "pause", "score": 90, "severity": "positive", "title": "Effective Pause", "description": "A 1.8s pause here — great for emphasis and letting your audience absorb what you said."},
        {"timestamp": 97.0, "category": "content", "metric": "evidence", "score": 42, "severity": "high", "title": "Weak Supporting Evidence", "description": "This claim lacks supporting data or examples. Back it up with a statistic or case study."},
        {"timestamp": 112.5, "category": "voice", "metric": "pitch_variation", "score": 85, "severity": "positive", "title": "Expressive Delivery", "description": "Your pitch variation here is excellent — you sound passionate and engaged."},
        {"timestamp": 124.0, "category": "presence", "metric": "posture", "score": 55, "severity": "medium", "title": "Uneven Shoulders", "description": "Your shoulders appear slightly uneven. Stand with squared shoulders to project confidence."},
        {"timestamp": 138.0, "category": "content", "metric": "clarity", "score": 78, "severity": "low", "title": "Complex Sentence", "description": "This sentence was long and complex. Shorter sentences improve clarity and impact."},
        {"timestamp": 156.0, "category": "voice", "metric": "pace", "score": 70, "severity": "low", "title": "Slight Slowdown", "description": "Your pace dropped to ~108 WPM here. Consider picking up the tempo."},
        {"timestamp": 172.0, "category": "content", "metric": "persuasiveness", "score": 88, "severity": "positive", "title": "Compelling Argument", "description": "Excellent logical structure here — your argument flows naturally and is highly persuasive."},
        {"timestamp": 185.0, "category": "presence", "metric": "eye_contact", "score": 90, "severity": "positive", "title": "Strong Eye Contact", "description": "Excellent camera presence in this section — very engaging."},
        {"timestamp": 198.0, "category": "voice", "metric": "loudness", "score": 48, "severity": "medium", "title": "Energy Drop Detected", "description": "Your vocal energy dropped here. Maintain consistent projection."},
        {"timestamp": 210.5, "category": "content", "metric": "clarity", "score": 92, "severity": "positive", "title": "Strong Conclusion", "description": "Your conclusion is clear, memorable, and well-delivered. Great finish!"},
    ]

    return {
        "session_id": "demo-session",
        "status": "complete",
        "duration_seconds": 220.0,
        "scores": {
            "overall": 74.2,
            "content": 71.5,
            "voice": 72.8,
            "presence": 79.0,
            "clarity": 74.0,
            "organization": 68.0,
            "persuasiveness": 72.0,
            "speaking_rate": 75.0,
            "filler_score": 65.0,
            "pause_quality": 80.0,
            "pitch_variation": 82.0,
            "eye_contact": 76.0,
            "posture": 68.0,
        },
        "events": events,
        "coaching": {
            "strengths": [
                "Strong, confident opening pace and delivery",
                "Excellent pitch variation — you sound passionate and engaged",
                "Memorable, well-structured conclusion",
            ],
            "weaknesses": [
                "Speaking rate spikes above 175 WPM in two segments",
                "Eye contact breaks during key argument sections",
                "Some claims lack supporting evidence or statistics",
            ],
            "tips": [
                "Practice with a metronome app set to 135 BPM to internalize ideal pace",
                "Place a sticky note with 'LOOK UP' on your monitor during rehearsal",
                "For every major claim, prepare one data point or example",
                "Use pause-breath technique: inhale for 1s before key points",
                "Record yourself and watch at 1.25x speed to identify filler word patterns",
            ],
            "improved_excerpt": "Rather than saying 'um, so basically what I mean is...', try: 'The core issue is straightforward. When we examine the data, three patterns emerge consistently.'",
            "summary": "A solid presentation with genuine strengths in vocal expressiveness and conclusion delivery. Focus on controlling speaking pace and maintaining consistent eye contact to significantly raise your overall score.",
            "transcript": "Good morning everyone. Um, so today I want to talk about the future of artificial intelligence and how it's going to, uh, basically change the way we work. The key thing to understand is that AI isn't replacing jobs — it's fundamentally transforming them. We see this in data from over 500 companies showing that AI adoption increased productivity by 40% on average. Moving to my second point...",
        },
    }
