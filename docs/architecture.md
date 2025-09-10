```
.
├── benchmark/
│   ├── __init__.py
│   ├── models.py
│   ├── benchmark.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── loader.py
│   ├── execution/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── simple_executor.py
│   │   ├── agentic/
│   │   │   ├── __init__.py
│   │   │   ├── context.py
│   │   │   └── executor.py
│   │   └── llm/
│   │       ├── __init__.py
│   │       ├── exceptions.py
│   │       ├── factory.py
│   │       ├── provider.py
│   │       └── providers/
│   │           ├── __init__.py
│   │           ├── openai.py
│   │           └── openrouter.py
│   └── evaluation/
│       ├── __init__.py
│       ├── evaluator.py
│       └── graders.py
├── visualizer/
│   ├── __init__.py
│   ├── aggregator.py
│   ├── formatter.py
│   └── graph.py
├── features/
│   ├── __init__.py
│   └── tools.py
├── utils/
│   ├── __init__.py
│   └── error_handler.py
├── tests/
│   └── example_benchmark/
│       ├── config.yaml
│       ├── example_benchmark.py
│       └── questions.jsonl
├── docs/
│   ├── architecture.md
│   └── running.md
├── prompts/
│   ├── conversationalist
│   ├── direct
│   └── README.md
├── .env.example
├── .gitignore
├── global_config.yaml
├── main.py
├── pyproject.toml
├── example_benchmark.ipynb
└── README.md
```

---

## Core Architecture

### Primary Execution Flow

The benchmark library has **one primary execution path** for all benchmarks:

```
CLI (main.py) or Programmatic Import
    ↓
Benchmark.__init__()
    ├── Load & merge configurations
    ├── Parse tasks from questions.jsonl
    └── Initialize executor with LLM providers
    ↓
Benchmark.run()
    ├── For each task:
    │   ├── Executor.execute_task() → list[TaskResult]
    │   └── Benchmark.grade() → Grade
    └── Aggregate → BenchmarkOutput
    ↓
Save results & display summary
```

### Execution Mode Details

**Simple Execution** (default):

```
SimpleExecutor.execute_task(task)
    ├── For each model in parallel:
    │   ├── LLMProvider.get_completion(messages)
    │   ├── Handle retries & errors
    │   └── Return TaskResult
    └── Return list[TaskResult] (one per model)
```

**Agentic Execution** (tool-using):

```
AgenticExecutor.execute_task(task)
    ├── For each model:
    │   ├── Create ExecutionContext
    │   └── Multi-round loop (max 10 rounds):
    │       ├── Plan: LLM decides next tool calls (JSON)
    │       ├── Execute: Run tools (sequential/parallel)
    │       ├── Update: Append results, compress if needed
    │       └── Check: Complete or continue?
    │   ├── Synthesize final answer
    │   └── Return TaskResult with execution history
    └── Return list[TaskResult]
```

---

## Detailed Component Specifications

### `benchmark/models.py`

**Purpose**: Centralized Pydantic models and typed aliases.

**Data Models**:

-   **`ChatMessage`**: Single message in chat conversation

    -   `role: str` - Message role (system, user, assistant)
    -   `content: str` - Message content
    -   `name: Optional[str]` - Optional sender name
    -   `function_call: Optional[dict]` - Optional function call metadata

-   **`Task`**: Individual benchmark task

    -   `id: str` - Unique task identifier
    -   `messages: list[ChatMessage]` - Conversation history
    -   `ground_truth: Any` - Expected answer for evaluation
    -   `metadata: dict` - Additional task-specific data
    -   `timeout: Optional[int]` - Task-specific timeout override

-   **`ModelConfig`**: LLM model configuration

    -   `name: str` - Model identifier
    -   `provider: str` - Provider type (openai, openrouter, azure)
    -   `api_key: Optional[str]` - API authentication key
    -   `base_url: Optional[str]` - Custom API endpoint
    -   `temperature: float` - Sampling temperature
    -   `max_tokens: int` - Maximum response tokens
    -   `config: dict` - Additional provider-specific settings

-   **`BenchmarkRunConfig`**: Merged runtime configuration

    -   `metadata: dict` - Benchmark metadata (name, version, description)
    -   `models: list[ModelConfig]` - Models to test
    -   `execution: dict` - Execution settings (timeout, retries, rounds)
    -   `evaluation: dict` - Evaluation settings (judge stability, consensus)
    -   `results: dict` - Output configuration (directory, format)
    -   `concurrent_execution: bool` - Enable parallel model execution

-   **`TaskResult`**: Result of task execution

    -   `task_id: str` - Reference to source task
    -   `model_name: str` - Model that generated the result
    -   `response: str` - Model's generated response
    -   `raw_response: dict` - Complete provider response payload
    -   `execution_time: float` - Execution duration in seconds
    -   `token_usage: dict` - Token consumption metrics
    -   `error: Optional[str]` - Error message if execution failed
    -   `execution_results: list[dict]` - Tool execution history (agentic mode)
    -   `accumulated_information: str` - Multi-round context (agentic mode)
    -   `total_rounds: int` - Number of execution rounds (agentic mode)
    -   `available_tools: dict` - Tools available during execution (agentic mode)

-   **`Grade`**: Evaluation grade for a task result

    -   `score: float` - Normalized score (0.0-1.0)
    -   `passed: bool` - Binary pass/fail indicator
    -   `reasoning: str` - Explanation of the grade
    -   `grader_name: str` - Identifier of the grading method
    -   `subdimension_scores: dict` - Detailed scoring breakdown (for LLM judge)
    -   `metadata: dict` - Additional grading context

-   **`BenchmarkOutput`**: Aggregate benchmark results
    -   `metadata: dict` - Run metadata (timestamp, config snapshot)
    -   `results: list[tuple[TaskResult, Grade]]` - All task outcomes
    -   `summary: dict` - Aggregate statistics (mean score, pass rate)
    -   `errors: list[str]` - Execution errors encountered
    -   `execution_time: float` - Total benchmark duration

---

### `benchmark/benchmark.py`

**Purpose**: Abstract base class that users extend to define benchmarks.

**Class: `Benchmark(ABC)`**

**Methods**:

-   `__init__(self, config=None, questions=None, executor_class=SimpleExecutor, global_config="global_config.yaml", executor_kwargs=None)`

    -   Loads configuration via `config.loader.load_config()`
        -   Merges global_config.yaml with benchmark-specific config
        -   Applies environment variable overrides (BENCHMARK\_\* prefix)
        -   Validates with BenchmarkRunConfig Pydantic model
    -   Loads tasks from questions file
        -   Reads JSONL file line by line
        -   Parses each into Task Pydantic model
        -   Stores in self.tasks list
    -   Instantiates executor
        -   Extracts models from config.models
        -   Creates LLM providers via LLMFactory.create_llm_provider()
        -   Calls executor_class(models, \*\*executor_kwargs)
        -   For agentic: pass tool_registry in executor_kwargs
    -   Sets up logging and error handling
    -   Stores config, tasks, executor as instance attributes

-   `@abstractmethod async def grade(self, result: TaskResult, task: Task) -> Grade`

    -   **User must implement** - defines how to score model responses
    -   Receives executor output (TaskResult) and original task
    -   Should compare result.response vs task.ground_truth
    -   Can use helpers from `evaluation.graders` module:
        -   `exact_match()`, `substring_match()`, `regex_match()`
        -   `json_schema_match()`, `numeric_tolerance_match()`
    -   Can implement custom logic for complex grading
    -   Must return Grade object with:
        -   score (float 0.0-1.0)
        -   passed (bool)
        -   reasoning (str explanation)
        -   grader_name (str identifier)

-   `async def run(self) -> BenchmarkOutput`
    -   **Main orchestration method** - runs complete benchmark
    -   Flow:
        1. Initialize results list and timing
        2. For each task in self.tasks:
           a. Call self.executor.execute_task(task)
           b. Returns list[TaskResult] (one per model)
           c. For each TaskResult: - Call self.grade(result, task) → Grade - Catch and log any grading errors - Store (TaskResult, Grade) tuple
        3. Calculate summary statistics:
            - Mean score across all results
            - Pass rate (% with passed=True)
            - Total execution time
            - Token usage totals
        4. Construct BenchmarkOutput with:
            - metadata (timestamp, config snapshot)
            - results (list of (TaskResult, Grade) tuples)
            - summary (statistics dict)
            - errors (any errors encountered)
            - execution_time (total duration)
        5. If config.results.save_results=True:
            - Save to config.results.output_dir as JSON
        6. Return BenchmarkOutput instance

**Properties**:

-   `config: BenchmarkRunConfig` - Validated configuration object
-   `tasks: list[Task]` - Loaded benchmark tasks from questions file
-   `executor: Executor` - Instantiated executor (Simple or Agentic)

**Usage Example**:

```python
class MyBenchmark(Benchmark):
    async def grade(self, result: TaskResult, task: Task) -> Grade:
        # Simple exact match grading
        if result.response.strip() == task.ground_truth:
            return Grade(
                score=1.0,
                passed=True,
                reasoning="Exact match",
                grader_name="exact_match"
            )
        return Grade(score=0.0, passed=False, reasoning="No match", grader_name="exact_match")

# Run benchmark
benchmark = MyBenchmark()  # Loads tests/my_benchmark/config.yaml automatically
result = await benchmark.run()
```

---

### `benchmark/config/loader.py`

**Purpose**: Configuration management with YAML loading, validation, and override support.

