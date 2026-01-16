"""Base detector interface for text AI detection."""

from abc import ABC, abstractmethod
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class DetectionResult:
    """Result from a text detection."""

    ai_probability: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0, how confident is the detector
    method: str  # Name of detection method
    details: Optional[Dict] = None  # Additional details
    error: Optional[str] = None  # Error message if detection failed


class BaseTextDetector(ABC):
    """Abstract base class for text AI detectors."""

    def __init__(self, config: Dict):
        """
        Initialize detector with configuration.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.name = self.__class__.__name__

    @abstractmethod
    def detect(self, text: str) -> DetectionResult:
        """
        Detect if text is AI-generated.

        Args:
            text: Text to analyze

        Returns:
            DetectionResult with AI probability and confidence
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if detector is available and ready to use.

        Returns:
            True if detector can be used
        """
        pass

    def validate_text(self, text: str, min_words: int = 50) -> bool:
        """
        Validate that text meets minimum requirements.

        Args:
            text: Text to validate
            min_words: Minimum number of words

        Returns:
            True if text is valid for detection
        """
        if not text or not text.strip():
            return False

        word_count = len(text.split())
        return word_count >= min_words

    def get_name(self) -> str:
        """Get detector name."""
        return self.name

    def get_weight(self) -> float:
        """
        Get detector weight for ensemble voting.

        Returns:
            Weight value (default: 1.0)
        """
        return self.config.get("weight", 1.0)
