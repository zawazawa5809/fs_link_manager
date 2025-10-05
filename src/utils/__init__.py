"""Utility modules for FS Link Manager"""

from .error_handler import (
    handle_errors, ErrorReporter, AppError,
    DatabaseError, FileOperationError, ValidationError
)
from .auto_tagger import generate_auto_tags, merge_tags

__all__ = [
    'handle_errors', 'ErrorReporter', 'AppError',
    'DatabaseError', 'FileOperationError', 'ValidationError',
    'generate_auto_tags', 'merge_tags'
]
