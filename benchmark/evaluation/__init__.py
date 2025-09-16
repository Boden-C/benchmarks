"""
Evaluation module for benchmarks.

Provides result evaluation, grading, and scoring utilities.
"""

from benchmark.evaluation.evaluator import Evaluator
from benchmark.evaluation.graders import (
    exact_match,
    substring_match,
    numeric_match,
    llm_judge,
)

__all__ = [
    "Evaluator",
    "exact_match",
    "substring_match",
    "numeric_match",
    "llm_judge",
]
