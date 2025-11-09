"""
Serialization utilities - camelCase ↔ snake_case transformation.

Provides single source of truth for all casing transformations.
Backend database uses camelCase (quoted identifiers), API uses camelCase.

Usage:
    from app.common.serialization import dict_to_camel_case

    response_data = dict_to_camel_case(db_row)
"""

from typing import Dict, Any, List, Union
import re
import logging

logger = logging.getLogger(__name__)


def to_camel_case(snake_str: str) -> str:
    """
    Convert snake_case string to camelCase.

    Args:
        snake_str: String in snake_case format

    Returns:
        String in camelCase format

    Example:
        >>> to_camel_case("patient_id")
        'patientId'
        >>> to_camel_case("first_name")
        'firstName'
    """
    if not snake_str:
        return snake_str

    components = snake_str.split('_')
    # Keep first component lowercase, capitalize rest
    return components[0] + ''.join(x.title() for x in components[1:])


def to_snake_case(camel_str: str) -> str:
    """
    Convert camelCase string to snake_case.

    Args:
        camel_str: String in camelCase format

    Returns:
        String in snake_case format

    Example:
        >>> to_snake_case("patientId")
        'patient_id'
        >>> to_snake_case("firstName")
        'first_name'
    """
    if not camel_str:
        return camel_str

    # Insert underscore before uppercase letters, then lowercase
    snake = re.sub('([A-Z])', r'_\1', camel_str).lower()
    # Remove leading underscore if present
    return snake.lstrip('_')


def dict_to_camel_case(data: Union[Dict, List, Any]) -> Union[Dict, List, Any]:
    """
    Recursively convert dictionary keys from snake_case to camelCase.

    Handles:
    - Nested dictionaries
    - Lists of dictionaries
    - Mixed data structures

    Args:
        data: Data structure to convert (dict, list, or primitive)

    Returns:
        Data structure with camelCase keys

    Example:
        >>> dict_to_camel_case({'patient_id': 'P001', 'first_name': 'John'})
        {'patientId': 'P001', 'firstName': 'John'}
    """
    if isinstance(data, dict):
        camel_dict = {}
        for key, value in data.items():
            # Convert key to camelCase
            camel_key = to_camel_case(key)

            # Recursively convert nested structures
            if isinstance(value, (dict, list)):
                camel_dict[camel_key] = dict_to_camel_case(value)
            else:
                camel_dict[camel_key] = value

        return camel_dict

    elif isinstance(data, list):
        return [dict_to_camel_case(item) for item in data]

    else:
        # Primitive type - return as-is
        return data


def dict_to_snake_case(data: Union[Dict, List, Any]) -> Union[Dict, List, Any]:
    """
    Recursively convert dictionary keys from camelCase to snake_case.

    Args:
        data: Data structure to convert (dict, list, or primitive)

    Returns:
        Data structure with snake_case keys

    Example:
        >>> dict_to_snake_case({'patientId': 'P001', 'firstName': 'John'})
        {'patient_id': 'P001', 'first_name': 'John'}
    """
    if isinstance(data, dict):
        snake_dict = {}
        for key, value in data.items():
            # Convert key to snake_case
            snake_key = to_snake_case(key)

            # Recursively convert nested structures
            if isinstance(value, (dict, list)):
                snake_dict[snake_key] = dict_to_snake_case(value)
            else:
                snake_dict[snake_key] = value

        return snake_dict

    elif isinstance(data, list):
        return [dict_to_snake_case(item) for item in data]

    else:
        # Primitive type - return as-is
        return data


def clean_none_values(data: Dict[str, Any], recursive: bool = True) -> Dict[str, Any]:
    """
    Remove keys with None values from dictionary.

    Args:
        data: Dictionary to clean
        recursive: If True, clean nested dictionaries

    Returns:
        Dictionary without None values

    Example:
        >>> clean_none_values({'a': 1, 'b': None, 'c': 3})
        {'a': 1, 'c': 3}
    """
    cleaned = {}

    for key, value in data.items():
        if value is None:
            continue

        if recursive and isinstance(value, dict):
            cleaned[key] = clean_none_values(value, recursive=True)
        elif recursive and isinstance(value, list):
            cleaned[key] = [
                clean_none_values(item, recursive=True) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            cleaned[key] = value

    return cleaned
