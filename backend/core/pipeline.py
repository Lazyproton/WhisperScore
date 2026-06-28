"""
WhisperScore — Analysis Pipeline Orchestrator
Runs all analyzers, extracts audio with FFmpeg, and aggregates results.

Analyzer execution order:
  1. FFmpeg   — extract audio from video
  2. Audio    — Whisper, Silero, librosa, Parselmouth, Expressiveness (parallel)
  3. Video    — FaceMesh, Hands, Pose  (parallel, if video enabled)
  4. LLM      — Content analysis with transcript from Whisper
  5. Scoring  — Aggregate all results into final scores
  6. Merge    — Sort all events by timestamp

Adding a new analyzer:
  1. Create a module in analyzers/ implementing BaseAnalyzer
  2. Import and instantiate it here
  3. Add its result to the results dict
  No other files need modification.
"""
import asyncio
import logging
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, Optional

from analyzers.audio.whisper       import WhisperAnalyzer
from analyzers.audio.silero        import SileroAnalyzer
from analyzers.audio.librosa_a     import LibrosaAnalyzer
from analyzers.audio.parselmouth   import ParselmouthAnalyzer
from analyzers.audio.expressiveness import VocalExpressivenessAnalyzer
from analyzers.video.face              import FaceAnalyzer
from analyzers.video.gesture           import GestureAnalyzer
from analyzers.video.grlib_plugin      import GRLibAnalyzer
from analyzers.content.llm         import LLMAnalyzer
from analyzers.scoring.engine      import compute_scores
from core.config import settings

logger = logging.getLogger(__name__)


