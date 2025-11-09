"""
Staff domain logic.

Handles staff name resolution (ID → Name + Role).
"""

from .resolver import StaffResolver

__all__ = [
    'StaffResolver'
]
