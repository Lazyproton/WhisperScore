"""
WhisperScore — Analysis Pipeline Orchestrator
Runs all analyzers, extracts audio with FFmpeg, and aggregates results.
"""
import asyncio
import logging
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, Optional

from analyzers.audio.whisper import WhisperAnalyzer
from analyzers.audio.silero import SileroAnalyzer
from analyzers.audio.librosa_a import LibrosaAnalyzer
from analyzers.audio.parselmouth import ParselmouthAnalyzer
from analyzers.video.face_mesh import FaceMeshAnalyzer
from analyzers.video.pose import PoseAnalyzer
from analyzers.content.llm import LLMAnalyzer
from analyzers.scoring.engine import compute_scores
from analyzers.timeline.events import Event
from core.config import settings

logger = logging.getLogger(__name__)


def extract_audio(video_path: str, output_path: str) -> str:
    """
    Uses FFmpeg to extract and normalize audio from a video or audio file.
    Returns path to the extracted WAV file.
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vn",                          # No video
        "-acodec", "pcm_s16le",         # PCM 16-bit
        "-ar", "16000",                 # 16 kHz (required by Whisper + Silero)
        "-ac", "1",                     # Mono
        "-loglevel", "error",
        output_path,
    ]
    logger.info(f"Extracting audio: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed: {result.stderr}")
    return output_path


def get_duration(file_path: str) -> float:
    """Get media duration via ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except Exception:
        return 0.0


