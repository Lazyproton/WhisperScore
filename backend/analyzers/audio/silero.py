"""
WhisperScore — Silero VAD Analyzer  (Feature 4: Pause Intelligence)
Uses Silero Voice Activity Detection to:
  - Detect speech vs. silence segments
  - Identify pause timestamps and durations
  - Classify pauses:
      strategic   — 0.8–2.0s before a sentence start (emphasis)
      awkward     — mid-sentence, short silence with no apparent cause
      very_long   — > 5s, likely a distraction
      filler_adj  — immediately follows a filler word (uh/um territory)
      effective   — 0.5–2.0s at sentence boundary, clean
"""
import logging
from typing import Optional, List, Dict
from analyzers.base import BaseAnalyzer, AnalyzerResult
from analyzers.timeline.events import Event, EventSeverity, voice_event

logger = logging.getLogger(__name__)

# Pause thresholds (seconds)
LONG_PAUSE_THRESHOLD      = 2.5
VERY_LONG_PAUSE_THRESHOLD = 5.0
GOOD_PAUSE_MIN            = 0.5
GOOD_PAUSE_MAX            = 2.0
STRATEGIC_MAX             = 2.0   # pauses ≤ this before a sentence = strategic
FILLER_WINDOW             = 1.5   # seconds after a filler word counts as filler_adj

SAMPLE_RATE = 16000

# Common filler words (matches Whisper output)
FILLER_WORDS = {"um", "uh", "like", "you know", "basically", "literally",
                "actually", "so", "right", "okay", "hmm"}


def _classify_pause(
    pause: Dict,
    word_timestamps: List[Dict],
    filler_timestamps: List[float],
) -> str:
    """
    Classify a pause as: strategic | awkward | filler_adj | effective | long | very_long
    """
    d = pause["duration"]
    start = pause["start"]

    if d >= VERY_LONG_PAUSE_THRESHOLD:
        return "very_long"

    # Check if a filler word ended within FILLER_WINDOW before this pause
    for ft in filler_timestamps:
        if 0 <= start - ft <= FILLER_WINDOW:
            return "filler_adj"

    if d >= LONG_PAUSE_THRESHOLD:
        return "long"

    # Check if pause is at a sentence boundary (word before is end-of-sentence)
    if word_timestamps:
        words_before = [w for w in word_timestamps if w["end"] <= start + 0.1]
        if words_before:
            last_word = words_before[-1]["word"].strip().rstrip(",.;:")
            is_sentence_end = words_before[-1]["word"].strip().endswith((".", "?", "!"))
            if is_sentence_end and GOOD_PAUSE_MIN <= d <= STRATEGIC_MAX:
                return "strategic"

    if GOOD_PAUSE_MIN <= d <= GOOD_PAUSE_MAX:
        return "effective"

    return "awkward"


