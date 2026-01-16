"""Linguistic feature analyzer for AI text detection."""

from typing import Dict, List
import torch
from transformers import GPT2LMHeadModel, GPT2Tokenizer
import numpy as np
from collections import Counter
import math
from pathlib import Path

from ..base_detector import BaseTextDetector, DetectionResult
from ...utils.logger import get_logger


class LinguisticAnalyzer(BaseTextDetector):
    """Analyze linguistic features to detect AI-generated text."""

    def __init__(self, config: Dict):
        """
        Initialize linguistic analyzer.

        Args:
            config: Configuration dictionary
        """
        super().__init__(config)
        self.logger = get_logger()

        # Load GPT-2 for perplexity calculation
        self.perplexity_model = None
        self.perplexity_tokenizer = None
        self._load_perplexity_model()

        # Thresholds (tuned based on empirical data)
        self.ai_perplexity_threshold = 30.0  # AI text typically has lower perplexity
        self.ai_burstiness_threshold = 0.3  # AI text typically has lower burstiness
        self.ai_entropy_threshold = 4.0  # AI text typically has moderate entropy

    def _load_perplexity_model(self):
        """Load GPT-2 model for perplexity calculation."""
        try:
            model_path = Path("models/text/perplexity_model")

            if model_path.exists() and (model_path / "config.json").exists():
                self.logger.info(f"Loading GPT-2 model from {model_path}")
                self.perplexity_tokenizer = GPT2Tokenizer.from_pretrained(str(model_path))
                self.perplexity_model = GPT2LMHeadModel.from_pretrained(str(model_path))
            else:
                self.logger.info("Downloading GPT-2 model for perplexity")
                self.perplexity_tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
                self.perplexity_model = GPT2LMHeadModel.from_pretrained("gpt2")

                # Save locally
                model_path.mkdir(parents=True, exist_ok=True)
                self.perplexity_tokenizer.save_pretrained(str(model_path))
                self.perplexity_model.save_pretrained(str(model_path))

            self.perplexity_model.eval()
            self.device = torch.device("cpu")
            self.perplexity_model.to(self.device)

            self.logger.info("GPT-2 perplexity model loaded successfully")

        except Exception as e:
            self.logger.error(f"Failed to load perplexity model: {e}")
            self.perplexity_model = None
            self.perplexity_tokenizer = None

    def is_available(self) -> bool:
        """Check if analyzer is available."""
        # Can work without perplexity model (using other features)
        return True

    def detect(self, text: str) -> DetectionResult:
        """
        Analyze linguistic features to detect AI text.

        Args:
            text: Text to analyze

        Returns:
            DetectionResult
        """
        if not self.validate_text(text):
            return DetectionResult(
                ai_probability=0.5,
                confidence=0.0,
                method="linguistic",
                error="Text too short for reliable analysis",
            )

        try:
            features = {}
            scores = []

            # Calculate perplexity
            if self.perplexity_model is not None:
                perplexity = self._calculate_perplexity(text)
                features["perplexity"] = perplexity

                # Lower perplexity suggests AI (more predictable)
                perplexity_score = self._score_perplexity(perplexity)
                scores.append(perplexity_score)
            else:
                self.logger.warning("Perplexity model not available, skipping perplexity")

            # Calculate burstiness
            burstiness = self._calculate_burstiness(text)
            features["burstiness"] = burstiness

            # Lower burstiness suggests AI (more uniform)
            burstiness_score = self._score_burstiness(burstiness)
            scores.append(burstiness_score)

            # Calculate entropy
            entropy = self._calculate_entropy(text)
            features["entropy"] = entropy

            # Moderate entropy suggests AI
            entropy_score = self._score_entropy(entropy)
            scores.append(entropy_score)

            # Calculate vocabulary richness
            vocab_richness = self._calculate_vocabulary_richness(text)
            features["vocabulary_richness"] = vocab_richness

            # Very high richness might suggest AI
            richness_score = self._score_vocabulary_richness(vocab_richness)
            scores.append(richness_score)

            # Average all scores
            ai_probability = np.mean(scores)

            # Confidence based on agreement among features
            confidence = 1.0 - np.std(scores)  # Lower std = higher confidence

            self.logger.debug(
                f"Linguistic analysis: perplexity={features.get('perplexity', 'N/A')}, "
                f"burstiness={burstiness:.3f}, entropy={entropy:.3f}, "
                f"vocab_richness={vocab_richness:.3f}"
            )

            return DetectionResult(
                ai_probability=ai_probability,
                confidence=confidence,
                method="linguistic",
                details=features,
            )

        except Exception as e:
            self.logger.error(f"Linguistic analysis error: {e}", exc_info=True)
            return DetectionResult(
                ai_probability=0.5,
                confidence=0.0,
                method="linguistic",
                error=f"Analysis error: {str(e)}",
            )

    def _calculate_perplexity(self, text: str) -> float:
        """Calculate perplexity using GPT-2."""
        try:
            # Tokenize
            encodings = self.perplexity_tokenizer(
                text, return_tensors="pt", truncation=True, max_length=1024
            )
            input_ids = encodings.input_ids.to(self.device)

            # Calculate loss
            with torch.no_grad():
                outputs = self.perplexity_model(input_ids, labels=input_ids)
                loss = outputs.loss

            # Perplexity = exp(loss)
            perplexity = torch.exp(loss).item()

            return perplexity

        except Exception as e:
            self.logger.warning(f"Perplexity calculation failed: {e}")
            return 50.0  # Neutral value

    def _calculate_burstiness(self, text: str) -> float:
        """
        Calculate burstiness (variance in sentence lengths).
        AI text tends to have more uniform sentence lengths.
        """
        # Split into sentences (simple approach)
        sentences = [s.strip() for s in text.replace("!", ".").replace("?", ".").split(".") if s.strip()]

        if len(sentences) < 2:
            return 0.5

        # Calculate word counts per sentence
        lengths = [len(s.split()) for s in sentences]

        # Calculate coefficient of variation (std / mean)
        mean_length = np.mean(lengths)
        std_length = np.std(lengths)

        if mean_length == 0:
            return 0.0

        burstiness = std_length / mean_length

        return min(burstiness, 2.0) / 2.0  # Normalize to 0-1

    def _calculate_entropy(self, text: str) -> float:
        """Calculate Shannon entropy of word distribution."""
        words = text.lower().split()

        if len(words) == 0:
            return 0.0

        # Count word frequencies
        word_counts = Counter(words)
        total_words = len(words)

        # Calculate entropy
        entropy = 0.0
        for count in word_counts.values():
            probability = count / total_words
            entropy -= probability * math.log2(probability)

        return entropy

    def _calculate_vocabulary_richness(self, text: str) -> float:
        """
        Calculate vocabulary richness (unique words / total words).
        Also known as Type-Token Ratio (TTR).
        """
        words = text.lower().split()

        if len(words) == 0:
            return 0.0

        unique_words = len(set(words))
        total_words = len(words)

        return unique_words / total_words

    def _score_perplexity(self, perplexity: float) -> float:
        """Convert perplexity to AI probability score."""
        # Lower perplexity = higher AI probability
        # Typical ranges: Human 40-100, AI 10-40
        if perplexity < 20:
            return 0.9  # Very likely AI
        elif perplexity < 30:
            return 0.7  # Likely AI
        elif perplexity < 50:
            return 0.5  # Uncertain
        else:
            return 0.3  # Likely human

    def _score_burstiness(self, burstiness: float) -> float:
        """Convert burstiness to AI probability score."""
        # Lower burstiness = higher AI probability
        # Typical ranges: Human 0.4-0.8, AI 0.2-0.4
        if burstiness < 0.25:
            return 0.8  # Likely AI
        elif burstiness < 0.35:
            return 0.6  # Possibly AI
        elif burstiness < 0.5:
            return 0.4  # Uncertain
        else:
            return 0.2  # Likely human

    def _score_entropy(self, entropy: float) -> float:
        """Convert entropy to AI probability score."""
        # Moderate entropy suggests AI
        # Typical ranges: Human 3-6, AI 3.5-5
        if 3.5 <= entropy <= 5.0:
            return 0.7  # Possibly AI (in typical AI range)
        elif entropy < 3.0 or entropy > 6.0:
            return 0.3  # Likely human (outside typical range)
        else:
            return 0.5  # Uncertain

    def _score_vocabulary_richness(self, richness: float) -> float:
        """Convert vocabulary richness to AI probability score."""
        # Very high or very low richness can indicate AI
        # Typical ranges: Human 0.3-0.5, AI 0.4-0.6 (often higher)
        if 0.45 <= richness <= 0.65:
            return 0.6  # Possibly AI
        elif richness > 0.65:
            return 0.7  # Unusually high, possibly AI
        else:
            return 0.4  # More typical of human

    def __del__(self):
        """Cleanup model from memory."""
        if self.perplexity_model is not None:
            del self.perplexity_model
            del self.perplexity_tokenizer
            torch.cuda.empty_cache() if torch.cuda.is_available() else None
