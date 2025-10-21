"""
Custom validators for landlord app models
"""
from django.core.exceptions import ValidationError


def validate_country_whitelist(value):
    """
    Validate that country is one of the whitelisted values: DE, AT, CH

    Args:
        value: Country code to validate

    Raises:
        ValidationError: If country is not in whitelist
    """
    ALLOWED_COUNTRIES = ['DE', 'AT', 'CH']

    if value not in ALLOWED_COUNTRIES:
        raise ValidationError(
            f"Country '{value}' is not allowed. Must be one of: {', '.join(ALLOWED_COUNTRIES)}",
            code='invalid_country'
        )


def validate_postal_code_de(value):
    """
    Validate German postal code format (5 digits)

    Args:
        value: Postal code to validate

    Raises:
        ValidationError: If postal code is not 5 digits
    """
    if not value.isdigit() or len(value) != 5:
        raise ValidationError(
            'German postal code must be exactly 5 digits',
            code='invalid_postal_code_de'
        )


def validate_serial_number_format(value):
    """
    Validate meter serial number format (alphanumeric + dash/slash)

    Args:
        value: Serial number to validate

    Raises:
        ValidationError: If serial number contains invalid characters
    """
    # Allow empty strings (blank=True on model field)
    if not value:
        return

    import re

    # Allow: A-Z, a-z, 0-9, dash (-), slash (/)
    pattern = r'^[A-Za-z0-9\-/]+$'

    if not re.match(pattern, value):
        raise ValidationError(
            'Serial number can only contain letters, numbers, dashes, and slashes',
            code='invalid_serial_number'
        )
