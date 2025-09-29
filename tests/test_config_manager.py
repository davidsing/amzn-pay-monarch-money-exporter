"""Tests for config_manager module."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open

from src.config_manager import ConfigManager, ConfigurationError


class TestConfigManager:
    """Test cases for ConfigManager class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config_manager = ConfigManager()

    def test_init(self):
        """Test ConfigManager initialization."""
        assert self.config_manager.config_dir == Path("config")
        assert self.config_manager.settings is None
        assert self.config_manager.category_mappings is None

    def test_init_custom_dir(self):
        """Test ConfigManager with custom config directory."""
        config_manager = ConfigManager("custom_config")
        assert config_manager.config_dir == Path("custom_config")

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_load_settings_success(self, mock_file, mock_exists):
        """Test successful settings loading."""
        mock_exists.return_value = True
        mock_settings = {
            "output": {"csv_format": "monarch_money"},
            "processing": {"pdf_parser": "pdfplumber"},
            "file_handling": {"input_directory": "./data"},
            "validation": {"verify_gross_net_balance": True},
            "monarch_money": {
                "expected_columns": 9,
                "column_order": ["date", "description", "original_description",
                               "amount", "transaction_type", "category",
                               "account_name", "labels", "notes"]
            }
        }
        mock_file.return_value.read.return_value = json.dumps(mock_settings)

        result = self.config_manager.load_settings()

        assert result == mock_settings
        assert self.config_manager.settings == mock_settings

    @patch("pathlib.Path.exists")
    def test_load_settings_file_not_found(self, mock_exists):
        """Test settings loading when file doesn't exist."""
        mock_exists.return_value = False

        with pytest.raises(ConfigurationError, match="Settings file not found"):
            self.config_manager.load_settings()

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_load_settings_invalid_json(self, mock_file, mock_exists):
        """Test settings loading with invalid JSON."""
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = "invalid json"

        with pytest.raises(ConfigurationError, match="Invalid JSON in settings file"):
            self.config_manager.load_settings()

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_load_category_mappings_success(self, mock_file, mock_exists):
        """Test successful category mappings loading."""
        mock_exists.return_value = True
        mock_mappings = {
            "earnings": {"regular": {"category": "Income:Salary"}},
            "deductions": {"federal_income_tax": {"category": "Taxes:Federal"}},
            "field_mappings": {
                "earnings_patterns": {"regular": ["Regular"]},
                "deduction_patterns": {"federal_income_tax": ["Federal Income Tax"]}
            }
        }
        mock_file.return_value.read.return_value = json.dumps(mock_mappings)

        result = self.config_manager.load_category_mappings()

        assert result == mock_mappings
        assert self.config_manager.category_mappings == mock_mappings

    def test_validate_settings_missing_section(self):
        """Test settings validation with missing required section."""
        self.config_manager.settings = {
            "output": {"csv_format": "monarch_money"},
            # Missing other required sections
        }

        with pytest.raises(ConfigurationError, match="Missing required section"):
            self.config_manager._validate_settings()

    def test_validate_settings_column_mismatch(self):
        """Test settings validation with column count mismatch."""
        self.config_manager.settings = {
            "output": {"csv_format": "monarch_money"},
            "processing": {"pdf_parser": "pdfplumber"},
            "file_handling": {"input_directory": "./data"},
            "validation": {"verify_gross_net_balance": True},
            "monarch_money": {
                "expected_columns": 9,
                "column_order": ["date", "description"]  # Only 2 columns
            }
        }

        with pytest.raises(ConfigurationError, match="Column order length"):
            self.config_manager._validate_settings()

    def test_get_setting_with_loaded_settings(self):
        """Test getting setting value with dot notation."""
        self.config_manager.settings = {
            "output": {
                "csv_format": "monarch_money",
                "date_format": "YYYY-MM-DD"
            }
        }

        assert self.config_manager.get_setting("output.csv_format") == "monarch_money"
        assert self.config_manager.get_setting("output.date_format") == "YYYY-MM-DD"
        assert self.config_manager.get_setting("nonexistent.key", "default") == "default"

    @patch.object(ConfigManager, 'load_settings')
    def test_get_setting_auto_load(self, mock_load):
        """Test that get_setting auto-loads settings if not loaded."""
        self.config_manager.settings = None  # Ensure settings not loaded
        mock_load.return_value = {"test": {"value": "loaded"}}

        # Mock the settings attribute after load_settings is called
        def side_effect():
            self.config_manager.settings = {"test": {"value": "loaded"}}
            return {"test": {"value": "loaded"}}

        mock_load.side_effect = side_effect

        result = self.config_manager.get_setting("test.value")

        mock_load.assert_called_once()
        assert result == "loaded"

    def test_get_category_mapping(self):
        """Test getting category mapping."""
        self.config_manager.category_mappings = {
            "earnings": {
                "regular": {
                    "category": "Income:Salary",
                    "description": "Regular salary income"
                }
            }
        }

        result = self.config_manager.get_category_mapping("earnings", "regular")

        assert result == {
            "category": "Income:Salary",
            "description": "Regular salary income"
        }

    def test_get_category_mapping_not_found(self):
        """Test getting non-existent category mapping."""
        self.config_manager.category_mappings = {"earnings": {}}

        result = self.config_manager.get_category_mapping("earnings", "nonexistent")

        assert result is None

    def test_get_earnings_pattern(self):
        """Test getting earnings pattern."""
        self.config_manager.category_mappings = {
            "field_mappings": {
                "earnings_patterns": {
                    "regular": ["Regular", "Base Pay"]
                }
            }
        }

        result = self.config_manager.get_earnings_pattern("regular")

        assert result == ["Regular", "Base Pay"]

    def test_get_deduction_pattern(self):
        """Test getting deduction pattern."""
        self.config_manager.category_mappings = {
            "field_mappings": {
                "deduction_patterns": {
                    "federal_tax": ["Federal Income Tax", "Fed Tax"]
                }
            }
        }

        result = self.config_manager.get_deduction_pattern("federal_tax")

        assert result == ["Federal Income Tax", "Fed Tax"]


def test_get_config_manager():
    """Test factory function for ConfigManager."""
    config_manager = ConfigManager()
    assert isinstance(config_manager, ConfigManager)