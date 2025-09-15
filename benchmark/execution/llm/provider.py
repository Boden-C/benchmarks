"""
Universal LLM provider abstraction with error handling.

Provides a unified interface for calling various LLM providers with
automatic retry logic and comprehensive error handling.
"""

import asyncio
import json
import logging
import re
from typing import Union, Optional, Any

from benchmark.execution.llm.exceptions import (
    LLMProviderError,
    LLMAuthenticationError,
    LLMAPIError,
    ContentFilterError,
    TokenLimitError,
    InvalidResponseError,
)

logger = logging.getLogger(__name__)

# Models using max_completion_tokens instead of max_tokens
MODELS_WITH_MAX_COMPLETION_TOKENS = {
    "o1", "o1-preview", "o1-mini",
    "o3", "o3-mini",
    "o4", "o4-mini",
    "gpt-5", "gpt-5-mini",
}


class LLMProvider:
    """Universal LLM provider abstraction."""
    
    def __init__(
        self,
        client: Any,
        deployment_name: str,
        provider_type: str = "azure"
    ) -> None:
        """
        Initialize LLM provider.
        
        Args:
            client: Provider-specific client instance
            deployment_name: Model deployment name
            provider_type: Provider identifier (azure, openrouter, openai)
        """
        self.client = client
        self.deployment_name = deployment_name
        self.provider_type = provider_type
        logger.debug(f"Initialized {provider_type} provider for {deployment_name}")
    
    async def get_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        return_usage: bool = False,
        temperature: float = 0.7,
        **kwargs
    ) -> Union[str, tuple[str, dict[str, int]]]:
        """
        Get completion from LLM with retry logic.
        
        Args:
            system_prompt: System message content
            user_prompt: User message content
            max_tokens: Maximum tokens in response
            return_usage: Whether to return token usage
            temperature: Sampling temperature
            **kwargs: Additional provider-specific parameters
        
        Returns:
            Completion text, or (text, usage_dict) if return_usage=True
        
        Raises:
            TokenLimitError: If token limit exceeded
            ContentFilterError: If content filtered
            LLMAuthenticationError: If authentication fails
            LLMAPIError: For other API errors
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": user_prompt})
        
        # Determine token parameter name based on model
        token_param = "max_completion_tokens" if any(
            model in self.deployment_name.lower()
            for model in MODELS_WITH_MAX_COMPLETION_TOKENS
        ) else "max_tokens"
        
        params = {
            "messages": messages,
            token_param: max_tokens,
            "temperature": temperature,
            **kwargs
        }
        
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                # Make API call
                if self.provider_type == "azure":
                    response = await self.client.chat.completions.create(
                        model=self.deployment_name,
                        **params
                    )
                elif self.provider_type in ("openrouter", "openai"):
                    response = await self.client.chat.completions.create(
                        model=self.deployment_name,
                        **params
                    )
                else:
                    raise LLMProviderError(f"Unknown provider type: {self.provider_type}")
                
                # Extract response
                content = response.choices[0].message.content or ""
                
                if return_usage:
                    usage = {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens,
                    }
                    return content, usage
                
                return content
                
            except Exception as e:
                error_msg = str(e).lower()
                
                # Check for authentication errors
                if any(term in error_msg for term in ["unauthorized", "invalid_api_key", "authentication"]):
                    logger.error(f"Authentication error: {e}")
                    raise LLMAuthenticationError(f"Authentication failed: {e}")
                
                # Check for token limit errors
                if self._is_token_limit_error(error_msg):
                    requested, max_allowed = self._extract_requested_tokens(str(e))
                    logger.warning(f"Token limit exceeded: {requested}/{max_allowed}")
                    raise TokenLimitError(
                        f"Token limit exceeded: {e}",
                        requested=requested or 0,
                        max_tokens=max_allowed or 0
                    )
                
                # Check for content filter errors
                if self._is_content_filter_error(error_msg):
                    logger.warning(f"Content filter triggered: {e}")
                    raise ContentFilterError(f"Content filtered: {e}")
                
                # Retry on transient errors
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    logger.warning(f"API call failed (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"API call failed after {max_retries} attempts: {e}")
                    raise LLMAPIError(f"API call failed: {e}")
    
    def _is_token_limit_error(self, error_message: str) -> bool:
        """
        Check if error is token limit related.
        
        Args:
            error_message: Error message (lowercased)
        
        Returns:
            True if token limit error
        """
        patterns = [
            "token limit",
            "context length",
            "maximum context",
            "too many tokens",
            "exceeds token limit",
        ]
        return any(pattern in error_message for pattern in patterns)
    
    def _is_content_filter_error(self, error_message: str) -> bool:
        """
        Check if error is content filter related.
        
        Args:
            error_message: Error message (lowercased)
        
        Returns:
            True if content filter error
        """
        patterns = [
            "content_filter",
            "content filter",
            "safety",
            "policy violation",
            "inappropriate content",
        ]
        return any(pattern in error_message for pattern in patterns)
    
    def _extract_requested_tokens(self, error_message: str) -> tuple[Optional[int], Optional[int]]:
        """
        Extract token counts from error message.
        
        Args:
            error_message: Full error message
        
        Returns:
            Tuple of (requested_tokens, max_tokens) or (None, None)
        """
        # Try to find patterns like "requested: 12345, limit: 8192"
        patterns = [
            r"requested[:\s]+(\d+).*?(?:limit|maximum)[:\s]+(\d+)",
            r"(\d+).*?(?:exceeds|over).*?(\d+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, error_message, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1)), int(match.group(2))
                except (ValueError, IndexError):
                    pass
        
        return None, None
    
    def clean_and_parse_json(self, raw_json: str) -> Any:
        """
        Parse JSON with automatic cleaning.
        
        Args:
            raw_json: Raw JSON string (possibly wrapped in markdown)
        
        Returns:
            Parsed JSON object
        
        Raises:
            InvalidResponseError: If parsing fails
        """
        # Try standard parsing first
        try:
            return json.loads(raw_json)
        except json.JSONDecodeError:
            pass
        
        # Remove markdown code blocks
        cleaned = raw_json.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines)
        
        # Try parsing cleaned version
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            raise InvalidResponseError(f"Invalid JSON response: {e}")
