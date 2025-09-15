"""
Model configuration and provider factory.

Centralized model registry and factory for creating configured LLM providers.
"""

import os
import logging
from typing import Any

from benchmark.models import ModelConfig
from benchmark.execution.llm.provider import LLMProvider
from benchmark.execution.llm.providers.openai import create_openai_provider
from benchmark.execution.llm.providers.openrouter import create_openrouter_provider

logger = logging.getLogger(__name__)


class LLMFactory:
    """Factory for creating LLM providers."""
    
    @staticmethod
    def get_model_configs() -> dict[str, ModelConfig]:
        """
        Get comprehensive model registry.
        
        Returns:
            Dictionary mapping model names to configurations
        """
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        azure_key = os.getenv("AZURE_OPENAI_API_KEY", "")
        openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
        
        configs = {
            # Azure OpenAI models
            "gpt-4o": ModelConfig(
                name="gpt-4o",
                provider="azure",
                api_key=azure_key,
                base_url=azure_endpoint,
            ),
            "gpt-4o-mini": ModelConfig(
                name="gpt-4o-mini",
                provider="azure",
                api_key=azure_key,
                base_url=azure_endpoint,
            ),
            "o1": ModelConfig(
                name="o1",
                provider="azure",
                api_key=azure_key,
                base_url=azure_endpoint,
            ),
            "o1-mini": ModelConfig(
                name="o1-mini",
                provider="azure",
                api_key=azure_key,
                base_url=azure_endpoint,
            ),
            "o4-mini": ModelConfig(
                name="o4-mini",
                provider="azure",
                api_key=azure_key,
                base_url=azure_endpoint,
            ),
            
            # OpenRouter models
            "claude-sonnet-4": ModelConfig(
                name="anthropic/claude-sonnet-4",
                provider="openrouter",
                api_key=openrouter_key,
            ),
            "claude-opus-4": ModelConfig(
                name="anthropic/claude-opus-4",
                provider="openrouter",
                api_key=openrouter_key,
            ),
            "gemini-2.0-flash-exp": ModelConfig(
                name="google/gemini-2.0-flash-exp:free",
                provider="openrouter",
                api_key=openrouter_key,
            ),
            "gemini-pro-1.5": ModelConfig(
                name="google/gemini-pro-1.5",
                provider="openrouter",
                api_key=openrouter_key,
            ),
            "deepseek-chat": ModelConfig(
                name="deepseek/deepseek-chat",
                provider="openrouter",
                api_key=openrouter_key,
            ),
            "qwen-2.5-72b": ModelConfig(
                name="qwen/qwen-2.5-72b-instruct",
                provider="openrouter",
                api_key=openrouter_key,
            ),
        }
        
        # Add custom models from environment
        for key, value in os.environ.items():
            if key.startswith("CUSTOM_MODEL_"):
                model_name = key[13:].lower().replace("_", "-")
                configs[model_name] = ModelConfig(
                    name=model_name,
                    provider="custom",
                    api_key=os.getenv(f"{key}_API_KEY", ""),
                    base_url=os.getenv(f"{key}_BASE_URL", ""),
                )
        
        return configs
    
    @staticmethod
    async def create_llm_provider(model_config: ModelConfig) -> LLMProvider:
        """
        Factory method creating configured provider instances.
        
        Args:
            model_config: Model configuration
        
        Returns:
            Configured LLMProvider instance
        
        Raises:
            ValueError: If provider type unknown or configuration invalid
        """
        provider_type = model_config.provider.lower()
        
        logger.debug(f"Creating provider for {model_config.name} ({provider_type})")
        
        if provider_type == "azure":
            return await create_openai_provider(model_config, provider_type="azure")
        elif provider_type == "openai":
            return await create_openai_provider(model_config, provider_type="openai")
        elif provider_type == "openrouter":
            return await create_openrouter_provider(model_config)
        elif provider_type == "custom":
            # Use OpenAI-compatible client for custom endpoints
            return await create_openai_provider(model_config, provider_type="custom")
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")
