"""
Base executor protocol and hook system.

Defines the core contract for task execution and provides hooks for
instrumentation and monitoring.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional

from benchmark.models import Task, TaskResult, ModelConfig

logger = logging.getLogger(__name__)


class Executor(ABC):
    """Protocol for task executors."""
    
    def __init__(self, models: list[ModelConfig], **kwargs) -> None:
        """
        Initialize executor with model configurations.
        
        Args:
            models: List of model configurations
            **kwargs: Additional executor-specific parameters
        """
        self.models = models
        self.hooks: list["ExecutionHook"] = kwargs.get("hooks", [])
        logger.info(f"Initialized {self.__class__.__name__} with {len(models)} models")
    
    @abstractmethod
    async def execute_task(self, task: Task) -> list[TaskResult]:
        """
        Execute task across all configured models.
        
        Args:
            task: Task to execute
        
        Returns:
            List of TaskResult objects (one per model)
        """
        pass
    
    async def _run_hooks_before_task(self, task: Task) -> None:
        """Execute all before_task hooks."""
        for hook in self.hooks:
            try:
                await hook.before_task(task)
            except Exception as e:
                logger.warning(f"Hook before_task failed: {e}")
    
    async def _run_hooks_after_task(self, task: Task, results: list[TaskResult]) -> None:
        """Execute all after_task hooks."""
        for hook in self.hooks:
            try:
                await hook.after_task(task, results)
            except Exception as e:
                logger.warning(f"Hook after_task failed: {e}")


class ExecutionHook(ABC):
    """Protocol for execution lifecycle hooks."""
    
    @abstractmethod
    async def before_task(self, task: Task) -> None:
        """
        Called before task execution.
        
        Args:
            task: Task about to be executed
        """
        pass
    
    @abstractmethod
    async def after_task(self, task: Task, results: list[TaskResult]) -> None:
        """
        Called after task completion.
        
        Args:
            task: Task that was executed
            results: Execution results for all models
        """
        pass
