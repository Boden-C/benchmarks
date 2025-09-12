"""
Configuration loading and management system.

Provides singleton configuration management with support for YAML loading,
environment variable overrides, and hierarchical configuration merging.
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Any, Optional
from pydantic import ValidationError

from benchmark.models import BenchmarkRunConfig, ModelConfig

logger = logging.getLogger(__name__)


class BenchmarkConfig:
    """Singleton configuration manager."""
    
    _instance: Optional["BenchmarkConfig"] = None
    _config: dict[str, Any] = {}
    
    def __new__(cls) -> "BenchmarkConfig":
        """Ensure single instance across application."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self) -> None:
        """Initialize configuration on first instantiation."""
        if not self._config:
            self._load_config()
    
    def _load_config(self) -> None:
        """Load YAML, apply environment overrides, validate structure."""
        self._config = self._get_default_config()
        self._apply_env_overrides()
        logger.debug("Configuration loaded and validated")
    
    def _get_default_config(self) -> dict[str, Any]:
        """Return comprehensive default configuration dictionary."""
        return {
            "execution": {
                "mcp_timeout": 30,
                "task_timeout": 300,
                "max_retries": 3,
                "default_port": 8000,
                "distraction_servers_count": 2,
                "retry_delay": 1,
                "task_delay": 0,
                "max_execution_rounds": 10,
                "compression_retries": 3,
                "server_semaphore_limit": 10,
                "content_summary_threshold": 10000,
                "content_truncate_length": 50000,
                "error_truncate_length": 1000,
                "sequential_only_tools": [],
            },
            "llm": {
                "planning_tokens": 16000,
                "summarization_max_tokens": 4000,
                "evaluation_max_tokens": 4000,
                "token_reduction_factors": [0.8, 0.6, 0.4],
                "azure_api_version": "2024-08-01-preview",
            },
            "benchmark": {
                "tasks_file": "tasks.jsonl",
                "all_task_files": [],
                "enable_judge_stability": False,
                "filter_problematic_tools": True,
                "concurrent_summarization": False,
                "use_fuzzy_descriptions": False,
                "concrete_description_ref": True,
            },
            "cache": {
                "enabled": False,
                "dir": ".cache/",
                "ttl": 86400,
                "max_size_mb": 1000,
                "key_strategy": "content_hash",
                "log_stats": True,
                "cleanup_interval": 3600,
                "server_whitelist": [],
            },
        }
    
    def _apply_env_overrides(self) -> None:
        """Process environment variables with BENCHMARK_ prefix."""
        for key, value in os.environ.items():
            if key.startswith("BENCHMARK_"):
                config_path = key[10:].lower().replace("_", ".")
                converted_value = self._convert_env_value(value)
                self._set_nested_value(self._config, config_path, converted_value)
                logger.debug(f"Applied env override: {config_path}={converted_value}")
    
    def _convert_env_value(self, value: str) -> Any:
        """Convert string env values to proper types."""
        # Boolean conversion
        if value.lower() in ("true", "yes", "1"):
            return True
        if value.lower() in ("false", "no", "0"):
            return False
        
        # Integer conversion
        try:
            return int(value)
        except ValueError:
            pass
        
        # Float conversion
        try:
            return float(value)
        except ValueError:
            pass
        
        # List conversion (comma-separated)
        if "," in value:
            return [item.strip() for item in value.split(",")]
        
        return value
    
    def _set_nested_value(self, config: dict, path: str, value: Any) -> None:
        """Update nested dict values using dot notation."""
        keys = path.split(".")
        current = config
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """Retrieve config value using dot notation."""
        keys = key_path.split(".")
        current = self._config
        
        for key in keys:
            if not isinstance(current, dict) or key not in current:
                return default
            current = current[key]
        
        return current
    
    def get_section(self, section: str) -> dict[str, Any]:
        """Return entire config section."""
        return self._config.get(section, {})
    
    def reload(self) -> None:
        """Reload configuration from disk and re-apply overrides."""
        self._config = {}
        self._load_config()


