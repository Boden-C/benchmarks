"""
Tool registry for agentic execution.

Provides a registry system for custom tools that can be used during
multi-round agentic execution.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

logger = logging.getLogger(__name__)


class Tool(ABC):
    """Abstract base class for tools."""
    
    name: str = "tool"
    description: str = "A tool"
    parameters: dict[str, Any] = {}
    
    @abstractmethod
    async def execute(self, **kwargs: Any) -> Any:
        """
        Execute the tool.
        
        Args:
            **kwargs: Tool parameters
        
        Returns:
            Tool execution result
        """
        pass
    
    def get_schema(self) -> dict[str, Any]:
        """
        Get tool schema for LLM.
        
        Returns:
            OpenAI-style function schema
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": self.parameters,
            },
        }


class ToolRegistry:
    """Registry for managing tools."""
    
    def __init__(self) -> None:
        """Initialize tool registry."""
        self.tools: dict[str, Tool] = {}
        logger.info("Initialized tool registry")
    
    def register(self, tool: Tool) -> None:
        """
        Register a tool.
        
        Args:
            tool: Tool instance to register
        """
        self.tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")
    
    def unregister(self, tool_name: str) -> None:
        """
        Unregister a tool.
        
        Args:
            tool_name: Name of tool to unregister
        """
        if tool_name in self.tools:
            del self.tools[tool_name]
            logger.info(f"Unregistered tool: {tool_name}")
    
    def get_tool(self, tool_name: str) -> Optional[Tool]:
        """
        Get tool by name.
        
        Args:
            tool_name: Name of tool
        
        Returns:
            Tool instance or None
        """
        return self.tools.get(tool_name)
    
    def get_tool_schemas(self) -> dict[str, Any]:
        """
        Get schemas for all registered tools.
        
        Returns:
            Dictionary mapping tool names to schemas
        """
        return {
            name: tool.get_schema()
            for name, tool in self.tools.items()
        }
    
    async def execute_tool(self, tool_name: str, parameters: dict[str, Any]) -> Any:
        """
        Execute a tool by name.
        
        Args:
            tool_name: Name of tool to execute
            parameters: Tool parameters
        
        Returns:
            Tool execution result
        
        Raises:
            ValueError: If tool not found
        """
        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")
        
        logger.debug(f"Executing tool: {tool_name}")
        try:
            result = await tool.execute(**parameters)
            logger.debug(f"Tool {tool_name} completed successfully")
            return result
        except Exception as e:
            logger.error(f"Tool {tool_name} execution failed: {e}")
            raise
