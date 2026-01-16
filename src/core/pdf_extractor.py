"""PDF extraction module for text, images, and tables."""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
import fitz  # PyMuPDF
import pdfplumber
from PIL import Image
import io
import pytesseract
import pandas as pd

from ..utils.logger import get_logger
from ..utils.error_handlers import ErrorContext, PageProcessingError


class PDFExtractor:
    """Extract content from PDF documents."""

    def __init__(self, pdf_path: Path, enable_ocr: bool = True):
        """
        Initialize PDF extractor.

        Args:
            pdf_path: Path to PDF file
            enable_ocr: Enable OCR for scanned documents
        """
        self.pdf_path = pdf_path
        self.enable_ocr = enable_ocr
        self.logger = get_logger()

        # Open PDF with PyMuPDF
        try:
            self.fitz_doc = fitz.open(pdf_path)
            self.logger.info(f"Opened PDF: {pdf_path} ({self.fitz_doc.page_count} pages)")
        except Exception as e:
            self.logger.error(f"Failed to open PDF with PyMuPDF: {e}")
            raise

        # Open PDF with pdfplumber for table extraction
        try:
            self.plumber_doc = pdfplumber.open(pdf_path)
        except Exception as e:
            self.logger.warning(f"Failed to open PDF with pdfplumber: {e}")
            self.plumber_doc = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        """Close PDF documents."""
        if hasattr(self, "fitz_doc"):
            self.fitz_doc.close()
        if hasattr(self, "plumber_doc") and self.plumber_doc:
            self.plumber_doc.close()

    @property
    def page_count(self) -> int:
        """Get total number of pages."""
        return self.fitz_doc.page_count

    def extract_page(self, page_num: int) -> Dict:
        """
        Extract all content from a single page.

        Args:
            page_num: Page number (1-indexed)

        Returns:
            Dictionary with extracted content

        Raises:
            PageProcessingError: If page extraction fails
        """
        try:
            self.logger.debug(f"Extracting page {page_num}")

            # Convert to 0-indexed for PyMuPDF
            page_index = page_num - 1

            # Extract page image
            page_image = self._render_page_image(page_index)

            # Extract text
            text_blocks = self._extract_text_blocks(page_index)

            # Check if page needs OCR
            needs_ocr = self._check_if_scanned(text_blocks)

            if needs_ocr and self.enable_ocr:
                self.logger.info(f"Page {page_num} appears to be scanned, applying OCR")
                ocr_text = self._apply_ocr(page_image)
                # Add OCR text as a single block
                if ocr_text.strip():
                    text_blocks.append(
                        {
                            "text": ocr_text,
                            "bbox": [0, 0, page_image.width, page_image.height],
                            "font_info": {"ocr": True},
                        }
                    )

            # Extract images
            images = self._extract_images(page_index)

            # Extract tables
            tables = self._extract_tables(page_index)

            result = {
                "page_number": page_num,
                "page_image": page_image,
                "text_blocks": text_blocks,
                "images": images,
                "tables": tables,
                "needs_ocr": needs_ocr,
                "metadata": self._get_page_metadata(page_index),
            }

            self.logger.debug(
                f"Page {page_num} extraction complete: "
                f"{len(text_blocks)} text blocks, "
                f"{len(images)} images, "
                f"{len(tables)} tables"
            )

            return result

        except Exception as e:
            raise PageProcessingError(page_num, str(e))

    def _render_page_image(self, page_index: int, dpi: int = 150) -> Image.Image:
        """
        Render page as image.

        Args:
            page_index: Page index (0-indexed)
            dpi: Resolution for rendering

        Returns:
            PIL Image
        """
        page = self.fitz_doc[page_index]
        # Render at specified DPI
        zoom = dpi / 72  # 72 is default DPI
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)

        # Convert to PIL Image
        img_data = pix.tobytes("png")
        image = Image.open(io.BytesIO(img_data))

        return image

    def _extract_text_blocks(self, page_index: int) -> List[Dict]:
        """
        Extract text blocks with position information.

        Args:
            page_index: Page index (0-indexed)

        Returns:
            List of text block dictionaries
        """
        page = self.fitz_doc[page_index]
        blocks = []

        # Get text blocks with position
        text_dict = page.get_text("dict")

        for block in text_dict.get("blocks", []):
            if block.get("type") == 0:  # Text block
                # Extract text from lines
                text_content = []
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text_content.append(span.get("text", ""))

                text = " ".join(text_content).strip()

                if text:
                    bbox = block.get("bbox", [0, 0, 0, 0])
                    # Get font info from first span if available
                    font_info = {}
                    if block.get("lines"):
                        first_line = block["lines"][0]
                        if first_line.get("spans"):
                            first_span = first_line["spans"][0]
                            font_info = {
                                "size": first_span.get("size", 0),
                                "font": first_span.get("font", ""),
                                "color": first_span.get("color", 0),
                            }

                    blocks.append(
                        {
                            "text": text,
                            "bbox": list(bbox),
                            "font_info": font_info,
                        }
                    )

        return blocks

    def _check_if_scanned(self, text_blocks: List[Dict]) -> bool:
        """
        Check if page appears to be scanned (minimal text extracted).

        Args:
            text_blocks: List of extracted text blocks

        Returns:
            True if page appears to be scanned
        """
        if not text_blocks:
            return True

        # Calculate total text length
        total_text = " ".join(block["text"] for block in text_blocks)
        word_count = len(total_text.split())

        # If very few words, likely scanned
        return word_count < 10

    def _apply_ocr(self, image: Image.Image) -> str:
        """
        Apply OCR to extract text from image.

        Args:
            image: PIL Image

        Returns:
            Extracted text
        """
        try:
            text = pytesseract.image_to_string(image, lang="eng")
            return text
        except Exception as e:
            self.logger.warning(f"OCR failed: {e}")
            return ""

    def _extract_images(self, page_index: int) -> List[Dict]:
        """
        Extract images from page.

        Args:
            page_index: Page index (0-indexed)

        Returns:
            List of image dictionaries
        """
        page = self.fitz_doc[page_index]
        images = []

        image_list = page.get_images(full=True)

        for img_index, img_info in enumerate(image_list):
            try:
                xref = img_info[0]
                base_image = self.fitz_doc.extract_image(xref)

                # Convert to PIL Image
                image_bytes = base_image["image"]
                image = Image.open(io.BytesIO(image_bytes))

                # Get image position (approximate)
                # Note: Getting exact bbox for images is complex, using page bounds as fallback
                rect = page.rect
                bbox = [rect.x0, rect.y0, rect.x1, rect.y1]

                # Try to get better position using image references
                img_rects = page.get_image_rects(xref)
                if img_rects:
                    bbox = list(img_rects[0])

                images.append(
                    {
                        "image": image,
                        "bbox": bbox,
                        "width": image.width,
                        "height": image.height,
                        "format": base_image.get("ext", "unknown"),
                    }
                )

            except Exception as e:
                self.logger.warning(f"Failed to extract image {img_index}: {e}")
                continue

        return images

    def _extract_tables(self, page_index: int) -> List[Dict]:
        """
        Extract tables from page.

        Args:
            page_index: Page index (0-indexed)

        Returns:
            List of table dictionaries
        """
        tables = []

        if self.plumber_doc is None:
            return tables

        try:
            # Get page from pdfplumber (1-indexed)
            page = self.plumber_doc.pages[page_index]

            # Extract tables
            extracted_tables = page.extract_tables()

            for table_data in extracted_tables:
                if table_data:
                    # Convert to pandas DataFrame
                    df = pd.DataFrame(table_data[1:], columns=table_data[0])

                    # Clean up None values
                    df = df.fillna("")

                    # Get table bounding box (approximate)
                    bbox = page.bbox  # Fallback to page bbox

                    tables.append(
                        {
                            "data": df,
                            "bbox": list(bbox),
                            "rows": len(df),
                            "cols": len(df.columns),
                        }
                    )

        except Exception as e:
            self.logger.warning(f"Table extraction failed for page {page_index + 1}: {e}")

        return tables

    def _get_page_metadata(self, page_index: int) -> Dict:
        """
        Get page metadata.

        Args:
            page_index: Page index (0-indexed)

        Returns:
            Dictionary with metadata
        """
        page = self.fitz_doc[page_index]
        rect = page.rect

        return {
            "width": rect.width,
            "height": rect.height,
            "rotation": page.rotation,
        }

    def extract_text_from_image(self, image: Image.Image) -> str:
        """
        Extract text from an image using OCR.

        Args:
            image: PIL Image

        Returns:
            Extracted text
        """
        if not self.enable_ocr:
            return ""

        return self._apply_ocr(image)
