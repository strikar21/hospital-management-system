"""
Input sanitization utilities for Hospital Management System
Provides functions to clean and validate user inputs
"""

import re
from typing import Optional


def sanitize_string(value: Optional[str], max_length: int = 1000) -> Optional[str]:
    """
    Remove potentially dangerous characters and trim whitespace

    Args:
        value: Input string to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized string or None
    """
    if not value:
        return value

    # Remove control characters (except newline, carriage return, tab)
    value = ''.join(char for char in value if ord(char) >= 32 or char in '\n\r\t')

    # Trim whitespace
    value = value.strip()

    # Limit length
    if len(value) > max_length:
        value = value[:max_length]

    return value if value else None


def sanitize_id(value: str, pattern: str = r'^[A-Z]{3}[0-9]{4}$') -> str:
    """
    Validate ID format (e.g., DOC0001, PAT0001, NUR0001)

    Args:
        value: ID to validate
        pattern: Regex pattern for validation

    Returns:
        Validated ID

    Raises:
        ValueError: If ID doesn't match pattern
    """
    if not value:
        raise ValueError('ID cannot be empty')

    value = value.strip().upper()

    if not re.match(pattern, value):
        raise ValueError(f'Invalid ID format: {value}. Expected pattern: {pattern}')

    return value


def sanitize_phone(value: Optional[str]) -> Optional[str]:
    """
    Clean phone number format

    Args:
        value: Phone number to clean

    Returns:
        Cleaned phone number or None

    Raises:
        ValueError: If phone number is too short after cleaning
    """
    if not value:
        return value

    # Keep only digits and +
    cleaned = ''.join(c for c in value if c.isdigit() or c == '+')

    # Validate minimum length
    if cleaned and len(cleaned) < 10:
        raise ValueError(f'Phone number too short: {cleaned}. Minimum 10 digits required.')

    # Validate maximum length
    if cleaned and len(cleaned) > 15:
        raise ValueError(f'Phone number too long: {cleaned}. Maximum 15 digits allowed.')

    return cleaned if cleaned else None


def sanitize_email(value: Optional[str]) -> Optional[str]:
    """
    Basic email sanitization (Pydantic EmailStr does heavy lifting)

    Args:
        value: Email to sanitize

    Returns:
        Sanitized email or None
    """
    if not value:
        return value

    # Trim whitespace and lowercase
    value = value.strip().lower()

    return value if value else None


def validate_dosage_format(dosage: str) -> str:
    """
    Validate medication dosage format

    Args:
        dosage: Dosage string (e.g., "500mg", "10ml", "2 tablets")

    Returns:
        Validated dosage string

    Raises:
        ValueError: If dosage format is invalid
    """
    if not dosage:
        raise ValueError('Dosage cannot be empty')

    dosage = dosage.strip()

    # Check for negative sign (invalid)
    if '-' in dosage or dosage.startswith('−'):  # Check both hyphen and minus sign
        raise ValueError(f'Dosage must be positive: {dosage}')

    # Must contain at least one digit
    if not any(c.isdigit() for c in dosage):
        raise ValueError(f'Dosage must contain numeric value: {dosage}')

    # Extract numeric part (including decimal point)
    numeric_part = ''.join(c for c in dosage if c.isdigit() or c == '.')

    try:
        value = float(numeric_part)
        if value <= 0:
            raise ValueError(f'Dosage must be positive: {dosage}')
        if value > 100000:  # Sanity check
            raise ValueError(f'Dosage value too large: {dosage}')
    except ValueError as e:
        if 'positive' in str(e) or 'large' in str(e):
            raise
        raise ValueError(f'Invalid dosage format: {dosage}')

    return dosage


def validate_frequency_format(frequency: str) -> str:
    """
    Validate medication frequency format

    Args:
        frequency: Frequency string

    Returns:
        Validated frequency string

    Raises:
        ValueError: If frequency format is invalid
    """
    if not frequency:
        raise ValueError('Frequency cannot be empty')

    frequency = frequency.strip()

    # Common valid patterns
    valid_patterns = [
        r'^Once daily$',
        r'^Twice daily$',
        r'^TDS$',  # Three times daily
        r'^QDS$',  # Four times daily
        r'^PRN$',  # As needed
        r'^STAT$',  # Immediately
        r'^\d+ times? (daily|weekly|monthly)$',
        r'^Every \d+ hours?$',
        r'^Q\d+H$',  # Every X hours (medical notation)
    ]

    # Check if matches any valid pattern (case-insensitive)
    if any(re.match(pattern, frequency, re.IGNORECASE) for pattern in valid_patterns):
        return frequency

    # If doesn't match common patterns, still allow (but could log warning)
    # Some medications have unique frequencies
    if len(frequency) > 100:
        raise ValueError('Frequency too long (max 100 characters)')

    return frequency


def clean_whitespace(value: Optional[str]) -> Optional[str]:
    """
    Clean excessive whitespace from string

    Args:
        value: String to clean

    Returns:
        String with normalized whitespace
    """
    if not value:
        return value

    # Replace multiple spaces with single space
    value = ' '.join(value.split())

    return value if value else None
