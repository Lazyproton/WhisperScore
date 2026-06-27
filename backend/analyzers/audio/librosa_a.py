"""
WhisperScore — librosa Acoustic Analyzer
Extracts RMS energy, loudness, spectral features, and energy events.
"""
import logging
from typing import Optional, List
from analyzers.base import BaseAnalyzer, AnalyzerResult
from analyzers.timeline.events import Event, EventSeverity, voice_event

logger = logging.getLogger(__name__)
WINDOW_SIZE = 5.0
ENERGY_DROP_THRESHOLD = 0.3


class LibrosaAnalyzer(BaseAnalyzer):
    name = "librosa"

    def analyze(self, audio_path=None, video_path=None, **kwargs) -> AnalyzerResult:
        if not audio_path:
            return AnalyzerResult(analyzer_name=self.name, success=False, error="No audio path")

        import librosa
        import numpy as np

        y, sr = librosa.load(audio_path, sr=None, mono=True)
        duration = librosa.get_duration(y=y, sr=sr)
        rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]
        rms_db = librosa.amplitude_to_db(rms, ref=np.max)
        spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        zcr = librosa.feature.zero_crossing_rate(y=y)[0]
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        avg_rms_db = float(np.mean(rms_db))
        rms_std = float(np.std(rms_db))

        hop_length = 512
        frames_per_window = int(WINDOW_SIZE * sr / hop_length)
        events: List[Event] = []
        prev_window_rms = None

        for i in range(0, len(rms), frames_per_window):
            window_rms = rms[i: i + frames_per_window]
            if len(window_rms) == 0:
                continue
            w_mean = float(np.mean(window_rms))
            t = i / (sr / hop_length)
            if prev_window_rms is not None:
                drop = (prev_window_rms - w_mean) / (prev_window_rms + 1e-9)
                if drop > ENERGY_DROP_THRESHOLD and prev_window_rms > 1e-5:
                    events.append(voice_event(
                        timestamp=t, metric="loudness",
                        title="Energy Drop Detected",
                        description="Your vocal energy dropped here. Maintain consistent projection.",
                        severity=EventSeverity.MEDIUM, score=50,
                    ))
            prev_window_rms = w_mean

        consistency_score = max(0, 100 - rms_std * 2)
        metrics = {
            "avg_loudness_db": round(avg_rms_db, 2),
            "loudness_std_db": round(rms_std, 2),
            "loudness_consistency_score": round(consistency_score, 1),
            "avg_spectral_centroid_hz": round(float(np.mean(spectral_centroid)), 1),
            "avg_zcr": round(float(np.mean(zcr)), 4),
            "estimated_tempo_bpm": round(float(tempo), 1),
            "duration_seconds": round(duration, 2),
        }
        return AnalyzerResult(
            analyzer_name=self.name, metrics=metrics, events=events,
            summary=f"Avg loudness: {avg_rms_db:.1f} dB, consistency: {consistency_score:.0f}/100",
        )
