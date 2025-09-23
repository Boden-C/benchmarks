# Design

This document outlines the conceptual design of the benchmark library: guiding principles, patterns, extension points, and testing approaches. For component mappings see [`architecture.md`](architecture.md). For runtime execution diagrams see [`flow.md`](flow.md).

## Design Highlights

- Pydantic-backed models provide strong typing and validation of configs, tasks, and outputs.
- Asynchronous I/O underpins executor and provider interactions to keep runs non-blocking.
- Configuration is hierarchical: defaults < global config < benchmark config < environment variables < programmatic overrides.
- Extensibility points are intentionally small, centering on executors, providers, and tools for agentic runs.

## Key Design Patterns

### Dependency Injection

Executors, providers, and tool registries are injected rather than hard-coded, enabling benchmarks to tailor execution strategies:

```python
# Simple single-turn execution
benchmark = MyBenchmark(executor_class=SimpleExecutor)

# Multi-round agentic execution
benchmark = MyBenchmark(
    executor_class=AgenticExecutor,
    executor_kwargs={"tool_registry": registry}
)
```

### Strategy Pattern

The `Executor` protocol exposes a uniform `execute_task` interface. Concrete strategies (simple or agentic) can be swapped without altering benchmark orchestration.

### Factory Pattern

`LLMFactory` centralizes provider instantiation, mapping `ModelConfig` entries to concrete provider classes and handling authentication concerns.

### Singleton Pattern

`BenchmarkConfig` ensures only one configuration instance is active, avoiding repeated parsing or conflicting state during a run.

### Context Manager Pattern

Async context managers encapsulate resource lifecycles (e.g., MCP connections), guaranteeing cleanup even on failure paths.

### Template Method Pattern

`Benchmark.run()` defines the execution skeleton. Subclasses override hooks like `grade()` and optional lifecycle methods to customize behavior without rewriting orchestration.

## Extension Points & Common Patterns

### Custom Benchmark with Simple Grading

```python
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

Demonstrates overriding `grade()` with deterministic graders (e.g., exact/substring matches).

### Agentic Benchmark with Tools

```python
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

Highlights constructing a tool registry, wiring it into an agentic executor, and grading tool usage.

### Custom Configuration Override

```python
config = apply_overrides(config, {
    "execution.timeout": 2000,
    "execution.max_retries": 5,
    "metadata.experiment_id": "exp_001",
    "results.output_dir": "./custom_results"
})
```

Shows programmatic overrides layered atop loaded configuration.

### Programmatic Task Manipulation

```python
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
```

Clarifies how tasks can be filtered or appended before execution.

### Advanced LLM Judge Integration

```python
avg_score = sum(eval_result.values()) / len(eval_result)
return Grade(
    score=avg_score / 100,
    passed=avg_score >= 70,
    reasoning=f"LLM Judge: {eval_result}",
    grader_name="llm_judge",
    subdimension_scores=eval_result
)
```

Demonstrates combining LLM-judge outputs with standard grading.

## Testing Strategy

### Unit Tests

- Validate executors, evaluators, and helper utilities in isolation.
- Mock providers to keep tests deterministic.

### Integration Tests

- Exercise benchmark execution end-to-end against synthetic tasks.
- Confirm configuration loading, task execution, and grading interplay.

### End-to-End Tests

- Validate CLI flows via subprocess or harness-based runs.
- Ensure exit codes, output persistence, and logging behave as expected.

Aligning new work with these strategies keeps the project’s perceived enterprise readiness intact.