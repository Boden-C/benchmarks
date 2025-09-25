# Visualizer

Results processing and visualization utilities for benchmark outputs.

## Overview

The `visualizer/` package provides helper functions and classes for aggregating, formatting, and visualizing benchmark results. These utilities are designed to be used programmatically in Jupyter notebooks or Python scripts to analyze benchmark data.

## Components

### `aggregator.py`

**`ResultsAggregator`** — Loads and aggregates benchmark results from JSON files.

**Key Methods:**

-   `load_results_file(filepath)` — Load single results file
-   `aggregate_files(filepaths)` — Combine results from multiple runs
-   `group_by_model(results)` — Group results by model name
-   `group_by_task(results)` — Group results by task ID
-   `calculate_summary_stats(results)` — Compute mean, median, stddev, percentiles
-   `aggregate_model_results(results)` — Calculate per-model statistics
-   `aggregate_task_results(results)` — Calculate per-task statistics
-   `compare_runs(baseline, current)` — Compare two benchmark runs

### `formatter.py`

**`ResultsFormatter`** — Formats benchmark data for display and export.

**Key Methods:**

-   `to_markdown_table(results)` — Generate Markdown table
-   `to_csv(results, path)` — Export to CSV file
-   `to_json(results, path)` — Export to JSON file
-   `format_summary(summary)` — Format console summary
-   `format_comparison(comparison)` — Format run comparison
-   `format_current_metrics(...)` — Display progress during execution

**Helper Functions:**

-   `execution_results_to_text(results)` — Convert execution results to readable text

### `graph.py`

**`GraphGenerator`** — Generates plots and visualizations.

**Requirements:** Optional `viz` dependencies (`matplotlib`, `pandas`, `seaborn`)

**Key Methods:**

-   `plot_model_comparison(results, metric, output_path)` — Bar chart comparing models
-   `plot_score_distribution(results, model_name, output_path)` — Score histogram/KDE
-   `plot_timeline(results, output_path)` — Timeline showing score progression
-   `plot_heatmap(task_results, output_path)` — Heatmap of model×task performance
-   `plot_execution_time_comparison(results, output_path)` — Execution time comparison

## Installation

Basic usage (aggregation and formatting):

```powershell
pip install -e .
```

With visualization support:

```powershell
pip install -e ".[viz]"
```

## Usage Examples

### Aggregate Multiple Runs

```python
from visualizer import ResultsAggregator

aggregator = ResultsAggregator()

# Load and combine results from default location
results = aggregator.aggregate_files([
    "tests/example_benchmark/results/run_20250101_120000.json",
    "tests/example_benchmark/results/run_20250102_143000.json",
    "tests/example_benchmark/results/run_20250103_091500.json"
])

# Calculate statistics
stats = aggregator.calculate_summary_stats(results)
print(f"Mean: {stats['mean']:.3f}")
print(f"Median: {stats['median']:.3f}")
print(f"Std Dev: {stats['stddev']:.3f}")

# Group by model
by_model = aggregator.aggregate_model_results(results)
for model, metrics in by_model.items():
    print(f"{model}: {metrics['mean']:.3f} ({metrics['pass_rate']:.1%} pass rate)")
```

### Format Results

```python
from visualizer import ResultsFormatter

formatter = ResultsFormatter()

# Markdown table
markdown = formatter.to_markdown_table(by_model)
print(markdown)

# Export to files
formatter.to_csv(by_model, "results/summary.csv")
formatter.to_json(by_model, "results/summary.json")

# Console summary
summary_text = formatter.format_summary({
    'total_tasks': 100,
    'mean_score': 0.85,
    'pass_rate': 0.92,
    'by_model': by_model
})
print(summary_text)
```

### Generate Visualizations

```python
from visualizer import GraphGenerator, GRAPH_AVAILABLE

if not GRAPH_AVAILABLE:
    print("Install viz dependencies: pip install -e '.[viz]'")
else:
    grapher = GraphGenerator()

    # Model comparison
    grapher.plot_model_comparison(
        by_model,
        metric="mean",
        output_path="plots/model_comparison.png"
    )

    # Score distribution
    grouped = aggregator.group_by_model(results)
    grapher.plot_score_distribution(
        grouped,
        model_name="gpt-4o",
        output_path="plots/gpt4o_distribution.png"
    )

    # Timeline
    grapher.plot_timeline(
        results,
        output_path="plots/timeline.png"
    )

    # Execution time comparison
    grapher.plot_execution_time_comparison(
        by_model,
        output_path="plots/execution_times.png"
    )
```

