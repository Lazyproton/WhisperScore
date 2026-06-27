"""
WhisperScore — Groq LLM Content Analyzer
Sends transcript to Groq API and receives structured coaching JSON.

Analyzes:
  - Clarity and logical flow
  - Speech structure (intro/body/conclusion)
  - Argument quality and persuasiveness
  - Supporting evidence
  - Personalized coaching tips
"""
import json
import logging
from typing import Optional, List
from analyzers.base import BaseAnalyzer, AnalyzerResult
from analyzers.timeline.events import EventSeverity, content_event
from core.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert public speaking and debate coach.
Analyze the provided speech transcript and return a JSON object with the following structure:

{
  "scores": {
    "clarity": <0-100>,
    "organization": <0-100>,
    "persuasiveness": <0-100>,
    "supporting_evidence": <0-100>,
    "logical_flow": <0-100>
  },
  "events": [
    {
      "timestamp_estimate": <seconds, estimate from transcript position>,
      "metric": "<clarity|organization|persuasiveness|evidence|logical_flow>",
      "severity": "<low|medium|high|positive>",
      "title": "<short title>",
      "description": "<1-2 sentence coaching description>"
    }
  ],
  "strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
  "weaknesses": ["<weakness 1>", "<weakness 2>", "<weakness 3>"],
  "tips": ["<actionable tip 1>", "<tip 2>", "<tip 3>", "<tip 4>", "<tip 5>"],
  "improved_excerpt": "<Rewrite the weakest paragraph with improvements>",
  "summary": "<2-3 sentence overall assessment>"
}

Generate 4-8 events. Be specific and timestamp them relative to the transcript position.
Focus on practical, actionable coaching. Return ONLY valid JSON."""


class LLMAnalyzer(BaseAnalyzer):
    name = "llm"

    def analyze(self, audio_path=None, video_path=None, **kwargs) -> AnalyzerResult:
        transcript = kwargs.get("transcript", "")
        duration = kwargs.get("duration_seconds", 0)

        if not transcript:
            return AnalyzerResult(
                analyzer_name=self.name,
                metrics={},
                events=[],
                summary="No transcript available for content analysis",
            )

        if not settings.GROQ_API_KEY:
            logger.warning("GROQ_API_KEY not set — using fallback content analysis")
            return self._fallback_analysis(transcript, duration)

        try:
            from groq import Groq
            client = Groq(api_key=settings.GROQ_API_KEY)

            # Truncate transcript to fit context window
            max_chars = 4000
            truncated = transcript[:max_chars]
            if len(transcript) > max_chars:
                truncated += "\n[transcript truncated]"

            response = client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Transcript:\n\n{truncated}"},
                ],
                temperature=0.3,
                max_tokens=2000,
                response_format={"type": "json_object"},
            )

            raw = response.choices[0].message.content
            data = json.loads(raw)

            events = []
            for e in data.get("events", []):
                events.append(content_event(
                    timestamp=float(e.get("timestamp_estimate", 0)),
                    metric=e.get("metric", "clarity"),
                    title=e.get("title", "Content Issue"),
                    description=e.get("description", ""),
                    severity=EventSeverity(e.get("severity", "medium")),
                    score=None,
                ))

            scores = data.get("scores", {})
            metrics = {
                "clarity": scores.get("clarity", 70),
                "organization": scores.get("organization", 70),
                "persuasiveness": scores.get("persuasiveness", 70),
                "supporting_evidence": scores.get("supporting_evidence", 70),
                "logical_flow": scores.get("logical_flow", 70),
                "strengths": data.get("strengths", []),
                "weaknesses": data.get("weaknesses", []),
                "tips": data.get("tips", []),
                "improved_excerpt": data.get("improved_excerpt", ""),
                "summary": data.get("summary", ""),
            }

            return AnalyzerResult(
                analyzer_name=self.name,
                metrics=metrics, events=events,
                summary=data.get("summary", "Content analysis complete"),
            )

        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return self._fallback_analysis(transcript, duration)

    def _fallback_analysis(self, transcript: str, duration: float) -> AnalyzerResult:
        """Basic heuristic content analysis when Groq is unavailable."""
        word_count = len(transcript.split())
        sentence_count = transcript.count(".") + transcript.count("!") + transcript.count("?")
        avg_sentence_length = word_count / max(sentence_count, 1)

        clarity = min(100, max(40, 100 - abs(avg_sentence_length - 18) * 2))
        organization = 65
        persuasiveness = 60

        events = [
            content_event(
                timestamp=0.0, metric="clarity",
                title="Content Structure Detected",
                description="Add your GROQ_API_KEY to get detailed AI coaching on your content.",
                severity=EventSeverity.LOW, score=clarity,
            ),
        ]

        return AnalyzerResult(
            analyzer_name=self.name,
            metrics={
                "clarity": clarity,
                "organization": organization,
                "persuasiveness": persuasiveness,
                "supporting_evidence": 60,
                "logical_flow": 65,
                "strengths": ["You completed the presentation", "Content was delivered"],
                "weaknesses": ["Add GROQ_API_KEY for detailed feedback"],
                "tips": ["Set GROQ_API_KEY in your .env file for AI coaching"],
                "improved_excerpt": "",
                "summary": "Basic analysis complete. Add GROQ_API_KEY for full AI coaching.",
            },
            events=events,
            summary="Fallback content analysis (no API key)",
        )