# Singleton instance
_config = BenchmarkConfig()


# Execution configuration getters
def get_mcp_timeout() -> int:
    """MCP server operation timeout (default: 30s)."""
    return _config.get("execution.mcp_timeout", 30)


def get_task_timeout() -> int:
    """Task execution timeout (default: 300s)."""
    return _config.get("execution.task_timeout", 300)


def get_max_retries() -> int:
    """Maximum retry attempts for failed operations (default: 3)."""
    return _config.get("execution.max_retries", 3)


def get_default_port() -> int:
    """Default MCP server port (default: 8000)."""
    return _config.get("execution.default_port", 8000)


def get_distraction_servers_count() -> int:
    """Number of distraction servers to add (default: 2)."""
    return _config.get("execution.distraction_servers_count", 2)


def get_retry_delay() -> int:
    """Delay between retry attempts in seconds (default: 1)."""
    return _config.get("execution.retry_delay", 1)


def get_task_delay() -> int:
    """Delay between tasks in seconds (default: 0)."""
    return _config.get("execution.task_delay", 0)


def get_max_execution_rounds() -> int:
    """Maximum agentic execution rounds (default: 10)."""
    return _config.get("execution.max_execution_rounds", 10)


def get_compression_retries() -> int:
    """Maximum information compression attempts (default: 3)."""
    return _config.get("execution.compression_retries", 3)


def get_server_semaphore_limit() -> int:
    """Concurrent server connection limit (default: 10)."""
    return _config.get("execution.server_semaphore_limit", 10)


def get_content_summary_threshold() -> int:
    """Content size threshold for summarization (default: 10000 chars)."""
    return _config.get("execution.content_summary_threshold", 10000)


def get_content_truncate_length() -> int:
    """Maximum content length before truncation (default: 50000 chars)."""
    return _config.get("execution.content_truncate_length", 50000)


def get_error_truncate_length() -> int:
    """Maximum error message length (default: 1000 chars)."""
    return _config.get("execution.error_truncate_length", 1000)


def get_sequential_only_tools() -> list[str]:
    """Tools requiring sequential execution (default: [])."""
    return _config.get("execution.sequential_only_tools", [])


# LLM configuration getters
def get_planning_tokens() -> int:
    """Token limit for planning prompts (default: 16000)."""
    return _config.get("llm.planning_tokens", 16000)


def get_summarization_max_tokens() -> int:
    """Max tokens for summarization responses (default: 4000)."""
    return _config.get("llm.summarization_max_tokens", 4000)


def get_evaluation_max_tokens() -> int:
    """Max tokens for evaluation responses (default: 4000)."""
    return _config.get("llm.evaluation_max_tokens", 4000)


def get_token_reduction_factors() -> list[float]:
    """Token reduction sequence (default: [0.8, 0.6, 0.4])."""
    return _config.get("llm.token_reduction_factors", [0.8, 0.6, 0.4])


def get_azure_api_version() -> str:
    """Azure OpenAI API version (default: 2024-08-01-preview)."""
    return _config.get("llm.azure_api_version", "2024-08-01-preview")


# Benchmark configuration getters
def get_tasks_file() -> str:
    """Default tasks file path (default: tasks.jsonl)."""
    return _config.get("benchmark.tasks_file", "tasks.jsonl")


def get_all_task_files() -> list[str]:
    """All task files for comprehensive runs (default: [])."""
    return _config.get("benchmark.all_task_files", [])


def is_judge_stability_enabled() -> bool:
    """LLM judge stability testing flag (default: False)."""
    return _config.get("benchmark.enable_judge_stability", False)


def is_problematic_tools_filter_enabled() -> bool:
    """Filter known problematic tools (default: True)."""
    return _config.get("benchmark.filter_problematic_tools", True)


def is_concurrent_summarization_enabled() -> bool:
    """Enable concurrent summarization (default: False)."""
    return _config.get("benchmark.concurrent_summarization", False)


