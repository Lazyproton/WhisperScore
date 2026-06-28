"""
WhisperScore — Groq LLM Content Analyzer
Features:
  5. Argument Strength Scorer — rates claim-evidence-warrant structure,
     flags unsupported assertions, purple prose, and logical gaps.
  6. Question Anticipation — predicts 3–5 tough audience questions with
     suggested answers, returned in the coaching panel.
"""
import json
import logging
from typing import Optional, List
from analyzers.base import BaseAnalyzer, AnalyzerResult
from analyzers.timeline.events import EventSeverity, content_event
from core.config import settings

logger = logging.getLogger(__name__)

# ── Prompt 1: Core content analysis + argument strength ──────────────────────
SYSTEM_PROMPT = """You are an expert public speaking, debate, and rhetoric coach.
Analyze the provided speech transcript and return a JSON object with this exact structure:

{
  "scores": {
    "clarity":            <0-100>,
    "organization":       <0-100>,
    "persuasiveness":     <0-100>,
    "supporting_evidence":<0-100>,
    "logical_flow":       <0-100>,
    "argument_strength":  <0-100>
  },
  "argument_analysis": {
    "unsupported_claims": [
      {"claim": "<exact quote or paraphrase>", "timestamp_estimate": <seconds>, "suggestion": "<how to support it>"}
    ],
    "strong_arguments": [
      {"argument": "<brief description>", "timestamp_estimate": <seconds>}
    ],
    "logical_gaps": [
      {"gap": "<description>", "timestamp_estimate": <seconds>}
    ],
    "evidence_quality": "<none|weak|moderate|strong>",
    "claim_count": <integer>,
    "supported_claim_count": <integer>
  },
  "events": [
    {
      "timestamp_estimate": <seconds>,
      "metric": "<clarity|organization|persuasiveness|evidence|logical_flow|argument_strength>",
      "severity": "<low|medium|high|positive>",
      "title": "<short title, max 5 words>",
      "description": "<1-2 sentence coaching description>"
    }
  ],
  "strengths":        ["<strength 1>", "<strength 2>", "<strength 3>"],
  "weaknesses":       ["<weakness 1>", "<weakness 2>", "<weakness 3>"],
  "tips":             ["<actionable tip 1>", "<tip 2>", "<tip 3>", "<tip 4>", "<tip 5>"],
  "improved_excerpt": "<Rewrite the weakest paragraph with improvements>",
  "summary":          "<2-3 sentence overall assessment>"
}

Argument Strength scoring rubric:
  90-100: Every major claim backed by concrete evidence/data
  70-89:  Most claims supported, minor gaps
  50-69:  Some claims unsupported, reasoning gaps present
  30-49:  Many claims are assertions without evidence
  0-29:   Predominantly unsupported claims, logical fallacies present

Generate 4-8 timeline events. Timestamp them relative to transcript position.
Return ONLY valid JSON."""

# ── Prompt 2: Question Anticipation ──────────────────────────────────────────
QUESTION_PROMPT = """You are a tough, skeptical audience member at a presentation.
Based on the speech transcript below, predict the 4 hardest questions the audience would ask,
and provide a concise suggested answer for each.

Return ONLY this JSON structure:
{
  "anticipated_questions": [
    {
      "question": "<the tough question>",
      "why_they_ask": "<1 sentence: what gap or claim triggers this>",
      "suggested_answer": "<2-3 sentence coached response>"
    }
  ]
}"""


