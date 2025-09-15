# Execution Module

Enterprise-grade task execution system for LLM benchmarking with support for both simple single-turn and complex multi-round agentic workflows.

## Overview

The execution module provides a flexible, extensible architecture for running benchmark tasks across multiple LLM providers with comprehensive error handling, retry logic, and state management.

## Quick Start

### Simple Execution

```python
from benchmark.execution import SimpleExecutor
from benchmark.models import ModelConfig, Task, ChatMessage

# Configure models
models = [
    ModelConfig(name="gpt-4o", provider="azure"),
    ModelConfig(name="claude-sonnet-4", provider="openrouter"),
]

# Create executor
executor = SimpleExecutor(models=models, concurrent_execution=True)

# Create task
task = Task(
    id="task_001",
    messages=[ChatMessage(role="user", content="What is 2+2?")],
    ground_truth="4",
)

# Execute
results = await executor.execute_task(task)
for result in results:
    print(f"{result.model_name}: {result.response}")
```

### Agentic Execution

```python
from benchmark.execution.agentic import AgenticExecutor
from features.tools import ToolRegistry, Tool

# Create tool registry
registry = ToolRegistry()

# Register tools
class CalculatorTool(Tool):
    name = "calculator"
    description = "Performs basic arithmetic"
    parameters = {
        "expression": {"type": "string", "description": "Math expression"}
    }
    
    async def execute(self, expression: str):
        return eval(expression)

registry.register(CalculatorTool())

# Create executor
executor = AgenticExecutor(
    models=models,
    tool_registry=registry,
    concurrent_summarization=False
)

# Execute with tool use
results = await executor.execute_task(task)
```

## Components

### Executors

#### SimpleExecutor
- **Purpose**: Single-turn chat completions
- **Use Cases**: Q&A, classification, simple generation
- **Features**:
  - Parallel model execution
  - Automatic retry on transient errors
  - Token usage tracking
  - Comprehensive error handling

#### AgenticExecutor
- **Purpose**: Multi-round planning and tool execution
- **Use Cases**: Complex reasoning, research tasks, multi-step problems
- **Features**:
  - Planning → Execution → Synthesis loop
  - Up to 10 execution rounds (configurable)
  - Automatic context compression
  - Tool orchestration
  - State management
  - Error recovery (token limits, content filters, JSON parsing)

### LLM Providers

#### Supported Providers
- **Azure OpenAI**: Enterprise-grade OpenAI models
- **OpenAI**: Direct OpenAI API
- **OpenRouter**: Access to Claude, Gemini, DeepSeek, Qwen, etc.
- **Custom**: Any OpenAI-compatible endpoint

#### Provider Features
- Automatic retry with exponential backoff
- Token limit detection and extraction
- Content filter detection
- Authentication error handling
- Usage tracking
- JSON response cleaning

### Error Handling

#### Exception Hierarchy
```
LLMProviderError (base)
├── LLMAuthenticationError     # API key/auth failures
├── LLMAPIError                # Network/communication errors
├── ContentFilterError         # Safety filter violations
├── TokenLimitError            # Context length exceeded
└── InvalidResponseError       # Malformed responses
```

#### Error Recovery
- **Token Limit**: Automatic compression (LLM + rule-based fallback)
- **Content Filter**: Logged and surfaced in results
- **Network Errors**: Retry with exponential backoff (3 attempts)
- **Invalid JSON**: Auto-fix with markdown removal and fallback structure
- **Authentication**: Immediate failure with clear error message

## Configuration

### Environment Variables

```bash
# Azure OpenAI
AZURE_OPENAI_API_KEY=your_key
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/

# OpenRouter
OPENROUTER_API_KEY=your_key

# Custom models
CUSTOM_MODEL_MYMODEL_API_KEY=your_key
CUSTOM_MODEL_MYMODEL_BASE_URL=https://api.example.com/v1
```

### Config File Settings

```yaml
execution:
    task_timeout: 300
    max_retries: 3
    retry_delay: 1
    max_execution_rounds: 10
    compression_retries: 3
    content_summary_threshold: 10000
    content_truncate_length: 50000

llm:
    planning_tokens: 16000
    summarization_max_tokens: 4000
    evaluation_max_tokens: 4000
    token_reduction_factors: [0.8, 0.6, 0.4]
```

### Programmatic Configuration

```python
from benchmark.config.loader import load_config, apply_overrides

config = load_config("global_config.yaml", "tests/my_benchmark/config.yaml")
config = apply_overrides(config, {
    "execution.max_execution_rounds": 15,
    "llm.planning_tokens": 20000,
})
```

