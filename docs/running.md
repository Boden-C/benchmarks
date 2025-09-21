# Running Benchmarks

Complete guide for defining, executing, and analyzing benchmarks.

# Running benchmarks (quick reference)

This document provides the practical usage guide for defining, running and analysing benchmarks with this repository. It has been reconciled with the code in `benchmark/` and the CLI implemented in `main.py`.

Quick start

1. Clone the repo and install in editable mode for development:

```powershell
git clone <repository-url>
cd benchmarks
pip install -e .

# optional groups
pip install -e ".[viz]"   # visualization helpers
pip install -e ".[dev]"   # development/test tooling
```

2. Copy `.env.example` to a local `.env` and populate provider keys (if you plan to call external LLM APIs). Example variables in `.env.example` include keys for Azure OpenAI and OpenRouter.

3. Run a benchmark from the repository root:

```powershell
python main.py --benchmark example_benchmark
```

CLI flags and common usage

-   `--benchmark <name>` (required): the benchmark directory name under `tests/` (for example `example_benchmark`).
-   `--config <path>`: optional path to a benchmark config YAML that overrides `tests/<name>/config.yaml`.
-   `--questions <path>`: optional path to the tasks file (JSONL) overriding the configured tasks file.
-   `--models <comma-separated>`: filter the models declared in the benchmark config (or use `all`).
-   `--output <path>`: path to write the results snapshot (JSON) when the run finishes.
-   `--list-models`: prints available models discovered from config and exits.
-   `--verbose`: more verbose logging.

The CLI falls back to `tests/<benchmark>/config.yaml` and the tasks path declared in that config when flags are not provided.

Defining a benchmark

Place a benchmark under `tests/<name>/` with at minimum:

-   `config.yaml` — benchmark configuration (metadata, models list, execution settings, evaluation toggles, results output)
    -- `questions.jsonl` — newline-delimited JSON tasks. Each line should at least include `id`, `messages` (list of chat messages) and `ground_truth`.

        Note: `questions.jsonl` follows OpenRouter-style chat payloads (message objects with `role` and `content` fields). The repo `README.md` and the execution module expect OpenRouter-style chat messages; any model-specific hints in the task payload are ignored and models are selected from the benchmark `config.yaml`.

-   `<name>.py` — optional: a `Benchmark` subclass implementing `async def grade(self, result, task)`.

Example task line (JSONL):

```jsonl
{
    "id": "task_001",
    "messages": [
        {
            "role": "user",
            "content": "What is 2+2?"
        }
    ],
    "ground_truth": "4"
}
```

Configuration system

Configuration is hierarchical and merged in this order (lowest → highest):

1. built-in defaults (in `benchmark.config.loader._get_default_config()`)
2. `global_config.yaml` at the repo root
3. `tests/<benchmark>/config.yaml`
4. environment variables with `BENCHMARK_*` prefix
5. programmatic overrides via `apply_overrides()`

Use `benchmark.config.loader.load_config(global_source, benchmark_source)` to load and validate a merged `BenchmarkRunConfig` instance programmatically. Use `apply_overrides()` to apply runtime changes.

Execution modes

-   SimpleExecutor (default): single-turn chat completion. Fast, parallel per-model execution. Use for Q&A, classification, and simple generation tasks.
-   AgenticExecutor: multi-round planning and tool orchestration (requires `features.tools.ToolRegistry` and registered `Tool` implementations). Use for multi-step problems that benefit from external tools.

Programmatic usage (basic)

```python
import asyncio
from tests.example_benchmark.example_benchmark import ExampleBenchmark

async def run():
    benchmark = ExampleBenchmark()
    output = await benchmark.run()
    print(output.summary)

asyncio.run(run())
```

Programmatic configuration and overrides

```python
from benchmark.config.loader import load_config, apply_overrides

config = load_config("global_config.yaml", "tests/example_benchmark/config.yaml")
config = apply_overrides(config, {"execution": {"timeout": 2000}})

# pass the config into your Benchmark subclass (constructor supports a `config` param)
benchmark = ExampleBenchmark(config=config)
```

Grading and evaluation

The user-provided `Benchmark.grade()` method receives each `TaskResult` and the original `Task`. Use the helpers in `benchmark.evaluation.graders` for common patterns (exact, substring, regex, numeric, JSON). For subjective evaluation, an LLM-based judge is available via `benchmark.evaluation.graders.llm_judge` which uses the configured provider factory.

Saving and analysing results

-   `Benchmark.run()` returns a `BenchmarkOutput` dataclass containing `results`, `summary`, and `metadata`.
    -- When `config.results.save_intermediate` is enabled, `Benchmark.run()` will write snapshots to `config.results.output_dir`.
-   The optional `visualizer/` package provides `aggregator`, `formatter`, and `graph` utilities to merge and visualise run outputs.

