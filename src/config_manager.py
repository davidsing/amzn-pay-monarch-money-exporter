"""
Configuration management for ADP Paystub to Monarch Money CSV Exporter.

This module handles loading and validating configuration files including
settings.json and category_mappings.json.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/paystub_processor.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when there's an error in configuration."""
    pass


class ConfigManager:
    """Manages loading and validation of configuration files."""

    def __init__(self, config_dir: str = "config"):
        """
        Initialize ConfigManager.

        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = Path(config_dir)
        self.settings = None
        self.category_mappings = None

    def load_settings(self) -> Dict[str, Any]:
        """
        Load and validate settings.json.

        Returns:
            Dictionary containing settings

        Raises:
            ConfigurationError: If settings file is invalid
        """
        settings_path = self.config_dir / "settings.json"

        if not settings_path.exists():
            raise ConfigurationError(f"Settings file not found: {settings_path}")

        try:
            with open(settings_path, 'r') as f:
                self.settings = json.load(f)

            self._validate_settings()
            logger.info("Settings loaded successfully")
            return self.settings

        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON in settings file: {e}")
        except Exception as e:
            raise ConfigurationError(f"Error loading settings: {e}")

    def load_category_mappings(self) -> Dict[str, Any]:
        """
        Load and validate category_mappings.json.

        Returns:
            Dictionary containing category mappings

        Raises:
            ConfigurationError: If category mappings file is invalid
        """
        mappings_path = self.config_dir / "category_mappings.json"

        if not mappings_path.exists():
            raise ConfigurationError(f"Category mappings file not found: {mappings_path}")

        try:
            with open(mappings_path, 'r') as f:
                self.category_mappings = json.load(f)

            self._validate_category_mappings()
            logger.info("Category mappings loaded successfully")
            return self.category_mappings

        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON in category mappings file: {e}")
        except Exception as e:
            raise ConfigurationError(f"Error loading category mappings: {e}")

    def _validate_settings(self):
        """Validate settings configuration."""
        required_sections = ["output", "processing", "file_handling", "validation", "monarch_money"]

        for section in required_sections:
            if section not in self.settings:
                raise ConfigurationError(f"Missing required section in settings: {section}")

        # Validate Monarch Money column configuration
        monarch_config = self.settings["monarch_money"]
        expected_columns = monarch_config.get("expected_columns", 9)
        column_order = monarch_config.get("column_order", [])

        if len(column_order) != expected_columns:
            raise ConfigurationError(
                f"Column order length ({len(column_order)}) doesn't match expected columns ({expected_columns})"
            )

        logger.debug("Settings validation passed")

    def _validate_category_mappings(self):
        """Validate category mappings configuration."""
        required_sections = ["earnings", "deductions", "field_mappings"]

        for section in required_sections:
            if section not in self.category_mappings:
                raise ConfigurationError(f"Missing required section in category mappings: {section}")

        # Validate field mappings have both earnings and deduction patterns
        field_mappings = self.category_mappings["field_mappings"]
        if "earnings_patterns" not in field_mappings:
            raise ConfigurationError("Missing earnings_patterns in field_mappings")
        if "deduction_patterns" not in field_mappings:
            raise ConfigurationError("Missing deduction_patterns in field_mappings")

        logger.debug("Category mappings validation passed")

    def get_setting(self, path: str, default: Any = None) -> Any:
        """
        Get a setting value using dot notation.

        Args:
            path: Dot-separated path to setting (e.g., "output.csv_format")
            default: Default value if setting not found

        Returns:
            Setting value or default
        """
        if not self.settings:
            self.load_settings()

        keys = path.split('.')
        value = self.settings

        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default

    def get_category_mapping(self, category_type: str, item_key: str) -> Optional[Dict[str, str]]:
        """
        Get category mapping for a specific item.

        Args:
            category_type: Type of category (earnings, deductions, etc.)
            item_key: Key for the specific item

        Returns:
            Dictionary with category and description or None
        """
        if not self.category_mappings:
            self.load_category_mappings()

        try:
            return self.category_mappings[category_type][item_key]
        except KeyError:
            logger.warning(f"No category mapping found for {category_type}.{item_key}")
            return None

    def get_earnings_pattern(self, pattern_key: str) -> Optional[list]:
        """Get earnings pattern list for matching PDF text."""
        if not self.category_mappings:
            self.load_category_mappings()

        try:
            return self.category_mappings["field_mappings"]["earnings_patterns"][pattern_key]
        except KeyError:
            return None

    def get_deduction_pattern(self, pattern_key: str) -> Optional[list]:
        """Get deduction pattern list for matching PDF text."""
        if not self.category_mappings:
            self.load_category_mappings()

        try:
            return self.category_mappings["field_mappings"]["deduction_patterns"][pattern_key]
        except KeyError:
            return None

    def setup_logging(self):
        """Setup logging based on configuration."""
        if not self.settings:
            self.load_settings()

        log_config = self.settings.get("logging", {})
        log_level = getattr(logging, log_config.get("level", "INFO"))
        log_file = log_config.get("log_file", "logs/paystub_processor.log")

        # Ensure log directory exists
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)

        # Configure root logger
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ],
            force=True
        )

        logger.info(f"Logging configured: level={log_config.get('level', 'INFO')}, file={log_file}")


def get_config_manager() -> ConfigManager:
    """Get a configured ConfigManager instance."""
    return ConfigManager()


if __name__ == "__main__":
    # Test configuration loading
    config = ConfigManager()
    try:
        settings = config.load_settings()
        mappings = config.load_category_mappings()
        config.setup_logging()
        print("Configuration loaded successfully!")
        print(f"Monarch Money format: {config.get_setting('output.csv_format')}")
        print(f"Expected columns: {config.get_setting('monarch_money.expected_columns')}")
    except ConfigurationError as e:
        print(f"Configuration error: {e}")