## Advanced Usage

### Custom Hooks

```python
from benchmark.execution.base import ExecutionHook

class MetricsHook(ExecutionHook):
    async def before_task(self, task):
        print(f"Starting task: {task.id}")
    
    async def after_task(self, task, results):
        for result in results:
            print(f"Completed: {result.model_name} in {result.execution_time:.2f}s")

executor = SimpleExecutor(models=models, hooks=[MetricsHook()])
```

### Custom Provider

```python
from benchmark.execution.llm import LLMFactory
from benchmark.models import ModelConfig

config = ModelConfig(
    name="my-custom-model",
    provider="custom",
    api_key="sk-...",
    base_url="https://api.example.com/v1",
    config={"temperature": 0.5}
)

provider = await LLMFactory.create_llm_provider(config)
response = await provider.get_completion(
    system_prompt="You are helpful.",
    user_prompt="Hello!",
    max_tokens=2048,
    temperature=0.7
)
```

### Token Limit Handling

```python
from benchmark.execution.llm.exceptions import TokenLimitError

try:
    response = await provider.get_completion(prompt, max_tokens=100000)
except TokenLimitError as e:
    print(f"Requested: {e.requested}, Max: {e.max_tokens}")
    # Automatically handled in AgenticExecutor via compression
```

## Architecture

### Execution Flow

```
Task → Executor → LLMProvider → API → Response
         ↓
    TaskResult
```

### Agentic Flow

```
Task → AgenticExecutor
         ├─→ Plan (LLM)
         ├─→ Execute Tools
         ├─→ Update State
         ├─→ Compress if needed
         └─→ Synthesize Solution
              ↓
         TaskResult (with tool_calls, conversation_history)
```

## File Structure

```
execution/
├── __init__.py                     # Module exports
├── base.py                         # Executor protocol
├── simple_executor.py              # Simple executor
├── IMPLEMENTATION.md               # Implementation details
├── ARCHITECTURE_FLOW.md            # Architecture diagrams
├── agentic/
│   ├── __init__.py
│   ├── context.py                  # State management
│   └── executor.py                 # Agentic executor
└── llm/
    ├── __init__.py
    ├── exceptions.py               # Exception hierarchy
    ├── provider.py                 # LLM provider
    ├── factory.py                  # Provider factory
    └── providers/
        ├── __init__.py
        ├── openai.py               # Azure/OpenAI/Custom
        └── openrouter.py           # OpenRouter
```

## Best Practices

1. **Use SimpleExecutor** for straightforward tasks (Q&A, classification)
2. **Use AgenticExecutor** for complex, multi-step tasks requiring tools
3. **Configure timeouts** appropriately for your tasks
4. **Monitor token usage** to optimize costs
5. **Implement custom hooks** for observability
6. **Handle errors gracefully** with typed exceptions
7. **Test with multiple providers** for robustness
8. **Use concurrent execution** when tasks are independent
9. **Enable compression** for long-running agentic tasks
10. **Leverage tool registry** for reusable capabilities

## Performance

### Simple Executor
- Parallel execution across models (configurable)
- Typical task: 1-5 seconds per model
- Token usage: Varies by model and task complexity

### Agentic Executor
- Sequential execution (complex state management)
- Typical task: 10-60 seconds (depends on rounds)
- Token usage: Higher due to planning and synthesis
- Compression: Automatically triggered above threshold

## Troubleshooting

### Import Errors
```python
# Ensure proper imports
from benchmark.execution import SimpleExecutor, AgenticExecutor
from benchmark.execution.llm import LLMFactory
```

### Provider Initialization Failures
- Verify API keys in environment variables
- Check endpoint URLs (Azure requires full endpoint)
- Ensure required packages installed: `pip install openai`

### Token Limit Errors
- Enable compression in agentic mode
- Reduce planning_tokens in config
- Use token_reduction_factors to control compression

### Timeout Errors
- Increase task_timeout in config
- Check network connectivity
- Verify provider service status

## Contributing

When extending the execution module:

1. Follow the Executor protocol for new executors
2. Use typed exceptions from llm.exceptions
3. Add comprehensive docstrings with Args/Returns/Raises
4. Include error handling and logging
5. Add tests for new functionality
6. Update documentation

## See Also

- [IMPLEMENTATION.md](IMPLEMENTATION.md) - Implementation details
- [ARCHITECTURE_FLOW.md](ARCHITECTURE_FLOW.md) - Architecture diagrams
- [../../docs/architecture.md](../../docs/architecture.md) - Overall architecture
- [../../docs/running.md](../../docs/running.md) - Running benchmarks