Notes & troubleshooting

-   If you find contradictions between docs and implementation, please open an issue or submit a patch; this documentation has been updated to match the current implementation where practical.
-   Don't commit API keys — use `.env` or environment variables for credentials.

If you need a minimal working example, inspect `tests/example_benchmark/` which includes a `config.yaml`, `questions.jsonl`, and an example benchmark implementation.

# Run with custom config

benchmark = MyBenchmark(config=config)
result = await benchmark.run()

````

### Task Manipulation

```python
from benchmark.models import Task, ChatMessage

benchmark = MyBenchmark()

# Filter tasks by difficulty
benchmark.tasks = [
    t for t in benchmark.tasks
    if t.metadata.get("difficulty") == "hard"
]

# Add custom task
new_task = Task(
    id="custom_001",
    messages=[ChatMessage(role="user", content="Custom question?")],
    ground_truth="Expected answer",
    metadata={"difficulty": "medium", "custom": True}
)
benchmark.tasks.append(new_task)

result = await benchmark.run()
````

### Custom Executor Setup

```python
from benchmark.execution.agentic.executor import AgenticExecutor
from features.tools import ToolRegistry, Tool

# Create custom tool
class WebSearchTool(Tool):
    name = "web_search"
    description = "Searches the web"
    parameters = {"query": {"type": "string"}}

    async def execute(self, query: str):
        # Implementation
        return f"Search results for: {query}"

# Register tools
registry = ToolRegistry()
registry.register(WebSearchTool())

# Create executor
executor = AgenticExecutor(
    models=config.models,
    tool_registry=registry,
    concurrent_summarization=True
)

# Use with benchmark
benchmark = MyBenchmark(executor_class=executor)
result = await benchmark.run()
```

---

## Evaluation and Grading

### Built-in Grading Functions

The evaluation module provides several built-in graders in `benchmark.evaluation.graders`:

#### Exact Match

```python
from benchmark.evaluation.graders import exact_match

# Case-insensitive exact match
if exact_match(response, ground_truth, case_sensitive=False):
    return Grade(score=1.0, passed=True, reasoning="Exact match", grader_name="exact_match")
```

#### Substring Match

```python
from benchmark.evaluation.graders import substring_match

# Check if ground truth appears in response
if substring_match(response, ground_truth, min_length=5):
    return Grade(score=1.0, passed=True, reasoning="Substring found", grader_name="substring_match")
```

#### Fuzzy Match

```python
from benchmark.evaluation.graders import fuzzy_match

# Similarity-based matching (80% threshold)
if fuzzy_match(response, ground_truth, threshold=0.8):
    return Grade(score=1.0, passed=True, reasoning="High similarity", grader_name="fuzzy_match")
```

#### Numeric Match

```python
from benchmark.evaluation.graders import numeric_match

# Extract and compare numeric values
if numeric_match(response, 42.0, tolerance=0.01, extract_first=True):
    return Grade(score=1.0, passed=True, reasoning="Numeric match", grader_name="numeric_match")
```

#### Regex Match

```python
from benchmark.evaluation.graders import regex_match
import re

# Pattern-based validation
pattern = r'\b\d{3}-\d{4}\b'  # Phone number format
if regex_match(response, pattern, flags=re.IGNORECASE):
    return Grade(score=1.0, passed=True, reasoning="Pattern matched", grader_name="regex_match")
```

#### JSON Match

```python
from benchmark.evaluation.graders import json_match

# Validate JSON structure
expected_schema = {"status": "success", "count": 5}
if json_match(response, expected_schema, strict=False):
    return Grade(score=1.0, passed=True, reasoning="Valid JSON", grader_name="json_match")
```

### LLM-Based Judging

For subjective or complex evaluations, use the LLM judge:

```python
from benchmark.evaluation.graders import llm_judge
from benchmark.execution.llm.factory import LLMFactory

class SubjectiveBenchmark(Benchmark):
    async def grade(self, result: TaskResult, task: Task) -> Grade:
        # Create judge provider
        judge_config = await LLMFactory.create_llm_provider(
            ModelConfig(name="gpt-4o", provider="azure")
        )

        # Use LLM to judge
        passed, score, reasoning = await llm_judge(
            response=result.response,
            ground_truth=task.ground_truth,
            task_description=task.messages[0].content,
            llm_provider=judge_config,
            criteria="Accuracy, completeness, and clarity"
        )

        return Grade(
            score=score,
            passed=passed,
            reasoning=reasoning,
            grader_name="llm_judge"
        )
```

### Composite Grading

Combine multiple grading strategies:

```python
from benchmark.evaluation.graders import exact_match, substring_match, numeric_match

