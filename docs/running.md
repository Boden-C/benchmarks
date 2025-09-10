# Running Benchmarks

Complete guide for defining, executing, and analyzing benchmarks.

---

## Quick Start

### Installation

```powershell
# Clone and install
git clone <repository-url>
cd benchmarks
pip install -e .

# With visualization support
pip install -e ".[viz]"

# With development tools
pip install -e ".[dev]"
```

### Configuration

Copy `.env.example` to `.env`:

```env
# Azure OpenAI
AZURE_OPENAI_API_KEY=your_key_here
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/

# OpenRouter
OPENROUTER_API_KEY=your_key_here

# Other providers
LLAMA_4_MAVERICK_API_KEY=your_key_here
LLAMA_4_MAVERICK_BASE_URL=https://api.example.com/v1
```

### Run Your First Benchmark

```powershell
# Basic execution
python main.py --benchmark example_benchmark

# Specific models
python main.py --benchmark example_benchmark --models gpt-4o,o4-mini

# List available models
python main.py --list-models
```

---

## Defining a Benchmark

### 1. Create Benchmark Directory

```
tests/
└── my_benchmark/
    ├── config.yaml
    ├── questions.jsonl
    └── my_benchmark.py
```

### 2. Define Configuration

Create `tests/my_benchmark/config.yaml`:

```yaml
metadata:
    name: "My Benchmark"
    version: "1.0.0"
    description: "Custom benchmark description"

models:
    - name: "gpt-4o"
      provider: "azure"
    - name: "claude-sonnet-4"
      provider: "openrouter"

execution:
    timeout: 1200
    max_retries: 3
    concurrent_execution: true

evaluation:
    enable_llm_judge: false

results:
    output_dir: "./results"
    save_intermediate: true
```

### 3. Create Tasks

Create `tests/my_benchmark/questions.jsonl`:

```jsonl
{"id": "task_001", "messages": [{"role": "user", "content": "What is 2+2?"}], "ground_truth": "4", "metadata": {"difficulty": "easy"}}
{"id": "task_002", "messages": [{"role": "user", "content": "Explain quantum entanglement"}], "ground_truth": "Quantum entanglement is...", "metadata": {"difficulty": "hard"}}
```

### 4. Implement Benchmark Class

Create `tests/my_benchmark/my_benchmark.py`:

```python
from benchmark.benchmark import Benchmark
from benchmark.models import TaskResult, Task, Grade
from benchmark.evaluation.graders import exact_match, substring_match

class MyBenchmark(Benchmark):
    async def grade(self, result: TaskResult, task: Task) -> Grade:
        response = result.response
        ground_truth = task.ground_truth

        # Exact match grading
        if exact_match(response, ground_truth):
            return Grade(
                score=1.0,
                passed=True,
                reasoning="Exact match with ground truth",
                grader_name="exact_match"
            )

        # Partial credit for substring match
        elif substring_match(response, ground_truth):
            return Grade(
                score=0.5,
                passed=False,
                reasoning="Partial match found",
                grader_name="substring_match"
            )

        # No match
        else:
            return Grade(
                score=0.0,
                passed=False,
                reasoning="No match with ground truth",
                grader_name="exact_match"
            )
```

---

## Execution Modes

### Simple Execution

Single-turn chat completions. Default mode for straightforward Q&A tasks.

**Characteristics**:

-   One prompt, one response per task
-   Parallel execution across models
-   Fast and efficient
-   No tool usage

**Usage**:

```python
from benchmark.execution.simple_executor import SimpleExecutor

benchmark = MyBenchmark(executor_class=SimpleExecutor)
result = await benchmark.run()
```

**When to Use**:

-   Classification tasks
-   Simple Q&A
-   Text generation
-   Summarization

### Agentic Execution

Multi-round planning and tool execution. For complex tasks requiring reasoning and tool use.

**Characteristics**:

-   Planning → Tool Execution → Synthesis loop
-   Up to 10 execution rounds
-   Tool orchestration
-   State management with compression
-   Accumulated context tracking

**Usage**:

```python
from benchmark.execution.agentic.executor import AgenticExecutor
from features.tools import ToolRegistry, Tool

# Register tools
registry = ToolRegistry()
registry.register(SearchTool())
registry.register(CalculatorTool())

# Create benchmark with agentic executor
benchmark = MyBenchmark(
    executor_class=AgenticExecutor,
    tool_registry=registry
)
result = await benchmark.run()
```

**When to Use**:

