"""
CSV Security Utilities
Security Fix (2025-10-23): Prevent CSV injection attacks.

When exporting data to CSV, malicious formulas (starting with =, +, -, @)
can be executed by Excel/LibreOffice when opening the file.

Example Attack:
  =cmd|'/c calc'!A1  (opens calculator on Windows)
  =IMPORTXML(...)    (exfiltrates data)

Solution: Prefix dangerous characters with single quote (') to neutralize.
"""
from __future__ import annotations


def sanitize_csv_value(value: str | None) -> str:
    """
    Sanitize a value for safe CSV export.

    Prevents CSV injection by prefixing formulas with single quote.
    Excel/LibreOffice will treat it as text, not executable code.

    Args:
        value: String value to sanitize (can be None)

    Returns:
        Sanitized string safe for CSV export

    Examples:
        >>> sanitize_csv_value("=SUM(A1:A10)")
        "'=SUM(A1:A10)"

        >>> sanitize_csv_value("Normal text")
        "Normal text"

        >>> sanitize_csv_value(None)
        ""
    """
    if value is None:
        return ""

    # Convert to string if not already
    value = str(value)

    if not value:
        return ""

    # Dangerous characters that can start formulas
    # Note: Tab/CR at start are dangerous but strip() would remove them
    # Check BEFORE stripping to catch leading whitespace attacks
    FORMULA_CHARS = {'=', '+', '-', '@', '\t', '\r'}

    # Check first character (before strip!)
    if value[0] in FORMULA_CHARS:
        # Prefix with single quote to neutralize
        return f"'{value}"

    # Now safe to strip for normal values
    return value.strip()


def sanitize_csv_row(row: dict[str, any]) -> dict[str, str]:
    """
    Sanitize all values in a CSV row dictionary.

    Args:
        row: Dictionary of column_name -> value

    Returns:
        Dictionary with all values sanitized

    Example:
        >>> sanitize_csv_row({"name": "Alice", "formula": "=1+1"})
        {"name": "Alice", "formula": "'=1+1"}
    """
    return {key: sanitize_csv_value(value) for key, value in row.items()}