class CompositeBenchmark(Benchmark):
    async def grade(self, result: TaskResult, task: Task) -> Grade:
        response = result.response
        ground_truth = task.ground_truth

        # Try exact match first
        if exact_match(response, ground_truth):
            return Grade(score=1.0, passed=True,
                        reasoning="Exact match", grader_name="exact_match")

        # Check for numeric answer
        if isinstance(ground_truth, (int, float)):
            if numeric_match(response, ground_truth, tolerance=0.01):
                return Grade(score=1.0, passed=True,
                            reasoning="Numeric match", grader_name="numeric_match")

        # Partial credit for substring
        if substring_match(response, str(ground_truth)):
            return Grade(score=0.5, passed=False,
                        reasoning="Partial match", grader_name="substring_match")

        # No match
        return Grade(score=0.0, passed=False,
                    reasoning="No match", grader_name="composite")
```

### Custom Graders

Create custom grading logic:

```python
from benchmark.evaluation.graders import create_custom_grader

# Define custom validation
def is_valid_email(response: str, ground_truth: Any) -> bool:
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, response.strip()))

# Create grader
email_grader = create_custom_grader(
    grading_function=is_valid_email,
    score_on_pass=1.0,
    score_on_fail=0.0
)

# Use in benchmark
class EmailBenchmark(Benchmark):
    async def grade(self, result: TaskResult, task: Task) -> Grade:
        passed, score = email_grader(result.response, task.ground_truth)
        return Grade(
            score=score,
            passed=passed,
            reasoning="Valid email format" if passed else "Invalid email",
            grader_name="email_validator"
        )
```

### Advanced Evaluation

Configure the evaluator for parallel grading:

```python
from benchmark.evaluation.evaluator import Evaluator

# Create evaluator with custom settings
evaluator = Evaluator(
    grade_function=my_grade_function,
    parallel=True,
    max_concurrent=20
)

# Evaluate results
graded_results = await evaluator.evaluate_results(results, tasks)

# Calculate summary
summary = evaluator.calculate_summary(graded_results)

# Access per-model statistics
for model_name, stats in summary['by_model'].items():
    print(f"{model_name}: {stats['mean_score']:.2f} ({stats['pass_rate']:.1%})")

# Access per-task statistics
for task_id, stats in summary['by_task'].items():
    print(f"{task_id}: {stats['mean_score']:.2f} (difficulty: {stats['pass_rate']:.1%})")
```

---

## Result Analysis

### Aggregation

```python
from visualizer.aggregator import ResultsAggregator

aggregator = ResultsAggregator()

# Aggregate multiple runs
results = aggregator.aggregate_files([
    "results/run_20250101.json",
    "results/run_20250102.json",
    "results/run_20250103.json"
])

# Calculate statistics
stats = aggregator.calculate_summary_stats(results)
model_comparison = aggregator.group_by_model(results)

print(f"Mean score: {stats['mean']:.3f}")
print(f"Median: {stats['median']:.3f}")
print(f"Std dev: {stats['stddev']:.3f}")
```

### Formatting and Export

```python
from visualizer.formatter import ResultsFormatter

formatter = ResultsFormatter()

# Markdown table
markdown = formatter.to_markdown_table(stats)

# Export formats
formatter.to_csv(stats, "results/summary.csv")
formatter.to_json(stats, "results/summary.json")
```

### Visualization

```python
from visualizer.graph import GraphGenerator

grapher = GraphGenerator()
grapher.plot_model_comparison(model_comparison, metric="score", output_path="comparison.png")
grapher.plot_score_distribution(model_comparison, model_name="gpt-4o", output_path="dist.png")
grapher.plot_timeline(results, output_path="timeline.png")
```

---

## Troubleshooting

**Token limit exceeded**: Enable compression with `execution.compression_retries: 2-3` and configure `llm.token_reduction_factors: [0.8, 0.6, 0.4]`

**Authentication errors**: Verify API keys in `.env` file and endpoint URLs

**Timeout errors**: Increase `execution.task_timeout` and `execution.max_retries`

**JSON parsing errors**: Automatic retry with `_fix_invalid_json_format()` handles most cases

**Tool execution failures**: Check tool.execute() error handling and parameter validation

---

## Best Practices

-   Keep sensitive data in `.env`, never in YAML
-   Include deterministic `ground_truth` for automated grading
-   Start with automated graders, use LLM judge for subjective cases
-   Keep tools focused and single-purpose
-   Use concurrent execution for independent tasks
-   Monitor token usage and optimize prompts
-   Use `utils.logger` for consistent error handling and logging
-   Validate configuration early to catch issues before execution

---

## Next Steps

-   Review `architecture.md` for complete system design
-   See `flow.md` for runtime execution flow and mode diagrams
-   Explore `tests/example_benchmark/` for reference implementation
-   Check `global_config.yaml` for available settings
