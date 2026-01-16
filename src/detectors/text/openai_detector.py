"""OpenAI API-based text AI detector."""

from typing import Dict, Optional
import json
import openai
from openai import OpenAI
import os

from ..base_detector import BaseTextDetector, DetectionResult
from ...utils.logger import get_logger
from ...utils.error_handlers import retry_on_failure


class OpenAIDetector(BaseTextDetector):
    """Detect AI-generated text using OpenAI API."""

    def __init__(self, config: Dict):
        """
        Initialize OpenAI detector.

        Args:
            config: Configuration dictionary with OpenAI settings
        """
        super().__init__(config)
        self.logger = get_logger()

        # Get API key
        self.api_key = config.get("api_key") or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            self.logger.warning("OpenAI API key not found. OpenAI detector will be disabled.")
            self.client = None
        else:
            self.client = OpenAI(api_key=self.api_key)

        # Configuration
        self.model = config.get("model", "gpt-4")
        self.max_tokens = config.get("max_tokens", 2000)
        self.temperature = config.get("temperature", 0.0)

        # Detection prompt
        self.detection_prompt = """You are an AI text detector. Analyze the following text and determine if it was likely written by an AI language model (like GPT, Claude, etc.) or by a human.

Provide your analysis in the following JSON format:
{
  "ai_probability": <float between 0 and 1>,
  "confidence": <float between 0 and 1>,
  "suspected_model": "<model name or 'unknown' or 'human'>",
  "reasoning": "<brief explanation>"
}

Consider these indicators:
- AI text often has consistent sentence structure and length
- AI text typically has lower perplexity (more predictable)
- AI text may have characteristic phrasing patterns
- AI text often lacks personal anecdotes or specific details
- Human text may have more varied sentence structure and occasional errors

Text to analyze:
---
{text}
---

Respond ONLY with the JSON, no additional text."""

    def is_available(self) -> bool:
        """Check if OpenAI API is available."""
        return self.client is not None and self.api_key is not None

    @retry_on_failure(max_retries=2, delay=1.0)
    def detect(self, text: str) -> DetectionResult:
        """
        Detect AI-generated text using OpenAI API.

        Args:
            text: Text to analyze

        Returns:
            DetectionResult
        """
        if not self.is_available():
            return DetectionResult(
                ai_probability=0.5,
                confidence=0.0,
                method="openai_api",
                error="OpenAI API not available (missing API key)",
            )

        if not self.validate_text(text):
            return DetectionResult(
                ai_probability=0.5,
                confidence=0.0,
                method="openai_api",
                error="Text too short for reliable detection",
            )

        try:
            # Truncate text if too long (to save costs)
            words = text.split()
            if len(words) > 1000:
                text = " ".join(words[:1000])
                self.logger.debug("Truncated text to 1000 words for OpenAI API")

            # Prepare prompt
            prompt = self.detection_prompt.format(text=text)

            # Call OpenAI API
            self.logger.debug(f"Calling OpenAI API with model {self.model}")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful AI text detection assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            # Parse response
            content = response.choices[0].message.content.strip()

            # Try to parse JSON response
            # Extract JSON from response (in case there's extra text)
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                json_str = content[json_start:json_end]
                result_data = json.loads(json_str)

                ai_prob = float(result_data.get("ai_probability", 0.5))
                confidence = float(result_data.get("confidence", 0.7))
                suspected_model = result_data.get("suspected_model", "unknown")
                reasoning = result_data.get("reasoning", "")

                self.logger.debug(
                    f"OpenAI detection: AI prob={ai_prob:.2f}, confidence={confidence:.2f}"
                )

                return DetectionResult(
                    ai_probability=ai_prob,
                    confidence=confidence,
                    method="openai_api",
                    details={
                        "suspected_model": suspected_model,
                        "reasoning": reasoning,
                        "model_used": self.model,
                    },
                )
            else:
                raise ValueError("No valid JSON found in response")

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse OpenAI response: {e}")
            self.logger.debug(f"Response content: {content}")
            return DetectionResult(
                ai_probability=0.5,
                confidence=0.0,
                method="openai_api",
                error=f"Failed to parse API response: {str(e)}",
            )

        except Exception as e:
            self.logger.error(f"OpenAI API error: {e}")
            return DetectionResult(
                ai_probability=0.5,
                confidence=0.0,
                method="openai_api",
                error=f"API error: {str(e)}",
            )
