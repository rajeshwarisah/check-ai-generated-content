"""Input validation utilities for the AI content detection system."""

from pathlib import Path
from typing import Optional, Tuple
import fitz  # PyMuPDF


class ValidationError(Exception):
    """Custom exception for validation errors."""

    pass


def validate_pdf_path(pdf_path: str) -> Path:
    """
    Validate PDF file path.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Path object

    Raises:
        ValidationError: If path is invalid or file doesn't exist
    """
    path = Path(pdf_path)

    if not path.exists():
        raise ValidationError(f"PDF file not found: {pdf_path}")

    if not path.is_file():
        raise ValidationError(f"Path is not a file: {pdf_path}")

    if path.suffix.lower() != ".pdf":
        raise ValidationError(f"File is not a PDF: {pdf_path}")

    return path


def validate_pdf_integrity(pdf_path: Path) -> Tuple[bool, Optional[str]]:
    """
    Check if PDF file is valid and not corrupted.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        doc = fitz.open(pdf_path)

        # Check if PDF is encrypted/password protected
        if doc.is_encrypted:
            doc.close()
            return False, "PDF is password-protected or encrypted"

        # Check if PDF has pages
        if doc.page_count == 0:
            doc.close()
            return False, "PDF has no pages"

        doc.close()
        return True, None

    except Exception as e:
        return False, f"PDF is corrupted or invalid: {str(e)}"


def validate_page_range(
    page_range: Optional[str], total_pages: int
) -> Tuple[int, int]:
    """
    Validate and parse page range specification.

    Args:
        page_range: Page range string (e.g., "1-10", "5", None for all)
        total_pages: Total number of pages in document

    Returns:
        Tuple of (start_page, end_page) (1-indexed, inclusive)

    Raises:
        ValidationError: If page range is invalid
    """
    if page_range is None or page_range.strip() == "":
        return 1, total_pages

    try:
        if "-" in page_range:
            # Range specification
            parts = page_range.split("-")
            if len(parts) != 2:
                raise ValidationError(
                    f"Invalid page range format: {page_range}. Use format '1-10'"
                )

            start = int(parts[0].strip())
            end = int(parts[1].strip())

            if start < 1:
                raise ValidationError("Page numbers must start from 1")

            if start > end:
                raise ValidationError(
                    f"Start page ({start}) must be less than or equal to end page ({end})"
                )

            if end > total_pages:
                raise ValidationError(
                    f"End page ({end}) exceeds total pages ({total_pages})"
                )

            return start, end

        else:
            # Single page
            page = int(page_range.strip())

            if page < 1:
                raise ValidationError("Page numbers must start from 1")

            if page > total_pages:
                raise ValidationError(
                    f"Page {page} exceeds total pages ({total_pages})"
                )

            return page, page

    except ValueError as e:
        if "invalid literal" in str(e):
            raise ValidationError(f"Invalid page number in range: {page_range}")
        raise ValidationError(str(e))


def validate_output_path(output_path: str) -> Path:
    """
    Validate output file path.

    Args:
        output_path: Path to output file

    Returns:
        Path object

    Raises:
        ValidationError: If path is invalid
    """
    path = Path(output_path)

    # Ensure parent directory exists
    if not path.parent.exists():
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise ValidationError(f"Cannot create output directory: {e}")

    # Check if we can write to this location
    try:
        # Try creating a temporary file
        test_file = path.parent / ".write_test"
        test_file.touch()
        test_file.unlink()
    except Exception as e:
        raise ValidationError(f"Cannot write to output location: {e}")

    return path


def validate_text_length(text: str, min_words: int = 50) -> bool:
    """
    Check if text has minimum required length for analysis.

    Args:
        text: Text to validate
        min_words: Minimum number of words required

    Returns:
        True if text is long enough, False otherwise
    """
    if not text or not text.strip():
        return False

    word_count = len(text.split())
    return word_count >= min_words


def validate_image_size(width: int, height: int, min_size: int = 64) -> bool:
    """
    Check if image meets minimum size requirements.

    Args:
        width: Image width in pixels
        height: Image height in pixels
        min_size: Minimum dimension in pixels

    Returns:
        True if image is large enough, False otherwise
    """
    return width >= min_size and height >= min_size


def validate_api_key(api_key: Optional[str]) -> bool:
    """
    Validate API key is present and non-empty.

    Args:
        api_key: API key string

    Returns:
        True if valid, False otherwise
    """
    return api_key is not None and len(api_key.strip()) > 0
