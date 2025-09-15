# Execution Module Architecture

## Directory Structure

```
benchmark/execution/
├── __init__.py                     # Exports: Executor, ExecutionHook, SimpleExecutor, AgenticExecutor, ExecutionContext
├── base.py                         # Base protocols
├── simple_executor.py              # Simple single-turn executor
├── IMPLEMENTATION.md               # Implementation documentation
├── agentic/
│   ├── __init__.py                 # Exports: ExecutionContext, AgenticExecutor
│   ├── context.py                  # ExecutionContext dataclass
│   └── executor.py                 # AgenticExecutor implementation
└── llm/
    ├── __init__.py                 # LLM module exports
    ├── exceptions.py               # Exception hierarchy
    ├── provider.py                 # LLMProvider class
    ├── factory.py                  # LLMFactory class
    └── providers/
        ├── __init__.py
        ├── openai.py               # Azure/OpenAI/Custom provider factory
        └── openrouter.py           # OpenRouter provider factory
```

## Execution Flow

### Simple Execution Flow

```
SimpleExecutor.execute_task()
    │
    ├─→ _initialize_providers()
    │       └─→ LLMFactory.create_llm_provider() for each model
    │
    ├─→ For each model (parallel or sequential):
    │   │
    │   └─→ _execute_single_model()
    │       │
    │       ├─→ Build prompts from task.messages
    │       │
    │       ├─→ LLMProvider.get_completion()
    │       │   │
    │       │   ├─→ Try API call (with retry logic)
    │       │   │
    │       │   ├─→ Check for errors:
    │       │   │   ├─→ TokenLimitError
    │       │   │   ├─→ ContentFilterError
    │       │   │   ├─→ LLMAuthenticationError
    │       │   │   └─→ LLMAPIError
    │       │   │
    │       │   └─→ Return (response, usage_dict)
    │       │
    │       ├─→ Create TaskResult
    │       │
    │       └─→ Log metrics
    │
    └─→ Return list[TaskResult]
```

### Agentic Execution Flow

```
AgenticExecutor.execute()
    │
    ├─→ Initialize ExecutionContext
    │
    ├─→ Multi-round loop (max 10 rounds):
    │   │
    │   ├─→ _plan_next_actions()
    │   │   │
    │   │   ├─→ Build planning prompt with:
    │   │   │   ├─→ Task description
    │   │   │   ├─→ Available tools
    │   │   │   └─→ Accumulated information
    │   │   │
    │   │   ├─→ LLMProvider.get_completion()
    │   │   │
    │   │   ├─→ Parse JSON response
    │   │   │   └─→ Auto-fix if malformed
    │   │   │
    │   │   └─→ Return plan dict
    │   │
    │   ├─→ Check if task_complete
    │   │   └─→ If yes, break loop
    │   │
    │   ├─→ _execute_planned_tools()
    │   │   │
    │   │   ├─→ For each tool in plan:
    │   │   │   │
    │   │   │   ├─→ ToolRegistry.execute_tool()
    │   │   │   │
    │   │   │   └─→ Collect result/error
    │   │   │
    │   │   └─→ Return execution_results
    │   │
    │   ├─→ _update_state()
    │   │   │
    │   │   ├─→ Format execution results
    │   │   │
    │   │   ├─→ Append to accumulated_info
    │   │   │
    │   │   ├─→ Check size threshold
    │   │   │   │
    │   │   │   └─→ If exceeded:
    │   │   │       └─→ compress_accumulated_information()
    │   │   │           │
    │   │   │           ├─→ Try LLM summarization
    │   │   │           │
    │   │   │           └─→ Fallback to rule-based compression
    │   │   │
    │   │   └─→ Return updated accumulated_info
    │   │
    │   └─→ context.start_new_round()
    │
    ├─→ _synthesize_final_solution()
    │   │
    │   ├─→ Build synthesis prompt
    │   │
    │   ├─→ LLMProvider.get_completion()
    │   │
    │   └─→ Return final answer
    │
    └─→ Create TaskResult with:
        ├─→ response
        ├─→ execution_time
        ├─→ conversation_history
        ├─→ tool_calls
        ├─→ metadata (rounds, compressions, etc.)
        └─→ available_tools
```

## Error Recovery Flow

### Token Limit Error Recovery

