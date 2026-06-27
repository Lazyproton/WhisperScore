"""
WhisperScore — Base Analyzer Interface
Every analyzer must implement this protocol.
New analyzers can be added by creating a new module without
modifying existing code.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from analyzers.timeline.events import Event


@dataclass
class AnalyzerResult:
    """
    Standard output from every analyzer.
    The pipeline collects these and aggregates them.
    """
    analyzer_name: str
    metrics: Dict[str, Any] = field(default_factory=dict)
    events: List[Event] = field(default_factory=list)
    summary: str = ""
    error: Optional[str] = None
    success: bool = True


class BaseAnalyzer(ABC):
    """
    Abstract base class for all WhisperScore analyzers.

    Subclasses implement analyze() and return an AnalyzerResult.
    Analyzers must not depend on each other — they receive only
    the recording paths and optional shared context.

    Usage:
        class MyAnalyzer(BaseAnalyzer):
            name = "my_analyzer"

            def analyze(self, audio_path=None, video_path=None, **kwargs):
                ...
                return AnalyzerResult(analyzer_name=self.name, ...)
    """

    name: str = "base"

    @abstractmethod
    def analyze(
        self,
        audio_path: Optional[str] = None,
        video_path: Optional[str] = None,
        **kwargs,
    ) -> AnalyzerResult:
        """
        Run analysis on the provided media files.

        Args:
            audio_path: Path to the extracted WAV audio file.
            video_path: Path to the original video file.
            **kwargs: Additional context (e.g., transcript from Whisper).

        Returns:
            AnalyzerResult with metrics, events, and summary.
        """
        raise NotImplementedError

    def safe_analyze(
        self,
        audio_path: Optional[str] = None,
        video_path: Optional[str] = None,
        **kwargs,
    ) -> AnalyzerResult:
        """
        Wraps analyze() with error handling.
        The pipeline calls this instead of analyze() directly.
        """
        try:
            return self.analyze(audio_path=audio_path, video_path=video_path, **kwargs)
        except Exception as e:
            return AnalyzerResult(
                analyzer_name=self.name,
                success=False,
                error=str(e),
                summary=f"Analyzer {self.name} failed: {e}",
            )
