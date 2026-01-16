"""Page processor that orchestrates PDF extraction and content classification."""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
from rich.progress import Progress, TaskID

from .pdf_extractor import PDFExtractor
from .content_classifier import ContentClassifier
from ..utils.config import get_config
from ..utils.logger import get_logger
from ..utils.validators import (
    validate_pdf_path,
    validate_pdf_integrity,
    validate_page_range,
)
from ..utils.error_handlers import (
    PDFProcessingError,
    PageProcessingError,
    handle_page_error,
)


class PageProcessor:
    """Main processor for handling PDF pages."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize page processor.

        Args:
            config_path: Path to configuration file
        """
        self.config = get_config(config_path)
        self.logger = get_logger()
        self.classifier = ContentClassifier(self.config.to_dict())

    def process_pdf(
        self,
        pdf_path: str,
        page_range: Optional[str] = None,
        show_progress: bool = True,
    ) -> Dict:
        """
        Process PDF document.

        Args:
            pdf_path: Path to PDF file
            page_range: Page range to process (e.g., "1-10", None for all)
            show_progress: Show progress bar

        Returns:
            Processing results dictionary

        Raises:
            PDFProcessingError: If PDF processing fails
        """
        # Validate PDF
        self.logger.info(f"Processing PDF: {pdf_path}")
        try:
            pdf_path_obj = validate_pdf_path(pdf_path)
        except Exception as e:
            raise PDFProcessingError(f"Invalid PDF path: {e}")

        # Check PDF integrity
        is_valid, error_msg = validate_pdf_integrity(pdf_path_obj)
        if not is_valid:
            raise PDFProcessingError(error_msg)

        # Open PDF
        with PDFExtractor(pdf_path_obj, enable_ocr=True) as extractor:
            total_pages = extractor.page_count
            self.logger.info(f"PDF has {total_pages} pages")

            # Validate and parse page range
            try:
                start_page, end_page = validate_page_range(page_range, total_pages)
                self.logger.info(f"Processing pages {start_page} to {end_page}")
            except Exception as e:
                raise PDFProcessingError(f"Invalid page range: {e}")

            # Check max pages limit
            max_pages = self.config.get("pdf_processing.max_pages", 450)
            pages_to_process = end_page - start_page + 1
            if pages_to_process > max_pages:
                raise PDFProcessingError(
                    f"Page count ({pages_to_process}) exceeds maximum ({max_pages})"
                )

            # Process pages
            results = []
            failed_pages = []

            if show_progress:
                with Progress() as progress:
                    task = progress.add_task(
                        "[cyan]Processing pages...", total=pages_to_process
                    )

                    for page_num in range(start_page, end_page + 1):
                        result = self._process_single_page(extractor, page_num)
                        if result["status"] == "failed":
                            failed_pages.append(page_num)
                        results.append(result)
                        progress.update(task, advance=1)
            else:
                for page_num in range(start_page, end_page + 1):
                    result = self._process_single_page(extractor, page_num)
                    if result["status"] == "failed":
                        failed_pages.append(page_num)
                    results.append(result)

            # Create summary
            summary = {
                "pdf_path": str(pdf_path_obj),
                "total_pages": total_pages,
                "processed_pages": pages_to_process,
                "successful_pages": pages_to_process - len(failed_pages),
                "failed_pages": failed_pages,
                "page_range": f"{start_page}-{end_page}",
            }

            self.logger.info(
                f"Processing complete: {summary['successful_pages']}/{pages_to_process} pages successful"
            )

            if failed_pages:
                self.logger.warning(f"Failed pages: {failed_pages}")

            return {
                "summary": summary,
                "results": results,
            }

    def _process_single_page(
        self, extractor: PDFExtractor, page_num: int
    ) -> Dict:
        """
        Process a single page.

        Args:
            extractor: PDF extractor instance
            page_num: Page number to process

        Returns:
            Page processing result
        """
        try:
            # Extract page content
            page_data = extractor.extract_page(page_num)

            # Classify content
            classification = self.classifier.classify_page(page_data)

            # Combine results
            result = {
                "page_number": page_num,
                "status": "success",
                "extraction": page_data,
                "classification": classification,
            }

            return result

        except PageProcessingError as e:
            self.logger.error(f"Page {page_num} processing failed: {e}")
            return handle_page_error(page_num, e, self.logger)

        except Exception as e:
            self.logger.error(f"Unexpected error processing page {page_num}: {e}")
            return handle_page_error(page_num, e, self.logger)

    def process_single_page_standalone(
        self, pdf_path: str, page_num: int
    ) -> Dict:
        """
        Process a single page as a standalone operation.

        Args:
            pdf_path: Path to PDF file
            page_num: Page number to process

        Returns:
            Page processing result
        """
        # Validate PDF
        pdf_path_obj = validate_pdf_path(pdf_path)

        with PDFExtractor(pdf_path_obj, enable_ocr=True) as extractor:
            if page_num < 1 or page_num > extractor.page_count:
                raise PDFProcessingError(
                    f"Page number {page_num} out of range (1-{extractor.page_count})"
                )

            return self._process_single_page(extractor, page_num)

    def get_pdf_info(self, pdf_path: str) -> Dict:
        """
        Get basic information about a PDF.

        Args:
            pdf_path: Path to PDF file

        Returns:
            PDF information dictionary
        """
        pdf_path_obj = validate_pdf_path(pdf_path)

        with PDFExtractor(pdf_path_obj, enable_ocr=False) as extractor:
            return {
                "path": str(pdf_path_obj),
                "page_count": extractor.page_count,
                "file_size": pdf_path_obj.stat().st_size,
            }
