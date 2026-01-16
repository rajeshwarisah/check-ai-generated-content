"""Content classification module for identifying page content types."""

from typing import Dict, List, Tuple
from PIL import Image

from ..utils.logger import get_logger
from ..utils.validators import validate_text_length, validate_image_size


class ContentClassifier:
    """Classify page content into types (text, image, table, mixed)."""

    def __init__(self, config: Dict):
        """
        Initialize content classifier.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.logger = get_logger()

        # Get configuration
        classification_config = config.get("content_classification", {})
        self.priority_order = classification_config.get(
            "priority_order", ["table", "image_with_text", "image", "text"]
        )

        # Table detection settings
        table_config = classification_config.get("table_detection", {})
        self.min_table_rows = table_config.get("min_rows", 2)
        self.min_table_cols = table_config.get("min_cols", 2)

        # Text detection settings
        text_config = config.get("text_detection", {})
        self.min_text_words = text_config.get("min_words", 50)

        # Image detection settings
        image_config = config.get("image_detection", {})
        self.min_image_size = image_config.get("min_resolution", 64)

    def classify_page(self, page_data: Dict) -> Dict:
        """
        Classify page content type(s).

        Args:
            page_data: Page data from PDF extractor

        Returns:
            Classification result dictionary
        """
        page_num = page_data["page_number"]
        self.logger.debug(f"Classifying page {page_num}")

        # Analyze content
        has_tables = self._has_valid_tables(page_data["tables"])
        has_images = self._has_valid_images(page_data["images"])
        has_text = self._has_valid_text(page_data["text_blocks"])

        # Determine primary content type based on priority
        primary_type = self._determine_primary_type(has_tables, has_images, has_text)

        # Check for text in images
        has_text_in_images = False
        if has_images and page_data["images"]:
            has_text_in_images = True  # Will be verified during detection

        # Create classification result
        result = {
            "page_number": page_num,
            "primary_type": primary_type,
            "content_types": {
                "has_tables": has_tables,
                "has_images": has_images,
                "has_text": has_text,
                "has_text_in_images": has_text_in_images,
            },
            "is_mixed_content": sum([has_tables, has_images, has_text]) > 1,
            "elements": self._classify_elements(page_data),
        }

        self.logger.debug(
            f"Page {page_num} classification: primary={primary_type}, "
            f"mixed={result['is_mixed_content']}"
        )

        return result

    def _has_valid_tables(self, tables: List[Dict]) -> bool:
        """
        Check if page has valid tables.

        Args:
            tables: List of table dictionaries

        Returns:
            True if page has valid tables
        """
        for table in tables:
            rows = table.get("rows", 0)
            cols = table.get("cols", 0)

            if rows >= self.min_table_rows and cols >= self.min_table_cols:
                return True

        return False

    def _has_valid_images(self, images: List[Dict]) -> bool:
        """
        Check if page has valid images.

        Args:
            images: List of image dictionaries

        Returns:
            True if page has valid images
        """
        for image_data in images:
            width = image_data.get("width", 0)
            height = image_data.get("height", 0)

            if validate_image_size(width, height, self.min_image_size):
                return True

        return False

    def _has_valid_text(self, text_blocks: List[Dict]) -> bool:
        """
        Check if page has sufficient text.

        Args:
            text_blocks: List of text block dictionaries

        Returns:
            True if page has sufficient text
        """
        # Combine all text
        all_text = " ".join(block.get("text", "") for block in text_blocks)

        return validate_text_length(all_text, self.min_text_words)

    def _determine_primary_type(
        self, has_tables: bool, has_images: bool, has_text: bool
    ) -> str:
        """
        Determine primary content type based on priority.

        Args:
            has_tables: Whether page has tables
            has_images: Whether page has images
            has_text: Whether page has text

        Returns:
            Primary content type
        """
        # Priority: tables > images > text
        if has_tables:
            return "table"
        elif has_images:
            return "image"
        elif has_text:
            return "text"
        else:
            return "empty"

    def _classify_elements(self, page_data: Dict) -> List[Dict]:
        """
        Classify individual elements on the page.

        Args:
            page_data: Page data from PDF extractor

        Returns:
            List of classified elements
        """
        elements = []

        # Classify tables
        for i, table in enumerate(page_data["tables"]):
            if (
                table["rows"] >= self.min_table_rows
                and table["cols"] >= self.min_table_cols
            ):
                elements.append(
                    {
                        "type": "table",
                        "index": i,
                        "bbox": table["bbox"],
                        "data": table["data"],
                        "priority": self._get_priority("table"),
                    }
                )

        # Classify images
        for i, image_data in enumerate(page_data["images"]):
            if validate_image_size(
                image_data["width"], image_data["height"], self.min_image_size
            ):
                elements.append(
                    {
                        "type": "image",
                        "index": i,
                        "bbox": image_data["bbox"],
                        "image": image_data["image"],
                        "priority": self._get_priority("image"),
                    }
                )

        # Classify text blocks
        all_text = " ".join(block.get("text", "") for block in page_data["text_blocks"])
        if validate_text_length(all_text, self.min_text_words):
            # Combine text blocks into one element
            # Get bounding box that encompasses all text
            if page_data["text_blocks"]:
                all_bboxes = [block["bbox"] for block in page_data["text_blocks"]]
                combined_bbox = self._merge_bboxes(all_bboxes)
            else:
                combined_bbox = [0, 0, 0, 0]

            elements.append(
                {
                    "type": "text",
                    "index": 0,
                    "bbox": combined_bbox,
                    "text": all_text,
                    "priority": self._get_priority("text"),
                }
            )

        # Sort by priority
        elements.sort(key=lambda x: x["priority"])

        return elements

    def _get_priority(self, content_type: str) -> int:
        """
        Get priority value for content type (lower is higher priority).

        Args:
            content_type: Content type string

        Returns:
            Priority value
        """
        try:
            return self.priority_order.index(content_type)
        except ValueError:
            return 999  # Lowest priority

    def _merge_bboxes(self, bboxes: List[List[float]]) -> List[float]:
        """
        Merge multiple bounding boxes into one encompassing box.

        Args:
            bboxes: List of bounding boxes [x0, y0, x1, y1]

        Returns:
            Merged bounding box
        """
        if not bboxes:
            return [0, 0, 0, 0]

        x0 = min(bbox[0] for bbox in bboxes)
        y0 = min(bbox[1] for bbox in bboxes)
        x1 = max(bbox[2] for bbox in bboxes)
        y1 = max(bbox[3] for bbox in bboxes)

        return [x0, y0, x1, y1]

    def should_analyze_element(self, element: Dict) -> bool:
        """
        Determine if an element should be analyzed.

        Args:
            element: Element dictionary

        Returns:
            True if element should be analyzed
        """
        element_type = element["type"]

        if element_type == "table":
            return True  # Always analyze tables

        elif element_type == "image":
            # Check image size
            image = element.get("image")
            if image:
                return validate_image_size(
                    image.width, image.height, self.min_image_size
                )
            return False

        elif element_type == "text":
            # Check text length
            text = element.get("text", "")
            return validate_text_length(text, self.min_text_words)

        return False