**Singleton Class: `BenchmarkConfig`**

**Core Methods**:

-   `__new__(cls)` - Ensures single instance across application
-   `__init__(self)` - Initializes configuration on first instantiation
-   `_load_config(self)` - Loads YAML, applies environment overrides, validates structure
-   `_get_default_config(self) -> dict` - Returns comprehensive default configuration dictionary
-   `_apply_env_overrides(self)` - Processes environment variables with BENCHMARK\_ prefix
-   `_convert_env_value(self, value: str)` - Converts string env values to proper types (int, bool, float, list)
-   `_set_nested_value(self, config: dict, path: str, value)` - Updates nested dict values using dot notation
-   `get(self, key_path: str, default=None)` - Retrieves config value using dot notation (e.g., "execution.max_retries")
-   `get_section(self, section: str) -> dict` - Returns entire config section (e.g., "execution" returns all execution settings)
-   `reload(self)` - Reloads configuration from disk, re-applies overrides

**Configuration Getter Functions**:

_Execution Configuration_:

-   `get_mcp_timeout() -> int` - MCP server operation timeout (default: 30s)
-   `get_task_timeout() -> int` - Task execution timeout (default: 300s)
-   `get_max_retries() -> int` - Maximum retry attempts for failed operations (default: 3)
-   `get_default_port() -> int` - Default MCP server port (default: 8000)
-   `get_distraction_servers_count() -> int` - Number of distraction servers to add (default: 2)
-   `get_retry_delay() -> int` - Delay between retry attempts in seconds (default: 1)
-   `get_task_delay() -> int` - Delay between tasks in seconds (default: 0)
-   `get_max_execution_rounds() -> int` - Maximum agentic execution rounds (default: 10)
-   `get_compression_retries() -> int` - Maximum information compression attempts (default: 3)
-   `get_server_semaphore_limit() -> int` - Concurrent server connection limit (default: 10)
-   `get_content_summary_threshold() -> int` - Content size threshold for summarization (default: 10000 chars)
-   `get_content_truncate_length() -> int` - Maximum content length before truncation (default: 50000 chars)
-   `get_error_truncate_length() -> int` - Maximum error message length (default: 1000 chars)
-   `get_sequential_only_tools() -> list[str]` - Tools requiring sequential execution (default: [])

_LLM Configuration_:

-   `get_planning_tokens() -> int` - Token limit for planning prompts (default: 16000)
-   `get_summarization_max_tokens() -> int` - Max tokens for summarization responses (default: 4000)
-   `get_evaluation_max_tokens() -> int` - Max tokens for evaluation responses (default: 4000)
-   `get_token_reduction_factors() -> list[float]` - Token reduction sequence (default: [0.8, 0.6, 0.4])
-   `get_azure_api_version() -> str` - Azure OpenAI API version (default: "2024-08-01-preview")

_Benchmark Configuration_:

-   `get_tasks_file() -> str` - Default tasks file path (default: "tasks.jsonl")
-   `get_all_task_files() -> list[str]` - All task files for comprehensive runs (default: all .jsonl in tasks/)
-   `is_judge_stability_enabled() -> bool` - LLM judge stability testing flag (default: False)
-   `is_problematic_tools_filter_enabled() -> bool` - Filter known problematic tools (default: True)
-   `is_concurrent_summarization_enabled() -> bool` - Enable concurrent summarization (default: False)
-   `use_fuzzy_descriptions() -> bool` - Use fuzzy task descriptions instead of concrete (default: False)
-   `is_concrete_description_ref_enabled() -> bool` - Include concrete description references (default: True)

_Cache Configuration_:

-   `is_cache_enabled() -> bool` - Tool call caching enabled flag (default: False)
-   `get_cache_dir() -> str` - Cache directory path (default: ".cache/")
-   `get_cache_ttl() -> int` - Cache time-to-live in seconds (default: 86400)
-   `get_cache_max_size_mb() -> int` - Maximum cache size in MB (default: 1000)
-   `get_cache_key_strategy() -> str` - Cache key generation strategy (default: "content_hash")
-   `is_cache_log_stats_enabled() -> bool` - Log cache statistics (default: True)
-   `get_cache_cleanup_interval() -> int` - Cache cleanup interval in seconds (default: 3600)
-   `get_cache_server_whitelist() -> list[str]` - Servers eligible for caching (default: [])

**Public Functions**:

-   `load_config(global_source: str, benchmark_source: str) -> BenchmarkRunConfig`

    -   Loads global_config.yaml from provided path
    -   Loads benchmark-specific config.yaml from provided path
    -   Deep merges configurations (benchmark overrides global, preserving nested structures)
    -   Applies environment variable overrides via BenchmarkConfig.\_apply_env_overrides()
    -   Validates merged configuration with Pydantic BenchmarkRunConfig model
    -   Returns typed BenchmarkRunConfig instance
    -   Raises ValidationError if configuration invalid

-   `apply_overrides(config: BenchmarkRunConfig, overrides: dict) -> BenchmarkRunConfig`
    -   Creates immutable copy of config to avoid mutation
    -   Applies programmatic overrides from dict (e.g., {"execution": {"max_retries": 5}})
    -   Merges overrides into config copy
    -   Re-validates with Pydantic to ensure consistency
    -   Returns updated BenchmarkRunConfig instance
    -   Used for notebook workflows and testing scenarios

---

### `benchmark/execution/base.py`

**Purpose**: Executor and hook protocols for task execution.

**Protocol: `Executor(ABC)`**

**Methods**:

-   `__init__(self, models: list[ModelConfig], **kwargs)`

    -   Accepts list of models to test
    -   Stores shared resources (tool registry, config)
    -   Initializes provider instances via LLMFactory

-   `async def execute_task(self, task: Task) -> list[TaskResult]`
    -   Core contract for all executors
    -   Takes single task
    -   Returns list of results (one per model)
    -   Must handle errors gracefully

**Protocol: `ExecutionHook`**

**Methods**:

-   `async def before_task(self, task: Task)` - Called before task execution
-   `async def after_task(self, task: Task, results: list[TaskResult])` - Called after completion
-   Used for logging, metrics, instrumentation

---

### `benchmark/execution/simple_executor.py`

**Purpose**: Single-turn chat completion executor.

**Class: `SimpleExecutor(Executor)`**

**Methods**:

-   `__init__(self, models: list[ModelConfig], **kwargs)`

    -   Calls parent constructor
    -   Creates LLMProvider instance for each model via `LLMFactory.create_llm_provider()`
    -   Stores provider mapping

-   `async def execute_task(self, task: Task) -> list[TaskResult]`

    -   Extracts messages from task
    -   For each model, calls `provider.get_completion(messages)`
    -   Measures execution time
    -   Extracts token usage from response
    -   Normalizes response content
    -   Handles errors with try-except, returns TaskResult with error field
    -   Returns list of TaskResult objects

-   `async def _execute_single_model(self, task: Task, provider: LLMProvider, model_name: str) -> TaskResult`

    -   Helper for single model execution
    -   Wraps provider call with timing
    -   Constructs TaskResult from response

-   `_normalize_response(self, raw_response: dict) -> str`

    -   Extracts text content from provider response
    -   Handles various response formats

-   `_extract_token_usage(self, raw_response: dict) -> dict`

    -   Parses token usage from response
    -   Returns dict with prompt_tokens, completion_tokens, total_tokens

-   `_handle_execution_error(self, error: Exception, task: Task, model: str) -> TaskResult`

    -   Creates TaskResult with error information
    -   Logs error details

-   `_log_execution_metrics(self, result: TaskResult)`
    -   Logs execution time and token usage
    -   Used for monitoring and debugging

---

### `benchmark/execution/agentic/context.py`

**Purpose**: Execution state management for multi-round agentic execution.

**Dataclass: `ExecutionContext`**

**Fields**:

-   `compression_used: bool` - Compression applied flag
-   `max_compression_attempts: int` - Maximum compression attempts
-   `compression_attempts: int` - Current compression count
-   `token_reduction_used: bool` - Token reduction applied flag
-   `max_token_reductions: int` - Maximum reduction attempts
-   `token_reduction_attempts: int` - Current reduction count
-   `format_fix_used: bool` - Format fix applied flag
-   `max_format_fixes: int` - Maximum fix attempts
-   `format_fix_attempts: int` - Current fix count
-   `current_round: int` - Current execution round
-   `max_rounds: int` - Maximum rounds allowed
-   `task_retries: int` - Task retry count
-   `max_task_retries: int` - Maximum task retries

**Methods**:

-   `can_compress(self) -> bool` - Returns True if compression available
-   `mark_compressed(self)` - Increments compression counter, sets flag
-   `can_reduce_tokens(self) -> bool` - Returns True if token reduction available
-   `apply_token_reduction(self)` - Increments reduction counter, sets flag
-   `can_fix_format(self) -> bool` - Returns True if format fixes available
-   `increment_format_fixes(self)` - Increments format fix counter
-   `can_retry_round(self) -> bool` - Returns True if more rounds allowed
-   `start_new_round(self)` - Increments round counter, resets round-specific state
-   `can_retry_task(self) -> bool` - Returns True if task retries available
-   `start_new_task_retry(self)` - Increments task retry counter
-   `get_status_summary(self) -> str` - Returns human-readable status string

---

### `benchmark/execution/agentic/executor.py`

**Purpose**: Multi-round agentic executor with planning and tool execution.

**Class: `AgenticExecutor(Executor)`**

