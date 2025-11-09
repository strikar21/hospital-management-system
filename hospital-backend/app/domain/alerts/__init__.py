"""
Alerts domain logic.

Handles alert generation, deduplication, and processing pipeline.
"""

from .pipeline import AlertPipeline
from .deduplicator import AlertDeduplicator

__all__ = [
    'AlertPipeline',
    'AlertDeduplicator'
]
