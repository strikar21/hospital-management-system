"""Unit conversions for vital signs."""


def celsius_to_fahrenheit(celsius: float) -> float:
    """
    Convert temperature from Celsius to Fahrenheit.

    Args:
        celsius: Temperature in Celsius

    Returns:
        Temperature in Fahrenheit

    Example:
        >>> celsius_to_fahrenheit(37.0)
        98.6
    """
    return (celsius * 9/5) + 32


def fahrenheit_to_celsius(fahrenheit: float) -> float:
    """
    Convert temperature from Fahrenheit to Celsius.

    Args:
        fahrenheit: Temperature in Fahrenheit

    Returns:
        Temperature in Celsius

    Example:
        >>> fahrenheit_to_celsius(98.6)
        37.0
    """
    return (fahrenheit - 32) * 5/9


def mmhg_to_kpa(mmhg: float) -> float:
    """
    Convert blood pressure from mmHg to kPa.

    Args:
        mmhg: Pressure in mmHg

    Returns:
        Pressure in kPa

    Example:
        >>> mmhg_to_kpa(120)
        16.0
    """
    return mmhg * 0.133322


def kpa_to_mmhg(kpa: float) -> float:
    """
    Convert blood pressure from kPa to mmHg.

    Args:
        kpa: Pressure in kPa

    Returns:
        Pressure in mmHg

    Example:
        >>> kpa_to_mmhg(16.0)
        120.0
    """
    return kpa / 0.133322