-   Multi-step problem solving
-   Tasks requiring tool use
-   Complex reasoning
-   Information gathering across sources

---

## Configuration System

### Configuration Hierarchy

Configuration is loaded in this priority order:

1. **Default values** - Defined in `BenchmarkConfig._get_default_config()`
2. **Global config** - `global_config.yaml` at repository root
3. **Benchmark config** - `tests/<benchmark>/config.yaml`
4. **Environment variables** - `BENCHMARK_*` prefix overrides
5. **Programmatic overrides** - Runtime modifications

### Global Configuration

Edit `global_config.yaml` for framework-level defaults:

```yaml
execution:
    task_timeout: 1500
    max_retries: 3
    retry_delay: 2
    max_execution_rounds: 10
    compression_retries: 2

llm:
    planning_tokens: 8000
    summarization_max_tokens: 4000
    evaluation_max_tokens: 8000
    token_reduction_factors: [0.8, 0.6, 0.4]

benchmark:
    enable_judge_stability: false
    concurrent_summarization: false
    use_fuzzy_descriptions: false

cache:
    enabled: false
    ttl_hours: 24
    max_size_mb: 1000
```

### Environment Variable Overrides

Override any configuration with environment variables:

```powershell
# Override task timeout
$env:BENCHMARK_EXECUTION_TASK_TIMEOUT = "2000"

# Override max rounds
$env:BENCHMARK_EXECUTION_MAX_EXECUTION_ROUNDS = "15"

# Enable caching
$env:BENCHMARK_CACHE_ENABLED = "true"

# Run benchmark
python main.py --benchmark my_benchmark
```

### Programmatic Overrides

Modify configuration at runtime:

```python
from benchmark.config.loader import load_config, apply_overrides

# Load base configuration
config = load_config(
    global_source="global_config.yaml",
    benchmark_source="tests/my_benchmark/config.yaml"
)

# Apply overrides
config = apply_overrides(config, {
    "execution.timeout": 2000,
    "metadata.notes": "Custom run",
    "evaluation.enable_llm_judge": True
})

# Create benchmark with custom config
benchmark = MyBenchmark(config=config)
result = await benchmark.run()
```

---

## CLI Usage

### Basic Commands

```powershell
# Run benchmark
python main.py --benchmark <name>

# Custom config
python main.py --benchmark <name> --config path/to/config.yaml

# Custom tasks
python main.py --benchmark <name> --questions path/to/questions.jsonl

# Specific models
python main.py --benchmark <name> --models gpt-4o,claude-sonnet-4

# All models
python main.py --benchmark <name> --models all

# Custom output
python main.py --benchmark <name> --output results/custom.json

# Verbose logging
python main.py --benchmark <name> --verbose
```

### Feature Toggles

```powershell
# Disable features
python main.py --benchmark <name> --disable-fuzzy
python main.py --benchmark <name> --disable-judge-stability
python main.py --benchmark <name> --disable-concurrent-summarization

# Enable caching
python main.py --benchmark <name> --enable-cache
```

### Advanced Examples

```powershell
# Complete custom run
python main.py --benchmark my_benchmark `
  --config custom.yaml `
  --questions custom_tasks.jsonl `
  --models gpt-4o,o4-mini `
  --output results/experiment_001.json `
  --enable-cache `
  --verbose

# List available models
python main.py --list-models
```

---

## Programmatic Usage

### Basic Execution

```python
import asyncio
from tests.my_benchmark.my_benchmark import MyBenchmark

async def run_benchmark():
    benchmark = MyBenchmark()
    result = await benchmark.run()

    print(f"Tasks completed: {len(result.results)}")
    print(f"Mean score: {result.summary['mean_score']:.2f}")
    print(f"Pass rate: {result.summary['pass_rate']:.2%}")

    return result

result = asyncio.run(run_benchmark())
```

### Custom Configuration

```python
from benchmark.config.loader import load_config, apply_overrides
from tests.my_benchmark.my_benchmark import MyBenchmark

# Load and customize config
config = load_config(
    global_source="global_config.yaml",
    benchmark_source="tests/my_benchmark/config.yaml"
)

config = apply_overrides(config, {
    "execution.timeout": 2000,
    "execution.max_retries": 5,
    "metadata.experiment_id": "exp_001"
})

# Run with custom config
benchmark = MyBenchmark(config=config)
result = await benchmark.run()
```

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
```

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

---

## Next Steps

-   Review `architecture.md` for complete system design
-   Explore `tests/example_benchmark/` for reference implementation
-   Check `global_config.yaml` for available settings
