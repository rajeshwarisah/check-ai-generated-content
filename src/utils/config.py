"""Configuration management for the AI content detection system."""

import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
from dotenv import load_dotenv


class Config:
    """Configuration manager that loads settings from YAML and environment variables."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration.

        Args:
            config_path: Path to custom config file. If None, uses default config.
        """
        # Load environment variables
        load_dotenv()

        # Determine project root
        self.project_root = Path(__file__).parent.parent.parent

        # Load configuration file
        if config_path is None:
            config_path = self.project_root / "config" / "default.yaml"
        else:
            config_path = Path(config_path)

        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path, "r") as f:
            self._config = yaml.safe_load(f)

        # Override with environment variables where applicable
        self._apply_env_overrides()

    def _apply_env_overrides(self):
        """Override config values with environment variables."""
        # OpenAI API configuration
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            if "text_detection" not in self._config:
                self._config["text_detection"] = {}
            if "detectors" not in self._config["text_detection"]:
                self._config["text_detection"]["detectors"] = {}
            if "openai" not in self._config["text_detection"]["detectors"]:
                self._config["text_detection"]["detectors"]["openai"] = {}
            self._config["text_detection"]["detectors"]["openai"]["api_key"] = openai_key

        # Override model from env if present
        openai_model = os.getenv("OPENAI_MODEL")
        if openai_model:
            self._config["text_detection"]["detectors"]["openai"]["model"] = openai_model

        # Thresholds
        ai_threshold = os.getenv("AI_DETECTION_THRESHOLD")
        if ai_threshold:
            self._config["thresholds"]["ai_detection"] = float(ai_threshold)

        # Processing configuration
        max_pages = os.getenv("MAX_PDF_PAGES")
        if max_pages:
            self._config["pdf_processing"]["max_pages"] = int(max_pages)

        # Output directories
        output_dir = os.getenv("OUTPUT_DIR")
        if output_dir:
            self._config["output"]["reports_dir"] = output_dir

        log_dir = os.getenv("LOG_DIR")
        if log_dir:
            self._config["output"]["logs_dir"] = log_dir

        # Log level
        log_level = os.getenv("LOG_LEVEL")
        if log_level:
            self._config["logging"]["level"] = log_level

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.

        Args:
            key_path: Dot-separated path to config value (e.g., "thresholds.ai_detection")
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key_path.split(".")
        value = self._config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def get_threshold(self, threshold_type: str) -> float:
        """Get a detection threshold value."""
        return self.get(f"thresholds.{threshold_type}", 0.80)

    def get_output_dir(self, dir_type: str = "reports_dir") -> Path:
        """Get output directory path and ensure it exists."""
        dir_path = self.project_root / self.get(f"output.{dir_type}", "outputs/reports")
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path

    def get_model_path(self, model_type: str) -> Path:
        """Get model directory path."""
        model_path = self.get(f"{model_type}_detection.detectors.{model_type.split('_')[0]}.model_path")
        if model_path:
            return self.project_root / model_path
        return self.project_root / "models" / model_type

    @property
    def openai_api_key(self) -> Optional[str]:
        """Get OpenAI API key."""
        return self.get("text_detection.detectors.openai.api_key") or os.getenv("OPENAI_API_KEY")

    @property
    def project_root_path(self) -> Path:
        """Get project root directory."""
        return self.project_root

    def to_dict(self) -> Dict[str, Any]:
        """Return configuration as dictionary."""
        return self._config.copy()


# Global config instance
_config_instance: Optional[Config] = None


def get_config(config_path: Optional[str] = None) -> Config:
    """
    Get or create global configuration instance.

    Args:
        config_path: Path to config file. Only used on first call.

    Returns:
        Config instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = Config(config_path)
    return _config_instance


def reset_config():
    """Reset global config instance (mainly for testing)."""
    global _config_instance
    _config_instance = None
