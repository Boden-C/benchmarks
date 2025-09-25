"""
Visualization suite.

Provides aggregation, formatting, and graphing utilities for benchmark results.

Note: Graph generation requires optional dependencies. Install with:
    pip install -e ".[viz]"
"""

from visualizer.aggregator import ResultsAggregator
from visualizer.formatter import ResultsFormatter, execution_results_to_text

try:
    from visualizer.graph import GraphGenerator
    GRAPH_AVAILABLE = True
except ImportError:
    GRAPH_AVAILABLE = False
    GraphGenerator = None

__all__ = [
    "ResultsAggregator",
    "ResultsFormatter",
    "execution_results_to_text",
    "GraphGenerator",
    "GRAPH_AVAILABLE",
]
