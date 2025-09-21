# benchmark (package)

This package contains the core implementation of the benchmarking framework. It is intentionally small and focused: the package exposes models, the `Benchmark` base class, executors and providers, and evaluation helpers.

Key modules

-   `models.py` — Pydantic models for Tasks, TaskResult, ModelConfig, Grade and BenchmarkRunConfig.
-   `benchmark.py` — `Benchmark` base class: configuration loading, task loading, executor wiring, orchestration, and persistence hooks.
-   `config/loader.py` — configuration loader, environment overrides and programmatic helpers (`load_config`, `apply_overrides`).
-   `execution/` — executors and LLM provider abstractions. Notable files:
    -   `simple_executor.py` — single-turn completion executor
    -   `agentic/` — agentic execution (planning, tools, context state)
    -   `llm/` — provider factory and concrete provider implementations
-   `evaluation/` — graders and an evaluator orchestration layer.

Quick reference

-   To implement a benchmark: subclass `Benchmark` and implement `async def grade(self, result, task)`.
-   To run programmatically: instantiate your subclass and call `await benchmark.run()` (or wrap in `asyncio.run`).
-   For CLI usage, prefer the repository-level `main.py` which handles discovery of tests and configuration files.

Extension points

-   Executors: create a class that implements the `Executor` protocol found in `execution/base.py`.
-   Providers: add implementations under `execution/llm/providers` and register them via the `LLMFactory`.
-   Tools: extend `features.tools.Tool` and register with a `ToolRegistry` for agentic executions.

See the top-level `docs/` for usage examples and `tests/example_benchmark/` for a minimal working example.