def use_fuzzy_descriptions() -> bool:
    """Use fuzzy task descriptions instead of concrete (default: False)."""
    return _config.get("benchmark.use_fuzzy_descriptions", False)


def is_concrete_description_ref_enabled() -> bool:
    """Include concrete description references (default: True)."""
    return _config.get("benchmark.concrete_description_ref", True)


# Cache configuration getters
def is_cache_enabled() -> bool:
    """Tool call caching enabled flag (default: False)."""
    return _config.get("cache.enabled", False)


def get_cache_dir() -> str:
    """Cache directory path (default: .cache/)."""
    return _config.get("cache.dir", ".cache/")


def get_cache_ttl() -> int:
    """Cache time-to-live in seconds (default: 86400)."""
    return _config.get("cache.ttl", 86400)


def get_cache_max_size_mb() -> int:
    """Maximum cache size in MB (default: 1000)."""
    return _config.get("cache.max_size_mb", 1000)


def get_cache_key_strategy() -> str:
    """Cache key generation strategy (default: content_hash)."""
    return _config.get("cache.key_strategy", "content_hash")


def is_cache_log_stats_enabled() -> bool:
    """Log cache statistics (default: True)."""
    return _config.get("cache.log_stats", True)


def get_cache_cleanup_interval() -> int:
    """Cache cleanup interval in seconds (default: 3600)."""
    return _config.get("cache.cleanup_interval", 3600)


def get_cache_server_whitelist() -> list[str]:
    """Servers eligible for caching (default: [])."""
    return _config.get("cache.server_whitelist", [])


def load_config(
    global_source: str = "global_config.yaml",
    benchmark_source: Optional[str] = None
) -> BenchmarkRunConfig:
    """
    Load and merge configurations from multiple sources.
    
    Args:
        global_source: Path to global configuration file
        benchmark_source: Optional path to benchmark-specific configuration
    
    Returns:
        Validated BenchmarkRunConfig instance
    
    Raises:
        ValidationError: If configuration is invalid
        FileNotFoundError: If config files don't exist
    """
    config_dict: dict[str, Any] = {}
    
    # Load global config
    global_path = Path(global_source)
    if global_path.exists():
        with open(global_path, "r") as f:
            global_config = yaml.safe_load(f) or {}
            config_dict.update(global_config)
            logger.info(f"Loaded global config from {global_source}")
    else:
        logger.warning(f"Global config not found: {global_source}")
    
    # Load benchmark-specific config
    if benchmark_source:
        benchmark_path = Path(benchmark_source)
        if benchmark_path.exists():
            with open(benchmark_path, "r") as f:
                benchmark_config = yaml.safe_load(f) or {}
                # Deep merge
                for key, value in benchmark_config.items():
                    if key in config_dict and isinstance(config_dict[key], dict) and isinstance(value, dict):
                        config_dict[key].update(value)
                    else:
                        config_dict[key] = value
                logger.info(f"Loaded benchmark config from {benchmark_source}")
        else:
            logger.warning(f"Benchmark config not found: {benchmark_source}")
    
    # Ensure required fields exist
    if "models" not in config_dict:
        config_dict["models"] = []
    if "metadata" not in config_dict:
        config_dict["metadata"] = {}
    
    # Validate and return
    try:
        return BenchmarkRunConfig(**config_dict)
    except ValidationError as e:
        logger.error(f"Configuration validation failed: {e}")
        raise


def apply_overrides(
    config: BenchmarkRunConfig,
    overrides: dict[str, Any]
) -> BenchmarkRunConfig:
    """
    Apply runtime overrides to configuration.
    
    Args:
        config: Base configuration
        overrides: Dictionary of overrides using dot notation keys
    
    Returns:
        New BenchmarkRunConfig instance with overrides applied
    """
    # Create mutable copy
    config_dict = config.model_dump()
    
    # Apply overrides
    for key_path, value in overrides.items():
        keys = key_path.split(".")
        current = config_dict
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
        logger.debug(f"Applied override: {key_path}={value}")
    
    # Return new validated instance
    return BenchmarkRunConfig(**config_dict)
