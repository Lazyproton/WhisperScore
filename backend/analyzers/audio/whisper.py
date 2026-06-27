"""
WhisperScore — Whisper Analyzer
Uses faster-whisper for:
  - Speech-to-text transcription
  - Word-level timestamps
  - Speaking rate (WPM)
  - Filler word detection
"""
import logging
from typing import Optional, List, Dict
from analyzers.base import BaseAnalyzer, AnalyzerResult
from analyzers.timeline.events import Event, EventCategory, EventSeverity, voice_event

logger = logging.getLogger(__name__)

# Common English filler words
FILLER_WORDS = {
    "um", "uh", "ah", "er", "like", "you know", "basically",
    "literally", "actually", "right", "okay", "so", "well",
    "i mean", "sort of", "kind of", "you see",
}

# WPM thresholds
WPM_TOO_FAST = 160
WPM_TOO_SLOW = 100
WPM_IDEAL_MIN = 120
WPM_IDEAL_MAX = 150

# Pause between chunks to trigger a "fast pace" event (seconds)
PACE_WINDOW = 30.0  # Check WPM per 30-second window


class WhisperAnalyzer(BaseAnalyzer):
    """
    Transcribes speech using faster-whisper and extracts
    timing and speaking-rate features.
    """

    name = "whisper"

    def __init__(self, model_size: str = "base", device: str = "cpu", compute_type: str = "int8"):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None

    def _load_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel
            logger.info(f"Loading faster-whisper model: {self.model_size}")
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
        return self._model

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

        model = self._load_model()
        logger.info(f"Transcribing: {audio_path}")

        segments, info = model.transcribe(
            audio_path,
            word_timestamps=True,
            language="en",
        )

        # Collect all words with timestamps
        words: List[Dict] = []
        transcript_parts: List[str] = []
        duration = info.duration

        for segment in segments:
            transcript_parts.append(segment.text.strip())
            if segment.words:
                for w in segment.words:
                    words.append({
                        "word": w.word.strip().lower(),
                        "start": w.start,
                        "end": w.end,
                        "probability": w.probability,
                    })

        transcript = " ".join(transcript_parts)
        total_words = len(words)
        speaking_duration = duration if duration else 1

        # ─── Speaking Rate ─────────────────────────────────────────
        avg_wpm = (total_words / speaking_duration) * 60 if speaking_duration > 0 else 0

        # ─── Filler Word Detection ─────────────────────────────────
        filler_occurrences = []
        for w in words:
            word_clean = w["word"].strip(".,!?;:'\"").lower()
            if word_clean in FILLER_WORDS:
                filler_occurrences.append(w)

        # ─── Generate Events ───────────────────────────────────────
        events: List[Event] = []

        # Per-window speaking rate events
        window_start = 0.0
        while window_start < duration:
            window_end = window_start + PACE_WINDOW
            window_words = [
                w for w in words
                if window_start <= w["start"] < window_end
            ]
            if window_words:
                window_wpm = len(window_words) / PACE_WINDOW * 60
                if window_wpm > WPM_TOO_FAST:
                    events.append(voice_event(
                        timestamp=window_start,
                        metric="pace",
                        title="Speaking Too Fast",
                        description=(
                            f"You spoke at ~{int(window_wpm)} WPM in this segment. "
                            f"Aim for {WPM_IDEAL_MIN}–{WPM_IDEAL_MAX} WPM for clarity."
                        ),
                        severity=EventSeverity.HIGH if window_wpm > 180 else EventSeverity.MEDIUM,
                        score=max(0, 100 - (window_wpm - WPM_IDEAL_MAX) * 1.5),
                        wpm=round(window_wpm, 1),
                    ))
                elif window_wpm < WPM_TOO_SLOW:
                    events.append(voice_event(
                        timestamp=window_start,
                        metric="pace",
                        title="Speaking Too Slowly",
                        description=(
                            f"Your pace dropped to ~{int(window_wpm)} WPM. "
                            "Consider picking up the tempo to maintain engagement."
                        ),
                        severity=EventSeverity.LOW,
                        score=max(0, 100 - (WPM_IDEAL_MIN - window_wpm) * 1.5),
                        wpm=round(window_wpm, 1),
                    ))
                elif WPM_IDEAL_MIN <= window_wpm <= WPM_IDEAL_MAX:
                    if len(events) == 0 or window_start > 60:
                        events.append(voice_event(
                            timestamp=window_start,
                            metric="pace",
                            title="Excellent Speaking Pace",
                            description=(
                                f"Great pacing at ~{int(window_wpm)} WPM — "
                                "clear and engaging for your audience."
                            ),
                            severity=EventSeverity.POSITIVE,
                            score=90,
                            wpm=round(window_wpm, 1),
                        ))
            window_start += PACE_WINDOW

        # Filler word events (grouped — one event per 3 fillers)
        if filler_occurrences:
            for i, filler in enumerate(filler_occurrences):
                if i % 3 == 0:  # Event every 3rd occurrence
                    count_in_window = min(3, len(filler_occurrences) - i)
                    events.append(voice_event(
                        timestamp=filler["start"],
                        metric="fillers",
                        title="Filler Words Detected",
                        description=(
                            f'Detected \"{filler["word"]}\" and similar fillers here. '
                            "Replace with a confident pause or rephrase."
                        ),
                        severity=EventSeverity.MEDIUM if len(filler_occurrences) > 5 else EventSeverity.LOW,
                        score=max(30, 100 - len(filler_occurrences) * 5),
                        filler_word=filler["word"],
                        count=count_in_window,
                    ))

        metrics = {
            "avg_wpm": round(avg_wpm, 1),
            "total_words": total_words,
            "duration_seconds": round(duration, 2),
            "filler_count": len(filler_occurrences),
            "filler_words": list({w["word"] for w in filler_occurrences}),
            "transcript": transcript,
            "words": words,
        }

        return AnalyzerResult(
            analyzer_name=self.name,
            metrics=metrics,
            events=events,
            summary=(
                f"Transcribed {total_words} words in {duration:.0f}s "
                f"(avg {avg_wpm:.0f} WPM, {len(filler_occurrences)} fillers)"
            ),
        )
