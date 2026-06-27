"""
WhisperScore — Parselmouth (Praat) Analyzer
Extracts advanced vocal quality metrics:
  - Pitch (F0) mean and variation
  - Jitter (pitch stability)
  - Shimmer (amplitude stability)
  - Harmonics-to-Noise Ratio (HNR)
"""
import logging
from typing import Optional
from analyzers.base import BaseAnalyzer, AnalyzerResult
from analyzers.timeline.events import EventSeverity, voice_event

logger = logging.getLogger(__name__)

# Thresholds
JITTER_HIGH = 0.02    # > 2% jitter = vocal strain
SHIMMER_HIGH = 0.08   # > 8% shimmer = breathiness
HNR_LOW = 10.0        # < 10 dB HNR = hoarse/breathy
PITCH_VAR_LOW = 20.0  # < 20 Hz std = monotone


class ParselmouthAnalyzer(BaseAnalyzer):
    name = "parselmouth"

    def analyze(self, audio_path=None, video_path=None, **kwargs) -> AnalyzerResult:
        if not audio_path:
            return AnalyzerResult(analyzer_name=self.name, success=False, error="No audio path")

        import parselmouth
        from parselmouth.praat import call
        import numpy as np

        logger.info(f"Running Parselmouth analysis on: {audio_path}")
        snd = parselmouth.Sound(audio_path)

        # Pitch analysis
        pitch = call(snd, "To Pitch", 0.0, 75, 500)
        pitch_values = pitch.selected_array["frequency"]
        voiced = pitch_values[pitch_values > 0]

        avg_pitch = float(np.mean(voiced)) if len(voiced) > 0 else 0.0
        pitch_std = float(np.std(voiced)) if len(voiced) > 0 else 0.0

        # Point process for jitter/shimmer
        point_process = call(snd, "To PointProcess (periodic, cc)", 75, 500)
        jitter = call(point_process, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3)
        shimmer = call([snd, point_process], "Get shimmer (local)", 0, 0, 0.0001, 0.02, 1.3, 1.6)

        # HNR
        harmonicity = call(snd, "To Harmonicity (cc)", 0.01, 75, 0.1, 1.0)
        hnr = call(harmonicity, "Get mean", 0, 0)

        events = []

        # Monotone detection
        if pitch_std < PITCH_VAR_LOW:
            events.append(voice_event(
                timestamp=0.0, metric="pitch_variation",
                title="Monotone Delivery",
                description=(
                    f"Your pitch varied only {pitch_std:.0f} Hz — this sounds monotone. "
                    "Use intentional pitch rises and falls to keep listeners engaged."
                ),
                severity=EventSeverity.HIGH,
                score=max(20, pitch_std * 2),
            ))
        else:
            events.append(voice_event(
                timestamp=0.0, metric="pitch_variation",
                title="Good Pitch Variation",
                description=f"Your pitch varies {pitch_std:.0f} Hz — expressive and engaging.",
                severity=EventSeverity.POSITIVE, score=85,
            ))

        # Jitter
        if jitter > JITTER_HIGH:
            events.append(voice_event(
                timestamp=0.0, metric="jitter",
                title="Vocal Tension Detected",
                description=(
                    f"Jitter of {jitter*100:.1f}% suggests vocal tension or nervousness. "
                    "Practice deep breathing exercises before speaking."
                ),
                severity=EventSeverity.MEDIUM, score=50,
            ))

        # HNR
        if hnr < HNR_LOW:
            events.append(voice_event(
                timestamp=0.0, metric="hnr",
                title="Breathy Voice Quality",
                description=(
                    f"Low HNR ({hnr:.1f} dB) indicates breathiness. "
                    "Engage your diaphragm more fully for a cleaner, projected voice."
                ),
                severity=EventSeverity.LOW, score=60,
            ))

        # Pitch variation score
        pitch_var_score = min(100, max(0, (pitch_std / 80) * 100))

        metrics = {
            "avg_pitch_hz": round(avg_pitch, 1),
            "pitch_std_hz": round(pitch_std, 1),
            "pitch_variation_score": round(pitch_var_score, 1),
            "jitter": round(float(jitter), 4),
            "shimmer": round(float(shimmer), 4),
            "hnr_db": round(float(hnr), 2),
        }

        return AnalyzerResult(
            analyzer_name=self.name, metrics=metrics, events=events,
            summary=f"Pitch: {avg_pitch:.0f} Hz (±{pitch_std:.0f}), Jitter: {jitter*100:.1f}%, HNR: {hnr:.1f} dB",
        )