### Compare Benchmark Runs

```python
# Load baseline and current runs
baseline_results = aggregator.aggregate_files(["results/baseline.json"])
current_results = aggregator.aggregate_files(["results/current.json"])

# Compare
comparison = aggregator.compare_runs(baseline_results, current_results)

# Format comparison
comparison_text = formatter.format_comparison(comparison)
print(comparison_text)
```

### Typical Jupyter Notebook Workflow

```python
import sys
from pathlib import Path

# Add project root to path if needed
sys.path.insert(0, str(Path.cwd().parent))

from visualizer import ResultsAggregator, ResultsFormatter, GraphGenerator

# Setup
aggregator = ResultsAggregator()
formatter = ResultsFormatter()
grapher = GraphGenerator()

# Load results from default benchmark location
results_dir = Path("tests/example_benchmark/results")
result_files = list(results_dir.glob("*.json"))
results = aggregator.aggregate_files(result_files)

# Analyze
by_model = aggregator.aggregate_model_results(results)
by_task = aggregator.aggregate_task_results(results)

# Display
print(formatter.to_markdown_table(by_model))

# Visualize
grapher.plot_model_comparison(by_model, metric="mean")
grapher.plot_score_distribution(aggregator.group_by_model(results))

# Export to benchmark analysis directory
analysis_dir = Path("tests/example_benchmark/analysis")
formatter.to_csv(by_model, analysis_dir / "model_results.csv")
```

## Data Structures

### Result Dictionary

Each result in the aggregated list has this structure:

```python
{
    'task_id': str,
    'model_name': str,
    'score': float,  # 0.0 to 1.0
    'passed': bool,
    'execution_time': float,  # seconds
    'token_usage': {
        'prompt_tokens': int,
        'completion_tokens': int,
        'total_tokens': int
    },
    'grader_name': str,
    'metadata': dict
}
```

### Aggregated Statistics

Statistics dictionaries contain:

```python
{
    'count': int,
    'mean': float,
    'median': float,
    'stddev': float,
    'min': float,
    'max': float,
    'percentiles': {
        '25th': float,
        '50th': float,
        '75th': float,
        '90th': float,  # if count >= 20
        '95th': float   # if count >= 20
    },
    'pass_rate': float,
    'total_passed': int,
    'total_failed': int,
    'avg_execution_time': float,
    'total_execution_time': float,
    'token_usage': dict,
    'avg_tokens_per_task': dict
}
```

## Design Notes

-   **Library, not CLI**: The visualizer is intentionally a library of helper functions, not a standalone CLI tool. Users compose their own analysis workflows.
-   **Programmatic Usage**: Designed for Jupyter notebooks and Python scripts where users have full control over data loading, transformation, and output.
-   **Optional Dependencies**: Graphing requires `matplotlib`, `pandas`, and `seaborn`. Install with `pip install -e ".[viz]"`.
-   **Stateless**: Classes maintain minimal state. Each method can be called independently.
-   **Extensible**: Users can subclass formatters and generators or use the helper functions as building blocks.

## Integration with Benchmark Module

The visualizer operates on the JSON output files produced by `Benchmark._save_results()`:

```python
# In benchmark code
output = await benchmark.run()
# Automatically saved to tests/<benchmark_name>/results/ directory

# In analysis notebook
from visualizer import ResultsAggregator
aggregator = ResultsAggregator()
results = aggregator.aggregate_files(["tests/example_benchmark/results/example_20250101_120000.json"])
```

The `BenchmarkOutput.model_dump()` format is the canonical input for all visualizer functions.

**Default Result Locations:**

-   Results are saved to `tests/<benchmark_name>/results/` by default
-   Can be overridden via `config.results.output_dir`
-   Analysis outputs typically saved to `tests/<benchmark_name>/analysis/`
