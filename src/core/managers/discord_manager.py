import discord
import asyncio
import time
from typing import Any, Dict, List, Optional

from src.tools.base import registry, ToolContext
from src.bot.ui.components import ClarificationView, TextInputModal
from src.core.utils.discord_utils import resolve_member

class DiscordManager:
    """Manages Discord interactions and orchestrates tool execution."""
    
    def __init__(self, guild: discord.Guild, bot: Any, interaction: Optional[discord.Interaction] = None):
        self.guild = guild
        self.bot = bot
        self.interaction = interaction
        self._member_cache: List[discord.Member] = []
        self._last_fetch_time = 0
        self._cache_ttl = 600
        
        # Shared state for the current request session
        self.shared_state: Dict[str, Any] = {}
        self.state_events: Dict[str, asyncio.Event] = {}

    def set_shared_value(self, key: str, value: Any):
        """Sets a value in the shared session state and triggers associated events."""
        self.shared_state[key] = value
        if key in self.state_events:
            self.state_events[key].set()

    async def wait_for_shared_value(self, key: str, timeout: float = 300.0) -> Any:
        """Waits for a value to appear in the shared state (async)."""
        if key in self.shared_state:
            return self.shared_state[key]
        
        if key not in self.state_events:
            self.state_events[key] = asyncio.Event()
        
        try:
            await asyncio.wait_for(self.state_events[key].wait(), timeout=timeout)
            return self.shared_state.get(key)
        except asyncio.TimeoutError:
            return None

    async def _ensure_member_cache(self):
        """Ensures the member cache is up to date."""
        now = time.time()
        
        # Если в guild.members уже есть люди (благодаря chunk_at_startup=True), просто берем их
        # Это мгновенно и не нагружает сеть
        if len(self.guild.members) > 1:
            if not self._member_cache or (now - self._last_fetch_time > self._cache_ttl):
                self._member_cache = list(self.guild.members)
                self._last_fetch_time = now
            return

        # Если же список пуст, значит чанкинг еще не завершился или выключен
        if not self._member_cache or (now - self._last_fetch_time > self._cache_ttl):
            try:
                # Ограничиваем fetch_members, чтобы не вешать бота на гигантских серверах
                # Лучше иметь неполный кэш, чем получить Unknown Interaction
                self._member_cache = [m async for m in self.guild.fetch_members(limit=1000)]
                self._last_fetch_time = now
            except Exception as e:
                print(f"[WARN] Failed to fetch members: {e}")
                self._member_cache = list(self.guild.members)

    async def execute_tool(self, name: str, args: Dict[str, Any]) -> Any:
        """Executes a tool by name with given arguments."""
        await self._ensure_member_cache()
        
        context = ToolContext(
            guild=self.guild,
            bot=self.bot,
            interaction=self.interaction,
            manager=self
        )
        
        # Network retry logic
        max_retries = 3
        last_error = None
        
        for attempt in range(max_retries):
            try:
                return await registry.execute(name, context, args)
            except Exception as e:
                import aiohttp
                if isinstance(e, (aiohttp.ClientError, asyncio.TimeoutError)):
                    last_error = e
                    await asyncio.sleep(2 * (attempt + 1))
                    continue
                return f"Error: {str(e)}"
        
        return f"Network Error after {max_retries} attempts: {str(last_error)}"

    async def ask_user_clarification(self, question: str, input_type: str = "buttons", options: Optional[List[str]] = None) -> str:
        """Asks user for clarification using Discord UI components."""
        if not self.interaction:
            return "CLARIFICATION_REQUIRED_IN_CLI"

        # Gatekeeper for permission questions
        q_lower = (question or "").lower()
        if any(word in q_lower for word in ["прав", "разрешен", "админ", "permission", "admin"]):
            return "ИИ ОШИБКА: Запрещено задавать вопросы о правах доступа."

        if input_type == "text_input":
            modal = TextInputModal(question)
            if not self.interaction.response.is_done():
                await self.interaction.response.send_modal(modal)
                await modal.wait()
                return modal.result or "Cancelled"
            return "Error: Cannot show modal in this context."

        view = ClarificationView(self.interaction.user.id, options, input_type, question)
        msg = await self.interaction.followup.send(content=f"🔔 **Запрос подтверждения:**\n{question}", view=view)
        
        if await view.wait():
            try: await msg.edit(content="❌ Время ожидания истекло.", view=None)
            except: pass
            return "Timed out"
        
        return str(view.result)

    async def send_premium_report(self, text: str):
        """Sends a beautiful report embed."""
        text = (text or "").strip()
        usage_info = ""
        if "📊" in text:
            parts = text.split("📊", 1)
            text = parts[0].strip()
            usage_info = "📊 " + parts[1].strip().replace("`", "")

        embed = discord.Embed(
            title="Wizardbot",
            description=text,
            color=0x2B90D9
        )
        
        if self.bot and getattr(self.bot, "user", None):
            embed.set_author(name="Wizardbot", icon_url=self.bot.user.display_avatar.url)
        
        if usage_info:
            embed.set_footer(text=usage_info)
            
        embed.timestamp = discord.utils.utcnow()
        
        if not self.interaction:
            print(f"\n[CLI-REPORT] {text}\n{usage_info}")
            return

        try:
            await self.interaction.followup.send(embed=embed)
        except:
            try: await self.interaction.channel.send(embed=embed)
            except:
                try: await self.interaction.user.send(embed=embed)
                except: print("CRITICAL: Failed to deliver report.")
