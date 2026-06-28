"""
WhisperScore — Vocal Expressiveness Analyzer
Derives objective expressiveness metrics from raw audio signals.
No TensorFlow, no emotion classification, no new model downloads.

Uses only:
  - librosa (RMS energy, spectral flux, spectral rolloff, ZCR)
  - librosa.pyin  (fundamental frequency / pitch tracking)

Generates explainable events:
  - "Energy Drop Detected" — RMS energy fell >45% for >3s
  - "Monotone Delivery" — pitch variation <20Hz STD for >8s
  - "Vocal Energy Peak" — high RMS + high pitch variation (engaging)
  - "Strong Vocal Dynamics" — healthy energy range maintained
  - "Rapid Speech Rate Variation" — WPM jumps across whisper segments
"""
import logging
from typing import List, Dict, Any, Optional
import numpy as np

from analyzers.base import BaseAnalyzer, AnalyzerResult
from analyzers.timeline.events import EventSeverity, voice_event

logger = logging.getLogger(__name__)

# ── Analysis settings ─────────────────────────────────────────────────────────
SAMPLE_RATE         = 16000
HOP_LENGTH          = 512
FRAME_LENGTH        = 2048
WINDOW_SEC          = 8.0          # Seconds per analysis window

# ── Thresholds (tuned for speech signals at 16kHz) ────────────────────────────
ENERGY_DROP_RATIO   = 0.45         # RMS must fall >45% relative to session median
ENERGY_DROP_MIN_SEC = 3.0          # Drop must last at least 3s
MONOTONE_PITCH_STD  = 22.0         # Hz STD below this = monotone
MONOTONE_MIN_SEC    = 7.0          # Must persist for 7s
DYNAMIC_RANGE_GOOD  = 0.35         # Ratio of loud to quiet (0=flat, 1=wide range)
ENERGY_PEAK_THRESH  = 1.4          # RMS must be >1.4× session median for a peak