```
TokenLimitError raised
    │
    ├─→ Check context.can_compress()
    │   │
    │   ├─→ Yes: compress_accumulated_information()
    │   │   │
    │   │   ├─→ Apply token reduction factor
    │   │   │   (0.8, 0.6, 0.4 on successive attempts)
    │   │   │
    │   │   ├─→ Try LLM summarization
    │   │   │
    │   │   └─→ Fallback to rule-based compression
    │   │       (keep first/last portions)
    │   │
    │   └─→ No: Raise error (max compressions reached)
    │
    └─→ Retry with compressed context
```

### Invalid JSON Recovery

```
JSON parsing fails
    │
    ├─→ Check context.can_fix_format()
    │   │
    │   ├─→ Yes: _fix_invalid_json_format()
    │   │   │
    │   │   ├─→ Remove markdown code blocks
    │   │   │
    │   │   ├─→ Try parsing cleaned version
    │   │   │
    │   │   └─→ Fallback to minimal valid structure
    │   │       {"task_complete": false, "tool_calls": []}
    │   │
    │   └─→ No: Raise InvalidResponseError
    │
    └─→ Continue with fixed JSON
```

## Provider Initialization

```
LLMFactory.create_llm_provider(model_config)
    │
    ├─→ Check provider_type:
    │   │
    │   ├─→ "azure":
    │   │   └─→ create_openai_provider(model_config, "azure")
    │   │       └─→ AsyncAzureOpenAI(api_key, endpoint, api_version)
    │   │
    │   ├─→ "openai":
    │   │   └─→ create_openai_provider(model_config, "openai")
    │   │       └─→ AsyncOpenAI(api_key)
    │   │
    │   ├─→ "openrouter":
    │   │   └─→ create_openrouter_provider(model_config)
    │   │       └─→ AsyncOpenAI(api_key, base_url="https://openrouter.ai/api/v1")
    │   │
    │   └─→ "custom":
    │       └─→ create_openai_provider(model_config, "custom")
    │           └─→ AsyncOpenAI(api_key, base_url)
    │
    └─→ Return LLMProvider(client, deployment_name, provider_type)
```

## Key Classes and Their Responsibilities

### Executor (Abstract)
- Define execution contract
- Hook management
- Task orchestration

### SimpleExecutor
- Single-turn execution
- Model parallelization
- Basic error handling
- Token tracking

### AgenticExecutor
- Multi-round execution
- Planning loop
- Tool orchestration
- Context management
- Compression handling
- Solution synthesis

### ExecutionContext
- State tracking
- Limit enforcement
- Attempt counting
- Status reporting

### LLMProvider
- Unified API interface
- Retry logic
- Error detection
- Token counting
- JSON parsing

### LLMFactory
- Model registry
- Provider creation
- Configuration validation
- Environment integration

## Configuration Integration

The execution module reads configuration from:

```python
# From benchmark.config.loader
get_max_execution_rounds()          # Default: 10
get_compression_retries()           # Default: 3
get_planning_tokens()               # Default: 16000
get_summarization_max_tokens()      # Default: 4000
get_token_reduction_factors()       # Default: [0.8, 0.6, 0.4]
get_content_summary_threshold()     # Default: 10000
get_content_truncate_length()       # Default: 50000
```

These can be overridden via:
1. `global_config.yaml`
2. Benchmark-specific `config.yaml`
3. Environment variables (`BENCHMARK_*`)
4. Programmatic overrides

## Usage Examples

### Simple Execution

```python
from benchmark.execution import SimpleExecutor
from benchmark.models import ModelConfig

executor = SimpleExecutor(
    models=[
        ModelConfig(name="gpt-4o", provider="azure"),
        ModelConfig(name="claude-sonnet-4", provider="openrouter"),
    ],
    concurrent_execution=True
)

results = await executor.execute_task(task)
```

### Agentic Execution

```python
from benchmark.execution.agentic import AgenticExecutor
from features.tools import ToolRegistry

registry = ToolRegistry()
registry.register(MyCustomTool())

executor = AgenticExecutor(
    models=[ModelConfig(name="gpt-4o", provider="azure")],
    tool_registry=registry,
    concurrent_summarization=False
)

results = await executor.execute_task(task)
```

### Custom Provider

```python
from benchmark.execution.llm import LLMFactory
from benchmark.models import ModelConfig

# Create custom provider
config = ModelConfig(
    name="my-model",
    provider="custom",
    api_key="...",
    base_url="https://api.example.com/v1"
)

provider = await LLMFactory.create_llm_provider(config)
response, usage = await provider.get_completion(
    system_prompt="You are helpful.",
    user_prompt="Hello!",
    return_usage=True
)
```
