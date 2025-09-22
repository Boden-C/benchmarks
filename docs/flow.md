This document extracts the runtime execution flow and mode-specific details from the main architecture document.

Primary execution flow

All benchmarks follow a single primary execution path:

1. CLI (`main.py`) or programmatic import instantiates a `Benchmark` subclass.
2. `Benchmark.__init__()` loads and merges configuration (global + benchmark) using `benchmark.config.loader` and loads tasks from a JSONL file.
3. `Benchmark.run()` iterates tasks and delegates execution to an `Executor` instance (default `SimpleExecutor`).
4. Each executor returns one or more `TaskResult` objects for the task (typically one per model).
5. The benchmark's `grade()` method (implemented by user subclasses) scores each `TaskResult` producing a `Grade`.
6. Results are aggregated into a `BenchmarkOutput` and optionally persisted.

Execution modes

-   Simple execution (`benchmark.execution.simple_executor.SimpleExecutor`) performs single-turn chat completions. It typically runs completions for each configured model in parallel and returns a `TaskResult` per model.
-   Agentic execution (`benchmark.execution.agentic.executor.AgenticExecutor`) is a multi-round planner/executor that can call external tools via a `ToolRegistry` and maintains an `ExecutionContext` (see `benchmark.execution.agentic.context`). It supports planning → tool execution → synthesis loops and is intended for complex, tool-augmented tasks.

Flow diagrams (text)

CLI (main.py) or Programmatic Import
↓
Benchmark.**init**()
├── Load & merge configurations
├── Parse tasks from questions.jsonl
└── Initialize executor with LLM providers
↓
Benchmark.run()
├── For each task:
│ ├── Executor.execute_task() → list[TaskResult]
│ └── Benchmark.grade() → Grade
└── Aggregate → BenchmarkOutput
↓
Save results & display summary

Simple Execution (default):

SimpleExecutor.execute_task(task)
├── For each model in parallel:
│ ├── LLMProvider.get_completion(messages)
│ ├── Handle retries & errors
│ └── Return TaskResult
└── Return list[TaskResult] (one per model)

Agentic Execution (tool-using):

AgenticExecutor.execute_task(task)
├── For each model:
│ ├── Create ExecutionContext
│ └── Multi-round loop (max 10 rounds):
│ ├── Plan: LLM decides next tool calls (JSON)
│ ├── Execute: Run tools (sequential/parallel)
│ ├── Update: Append results, compress if needed
│ └── Check: Complete or continue?
│ ├── Synthesize final answer
│ └── Return TaskResult with execution history
└── Return list[TaskResult]

Notes

-   Keep `flow.md` focused on run-time behavior and the sequence of operations. Implementation details and data model specifications remain in `architecture.md`.
-   If you update execution semantics in code, update both `docs/flow.md` and the corresponding sections in `docs/architecture.md` to keep them synchronized.