**Methods**:

-   `__init__(self, models: list[ModelConfig], tool_registry: ToolRegistry, concurrent_summarization: bool = False)`

    -   Initializes parent executor
    -   Stores tool registry reference
    -   Sets up concurrent summarization flag
    -   Creates provider instances

-   `async def execute_task(self, task: Task) -> list[TaskResult]`

    -   For each model, calls `self.execute(task, model_name)`
    -   Returns list of TaskResult objects

-   `async def execute(self, task: Task, model_name: str) -> TaskResult`

    -   Creates ExecutionContext
    -   Initializes accumulated_information as empty string
    -   Gets available_tools from tool_registry
    -   Enters planning→execution→update loop until task complete or max rounds:
        -   Calls `_plan_next_actions()`
        -   Calls `_execute_planned_tools()`
        -   Calls `_update_state()`
        -   Checks if synthesis should occur
    -   Calls `_synthesize_final_solution()`
    -   Returns TaskResult with execution history

-   `async def _plan_next_actions(self, task: Task, accumulated_info: str, available_tools: dict, context: ExecutionContext) -> dict`

    -   Builds planning prompt with `_build_planning_prompt()`
    -   Calls LLM with planning prompt
    -   Parses JSON response
    -   If JSON invalid, calls `_fix_invalid_json_format()` if fixes available
    -   If token limit error and compression available, calls `compress_accumulated_information()`
    -   If token limit error and reduction available, applies token reduction factor
    -   Returns parsed plan with tool calls

-   `async def _execute_planned_tools(self, planned_tools: list[dict], available_tools: dict, context: ExecutionContext) -> list[dict]`

    -   Identifies sequential vs parallel tools using `config.get_sequential_only_tools()`
    -   For sequential tools, executes one by one via `tool.execute(**params)`
    -   For parallel tools, executes concurrently via `asyncio.gather()`
    -   Captures execution results, errors, timing
    -   Logs token statistics with `_log_tools_token_stats()`
    -   Returns list of execution result dicts

-   `async def _update_state(self, execution_results: list[dict], accumulated_info: str, context: ExecutionContext) -> str`

    -   Appends execution results to accumulated_information
    -   If concurrent_summarization enabled and content large, calls `_summarize_content()`
    -   Checks if accumulated_info exceeds threshold
    -   If exceeded and compression available, compresses via `compress_accumulated_information()`
    -   Returns updated accumulated_information string

-   `async def _synthesize_final_solution(self, task: Task, accumulated_info: str, context: ExecutionContext) -> str`

    -   Builds synthesis prompt with task and accumulated context
    -   Calls LLM to generate final answer
    -   Handles token errors with compression/reduction
    -   Returns synthesized solution string

-   `async def compress_accumulated_information(self, accumulated_info: str, max_tokens: int, context: ExecutionContext) -> str`

    -   Calls LLM to compress accumulated_info to max_tokens
    -   If LLM compression fails, calls `_fallback_rule_based_compression()`
    -   Marks compression used in context
    -   Returns compressed string

-   `async def _summarize_content(self, content: str, max_tokens: int, retry_count: int) -> str`

    -   Calls LLM to summarize content
    -   Retries up to retry_count times on failure
    -   Returns summarized content

-   `def _fallback_rule_based_compression(self, text: str, max_tokens: int) -> str`

    -   Estimates tokens with `_estimate_token_count()`
    -   If under limit, returns original
    -   Otherwise truncates to max_tokens, preserving structure
    -   Returns compressed text

-   `def _estimate_token_count(self, text: str) -> int`

    -   Rough estimation: len(text) / 4
    -   Returns estimated token count

-   `def _log_tools_token_stats(self, execution_results: list[dict])`

    -   Aggregates token usage from tool executions
    -   Logs total tokens used
    -   Used for monitoring

-   `def _is_token_limit_error(self, error: Exception) -> bool`

    -   Checks if exception is TokenLimitError
    -   Checks error message for token limit indicators
    -   Returns boolean

-   `def _is_content_filter_error(self, error: Exception) -> bool`

    -   Checks if exception is ContentFilterError
    -   Checks error message for content filter indicators
    -   Returns boolean

-   `def _fix_invalid_json_format(self, invalid_json: str) -> dict`

    -   Attempts to repair malformed JSON using json_repair library
    -   Returns parsed dict or raises error

-   `def _build_planning_prompt(self, task: Task, accumulated_info: str, available_tools: dict) -> str`

    -   Constructs prompt with task description
    -   Includes accumulated information
    -   Lists available tools with schemas
    -   Specifies JSON response format
    -   Returns prompt string

-   `def _build_execution_summary(self, execution_results: list[dict], total_rounds: int) -> str`
    -   Formats execution history into readable text
    -   Includes round-by-round breakdown
    -   Returns summary string

---

### `benchmark/execution/llm/exceptions.py`

**Purpose**: LLM-specific exception hierarchy.

**Exception Classes**:

-   `LLMProviderError(Exception)` - Base exception for all LLM provider errors
-   `LLMAuthenticationError(LLMProviderError)` - Authentication and API key errors
-   `LLMAPIError(LLMProviderError)` - API communication and network errors
-   `ContentFilterError(LLMProviderError)` - Content safety and filter violations
-   `TokenLimitError(LLMProviderError)` - Token limit exceeded errors
-   `InvalidResponseError(LLMProviderError)` - Malformed or invalid response errors

---

### `benchmark/execution/llm/provider.py`

**Purpose**: Universal LLM provider abstraction with error handling and retry logic.

**Constants**:

-   `MODELS_WITH_MAX_COMPLETION_TOKENS: set[str]` - Models using max_completion_tokens parameter (o1, o3, o4, gpt-5 series)

**Class: `LLMProvider`**

**Methods**:

-   `__init__(self, client, deployment_name: str, provider_type: str = "azure")`

    -   Stores AsyncOpenAI or AsyncAzureOpenAI client
    -   Stores deployment/model name (used for completion API calls)
    -   Stores provider type for error handling differences

-   `async def get_completion(self, system_prompt: str, user_prompt: str, max_tokens: int = 4096, return_usage: bool = False, temperature: float = 0.7, **kwargs) -> Union[str, tuple[str, dict]]`

    -   Attempts completion up to 3 times with exponential backoff (1s, 2s delays)
    -   Constructs messages list from system_prompt and user_prompt
    -   Determines if max_tokens or max_completion_tokens parameter based on deployment_name
    -   Calls client.chat.completions.create() with appropriate parameters
    -   On token limit error, checks with `_is_token_limit_error()`, extracts counts with `_extract_requested_tokens()`, logs details, re-raises TokenLimitError
    -   On content filter error, checks with `_is_content_filter_error()`, re-raises ContentFilterError (no retries)
    -   Validates response content is not empty, raises InvalidResponseError if empty
    -   Extracts response content from choices[0].message.content
    -   If return_usage=True, returns (content, usage_dict) tuple
    -   If return_usage=False, returns content string only
    -   On other errors, logs warning and retries with exponential backoff

-   `def _is_token_limit_error(self, error_message: str) -> bool`

    -   Checks error message string for token limit indicators
    -   Searches for: "maximum context length", "token limit", "too many tokens"
    -   Case-insensitive matching
    -   Returns boolean

-   `def _is_content_filter_error(self, error_message: str) -> bool`

    -   Checks error message string for content filter violations
    -   Searches for: "content_filter", "ResponsibleAIPolicyViolation"
    -   Case-insensitive matching
    -   Returns boolean

-   `def _extract_requested_tokens(self, error_message: str) -> tuple[Optional[int], Optional[int]]`

    -   Parses error message for token count information
    -   Uses regex patterns to extract requested and maximum allowed tokens
    -   Pattern examples: "requested: 5000 tokens", "maximum: 4096"
    -   Returns (requested_tokens, max_allowed_tokens) tuple
    -   Returns (None, None) if parsing fails

