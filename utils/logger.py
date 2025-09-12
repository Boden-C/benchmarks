"""
Logging utilities for the benchmark library.

Centralized logging configuration and utilities.
"""

import logging
import traceback
from typing import Optional, Any

logger = logging.getLogger(__name__)


class BenchmarkError(Exception):
    """Base exception for benchmark library errors."""
    pass


class ConfigurationError(BenchmarkError):
    """Configuration-related error."""
    pass


class ExecutionError(BenchmarkError):
    """Task execution error."""
    pass


class EvaluationError(BenchmarkError):
    """Result evaluation error."""
    pass


def handle_error(
    error: Exception,
    context: str,
    reraise: bool = True,
    default_value: Optional[Any] = None
) -> Optional[Any]:
    """
    Handle error with logging and optional re-raising.
    
    Args:
        error: Exception that occurred
        context: Context description for logging
        reraise: Whether to re-raise the exception
        default_value: Value to return if not re-raising
    
    Returns:
        default_value if not re-raising
    
    Raises:
        Exception: If reraise is True
    """
    log_error(error, context)
    
    if reraise:
        raise
    
    return default_value


def log_error(error: Exception, context: str) -> None:
    """
    Log error with context and traceback.
    
    Args:
        error: Exception that occurred
        context: Context description
    """
    error_type = type(error).__name__
    error_msg = str(error)
    trace = traceback.format_exc()
    
    logger.error(
        f"Error in {context}: {error_type} - {error_msg}\n"
        f"Traceback:\n{trace}"
    )
