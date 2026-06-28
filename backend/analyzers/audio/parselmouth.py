"""
WhisperScore — Parselmouth (Praat) Analyzer  (Feature 9: Vocal Confidence)
Extracts advanced vocal quality metrics:
  - Pitch (F0) mean and variation
  - Jitter (pitch cycle-to-cycle instability → vocal tension/nervousness)
  - Shimmer (amplitude instability → breathiness/hoarseness)
  - Harmonics-to-Noise Ratio / HNR (vocal clarity, projection quality)
  - Upspeak detection (rising terminal pitch on statements → low confidence)
  - Vocal confidence composite score
"""
import logging
from typing import Optional, List
import numpy as np

from analyzers.base import BaseAnalyzer, AnalyzerResult
from analyzers.timeline.events import EventSeverity, voice_event

logger = logging.getLogger(__name__)

# ── Thresholds ────────────────────────────────────────────────────────────────
JITTER_HIGH           = 0.020   # > 2%  jitter  = vocal tension
JITTER_VERY_HIGH      = 0.040   # > 4%  jitter  = significant strain
SHIMMER_HIGH          = 0.080   # > 8%  shimmer = breathiness
SHIMMER_VERY_HIGH     = 0.140   # > 14% shimmer = hoarseness
HNR_LOW               = 10.0    # < 10 dB HNR   = breathy/strained
HNR_VERY_LOW          = 5.0     # < 5  dB HNR   = very poor vocal quality
PITCH_VAR_LOW         = 20.0    # < 20 Hz std   = monotone
UPSPEAK_RISE_HZ       = 15.0    # terminal pitch rise > 15 Hz on a "statement" = upspeak
UPSPEAK_WINDOW        = 0.25    # seconds at end of utterance to sample
UPSPEAK_MIN_EVENTS    = 3       # how many to flag before generating an event


