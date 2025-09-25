# Architecture

This document describes the core architecture of the benchmark library and maps components to files in the repository. It has been reconciled with the current codebase: the `benchmark/` package is the implementation surface, `visualizer/` provides optional analysis utilities, and `tests/` contains example benchmark suites.

Key components (mapped to files)

-   `benchmark/models.py` — Pydantic models used across the system (Task, ChatMessage, ModelConfig, TaskResult, Grade, BenchmarkRunConfig, BenchmarkOutput). These define the canonical data shapes for tasks, models, execution results and grades.
-   `benchmark/benchmark.py` — The `Benchmark` base class. Responsibilities:

    -   Load & validate configuration using `benchmark.config.loader.load_config`
    -   Load tasks (JSONL) into `Task` models
    -   Instantiate an `Executor` (Simple or Agentic) with providers created from `benchmark.execution.llm.factory`
    -   Orchestrate execution and grading, assemble a `BenchmarkOutput`

-   `benchmark/config/loader.py` — Configuration loader and `BenchmarkConfig` singleton. Provides:

    -   Default values, YAML merging (global + benchmark), environment variable overrides (`BENCHMARK_*`), and Pydantic validation
    -   Public helpers: `load_config()` and `apply_overrides()` for programmatic usage

-   `benchmark/execution/base.py` — Abstract executor protocol (`Executor`) and `ExecutionHook` definitions used by executor implementations.
-   `benchmark/execution/simple_executor.py` — Single-turn executor implementation. Key behaviors:

    -   Invoke LLM providers (through `LLMFactory`) for each model
    -   Normalize responses, extract token usage, handle retries and errors
    -   Return `TaskResult` objects

-   `benchmark/execution/agentic/context.py` — Execution state container used by agentic runs (`ExecutionContext`). Tracks compression, token reduction and round/retry counts.
-   `benchmark/execution/llm/` — Provider abstraction and concrete providers (`openai`, `openrouter`). The factory (`factory.py`) builds provider instances from `ModelConfig` entries.
-   `benchmark/evaluation/` — Grading helpers and orchestrator. `graders.py` exposes multiple deterministic graders (exact, substring, fuzzy, numeric, regex, json_schema) and `evaluator.py` can orchestrate grading across results.

Design notes and decisions

-   Pydantic is used for strong typing and validation of configs/tasks/outputs.
-   Async I/O is used for non-blocking provider calls.
-   The configuration system is hierarchical: defaults < global_config.yaml < benchmark config < environment < programmatic overrides.
-   Extensibility points are intentionally small: new `Executor` subclasses, new `LLMProvider` implementations, and custom `Tool` classes for agentic execution.

If you find any mismatch between this document and the code, follow the code when resolving contradictions: the code defines the true behavior.

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

    #codebase

    This document provides a high-level overview of the benchmark library architecture. For a detailed, component-by-component specification and design rationale, see `./design.md`.

    The implementation lives under the `benchmark/` package. Optional analysis utilities are in `visualizer/` and example suites live in `tests/`.

    Key components

    -   `benchmark/models.py` — Pydantic models used across the system (Task, ChatMessage, ModelConfig, TaskResult, Grade, BenchmarkRunConfig, BenchmarkOutput).
    -   `benchmark/benchmark.py` — The `Benchmark` base class that orchestrates execution and grading.
    -   `benchmark/config/loader.py` — Configuration loader and `BenchmarkConfig` singleton with helpers `load_config()` and `apply_overrides()`.
    -   `benchmark/execution/` — Executors and provider integrations. `simple_executor.py` implements single-turn execution; `agentic/` contains multi-round agentic executors and `llm/` contains provider adapters and the factory.
    -   `benchmark/evaluation/` — Grading helpers and orchestrator; deterministic graders are in `graders.py` and evaluator orchestration is in `evaluator.py`.

    Design highlights

    -   Pydantic is used for strong typing and validation.
    -   Async I/O is used for non-blocking provider calls.
    -   Configuration is hierarchical: defaults < global_config.yaml < benchmark config < environment < programmatic overrides.
    -   Extensibility points: add new `Executor` subclasses, LLM provider implementations, or custom `Tool` classes for agentic execution.

    For the full detailed specification and the mapping of methods/files to behavior, open `./design.md`.

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

-   `def _save_results(self, output: BenchmarkOutput) -> None` — Internal helper that writes results when `config.results.save_intermediate` is enabled.

    -   Serializes benchmark results to JSON file
    -   Creates output directory if doesn't exist (defaults to `tests/<benchmark_name>/results/`)
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
    -   Calls the runner's save helper (e.g. `_save_results`) if `config.results.save_intermediate` is enabled or an explicit output path is provided
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

-   `def load_results_file(self, filepath: str | Path) -> dict`

    -   Loads results from a single JSON file
    -   Parses file and returns dictionary
    -   Used internally by `aggregate_files()`

-   `def aggregate_files(self, filepaths: list[str | Path]) -> list[dict]`

    -   Loads results from multiple JSON files
    -   Extracts results arrays from BenchmarkOutput format
    -   Combines TaskResult and Grade pairs into flat dictionaries
    -   Returns combined list of all results across files

