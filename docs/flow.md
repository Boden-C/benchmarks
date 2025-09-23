# Execution Flow

This document captures the primary execution paths and configuration loading lifecycle. For component mappings see [`architecture.md`](architecture.md). For design rationale see [`design.md`](design.md).

## Simple Execution Flow

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

## Agentic Execution Flow

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

## Configuration Loading Flow

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
