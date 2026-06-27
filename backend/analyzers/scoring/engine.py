"""
WhisperScore — Scoring Engine
Aggregates results from all analyzers into final scores.

Score weights:
  Content:  35%
  Voice:    35%
  Presence: 30%
"""
import logging
from typing import List, Dict, Any
from analyzers.base import AnalyzerResult

logger = logging.getLogger(__name__)


def compute_scores(analyzer_results: Dict[str, AnalyzerResult]) -> Dict[str, Any]:
    """
    Takes the results from all analyzers and produces a final score breakdown.

    Args:
        analyzer_results: Dict keyed by analyzer name.

    Returns:
        Dict with overall, content, voice, presence, and sub-scores.
    """
    scores = {}

    # ─── Voice Score ─────────────────────────────────────────────────────────
    voice_components = []

    whisper = analyzer_results.get("whisper")
    if whisper and whisper.success:
        wpm = whisper.metrics.get("avg_wpm", 130)
        filler_count = whisper.metrics.get("filler_count", 0)
        total_words = max(whisper.metrics.get("total_words", 1), 1)
        duration = whisper.metrics.get("duration_seconds", 60)

        # WPM score (ideal: 120-150)
        if 120 <= wpm <= 150:
            wpm_score = 90
        elif wpm < 100 or wpm > 180:
            wpm_score = max(30, 90 - abs(wpm - 135) * 0.8)
        else:
            wpm_score = max(50, 90 - abs(wpm - 135) * 0.5)

        # Filler score
        filler_rate = filler_count / (duration / 60) if duration > 0 else 0
        filler_score = max(20, 100 - filler_rate * 8)

        scores["speaking_rate"] = round(wpm_score, 1)
        scores["filler_score"] = round(filler_score, 1)
        voice_components.extend([wpm_score * 0.4, filler_score * 0.3])

    silero = analyzer_results.get("silero")
    if silero and silero.success:
        long_pauses = silero.metrics.get("long_pause_count", 0)
        good_pauses = silero.metrics.get("good_pause_count", 0)
        speaking_ratio = silero.metrics.get("speaking_ratio", 0.8)
        pause_score = max(30, 100 - long_pauses * 10 + good_pauses * 5)
        scores["pause_quality"] = round(min(100, pause_score), 1)
        voice_components.append(pause_score * 0.15)

    librosa = analyzer_results.get("librosa")
    if librosa and librosa.success:
        consistency = librosa.metrics.get("loudness_consistency_score", 70)
        voice_components.append(consistency * 0.1)

    parselmouth = analyzer_results.get("parselmouth")
    if parselmouth and parselmouth.success:
        pitch_var = parselmouth.metrics.get("pitch_variation_score", 60)
        scores["pitch_variation"] = round(pitch_var, 1)
        voice_components.append(pitch_var * 0.05)

    if voice_components:
        total_weight = 0.4 + 0.3 + 0.15 + 0.1 + 0.05
        voice_score = sum(voice_components) / total_weight if total_weight > 0 else 60
    else:
        voice_score = 60
    scores["voice"] = round(min(100, max(0, voice_score)), 1)

    # ─── Presence Score ───────────────────────────────────────────────────────
    presence_components = []

    face_mesh = analyzer_results.get("face_mesh")
    if face_mesh and face_mesh.success:
        eye_contact = face_mesh.metrics.get("eye_contact_percentage", 60)
        eye_score = min(100, eye_contact)
        scores["eye_contact"] = round(eye_score, 1)
        presence_components.append(eye_score * 0.6)

    pose = analyzer_results.get("pose")
    if pose and pose.success:
        posture = pose.metrics.get("posture_score", 70)
        scores["posture"] = round(posture, 1)
        presence_components.append(posture * 0.4)

    if presence_components:
        total_weight = sum([0.6 if face_mesh and face_mesh.success else 0,
                            0.4 if pose and pose.success else 0])
        presence_score = sum(presence_components) / total_weight if total_weight > 0 else 65
    else:
        presence_score = 65
    scores["presence"] = round(min(100, max(0, presence_score)), 1)

    # ─── Content Score ────────────────────────────────────────────────────────
    llm = analyzer_results.get("llm")
    if llm and llm.success:
        clarity = llm.metrics.get("clarity", 70)
        organization = llm.metrics.get("organization", 70)
        persuasiveness = llm.metrics.get("persuasiveness", 65)
        evidence = llm.metrics.get("supporting_evidence", 65)
        logical_flow = llm.metrics.get("logical_flow", 70)

        scores["clarity"] = round(clarity, 1)
        scores["organization"] = round(organization, 1)
        scores["persuasiveness"] = round(persuasiveness, 1)

        content_score = (
            clarity * 0.3 +
            organization * 0.25 +
            persuasiveness * 0.2 +
            evidence * 0.15 +
            logical_flow * 0.1
        )
    else:
        content_score = 65
    scores["content"] = round(min(100, max(0, content_score)), 1)

    # ─── Overall Score ────────────────────────────────────────────────────────
    overall = (
        scores["content"] * 0.35 +
        scores["voice"] * 0.35 +
        scores["presence"] * 0.30
    )
    scores["overall"] = round(overall, 1)

    logger.info(
        f"Scores: overall={scores['overall']}, content={scores['content']}, "
        f"voice={scores['voice']}, presence={scores['presence']}"
    )
    return scores