-   `def group_by_model(self, results: list[dict]) -> dict`

    -   Groups results by model_name field
    -   Creates dict mapping model → list[results]
    -   Handles missing model_name gracefully (uses 'unknown')
    -   Used as first step in aggregation pipeline

-   `def group_by_task(self, results: list[dict]) -> dict`

    -   Groups results by task_id field
    -   Creates dict mapping task_id → list[results]
    -   Handles missing task_id gracefully (uses 'unknown')
    -   Used for per-task analysis

-   `def calculate_summary_stats(self, results: list[dict]) -> dict`

    -   Computes comprehensive summary statistics
    -   Calculates: count, mean, median, min, max, stddev
    -   Computes percentiles (25th, 50th, 75th) when count >= 4
    -   Computes percentiles (5th, 90th, 95th) when count >= 20
    -   Returns detailed statistics dict

-   `def aggregate_model_results(self, results: list[dict]) -> dict`

    -   Groups results by model name via `group_by_model()`
    -   For each model, calculates aggregate statistics:
        -   Total tasks executed (count)
        -   Pass rate (tasks with passed=True)
        -   Total passed and failed counts
        -   Mean, median, stddev of scores
        -   Percentiles (when sufficient data)
        -   Average execution time per task
        -   Total execution time
        -   Token usage totals (by token type)
        -   Average tokens per task (by token type)
    -   Returns dict mapping model → aggregated_stats

-   `def aggregate_task_results(self, results: list[dict]) -> dict`

    -   Groups results by task ID via `group_by_task()`
    -   For each task, calculates aggregate statistics:
        -   Summary stats (mean, median, stddev, percentiles)
        -   Pass rate across models
        -   Number of unique models tested
    -   Returns dict mapping task_id → aggregated_stats

-   `def aggregate_current_metrics(self, results: list[dict]) -> dict`

    -   Calculates current state metrics during execution
    -   Used for progress reporting and live updates
    -   Computes: completed count, mean_score, pass_rate
    -   Returns current metrics dict

-   `def compare_runs(self, baseline_results: list[dict], current_results: list[dict]) -> dict`

    -   Compares two benchmark runs and calculates differences
    -   Aggregates both runs using `aggregate_model_results()`
    -   For each model, returns:
        -   baseline statistics
        -   current statistics
        -   delta (mean_score, pass_rate, count)
    -   Handles models present in only one run
    -   Returns comparison dict mapping model → {baseline, current, delta}

---

### `visualizer/formatter.py`

**Purpose**: Output formatting and display for benchmark results.

**Class: `ResultsFormatter`**

**Methods**:

-   `__init__(self)`

    -   Initializes formatter instance
    -   Tracks last_metrics for calculating diff displays
    -   Sets up color_codes for ANSI console formatting
    -   Stores formatting configurations (colors, widths, precision)

-   `def to_markdown_table(self, aggregated_results: dict) -> str`

    -   Converts aggregated results to Markdown table format
    -   Columns: Model | Tasks | Pass Rate | Mean Score | Median | Std Dev | Avg Time (s)
    -   Sorts models alphabetically
    -   Formats scores with 3 decimal precision
    -   Formats percentages as XX.X%
    -   Returns complete Markdown table string

-   `def to_csv(self, aggregated_results: dict, output_path: str | Path)`

    -   Exports aggregated results to CSV file
    -   Headers: model_name, count, pass_rate, mean_score, median_score, stddev, min_score, max_score, avg_execution_time, total_execution_time, total_passed, total_failed
    -   Includes token usage columns if present (total*\* and avg*\* for each token type)
    -   Writes one row per model
    -   Creates parent directories if needed
    -   Uses UTF-8 encoding

-   `def to_json(self, aggregated_results: dict, output_path: str | Path)`

    -   Exports aggregated results to JSON file
    -   Includes timestamp metadata (UTC ISO format)
    -   Pretty-prints with indent=2 for readability
    -   Preserves full nested structure
    -   Creates parent directories if needed
    -   Uses UTF-8 encoding

-   `def format_current_metrics(self, model_name: str, completed: int, total: int, metrics: dict, task_file: Optional[str])`

    -   Formats and displays current progress metrics during execution
    -   Shows:
        -   Model name (bold cyan)
        -   Progress: [completed/total] (percentage)
        -   Pass rate and mean score
        -   Current task file being processed (if provided)
    -   Calculates and shows diff from last update:
        -   Tasks completed since last call
        -   Score change with ↑/↓/→ indicators
        -   Green for positive, red for negative change
    -   Prints to console with ANSI colors and formatting
    -   Updates last_metrics for next diff calculation

-   `def format_summary(self, summary: dict) -> str`

    -   Formats benchmark summary for console output
    -   Displays:
        -   Total tasks, mean score, median score, pass rate
        -   Per-model breakdown (if 'by_model' present)
    -   Uses bold headers and separators
    -   Returns formatted multi-line string

-   `def format_comparison(self, comparison: dict) -> str`

    -   Formats comparison between two runs
    -   For each model shows:
        -   Mean score: baseline → current with delta and indicator
        -   Pass rate: baseline → current with delta and indicator
    -   Uses color coding (green/red) and arrows (↑/↓/→)
    -   Returns formatted multi-line string

