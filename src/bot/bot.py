import discord
import asyncio
import os
import sys
from discord.ext import commands, tasks
from typing import Dict, Any

from src.ai.handlers.timeweb import TimewebHandler
from src.core.cli.cli_manager import CLIManager
from src.core.managers.key_manager import key_manager
from src.core.managers.billing_manager import billing_manager
from src.utils.string_utils import pluralize

class WizardBot(commands.Bot):
    """The main Discord bot class for WizardBot."""
    
    def __init__(self, admin_id: int):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents, chunk_at_startup=True)
        self.admin_id = admin_id
        self.ai = TimewebHandler()
        self.cli = CLIManager(self)
        self.discord_cli_sessions: Dict[int, Any] = {}

    async def setup_hook(self):
        """Initialization hook before starting the bot."""
        await key_manager.connect()
        await billing_manager.init_db()
        print("🛠️ Система инициализирована.")
        self.amnesty_loop.start()
        
        # Load Cogs
        await self.load_extension("src.bot.cogs.ai_commands")
        await self.load_extension("src.bot.cogs.admin_commands")

    async def notify_admin_error(self, error: Exception, context: str, user_info: str = None, query: str = None):
        """Notifies the bot owner about an error via DM."""
        try:
            owner = await self.fetch_user(self.admin_id)
            import traceback
            tb = traceback.format_exc()
            await owner.send(
                f"❌ **ERROR IN {context}**\n"
                f"User: {user_info}\n"
                f"Query: {query}\n"
                f"```python\n{tb[:1800]}\n```"
            )
        except: pass

    @tasks.loop(minutes=1)
    async def amnesty_loop(self):
        """Cyclic key management checking."""
        from src.core.managers.key_manager import key_manager
        await key_manager.check_amnesty()

    async def on_ready(self):
        print(f"✨ Бот Wizard готов. Админ ID: {self.admin_id}")
        
        # --- ДИАГНОСТИКА ЗРЕНИЯ ---
        print("🔍 [DIAGNOSTIC] Checking Bot Vision:")
        for guild in self.guilds:
            print(f"   • Server: {guild.name} (ID: {guild.id})")
            print(f"   • Members visible: {len(guild.members)}")
            if len(guild.members) <= 1:
                print("   ⚠️ WARNING: Bot sees only itself! Check 'SERVER MEMBERS INTENT' in Developer Portal.")
        # --------------------------
        
        self.loop.create_task(self.update_status_task())
        await self.cli.start()

    async def update_status_task(self):
        """Background task to rotate bot status."""
        await self.wait_until_ready()
        
        # Определяем, находимся ли мы в режиме тестирования
        is_test = os.environ.get('PYTEST_CURRENT_TEST') or 'pytest' in sys.modules
        
        counter = 0
        while not self.is_closed():
            try:
                if is_test:
                    # Статус для тестов: Активен, текст "Находится на калибровке"
                    await self.change_presence(
                        status=discord.Status.online,
                        activity=discord.Activity(
                            type=discord.ActivityType.custom,
                            name="custom",
                            state="Находится на калибровке"
                        )
                    )
                    await asyncio.sleep(30)
                    continue

                if counter % 2 == 0:
                    count = len(self.guilds)
                    form = pluralize(count, ["сервер", "сервера", "серверов"])
                    await self.change_presence(activity=discord.Activity(
                        type=discord.ActivityType.watching, 
                        name=f"{count} {form} ✨"
                    ))
                else:
                    active = self.ai.active_agents
                    form = pluralize(active, ["субагент", "субагента", "субагентов"])
                    await self.change_presence(activity=discord.Activity(
                        type=discord.ActivityType.competing, 
                        name=f"{active} {form} 🌀"
                    ))
                counter += 1
            except: pass
            await asyncio.sleep(15)

    async def on_message(self, message: discord.Message):
        if message.author.bot: return
        
        # CLI integration
        if self.cli and getattr(self.cli, "session", None):
            await self.cli.session.chat_msg_received(message)
            
        for session in list(self.discord_cli_sessions.values()):
            await session.chat_msg_received(message)

        if isinstance(message.channel, discord.DMChannel):
            if message.author.id in self.discord_cli_sessions:
                if not message.content.startswith("!w login"):
                    session = self.discord_cli_sessions[message.author.id]
                    res = await session.handle_input(message.content)
                    if res == "exit": del self.discord_cli_sessions[message.author.id]
                    return
        
        await self.process_commands(message)
