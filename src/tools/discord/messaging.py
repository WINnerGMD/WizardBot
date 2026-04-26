import discord
from typing import Any, Dict
from src.tools.base import BaseTool, ToolContext, registry
from src.core.utils.discord_utils import parse_color

class SendEmbedMessageTool(BaseTool):
    name = "send_embed_message"
    async def execute(self, ctx: ToolContext, args: Dict[str, Any]) -> Any:
        ch_ref = args.get('channel_name')
        ch = ctx.guild.get_channel(int(ch_ref)) if str(ch_ref).isdigit() else discord.utils.get(ctx.guild.channels, name=ch_ref)
        if not ch: return "Канал не найден."
        
        embed = discord.Embed(
            title=args.get('title'), 
            description=args.get('description'), 
            color=parse_color(args.get('color_hex'))
        )
        for f in args.get('fields', []): 
            embed.add_field(name=f['name'], value=f['value'], inline=f.get('inline', False))
        if args.get('footer'): embed.set_footer(text=args['footer'])
        if args.get('image_url'): embed.set_image(url=args['image_url'])
        
        await ch.send(embed=embed)
        return "Embed отправлен."

class SendWebhookMessageTool(BaseTool):
    name = "send_webhook_message"
    async def execute(self, ctx: ToolContext, args: Dict[str, Any]) -> Any:
        ch_ref = args.get('channel_name')
        ch = ctx.guild.get_channel(int(ch_ref)) if str(ch_ref).isdigit() else discord.utils.get(ctx.guild.channels, name=ch_ref)
        if not ch: return "Канал не найден."
        
        wh = await ch.create_webhook(name=args.get("webhook_name") or "Wizardbot")
        try: 
            await wh.send(
                content=args.get("content"), 
                username=args.get("webhook_name"), 
                avatar_url=args.get("avatar_url")
            )
        finally: 
            await wh.delete()
        return "Webhook сообщение отправлено."

class PinMessageTool(BaseTool):
    name = "pin_message"
    async def execute(self, ctx: ToolContext, args: Dict[str, Any]) -> Any:
        ch_ref = args.get("channel_id")
        ch = ctx.guild.get_channel(int(ch_ref)) if str(ch_ref).isdigit() else discord.utils.get(ctx.guild.channels, name=ch_ref)
        if not ch: return "Канал не найден."
        msg = await ch.fetch_message(int(args["message_id"]))
        await msg.pin()
        return f"Сообщение {args['message_id']} закреплено в {ch.name}."

class AskUserClarificationTool(BaseTool):
    name = "ask_user_clarification"
    async def execute(self, ctx: ToolContext, args: Dict[str, Any]) -> Any:
        return await ctx.manager.ask_user_clarification(
            args.get("question"), 
            args.get("input_type", "buttons"), 
            args.get("options")
        )

class EditServerSettingsTool(BaseTool):
    name = "edit_server_settings"
    async def execute(self, ctx: ToolContext, args: Dict[str, Any]) -> Any:
        kwargs = {}
        if "name" in args: kwargs["name"] = args["name"]
        if "description" in args: kwargs["description"] = args["description"]
        if "verification_level" in args:
            lvl = args["verification_level"].lower()
            kwargs["verification_level"] = getattr(discord.VerificationLevel, lvl, discord.VerificationLevel.none)
        if "default_notifications" in args:
            dn = args["default_notifications"].lower()
            kwargs["default_notifications"] = getattr(discord.NotificationLevel, dn, discord.NotificationLevel.all_messages)
        
        await ctx.guild.edit(**kwargs)
        return f"Настройки сервера обновлены: {list(kwargs.keys())}"

# Registering tools
registry.register(SendEmbedMessageTool())
registry.register(SendWebhookMessageTool())
registry.register(PinMessageTool())
registry.register(AskUserClarificationTool())
registry.register(EditServerSettingsTool())
