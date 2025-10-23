"""
Tests for custom validators
Coverage Target: 95%+ (from 73%)
"""
from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError
from landlord.validators import (
    validate_country_whitelist,
    validate_postal_code_de,
    validate_serial_number_format,
)


class TestCountryWhitelist:
    """Test country whitelist validator."""

    def test_valid_countries(self):
        """Valid countries (DE, AT, CH) pass validation."""
        validate_country_whitelist('DE')  # Should not raise
        validate_country_whitelist('AT')  # Should not raise
        validate_country_whitelist('CH')  # Should not raise

    def test_invalid_country_raises(self):
        """Invalid country raises ValidationError."""
        with pytest.raises(ValidationError, match="not allowed"):
            validate_country_whitelist('US')
        
        with pytest.raises(ValidationError, match="not allowed"):
            validate_country_whitelist('FR')

    def test_invalid_country_error_code(self):
        """ValidationError has correct error code."""
        with pytest.raises(ValidationError) as exc_info:
            validate_country_whitelist('GB')
        
        assert exc_info.value.code == 'invalid_country'

    def test_case_sensitive(self):
        """Validator is case-sensitive."""
        with pytest.raises(ValidationError):
            validate_country_whitelist('de')  # lowercase fails
        
        with pytest.raises(ValidationError):
            validate_country_whitelist('De')  # mixed case fails


class TestPostalCodeDE:
    """Test German postal code validator."""

    def test_valid_postal_codes(self):
        """Valid 5-digit postal codes pass."""
        validate_postal_code_de('12345')
        validate_postal_code_de('00000')
        validate_postal_code_de('99999')

    def test_invalid_length_raises(self):
        """Non-5-digit codes raise ValidationError."""
        with pytest.raises(ValidationError, match="5 digits"):
            validate_postal_code_de('1234')  # Too short
        
        with pytest.raises(ValidationError, match="5 digits"):
            validate_postal_code_de('123456')  # Too long

    def test_non_numeric_raises(self):
        """Non-numeric codes raise ValidationError."""
        with pytest.raises(ValidationError, match="5 digits"):
            validate_postal_code_de('1234A')
        
        with pytest.raises(ValidationError, match="5 digits"):
            validate_postal_code_de('ABCDE')

    def test_error_code(self):
        """ValidationError has correct error code."""
        with pytest.raises(ValidationError) as exc_info:
            validate_postal_code_de('ABC')
        
        assert exc_info.value.code == 'invalid_postal_code_de'


class TestSerialNumberFormat:
    """Test meter serial number validator."""

    def test_valid_serial_numbers(self):
        """Valid alphanumeric + dash/slash formats pass."""
        validate_serial_number_format('ABC123')
        validate_serial_number_format('ABC-123')
        validate_serial_number_format('ABC/123')
        validate_serial_number_format('ABC-123/456')
        validate_serial_number_format('a1b2c3')  # lowercase OK
        validate_serial_number_format('123456789')  # numbers only OK

    def test_empty_string_allowed(self):
        """Empty string is allowed (for blank=True fields)."""
        validate_serial_number_format('')  # Should not raise
        validate_serial_number_format(None)  # Should not raise

    def test_invalid_characters_raise(self):
        """Invalid characters raise ValidationError."""
        with pytest.raises(ValidationError, match="letters, numbers, dashes, and slashes"):
            validate_serial_number_format('ABC 123')  # Space not allowed
        
        with pytest.raises(ValidationError, match="letters, numbers, dashes, and slashes"):
            validate_serial_number_format('ABC#123')  # Hash not allowed
        
        with pytest.raises(ValidationError, match="letters, numbers, dashes, and slashes"):
            validate_serial_number_format('ABC.123')  # Dot not allowed

    def test_error_code(self):
        """ValidationError has correct error code."""
        with pytest.raises(ValidationError) as exc_info:
            validate_serial_number_format('ABC*123')
        
        assert exc_info.value.code == 'invalid_serial_number'

    def test_unicode_not_allowed(self):
        """Unicode characters raise ValidationError."""
        with pytest.raises(ValidationError):
            validate_serial_number_format('ABC€123')
        
        with pytest.raises(ValidationError):
            validate_serial_number_format('ABCä123')
