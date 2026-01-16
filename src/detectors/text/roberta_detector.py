"""RoBERTa-based text AI detector."""

from typing import Dict, Optional
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import os
from pathlib import Path

from ..base_detector import BaseTextDetector, DetectionResult
from ...utils.logger import get_logger


class RoBERTaDetector(BaseTextDetector):
    """Detect AI-generated text using RoBERTa model."""

    def __init__(self, config: Dict):
        """
        Initialize RoBERTa detector.

        Args:
            config: Configuration dictionary with model settings
        """
        super().__init__(config)
        self.logger = get_logger()

        # Configuration
        self.model_path = config.get("model_path", "models/text/roberta_detector")
        self.model_id = config.get(
            "model_id", "Hello-SimpleAI/chatgpt-detector-roberta"
        )

        # Initialize model and tokenizer
        self.model = None
        self.tokenizer = None
        self._load_model()

    def _load_model(self):
        """Load RoBERTa model and tokenizer."""
        try:
            # Check if model exists locally
            model_path = Path(self.model_path)

            if model_path.exists() and (model_path / "config.json").exists():
                self.logger.info(f"Loading RoBERTa model from {self.model_path}")
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
                self.model = AutoModelForSequenceClassification.from_pretrained(
                    self.model_path
                )
            else:
                # Download from HuggingFace
                self.logger.info(f"Downloading RoBERTa model: {self.model_id}")
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_id)
                self.model = AutoModelForSequenceClassification.from_pretrained(
                    self.model_id
                )

                # Save locally for future use
                if not model_path.exists():
                    model_path.mkdir(parents=True, exist_ok=True)
                    self.logger.info(f"Saving model to {self.model_path}")
                    self.tokenizer.save_pretrained(self.model_path)
                    self.model.save_pretrained(self.model_path)

            # Set to evaluation mode
            self.model.eval()

            # Use CPU (for 8GB RAM efficiency)
            self.device = torch.device("cpu")
            self.model.to(self.device)

            self.logger.info("RoBERTa model loaded successfully")

        except Exception as e:
            self.logger.error(f"Failed to load RoBERTa model: {e}")
            self.model = None
            self.tokenizer = None

    def is_available(self) -> bool:
        """Check if RoBERTa model is available."""
        return self.model is not None and self.tokenizer is not None

    def detect(self, text: str) -> DetectionResult:
        """
        Detect AI-generated text using RoBERTa.

        Args:
            text: Text to analyze

        Returns:
            DetectionResult
        """
        if not self.is_available():
            return DetectionResult(
                ai_probability=0.5,
                confidence=0.0,
                method="roberta",
                error="RoBERTa model not available",
            )

        if not self.validate_text(text):
            return DetectionResult(
                ai_probability=0.5,
                confidence=0.0,
                method="roberta",
                error="Text too short for reliable detection",
            )

        try:
            # Truncate if too long (max 512 tokens for RoBERTa)
            words = text.split()
            if len(words) > 400:  # Conservative to stay under 512 tokens
                text = " ".join(words[:400])
                self.logger.debug("Truncated text to 400 words for RoBERTa")

            # Tokenize
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True,
            )

            # Move to device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Run inference
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits

            # Get probabilities
            probs = torch.softmax(logits, dim=-1)

            # Check model config for label ordering
            # The Hello-SimpleAI/chatgpt-detector-roberta model uses [Real, Fake] where:
            # Real (index 0) = Human-written
            # Fake (index 1) = AI-generated
            if probs.shape[-1] == 2:
                ai_prob = probs[0][1].item()  # Index 1 = Fake/AI class
            else:
                # If not binary, use first output
                ai_prob = probs[0][0].item()

            # Confidence based on how far from 0.5 (uncertainty)
            confidence = abs(ai_prob - 0.5) * 2  # Scale to 0-1

            self.logger.debug(
                f"RoBERTa detection: probs={probs[0].tolist()}, "
                f"AI prob={ai_prob:.2f}, confidence={confidence:.2f}"
            )

            return DetectionResult(
                ai_probability=ai_prob,
                confidence=confidence,
                method="roberta",
                details={
                    "model_id": self.model_id,
                    "truncated": len(words) > 400,
                },
            )

        except Exception as e:
            self.logger.error(f"RoBERTa detection error: {e}", exc_info=True)
            return DetectionResult(
                ai_probability=0.5,
                confidence=0.0,
                method="roberta",
                error=f"Detection error: {str(e)}",
            )

    def __del__(self):
        """Cleanup model from memory."""
        if self.model is not None:
            del self.model
            del self.tokenizer
            torch.cuda.empty_cache() if torch.cuda.is_available() else None