class AnalysisPipeline:
    """
    Orchestrates all analyzers for a given recording.

    Architecture:
      1. Extract audio with FFmpeg (always)
      2. Run audio analyzers concurrently (Whisper, Silero, librosa, Parselmouth)
      3. Run video analyzers concurrently (FaceMesh, Pose) [if video available]
      4. Run LLM analyzer with transcript from Whisper
      5. Compute aggregate scores
      6. Merge and sort all events

    New analyzers can be added by:
      1. Creating a new module in analyzers/
      2. Instantiating it in _run_audio_analyzers / _run_video_analyzers
      3. Adding its result to the results dict
      No existing files need modification.
    """

    def __init__(self):
        self._whisper = WhisperAnalyzer(
            model_size=settings.WHISPER_MODEL_SIZE,
            device=settings.WHISPER_DEVICE,
            compute_type=settings.WHISPER_COMPUTE_TYPE,
        )
        self._silero = SileroAnalyzer()
        self._librosa = LibrosaAnalyzer()
        self._parselmouth = ParselmouthAnalyzer()
        self._face_mesh = FaceMeshAnalyzer()
        self._pose = PoseAnalyzer()
        self._llm = LLMAnalyzer()

    def run(self, video_path: str, session_dir: str) -> dict:
        """
        Main entry point. Runs the full analysis pipeline synchronously.
        Called from a background thread by the API route.

        Returns a dict with all results, scores, and events.
        """
        logger.info(f"Starting pipeline for: {video_path}")

        # ── Step 1: Extract audio ──────────────────────────────────────────
        audio_path = str(Path(session_dir) / "audio.wav")
        extract_audio(video_path, audio_path)
        duration = get_duration(video_path)

        # ── Step 2: Run audio analyzers ────────────────────────────────────
        results = {}
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                "whisper": executor.submit(
                    self._whisper.safe_analyze, audio_path=audio_path
                ),
                "silero": executor.submit(
                    self._silero.safe_analyze, audio_path=audio_path
                ),
                "librosa": executor.submit(
                    self._librosa.safe_analyze, audio_path=audio_path
                ),
                "parselmouth": executor.submit(
                    self._parselmouth.safe_analyze, audio_path=audio_path
                ),
            }
            for name, future in futures.items():
                try:
                    results[name] = future.result(timeout=300)
                    logger.info(f"[{name}] complete: {results[name].summary}")
                except Exception as e:
                    logger.error(f"[{name}] failed: {e}")

        # ── Step 3: Run video analyzers ────────────────────────────────────
        if settings.ENABLE_VIDEO_ANALYSIS and video_path:
            with ThreadPoolExecutor(max_workers=2) as executor:
                video_futures = {
                    "face_mesh": executor.submit(
                        self._face_mesh.safe_analyze,
                        audio_path=audio_path,
                        video_path=video_path,
                    ),
                    "pose": executor.submit(
                        self._pose.safe_analyze,
                        audio_path=audio_path,
                        video_path=video_path,
                    ),
                }
                for name, future in video_futures.items():
                    try:
                        results[name] = future.result(timeout=300)
                        logger.info(f"[{name}] complete: {results[name].summary}")
                    except Exception as e:
                        logger.error(f"[{name}] failed: {e}")

        # ── Step 4: LLM content analysis ───────────────────────────────────
        whisper_result = results.get("whisper")
        transcript = (
            whisper_result.metrics.get("transcript", "")
            if whisper_result and whisper_result.success
            else ""
        )
        results["llm"] = self._llm.safe_analyze(
            transcript=transcript,
            duration_seconds=duration,
        )
        logger.info(f"[llm] complete: {results['llm'].summary}")

        # ── Step 5: Compute scores ─────────────────────────────────────────
        scores = compute_scores(results)

        # ── Step 6: Merge and sort all events ──────────────────────────────
        all_events = []
        for name, result in results.items():
            if result and result.success:
                all_events.extend(result.events)

        all_events.sort(key=lambda e: e.timestamp)

        # ── Step 7: Assemble output ────────────────────────────────────────
        whisper_metrics = whisper_result.metrics if (whisper_result and whisper_result.success) else {}
        silero_result = results.get("silero")
        silero_metrics = silero_result.metrics if (silero_result and silero_result.success) else {}
        librosa_result = results.get("librosa")
        parselmouth_result = results.get("parselmouth")
        face_result = results.get("face_mesh")
        pose_result = results.get("pose")
        llm_result = results.get("llm")

        return {
            "scores": scores,
            "events": [e.to_dict() for e in all_events],
            "duration_seconds": duration,
            "audio_path": audio_path,
            "metrics": {
                "voice": {
                    "avg_wpm": whisper_metrics.get("avg_wpm"),
                    "filler_count": whisper_metrics.get("filler_count"),
                    "filler_words": whisper_metrics.get("filler_words", []),
                    "pause_count": silero_metrics.get("pause_count"),
                    "long_pause_count": silero_metrics.get("long_pause_count"),
                    "speaking_duration_seconds": silero_metrics.get("speaking_duration_seconds"),
                    "avg_pitch_hz": (parselmouth_result.metrics.get("avg_pitch_hz") if parselmouth_result and parselmouth_result.success else None),
                    "pitch_variation": (parselmouth_result.metrics.get("pitch_std_hz") if parselmouth_result and parselmouth_result.success else None),
                    "avg_loudness_db": (librosa_result.metrics.get("avg_loudness_db") if librosa_result and librosa_result.success else None),
                },
                "presence": {
                    "eye_contact_percentage": (face_result.metrics.get("eye_contact_percentage") if face_result and face_result.success else None),
                    "posture_score": (pose_result.metrics.get("posture_score") if pose_result and pose_result.success else None),
                },
                "content": {
                    "word_count": whisper_metrics.get("total_words"),
                    "transcript": transcript,
                },
            },
            "coaching": {
                "strengths": (llm_result.metrics.get("strengths", []) if llm_result and llm_result.success else []),
                "weaknesses": (llm_result.metrics.get("weaknesses", []) if llm_result and llm_result.success else []),
                "tips": (llm_result.metrics.get("tips", []) if llm_result and llm_result.success else []),
                "improved_excerpt": (llm_result.metrics.get("improved_excerpt", "") if llm_result and llm_result.success else ""),
                "summary": (llm_result.metrics.get("summary", "") if llm_result and llm_result.success else ""),
            },
        }


# Singleton pipeline instance
pipeline = AnalysisPipeline()
