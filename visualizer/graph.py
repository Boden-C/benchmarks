"""
Visualization and plotting utilities.

Provides functions for generating graphs and plots from benchmark results,
including model comparisons, score distributions, and timelines.

Note: Requires optional viz dependencies. Install with: pip install -e ".[viz]"
"""

from pathlib import Path
from typing import Any, Optional

try:
    import matplotlib.pyplot as plt
    import pandas as pd
    import seaborn as sns
    
    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False


class GraphGenerator:
    """Generates visualizations from benchmark results."""
    
    def __init__(self):
        if not VISUALIZATION_AVAILABLE:
            raise ImportError(
                "Visualization dependencies not installed. "
                "Install with: pip install -e '.[viz]'"
            )
        
        sns.set_theme(style="whitegrid")
        self.color_palette = sns.color_palette("husl", 8)
    
    def plot_model_comparison(
        self,
        aggregated_results: dict[str, dict[str, Any]],
        metric: str = "mean",
        output_path: Optional[str | Path] = None,
        figsize: tuple[int, int] = (12, 6),
    ) -> None:
        """
        Generate bar chart comparing models on a specific metric.
        
        Args:
            aggregated_results: Dictionary of model statistics
            metric: Metric to compare (mean, median, pass_rate, etc.)
            output_path: Optional path to save figure
            figsize: Figure size as (width, height)
        """
        if not aggregated_results:
            return
        
        models = []
        values = []
        
        for model_name, stats in sorted(aggregated_results.items()):
            models.append(model_name)
            values.append(stats.get(metric, 0.0))
        
        fig, ax = plt.subplots(figsize=figsize)
        
        bars = ax.bar(models, values, color=self.color_palette[:len(models)])
        
        ax.set_xlabel('Model', fontsize=12, fontweight='bold')
        
        ylabel = metric.replace('_', ' ').title()
        if 'rate' in metric.lower():
            ylabel += ' (%)'
            ax.set_ylim([0, 1])
            values_display = [v * 100 for v in values]
        else:
            values_display = values
        
        ax.set_ylabel(ylabel, fontsize=12, fontweight='bold')
        ax.set_title(f'Model Comparison: {ylabel}', fontsize=14, fontweight='bold')
        
        for bar, value in zip(bars, values_display):
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.,
                height,
                f'{value:.2f}',
                ha='center',
                va='bottom',
                fontsize=10,
            )
        
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
        else:
            plt.show()
        
        plt.close()
    
    def plot_score_distribution(
        self,
        results: dict[str, list[dict[str, Any]]],
        model_name: Optional[str] = None,
        output_path: Optional[str | Path] = None,
        figsize: tuple[int, int] = (10, 6),
    ) -> None:
        """
        Generate histogram/KDE of score distribution.
        
        Args:
            results: Dictionary of model results (from group_by_model)
            model_name: Optional specific model to plot (plots all if None)
            output_path: Optional path to save figure
            figsize: Figure size as (width, height)
        """
        fig, ax = plt.subplots(figsize=figsize)
        
        models_to_plot = [model_name] if model_name else list(results.keys())
        
        for idx, model in enumerate(models_to_plot):
            model_results = results.get(model, [])
            if not model_results:
                continue
            
            scores = [r.get('score', 0.0) for r in model_results]
            
            ax.hist(
                scores,
                bins=20,
                alpha=0.6,
                label=model,
                color=self.color_palette[idx % len(self.color_palette)],
                edgecolor='black',
            )
        
        ax.set_xlabel('Score', fontsize=12, fontweight='bold')
        ax.set_ylabel('Frequency', fontsize=12, fontweight='bold')
        ax.set_title('Score Distribution', fontsize=14, fontweight='bold')
        ax.legend()
        
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
        else:
            plt.show()
        
        plt.close()
    
    def plot_timeline(
        self,
        results: list[dict[str, Any]],
        output_path: Optional[str | Path] = None,
        figsize: tuple[int, int] = (14, 6),
    ) -> None:
        """
        Generate timeline plot showing score progression.
        
        Args:
            results: List of result dictionaries with timestamps
            output_path: Optional path to save figure
            figsize: Figure size as (width, height)
        """
        if not results:
            return
        
        df = pd.DataFrame(results)
        
        if 'model_name' not in df.columns:
            return
        
        fig, ax = plt.subplots(figsize=figsize)
        
        for idx, model_name in enumerate(df['model_name'].unique()):
            model_data = df[df['model_name'] == model_name]
            
            x = range(len(model_data))
            y = model_data['score'].tolist()
            
            ax.plot(
                x,
                y,
                marker='o',
                label=model_name,
                color=self.color_palette[idx % len(self.color_palette)],
                linewidth=2,
                markersize=4,
            )
        
        ax.set_xlabel('Task Number', fontsize=12, fontweight='bold')
        ax.set_ylabel('Score', fontsize=12, fontweight='bold')
        ax.set_title('Score Timeline', fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
        else:
            plt.show()
        
        plt.close()
    
    def plot_heatmap(
        self,
        task_results: dict[str, dict[str, Any]],
        output_path: Optional[str | Path] = None,
        figsize: tuple[int, int] = (12, 8),
    ) -> None:
        """
        Generate heatmap showing model performance across tasks.
        
        Args:
            task_results: Dictionary mapping task_id to statistics per model
            output_path: Optional path to save figure
            figsize: Figure size as (width, height)
        """
        if not task_results:
            return
        
        models = set()
        for task_stats in task_results.values():
            if isinstance(task_stats, dict):
                models.update(task_stats.keys())
        
        models = sorted(list(models))
        tasks = sorted(list(task_results.keys()))
        
        data = []
        for task_id in tasks:
            row = []
            for model_name in models:
                task_stats = task_results.get(task_id, {})
                if isinstance(task_stats, dict):
                    model_stat = task_stats.get(model_name, {})
                    score = model_stat.get('score', 0.0) if isinstance(model_stat, dict) else 0.0
                else:
                    score = 0.0
                row.append(score)
            data.append(row)
        
        df = pd.DataFrame(data, index=tasks, columns=models)
        
        fig, ax = plt.subplots(figsize=figsize)
        
        sns.heatmap(
            df,
            annot=True,
            fmt='.2f',
            cmap='RdYlGn',
            center=0.5,
            vmin=0,
            vmax=1,
            cbar_kws={'label': 'Score'},
            ax=ax,
        )
        
        ax.set_title('Model Performance Heatmap', fontsize=14, fontweight='bold')
        ax.set_xlabel('Model', fontsize=12, fontweight='bold')
        ax.set_ylabel('Task', fontsize=12, fontweight='bold')
        
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
        else:
            plt.show()
        
        plt.close()
    
    def plot_execution_time_comparison(
        self,
        aggregated_results: dict[str, dict[str, Any]],
        output_path: Optional[str | Path] = None,
        figsize: tuple[int, int] = (12, 6),
    ) -> None:
        """
        Generate bar chart comparing model execution times.
        
        Args:
            aggregated_results: Dictionary of model statistics
            output_path: Optional path to save figure
            figsize: Figure size as (width, height)
        """
        if not aggregated_results:
            return
        
        models = []
        avg_times = []
        total_times = []
        
        for model_name, stats in sorted(aggregated_results.items()):
            models.append(model_name)
            avg_times.append(stats.get('avg_execution_time', 0.0))
            total_times.append(stats.get('total_execution_time', 0.0))
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)
        
        ax1.bar(models, avg_times, color=self.color_palette[:len(models)])
        ax1.set_xlabel('Model', fontsize=12, fontweight='bold')
        ax1.set_ylabel('Avg Time (seconds)', fontsize=12, fontweight='bold')
        ax1.set_title('Average Execution Time per Task', fontsize=14, fontweight='bold')
        ax1.tick_params(axis='x', rotation=45)
        
        for i, (model, time) in enumerate(zip(models, avg_times)):
            ax1.text(i, time, f'{time:.2f}s', ha='center', va='bottom', fontsize=9)
        
        ax2.bar(models, total_times, color=self.color_palette[:len(models)])
        ax2.set_xlabel('Model', fontsize=12, fontweight='bold')
        ax2.set_ylabel('Total Time (seconds)', fontsize=12, fontweight='bold')
        ax2.set_title('Total Execution Time', fontsize=14, fontweight='bold')
        ax2.tick_params(axis='x', rotation=45)
        
        for i, (model, time) in enumerate(zip(models, total_times)):
            ax2.text(i, time, f'{time:.1f}s', ha='center', va='bottom', fontsize=9)
        
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
        else:
            plt.show()
        
        plt.close()
