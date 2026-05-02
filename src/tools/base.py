from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union
import discord

class ToolContext:
    """Context passed to tools during execution."""
    def __init__(self, guild: discord.Guild, bot: Any, interaction: Optional[discord.Interaction] = None, manager: Any = None):
        self.guild = guild
        self.bot = bot
        self.interaction = interaction
        self.manager = manager
        self.user = interaction.user if interaction else None

class BaseTool(ABC):
    """Abstract base class for all tools."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def execute(self, context: ToolContext, args: Dict[str, Any]) -> Union[str, Dict[str, Any]]:
        """
        Executes the tool logic.
        Returns either a simple string or a dictionary containing 'content' and optional metadata like 'id'.
        """
        pass

class ToolRegistry:
    """Registry to manage and execute tools."""
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, name_or_tool: Any):
        """Register a tool directly or as a decorator."""
        if isinstance(name_or_tool, str):
            def decorator(func):
                self._tools[name_or_tool] = func
                return func
            return decorator
        
        # Handle BaseTool objects
        tool_name = getattr(name_or_tool, "name", None)
        if not tool_name and hasattr(name_or_tool, "__name__"):
            tool_name = name_or_tool.__name__
            
        if tool_name:
            self._tools[tool_name] = name_or_tool
        return name_or_tool

    async def execute(self, name: str, context: ToolContext, args: Dict[str, Any]) -> Any:
        tool = self._tools.get(name)
        if not tool:
            return f"Error: Tool '{name}' not found."
        try:
            return await tool.execute(context, args)
        except Exception as e:
            return f"Error executing tool '{name}': {str(e)}"

# Global registry instance
registry = ToolRegistry()
