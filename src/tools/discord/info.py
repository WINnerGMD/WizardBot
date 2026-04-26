import discord
import re
from typing import Any, Dict
from src.tools.base import BaseTool, ToolContext, registry
from src.core.utils.discord_utils import resolve_member

class ListServerInfoTool(BaseTool):
    name = "list_server_info"
    async def execute(self, ctx: ToolContext, args: Dict[str, Any]) -> Any:
        return {
            "roles": {r.name: r.id for r in ctx.guild.roles if r.name != "@everyone"},
            "categories": {cat.name: cat.id for cat in ctx.guild.categories},
            "channels": [f"{c.name}:{c.id} (Type: {c.type})" for c in ctx.guild.channels if not isinstance(c, discord.CategoryChannel)],
        }

class ListRolesTool(BaseTool):
    name = "list_roles"
    async def execute(self, ctx: ToolContext, args: Dict[str, Any]) -> Any:
        roles = {r.name: r.id for r in ctx.guild.roles if r.name != "@everyone"}
        if not roles:
            try:
                fetched_roles = await ctx.guild.fetch_roles()
                roles = {r.name: r.id for r in fetched_roles if r.name != "@everyone"}
            except:
                pass
        return roles

class ListChannelsTool(BaseTool):
    name = "list_channels"
    async def execute(self, ctx: ToolContext, args: Dict[str, Any]) -> Any:
        return {
            "categories": {cat.name: cat.id for cat in ctx.guild.categories},
            "channels": [f"{c.name}:{c.id} (Type: {c.type}, Category: {c.category.name if c.category else 'None'})" for c in ctx.guild.channels if not isinstance(c, discord.CategoryChannel)],
        }

class FetchMessageInfoTool(BaseTool):
    name = "fetch_message_info"
    async def execute(self, ctx: ToolContext, args: Dict[str, Any]) -> Any:
        url_or_id = (args.get("url_or_id") or "").strip()
        m = re.search(r"/channels/\d+/(?P<channel>\d+)/(?P<message>\d+)", url_or_id)
        if m:
            ch = ctx.guild.get_channel(int(m.group("channel")))
            if ch:
                msg = await ch.fetch_message(int(m.group("message")))
                return {"author": str(msg.author), "content": msg.content}
        return "Не удалось получить сообщение."

class ReadChannelHistoryTool(BaseTool):
    name = "read_channel_history"
    async def execute(self, ctx: ToolContext, args: Dict[str, Any]) -> Any:
        target = args.get("channel_name", "")
        if not target or str(target).lower() == "current":
            ch = ctx.interaction.channel if ctx.interaction else None
        else:
            ch = ctx.guild.get_channel(int(target)) if str(target).isdigit() else discord.utils.get(ctx.guild.channels, name=target)
            
        if not ch: return "Канал не найден или не указан контекст."
        
        limit = min(int(args.get("limit", 5)), 30)
        history = []
        async for msg in ch.history(limit=limit):
            if msg.content.startswith("!w") or msg.content.startswith("/prompt"): continue
            msg_data = [f"Автор: {msg.author.display_name}"]
            if msg.content: msg_data.append(f"Текст:\n{msg.content}")
            for i, e in enumerate(msg.embeds):
                eb = [f"[Embed {i}] Title: {e.title or '-'}", f"Desc: {e.description or '-'}"]
                for f in e.fields: eb.append(f"{f.name}: {f.value}")
                msg_data.append(" | ".join(eb))
            if len(msg_data) > 1: history.append("\n".join(msg_data))
        history.reverse()
        return "\n-----\n".join(history) if history else "Контекст не найден."

class QueryUsersTool(BaseTool):
    name = "query_users"
    async def execute(self, ctx: ToolContext, args: Dict[str, Any]) -> Any:
        q = args.get("query", "")
        # Используем кэш из менеджера если он есть
        cache = getattr(ctx.manager, '_member_cache', None)
        member, matches = await resolve_member(ctx.guild, q, cache=cache)
        if not matches:
            return "Никто не найден. Попробуйте поискать по-другому (транслит, часть имени)."
        return [f"{m.display_name} (ID: {m.id}, Name: {m.name})" for m in matches[:20]]

class GetServerStyleTool(BaseTool):
    name = "get_server_style"
    async def execute(self, ctx: ToolContext, args: Dict[str, Any]) -> Any:
        representative_channels = []
        # Берем по 2 канала из каждой категории, которые видны @everyone
        everyone_role = ctx.guild.default_role
        for cat in ctx.guild.categories:
            perms = cat.permissions_for(everyone_role)
            if perms.view_channel:
                for ch in cat.channels[:3]:
                    representative_channels.append(f"#{ch.name} (in {cat.name})")
        
        # Если категорий нет или каналов мало, берем просто первые 10 публичных
        if len(representative_channels) < 5:
            for ch in ctx.guild.text_channels[:15]:
                perms = ch.permissions_for(everyone_role)
                if perms.view_channel and f"#{ch.name}" not in str(representative_channels):
                    representative_channels.append(f"#{ch.name}")

        style_summary = "\n".join(representative_channels[:20])
        return (
            "АНАЛИЗ СТИЛИСТИКИ СЕРВЕРА:\n"
            "Используй эти примеры как образец для нейминга (эмодзи, регистр, префиксы):\n"
            f"{style_summary}\n\n"
            "ЗАПРЕЩЕНО спрашивать у пользователя название, если ты можешь вывести его из стиля или контекста."
        )

# Registering tools
registry.register(ListServerInfoTool())
registry.register(ListRolesTool())
registry.register(ListChannelsTool())
registry.register(FetchMessageInfoTool())
registry.register(ReadChannelHistoryTool())
registry.register(QueryUsersTool())
registry.register(GetServerStyleTool())
