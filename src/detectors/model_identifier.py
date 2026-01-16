"""AI model identification module."""

from typing import Dict, List, Optional
import re

from ..utils.logger import get_logger


class AIModelIdentifier:
    """Identify which AI model likely generated the text."""

    def __init__(self):
        """Initialize model identifier."""
        self.logger = get_logger()

        # Known model signatures and patterns
        self.model_patterns = {
            "gpt-4": {
                "keywords": [
                    "comprehensive",
                    "multifaceted",
                    "paramount",
                    "delve",
                    "crucial",
                    "vital",
                    "essential",
                    "significantly",
                    "furthermore",
                    "moreover",
                    "consequently",
                ],
                "patterns": [
                    r"it's important to note",
                    r"it('s | is) worth noting",
                    r"as an AI",
                    r"I('m | am) sorry, but",
                ],
                "characteristics": [
                    "verbose",
                    "formal",
                    "structured",
                ],
            },
            "gpt-3.5": {
                "keywords": [
                    "however",
                    "therefore",
                    "additionally",
                    "specifically",
                    "essentially",
                ],
                "patterns": [
                    r"as an AI (language )?model",
                    r"I don't have personal",
                ],
                "characteristics": [
                    "concise",
                    "structured",
                ],
            },
            "claude": {
                "keywords": [
                    "thoughtful",
                    "nuanced",
                    "appreciate",
                    "perspective",
                    "consider",
                ],
                "patterns": [
                    r"I aim to",
                    r"I try to",
                    r"I should note",
                    r"to be clear",
                ],
                "characteristics": [
                    "balanced",
                    "careful",
                ],
            },
            "bard": {
                "keywords": [
                    "explore",
                    "imagine",
                    "envision",
                ],
                "patterns": [
                    r"I'm Bard",
                    r"as a large language model",
                ],
                "characteristics": [
                    "creative",
                    "varied",
                ],
            },
        }

    def identify(
        self,
        text: str,
        detection_results: Optional[Dict] = None,
    ) -> Dict:
        """
        Identify which AI model likely generated the text.

        Args:
            text: Text to analyze
            detection_results: Optional detection results from other detectors

        Returns:
            Dictionary with model identification results
        """
        # If OpenAI detector already identified a model, use that
        if detection_results:
            individual_results = detection_results.get("individual_results", [])
            for result in individual_results:
                if result.get("method") == "openai_api" and result.get("details"):
                    suspected = result["details"].get("suspected_model")
                    if suspected and suspected not in ["unknown", "human"]:
                        return {
                            "model": suspected,
                            "confidence": 0.7,  # Trust OpenAI's identification
                            "method": "openai_api",
                        }

        # Pattern-based identification
        text_lower = text.lower()
        model_scores = {}

        for model_name, patterns_dict in self.model_patterns.items():
            score = 0
            matches = []

            # Check keywords
            keywords = patterns_dict.get("keywords", [])
            for keyword in keywords:
                count = text_lower.count(keyword.lower())
                if count > 0:
                    score += count * 0.5
                    matches.append(f"keyword: {keyword}")

            # Check regex patterns
            patterns = patterns_dict.get("patterns", [])
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    score += 2.0
                    matches.append(f"pattern: {pattern}")

            if score > 0:
                model_scores[model_name] = {
                    "score": score,
                    "matches": matches,
                }

        # Determine most likely model
        if model_scores:
            best_model = max(model_scores.items(), key=lambda x: x[1]["score"])
            model_name = best_model[0]
            score_data = best_model[1]

            # Normalize confidence (max score of 10 = 100% confidence)
            confidence = min(score_data["score"] / 10.0, 1.0)

            self.logger.debug(
                f"Model identification: {model_name} "
                f"(confidence: {confidence:.2f}, "
                f"matches: {len(score_data['matches'])})"
            )

            return {
                "model": model_name,
                "confidence": confidence,
                "method": "pattern_matching",
                "matches": score_data["matches"][:5],  # Top 5 matches
            }

        # No specific model identified
        return {
            "model": "unknown",
            "confidence": 0.0,
            "method": "pattern_matching",
        }

    def get_model_characteristics(self, model_name: str) -> List[str]:
        """
        Get known characteristics of an AI model.

        Args:
            model_name: Name of the model

        Returns:
            List of characteristic descriptions
        """
        if model_name in self.model_patterns:
            return self.model_patterns[model_name].get("characteristics", [])
        return []

    def format_model_name(self, model: str) -> str:
        """
        Format model name for display.

        Args:
            model: Model identifier

        Returns:
            Formatted model name
        """
        name_map = {
            "gpt-4": "GPT-4 (OpenAI)",
            "gpt-3.5": "GPT-3.5 (OpenAI)",
            "claude": "Claude (Anthropic)",
            "bard": "Bard (Google)",
            "unknown": "Unknown AI Model",
            "human": "Human",
            "unknown_ai_model": "Unknown AI Model",
        }

        return name_map.get(model, model)
