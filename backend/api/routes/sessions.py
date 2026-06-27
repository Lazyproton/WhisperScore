"""
WhisperScore — Session Routes
POST /api/sessions       — create session
GET  /api/sessions/{id}  — get session status
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models.database import get_db
from models.session import Session as SessionModel, SessionStatus
from schemas.analysis import SessionResponse, SessionStatusResponse
import uuid

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse, status_code=201)
def create_session(db: Session = Depends(get_db)):
    """Create a new recording session."""
    session = SessionModel(id=str(uuid.uuid4()), status=SessionStatus.PENDING)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/{session_id}", response_model=SessionStatusResponse)
def get_session(session_id: str, db: Session = Depends(get_db)):
    """Get session status (used for polling during analysis)."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionStatusResponse(
        id=session.id,
        status=session.status,
        error_message=session.error_message,
    )