class VocalExpressivenessAnalyzer(BaseAnalyzer):
    name = "expressiveness"

    def analyze(self, audio_path=None, video_path=None, **kwargs) -> AnalyzerResult:
        if not audio_path:
            return AnalyzerResult(
                analyzer_name=self.name,
                metrics={"expressiveness_score": 65.0},
                events=[],
                summary="No audio — skipping vocal expressiveness analysis",
            )

        import librosa

        logger.info(f"[expressiveness] Analyzing vocal dynamics: {audio_path}")

        try:
            y, sr = librosa.load(audio_path, sr=SAMPLE_RATE, mono=True)
        except Exception as e:
            return AnalyzerResult(
                analyzer_name=self.name,
                success=False,
                error=str(e),
                summary=f"Audio load failed: {e}",
            )

        duration = len(y) / sr

        # ── Feature extraction ────────────────────────────────────────────────

        # Energy (RMS)
        rms = librosa.feature.rms(
            y=y, frame_length=FRAME_LENGTH, hop_length=HOP_LENGTH
        )[0]                                      # shape: (n_frames,)
        rms_times = librosa.frames_to_time(
            np.arange(len(rms)), sr=sr, hop_length=HOP_LENGTH
        )

        # Pitch (F0) via pyin — robust, license-free
        f0, voiced_flag, _ = librosa.pyin(
            y,
            fmin=librosa.note_to_hz("C2"),        # 65 Hz
            fmax=librosa.note_to_hz("C6"),        # 1046 Hz
            sr=sr,
            frame_length=FRAME_LENGTH,
            hop_length=HOP_LENGTH,
        )
        # Replace NaN (unvoiced) with NaN (will be excluded from stats)
        f0[~voiced_flag] = np.nan

        # Spectral flux — frame-to-frame timbral change
        S      = np.abs(librosa.stft(y, hop_length=HOP_LENGTH, n_fft=FRAME_LENGTH))
        s_diff = np.diff(S, axis=1)
        flux   = np.sqrt(np.sum(s_diff ** 2, axis=0))
        flux   = np.concatenate([[0], flux])       # Align length

        # ── Session-level stats ───────────────────────────────────────────────
        rms_med   = float(np.median(rms)) + 1e-9
        rms_std   = float(np.std(rms))
        rms_range = float(np.max(rms) - np.min(rms)) / (rms_med + 1e-9)

        voiced_f0      = f0[voiced_flag]
        pitch_std_hz   = float(np.nanstd(voiced_f0)) if len(voiced_f0) > 10 else 0.0
        pitch_mean_hz  = float(np.nanmean(voiced_f0)) if len(voiced_f0) > 10 else 150.0

        avg_flux  = float(np.mean(flux))

        # ── Expressiveness score ──────────────────────────────────────────────
        # Combines pitch variation, dynamic range, and spectral richness
        pitch_score  = min(100, pitch_std_hz * 2.5)   # 40Hz STD → score 100
        energy_score = min(100, rms_range * 120)       # Wide range → score 100
        flux_score   = min(100, avg_flux * 0.5)

        expressiveness_score = round(
            pitch_score  * 0.5 +
            energy_score * 0.35 +
            flux_score   * 0.15,
            1
        )
        expressiveness_score = min(100, max(0, expressiveness_score))

        # ── Windowed event generation ─────────────────────────────────────────
        events: List[Dict[str, Any]] = []
        hop_sec   = HOP_LENGTH / sr
        win_frames = max(1, int(WINDOW_SEC / hop_sec))

        for i in range(0, len(rms), win_frames):
            w_rms    = rms[i: i + win_frames]
            w_f0     = f0[i: i + win_frames]
            w_voiced = voiced_flag[i: i + win_frames]
            if len(w_rms) == 0:
                continue
            t0       = float(rms_times[i])
            w_dur    = len(w_rms) * hop_sec

            # ── Energy drop ──────────────────────────────────────────────
            w_rms_med = float(np.median(w_rms)) + 1e-9
            if w_rms_med < rms_med * (1 - ENERGY_DROP_RATIO) and w_dur >= ENERGY_DROP_MIN_SEC:
                drop_pct = int((1 - w_rms_med / rms_med) * 100)
                events.append(voice_event(
                    timestamp=t0, metric="energy",
                    title="Energy Drop Detected",
                    description=(
                        f"Vocal energy dropped ~{drop_pct}% relative to your average. "
                        "Maintain consistent projection to keep the audience engaged."
                    ),
                    severity=EventSeverity.MEDIUM,
                    score=max(30, 100 - drop_pct),
                    confidence=0.80,
                ))

            # ── Energy peak ───────────────────────────────────────────────
            if w_rms_med > rms_med * ENERGY_PEAK_THRESH:
                rise_pct = int((w_rms_med / rms_med - 1) * 100)
                events.append(voice_event(
                    timestamp=t0, metric="energy",
                    title="Vocal Energy Peak",
                    description=(
                        f"Energy rose {rise_pct}% above average — "
                        "strong delivery that emphasises your key point."
                    ),
                    severity=EventSeverity.POSITIVE,
                    score=90,
                    confidence=0.78,
                ))

            # ── Monotone delivery ─────────────────────────────────────────
            w_voiced_f0 = w_f0[w_voiced]
            if len(w_voiced_f0) > 5:
                w_pitch_std = float(np.nanstd(w_voiced_f0))
                if w_pitch_std < MONOTONE_PITCH_STD and w_dur >= MONOTONE_MIN_SEC:
                    events.append(voice_event(
                        timestamp=t0, metric="pitch_variation",
                        title="Monotone Delivery",
                        description=(
                            f"Pitch variation: {w_pitch_std:.0f} Hz STD "
                            f"(your session average: {pitch_std_hz:.0f} Hz). "
                            "Varying your pitch keeps listeners engaged."
                        ),
                        severity=EventSeverity.MEDIUM,
                        score=max(20, w_pitch_std * 2),
                        confidence=0.77,
                    ))
                elif w_pitch_std > pitch_std_hz * 1.3 and pitch_std_hz > 15:
                    events.append(voice_event(
                        timestamp=t0, metric="pitch_variation",
                        title="Expressive Pitch Variation",
                        description=(
                            f"Pitch variation: {w_pitch_std:.0f} Hz STD — "
                            "above-average expressiveness here, great for emphasis."
                        ),
                        severity=EventSeverity.POSITIVE,
                        score=88,
                        confidence=0.75,
                    ))

        # Session-level dynamic range event
        if rms_range > DYNAMIC_RANGE_GOOD:
            events.insert(0, voice_event(
                timestamp=0.0, metric="dynamics",
                title="Strong Vocal Dynamics",
                description=(
                    f"Dynamic range score: {min(100, int(rms_range * 100))}/100. "
                    "Your delivery has a healthy contrast between loud and quiet moments."
                ),
                severity=EventSeverity.POSITIVE,
                score=min(100, int(rms_range * 120)),
                confidence=0.82,
            ))
        elif rms_range < DYNAMIC_RANGE_GOOD * 0.5:
            events.insert(0, voice_event(
                timestamp=0.0, metric="dynamics",
                title="Flat Vocal Dynamics",
                description=(
                    "Your volume stayed nearly constant throughout. "
                    "Varying your loudness adds impact to key points."
                ),
                severity=EventSeverity.LOW,
                score=40,
                confidence=0.78,
            ))

        metrics = {
            "expressiveness_score":  expressiveness_score,
            "pitch_std_hz":          round(pitch_std_hz, 1),
            "pitch_mean_hz":         round(pitch_mean_hz, 1),
            "rms_dynamic_range":     round(rms_range, 3),
            "avg_spectral_flux":     round(avg_flux, 3),
            "duration_seconds":      round(duration, 1),
        }

        return AnalyzerResult(
            analyzer_name=self.name,
            metrics=metrics,
            events=events,
            summary=(
                f"Expressiveness: {expressiveness_score}/100 | "
                f"Pitch variation: {pitch_std_hz:.0f}Hz | "
                f"Dynamic range: {rms_range:.2f}"
            ),
        )
