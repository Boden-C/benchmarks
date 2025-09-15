"""
LLM-specific exception hierarchy.

Provides typed exceptions for different LLM provider error scenarios.
"""


class LLMProviderError(Exception):
    """Base exception for all LLM provider errors."""
    pass


class LLMAuthenticationError(LLMProviderError):
    """Authentication and API key errors."""
    pass


class LLMAPIError(LLMProviderError):
    """API communication and network errors."""
    pass


class ContentFilterError(LLMProviderError):
    """Content safety and filter violations."""
    pass


class TokenLimitError(LLMProviderError):
    """Token limit exceeded errors."""
    
    def __init__(self, message: str, requested: int = 0, max_tokens: int = 0):
        super().__init__(message)
        self.requested = requested
        self.max_tokens = max_tokens


class InvalidResponseError(LLMProviderError):
    """Malformed or invalid response errors."""
    pass