def extract_audio(video_path: str, output_path: str) -> str:
    """
    Uses FFmpeg to extract and normalize audio from a video or audio file.
    Returns path to the extracted WAV file.
    """
    cmd = [
        "ffmpeg", "-y",
        "-i",       video_path,
        "-vn",                          # No video
        "-acodec",  "pcm_s16le",        # PCM 16-bit
        "-ar",      "16000",            # 16 kHz (required by Whisper + Silero + librosa.pyin)
        "-ac",      "1",                # Mono
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
        "-of",           "default=noprint_wrappers=1:nokey=1",
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
      2. Run audio analyzers concurrently (Whisper, Silero, librosa, Parselmouth, Expressiveness)
      3. Run video analyzers concurrently (Face, Gesture, GRLib) [if video available]
      4. Run LLM analyzer with transcript from Whisper
      5. Compute aggregate scores
      6. Merge and sort all events

    New analyzers can be added by:
      1. Creating a new module in analyzers/
      2. Instantiating it below
      3. Adding its result to the results dict
      No existing files need modification.
    """

    def __init__(self):
        # Audio analyzers
        self._whisper = WhisperAnalyzer(
            model_size=settings.WHISPER_MODEL_SIZE,
            device=settings.WHISPER_DEVICE,
            compute_type=settings.WHISPER_COMPUTE_TYPE,
        )
        self._silero        = SileroAnalyzer()
        self._librosa       = LibrosaAnalyzer()
        self._parselmouth   = ParselmouthAnalyzer()
        self._expressiveness = VocalExpressivenessAnalyzer()

        # Video analyzers
        self._face      = FaceAnalyzer()
        self._gesture   = GestureAnalyzer()
        self._grlib     = GRLibAnalyzer()

        # Content
        self._llm = LLMAnalyzer()

    def run(self, video_path: str, session_dir: str) -> dict:
        """
        Main entry point. Runs the full analysis pipeline synchronously.
        Called from a background thread by the API route.
        Returns a dict with all results, scores, and events.
        """
        logger.info(f"Starting pipeline for: {video_path}")

        # ── Step 1: Extract audio ──────────────────────────────────────────────
        audio_path = str(Path(session_dir) / "audio.wav")
        extract_audio(video_path, audio_path)
        duration = get_duration(video_path)

        # ── Step 2a: Whisper first (others need its word timestamps) ─────────
        results = {}
        results["whisper"] = self._whisper.safe_analyze(audio_path=audio_path)
        logger.info(f"[whisper] ✓ {results['whisper'].summary}")

        whisper_words = (
            results["whisper"].metrics.get("words", [])
            if results["whisper"] and results["whisper"].success
            else []
        )

        # ── Step 2b: Remaining audio analyzers (parallel) ─────────────────────
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                "silero":         executor.submit(self._silero.safe_analyze,
                                      audio_path=audio_path, word_timestamps=whisper_words),
                "librosa":        executor.submit(self._librosa.safe_analyze,       audio_path=audio_path),
                "parselmouth":    executor.submit(self._parselmouth.safe_analyze,
                                      audio_path=audio_path, word_timestamps=whisper_words),
                "expressiveness": executor.submit(self._expressiveness.safe_analyze, audio_path=audio_path),
            }
            for name, future in futures.items():
                try:
                    results[name] = future.result(timeout=300)
                    logger.info(f"[{name}] ✓ {results[name].summary}")
                except Exception as e:
                    logger.error(f"[{name}] ✗ {e}")

        # ── Step 3: Video analyzers (parallel) ────────────────────────────────
        if settings.ENABLE_VIDEO_ANALYSIS and video_path:
            with ThreadPoolExecutor(max_workers=3) as executor:
                video_futures = {
                    "face": executor.submit(
                        self._face.safe_analyze,
                        audio_path=audio_path, video_path=video_path,
                    ),
                    "gesture": executor.submit(
                        self._gesture.safe_analyze,
                        audio_path=audio_path, video_path=video_path,
                    ),
                    "grlib": executor.submit(
                        self._grlib.safe_analyze,
                        audio_path=audio_path, video_path=video_path,
                    ),
                }
                for name, future in video_futures.items():
                    try:
                        results[name] = future.result(timeout=300)
                        logger.info(f"[{name}] ✓ {results[name].summary}")
                    except Exception as e:
                        logger.error(f"[{name}] ✗ {e}")

        # ── Step 4: LLM content analysis ──────────────────────────────────────
        whisper_result = results.get("whisper")
        transcript = (
            whisper_result.metrics.get("transcript", "")
            if whisper_result and whisper_result.success
            else ""
        )
        word_timestamps = (
            whisper_result.metrics.get("words", [])
            if whisper_result and whisper_result.success
            else []
        )
        results["llm"] = self._llm.safe_analyze(
            transcript=transcript,
            duration_seconds=duration,
        )
        logger.info(f"[llm] ✓ {results['llm'].summary}")

        # ── Step 5: Compute scores ─────────────────────────────────────────────
        scores = compute_scores(results)

        # ── Step 6: Merge and sort all events ─────────────────────────────────
        all_events = []
        for name, result in results.items():
            if result and result.success:
                all_events.extend(result.events)
        all_events.sort(key=lambda e: e.timestamp)

        # ── Step 7: Assemble output ────────────────────────────────────────────
        def safe_metrics(key: str) -> dict:
            r = results.get(key)
            return r.metrics if (r and r.success) else {}

        w_m  = safe_metrics("whisper")
        s_m  = safe_metrics("silero")
        l_m  = safe_metrics("librosa")
        pm_m = safe_metrics("parselmouth")
        fm_m = safe_metrics("face")
        h_m  = safe_metrics("gesture")
        gr_m = safe_metrics("grlib")
        e_m  = safe_metrics("expressiveness")
        llm_r = results.get("llm")

        return {
            "scores":           scores,
            "events":           [e.to_dict() for e in all_events],
            "duration_seconds": duration,
            "audio_path":       audio_path,
            "metrics": {
                "voice": {
                    "avg_wpm":                  w_m.get("avg_wpm"),
                    "filler_count":             w_m.get("filler_count"),
                    "filler_words":             w_m.get("filler_words", []),
                    "pause_count":              s_m.get("pause_count"),
                    "long_pause_count":         s_m.get("long_pause_count"),
                    "speaking_duration_seconds": s_m.get("speaking_duration_seconds"),
                    "avg_pitch_hz":             pm_m.get("avg_pitch_hz"),
                    "pitch_variation":          pm_m.get("pitch_std_hz"),
                    "avg_loudness_db":          l_m.get("avg_loudness_db"),
                    "expressiveness_score":     e_m.get("expressiveness_score"),
                    "pitch_std_hz":             e_m.get("pitch_std_hz"),
                    "rms_dynamic_range":        e_m.get("rms_dynamic_range"),
                },
                "presence": {
                    "eye_contact_percentage":   fm_m.get("eye_contact_percentage"),
                    "blink_rate_per_min":       fm_m.get("blink_rate_bpm"),
                    "avg_movement_intensity":   fm_m.get("avg_movement_intensity"), # Optional placeholder
                    "posture_score":            h_m.get("gesture_score"), # Just use gesture_score for posture for now
                    "gesture_score":            h_m.get("gesture_score"),
                    "hands_visible_pct":        h_m.get("hands_visible_pct"),
                    "open_palm_pct":            h_m.get("open_palm_pct"),
                },
                "content": {
                    "word_count":               w_m.get("total_words"),
                    "transcript":               transcript,
                    "clarity":                  llm_r.metrics.get("clarity")              if llm_r and llm_r.success else None,
                    "organization":             llm_r.metrics.get("organization")         if llm_r and llm_r.success else None,
                    "persuasiveness":           llm_r.metrics.get("persuasiveness")       if llm_r and llm_r.success else None,
                    "argument_strength":        llm_r.metrics.get("argument_strength")    if llm_r and llm_r.success else None,
                    "argument_analysis":        llm_r.metrics.get("argument_analysis", {}) if llm_r and llm_r.success else {},
                },
                "voice_confidence": {
                    "vocal_confidence_score":   pm_m.get("vocal_confidence_score"),
                    "upspeak_count":            pm_m.get("upspeak_count"),
                    "jitter":                   pm_m.get("jitter"),
                    "shimmer":                  pm_m.get("shimmer"),
                    "hnr_db":                   pm_m.get("hnr_db"),
                },
                "pause_intelligence": {
                    "strategic_pause_count":    s_m.get("strategic_pause_count"),
                    "effective_pause_count":    s_m.get("effective_pause_count"),
                    "awkward_pause_count":      s_m.get("awkward_pause_count"),
                    "filler_adj_pause_count":   s_m.get("filler_adj_pause_count"),
                },
            },
            "coaching": {
                "strengths":              llm_r.metrics.get("strengths", [])              if llm_r and llm_r.success else [],
                "weaknesses":             llm_r.metrics.get("weaknesses", [])             if llm_r and llm_r.success else [],
                "tips":                   llm_r.metrics.get("tips", [])                   if llm_r and llm_r.success else [],
                "improved_excerpt":       llm_r.metrics.get("improved_excerpt", "")       if llm_r and llm_r.success else "",
                "summary":                llm_r.metrics.get("summary", "")               if llm_r and llm_r.success else "",
                "anticipated_questions":  llm_r.metrics.get("anticipated_questions", [])  if llm_r and llm_r.success else [],
            },
        }


# Singleton pipeline instance
pipeline = AnalysisPipeline()
