"""Logging configuration for the AI content detection system."""

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


class Logger:
    """Custom logger with file and console output."""

    def __init__(
        self,
        name: str,
        log_dir: Optional[Path] = None,
        level: str = "INFO",
        console_enabled: bool = True,
        file_enabled: bool = True,
    ):
        """
        Initialize logger.

        Args:
            name: Logger name
            log_dir: Directory for log files
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            console_enabled: Enable console output
            file_enabled: Enable file output
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))
        self.logger.handlers = []  # Clear any existing handlers

        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Console handler
        if console_enabled:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(getattr(logging, level.upper()))
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

        # File handler
        if file_enabled and log_dir:
            log_dir = Path(log_dir)
            log_dir.mkdir(parents=True, exist_ok=True)

            # Create log file with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = log_dir / f"{name}_{timestamp}.log"

            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(getattr(logging, level.upper()))
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

            self.logger.info(f"Logging to file: {log_file}")

    def debug(self, message: str):
        """Log debug message."""
        self.logger.debug(message)

    def info(self, message: str):
        """Log info message."""
        self.logger.info(message)

    def warning(self, message: str):
        """Log warning message."""
        self.logger.warning(message)

    def error(self, message: str, exc_info: bool = False):
        """Log error message."""
        self.logger.error(message, exc_info=exc_info)

    def critical(self, message: str, exc_info: bool = False):
        """Log critical message."""
        self.logger.critical(message, exc_info=exc_info)

    def exception(self, message: str):
        """Log exception with traceback."""
        self.logger.exception(message)


def setup_logger(
    name: str = "ai_detector",
    config: Optional[dict] = None,
) -> Logger:
    """
    Set up logger with configuration.

    Args:
        name: Logger name
        config: Configuration dictionary

    Returns:
        Logger instance
    """
    if config is None:
        config = {}

    # Get logging configuration
    log_config = config.get("logging", {})
    output_config = config.get("output", {})

    level = log_config.get("level", "INFO")
    console_enabled = log_config.get("console_enabled", True)
    file_enabled = log_config.get("file_enabled", True)

    # Get log directory
    log_dir = None
    if file_enabled:
        from .config import get_config

        cfg = get_config()
        log_dir = cfg.get_output_dir("logs_dir")

    return Logger(
        name=name,
        log_dir=log_dir,
        level=level,
        console_enabled=console_enabled,
        file_enabled=file_enabled,
    )


# Global logger instance
_logger_instance: Optional[Logger] = None


def get_logger(name: str = "ai_detector") -> Logger:
    """
    Get or create global logger instance.

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    global _logger_instance
    if _logger_instance is None:
        from .config import get_config

        config = get_config()
        _logger_instance = setup_logger(name, config.to_dict())
    return _logger_instance
