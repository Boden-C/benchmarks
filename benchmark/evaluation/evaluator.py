"""
Task result evaluator.

Orchestrates grading of task results using provided grading functions.
"""

import asyncio
import logging
from typing import Callable, Optional
from datetime import datetime

from benchmark.models import TaskResult, Task, Grade

logger = logging.getLogger(__name__)


class Evaluator:
    """Evaluates task results using provided grading function."""
    
    def __init__(
        self,
        grade_function: Callable[[TaskResult, Task], Grade],
        parallel: bool = True,
        max_concurrent: int = 10
    ) -> None:
        """
        Initialize evaluator.
        
        Args:
            grade_function: Async function that grades a TaskResult
            parallel: Whether to evaluate results in parallel
            max_concurrent: Maximum concurrent evaluations
        """
        self.grade_function = grade_function
        self.parallel = parallel
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent) if parallel else None
    
    async def evaluate_results(
        self,
        results: list[TaskResult],
        tasks: list[Task]
    ) -> list[tuple[TaskResult, Grade]]:
        """
        Evaluate all task results.
        
        Args:
            results: List of task results to evaluate
            tasks: Original tasks for context
        
        Returns:
            List of (TaskResult, Grade) tuples
        """
        task_map = {task.id: task for task in tasks}
        
        if self.parallel:
            graded = await self._evaluate_parallel(results, task_map)
        else:
            graded = await self._evaluate_sequential(results, task_map)
        
        logger.info(f"Evaluated {len(graded)} results")
        return graded
    
    async def _evaluate_parallel(
        self,
        results: list[TaskResult],
        task_map: dict[str, Task]
    ) -> list[tuple[TaskResult, Grade]]:
        """
        Evaluate results in parallel.
        
        Args:
            results: Task results to evaluate
            task_map: Mapping of task IDs to tasks
        
        Returns:
            List of graded results
        """
        async def grade_with_semaphore(result: TaskResult) -> tuple[TaskResult, Grade]:
            async with self._semaphore:
                return await self._grade_single(result, task_map)
        
        tasks = [grade_with_semaphore(result) for result in results]
        return await asyncio.gather(*tasks, return_exceptions=False)
    
    async def _evaluate_sequential(
        self,
        results: list[TaskResult],
        task_map: dict[str, Task]
    ) -> list[tuple[TaskResult, Grade]]:
        """
        Evaluate results sequentially.
        
        Args:
            results: Task results to evaluate
            task_map: Mapping of task IDs to tasks
        
        Returns:
            List of graded results
        """
        graded = []
        for result in results:
            graded_result = await self._grade_single(result, task_map)
            graded.append(graded_result)
        
        return graded
    
    async def _grade_single(
        self,
        result: TaskResult,
        task_map: dict[str, Task]
    ) -> tuple[TaskResult, Grade]:
        """
        Grade a single result.
        
        Args:
            result: Task result to grade
            task_map: Mapping of task IDs to tasks
        
        Returns:
            Tuple of (TaskResult, Grade)
        """
        task = task_map.get(result.task_id)
        
        if task is None:
            logger.error(f"Task not found for result: {result.task_id}")
            return (
                result,
                Grade(
                    score=0.0,
                    passed=False,
                    reasoning="Task not found",
                    grader_name="error"
                )
            )
        
        try:
            grade = await self.grade_function(result, task)
            
            if not isinstance(grade, Grade):
                logger.error(f"Invalid grade type: {type(grade)}")
                grade = Grade(
                    score=0.0,
                    passed=False,
                    reasoning="Invalid grade returned",
                    grader_name="error"
                )
            
            logger.debug(
                f"Graded {result.task_id} for {result.model_name}: "
                f"score={grade.score:.2f}, passed={grade.passed}"
            )
            
            return (result, grade)
        
        except Exception as e:
            logger.error(f"Error grading {result.task_id}: {e}")
            return (
                result,
                Grade(
                    score=0.0,
                    passed=False,
                    reasoning=f"Grading error: {str(e)}",
                    grader_name="error",
                    metadata={"error": str(e)}
                )
            )
    
    def calculate_summary(
        self,
        graded_results: list[tuple[TaskResult, Grade]]
    ) -> dict:
        """
        Calculate summary statistics for graded results.
        
        Args:
            graded_results: List of (TaskResult, Grade) tuples
        
        Returns:
            Dictionary with summary statistics
        """
        if not graded_results:
            return {
                "total_tasks": 0,
                "mean_score": 0.0,
                "median_score": 0.0,
                "min_score": 0.0,
                "max_score": 0.0,
                "pass_rate": 0.0,
                "total_passed": 0,
                "total_failed": 0,
                "by_model": {},
                "by_task": {},
            }
        
        scores = [grade.score for _, grade in graded_results]
        passed_count = sum(1 for _, grade in graded_results if grade.passed)
        
        sorted_scores = sorted(scores)
        n = len(sorted_scores)
        median = (
            sorted_scores[n // 2]
            if n % 2 == 1
            else (sorted_scores[n // 2 - 1] + sorted_scores[n // 2]) / 2
        )
        
        by_model = self._group_by_model(graded_results)
        by_task = self._group_by_task(graded_results)
        
        summary = {
            "total_tasks": len(graded_results),
            "mean_score": sum(scores) / len(scores),
            "median_score": median,
            "min_score": min(scores),
            "max_score": max(scores),
            "pass_rate": passed_count / len(graded_results),
            "total_passed": passed_count,
            "total_failed": len(graded_results) - passed_count,
            "by_model": by_model,
            "by_task": by_task,
        }
        
        logger.info(
            f"Summary: {summary['total_tasks']} tasks, "
            f"mean={summary['mean_score']:.3f}, "
            f"pass_rate={summary['pass_rate']:.1%}"
        )
        
        return summary
    
    def _group_by_model(
        self,
        graded_results: list[tuple[TaskResult, Grade]]
    ) -> dict[str, dict]:
        """
        Group results by model.
        
        Args:
            graded_results: List of graded results
        
        Returns:
            Dictionary mapping model names to statistics
        """
        model_results = {}
        
        for result, grade in graded_results:
            model_name = result.model_name
            
            if model_name not in model_results:
                model_results[model_name] = {
                    "scores": [],
                    "passed": 0,
                    "failed": 0,
                    "total_tokens": 0,
                    "total_time": 0.0,
                }
            
            model_results[model_name]["scores"].append(grade.score)
            if grade.passed:
                model_results[model_name]["passed"] += 1
            else:
                model_results[model_name]["failed"] += 1
            
            model_results[model_name]["total_tokens"] += result.token_usage.get("total_tokens", 0)
            model_results[model_name]["total_time"] += result.execution_time
        
        for model_name, data in model_results.items():
            scores = data["scores"]
            data["mean_score"] = sum(scores) / len(scores) if scores else 0.0
            data["pass_rate"] = data["passed"] / (data["passed"] + data["failed"])
            data["task_count"] = len(scores)
        
        return model_results
    
    def _group_by_task(
        self,
        graded_results: list[tuple[TaskResult, Grade]]
    ) -> dict[str, dict]:
        """
        Group results by task.
        
        Args:
            graded_results: List of graded results
        
        Returns:
            Dictionary mapping task IDs to statistics
        """
        task_results = {}
        
        for result, grade in graded_results:
            task_id = result.task_id
            
            if task_id not in task_results:
                task_results[task_id] = {
                    "scores": [],
                    "passed": 0,
                    "failed": 0,
                }
            
            task_results[task_id]["scores"].append(grade.score)
            if grade.passed:
                task_results[task_id]["passed"] += 1
            else:
                task_results[task_id]["failed"] += 1
        
        for task_id, data in task_results.items():
            scores = data["scores"]
            data["mean_score"] = sum(scores) / len(scores) if scores else 0.0
            data["pass_rate"] = data["passed"] / (data["passed"] + data["failed"])
            data["model_count"] = len(scores)
        
        return task_results
