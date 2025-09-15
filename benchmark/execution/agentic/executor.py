"""
Multi-round agentic executor with planning and tool execution.

Implements iterative planning → execution → synthesis loop with automatic
state management, context compression, and error recovery.
"""

import asyncio
import json
import logging
import re
import time
from typing import Any, Optional

from benchmark.models import Task, TaskResult, ModelConfig
from benchmark.execution.base import Executor
from benchmark.execution.llm.factory import LLMFactory
from benchmark.execution.llm.provider import LLMProvider
from benchmark.execution.llm.exceptions import (
    TokenLimitError,
    ContentFilterError,
    InvalidResponseError,
)
from benchmark.execution.agentic.context import ExecutionContext
from benchmark.config.loader import (
    get_max_execution_rounds,
    get_compression_retries,
    get_planning_tokens,
    get_summarization_max_tokens,
    get_token_reduction_factors,
    get_content_summary_threshold,
    get_content_truncate_length,
)
from features.tools import ToolRegistry

logger = logging.getLogger(__name__)


class AgenticExecutor(Executor):
    """Multi-round agentic executor with planning and tool execution."""
    
    def __init__(
        self,
        models: list[ModelConfig],
        tool_registry: ToolRegistry,
        concurrent_summarization: bool = False,
        **kwargs
    ) -> None:
        """
        Initialize agentic executor.
        
        Args:
            models: List of model configurations
            tool_registry: Registry of available tools
            concurrent_summarization: Enable concurrent summarization
            **kwargs: Additional parameters (hooks, etc.)
        """
        super().__init__(models, **kwargs)
        self.tool_registry = tool_registry
        self.concurrent_summarization = concurrent_summarization
        self.providers: dict[str, LLMProvider] = {}
        self.planning_provider: Optional[LLMProvider] = None
        
        logger.info(f"Initialized AgenticExecutor with {len(tool_registry.tools)} tools")
    
    async def execute_task(self, task: Task) -> list[TaskResult]:
        """
        Execute task across all models.
        
        Args:
            task: Task to execute
        
        Returns:
            List of TaskResult objects
        """
        await self._run_hooks_before_task(task)
        
        logger.info(f"Executing task {task.id} with agentic mode")
        
        # Initialize providers if needed
        if not self.providers:
            await self._initialize_providers()
        
        # Execute across all models sequentially (agentic execution is complex)
        results = []
        for model in self.models:
            result = await self.execute(task, model.name)
            results.append(result)
        
        await self._run_hooks_after_task(task, results)
        
        return results
    
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
        
        # Use first model as planning provider
        if self.models:
            self.planning_provider = self.providers[self.models[0].name]
    
    async def execute(self, task: Task, model_name: str) -> TaskResult:
        """
        Execute single task with agentic workflow.
        
        Args:
            task: Task to execute
            model_name: Model identifier
        
        Returns:
            TaskResult with execution history
        """
        start_time = time.time()
        provider = self.providers[model_name]
        
        # Initialize execution context
        context = ExecutionContext(
            max_rounds=get_max_execution_rounds(),
            max_compression_attempts=get_compression_retries(),
        )
        
        accumulated_info = ""
        conversation_history = []
        tool_calls_made = []
        available_tools = self.tool_registry.get_tool_schemas()
        
        logger.info(f"Starting agentic execution for {model_name} on task {task.id}")
        
        try:
            # Multi-round execution loop
            while context.can_retry_round():
                context.start_new_round()
                logger.debug(f"Round {context.current_round}: {context.get_status_summary()}")
                
                # Plan next actions
                try:
                    plan = await self._plan_next_actions(
                        task, accumulated_info, available_tools, context
                    )
                except TokenLimitError as e:
                    if context.can_compress():
                        logger.warning(f"Token limit in planning, compressing context")
                        accumulated_info = await self.compress_accumulated_information(
                            accumulated_info,
                            get_planning_tokens(),
                            context
                        )
                        continue
                    else:
                        raise
                
                # Check if task is complete
                if plan.get("task_complete", False):
                    logger.info(f"Task marked complete at round {context.current_round}")
                    break
                
                # Execute planned tools
                planned_tools = plan.get("tool_calls", [])
                if not planned_tools:
                    logger.warning("No tools planned, ending execution")
                    break
                
                execution_results = await self._execute_planned_tools(
                    planned_tools, available_tools, context
                )
                tool_calls_made.extend(execution_results)
                
                # Update accumulated information
                accumulated_info = await self._update_state(
                    execution_results, accumulated_info, context
                )
                
                # Log token statistics
                self._log_tools_token_stats(execution_results)
            
            # Synthesize final solution
            final_response = await self._synthesize_final_solution(
                task, accumulated_info, context
            )
            
            execution_time = time.time() - start_time
            
            result = TaskResult(
                task_id=task.id,
                model_name=model_name,
                response=final_response,
                execution_time=execution_time,
                success=True,
                conversation_history=conversation_history,
                tool_calls=tool_calls_made,
                available_tools=available_tools,
                metadata={
                    "mode": "agentic",
                    "rounds": context.current_round,
                    "compressions": context.compression_attempts,
                    "token_reductions": context.token_reduction_attempts,
                },
            )
            
            logger.info(
                f"Agentic execution completed for {model_name}: "
                f"{context.current_round} rounds, {len(tool_calls_made)} tool calls"
            )
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Agentic execution failed for {model_name}: {e}")
            
            return TaskResult(
                task_id=task.id,
                model_name=model_name,
                response="",
                execution_time=execution_time,
                success=False,
                error=str(e),
                conversation_history=conversation_history,
                tool_calls=tool_calls_made,
                available_tools=available_tools,
                metadata={
                    "mode": "agentic",
                    "rounds": context.current_round,
                    "error_type": e.__class__.__name__,
                },
            )
    
    async def _plan_next_actions(
        self,
        task: Task,
        accumulated_info: str,
        available_tools: dict[str, Any],
        context: ExecutionContext
    ) -> dict[str, Any]:
        """
        Plan next tool executions.
        
        Args:
            task: Current task
            accumulated_info: Accumulated information from previous rounds
            available_tools: Available tool schemas
            context: Execution context
        
        Returns:
            Parsed plan with tool calls
        """
        prompt = self._build_planning_prompt(task, accumulated_info, available_tools)
        
        response = await self.planning_provider.get_completion(
            system_prompt="You are a helpful planning assistant. Analyze the task and available information to plan the next actions.",
            user_prompt=prompt,
            max_tokens=get_planning_tokens(),
            temperature=0.7,
        )
        
        # Parse response as JSON
        try:
            plan = self.planning_provider.clean_and_parse_json(response)
            return plan
        except Exception as e:
            if context.can_fix_format():
                context.increment_format_fixes()
                logger.warning(f"Failed to parse plan, attempting fix: {e}")
                return self._fix_invalid_json_format(response)
            else:
                raise InvalidResponseError(f"Cannot parse planning response: {e}")
    
    async def _execute_planned_tools(
        self,
        planned_tools: list[dict[str, Any]],
        available_tools: dict[str, Any],
        context: ExecutionContext
    ) -> list[dict[str, Any]]:
        """
        Execute planned tools.
        
        Args:
            planned_tools: List of tool call specifications
            available_tools: Available tool schemas
            context: Execution context
        
        Returns:
            List of execution result dicts
        """
        results = []
        
        for tool_spec in planned_tools:
            tool_name = tool_spec.get("name")
            parameters = tool_spec.get("parameters", {})
            
            if not tool_name or tool_name not in available_tools:
                logger.warning(f"Tool not available: {tool_name}")
                results.append({
                    "tool": tool_name,
                    "success": False,
                    "error": "Tool not available",
                })
                continue
            
            try:
                result = await self.tool_registry.execute_tool(tool_name, parameters)
                results.append({
                    "tool": tool_name,
                    "parameters": parameters,
                    "success": True,
                    "result": result,
                })
                logger.debug(f"Tool {tool_name} executed successfully")
            except Exception as e:
                logger.error(f"Tool {tool_name} execution failed: {e}")
                results.append({
                    "tool": tool_name,
                    "parameters": parameters,
                    "success": False,
                    "error": str(e),
                })
        
        return results
    
    async def _update_state(
        self,
        execution_results: list[dict[str, Any]],
        accumulated_info: str,
        context: ExecutionContext
    ) -> str:
        """
        Update accumulated information with execution results.
        
        Args:
            execution_results: Tool execution results
            accumulated_info: Current accumulated information
            context: Execution context
        
        Returns:
            Updated accumulated_information string
        """
        # Format execution results
        new_info = "\n\n--- Round {} Results ---\n".format(context.current_round)
        
        for result in execution_results:
            tool_name = result.get("tool", "unknown")
            if result.get("success"):
                tool_result = result.get("result", "")
                # Truncate large results
                if len(str(tool_result)) > get_content_truncate_length():
                    tool_result = str(tool_result)[:get_content_truncate_length()] + "... [truncated]"
                new_info += f"\n{tool_name}: {tool_result}\n"
            else:
                error = result.get("error", "Unknown error")
                new_info += f"\n{tool_name}: ERROR - {error}\n"
        
        updated_info = accumulated_info + new_info
        
        # Check if compression needed
        if self._estimate_token_count(updated_info) > get_content_summary_threshold():
            if context.can_compress():
                logger.info("Accumulated info exceeds threshold, compressing")
                updated_info = await self.compress_accumulated_information(
                    updated_info,
                    get_summarization_max_tokens(),
                    context
                )
        
        return updated_info
    
    async def _synthesize_final_solution(
        self,
        task: Task,
        accumulated_info: str,
        context: ExecutionContext
    ) -> str:
        """
        Synthesize final solution from accumulated information.
        
        Args:
            task: Original task
            accumulated_info: All accumulated information
            context: Execution context
        
        Returns:
            Synthesized solution string
        """
        # Get original question
        user_message = next(
            (msg.content for msg in task.messages if msg.role == "user"),
            ""
        )
        
        prompt = f"""Based on the following accumulated information, provide a final answer to the original question.

Original Question: {user_message}

Accumulated Information:
{accumulated_info}

Provide a clear, concise answer to the question."""
        
        response = await self.planning_provider.get_completion(
            system_prompt="You are a helpful assistant that synthesizes information to answer questions.",
            user_prompt=prompt,
            max_tokens=4096,
            temperature=0.7,
        )
        
        return response
    
    async def compress_accumulated_information(
        self,
        accumulated_info: str,
        max_tokens: int,
        context: ExecutionContext
    ) -> str:
        """
        Compress accumulated information using LLM summarization.
        
        Args:
            accumulated_info: Text to compress
            max_tokens: Target token count
            context: Execution context
        
        Returns:
            Compressed string
        """
        if not context.can_compress():
            logger.warning("Maximum compression attempts reached, using fallback")
            return self._fallback_rule_based_compression(accumulated_info, max_tokens)
        
        context.mark_compressed()
        
        # Get token reduction factors
        reduction_factors = get_token_reduction_factors()
        factor = reduction_factors[min(context.compression_attempts - 1, len(reduction_factors) - 1)]
        target_tokens = int(max_tokens * factor)
        
        logger.info(f"Compressing with factor {factor}, target: {target_tokens} tokens")
        
        try:
            compressed = await self._summarize_content(
                accumulated_info,
                target_tokens,
                retry_count=0
            )
            return compressed
        except Exception as e:
            logger.error(f"Compression failed: {e}, using fallback")
            return self._fallback_rule_based_compression(accumulated_info, max_tokens)
    
    async def _summarize_content(
        self,
        content: str,
        max_tokens: int,
        retry_count: int
    ) -> str:
        """
        Summarize content using LLM.
        
        Args:
            content: Content to summarize
            max_tokens: Maximum tokens in summary
            retry_count: Current retry attempt
        
        Returns:
            Summarized content
        """
        prompt = f"""Summarize the following information, preserving all critical details and insights:

{content}

Provide a comprehensive summary."""
        
        summary = await self.planning_provider.get_completion(
            system_prompt="You are an expert at summarizing information while preserving critical details.",
            user_prompt=prompt,
            max_tokens=max_tokens,
            temperature=0.3,
        )
        
        return summary
    
    def _fallback_rule_based_compression(self, text: str, max_tokens: int) -> str:
        """
        Rule-based compression fallback.
        
        Args:
            text: Text to compress
            max_tokens: Target token count
        
        Returns:
            Compressed text
        """
        # Estimate characters per token (rough approximation)
        chars_per_token = 4
        target_chars = max_tokens * chars_per_token
        
        if len(text) <= target_chars:
            return text
        
        # Keep first and last portions
        keep_per_side = target_chars // 2
        compressed = (
            text[:keep_per_side] +
            "\n\n... [content compressed] ...\n\n" +
            text[-keep_per_side:]
        )
        
        logger.debug(f"Applied rule-based compression: {len(text)} -> {len(compressed)} chars")
        return compressed
    
    def _estimate_token_count(self, text: str) -> int:
        """
        Estimate token count for text.
        
        Args:
            text: Text to estimate
        
        Returns:
            Estimated token count
        """
        # Rough approximation: 1 token ≈ 4 characters
        return len(text) // 4
    
    def _log_tools_token_stats(self, execution_results: list[dict[str, Any]]) -> None:
        """
        Log token statistics for tool executions.
        
        Args:
            execution_results: Tool execution results
        """
        for result in execution_results:
            if result.get("success"):
                tool_name = result.get("tool", "unknown")
                result_data = str(result.get("result", ""))
                tokens = self._estimate_token_count(result_data)
                logger.debug(f"Tool {tool_name} returned ~{tokens} tokens")
    
    def _is_token_limit_error(self, error: Exception) -> bool:
        """
        Check if error is token limit related.
        
        Args:
            error: Exception to check
        
        Returns:
            True if token limit error
        """
        return isinstance(error, TokenLimitError)
    
    def _is_content_filter_error(self, error: Exception) -> bool:
        """
        Check if error is content filter related.
        
        Args:
            error: Exception to check
        
        Returns:
            True if content filter error
        """
        return isinstance(error, ContentFilterError)
    
    def _fix_invalid_json_format(self, invalid_json: str) -> dict[str, Any]:
        """
        Attempt to fix invalid JSON.
        
        Args:
            invalid_json: Malformed JSON string
        
        Returns:
            Parsed dict
        
        Raises:
            InvalidResponseError: If fix fails
        """
        # Try removing markdown code blocks
        cleaned = invalid_json.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines)
        
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Last resort: return minimal valid structure
            logger.warning("Cannot fix JSON, returning default structure")
            return {"task_complete": False, "tool_calls": []}
    
    def _build_planning_prompt(
        self,
        task: Task,
        accumulated_info: str,
        available_tools: dict[str, Any]
    ) -> str:
        """
        Build planning prompt for LLM.
        
        Args:
            task: Current task
            accumulated_info: Accumulated information
            available_tools: Available tool schemas
        
        Returns:
            Planning prompt string
        """
        user_message = next(
            (msg.content for msg in task.messages if msg.role == "user"),
            ""
        )
        
        tools_desc = "\n".join([
            f"- {name}: {schema.get('description', 'No description')}"
            for name, schema in available_tools.items()
        ])
        
        prompt = f"""Task: {user_message}

Available Tools:
{tools_desc}

Accumulated Information:
{accumulated_info or "(none yet)"}

Plan the next actions to complete the task. Respond with JSON:
{{
    "task_complete": true/false,
    "reasoning": "your reasoning",
    "tool_calls": [
        {{"name": "tool_name", "parameters": {{"param": "value"}}}}
    ]
}}"""
        
        return prompt
    
    def _build_execution_summary(
        self,
        execution_results: list[dict[str, Any]],
        total_rounds: int
    ) -> str:
        """
        Format execution history into readable text.
        
        Args:
            execution_results: All tool execution results
            total_rounds: Total rounds executed
        
        Returns:
            Summary string
        """
        summary = f"Execution completed in {total_rounds} rounds.\n\n"
        
        for i, result in enumerate(execution_results, 1):
            tool_name = result.get("tool", "unknown")
            success = result.get("success", False)
            summary += f"{i}. {tool_name}: {'SUCCESS' if success else 'FAILED'}\n"
        
        return summary