-   `def clean_and_parse_json(self, raw_json: str) -> Any`
    -   Attempts standard JSON parsing first
    -   On failure, removes markdown code fences (`json, `)
    -   Finds first { or [ character in text
    -   Uses json_repair library for malformed JSON
    -   Comprehensive error logging with traceback
    -   Returns parsed dict/list or raises ValueError

---

### `benchmark/execution/llm/factory.py`

**Purpose**: Model configuration and provider factory with comprehensive model registry.

**Class: `ModelConfig`**

**Attributes**:

-   `name: str` - Model identifier (e.g., "gpt-4o", "claude-sonnet-4")
-   `provider_type: str` - Provider type (azure, openrouter, openai, custom)
-   `**kwargs: dict` - Additional configuration (api_key, base_url, api_version, temperature, max_tokens, etc.)

**Methods**:

-   `__init__(self, name: str, provider_type: str, **kwargs)`
    -   Initializes model configuration
    -   Stores name, provider_type
    -   Captures all additional kwargs for provider-specific settings

**Class: `LLMFactory`**

**Static Methods**:

-   `@staticmethod def get_model_configs() -> dict[str, ModelConfig]`

    -   Returns comprehensive model registry (100+ models)
    -   **Azure OpenAI Models**:
        -   o4-mini, gpt-4o, gpt-4o-mini, o3-mini, gpt-5
        -   Each with Azure endpoints, API keys from environment
        -   API version configured (e.g., "2024-08-01-preview")
    -   **OpenRouter Models** (base_url="https://openrouter.ai/api/v1"):
        -   Open source: qwen-3-32b, gpt-oss-20b, gpt-oss-120b, deepseek-r1-0528, kimi-k2, minimax-m1
        -   Commercial: claude-sonnet-4, gemini-2.5-pro, gpt-4o, gpt-4o-mini
        -   Specialized: llama-3.3-70b, llama-3.1-405b, command-r-plus
    -   **Custom Providers**:
        -   Llama models with custom base URLs
        -   Provider-specific configurations
    -   Environment variable detection for API keys, endpoints
    -   Returns dict mapping model_name → ModelConfig instance

-   `@staticmethod async def create_llm_provider(model_config: ModelConfig) -> LLMProvider`
    -   Factory method creating configured provider instances
    -   Reads model_config.provider_type to determine provider
    -   **If "azure"**:
        -   Creates AsyncAzureOpenAI client
        -   Parameters: azure_endpoint, api_key, api_version, timeout
        -   Extracts from model_config kwargs or environment
    -   **If "openrouter"**:
        -   Creates AsyncOpenAI client
        -   Parameters: base_url="https://openrouter.ai/api/v1", api_key, timeout
        -   Sets custom headers for OpenRouter API
    -   **If "openai"**:
        -   Creates AsyncOpenAI client with default settings
        -   Parameters: api_key, organization, timeout
    -   **If custom provider**:
        -   Creates AsyncOpenAI client with custom base_url from config
    -   Instantiates LLMProvider with created client
    -   Returns configured LLMProvider instance ready for use

---

### `benchmark/runner.py`

**Purpose**: Optional orchestration layer for **specialized MCP server benchmarks** with distraction servers and fuzzy descriptions.

> **Note**: This module is NOT required for standard benchmarking workflows. The core `Benchmark.run()` flow handles all typical use cases. This runner is specifically for testing tool-calling models against MCP (Model Context Protocol) servers with added complexity like distraction servers.

**Class: `ConnectionManager`**

**Purpose**: Async context manager for MCP server lifecycle management (MCP benchmarks only).

**Methods**:

-   `__init__(self, server_configs: dict, enable_cache: bool = False, filter_problematic_tools: bool = True)`

    -   Stores server configuration dictionary
    -   Sets cache and tool filtering flags
    -   Initializes server manager reference to None

-   `async def __aenter__(self) -> Any`

    -   Async context manager entry point
    -   Creates PersistentMultiServerManager instance
    -   Initializes all configured MCP servers
    -   Sets up tool registries and schemas
    -   Returns server manager instance for use in context
    -   Handles initialization errors with logging

-   `async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool`
    -   Async context manager exit point
    -   Gracefully shuts down all MCP server connections
    -   Closes async clients and cleans up resources
    -   Logs any cleanup errors
    -   Returns False to not suppress exceptions from context body
    -   Ensures cleanup even if errors occurred during execution

**Class: `BenchmarkRunner`**

**Purpose**: Core benchmark execution orchestration with multi-model, multi-task support.

**Methods**:

-   `__init__(self, task_executor: TaskExecutor, evaluator: TaskEvaluator, results_aggregator: ResultsAggregator, results_formatter: ResultsFormatter, task_file: str, servers_info: dict, commands_config: dict, enable_fuzzy: bool = False, concrete_ref: bool = True)`

    -   Accepts dependency injection for executor, evaluator, aggregator, formatter
    -   Stores task file path and server configuration
    -   Stores commands configuration for distraction servers
    -   Sets fuzzy descriptions and concrete reference flags
    -   Initializes internal state for tracking execution progress

-   `def load_tasks(self) -> list[dict]`

    -   Reads task file (JSON or JSONL format)
    -   Parses and validates task structure
    -   Flattens nested task arrays if present
    -   Returns list of task dictionaries ready for execution
    -   Raises FileNotFoundError if task file doesn't exist
    -   Raises ValueError if task format invalid

-   `def load_server_configs(self) -> dict`

    -   Loads MCP server configuration file (typically servers.json)
    -   Parses JSON structure with server definitions
    -   Validates required fields (name, command, args, env)
    -   Returns dictionary mapping server_name → server_config
    -   Raises ValueError if configuration invalid

-   `def load_commands_config(self) -> dict`

    -   Loads commands configuration file (commands.json)
    -   Contains available MCP server types for distraction selection
    -   Returns dict with server types, categories, metadata
    -   Used for selecting random distraction servers

-   `def map_server_name_to_config(self, server_name: str, servers_info: dict) -> dict`

    -   Maps task's server_name to actual server configuration
    -   Handles aliases and name variations
    -   Returns matching server config dict
    -   Raises KeyError if server not found in servers_info

-   `def select_random_distraction_servers(self, excluded_servers: list[str], commands_config: dict, count: int = 2) -> list[dict]`

    -   Selects random servers from commands_config for distraction
    -   Excludes servers already used in task (excluded_servers list)
    -   Selects exactly `count` servers (default 2)
    -   Returns list of distraction server config dicts
    -   Used to test model's ability to focus on relevant tools

-   `async def execute_single_task_with_model(self, task_info: dict, servers_info: dict, model_name: str, llm_provider: LLMProvider, max_retries: int = 3, timeout_seconds: int = 300) -> dict`

    -   Executes single task with specific model
    -   Retry loop up to max_retries attempts on failure
    -   Prepares task execution context via `_prepare_task_execution()`
    -   Prepares server configs via `_prepare_server_configs()`
    -   Optionally adds distraction servers via `_prepare_distraction_servers()`
    -   Calls task_executor.execute() with prepared context
    -   Wraps execution in timeout (default 300s)
    -   Captures execution results, timing, errors
    -   Returns dict with task execution details

-   `async def _run_single_file_benchmark_core(self, selected_models: list[str], task_limit: Optional[int] = None) -> dict`

    -   Core benchmark execution loop for single task file
    -   Loads tasks via `load_tasks()`
    -   Optionally limits to first `task_limit` tasks
    -   For each model in selected_models:
        -   Creates LLMProvider via LLMFactory
        -   For each task:
            -   Calls `execute_single_task_with_model()`
            -   Calls `_evaluate_task_result()` for scoring
            -   Aggregates results via results_aggregator
            -   Formats progress via results_formatter
        -   Tracks completed tasks and metrics
    -   Returns dict with all execution results and metadata

-   `async def run_benchmark(self, selected_models: list[str], task_limit: Optional[int] = None) -> dict`

    -   Main benchmark orchestration method
    -   Supports multi-file benchmarks (loads all task files via config.get_all_task_files())
    -   For each task file:
        -   Calls `run_single_file_benchmark()` with file path
        -   Collects results
    -   Aggregates cross-file results
    -   Returns comprehensive benchmark results dict

-   `async def run_single_file_benchmark(self, task_file: str, selected_models: list[str], task_limit: Optional[int] = None) -> dict`

    -   Entry point for single task file benchmark
    -   Initializes benchmark state via `_initialize_benchmark()`
    -   Creates ConnectionManager for server lifecycle
    -   Within async context manager:
        -   Calls `_run_single_file_benchmark_core()`
        -   Ensures proper server cleanup on completion or error
    -   Returns execution results dict

-   `def save_results(self, results: dict, output_file: str) -> str`

    -   Serializes benchmark results to JSON file
    -   Creates output directory if doesn't exist
    -   Writes results with pretty-printing (indent=2)
    -   Returns absolute path to saved file
    -   Used for result persistence and later analysis

-   `def _prepare_task_execution(self, task_info: dict) -> dict`

    -   Prepares task context for execution
    -   Extracts task ID, description, expected_tool_calls
    -   Handles fuzzy vs concrete descriptions based on enable_fuzzy flag
    -   Applies description transformations
    -   Returns prepared task execution dict

-   `def _prepare_server_configs(self, server_name: str, servers_info: dict, task_data: dict) -> dict`

    -   Prepares server configuration for task execution
    -   Maps server_name to config via `map_server_name_to_config()`
    -   Applies task-specific server overrides
    -   Returns server config dict ready for ConnectionManager

-   `def _prepare_distraction_servers(self, existing_server_names: list[str], task_data: dict) -> list[dict]`

    -   Prepares distraction server configurations
    -   Gets distraction count from config.get_distraction_servers_count()
    -   Calls `select_random_distraction_servers()` excluding existing
    -   Returns list of distraction server configs

-   `def _initialize_benchmark(self, selected_models: list[str], task_limit: Optional[int]) -> dict`

    -   Initializes benchmark execution state
    -   Validates selected models against available models
    -   Creates initial metrics tracking structures
    -   Logs benchmark configuration
    -   Returns initialization metadata dict

-   `async def _evaluate_task_result(self, task_execution_info: dict, execution_result: dict, model_name: str, server_name: str) -> dict`
    -   Evaluates task execution result
    -   Calls evaluator.evaluate() with execution context
    -   Combines execution data with evaluation scores
    -   Returns comprehensive result dict with:
        -   Execution details (timing, rounds, tool calls)
        -   Evaluation scores (LLM judge + accuracy metrics)
        -   Model and server metadata

**Module-Level Functions**:

-   `def parse_arguments() -> argparse.Namespace`

    -   Creates ArgumentParser for CLI
    -   Defines arguments:
        -   `--task-file`: Task file path (default from config)
        -   `--models`: Comma-separated model list or "all"
        -   `--task-limit`: Limit number of tasks (for testing)
        -   `--output`: Output file path
        -   `--enable-fuzzy`: Enable fuzzy descriptions
        -   `--disable-concrete-ref`: Disable concrete references
        -   `--judge-stability`: Enable judge stability testing
        -   `--no-cache`: Disable caching
    -   Parses and returns arguments

-   `def _parse_and_validate_args() -> argparse.Namespace`

    -   Calls `parse_arguments()`
    -   Validates argument combinations
    -   Checks file paths exist
    -   Returns validated args

-   `def _create_runner_and_get_models(args: argparse.Namespace) -> tuple[BenchmarkRunner, list[str]]`

    -   Creates LLMFactory and loads model configs
    -   Determines selected models via `_determine_selected_models()`
    -   Creates TaskExecutor, TaskEvaluator instances
    -   Instantiates BenchmarkRunner with dependencies
    -   Returns (runner, selected_models) tuple

-   `def _determine_selected_models(args: argparse.Namespace, available_models: dict) -> list[str]`

    -   Parses --models argument
    -   If "all", returns all available model names
    -   Otherwise splits comma-separated list
    -   Validates each model exists in available_models
    -   Returns list of model names to run

-   `def _print_configuration(args: argparse.Namespace, selected_models: list[str], total_tasks: int)`

    -   Prints formatted benchmark configuration summary
    -   Shows: selected models, task count, fuzzy flag, cache status
    -   Used for user confirmation before execution

-   `async def main()`
    -   Async entry point for benchmark execution
    -   Calls `_parse_and_validate_args()`
    -   Calls `_create_runner_and_get_models()`
    -   Calls `_print_configuration()`
    -   Executes `runner.run_benchmark()` with await
    -   Calls `runner.save_results()` if output specified
    -   Prints summary statistics
    -   Handles KeyboardInterrupt for graceful shutdown
    -   Handles exceptions with logging and exit codes

---

### `benchmark/evaluation/evaluator.py`

**Purpose**: Comprehensive task evaluation with LLM-as-judge and accuracy metrics.

**Helper Functions**:

-   `def safe_get(item: Any, key: str, default: Any = None) -> Any`
    -   Safely retrieves value from dictionary/object
    -   Returns default if key doesn't exist or item is None
    -   Prevents KeyError/AttributeError in evaluation code
    -   Used throughout evaluators for robust data access

**Protocol: `LLMProvider`**

**Purpose**: Type definition for LLM provider contract used by evaluators.

**Methods**:

-   `async def get_completion(self, system_prompt: str, user_prompt: str, max_tokens: int, return_usage: bool = False) -> Union[str, tuple[str, dict]]`

    -   Protocol method signature for LLM completions
    -   Must return string response or (response, usage) tuple

-   `def clean_and_parse_json(self, text: str) -> Any`
    -   Protocol method signature for JSON parsing
    -   Must handle malformed JSON gracefully

**Class: `BaseEvaluator(ABC)`**

**Purpose**: Abstract base class defining evaluator interface.

**Methods**:

-   `__init__(self, llm_provider: LLMProvider)`

    -   Accepts LLM provider for evaluation
    -   Stores provider reference

-   `@abstractmethod async def evaluate(self, task: dict, execution_results: list[dict], final_solution: str, **kwargs) -> dict`
    -   Abstract method defining evaluation contract
    -   Subclasses must implement task-specific evaluation logic
    -   Returns evaluation dict with scores and metrics

**Class: `LLMJudge`**

**Purpose**: LLM-as-judge evaluator with 6-dimension scoring system and optional stability testing.

**Evaluation Dimensions**:

1. **task_fulfillment** (0-100): Degree to which task requirements met
2. **grounding** (0-100): Accuracy of information and tool outputs
3. **tool_appropriateness** (0-100): Selection of correct tools for task
4. **parameter_accuracy** (0-100): Correctness of tool parameters
5. **dependency_awareness** (0-100): Respect for tool execution dependencies
6. **parallelism_efficiency** (0-100): Optimal use of parallel execution

**Methods**:

-   `__init__(self, llm_provider: LLMProvider, enable_judge_stability: bool = False)`

    -   Stores LLM provider for evaluation calls
    -   Sets judge stability flag
    -   If stability enabled, runs 5 evaluations and averages for consensus
    -   Initializes internal state for tracking evaluations

-   `async def evaluate_task_performance(self, task: dict, final_solution: str, execution_results: list[dict], total_rounds: int, available_tools: dict, accumulated_information: str) -> dict`

    -   Main evaluation orchestration method
    -   Creates execution summary via `_create_execution_summary()`
    -   If enable_judge_stability=True:
        -   Runs `_perform_evaluation()` 5 times
        -   Collects all evaluation scores
        -   Calls `_calculate_average_scores()` for consensus
    -   If enable_judge_stability=False:
        -   Runs single `_perform_evaluation()`
    -   Returns evaluation dict with 6-dimension scores, reasoning, metadata

-   `async def _perform_evaluation(self, task: dict, final_solution: str, execution_summary: str, available_tools: dict) -> dict`

    -   Executes single evaluation pass
    -   Generates evaluation prompt via `_generate_randomized_prompt()`
    -   Calls llm_provider.get_completion() for evaluation
    -   Parses JSON response with score dimensions
    -   Validates score ranges (0-100 for each dimension)
    -   On token limit error, compresses content via `compress_for_judge()`
    -   On JSON parse error, retries with format hints
    -   Returns structured evaluation dict

-   `def _generate_randomized_prompt(self, task: dict, final_solution: str, execution_summary: str, available_tools: dict) -> str`

    -   Constructs evaluation prompt with task context
    -   **Randomizes dimension order** to reduce positional bias
    -   Formats available tools via `_format_available_tools()`
    -   Includes execution history and final solution
    -   Specifies JSON response schema with 6 dimensions
    -   Provides scoring guidelines (0=fail, 50=partial, 100=perfect)
    -   Returns complete evaluation prompt string

-   `def _format_available_tools(self, available_tools: dict) -> str`

    -   Formats tool schemas for evaluation prompt
    -   Lists tool names with parameters and descriptions
    -   Creates human-readable tool documentation
    -   Returns formatted string for prompt inclusion

-   `def _calculate_average_scores(self, evaluations: list[dict]) -> dict`

    -   Averages scores across multiple evaluation runs
    -   For each dimension, calculates mean score
    -   Calculates standard deviation for consensus measurement
    -   Identifies outlier evaluations
    -   Returns averaged evaluation dict with consensus metrics

-   `async def compress_for_judge(self, content: str, target_tokens: int, retry_attempt: int = 0) -> str`

    -   Compresses accumulated information for evaluation
    -   Calls LLM to intelligently summarize content
    -   Target token count based on config (default 4000)
    -   On failure, retries up to max_compression_retries
    -   Falls back to rule-based compression if LLM fails
    -   Returns compressed content string

-   `def _summarize_content(self, content: str, max_tokens: int) -> str`

    -   LLM-based content summarization
    -   Preserves key information and structure
    -   Returns summarized text within token limit

-   `def _fallback_rule_based_compression(self, text: str, max_tokens: int) -> str`

    -   Rule-based compression when LLM unavailable
    -   Estimates tokens via `_estimate_token_count()`
    -   Truncates preserving structure (complete sentences)
    -   Returns compressed text

-   `def _estimate_token_count(self, text: str) -> int`

    -   Rough token estimation: len(text) / 4
    -   Used for compression threshold checks
    -   Returns estimated token count

-   `def _is_token_limit_error(self, error_message: str) -> bool`

    -   Detects token limit errors for retry logic
    -   Checks for: "token limit", "context length", "too long"
    -   Returns boolean

-   `def _create_execution_summary(self, execution_results: list[dict], total_rounds: int, accumulated_info: str) -> str`
    -   Formats execution history for evaluation
    -   Includes round-by-round tool call breakdown
    -   Shows parameters, results, timing
    -   Appends accumulated information
    -   Returns formatted execution summary string

**Class: `TaskEvaluator(BaseEvaluator)`**

**Purpose**: Comprehensive evaluator combining LLM judge with accuracy metrics.

**Methods**:

-   `__init__(self, llm_provider: LLMProvider, enable_judge_stability: bool = False)`

    -   Creates LLMJudge instance with provided config
    -   Stores stability flag
    -   Initializes metric tracking structures

-   `async def evaluate(self, task: dict, execution_results: list[dict], final_solution: str, total_rounds: int, available_tools: dict, planning_json_compliance: float, accumulated_information: str) -> dict`

    -   Main evaluation method combining multiple evaluation sources
    -   Calls `llm_judge.evaluate_task_performance()` for 6-dimension scores
    -   Calls `_calculate_tool_accuracy_metrics()` for objective metrics
    -   Calls `_calculate_server_utilization_metrics()` for resource usage
    -   Combines all metrics into comprehensive evaluation dict:
        -   LLM judge scores (6 dimensions)
        -   Tool accuracy (schema compliance, success rate)
        -   Planning accuracy (JSON compliance, correct tool selection)
        -   Server utilization (tools used vs available)
        -   Execution performance (rounds, timing)
    -   Returns complete evaluation dict

-   `def _calculate_tool_accuracy_metrics(self, execution_results: list[dict], available_tools: dict, planning_json_compliance: float) -> dict`

    -   Analyzes tool execution for accuracy metrics
    -   For each tool call in execution_results:
        -   Checks if tool_name in available_tools (correct tool selection)
        -   Calls `_check_schema_compliance()` for parameter validation
        -   Tracks execution success vs errors
    -   Calculates metrics:
        -   `correct_tool_rate`: % of valid tool names
        -   `schema_compliance_rate`: % of calls with valid parameters
        -   `execution_success_rate`: % of successful executions
        -   `planning_json_compliance`: from planning phase
    -   Returns tool accuracy metrics dict

-   `def _check_schema_compliance(self, tool_name: str, parameters: dict, tool_schema: dict) -> bool`

    -   Validates tool call parameters against JSON schema
    -   Uses jsonschema library for validation
    -   Checks required fields present
    -   Checks parameter types match schema
    -   Checks parameter constraints (min, max, enum, etc.)
    -   Returns True if compliant, False otherwise

-   `def _calculate_server_utilization_metrics(self, execution_results: list[dict], available_tools: dict, task: dict) -> dict`
    -   Analyzes server and tool utilization
    -   Counts unique servers accessed
    -   Counts unique tools used vs available
    -   Compares against expected_tool_calls from task
    -   Calculates:
        -   `tools_used_count`: Number of unique tools called
        -   `tools_available_count`: Total available tools
        -   `server_utilization_rate`: % of servers used
        -   `expected_tools_match`: Alignment with task expectations
    -   Returns utilization metrics dict

---

### `benchmark/evaluation/graders.py`

**Purpose**: Reusable grading helper functions.

**Functions**:

-   `def exact_match(response: str, ground_truth: str) -> bool`

    -   Compares normalized strings
    -   Returns True if exact match

-   `def regex_match(response: str, pattern: str) -> bool`

    -   Tests response against regex pattern
    -   Returns True if matches

-   `def json_schema_match(response: str, schema: dict) -> bool`

    -   Parses JSON response
    -   Validates against JSON schema
    -   Returns True if valid

-   `def numeric_tolerance_match(response: str, ground_truth: str, tolerance: float = 0.01) -> bool`

    -   Extracts numeric values
    -   Compares with tolerance
    -   Returns True if within tolerance

-   `def substring_match(response: str, ground_truth: str, case_sensitive: bool = False) -> bool`

    -   Checks if ground_truth substring in response
    -   Returns True if found

-   `def llm_similarity_match(response: str, ground_truth: str, threshold: float = 0.8, llm_provider: LLMProvider = None) -> bool`
    -   Uses LLM to judge semantic similarity
    -   Returns True if similarity above threshold

---

### `visualizer/aggregator.py`

**Purpose**: Results aggregation and statistical calculation for benchmark analysis.

**Class: `ResultsAggregator`**

**Methods**:

-   `__init__(self)`

    -   Initializes aggregator state
    -   Sets up tracking structures for cumulative metrics
    -   Initializes validation rules

-   `def aggregate_model_results(self, results: list[dict]) -> dict`

    -   Groups results by model name via `group_by_model()`
    -   For each model, calculates aggregate statistics:
        -   Total tasks executed
        -   Pass rate (tasks with passing scores)
        -   Mean, median, stddev of scores
        -   Percentiles (25th, 50th, 75th, 90th, 95th)
        -   LLM judge dimension averages (6 dimensions)
        -   Tool accuracy averages
        -   Execution time statistics
        -   Token usage totals and averages
    -   Returns dict mapping model → aggregated_stats

-   `def aggregate_current_metrics(self, results: list[dict]) -> dict`

    -   Calculates current state metrics during execution
    -   Used for progress reporting and live updates
    -   Computes running statistics without full aggregation
    -   Returns current metrics dict

-   `def update_cumulative_metrics(self, current_metrics: dict, new_result: dict) -> dict`

    -   Incrementally updates running statistics with new result
    -   Efficient online algorithm avoiding recomputation
    -   Updates: count, sum, sum_of_squares for mean/variance
    -   Used for streaming aggregation during benchmark execution
    -   Returns updated cumulative metrics dict

-   `def calculate_current_metrics(self, completed_results: list[dict], total_results: int) -> dict`

    -   Computes current state metrics for progress display
    -   Calculates completion percentage
    -   Computes pass rate from completed tasks
    -   Calculates mean score across completed tasks
    -   Estimates time remaining based on current pace
    -   Returns comprehensive current metrics dict

-   `def _get_empty_model_summary(self, total_results: int) -> dict`

    -   Returns template for model summary with zero-initialized metrics
    -   Used for initializing new model tracking
    -   Includes all metric fields with default values

-   `def _get_empty_current_metrics(self) -> dict`

    -   Returns template for current metrics
    -   Zero-initialized counters and statistics
    -   Used for initialization before first result

-   `def _validate_llm_judge_fields(self, evaluation: dict, idx: int)`

    -   Validates LLM judge evaluation structure
    -   Checks presence of all 6 dimensions:
        -   task_fulfillment, grounding
        -   tool_appropriateness, parameter_accuracy
        -   dependency_awareness, parallelism_efficiency
    -   Validates score ranges (0-100)
    -   Raises ValueError with detailed error message if validation fails
    -   Includes result index (idx) in error for debugging

-   `def _validate_accuracy_fields(self, evaluation: dict, idx: int)`

    -   Validates accuracy metrics structure
    -   Checks for required fields:
        -   correct_tool_rate, schema_compliance_rate
        -   execution_success_rate, planning_json_compliance
    -   Validates metric ranges (0.0-1.0)
    -   Raises ValueError if fields missing or out of range

-   `def _validate_performance_fields(self, result: dict, idx: int)`

    -   Validates performance metrics structure
    -   Checks for execution_time, token_usage fields
    -   Validates numeric types and positive values
    -   Raises ValueError if invalid

-   `def _validate_execution_results(self, result: dict, idx: int)`

    -   Validates execution results structure
    -   Checks for tool_calls, execution_history arrays
    -   Validates round count and status
    -   Ensures required fields present
    -   Raises ValueError with context if invalid

-   `def _validate_current_metrics_fields(self, evaluation: dict)`

    -   Validates current metrics structure for consistency
    -   Ensures all expected fields present
    -   Checks field types match expected
    -   Used during metric updates

-   `def aggregate_files(self, file_paths: list[str]) -> dict`

    -   Loads results from multiple JSON files
    -   Combines results from different benchmark runs
    -   Calls `aggregate_model_results()` on combined data
    -   Useful for multi-run analysis and comparison
    -   Returns aggregated dict spanning all files

-   `def calculate_summary_stats(self, results: list[dict]) -> dict`

    -   Computes comprehensive summary statistics
    -   Calculates: mean, median, mode, stddev
    -   Computes percentiles (5th, 25th, 50th, 75th, 95th)
    -   Identifies min and max values with task IDs
    -   Returns detailed statistics dict

-   `def group_by_model(self, results: list[dict]) -> dict`
    -   Groups results by model_name field
    -   Creates dict mapping model → list[results]
    -   Handles missing model_name gracefully
    -   Used as first step in aggregation pipeline

---

### `visualizer/formatter.py`

**Purpose**: Output formatting and display for benchmark results.

**Class: `ResultsFormatter`**

**Methods**:

-   `__init__(self)`

    -   Initializes formatter instance
    -   Tracks last cumulative metrics for diff display
    -   Sets up formatting configurations (colors, widths, precision)

-   `def format_current_metrics(self, model_name: str, completed: int, total: int, metrics: dict, task_file: str)`

    -   Formats and displays current progress metrics during execution
    -   Shows completion percentage: "Progress: [completed/total] (XX%)"
    -   Displays running statistics:
        -   Pass rate: % of tasks passing threshold
        -   Mean score: Average across completed tasks
        -   Current task file being processed
    -   Calculates and shows diff from last update:
        -   Tasks completed since last call
        -   Score change (↑/↓ indicators)
    -   Pretty-prints to console with ANSI colors and formatting
    -   Updates last_metrics for next diff calculation

-   `def format_single_task_report(self, task_id: str, evaluation: dict, dependency_structures: dict)`

    -   Formats detailed single task result report
    -   Sections:
        -   **Task Header**: task_id, model, execution time
        -   **LLM Judge Scores**: 6-dimension breakdown with percentages
        -   **Tool Accuracy**: schema compliance, success rates
        -   **Execution Details**: rounds, tool calls, timing
        -   **Dependency Analysis**: from dependency_structures dict
    -   Returns formatted multi-line string suitable for logging or file output

-   `def to_markdown_table(self, aggregated_results: dict) -> str`

    -   Converts aggregated results to Markdown table format
    -   Columns: Model | Pass Rate | Mean Score | Median | Stddev | Exec Time
    -   Additional columns for each LLM judge dimension
    -   Sorts models by mean score descending
    -   Formats percentages, scores, times with appropriate precision
    -   Returns complete Markdown table string

-   `def to_csv(self, aggregated_results: dict, output_path: str)`

    -   Exports aggregated results to CSV file
    -   Headers: model_name, pass_rate, mean_score, median_score, stddev, exec_time_avg, task_count, [6 LLM judge dimensions], [4 accuracy metrics]
    -   Writes one row per model
    -   Handles nested dicts flattening
    -   Saves to output_path
    -   Used for data analysis in spreadsheets/BI tools

-   `def to_json(self, aggregated_results: dict, output_path: str)`

    -   Exports aggregated results to JSON file
    -   Pretty-prints with indent=2 for readability
    -   Preserves full nested structure
    -   Saves to output_path
    -   Includes metadata: timestamp, config snapshot
    -   Used for programmatic analysis and archiving

-   `def _format_score(self, score: float, precision: int = 2) -> str`

    -   Formats score with specified decimal precision
    -   Handles None values gracefully
    -   Returns formatted string

-   `def _format_percentage(self, value: float) -> str`

    -   Formats value as percentage (0-100%)
    -   Handles 0.0-1.0 range conversion
    -   Returns formatted string with % symbol

-   `def _format_duration(self, seconds: float) -> str`

    -   Formats execution time duration
    -   Converts to appropriate units (ms, s, m, h)
    -   Returns human-readable duration string

-   `def _calculate_diff(self, current: dict, previous: dict) -> dict`
    -   Calculates difference between current and previous metrics
    -   Used for progress change indicators
    -   Returns diff dict with deltas

**Function: `execution_results_to_text`**

-   `def execution_results_to_text(execution_results: list[dict]) -> str`
    -   Converts execution results to human-readable text format
    -   Formats each round of execution:
        -   Round number
        -   Tool calls with parameters
        -   Tool responses
        -   Errors if any
        -   Timing information
    -   Shows complete execution narrative
    -   Returns multi-line formatted string
    -   Used in evaluation prompts and debugging output

---

### `visualizer/graph.py`

**Purpose**: Visualization generation with matplotlib/plotly.

**Class: `GraphGenerator`**

**Methods**:

-   `__init__(self)`

    -   Initializes graph generator
    -   Sets up matplotlib/plotly configuration

-   `def plot_model_comparison(self, data: dict, metric: str, output_path: str)`

    -   Creates bar chart comparing models on specified metric
    -   Adds labels and legend
    -   Saves to output_path

-   `def plot_score_distribution(self, data: dict, model_name: str, output_path: str)`

    -   Creates histogram of score distribution for model
    -   Shows mean and median lines
    -   Saves to output_path

-   `def plot_timeline(self, data: dict, output_path: str)`
    -   Creates timeline of performance over benchmark run
    -   Shows trends across tasks
    -   Saves to output_path

---

### `features/tools.py`

**Purpose**: Tool registry and tool protocol for agentic execution.

**Protocol: `Tool`**

**Attributes**:

-   `name: str` - Unique tool identifier
-   `description: str` - Natural language description for LLM
-   `parameters: dict` - JSON Schema for input parameters

**Methods**:

-   `async def execute(self, **kwargs) -> Any`

    -   Abstract method - subclasses implement tool logic
    -   Receives parameters validated against JSON schema
    -   Returns execution result (any JSON-serializable type)
    -   Should handle errors gracefully, returning error dict

-   `def to_json_schema(self) -> dict`
    -   Converts tool definition to OpenAI function calling format
    -   Used in planning prompts for LLM
    -   Returns schema dict with name, description, parameters

**Example Tool Implementation**:

```python
class CalculatorTool(Tool):
    name = "calculator"
    description = "Performs arithmetic calculations"
    parameters = {
        "expression": {"type": "string", "description": "Math expression to evaluate"}
    }

    async def execute(self, expression: str) -> dict:
        try:
            result = eval(expression)  # In production, use safe_eval
            return {"result": result, "expression": expression}
        except Exception as e:
            return {"error": str(e), "expression": expression}
```

**Class: `ToolRegistry`**

**Purpose**: Thread-safe registry for tool management in agentic executors.

**Methods**:

-   `__init__(self)`

    -   Initializes empty registry
    -   Creates threading.Lock for thread safety
    -   Stores tools in dict: {tool_name: Tool}

-   `def register(self, tool: Tool) -> None`

    -   Adds tool to registry with thread-safe lock
    -   Validates tool name is unique
    -   Raises ValueError if duplicate name
    -   Thread-safe operation

-   `def get_tool(self, name: str) -> Tool`

    -   Retrieves tool by name with lock
    -   Raises KeyError if not found
    -   Returns Tool instance
    -   Thread-safe read

-   `def get_all_schemas(self) -> list[dict]`

    -   Returns all registered tool schemas
    -   Used for building planning prompts
    -   Returns list of schema dicts
    -   Thread-safe operation

-   `def list_tools(self) -> list[str]`
    -   Returns list of registered tool names
    -   Used for debugging and logging
    -   Thread-safe operation

**Usage Pattern in Benchmarks**:

```python
# In benchmark initialization
registry = ToolRegistry()
registry.register(CalculatorTool())
registry.register(SearchTool())
registry.register(DatabaseTool())

# Pass to agentic executor
benchmark = MyBenchmark(
    executor_class=AgenticExecutor,
    executor_kwargs={"tool_registry": registry}
)
```

---

### `utils/error_handler.py`

**Purpose**: Centralized error handling patterns.

**Decorator: `handle_errors`**

-   `def handle_errors(log_level: str = "ERROR", reraise: bool = True)`
    -   Function decorator for error handling
    -   Wraps function with try-except
    -   Logs exceptions via `log_exception()`
    -   Re-raises if reraise=True
    -   Returns decorator function

**Class: `ErrorContext`**

**Methods**:

-   `__init__(self, context_name: str, log_level: str = "ERROR")`

    -   Initializes error context manager
    -   Stores context name for logging

-   `def __enter__(self)`

    -   Context manager entry
    -   Returns self

-   `def __exit__(self, exc_type, exc_val, exc_tb)`
    -   Context manager exit
    -   Logs exception if occurred via `log_exception()`
    -   Returns False (doesn't suppress exceptions)

**Function: `log_exception`**

-   `def log_exception(exception: Exception, context: str, log_level: str = "ERROR")`
    -   Centralized exception logging
    -   Formats exception with traceback
    -   Logs with specified level
    -   Includes context information

---

### `main.py`

**Purpose**: CLI entry point for running benchmarks.

**Functions**:

-   `def parse_arguments() -> argparse.Namespace`

    -   Creates argument parser
    -   Defines CLI flags:
        -   `--benchmark`: Benchmark name to run
        -   `--config`: Custom config file path
        -   `--questions`: Custom questions file path
        -   `--models`: Comma-separated model list or "all"
        -   `--output`: Output file path
        -   `--verbose`: Enable verbose logging
        -   `--list-models`: List available models
        -   Feature toggles: `--disable-fuzzy`, `--enable-cache`, etc.
    -   Parses and returns arguments

-   `def _resolve_benchmark_module(benchmark_name: str)`

    -   Dynamically imports benchmark module from tests/
    -   Returns benchmark class
    -   Raises ImportError if not found

-   `def _list_available_models()`

    -   Calls LLMFactory.get_model_configs()
    -   Prints formatted model list
    -   Shows provider and configuration

-   `async def _run_benchmark_async(args: argparse.Namespace) -> BenchmarkOutput`

    -   Resolves benchmark module
    -   Loads configuration
    -   Applies CLI overrides
    -   Instantiates benchmark class
    -   Calls benchmark.run()
    -   Returns BenchmarkOutput

-   `def main()`
    -   Entry point function
    -   Parses arguments
    -   Handles --list-models flag
    -   Runs async benchmark via asyncio.run()
    -   Saves output if --output specified
    -   Prints summary statistics
    -   Handles exceptions and exits with appropriate code

---

## Execution Flow Diagrams

### Simple Execution Flow

```
CLI: main.py
    ↓
parse_arguments()
    ↓
_resolve_benchmark_module()
    ↓
Benchmark.__init__()
    ├── load_config() → BenchmarkRunConfig
    ├── load tasks → list[Task]
    └── SimpleExecutor(models)
    ↓
Benchmark.run()
    ↓
For each task:
    ├── SimpleExecutor.execute_task(task)
    │   ├── For each model:
    │   │   ├── LLMProvider.get_completion(messages)
    │   │   └── Return TaskResult
    │   └── Return list[TaskResult]
    ├── For each TaskResult:
    │   └── Benchmark.grade(result, task) → Grade
    └── Aggregate into BenchmarkOutput
    ↓
Save results
Print summary
```

### Agentic Execution Flow

```
CLI: main.py
    ↓
Benchmark.__init__(executor_class=AgenticExecutor)
    ├── load_config()
    ├── load tasks
    ├── ToolRegistry.register(tools)
    └── AgenticExecutor(models, tool_registry)
    ↓
Benchmark.run()
    ↓
For each task:
    ├── AgenticExecutor.execute_task(task)
    │   ├── For each model:
    │   │   ├── Create ExecutionContext
    │   │   ├── Initialize accumulated_info
    │   │   └── Planning Loop (max 10 rounds):
    │   │       ├── _plan_next_actions()
    │   │       │   ├── _build_planning_prompt()
    │   │       │   ├── LLMProvider.get_completion()
    │   │       │   ├── Parse JSON plan
    │   │       │   └── Handle errors (compress/reduce/fix)
    │   │       ├── _execute_planned_tools()
    │   │       │   ├── Identify sequential/parallel tools
    │   │       │   ├── Execute tools via ToolRegistry
    │   │       │   └── Collect results
    │   │       ├── _update_state()
    │   │       │   ├── Append results to accumulated_info
    │   │       │   ├── Check threshold
    │   │       │   └── Compress if needed
    │   │       └── Check completion
    │   │   ├── _synthesize_final_solution()
    │   │   │   └── LLMProvider.get_completion()
    │   │   └── Return TaskResult with execution_results
    │   └── Return list[TaskResult]
    ├── Optional: TaskEvaluator.evaluate()
    │   ├── LLMJudge.evaluate_task_performance()
    │   │   ├── _perform_evaluation() x3 (if stability)
    │   │   └── _calculate_average_scores()
    │   └── _calculate_tool_accuracy_metrics()
    ├── Benchmark.grade(result, task) → Grade
    └── Aggregate into BenchmarkOutput
```

### Configuration Loading Flow

```
Benchmark.__init__()
    ↓
config.loader.load_config(global_source, benchmark_source)
    ├── Load global_config.yaml
    │   └── Parse YAML → dict
    ├── Load benchmark config.yaml
    │   └── Parse YAML → dict
    ├── Deep merge (benchmark overrides global)
    ├── BenchmarkConfig._apply_env_overrides()
    │   ├── Scan environment for BENCHMARK_* vars
    │   ├── BenchmarkConfig._convert_env_value()
    │   └── BenchmarkConfig._set_nested_value()
    ├── Validate with Pydantic
    │   └── BenchmarkRunConfig.model_validate()
    └── Return BenchmarkRunConfig
```

---

## Key Design Patterns

### 1. Dependency Injection

Executors and tools are injected, enabling different execution strategies without modifying base classes:

```python
# Simple single-turn execution
benchmark = MyBenchmark(executor_class=SimpleExecutor)

# Multi-round agentic execution
benchmark = MyBenchmark(
    executor_class=AgenticExecutor,
    executor_kwargs={"tool_registry": registry}
)
```

### 2. Strategy Pattern

`Executor` protocol allows interchangeable execution strategies:

```python
class Executor(ABC):
    """All executors implement this protocol."""
    async def execute_task(self, task: Task) -> list[TaskResult]: ...

# Implementations
class SimpleExecutor(Executor): ...  # Single-turn
class AgenticExecutor(Executor): ...  # Multi-round with tools
```

### 3. Factory Pattern

`LLMFactory` centralizes provider instantiation:

```python
# Get all available model configurations
configs = LLMFactory.get_model_configs()

# Create provider for specific model
provider = await LLMFactory.create_llm_provider(configs["gpt-4o"])
```

### 4. Singleton Pattern

`BenchmarkConfig` ensures single configuration instance:

```python
class BenchmarkConfig:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

### 5. Context Manager Pattern

Async context managers for resource management:

```python
# Automatic cleanup
async with ConnectionManager(server_configs) as manager:
    # Use MCP servers
    tools = manager.get_tools()
# Servers automatically shut down
```

### 6. Template Method Pattern

`Benchmark` defines skeleton, subclasses fill in `grade()`:

```python
class Benchmark(ABC):
    async def run(self):  # Template method
        for task in self.tasks:
            result = await self.executor.execute_task(task)
            grade = await self.grade(result, task)  # Hook
            # ...

    @abstractmethod
    async def grade(self, result, task):  # Hook to implement
        pass
```

---

## Extension Points & Common Patterns

### 1. Custom Benchmark with Simple Grading

```python
from benchmark.benchmark import Benchmark
from benchmark.models import TaskResult, Task, Grade
from benchmark.evaluation.graders import exact_match, substring_match

class MyBenchmark(Benchmark):
    """Basic Q&A benchmark with exact matching."""

    async def grade(self, result: TaskResult, task: Task) -> Grade:
        response = result.response.strip().lower()
        expected = task.ground_truth.lower()

        if exact_match(response, expected):
            return Grade(score=1.0, passed=True,
                        reasoning="Exact match", grader_name="exact")
        elif substring_match(response, expected):
            return Grade(score=0.5, passed=False,
                        reasoning="Partial match", grader_name="substring")
        else:
            return Grade(score=0.0, passed=False,
                        reasoning="No match", grader_name="exact")

# Usage
benchmark = MyBenchmark()  # Auto-loads tests/my_benchmark/config.yaml
result = await benchmark.run()
```

### 2. Agentic Benchmark with Tools

```python
from benchmark.benchmark import Benchmark
from benchmark.execution.agentic.executor import AgenticExecutor
from features.tools import ToolRegistry, Tool

# Define custom tools
class CalculatorTool(Tool):
    name = "calculator"
    description = "Evaluates mathematical expressions"
    parameters = {"expression": {"type": "string"}}

    async def execute(self, expression: str):
        try:
            return {"result": eval(expression)}  # Use safe_eval in production
        except Exception as e:
            return {"error": str(e)}

class SearchTool(Tool):
    name = "search"
    description = "Searches knowledge base"
    parameters = {"query": {"type": "string"}}

    async def execute(self, query: str):
        # Implementation here
        return {"results": [...]}

# Create benchmark with tools
class AgenticBenchmark(Benchmark):
    def __init__(self):
        registry = ToolRegistry()
        registry.register(CalculatorTool())
        registry.register(SearchTool())

        super().__init__(
            executor_class=AgenticExecutor,
            executor_kwargs={"tool_registry": registry}
        )

    async def grade(self, result: TaskResult, task: Task) -> Grade:
        # Grade based on tool usage and final answer
        correct_tools_used = self._check_tool_usage(result, task)
        answer_correct = result.response == task.ground_truth

        if answer_correct and correct_tools_used:
            return Grade(score=1.0, passed=True,
                        reasoning="Correct with proper tool use",
                        grader_name="tool_aware")
        elif answer_correct:
            return Grade(score=0.7, passed=True,
                        reasoning="Correct but suboptimal tools",
                        grader_name="tool_aware")
        else:
            return Grade(score=0.0, passed=False,
                        reasoning="Incorrect answer",
                        grader_name="tool_aware")
```

### 3. Custom Configuration Override

```python
from benchmark.config.loader import load_config, apply_overrides

# Load and customize
config = load_config(
    global_source="global_config.yaml",
    benchmark_source="tests/my_benchmark/config.yaml"
)

# Apply runtime overrides
config = apply_overrides(config, {
    "execution.timeout": 2000,
    "execution.max_retries": 5,
    "metadata.experiment_id": "exp_001",
    "results.output_dir": "./custom_results"
})

# Use custom config
benchmark = MyBenchmark(config=config)
result = await benchmark.run()
```

### 4. Programmatic Task Manipulation

```python
from benchmark.models import Task, ChatMessage

benchmark = MyBenchmark()

# Filter tasks
benchmark.tasks = [t for t in benchmark.tasks
                   if t.metadata.get("difficulty") == "hard"]

# Add custom task
custom_task = Task(
    id="custom_001",
    messages=[ChatMessage(role="user", content="What is 2+2?")],
    ground_truth="4",
    metadata={"difficulty": "easy", "category": "math"}
)
benchmark.tasks.append(custom_task)

# Run modified benchmark
result = await benchmark.run()
```

### 5. Advanced LLM Judge Integration

```python
from benchmark.benchmark import Benchmark
from benchmark.evaluation.evaluator import TaskEvaluator
from benchmark.execution.llm.factory import LLMFactory

class JudgedBenchmark(Benchmark):
    async def grade(self, result: TaskResult, task: Task) -> Grade:
        # Use LLM judge for subjective grading
        judge_provider = await LLMFactory.create_llm_provider(
            self.config.models[0]  # Use first model as judge
        )

        evaluator = TaskEvaluator(
            llm_provider=judge_provider,
            enable_judge_stability=True  # 5x evaluation for consensus
        )

        # Get comprehensive evaluation
        eval_result = await evaluator.evaluate(
            task=task.__dict__,
            execution_results=result.execution_results or [],
            final_solution=result.response,
            total_rounds=result.total_rounds or 1,
            available_tools=result.available_tools or {},
            planning_json_compliance=1.0,
            accumulated_information=result.accumulated_information or ""
        )

        # Convert to Grade
        avg_score = sum(eval_result.values()) / len(eval_result)
        return Grade(
            score=avg_score / 100,  # Convert 0-100 to 0-1
            passed=avg_score >= 70,
            reasoning=f"LLM Judge: {eval_result}",
            grader_name="llm_judge",
            subdimension_scores=eval_result
        )
```

---

## Testing Strategy

### Unit Tests

Test individual components in isolation:

```python
# Test simple executor
async def test_simple_executor():
    executor = SimpleExecutor(models=[model_config])
    results = await executor.execute_task(task)
    assert len(results) == 1
    assert results[0].model_name == "gpt-4o"
```

### Integration Tests

Test component interactions:

```python
# Test benchmark execution
async def test_benchmark_run():
    benchmark = ExampleBenchmark()
    output = await benchmark.run()
    assert len(output.results) > 0
    assert output.summary["mean_score"] >= 0
```

### End-to-End Tests

Test complete workflows:

```python
# Test CLI execution
def test_cli_execution():
    result = subprocess.run([
        "python", "main.py",
        "--benchmark", "example_benchmark"
    ])
    assert result.returncode == 0
```

---

## Performance Considerations

### Concurrent Execution

-   Simple executor runs models in parallel
-   Agentic executor can parallelize tool calls
-   Use `concurrent_execution: true` in config

### Token Optimization

-   Multi-layered compression strategy
-   Token reduction factors: [0.8, 0.6, 0.4]
-   Fallback rule-based compression

### Caching

-   Optional tool call caching
-   Configurable TTL and size limits
-   Reduces redundant API calls

### Retry Strategy

-   Exponential backoff for transient failures
-   Round-level retries (max 10)
-   Task-level retries (max 3)
-   Token-level strategies (compression, reduction)

---

## Security Considerations

### API Key Management

-   Store keys in `.env` file
-   Never commit secrets to repository
-   Use environment variables for production

### Input Validation

-   Pydantic validation for all models
-   Schema compliance checking
-   Error handling for malformed inputs

### Output Sanitization

-   Truncate error messages
-   Filter sensitive information from logs
-   Validate JSON before parsing
