"""
Abstract benchmark base class.

Defines the core contract for benchmark implementations with automatic
configuration loading, task execution, and result aggregation.
"""

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Any, Type
from datetime import datetime

from benchmark.models import (
    Task,
    TaskResult,
    Grade,
    BenchmarkRunConfig,
    BenchmarkOutput,
    ChatMessage,
)
from benchmark.config.loader import load_config
from benchmark.execution.base import Executor
from benchmark.execution.simple_executor import SimpleExecutor
from benchmark.evaluation.evaluator import Evaluator

logger = logging.getLogger(__name__)


class Benchmark(ABC):
    """Abstract base class that users extend to define benchmarks."""
    
    def __init__(
        self,
        config: Optional[BenchmarkRunConfig] = None,
        questions: Optional[str] = None,
        executor_class: Optional[Type[Executor]] = None,
        global_config: str = "global_config.yaml",
        executor_kwargs: Optional[dict[str, Any]] = None
    ) -> None:
        """
        Initialize benchmark.
        
        Args:
            config: Optional pre-loaded configuration
            questions: Optional path to questions file
            executor_class: Optional executor class (defaults to SimpleExecutor)
            global_config: Path to global config file
            executor_kwargs: Optional kwargs for executor initialization
        """
        # Determine benchmark name and directory
        self.benchmark_name = self.__class__.__name__.lower().replace("benchmark", "")
        self.benchmark_dir = Path("tests") / self.benchmark_name
        
        # Load configuration
        if config is None:
            benchmark_config_path = self.benchmark_dir / "config.yaml"
            self.config = load_config(
                global_source=global_config,
                benchmark_source=str(benchmark_config_path) if benchmark_config_path.exists() else None
            )
            logger.info(f"Loaded config for benchmark: {self.benchmark_name}")
        else:
            self.config = config
        
        # Load tasks
        if questions is None:
            questions_path = self.benchmark_dir / "questions.jsonl"
        else:
            questions_path = Path(questions)
        
        self.tasks = self._load_tasks(questions_path)
        logger.info(f"Loaded {len(self.tasks)} tasks")
        
        # Initialize executor
        executor_class = executor_class or SimpleExecutor
        executor_kwargs = executor_kwargs or {}
        
        self.executor = executor_class(
            models=self.config.models,
            **executor_kwargs
        )
        logger.info(f"Initialized executor: {executor_class.__name__}")
    
    def _load_tasks(self, questions_path: Path) -> list[Task]:
        """
        Load tasks from questions file.
        
        Args:
            questions_path: Path to questions file (JSON or JSONL)
        
        Returns:
            List of Task objects
        """
        if not questions_path.exists():
            logger.warning(f"Questions file not found: {questions_path}")
            return []
        
        tasks = []
        
        try:
            # Try JSONL format first
            if questions_path.suffix == ".jsonl":
                with open(questions_path, "r", encoding="utf-8") as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            task_dict = json.loads(line)
                            task = self._parse_task(task_dict)
                            tasks.append(task)
                        except json.JSONDecodeError as e:
                            logger.error(f"Error parsing line {line_num} in {questions_path}: {e}")
            
            # Try JSON array format
            else:
                with open(questions_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for task_dict in data:
                            task = self._parse_task(task_dict)
                            tasks.append(task)
                    else:
                        task = self._parse_task(data)
                        tasks.append(task)
        
        except Exception as e:
            logger.error(f"Error loading tasks from {questions_path}: {e}")
        
        return tasks
    
    def _parse_task(self, task_dict: dict[str, Any]) -> Task:
        """
        Parse task dictionary into Task object.
        
        Args:
            task_dict: Task dictionary
        
        Returns:
            Task object
        """
        # Parse messages
        messages = []
        for msg in task_dict.get("messages", []):
            messages.append(ChatMessage(**msg))
        
        # Create task
        return Task(
            id=task_dict["id"],
            messages=messages,
            ground_truth=task_dict.get("ground_truth"),
            metadata=task_dict.get("metadata", {}),
            timeout=task_dict.get("timeout"),
        )
    
    @abstractmethod
    async def grade(self, result: TaskResult, task: Task) -> Grade:
        """
        Grade a task result.
        
        Subclasses must implement this method to define grading logic.
        
        Args:
            result: Task execution result
            task: Original task
        
        Returns:
            Grade object with score and reasoning
        """
        pass
    
    async def run(self) -> BenchmarkOutput:
        """
        Run complete benchmark.
        
        Executes all tasks across all models and evaluates results.
        
        Returns:
            BenchmarkOutput with results and summary
        """
        logger.info(f"Starting benchmark: {self.benchmark_name}")
        start_time = time.time()
        
        all_results: list[TaskResult] = []
        
        # Execute tasks
        for i, task in enumerate(self.tasks, 1):
            logger.info(f"Executing task {i}/{len(self.tasks)}: {task.id}")
            
            try:
                task_results = await self.executor.execute_task(task)
                all_results.extend(task_results)
                
                # Log progress
                successful = sum(1 for r in task_results if r.success)
                logger.info(
                    f"Task {task.id} completed: {successful}/{len(task_results)} successful"
                )
                
            except Exception as e:
                logger.error(f"Error executing task {task.id}: {e}")
        
        # Evaluate results
        logger.info("Evaluating results...")
        evaluator = Evaluator(self.grade)
        graded_results = await evaluator.evaluate_results(all_results, self.tasks)
        
        # Calculate summary
        summary = evaluator.calculate_summary(graded_results)
        execution_time = time.time() - start_time
        
        # Create output
        output = BenchmarkOutput(
            metadata={
                "benchmark_name": self.benchmark_name,
                "config": self.config.model_dump(),
                "timestamp": datetime.utcnow().isoformat(),
            },
            results=graded_results,
            summary=summary,
            execution_time=execution_time,
        )
        
        logger.info(
            f"Benchmark completed in {execution_time:.2f}s - "
            f"Mean score: {summary['mean_score']:.2f}, "
            f"Pass rate: {summary['pass_rate']:.1%}"
        )
        
        # Save results if configured
        self._save_results(output)
        
        return output
    
    def _save_results(self, output: BenchmarkOutput) -> None:
        """
        Save results to file.
        
        Args:
            output: Benchmark output to save
        """
        results_config = self.config.results
        output_dir = Path(results_config.get("output_dir", "results"))
        
        if not results_config.get("save_intermediate", True):
            logger.debug("Result saving disabled")
            return
        
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.benchmark_name}_{timestamp}.json"
            output_path = output_dir / filename
            
            # Convert to dict for JSON serialization
            output_dict = output.model_dump()
            
            # Handle non-serializable types
            def json_serializer(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                raise TypeError(f"Type {type(obj)} not serializable")
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(output_dict, f, indent=2, default=json_serializer)
            
            logger.info(f"Results saved to {output_path}")
            
        except Exception as e:
            logger.error(f"Error saving results: {e}")