class SileroAnalyzer(BaseAnalyzer):
    """
    Detects speech and silence segments using Silero VAD.
    Generates events for meaningful pauses with intelligent classification.
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

        # Word-level timestamps from Whisper (passed through pipeline kwargs)
        word_timestamps: List[Dict] = kwargs.get("word_timestamps", [])

        # Build a list of timestamps where filler words ended
        filler_timestamps: List[float] = []
        for w in word_timestamps:
            if w.get("word", "").strip().lower().strip(",.!?") in FILLER_WORDS:
                filler_timestamps.append(w.get("end", 0.0))

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
                pause_end   = segments[i]["start"]
                pause_dur   = pause_end - pause_start
                if pause_dur >= 0.3:
                    classification = _classify_pause(
                        {"start": pause_start, "end": pause_end, "duration": pause_dur},
                        word_timestamps,
                        filler_timestamps,
                    )
                    pauses.append({
                        "start":          pause_start,
                        "end":            pause_end,
                        "duration":       pause_dur,
                        "classification": classification,
                    })

            speaking_duration = sum(s["end"] - s["start"] for s in segments)
            silence_duration  = duration - speaking_duration

            # ─── Events ──────────────────────────────────────────────
            events: List[Event] = []

            # Limit total pause events to avoid noise (cap at top 10 worst)
            sorted_pauses = sorted(
                pauses,
                key=lambda p: (
                    {"very_long": 0, "long": 1, "filler_adj": 2,
                     "awkward": 3, "effective": 99, "strategic": 100}.get(p["classification"], 5)
                )
            )

            event_count = 0
            for pause in sorted_pauses:
                d  = pause["duration"]
                cl = pause["classification"]
                t  = pause["start"]

                if cl == "very_long":
                    events.append(voice_event(
                        timestamp=t, metric="pause",
                        title="Very Long Silence",
                        description=(
                            f"A {d:.1f}s silence may lose audience attention. "
                            "Fill with a transition phrase or continue more fluently."
                        ),
                        severity=EventSeverity.HIGH, score=20,
                        pause_duration=round(d, 2), pause_type=cl,
                    ))
                elif cl == "long":
                    events.append(voice_event(
                        timestamp=t, metric="pause",
                        title="Long Pause",
                        description=(
                            f"A {d:.1f}s pause feels awkward here. "
                            "Strategic pauses work best at 1–2 seconds."
                        ),
                        severity=EventSeverity.MEDIUM, score=55,
                        pause_duration=round(d, 2), pause_type=cl,
                    ))
                elif cl == "filler_adj" and event_count < 6:
                    events.append(voice_event(
                        timestamp=t, metric="pause",
                        title="Filler-Adjacent Silence",
                        description=(
                            f"A {d:.1f}s pause followed a filler word. "
                            "Replace the filler+pause with a single confident pause."
                        ),
                        severity=EventSeverity.MEDIUM, score=50,
                        pause_duration=round(d, 2), pause_type=cl,
                    ))
                    event_count += 1
                elif cl == "awkward" and event_count < 4:
                    events.append(voice_event(
                        timestamp=t, metric="pause",
                        title="Awkward Mid-Sentence Pause",
                        description=(
                            f"A {d:.1f}s pause in the middle of a thought. "
                            "Keep a steady rhythm to maintain listener engagement."
                        ),
                        severity=EventSeverity.LOW, score=65,
                        pause_duration=round(d, 2), pause_type=cl,
                    ))
                    event_count += 1
                elif cl == "strategic":
                    events.append(voice_event(
                        timestamp=t, metric="pause",
                        title="Strategic Pause",
                        description=(
                            f"A {d:.1f}s pause at sentence end — excellent for emphasis "
                            "and letting your audience absorb what you said."
                        ),
                        severity=EventSeverity.POSITIVE, score=92,
                        pause_duration=round(d, 2), pause_type=cl,
                    ))
                elif cl == "effective":
                    events.append(voice_event(
                        timestamp=t, metric="pause",
                        title="Effective Pause",
                        description=(
                            f"A {d:.1f}s pause here — great natural rhythm."
                        ),
                        severity=EventSeverity.POSITIVE, score=85,
                        pause_duration=round(d, 2), pause_type=cl,
                    ))

            # Tally by class
            counts = {}
            for p in pauses:
                counts[p["classification"]] = counts.get(p["classification"], 0) + 1

            long_pauses = [p for p in pauses if p["duration"] >= LONG_PAUSE_THRESHOLD]
            good_pauses = [
                p for p in pauses
                if p["classification"] in ("strategic", "effective")
            ]

            metrics = {
                "pause_count":               len(pauses),
                "long_pause_count":          len(long_pauses),
                "good_pause_count":          len(good_pauses),
                "strategic_pause_count":     counts.get("strategic", 0),
                "effective_pause_count":     counts.get("effective", 0),
                "awkward_pause_count":       counts.get("awkward", 0),
                "filler_adj_pause_count":    counts.get("filler_adj", 0),
                "speaking_duration_seconds": round(speaking_duration, 2),
                "silence_duration_seconds":  round(silence_duration, 2),
                "speaking_ratio":            round(speaking_duration / duration, 3) if duration else 0,
                "pauses":                    pauses,
                "speech_segments":           segments,
            }

            return AnalyzerResult(
                analyzer_name=self.name,
                metrics=metrics,
                events=events,
                summary=(
                    f"Found {len(pauses)} pauses — "
                    f"{counts.get('strategic', 0)} strategic, "
                    f"{counts.get('effective', 0)} effective, "
                    f"{counts.get('awkward', 0)} awkward, "
                    f"{counts.get('filler_adj', 0)} filler-adjacent, "
                    f"{len(long_pauses)} long/very-long. "
                    f"Speaking {speaking_duration:.0f}s / {duration:.0f}s total."
                ),
            )

        except Exception as e:
            logger.error(f"Silero VAD failed: {e}")
            raise
