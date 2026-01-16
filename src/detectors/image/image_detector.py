"""Image AI detector combining forensic analysis and text extraction."""

from typing import Dict, Optional
from PIL import Image
import pytesseract

from .forensic_analyzer import ForensicImageAnalyzer
from ...utils.logger import get_logger
from ...utils.validators import validate_image_size, validate_text_length


class ImageDetector:
    """Detect AI-generated images using forensic analysis."""

    def __init__(self, config: Dict):
        """
        Initialize image detector.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.logger = get_logger()

        # Get image detection config
        image_config = config.get("image_detection", {})
        self.min_resolution = image_config.get("min_resolution", 64)

        # Initialize forensic analyzer
        forensic_config = image_config.get("detectors", {}).get("forensic", {})
        self.forensic_analyzer = ForensicImageAnalyzer(forensic_config)

    def detect(self, image: Image.Image) -> Dict:
        """
        Detect if image is AI-generated.

        Args:
            image: PIL Image to analyze

        Returns:
            Detection results
        """
        # Validate image size
        if not validate_image_size(image.width, image.height, self.min_resolution):
            return {
                "status": "skipped",
                "reason": f"Image too small (min {self.min_resolution}x{self.min_resolution})",
                "ai_probability": None,
                "confidence": None,
            }

        try:
            # Run forensic analysis
            forensic_result = self.forensic_analyzer.analyze(image)

            # Extract text from image
            extracted_text = self._extract_text(image)

            return {
                "status": "analyzed",
                "ai_probability": forensic_result["ai_probability"],
                "confidence": forensic_result["confidence"],
                "method": "forensic_analysis",
                "features": forensic_result.get("features", {}),
                "extracted_text": extracted_text,
                "has_text": len(extracted_text.strip()) > 0,
                "image_size": f"{image.width}x{image.height}",
            }

        except Exception as e:
            self.logger.error(f"Image detection error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "ai_probability": None,
                "confidence": None,
            }

    def _extract_text(self, image: Image.Image) -> str:
        """Extract text from image using OCR."""
        try:
            text = pytesseract.image_to_string(image, lang="eng")
            return text.strip()
        except Exception as e:
            self.logger.debug(f"OCR failed: {e}")
            return ""

    def is_available(self) -> bool:
        """Check if detector is available."""
        return True  # Forensic analysis is always available
