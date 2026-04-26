from src.tools.base import registry

# Import all tool modules to trigger registration
import src.tools.discord.info
import src.tools.discord.roles
import src.tools.discord.channels
import src.tools.discord.messaging

def get_registry():
    return registry
