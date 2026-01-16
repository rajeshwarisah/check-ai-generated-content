"""Forensic image analyzer for AI-generated image detection."""

from typing import Dict
import numpy as np
from PIL import Image
import io

from ...utils.logger import get_logger


class ForensicImageAnalyzer:
    """Analyze images for AI generation using forensic techniques."""

    def __init__(self, config: Dict):
        """
        Initialize forensic analyzer.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.logger = get_logger()

    def analyze(self, image: Image.Image) -> Dict:
        """
        Analyze image using forensic techniques.

        Args:
            image: PIL Image to analyze

        Returns:
            Analysis results with AI probability
        """
        try:
            features = {}
            scores = []

            # Check image format and compression
            compression_score = self._analyze_compression(image)
            features["compression_artifacts"] = compression_score
            scores.append(compression_score)

            # Analyze noise patterns
            noise_score = self._analyze_noise_patterns(image)
            features["noise_consistency"] = noise_score
            scores.append(noise_score)

            # Check color distribution
            color_score = self._analyze_color_distribution(image)
            features["color_distribution"] = color_score
            scores.append(color_score)

            # Average all scores
            avg_score = np.mean(scores)

            # Confidence based on score variance
            confidence = 1.0 - (np.std(scores) / 0.5)  # Normalized
            confidence = max(0.0, min(1.0, confidence))

            self.logger.debug(
                f"Forensic analysis: compression={compression_score:.2f}, "
                f"noise={noise_score:.2f}, color={color_score:.2f}"
            )

            return {
                "ai_probability": avg_score,
                "confidence": confidence,
                "features": features,
            }

        except Exception as e:
            self.logger.error(f"Forensic analysis error: {e}")
            return {
                "ai_probability": 0.5,
                "confidence": 0.0,
                "error": str(e),
            }

    def _analyze_compression(self, image: Image.Image) -> float:
        """
        Analyze JPEG compression artifacts.
        AI images often have unusual compression patterns.
        """
        try:
            # Save to bytes and check quality
            buffer = io.BytesIO()

            # Convert to RGB if needed
            if image.mode != "RGB":
                image = image.convert("RGB")

            # Save as JPEG with quality 95
            image.save(buffer, format="JPEG", quality=95)
            size_high = buffer.tell()

            # Save as JPEG with quality 75
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=75)
            size_low = buffer.tell()

            # Compression ratio - AI images often compress differently
            if size_high > 0:
                ratio = size_low / size_high

                # Normal photos: ratio ~0.5-0.7
                # AI images: often higher (more uniform patterns)
                if ratio > 0.75:
                    return 0.6  # Slightly suspicious
                elif ratio > 0.7:
                    return 0.5  # Normal
                else:
                    return 0.4  # Likely real photo

            return 0.5

        except Exception as e:
            self.logger.debug(f"Compression analysis failed: {e}")
            return 0.5

    def _analyze_noise_patterns(self, image: Image.Image) -> float:
        """
        Analyze noise patterns.
        AI images often have very uniform or absent noise.
        """
        try:
            # Convert to numpy array
            img_array = np.array(image.convert("RGB"))

            # Calculate noise in different regions
            height, width = img_array.shape[:2]

            # Divide image into quadrants
            regions = [
                img_array[:height//2, :width//2],
                img_array[:height//2, width//2:],
                img_array[height//2:, :width//2],
                img_array[height//2:, width//2:],
            ]

            # Calculate standard deviation in each region
            region_stds = []
            for region in regions:
                if region.size > 0:
                    std = np.std(region)
                    region_stds.append(std)

            if not region_stds:
                return 0.5

            # Check variance in noise across regions
            noise_variance = np.std(region_stds)

            # Real photos: moderate variance (10-30)
            # AI images: often very low variance (< 10) or very high (> 40)
            if noise_variance < 5:
                return 0.7  # Very uniform - suspicious
            elif noise_variance < 10:
                return 0.6  # Somewhat uniform
            elif noise_variance > 40:
                return 0.6  # Too variable
            else:
                return 0.4  # Normal variance

        except Exception as e:
            self.logger.debug(f"Noise analysis failed: {e}")
            return 0.5

    def _analyze_color_distribution(self, image: Image.Image) -> float:
        """
        Analyze color distribution patterns.
        AI images sometimes have unusual color distributions.
        """
        try:
            # Convert to RGB
            img_rgb = image.convert("RGB")
            img_array = np.array(img_rgb)

            # Calculate color histograms
            r_hist = np.histogram(img_array[:, :, 0], bins=256, range=(0, 256))[0]
            g_hist = np.histogram(img_array[:, :, 1], bins=256, range=(0, 256))[0]
            b_hist = np.histogram(img_array[:, :, 2], bins=256, range=(0, 256))[0]

            # Normalize
            total_pixels = img_array.shape[0] * img_array.shape[1]
            r_hist = r_hist / total_pixels
            g_hist = g_hist / total_pixels
            b_hist = b_hist / total_pixels

            # Calculate entropy for each channel
            r_entropy = -np.sum(r_hist[r_hist > 0] * np.log2(r_hist[r_hist > 0]))
            g_entropy = -np.sum(g_hist[g_hist > 0] * np.log2(g_hist[g_hist > 0]))
            b_entropy = -np.sum(b_hist[b_hist > 0] * np.log2(b_hist[b_hist > 0]))

            # Average entropy
            avg_entropy = (r_entropy + g_entropy + b_entropy) / 3

            # Real photos: entropy typically 6-8
            # AI images: often 5-6 (more uniform) or >8 (too varied)
            if avg_entropy < 5.5:
                return 0.65  # Too uniform
            elif avg_entropy > 8.0:
                return 0.6  # Too varied
            else:
                return 0.45  # Normal range

        except Exception as e:
            self.logger.debug(f"Color analysis failed: {e}")
            return 0.5
