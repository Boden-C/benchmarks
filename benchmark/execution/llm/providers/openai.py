"""
OpenAI and Azure OpenAI provider implementation.

Creates LLM providers for OpenAI and Azure OpenAI endpoints.
"""

import logging
from typing import Literal

from benchmark.models import ModelConfig
from benchmark.execution.llm.provider import LLMProvider

logger = logging.getLogger(__name__)


async def create_openai_provider(
    model_config: ModelConfig,
    provider_type: Literal["azure", "openai", "custom"] = "azure"
) -> LLMProvider:
    """
    Create OpenAI or Azure OpenAI provider.
    
    Args:
        model_config: Model configuration
        provider_type: Provider type (azure, openai, or custom)
    
    Returns:
        Configured LLMProvider instance
    
    Raises:
        ValueError: If configuration is invalid
    """
    try:
        from openai import AsyncAzureOpenAI, AsyncOpenAI
    except ImportError:
        raise ImportError("openai package required. Install with: pip install openai")
    
    api_key = model_config.api_key or model_config.config.get("api_key")
    if not api_key:
        raise ValueError(f"API key required for {provider_type} provider")
    
    if provider_type == "azure":
        base_url = model_config.base_url or model_config.config.get("base_url")
        if not base_url:
            raise ValueError("Azure endpoint URL required")
        
        api_version = model_config.config.get("api_version", "2024-08-01-preview")
        
        client = AsyncAzureOpenAI(
            api_key=api_key,
            azure_endpoint=base_url,
            api_version=api_version,
        )
        
        logger.debug(f"Created Azure OpenAI client for {model_config.name}")
        
    elif provider_type == "openai":
        client = AsyncOpenAI(
            api_key=api_key,
        )
        
        logger.debug(f"Created OpenAI client for {model_config.name}")
        
    else:  # custom
        base_url = model_config.base_url or model_config.config.get("base_url")
        if not base_url:
            raise ValueError("Base URL required for custom provider")
        
        client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        
        logger.debug(f"Created custom OpenAI-compatible client for {model_config.name}")
    
    return LLMProvider(
        client=client,
        deployment_name=model_config.name,
        provider_type=provider_type,
    )
