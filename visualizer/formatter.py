"""
Output formatting and display utilities.

Provides functions for formatting benchmark results into various output formats
including Markdown tables, CSV, JSON, and console output.
"""

import json
import csv
from pathlib import Path
from typing import Any, Optional
from datetime import datetime


class ResultsFormatter:
    """Formats benchmark results for various output formats."""
    
    def __init__(self):
        self.last_metrics: dict[str, Any] = {}
        self.color_codes = {
            'reset': '\033[0m',
            'bold': '\033[1m',
            'green': '\033[92m',
            'red': '\033[91m',
            'yellow': '\033[93m',
            'blue': '\033[94m',
            'cyan': '\033[96m',
        }
    
    def to_markdown_table(self, aggregated_results: dict[str, dict[str, Any]]) -> str:
        """
        Format aggregated results as Markdown table.
        
        Args:
            aggregated_results: Dictionary of model statistics
            
        Returns:
            Markdown-formatted table string
        """
        if not aggregated_results:
            return "No results to display."
        
        lines = []
        lines.append("| Model | Tasks | Pass Rate | Mean Score | Median | Std Dev | Avg Time (s) |")
        lines.append("|-------|-------|-----------|------------|--------|---------|--------------|")
        
        for model_name, stats in sorted(aggregated_results.items()):
            lines.append(
                f"| {model_name} "
                f"| {stats.get('count', 0)} "
                f"| {self._format_percentage(stats.get('pass_rate', 0.0))} "
                f"| {self._format_score(stats.get('mean', 0.0))} "
                f"| {self._format_score(stats.get('median', 0.0))} "
                f"| {self._format_score(stats.get('stddev', 0.0))} "
                f"| {stats.get('avg_execution_time', 0.0):.2f} |"
            )
        
        return '\n'.join(lines)
    
    def to_csv(self, aggregated_results: dict[str, dict[str, Any]], output_path: str | Path) -> None:
        """
        Export aggregated results to CSV file.
        
        Args:
            aggregated_results: Dictionary of model statistics
            output_path: Path to output CSV file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not aggregated_results:
            return
        
        first_stats = next(iter(aggregated_results.values()))
        headers = ['model_name', 'count', 'pass_rate', 'mean_score', 'median_score', 
                   'stddev', 'min_score', 'max_score', 'avg_execution_time', 
                   'total_execution_time', 'total_passed', 'total_failed']
        
        if 'token_usage' in first_stats:
            token_keys = list(first_stats['token_usage'].keys())
            headers.extend([f'total_{key}' for key in token_keys])
            headers.extend([f'avg_{key}' for key in token_keys])
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            
            for model_name, stats in sorted(aggregated_results.items()):
                row = {
                    'model_name': model_name,
                    'count': stats.get('count', 0),
                    'pass_rate': stats.get('pass_rate', 0.0),
                    'mean_score': stats.get('mean', 0.0),
                    'median_score': stats.get('median', 0.0),
                    'stddev': stats.get('stddev', 0.0),
                    'min_score': stats.get('min', 0.0),
                    'max_score': stats.get('max', 0.0),
                    'avg_execution_time': stats.get('avg_execution_time', 0.0),
                    'total_execution_time': stats.get('total_execution_time', 0.0),
                    'total_passed': stats.get('total_passed', 0),
                    'total_failed': stats.get('total_failed', 0),
                }
                
                if 'token_usage' in stats:
                    for key, value in stats['token_usage'].items():
                        row[f'total_{key}'] = value
                
                if 'avg_tokens_per_task' in stats:
                    for key, value in stats['avg_tokens_per_task'].items():
                        row[f'avg_{key}'] = value
                
                writer.writerow(row)
    
    def to_json(self, aggregated_results: dict[str, dict[str, Any]], output_path: str | Path) -> None:
        """
        Export aggregated results to JSON file.
        
        Args:
            aggregated_results: Dictionary of model statistics
            output_path: Path to output JSON file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        output_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'results': aggregated_results,
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2)
    
    def format_current_metrics(
        self,
        model_name: str,
        completed: int,
        total: int,
        metrics: dict[str, Any],
        task_file: Optional[str] = None,
    ) -> None:
        """
        Format and display current progress metrics during execution.
        
        Args:
            model_name: Name of the model being tested
            completed: Number of completed tasks
            total: Total number of tasks
            metrics: Current metrics dictionary
            task_file: Optional task file being processed
        """
        percentage = (completed / total * 100) if total > 0 else 0
        
        print(f"\n{self.color_codes['bold']}{self.color_codes['cyan']}{model_name}{self.color_codes['reset']}")
        print(f"Progress: [{completed}/{total}] ({percentage:.1f}%)")
        
        if metrics:
            print(f"  Pass Rate: {self._format_percentage(metrics.get('pass_rate', 0.0))}")
            print(f"  Mean Score: {self._format_score(metrics.get('mean_score', 0.0))}")
        
        if task_file:
            print(f"  Current File: {task_file}")
        
        if model_name in self.last_metrics:
            prev = self.last_metrics[model_name]
            delta_completed = completed - prev.get('completed', 0)
            delta_score = metrics.get('mean_score', 0.0) - prev.get('mean_score', 0.0)
            
            if delta_completed > 0:
                indicator = '↑' if delta_score > 0 else '↓' if delta_score < 0 else '→'
                color = self.color_codes['green'] if delta_score > 0 else self.color_codes['red'] if delta_score < 0 else ''
                print(f"  Change: +{delta_completed} tasks, {color}{indicator} {abs(delta_score):.3f}{self.color_codes['reset']}")
        
        self.last_metrics[model_name] = {
            'completed': completed,
            'mean_score': metrics.get('mean_score', 0.0),
        }
    
    def format_summary(self, summary: dict[str, Any]) -> str:
        """
        Format benchmark summary for console output.
        
        Args:
            summary: Summary statistics dictionary
            
        Returns:
            Formatted summary string
        """
        lines = []
        lines.append(f"\n{self.color_codes['bold']}{'='*60}{self.color_codes['reset']}")
        lines.append(f"{self.color_codes['bold']}SUMMARY{self.color_codes['reset']}")
        lines.append(f"{self.color_codes['bold']}{'='*60}{self.color_codes['reset']}")
        
        lines.append(f"\nTotal Tasks: {summary.get('total_tasks', 0)}")
        lines.append(f"Mean Score: {self._format_score(summary.get('mean_score', 0.0))}")
        lines.append(f"Median Score: {self._format_score(summary.get('median_score', 0.0))}")
        lines.append(f"Pass Rate: {self._format_percentage(summary.get('pass_rate', 0.0))}")
        
        if 'by_model' in summary:
            lines.append(f"\n{self.color_codes['bold']}By Model:{self.color_codes['reset']}")
            for model_name, stats in summary['by_model'].items():
                lines.append(f"  {model_name}:")
                lines.append(f"    Mean: {self._format_score(stats.get('mean_score', 0.0))}")
                lines.append(f"    Pass Rate: {self._format_percentage(stats.get('pass_rate', 0.0))}")
        
        return '\n'.join(lines)
    
    def format_comparison(self, comparison: dict[str, dict[str, Any]]) -> str:
        """
        Format comparison between two runs.
        
        Args:
            comparison: Comparison dictionary from ResultsAggregator.compare_runs()
            
        Returns:
            Formatted comparison string
        """
        lines = []
        lines.append(f"\n{self.color_codes['bold']}RUN COMPARISON{self.color_codes['reset']}")
        lines.append("=" * 80)
        
        for model_name, data in sorted(comparison.items()):
            lines.append(f"\n{self.color_codes['cyan']}{model_name}{self.color_codes['reset']}")
            
            baseline = data.get('baseline', {})
            current = data.get('current', {})
            delta = data.get('delta', {})
            
            mean_delta = delta.get('mean_score', 0.0)
            mean_color = self.color_codes['green'] if mean_delta > 0 else self.color_codes['red'] if mean_delta < 0 else ''
            mean_indicator = '↑' if mean_delta > 0 else '↓' if mean_delta < 0 else '→'
            
            lines.append(f"  Mean Score: {self._format_score(baseline.get('mean', 0.0))} → "
                        f"{self._format_score(current.get('mean', 0.0))} "
                        f"{mean_color}{mean_indicator} {abs(mean_delta):.3f}{self.color_codes['reset']}")
            
            rate_delta = delta.get('pass_rate', 0.0)
            rate_color = self.color_codes['green'] if rate_delta > 0 else self.color_codes['red'] if rate_delta < 0 else ''
            rate_indicator = '↑' if rate_delta > 0 else '↓' if rate_delta < 0 else '→'
            
            lines.append(f"  Pass Rate: {self._format_percentage(baseline.get('pass_rate', 0.0))} → "
                        f"{self._format_percentage(current.get('pass_rate', 0.0))} "
                        f"{rate_color}{rate_indicator} {abs(rate_delta):.1%}{self.color_codes['reset']}")
        
        return '\n'.join(lines)
    
    def _format_score(self, score: float, precision: int = 3) -> str:
        """Format score with specified precision."""
        if score is None:
            return "N/A"
        return f"{score:.{precision}f}"
    
    def _format_percentage(self, value: float) -> str:
        """Format value as percentage."""
        if value is None:
            return "N/A"
        return f"{value * 100:.1f}%"
    
    def _format_duration(self, seconds: float) -> str:
        """Format execution time duration."""
        if seconds < 1:
            return f"{seconds * 1000:.0f}ms"
        elif seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            return f"{seconds / 60:.1f}m"
        else:
            return f"{seconds / 3600:.1f}h"


def execution_results_to_text(execution_results: list[dict[str, Any]]) -> str:
    """
    Convert execution results to human-readable text format.
    
    Args:
        execution_results: List of execution result dictionaries
        
    Returns:
        Formatted text representation
    """
    if not execution_results:
        return "No execution results available."
    
    lines = []
    
    for idx, result in enumerate(execution_results, 1):
        lines.append(f"\nRound {idx}:")
        
        if 'tool_calls' in result:
            lines.append("  Tool Calls:")
            for tool_call in result['tool_calls']:
                tool_name = tool_call.get('name', 'unknown')
                parameters = tool_call.get('parameters', {})
                lines.append(f"    - {tool_name}({parameters})")
        
        if 'response' in result:
            response = result['response']
            if isinstance(response, str):
                lines.append(f"  Response: {response[:100]}...")
            else:
                lines.append(f"  Response: {response}")
        
        if 'execution_time' in result:
            lines.append(f"  Execution Time: {result['execution_time']:.2f}s")
    
    return '\n'.join(lines)
