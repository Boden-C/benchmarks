"""
Simple single-turn executor.

Executes tasks as straightforward chat completions without tool use or
multi-round interactions.
"""

import asyncio
import logging
import time
from typing import Any

from benchmark.models import Task, TaskResult, ModelConfig
from benchmark.execution.base import Executor
from benchmark.execution.llm.factory import LLMFactory
from benchmark.execution.llm.provider import LLMProvider
from benchmark.execution.llm.exceptions import LLMProviderError

logger = logging.getLogger(__name__)


class SimpleExecutor(Executor):
    """Single-turn chat completion executor."""
    
    def __init__(self, models: list[ModelConfig], **kwargs) -> None:
        """
        Initialize simple executor.
        
        Args:
            models: List of model configurations
            **kwargs: Additional parameters (hooks, etc.)
        """
        super().__init__(models, **kwargs)
        self.providers: dict[str, LLMProvider] = {}
        self.concurrent_execution = kwargs.get("concurrent_execution", True)
        logger.debug(f"Concurrent execution: {self.concurrent_execution}")
    
    async def execute_task(self, task: Task) -> list[TaskResult]:
        """
        Execute task across all models.
        
        Args:
            task: Task to execute
        
        Returns:
            List of TaskResult objects
        """
        await self._run_hooks_before_task(task)
        
        logger.info(f"Executing task {task.id} across {len(self.models)} models")
        
        # Initialize providers if needed
        if not self.providers:
            await self._initialize_providers()
        
        # Execute across all models
        if self.concurrent_execution:
            tasks = [
                self._execute_single_model(task, self.providers[model.name], model.name)
                for model in self.models
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        else:
            results = []
            for model in self.models:
                result = await self._execute_single_model(
                    task, self.providers[model.name], model.name
                )
                results.append(result)
        
        # Convert exceptions to error results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                model_name = self.models[i].name
                final_results.append(
                    self._handle_execution_error(result, task, model_name)
                )
            else:
                final_results.append(result)
        
        await self._run_hooks_after_task(task, final_results)
        
        return final_results
    
    async def _initialize_providers(self) -> None:
        """Initialize LLM providers for all models."""
        logger.info("Initializing LLM providers")
        for model_config in self.models:
            try:
                provider = await LLMFactory.create_llm_provider(model_config)
                self.providers[model_config.name] = provider
                logger.debug(f"Initialized provider for {model_config.name}")
            except Exception as e:
                logger.error(f"Failed to initialize provider for {model_config.name}: {e}")
                raise
    
    async def _execute_single_model(
        self,
        task: Task,
        provider: LLMProvider,
        model_name: str
    ) -> TaskResult:
        """
        Execute task on a single model.
        
        Args:
            task: Task to execute
            provider: LLM provider instance
            model_name: Model identifier
        
        Returns:
            TaskResult object
        """
        start_time = time.time()
        
        try:
            # Build prompt from messages
            system_prompt = ""
            user_prompt = ""
            
            for msg in task.messages:
                if msg.role == "system":
                    system_prompt += msg.content + "\n"
                elif msg.role == "user":
                    user_prompt += msg.content + "\n"
            
            system_prompt = system_prompt.strip()
            user_prompt = user_prompt.strip()
            
            # Get completion
            logger.debug(f"Requesting completion from {model_name}")
            response, usage = await provider.get_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                return_usage=True,
                max_tokens=4096,
            )
            
            execution_time = time.time() - start_time
            
            result = TaskResult(
                task_id=task.id,
                model_name=model_name,
                response=response,
                execution_time=execution_time,
                token_usage=usage,
                success=True,
                metadata={"mode": "simple"},
            )
            
            self._log_execution_metrics(result)
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Execution failed for {model_name} on task {task.id}: {e}")
            return self._handle_execution_error(e, task, model_name, execution_time)
    
    def _handle_execution_error(
        self,
        error: Exception,
        task: Task,
        model: str,
        execution_time: float = 0.0
    ) -> TaskResult:
        """
        Create error result from exception.
        
        Args:
            error: Exception that occurred
            task: Task being executed
            model: Model name
            execution_time: Time spent before error
        
        Returns:
            TaskResult with error details
        """
        error_msg = str(error)
        if isinstance(error, LLMProviderError):
            error_msg = f"{error.__class__.__name__}: {error}"
        
        logger.warning(f"Task {task.id} failed on {model}: {error_msg}")
        
        return TaskResult(
            task_id=task.id,
            model_name=model,
            response="",
            execution_time=execution_time,
            success=False,
            error=error_msg,
            metadata={"mode": "simple", "error_type": error.__class__.__name__},
        )
    
    def _log_execution_metrics(self, result: TaskResult) -> None:
        """
        Log execution metrics for monitoring.
        
        Args:
            result: Task result to log
        """
        logger.info(
            f"Task {result.task_id} completed on {result.model_name}: "
            f"{result.execution_time:.2f}s, "
            f"{result.token_usage.get('total_tokens', 0)} tokens"
        )
