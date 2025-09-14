"""
Core data models for the benchmark library.

Centralized Pydantic models and type aliases for type-safe data handling
throughout the benchmarking pipeline.
"""

from typing import Optional, Any, Literal
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class ChatMessage(BaseModel):
    """Single message in a chat conversation."""
    
    model_config = ConfigDict(extra="allow")
    
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    name: Optional[str] = None
    function_call: Optional[dict[str, Any]] = None


class Task(BaseModel):
    """Individual benchmark task definition."""
    
    model_config = ConfigDict(extra="allow")
    
    id: str
    messages: list[ChatMessage]
    ground_truth: Any
    metadata: dict[str, Any] = Field(default_factory=dict)
    timeout: Optional[int] = None


class ModelConfig(BaseModel):
    """LLM model configuration."""
    
    model_config = ConfigDict(extra="allow")
    
    name: str
    provider: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    config: dict[str, Any] = Field(default_factory=dict)


class BenchmarkRunConfig(BaseModel):
    """Merged runtime configuration for benchmark execution."""
    
    model_config = ConfigDict(extra="allow")
    
    metadata: dict[str, Any] = Field(default_factory=dict)
    models: list[ModelConfig]
    execution: dict[str, Any] = Field(default_factory=dict)
    evaluation: dict[str, Any] = Field(default_factory=dict)
    results: dict[str, Any] = Field(default_factory=dict)


class TaskResult(BaseModel):
    """Result of a single task execution."""
    
    model_config = ConfigDict(extra="allow")
    
    task_id: str
    model_name: str
    response: str
    execution_time: float
    token_usage: dict[str, int] = Field(default_factory=dict)
    error: Optional[str] = None
    success: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)
    raw_response: Optional[dict[str, Any]] = None
    conversation_history: list[dict[str, Any]] = Field(default_factory=list)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    available_tools: dict[str, Any] = Field(default_factory=dict)


class Grade(BaseModel):
    """Evaluation grade for a task result."""
    
    model_config = ConfigDict(extra="allow")
    
    score: float = Field(ge=0.0, le=1.0)
    passed: bool
    reasoning: str
    grader_name: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class BenchmarkOutput(BaseModel):
    """Aggregate benchmark results."""
    
    model_config = ConfigDict(extra="allow")
    
    metadata: dict[str, Any]
    results: list[tuple[TaskResult, Grade]]
    summary: dict[str, Any]
    execution_time: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