-   `def _format_score(self, score: float, precision: int = 3) -> str`

    -   Formats score with specified decimal precision
    -   Handles None values gracefully (returns "N/A")
    -   Returns formatted string

-   `def _format_percentage(self, value: float) -> str`

    -   Formats value as percentage (0.0-1.0 → XX.X%)
    -   Handles None values gracefully (returns "N/A")
    -   Returns formatted string with % symbol

-   `def _format_duration(self, seconds: float) -> str`

    -   Formats execution time duration
    -   Converts to appropriate units:
        -   < 1s: milliseconds (ms)
        -   < 60s: seconds (s)
        -   < 3600s: minutes (m)
        -   > = 3600s: hours (h)
    -   Returns human-readable duration string

**Function: `execution_results_to_text`**

-   `def execution_results_to_text(execution_results: list[dict]) -> str`
    -   Converts execution results to human-readable text format
    -   Formats each round of execution:
        -   Round number
        -   Tool calls with parameters
        -   Response (truncated to 100 chars if string)
        -   Execution time
    -   Shows complete execution narrative
    -   Returns multi-line formatted string
    -   Used in debugging and result analysis

---

### `visualizer/graph.py`

**Purpose**: Visualization generation with matplotlib, pandas, and seaborn.

**Note**: Requires optional viz dependencies (`matplotlib`, `pandas`, `seaborn`). Install with `pip install -e ".[viz]"`.

**Class: `GraphGenerator`**

**Methods**:

-   `__init__(self)`

    -   Initializes graph generator
    -   Raises ImportError if visualization dependencies not installed
    -   Sets up seaborn theme (whitegrid)
    -   Initializes color palette (husl, 8 colors)

-   `def plot_model_comparison(self, aggregated_results: dict, metric: str = "mean", output_path: Optional[str | Path] = None, figsize: tuple[int, int] = (12, 6))`

    -   Creates bar chart comparing models on specified metric
    -   Supported metrics: mean, median, pass_rate, stddev, etc.
    -   Adds value labels on top of bars
    -   Handles percentage scaling for rate metrics
    -   Saves to output_path if provided, otherwise displays
    -   Uses 300 DPI for high-quality output

-   `def plot_score_distribution(self, results: dict, model_name: Optional[str] = None, output_path: Optional[str | Path] = None, figsize: tuple[int, int] = (10, 6))`

    -   Creates histogram of score distribution
    -   If model_name provided, plots single model; otherwise plots all models
    -   Uses 20 bins with alpha transparency for overlays
    -   Includes legend for multiple models
    -   Saves to output_path if provided, otherwise displays

-   `def plot_timeline(self, results: list[dict], output_path: Optional[str | Path] = None, figsize: tuple[int, int] = (14, 6))`

    -   Creates line plot showing score progression over tasks
    -   Converts results to pandas DataFrame
    -   Plots separate line for each model
    -   Uses markers for data points
    -   Includes grid for readability
    -   Saves to output_path if provided, otherwise displays

-   `def plot_heatmap(self, task_results: dict, output_path: Optional[str | Path] = None, figsize: tuple[int, int] = (12, 8))`

    -   Creates heatmap showing model performance across tasks
    -   Rows: tasks, Columns: models
    -   Color scale: RdYlGn (red-yellow-green) centered at 0.5
    -   Annotates cells with score values
    -   Includes colorbar with 'Score' label
    -   Saves to output_path if provided, otherwise displays

-   `def plot_execution_time_comparison(self, aggregated_results: dict, output_path: Optional[str | Path] = None, figsize: tuple[int, int] = (12, 6))`

    -   Creates dual bar chart comparing execution times
    -   Left panel: average execution time per task
    -   Right panel: total execution time
    -   Adds value labels on bars
    -   Rotates x-axis labels for readability
    -   Saves to output_path if provided, otherwise displays

**Module-level Constants**:

-   `VISUALIZATION_AVAILABLE: bool` - True if viz dependencies installed, False otherwise

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

### `utils/logger.py`

**Purpose**: Centralized logging utilities and custom exceptions.

**Exception Classes**:

-   `BenchmarkError(Exception)` - Base exception for all benchmark errors
-   `ConfigurationError(BenchmarkError)` - Configuration-related errors
-   `ExecutionError(BenchmarkError)` - Task execution errors
-   `EvaluationError(BenchmarkError)` - Result evaluation errors

**Functions**:

-   `handle_error(error: Exception, context: str, reraise: bool = True, default_value: Optional[Any] = None) -> Optional[Any]`

    -   Handles exception with logging and optional re-raising
    -   Logs error via `log_error()` with full context
    -   Re-raises exception if reraise=True
    -   Returns default_value if not re-raising
    -   Used for centralized error handling patterns

-   `log_error(error: Exception, context: str) -> None`

    -   Logs exception with context and full traceback
    -   Formats error type, message, and stack trace
    -   Uses module-level logger for consistent formatting
    -   Used throughout codebase for error logging

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
