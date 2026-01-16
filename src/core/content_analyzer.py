"""Content analyzer that integrates PDF extraction with AI detection."""

from typing import Dict, List, Optional
from pathlib import Path

from .page_processor import PageProcessor
from ..detectors.text.ensemble_text import EnsembleTextDetector
from ..detectors.image.image_detector import ImageDetector
from ..detectors.model_identifier import AIModelIdentifier
from ..utils.config import get_config
from ..utils.logger import get_logger
from ..utils.validators import validate_text_length


class ContentAnalyzer:
    """Analyze PDF content for AI-generated elements."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize content analyzer.

        Args:
            config_path: Path to configuration file
        """
        self.config = get_config(config_path)
        self.logger = get_logger()

        # Initialize components
        self.page_processor = PageProcessor(config_path)
        self.text_detector = EnsembleTextDetector(self.config.to_dict())
        self.image_detector = ImageDetector(self.config.to_dict())
        self.model_identifier = AIModelIdentifier()

        # Get configuration
        self.min_text_words = self.config.get("text_detection.min_words", 50)
        self.ai_threshold = self.config.get("thresholds.ai_detection", 0.80)

        self.logger.info("Content analyzer initialized")

    def analyze_pdf(
        self,
        pdf_path: str,
        page_range: Optional[str] = None,
        show_progress: bool = True,
    ) -> Dict:
        """
        Analyze entire PDF for AI-generated content.

        Args:
            pdf_path: Path to PDF file
            page_range: Page range to analyze (e.g., "1-10")
            show_progress: Show progress bars

        Returns:
            Complete analysis results
        """
        self.logger.info(f"Analyzing PDF: {pdf_path}")

        # Step 1: Extract content from PDF
        self.logger.info("Step 1: Extracting PDF content")
        extraction_results = self.page_processor.process_pdf(
            pdf_path, page_range, show_progress
        )

        # Step 2: Analyze each page
        self.logger.info("Step 2: Analyzing content for AI detection")
        analyzed_pages = []

        for page_result in extraction_results["results"]:
            if page_result["status"] == "failed":
                # Keep failed pages in results
                analyzed_pages.append(page_result)
                continue

            # Analyze this page
            page_analysis = self._analyze_page(page_result)
            analyzed_pages.append(page_analysis)

        # Step 3: Generate summary
        summary = self._generate_summary(analyzed_pages, extraction_results["summary"])

        self.logger.info(
            f"Analysis complete: {summary['ai_detected_pages']}/{summary['total_analyzed']} pages "
            f"contain AI-generated content"
        )

        return {
            "summary": summary,
            "pages": analyzed_pages,
            "pdf_info": {
                "path": pdf_path,
                "page_range": extraction_results["summary"]["page_range"],
            },
        }

    def _analyze_page(self, page_result: Dict) -> Dict:
        """
        Analyze a single page for AI-generated content.

        Args:
            page_result: Page result from extraction

        Returns:
            Page analysis with AI detection results
        """
        page_num = page_result["page_number"]
        self.logger.debug(f"Analyzing page {page_num}")

        classification = page_result["classification"]
        extraction = page_result["extraction"]

        # Analyze each classified element
        element_analyses = []

        for element in classification["elements"]:
            element_type = element["type"]

            if element_type == "text":
                # Text detection
                analysis = self._analyze_text_element(element)
                element_analyses.append(analysis)

            elif element_type == "table":
                # Tables are text-based
                analysis = self._analyze_table_element(element)
                element_analyses.append(analysis)

            elif element_type == "image":
                # Image detection (Phase 3 - placeholder for now)
                analysis = self._analyze_image_element(element)
                element_analyses.append(analysis)

        # Determine overall page status
        page_analysis = self._aggregate_page_results(
            page_num, classification, element_analyses
        )

        # Add original extraction data
        page_analysis["extraction"] = extraction
        page_analysis["classification"] = classification

        return page_analysis

    def _analyze_text_element(self, element: Dict) -> Dict:
        """Analyze text element for AI detection."""
        text = element.get("text", "")

        if not validate_text_length(text, self.min_text_words):
            return {
                "element_type": "text",
                "bbox": element["bbox"],
                "status": "skipped",
                "reason": f"Text too short (< {self.min_text_words} words)",
                "ai_probability": None,
                "confidence": None,
            }

        # Run text detection
        try:
            detection_result = self.text_detector.detect(text)

            if detection_result["status"] == "error":
                return {
                    "element_type": "text",
                    "bbox": element["bbox"],
                    "status": "error",
                    "error": detection_result.get("error"),
                    "ai_probability": None,
                    "confidence": None,
                }

            # Model identification (only if AI probability is high)
            suspected_model = None
            model_confidence = None

            if detection_result["ai_probability"] >= 0.5:  # Only identify if likely AI
                model_info = self.model_identifier.identify(text, detection_result)
                suspected_model = model_info["model"]
                model_confidence = model_info["confidence"]

            return {
                "element_type": "text",
                "bbox": element["bbox"],
                "status": "analyzed",
                "ai_probability": detection_result["ai_probability"],
                "confidence": detection_result["confidence"],
                "suspected_model": suspected_model,
                "model_confidence": model_confidence,
                "explanation": detection_result["explanation"],
                "individual_results": detection_result["individual_results"],
                "text_preview": " ".join(text.split()[:50]) + "...",
                "word_count": len(text.split()),
            }

        except Exception as e:
            self.logger.error(f"Text analysis error: {e}")
            return {
                "element_type": "text",
                "bbox": element["bbox"],
                "status": "error",
                "error": str(e),
                "ai_probability": None,
                "confidence": None,
            }

    def _analyze_table_element(self, element: Dict) -> Dict:
        """Analyze table element for AI detection."""
        # Convert table to text
        df = element.get("data")

        if df is None or df.empty:
            return {
                "element_type": "table",
                "bbox": element["bbox"],
                "status": "skipped",
                "reason": "Empty table",
                "ai_probability": None,
                "confidence": None,
            }

        # Convert table to text representation
        table_text = df.to_string()

        # Also include column headers and cell values as sentences
        text_parts = []
        text_parts.append(" ".join(str(col) for col in df.columns))
        for _, row in df.iterrows():
            text_parts.append(" ".join(str(val) for val in row.values))

        combined_text = " ".join(text_parts)

        if not validate_text_length(combined_text, self.min_text_words):
            return {
                "element_type": "table",
                "bbox": element["bbox"],
                "status": "skipped",
                "reason": f"Table text too short (< {self.min_text_words} words)",
                "ai_probability": None,
                "confidence": None,
                "table_size": f"{len(df)} rows × {len(df.columns)} cols",
            }

        # Run text detection on table content
        try:
            detection_result = self.text_detector.detect(combined_text)

            if detection_result["status"] == "error":
                return {
                    "element_type": "table",
                    "bbox": element["bbox"],
                    "status": "error",
                    "error": detection_result.get("error"),
                    "ai_probability": None,
                    "confidence": None,
                }

            return {
                "element_type": "table",
                "bbox": element["bbox"],
                "status": "analyzed",
                "ai_probability": detection_result["ai_probability"],
                "confidence": detection_result["confidence"],
                "explanation": detection_result["explanation"],
                "individual_results": detection_result["individual_results"],
                "table_size": f"{len(df)} rows × {len(df.columns)} cols",
                "word_count": len(combined_text.split()),
            }

        except Exception as e:
            self.logger.error(f"Table analysis error: {e}")
            return {
                "element_type": "table",
                "bbox": element["bbox"],
                "status": "error",
                "error": str(e),
                "ai_probability": None,
                "confidence": None,
            }

    def _analyze_image_element(self, element: Dict) -> Dict:
        """Analyze image element for AI detection."""
        image = element.get("image")

        if image is None:
            return {
                "element_type": "image",
                "bbox": element["bbox"],
                "status": "error",
                "error": "No image data",
                "ai_probability": None,
                "confidence": None,
            }

        try:
            # Run image detection
            detection_result = self.image_detector.detect(image)

            if detection_result["status"] == "skipped":
                return {
                    "element_type": "image",
                    "bbox": element["bbox"],
                    "status": "skipped",
                    "reason": detection_result.get("reason"),
                    "ai_probability": None,
                    "confidence": None,
                }

            if detection_result["status"] == "error":
                return {
                    "element_type": "image",
                    "bbox": element["bbox"],
                    "status": "error",
                    "error": detection_result.get("error"),
                    "ai_probability": None,
                    "confidence": None,
                }

            # If image has text, also analyze the text
            text_analysis = None
            if detection_result.get("has_text") and detection_result.get("extracted_text"):
                extracted_text = detection_result["extracted_text"]
                if validate_text_length(extracted_text, self.min_text_words):
                    try:
                        text_result = self.text_detector.detect(extracted_text)
                        if text_result["status"] == "success":
                            text_analysis = {
                                "ai_probability": text_result["ai_probability"],
                                "confidence": text_result["confidence"],
                                "word_count": len(extracted_text.split()),
                            }
                    except Exception as e:
                        self.logger.warning(f"Text analysis in image failed: {e}")

            return {
                "element_type": "image",
                "bbox": element["bbox"],
                "status": "analyzed",
                "ai_probability": detection_result["ai_probability"],
                "confidence": detection_result["confidence"],
                "method": detection_result.get("method"),
                "features": detection_result.get("features", {}),
                "image_size": detection_result.get("image_size"),
                "has_text": detection_result.get("has_text", False),
                "text_analysis": text_analysis,
            }

        except Exception as e:
            self.logger.error(f"Image analysis error: {e}")
            return {
                "element_type": "image",
                "bbox": element["bbox"],
                "status": "error",
                "error": str(e),
                "ai_probability": None,
                "confidence": None,
            }

    def _aggregate_page_results(
        self, page_num: int, classification: Dict, element_analyses: List[Dict]
    ) -> Dict:
        """Aggregate element analyses into overall page result."""
        analyzed_elements = [e for e in element_analyses if e["status"] == "analyzed"]

        if not analyzed_elements:
            return {
                "page_number": page_num,
                "status": "no_analysis",
                "reason": "No elements could be analyzed",
                "contains_ai": False,
                "ai_probability": None,
                "confidence": None,
                "elements": element_analyses,
            }

        # Calculate page-level metrics
        ai_probabilities = [e["ai_probability"] for e in analyzed_elements]
        confidences = [e["confidence"] for e in analyzed_elements]

        avg_ai_prob = sum(ai_probabilities) / len(ai_probabilities)
        avg_confidence = sum(confidences) / len(confidences)

        # Determine if page contains AI content
        contains_ai = avg_ai_prob >= self.ai_threshold

        # Count AI-detected elements
        ai_elements = [
            e for e in analyzed_elements if e["ai_probability"] >= self.ai_threshold
        ]

        return {
            "page_number": page_num,
            "status": "analyzed",
            "contains_ai": contains_ai,
            "ai_probability": avg_ai_prob,
            "confidence": avg_confidence,
            "elements_analyzed": len(analyzed_elements),
            "elements_with_ai": len(ai_elements),
            "elements": element_analyses,
            "primary_type": classification["primary_type"],
            "is_mixed_content": classification["is_mixed_content"],
        }

    def _generate_summary(self, analyzed_pages: List[Dict], extraction_summary: Dict) -> Dict:
        """Generate summary statistics for entire analysis."""
        total_pages = len(analyzed_pages)
        analyzed_pages_list = [p for p in analyzed_pages if p["status"] == "analyzed"]
        failed_pages = [p for p in analyzed_pages if p["status"] == "failed"]

        ai_detected_pages = [
            p for p in analyzed_pages_list if p.get("contains_ai", False)
        ]

        # Gather all analyzed elements
        all_elements = []
        for page in analyzed_pages_list:
            all_elements.extend(page.get("elements", []))

        analyzed_elements = [e for e in all_elements if e["status"] == "analyzed"]

        # Count by element type
        text_elements = [e for e in analyzed_elements if e["element_type"] == "text"]
        table_elements = [e for e in analyzed_elements if e["element_type"] == "table"]
        image_elements = [e for e in analyzed_elements if e["element_type"] == "image"]

        # AI detection stats
        ai_text_elements = [
            e for e in text_elements if e.get("ai_probability", 0) >= self.ai_threshold
        ]
        ai_table_elements = [
            e for e in table_elements if e.get("ai_probability", 0) >= self.ai_threshold
        ]

        return {
            "total_pages": total_pages,
            "total_analyzed": len(analyzed_pages_list),
            "total_failed": len(failed_pages),
            "ai_detected_pages": len(ai_detected_pages),
            "ai_percentage": (
                (len(ai_detected_pages) / len(analyzed_pages_list) * 100)
                if analyzed_pages_list
                else 0
            ),
            "elements": {
                "total_analyzed": len(analyzed_elements),
                "text_elements": len(text_elements),
                "table_elements": len(table_elements),
                "image_elements": len(image_elements),
                "ai_detected_text": len(ai_text_elements),
                "ai_detected_tables": len(ai_table_elements),
            },
            "failed_pages": [p["page_number"] for p in failed_pages],
        }
