"""
Results aggregation and statistical analysis.

Provides utilities for loading, combining, and analyzing benchmark results
from multiple runs or files.
"""

import json
import statistics
from pathlib import Path
from typing import Any, Optional
from collections import defaultdict


class ResultsAggregator:
    """Aggregates and analyzes benchmark results across multiple runs."""
    
    def __init__(self):
        self.cumulative_metrics: dict[str, Any] = {}
        self.validation_rules: dict[str, Any] = {}
    
    def load_results_file(self, filepath: str | Path) -> dict[str, Any]:
        """
        Load results from a single JSON file.
        
        Args:
            filepath: Path to results JSON file
            
        Returns:
            Parsed results dictionary
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def aggregate_files(self, filepaths: list[str | Path]) -> list[dict[str, Any]]:
        """
        Load and combine results from multiple files.
        
        Args:
            filepaths: List of paths to result JSON files
            
        Returns:
            Combined list of all results across files
        """
        all_results = []
        
        for filepath in filepaths:
            data = self.load_results_file(filepath)
            results = data.get('results', [])
            
            for result_pair in results:
                task_result, grade = result_pair
                all_results.append({
                    'task_id': task_result.get('task_id'),
                    'model_name': task_result.get('model_name'),
                    'score': grade.get('score'),
                    'passed': grade.get('passed'),
                    'execution_time': task_result.get('execution_time'),
                    'token_usage': task_result.get('token_usage', {}),
                    'grader_name': grade.get('grader_name'),
                    'metadata': {**task_result.get('metadata', {}), **grade.get('metadata', {})},
                })
        
        return all_results
    
    def group_by_model(self, results: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        """
        Group results by model name.
        
        Args:
            results: List of result dictionaries
            
        Returns:
            Dictionary mapping model name to list of results
        """
        grouped = defaultdict(list)
        
        for result in results:
            model_name = result.get('model_name', 'unknown')
            grouped[model_name].append(result)
        
        return dict(grouped)
    
    def group_by_task(self, results: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        """
        Group results by task ID.
        
        Args:
            results: List of result dictionaries
            
        Returns:
            Dictionary mapping task ID to list of results
        """
        grouped = defaultdict(list)
        
        for result in results:
            task_id = result.get('task_id', 'unknown')
            grouped[task_id].append(result)
        
        return dict(grouped)
    
    def calculate_summary_stats(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Calculate comprehensive summary statistics.
        
        Args:
            results: List of result dictionaries
            
        Returns:
            Dictionary with summary statistics including mean, median, stddev, percentiles
        """
        if not results:
            return {
                'count': 0,
                'mean': 0.0,
                'median': 0.0,
                'stddev': 0.0,
                'min': 0.0,
                'max': 0.0,
                'percentiles': {},
            }
        
        scores = [r.get('score', 0.0) for r in results]
        
        stats = {
            'count': len(scores),
            'mean': statistics.mean(scores),
            'median': statistics.median(scores),
            'min': min(scores),
            'max': max(scores),
        }
        
        if len(scores) > 1:
            stats['stddev'] = statistics.stdev(scores)
        else:
            stats['stddev'] = 0.0
        
        if len(scores) >= 4:
            stats['percentiles'] = {
                '25th': statistics.quantiles(scores, n=4)[0],
                '50th': statistics.quantiles(scores, n=4)[1],
                '75th': statistics.quantiles(scores, n=4)[2],
            }
            
            if len(scores) >= 20:
                stats['percentiles'].update({
                    '5th': statistics.quantiles(scores, n=20)[0],
                    '90th': statistics.quantiles(scores, n=20)[17],
                    '95th': statistics.quantiles(scores, n=20)[18],
                })
        
        return stats
    
    def aggregate_model_results(self, results: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        """
        Calculate aggregate statistics per model.
        
        Args:
            results: List of result dictionaries
            
        Returns:
            Dictionary mapping model name to aggregated statistics
        """
        grouped = self.group_by_model(results)
        aggregated = {}
        
        for model_name, model_results in grouped.items():
            stats = self.calculate_summary_stats(model_results)
            
            passed_count = sum(1 for r in model_results if r.get('passed', False))
            stats['pass_rate'] = passed_count / len(model_results) if model_results else 0.0
            stats['total_passed'] = passed_count
            stats['total_failed'] = len(model_results) - passed_count
            
            exec_times = [r.get('execution_time', 0.0) for r in model_results]
            stats['avg_execution_time'] = statistics.mean(exec_times) if exec_times else 0.0
            stats['total_execution_time'] = sum(exec_times)
            
            total_tokens = defaultdict(int)
            for r in model_results:
                for key, value in r.get('token_usage', {}).items():
                    total_tokens[key] += value
            
            stats['token_usage'] = dict(total_tokens)
            
            if total_tokens:
                stats['avg_tokens_per_task'] = {
                    key: value / len(model_results)
                    for key, value in total_tokens.items()
                }
            
            aggregated[model_name] = stats
        
        return aggregated
    
    def aggregate_task_results(self, results: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        """
        Calculate aggregate statistics per task.
        
        Args:
            results: List of result dictionaries
            
        Returns:
            Dictionary mapping task ID to aggregated statistics
        """
        grouped = self.group_by_task(results)
        aggregated = {}
        
        for task_id, task_results in grouped.items():
            stats = self.calculate_summary_stats(task_results)
            
            passed_count = sum(1 for r in task_results if r.get('passed', False))
            stats['pass_rate'] = passed_count / len(task_results) if task_results else 0.0
            stats['models_tested'] = len(set(r.get('model_name') for r in task_results))
            
            aggregated[task_id] = stats
        
        return aggregated
    
    def aggregate_current_metrics(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Calculate current running metrics during execution.
        
        Args:
            results: List of result dictionaries collected so far
            
        Returns:
            Dictionary with current aggregate metrics
        """
        if not results:
            return {
                'completed': 0,
                'mean_score': 0.0,
                'pass_rate': 0.0,
            }
        
        scores = [r.get('score', 0.0) for r in results]
        passed = sum(1 for r in results if r.get('passed', False))
        
        return {
            'completed': len(results),
            'mean_score': statistics.mean(scores),
            'pass_rate': passed / len(results),
        }
    
    def compare_runs(
        self,
        baseline_results: list[dict[str, Any]],
        current_results: list[dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        """
        Compare two benchmark runs and calculate differences.
        
        Args:
            baseline_results: Results from baseline run
            current_results: Results from current run
            
        Returns:
            Dictionary with comparison metrics and deltas
        """
        baseline_stats = self.aggregate_model_results(baseline_results)
        current_stats = self.aggregate_model_results(current_results)
        
        comparison = {}
        
        for model_name in set(baseline_stats.keys()) | set(current_stats.keys()):
            baseline = baseline_stats.get(model_name, {})
            current = current_stats.get(model_name, {})
            
            comparison[model_name] = {
                'baseline': baseline,
                'current': current,
                'delta': {
                    'mean_score': current.get('mean', 0.0) - baseline.get('mean', 0.0),
                    'pass_rate': current.get('pass_rate', 0.0) - baseline.get('pass_rate', 0.0),
                    'count': current.get('count', 0) - baseline.get('count', 0),
                },
            }
        
        return comparison
