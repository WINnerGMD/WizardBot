from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
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
    async def execute(self, context: ToolContext, args: Dict[str, Any]) -> Any:
        pass

class ToolRegistry:
    """Registry to manage and execute tools."""
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        self._tools[tool.name] = tool

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