class ParselmouthAnalyzer(BaseAnalyzer):
    name = "parselmouth"

    def analyze(self, audio_path=None, video_path=None, **kwargs) -> AnalyzerResult:
        if not audio_path:
            return AnalyzerResult(analyzer_name=self.name, success=False, error="No audio path")

        import parselmouth
        from parselmouth.praat import call

        logger.info(f"Running Parselmouth analysis on: {audio_path}")
        snd = parselmouth.Sound(audio_path)
        duration = snd.duration

        # ── Pitch ─────────────────────────────────────────────────────────────
        pitch_obj = call(snd, "To Pitch", 0.0, 75, 500)
        pitch_values = pitch_obj.selected_array["frequency"]
        voiced = pitch_values[pitch_values > 0]

        avg_pitch = float(np.mean(voiced))  if len(voiced) > 0 else 0.0
        pitch_std = float(np.std(voiced))   if len(voiced) > 0 else 0.0

        # ── Jitter & Shimmer ──────────────────────────────────────────────────
        point_process = call(snd, "To PointProcess (periodic, cc)", 75, 500)
        jitter   = call(point_process, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3)
        shimmer  = call([snd, point_process], "Get shimmer (local)", 0, 0, 0.0001, 0.02, 1.3, 1.6)

        # ── HNR ───────────────────────────────────────────────────────────────
        harmonicity = call(snd, "To Harmonicity (cc)", 0.01, 75, 0.1, 1.0)
        hnr = call(harmonicity, "Get mean", 0, 0)

        # ── Upspeak Detection ─────────────────────────────────────────────────
        # Sample pitch at the tail of each speech segment and check for
        # a significant rising contour (terminal rise on statements).
        word_timestamps: List[dict] = kwargs.get("word_timestamps", [])
        upspeak_count = 0
        upspeak_timestamps: List[float] = []

        if word_timestamps and len(voiced) > 0:
            # Group words into utterances (split on long pauses > 0.5s)
            utterances: List[List[dict]] = []
            current: List[dict] = [word_timestamps[0]]
            for i in range(1, len(word_timestamps)):
                gap = word_timestamps[i]["start"] - word_timestamps[i - 1]["end"]
                if gap > 0.5:
                    utterances.append(current)
                    current = []
                current.append(word_timestamps[i])
            if current:
                utterances.append(current)

            for utt in utterances:
                if not utt:
                    continue
                utt_end = utt[-1].get("end", 0.0)
                if utt_end < UPSPEAK_WINDOW * 2:
                    continue
                # Sample pitch at mid-utterance vs end
                mid_t  = utt_end - UPSPEAK_WINDOW * 2
                end_t  = utt_end - 0.05

                try:
                    pitch_mid = call(pitch_obj, "Get value at time",
                                     mid_t, "Hertz", "Linear")
                    pitch_end = call(pitch_obj, "Get value at time",
                                     end_t, "Hertz", "Linear")

                    if (pitch_mid and pitch_end
                            and pitch_mid > 0 and pitch_end > 0):
                        rise = pitch_end - pitch_mid
                        last_word_text = utt[-1].get("word", "").strip()
                        is_question = last_word_text.endswith("?")

                        if rise > UPSPEAK_RISE_HZ and not is_question:
                            upspeak_count += 1
                            upspeak_timestamps.append(utt_end - UPSPEAK_WINDOW)
                except Exception:
                    pass

        # ── Vocal Confidence Score ────────────────────────────────────────────
        # Composite: lower jitter/shimmer + higher HNR + low upspeak = confident
        jitter_score   = max(0, min(100, 100 - (jitter / JITTER_VERY_HIGH) * 80))
        shimmer_score  = max(0, min(100, 100 - (shimmer / SHIMMER_VERY_HIGH) * 80))
        hnr_score      = max(0, min(100, (hnr / 20.0) * 100))  # 20 dB = excellent
        upspeak_penalty = min(30, upspeak_count * 5)           # up to -30 points
        pitch_var_score = min(100, max(0, (pitch_std / 80) * 100))

        vocal_confidence = (
            jitter_score  * 0.20 +
            shimmer_score * 0.20 +
            hnr_score     * 0.30 +
            pitch_var_score * 0.15 +
            max(0, 100 - upspeak_penalty) * 0.15
        )

        # ── Events ────────────────────────────────────────────────────────────
        events = []

        # Pitch variation
        if pitch_std < PITCH_VAR_LOW:
            events.append(voice_event(
                timestamp=0.0, metric="pitch_variation",
                title="Monotone Delivery",
                description=(
                    f"Your pitch varied only {pitch_std:.0f} Hz — sounds flat. "
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
        if jitter > JITTER_VERY_HIGH:
            events.append(voice_event(
                timestamp=0.0, metric="vocal_tension",
                title="High Vocal Tension",
                description=(
                    f"Jitter of {jitter * 100:.1f}% indicates significant vocal strain. "
                    "Practice slow diaphragmatic breathing before speaking."
                ),
                severity=EventSeverity.HIGH, score=30,
                jitter=round(float(jitter), 4),
            ))
        elif jitter > JITTER_HIGH:
            events.append(voice_event(
                timestamp=0.0, metric="vocal_tension",
                title="Mild Vocal Tension",
                description=(
                    f"Jitter of {jitter * 100:.1f}% suggests some nervousness. "
                    "Warm up your voice and breathe deeply before presentations."
                ),
                severity=EventSeverity.MEDIUM, score=55,
                jitter=round(float(jitter), 4),
            ))

        # Shimmer
        if shimmer > SHIMMER_VERY_HIGH:
            events.append(voice_event(
                timestamp=0.0, metric="vocal_clarity",
                title="Breathy / Hoarse Voice",
                description=(
                    f"Shimmer of {shimmer * 100:.1f}% indicates breathiness or hoarseness. "
                    "Engage your core and project from the diaphragm."
                ),
                severity=EventSeverity.HIGH, score=30,
                shimmer=round(float(shimmer), 4),
            ))
        elif shimmer > SHIMMER_HIGH:
            events.append(voice_event(
                timestamp=0.0, metric="vocal_clarity",
                title="Slightly Breathy Voice",
                description=(
                    f"Shimmer of {shimmer * 100:.1f}% — voice is slightly breathy. "
                    "Focus on clear consonants and fuller breath support."
                ),
                severity=EventSeverity.LOW, score=65,
                shimmer=round(float(shimmer), 4),
            ))

        # HNR
        if hnr < HNR_VERY_LOW:
            events.append(voice_event(
                timestamp=0.0, metric="vocal_clarity",
                title="Poor Vocal Clarity",
                description=(
                    f"HNR of {hnr:.1f} dB — voice lacks clear harmonic resonance. "
                    "Hydrate well and avoid straining your voice before recording."
                ),
                severity=EventSeverity.HIGH, score=25,
                hnr_db=round(float(hnr), 2),
            ))
        elif hnr < HNR_LOW:
            events.append(voice_event(
                timestamp=0.0, metric="vocal_clarity",
                title="Breathy Voice Quality",
                description=(
                    f"Low HNR ({hnr:.1f} dB) indicates breathiness. "
                    "Engage your diaphragm more fully for a cleaner, projected voice."
                ),
                severity=EventSeverity.LOW, score=60,
                hnr_db=round(float(hnr), 2),
            ))

        # Upspeak
        if upspeak_count >= UPSPEAK_MIN_EVENTS:
            # Pin event to the first detected upspeak
            ts = upspeak_timestamps[0] if upspeak_timestamps else 0.0
            events.append(voice_event(
                timestamp=ts, metric="vocal_confidence",
                title="Upspeak Detected",
                description=(
                    f"Rising pitch at the end of {upspeak_count} statements sounds like questions. "
                    "End declarative sentences with a downward pitch to project confidence."
                ),
                severity=EventSeverity.MEDIUM,
                score=max(40, 100 - upspeak_count * 8),
                upspeak_count=upspeak_count,
            ))
        elif upspeak_count == 0 and len(word_timestamps) > 20:
            events.append(voice_event(
                timestamp=0.0, metric="vocal_confidence",
                title="Confident Statement Endings",
                description="Your statements end with downward intonation — projects authority and confidence.",
                severity=EventSeverity.POSITIVE, score=90,
            ))

        # Overall vocal confidence event
        if vocal_confidence >= 75:
            events.append(voice_event(
                timestamp=0.0, metric="vocal_confidence",
                title="Strong Vocal Confidence",
                description=f"Composite vocal confidence score: {vocal_confidence:.0f}/100 — clear, stable, and assured delivery.",
                severity=EventSeverity.POSITIVE, score=round(vocal_confidence, 1),
            ))
        elif vocal_confidence < 50:
            events.append(voice_event(
                timestamp=0.0, metric="vocal_confidence",
                title="Low Vocal Confidence",
                description=(
                    f"Composite vocal confidence score: {vocal_confidence:.0f}/100. "
                    "Focus on breath support, reducing jitter, and ending statements firmly."
                ),
                severity=EventSeverity.HIGH, score=round(vocal_confidence, 1),
            ))

        metrics = {
            "avg_pitch_hz":           round(avg_pitch, 1),
            "pitch_std_hz":           round(pitch_std, 1),
            "pitch_variation_score":  round(pitch_var_score, 1),
            "jitter":                 round(float(jitter), 4),
            "shimmer":                round(float(shimmer), 4),
            "hnr_db":                 round(float(hnr), 2),
            "upspeak_count":          upspeak_count,
            "jitter_score":           round(jitter_score, 1),
            "shimmer_score":          round(shimmer_score, 1),
            "hnr_score":              round(hnr_score, 1),
            "vocal_confidence_score": round(vocal_confidence, 1),
        }

        return AnalyzerResult(
            analyzer_name=self.name, metrics=metrics, events=events,
            summary=(
                f"Pitch: {avg_pitch:.0f} Hz (±{pitch_std:.0f}), "
                f"Jitter: {jitter * 100:.1f}%, Shimmer: {shimmer * 100:.1f}%, "
                f"HNR: {hnr:.1f} dB, Upspeak: {upspeak_count}x, "
                f"Vocal Confidence: {vocal_confidence:.0f}/100"
            ),
        )
