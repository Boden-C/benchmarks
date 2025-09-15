"""
OpenRouter provider implementation.

Creates LLM providers for OpenRouter API.
"""

import logging

from benchmark.models import ModelConfig
from benchmark.execution.llm.provider import LLMProvider

logger = logging.getLogger(__name__)


async def create_openrouter_provider(model_config: ModelConfig) -> LLMProvider:
    """
    Create OpenRouter provider.
    
    Args:
        model_config: Model configuration
    
    Returns:
        Configured LLMProvider instance
    
    Raises:
        ValueError: If configuration is invalid
    """
    try:
        from openai import AsyncOpenAI
    except ImportError:
        raise ImportError("openai package required. Install with: pip install openai")
    
    api_key = model_config.api_key or model_config.config.get("api_key")
    if not api_key:
        raise ValueError("OpenRouter API key required")
    
    base_url = model_config.base_url or "https://openrouter.ai/api/v1"
    
    client = AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
    )
    
    logger.debug(f"Created OpenRouter client for {model_config.name}")
    
    return LLMProvider(
        client=client,
        deployment_name=model_config.name,
        provider_type="openrouter",
    )
