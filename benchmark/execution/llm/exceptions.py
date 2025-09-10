"""Custom exceptions for LLM providers."""

class LLMProviderError(Exception):
    """Base exception for LLM provider errors."""
    pass

class LLMAuthenticationError(LLMProviderError):
    """Raised for authentication failures with the LLM API."""
    pass

class LLMAPIError(LLMProviderError):
    """Raised for general API errors (e.g., server errors, rate limits)."""
    pass

class ContentFilterError(LLMProviderError):
    """Raised when a response is blocked by content filters."""
    pass
