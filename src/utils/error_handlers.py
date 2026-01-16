"""Error handling utilities for the AI content detection system."""

from typing import Any, Callable, Optional, TypeVar, cast
from functools import wraps
import traceback


T = TypeVar("T")


class PDFProcessingError(Exception):
    """Base exception for PDF processing errors."""

    pass


class PageProcessingError(Exception):
    """Exception for single page processing errors."""

    def __init__(self, page_number: int, message: str):
        self.page_number = page_number
        super().__init__(f"Error processing page {page_number}: {message}")


class APIError(Exception):
    """Exception for API-related errors."""

    pass


class ModelError(Exception):
    """Exception for model loading/inference errors."""

    pass


class ConfigurationError(Exception):
    """Exception for configuration errors."""

    pass


def handle_page_error(
    page_number: int, error: Exception, logger: Optional[Any] = None
) -> dict:
    """
    Handle errors that occur during page processing.

    Args:
        page_number: Page number where error occurred
        error: The exception that was raised
        logger: Logger instance

    Returns:
        Error result dictionary
    """
    error_message = str(error)
    error_type = type(error).__name__

    if logger:
        logger.error(
            f"Page {page_number} processing failed: {error_type} - {error_message}"
        )
        logger.debug(f"Traceback: {traceback.format_exc()}")

    return {
        "page_number": page_number,
        "status": "failed",
        "error_type": error_type,
        "error_message": error_message,
        "results": None,
    }


def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """
    Decorator to retry a function on failure.

    Args:
        max_retries: Maximum number of retry attempts
        delay: Delay between retries in seconds

    Returns:
        Decorated function
    """
    import time

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        time.sleep(delay * (2**attempt))  # Exponential backoff
                        continue
                    break

            # If we get here, all retries failed
            raise last_exception  # type: ignore

        return wrapper

    return decorator


def safe_execute(
    func: Callable[..., T],
    *args,
    default: Optional[T] = None,
    logger: Optional[Any] = None,
    **kwargs,
) -> T:
    """
    Safely execute a function and return default value on error.

    Args:
        func: Function to execute
        *args: Positional arguments for function
        default: Default value to return on error
        logger: Logger instance
        **kwargs: Keyword arguments for function

    Returns:
        Function result or default value
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if logger:
            logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
        return cast(T, default)


def validate_critical_error(error: Exception, logger: Optional[Any] = None) -> bool:
    """
    Determine if an error is critical and should halt processing.

    Args:
        error: Exception to evaluate
        logger: Logger instance

    Returns:
        True if error is critical, False otherwise
    """
    critical_errors = (
        PDFProcessingError,
        APIError,
        ConfigurationError,
        FileNotFoundError,
        PermissionError,
    )

    is_critical = isinstance(error, critical_errors)

    if is_critical and logger:
        logger.critical(f"Critical error encountered: {type(error).__name__}")

    return is_critical


class ErrorContext:
    """Context manager for handling errors with automatic logging."""

    def __init__(
        self,
        operation: str,
        logger: Optional[Any] = None,
        raise_on_error: bool = True,
        default_return: Optional[Any] = None,
    ):
        """
        Initialize error context.

        Args:
            operation: Description of operation being performed
            logger: Logger instance
            raise_on_error: Whether to re-raise exceptions
            default_return: Default value to return on error (if not raising)
        """
        self.operation = operation
        self.logger = logger
        self.raise_on_error = raise_on_error
        self.default_return = default_return
        self.error: Optional[Exception] = None

    def __enter__(self):
        if self.logger:
            self.logger.debug(f"Starting: {self.operation}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.error = exc_val
            if self.logger:
                self.logger.error(
                    f"Error in {self.operation}: {exc_type.__name__} - {exc_val}",
                    exc_info=True,
                )

            if self.raise_on_error:
                return False  # Re-raise the exception

            return True  # Suppress the exception

        if self.logger:
            self.logger.debug(f"Completed: {self.operation}")
        return True


def format_error_for_report(error: Exception, context: Optional[str] = None) -> dict:
    """
    Format error information for inclusion in reports.

    Args:
        error: Exception to format
        context: Additional context information

    Returns:
        Dictionary with formatted error information
    """
    return {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "context": context,
        "is_critical": validate_critical_error(error),
    }
