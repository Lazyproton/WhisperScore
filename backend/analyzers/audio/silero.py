"""
WhisperScore — Silero VAD Analyzer
Uses Silero Voice Activity Detection to:
  - Detect speech vs. silence segments
  - Identify pause timestamps and durations
  - Detect unnaturally long or short pauses
"""
import logging
from typing import Optional, List, Dict
from analyzers.base import BaseAnalyzer, AnalyzerResult
from analyzers.timeline.events import Event, EventSeverity, voice_event

logger = logging.getLogger(__name__)

# Pause thresholds (seconds)
LONG_PAUSE_THRESHOLD = 2.5
VERY_LONG_PAUSE_THRESHOLD = 5.0
GOOD_PAUSE_MIN = 0.5
GOOD_PAUSE_MAX = 2.0

SAMPLE_RATE = 16000


class SileroAnalyzer(BaseAnalyzer):
    """
    Detects speech and silence segments using Silero VAD.
    Generates events for meaningful pauses.
    """

    name = "silero"

    def __init__(self):
        self._model = None
        self._utils = None

    def _load_model(self):
        if self._model is None:
            import torch
            logger.info("Loading Silero VAD model...")
            model, utils = torch.hub.load(
                repo_or_dir="snakers4/silero-vad",
                model="silero_vad",
                force_reload=False,
                onnx=False,
            )
            self._model = model
            self._utils = utils
        return self._model, self._utils

    def analyze(
        self,
        audio_path: Optional[str] = None,
        video_path: Optional[str] = None,
        **kwargs,
    ) -> AnalyzerResult:
        if not audio_path:
            return AnalyzerResult(
                analyzer_name=self.name,
                success=False,
                error="No audio path provided",
            )

        import torch
        import soundfile as sf
        import numpy as np

        try:
            model, utils = self._load_model()
            (get_speech_timestamps, _, read_audio, *_) = utils

            audio = read_audio(audio_path, sampling_rate=SAMPLE_RATE)
            duration = len(audio) / SAMPLE_RATE

            speech_timestamps = get_speech_timestamps(
                audio,
                model,
                sampling_rate=SAMPLE_RATE,
                threshold=0.5,
                min_speech_duration_ms=250,
                min_silence_duration_ms=300,
            )

            # Convert frame indices to seconds
            segments = [
                {"start": t["start"] / SAMPLE_RATE, "end": t["end"] / SAMPLE_RATE}
                for t in speech_timestamps
            ]

            # Identify pauses (gaps between speech segments)
            pauses: List[Dict] = []
            for i in range(1, len(segments)):
                pause_start = segments[i - 1]["end"]
                pause_end = segments[i]["start"]
                pause_duration = pause_end - pause_start
                if pause_duration >= 0.3:
                    pauses.append({
                        "start": pause_start,
                        "end": pause_end,
                        "duration": pause_duration,
                    })

            speaking_duration = sum(s["end"] - s["start"] for s in segments)
            silence_duration = duration - speaking_duration

            # ─── Events ──────────────────────────────────────────────
            events: List[Event] = []

            for pause in pauses:
                d = pause["duration"]
                if d >= VERY_LONG_PAUSE_THRESHOLD:
                    events.append(voice_event(
                        timestamp=pause["start"],
                        metric="pause",
                        title="Very Long Silence",
                        description=(
                            f"A {d:.1f}s silence here may lose audience attention. "
                            "Fill with a transition phrase or continue more fluently."
                        ),
                        severity=EventSeverity.HIGH,
                        score=20,
                        pause_duration=round(d, 2),
                    ))
                elif d >= LONG_PAUSE_THRESHOLD:
                    events.append(voice_event(
                        timestamp=pause["start"],
                        metric="pause",
                        title="Long Pause",
                        description=(
                            f"A {d:.1f}s pause here may feel awkward. "
                            "Strategic pauses work best at 1–2 seconds."
                        ),
                        severity=EventSeverity.MEDIUM,
                        score=55,
                        pause_duration=round(d, 2),
                    ))
                elif GOOD_PAUSE_MIN <= d <= GOOD_PAUSE_MAX:
                    events.append(voice_event(
                        timestamp=pause["start"],
                        metric="pause",
                        title="Effective Pause",
                        description=(
                            f"A {d:.1f}s pause here — great for emphasis and "
                            "letting your audience absorb what you said."
                        ),
                        severity=EventSeverity.POSITIVE,
                        score=88,
                        pause_duration=round(d, 2),
                    ))

            long_pauses = [p for p in pauses if p["duration"] >= LONG_PAUSE_THRESHOLD]
            good_pauses = [
                p for p in pauses
                if GOOD_PAUSE_MIN <= p["duration"] <= GOOD_PAUSE_MAX
            ]

            metrics = {
                "pause_count": len(pauses),
                "long_pause_count": len(long_pauses),
                "good_pause_count": len(good_pauses),
                "speaking_duration_seconds": round(speaking_duration, 2),
                "silence_duration_seconds": round(silence_duration, 2),
                "speaking_ratio": round(speaking_duration / duration, 3) if duration else 0,
                "pauses": pauses,
                "speech_segments": segments,
            }

            return AnalyzerResult(
                analyzer_name=self.name,
                metrics=metrics,
                events=events,
                summary=(
                    f"Found {len(pauses)} pauses ({len(long_pauses)} long, "
                    f"{len(good_pauses)} effective). "
                    f"Speaking {speaking_duration:.0f}s / {duration:.0f}s total."
                ),
            )

        except Exception as e:
            logger.error(f"Silero VAD failed: {e}")
            raise
