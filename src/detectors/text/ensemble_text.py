"""Ensemble text detector that combines multiple detection methods."""

from typing import Dict, List, Optional
import numpy as np

from ..base_detector import BaseTextDetector, DetectionResult
from .openai_detector import OpenAIDetector
from .roberta_detector import RoBERTaDetector
from .linguistic_analyzer import LinguisticAnalyzer
from ...utils.logger import get_logger
from ...utils.config import get_config


class EnsembleTextDetector:
    """Combine multiple text detectors using weighted voting."""

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize ensemble detector.

        Args:
            config: Configuration dictionary (if None, uses global config)
        """
        if config is None:
            cfg = get_config()
            config = cfg.to_dict()

        self.config = config
        self.logger = get_logger()

        # Get text detection configuration
        text_config = config.get("text_detection", {})
        detectors_config = text_config.get("detectors", {})

        # Initialize detectors
        self.detectors: List[BaseTextDetector] = []

        # OpenAI detector
        if detectors_config.get("openai", {}).get("enabled", True):
            try:
                openai_config = detectors_config.get("openai", {})
                detector = OpenAIDetector(openai_config)
                if detector.is_available():
                    self.detectors.append(detector)
                    self.logger.info("OpenAI detector enabled")
                else:
                    self.logger.warning("OpenAI detector not available (check API key)")
            except Exception as e:
                self.logger.error(f"Failed to initialize OpenAI detector: {e}")

        # RoBERTa detector
        if detectors_config.get("roberta", {}).get("enabled", True):
            try:
                roberta_config = detectors_config.get("roberta", {})
                detector = RoBERTaDetector(roberta_config)
                if detector.is_available():
                    self.detectors.append(detector)
                    self.logger.info("RoBERTa detector enabled")
                else:
                    self.logger.warning("RoBERTa detector not available")
            except Exception as e:
                self.logger.error(f"Failed to initialize RoBERTa detector: {e}")

        # Linguistic analyzer
        if detectors_config.get("linguistic", {}).get("enabled", True):
            try:
                linguistic_config = detectors_config.get("linguistic", {})
                detector = LinguisticAnalyzer(linguistic_config)
                if detector.is_available():
                    self.detectors.append(detector)
                    self.logger.info("Linguistic analyzer enabled")
            except Exception as e:
                self.logger.error(f"Failed to initialize linguistic analyzer: {e}")

        if not self.detectors:
            self.logger.error("No text detectors available!")

        self.logger.info(f"Ensemble detector initialized with {len(self.detectors)} detectors")

    def detect(self, text: str) -> Dict:
        """
        Detect AI-generated text using ensemble of detectors.

        Args:
            text: Text to analyze

        Returns:
            Dictionary with ensemble results
        """
        if not self.detectors:
            return {
                "status": "error",
                "error": "No detectors available",
                "ai_probability": 0.5,
                "confidence": 0.0,
            }

        # Run all detectors
        results = []
        for detector in self.detectors:
            try:
                self.logger.debug(f"Running {detector.get_name()} detector")
                result = detector.detect(text)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Detector {detector.get_name()} failed: {e}")
                # Add error result
                results.append(
                    DetectionResult(
                        ai_probability=0.5,
                        confidence=0.0,
                        method=detector.get_name(),
                        error=str(e),
                    )
                )

        # Calculate ensemble score
        ensemble_result = self._calculate_ensemble(results)

        return ensemble_result

    def _calculate_ensemble(self, results: List[DetectionResult]) -> Dict:
        """
        Calculate ensemble score from individual results.

        Args:
            results: List of DetectionResults

        Returns:
            Ensemble result dictionary
        """
        # Filter out failed results for voting
        valid_results = [r for r in results if r.error is None]

        if not valid_results:
            return {
                "status": "error",
                "error": "All detectors failed",
                "ai_probability": 0.5,
                "confidence": 0.0,
                "individual_results": self._format_results(results),
            }

        # Weighted voting
        weighted_probs = []
        weights = []

        for result in valid_results:
            # Get detector weight from config
            weight = self._get_detector_weight(result.method)

            # Weight by both config weight and detector confidence
            effective_weight = weight * result.confidence

            weighted_probs.append(result.ai_probability * effective_weight)
            weights.append(effective_weight)

        # Calculate weighted average
        total_weight = sum(weights)
        if total_weight > 0:
            ensemble_probability = sum(weighted_probs) / total_weight
        else:
            ensemble_probability = 0.5

        # Calculate ensemble confidence
        # Based on:
        # 1. Agreement among detectors (low std = high confidence)
        # 2. Individual confidence scores
        probabilities = [r.ai_probability for r in valid_results]
        confidences = [r.confidence for r in valid_results]

        agreement = 1.0 - (np.std(probabilities) / 0.5)  # Normalize by max possible std
        agreement = max(0.0, min(1.0, agreement))  # Clamp to [0, 1]

        avg_confidence = np.mean(confidences)

        # Ensemble confidence is combination of agreement and individual confidences
        ensemble_confidence = (agreement * 0.6) + (avg_confidence * 0.4)

        # Determine suspected AI model (if any detector identified one)
        suspected_model = self._identify_model(results)

        # Generate explanation
        explanation = self._generate_explanation(results, ensemble_probability, ensemble_confidence)

        self.logger.info(
            f"Ensemble result: AI probability={ensemble_probability:.2f}, "
            f"confidence={ensemble_confidence:.2f}, "
            f"model={suspected_model}"
        )

        return {
            "status": "success",
            "ai_probability": ensemble_probability,
            "confidence": ensemble_confidence,
            "suspected_model": suspected_model,
            "explanation": explanation,
            "individual_results": self._format_results(results),
            "num_detectors_used": len(valid_results),
            "num_detectors_failed": len(results) - len(valid_results),
        }

    def _get_detector_weight(self, method: str) -> float:
        """Get configured weight for a detector."""
        detectors_config = self.config.get("text_detection", {}).get("detectors", {})

        # Map method name to config key
        method_map = {
            "openai_api": "openai",
            "roberta": "roberta",
            "linguistic": "linguistic",
        }

        config_key = method_map.get(method, method)
        return detectors_config.get(config_key, {}).get("weight", 0.33)

    def _identify_model(self, results: List[DetectionResult]) -> str:
        """
        Identify suspected AI model from detector results.

        Args:
            results: List of DetectionResults

        Returns:
            Suspected model name or "unknown"
        """
        # Check OpenAI detector result for model identification
        for result in results:
            if result.method == "openai_api" and result.details:
                model = result.details.get("suspected_model")
                if model and model not in ["unknown", "human"]:
                    return model

        # If high AI probability but no specific model identified
        ai_probs = [r.ai_probability for r in results if r.error is None]
        if ai_probs and np.mean(ai_probs) > 0.7:
            return "unknown_ai_model"

        return "unknown"

    def _generate_explanation(
        self, results: List[DetectionResult], ai_prob: float, confidence: float
    ) -> str:
        """Generate human-readable explanation of detection."""
        if ai_prob >= 0.8:
            verdict = "highly likely AI-generated"
        elif ai_prob >= 0.6:
            verdict = "likely AI-generated"
        elif ai_prob >= 0.4:
            verdict = "uncertain origin"
        else:
            verdict = "likely human-written"

        conf_desc = "high" if confidence >= 0.7 else "moderate" if confidence >= 0.5 else "low"

        explanation = f"This text is {verdict} with {conf_desc} confidence ({confidence:.0%}). "

        # Add detector-specific insights
        insights = []
        for result in results:
            if result.error:
                continue

            method = result.method
            prob = result.ai_probability

            if method == "openai_api" and result.details:
                reasoning = result.details.get("reasoning", "")
                if reasoning:
                    insights.append(f"OpenAI analysis: {reasoning}")

            elif method == "linguistic" and result.details:
                perplexity = result.details.get("perplexity")
                burstiness = result.details.get("burstiness")

                if perplexity is not None:
                    if perplexity < 30:
                        insights.append(
                            f"Low perplexity ({perplexity:.1f}) suggests predictable, AI-like patterns"
                        )
                    elif perplexity > 50:
                        insights.append(
                            f"High perplexity ({perplexity:.1f}) suggests more varied, human-like writing"
                        )

                if burstiness is not None:
                    if burstiness < 0.3:
                        insights.append(
                            f"Low burstiness ({burstiness:.2f}) indicates uniform sentence structure typical of AI"
                        )
                    elif burstiness > 0.5:
                        insights.append(
                            f"High burstiness ({burstiness:.2f}) suggests varied sentence lengths typical of humans"
                        )

            elif method == "roberta":
                if prob > 0.7:
                    insights.append("RoBERTa classifier detected strong AI patterns")
                elif prob < 0.3:
                    insights.append("RoBERTa classifier detected human writing patterns")

        if insights:
            explanation += "\n\nKey indicators:\n- " + "\n- ".join(insights)

        return explanation

    def _format_results(self, results: List[DetectionResult]) -> List[Dict]:
        """Format individual results for output."""
        formatted = []
        for result in results:
            formatted.append(
                {
                    "method": result.method,
                    "ai_probability": result.ai_probability,
                    "confidence": result.confidence,
                    "details": result.details,
                    "error": result.error,
                }
            )
        return formatted

    def is_available(self) -> bool:
        """Check if ensemble has at least one detector available."""
        return len(self.detectors) > 0