class LLMAnalyzer(BaseAnalyzer):
    name = "llm"

    def analyze(self, audio_path=None, video_path=None, **kwargs) -> AnalyzerResult:
        transcript = kwargs.get("transcript", "")
        duration   = kwargs.get("duration_seconds", 0)

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

            max_chars = 4000
            truncated = transcript[:max_chars]
            if len(transcript) > max_chars:
                truncated += "\n[transcript truncated]"

            # ── Call 1: Core analysis + argument strength ─────────────────────
            response = client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": f"Speech transcript:\n\n{truncated}"},
                ],
                temperature=0.3,
                max_tokens=2500,
                response_format={"type": "json_object"},
            )
            data = json.loads(response.choices[0].message.content)

            # ── Call 2: Question anticipation ─────────────────────────────────
            q_response = client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": QUESTION_PROMPT},
                    {"role": "user",   "content": f"Transcript:\n\n{truncated}"},
                ],
                temperature=0.5,
                max_tokens=800,
                response_format={"type": "json_object"},
            )
            q_data = json.loads(q_response.choices[0].message.content)

            # ── Build timeline events ─────────────────────────────────────────
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

            # Emit events for unsupported claims (argument strength)
            arg_analysis = data.get("argument_analysis", {})
            for uc in arg_analysis.get("unsupported_claims", [])[:3]:
                events.append(content_event(
                    timestamp=float(uc.get("timestamp_estimate", 0)),
                    metric="argument_strength",
                    title="Unsupported Claim",
                    description=(
                        f"\"{uc.get('claim', '')[:80]}\" — "
                        f"{uc.get('suggestion', 'Back this up with data or an example.')}"
                    ),
                    severity=EventSeverity.MEDIUM,
                    score=None,
                ))

            for sa in arg_analysis.get("strong_arguments", [])[:2]:
                events.append(content_event(
                    timestamp=float(sa.get("timestamp_estimate", 0)),
                    metric="argument_strength",
                    title="Strong Argument",
                    description=sa.get("argument", "Well-structured point with clear support."),
                    severity=EventSeverity.POSITIVE,
                    score=None,
                ))

            # ── Scores & metrics ──────────────────────────────────────────────
            scores = data.get("scores", {})
            metrics = {
                "clarity":             scores.get("clarity", 70),
                "organization":        scores.get("organization", 70),
                "persuasiveness":      scores.get("persuasiveness", 70),
                "supporting_evidence": scores.get("supporting_evidence", 70),
                "logical_flow":        scores.get("logical_flow", 70),
                "argument_strength":   scores.get("argument_strength", 65),
                "strengths":           data.get("strengths", []),
                "weaknesses":          data.get("weaknesses", []),
                "tips":                data.get("tips", []),
                "improved_excerpt":    data.get("improved_excerpt", ""),
                "summary":             data.get("summary", ""),
                # Argument analysis details
                "argument_analysis": {
                    "evidence_quality":      arg_analysis.get("evidence_quality", "unknown"),
                    "claim_count":           arg_analysis.get("claim_count", 0),
                    "supported_claim_count": arg_analysis.get("supported_claim_count", 0),
                    "unsupported_claims":    arg_analysis.get("unsupported_claims", []),
                    "strong_arguments":      arg_analysis.get("strong_arguments", []),
                    "logical_gaps":          arg_analysis.get("logical_gaps", []),
                },
                # Question anticipation
                "anticipated_questions": q_data.get("anticipated_questions", []),
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
        word_count      = len(transcript.split())
        sentence_count  = transcript.count(".") + transcript.count("!") + transcript.count("?")
        avg_sent_len    = word_count / max(sentence_count, 1)

        clarity         = min(100, max(40, 100 - abs(avg_sent_len - 18) * 2))
        organization    = 65
        persuasiveness  = 60

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
                "clarity":             clarity,
                "organization":        organization,
                "persuasiveness":      persuasiveness,
                "supporting_evidence": 60,
                "logical_flow":        65,
                "argument_strength":   60,
                "strengths":  ["You completed the presentation", "Content was delivered"],
                "weaknesses": ["Add GROQ_API_KEY for detailed feedback"],
                "tips":       ["Set GROQ_API_KEY in your .env file for AI coaching"],
                "improved_excerpt": "",
                "summary":    "Basic analysis complete. Add GROQ_API_KEY for full AI coaching.",
                "argument_analysis": {
                    "evidence_quality": "unknown",
                    "claim_count": 0,
                    "supported_claim_count": 0,
                    "unsupported_claims": [],
                    "strong_arguments": [],
                    "logical_gaps": [],
                },
                "anticipated_questions": [],
            },
            events=events,
            summary="Fallback content analysis (no API key)",
        )
