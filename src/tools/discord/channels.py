import discord
from typing import Any, Dict
from src.tools.base import BaseTool, ToolContext, registry
from src.core.utils.discord_utils import (
    build_overwrites, check_perms
)

class CreateCategoryTool(BaseTool):
    name = "create_category"
    async def execute(self, ctx: ToolContext, args: Dict[str, Any]) -> Any:
        if not check_perms(ctx.user, manage_channels=True):
            return "⛔ ОШИБКА: У вас нет прав на управление каналами в Discord."
        name = args.get('name')
        if not name: return "⛔ ОШИБКА: Не указано имя категории."
        overwrites = build_overwrites(ctx.guild, args.get('permissions'))
        cat = await ctx.guild.create_category(name, overwrites=overwrites or None)
        return f"Категория '{name}' (ID: {cat.id}) создана."

class CreateTextChannelTool(BaseTool):
    name = "create_text_channel"
    async def execute(self, ctx: ToolContext, args: Dict[str, Any]) -> Any:
        if not check_perms(ctx.user, manage_channels=True):
            return "⛔ ОШИБКА: У вас нет прав на управление каналами в Discord."
        name = args.get('name')
        if not name: return "⛔ ОШИБКА: Не указано имя канала."
        cat_ref = args.get('category_name', '')
        cat = ctx.guild.get_channel(int(cat_ref)) if str(cat_ref).isdigit() else discord.utils.get(ctx.guild.categories, name=cat_ref)
        overwrites = build_overwrites(ctx.guild, args.get('permissions'))
        raw_nsfw = args.get('nsfw', False)
        nsfw = str(raw_nsfw).lower() == 'true' if isinstance(raw_nsfw, str) else bool(raw_nsfw)
        ch = await ctx.guild.create_text_channel(name, category=cat, overwrites=overwrites or None, nsfw=nsfw)
        return f"Канал '{name}' (ID: {ch.id}, NSFW: {nsfw}) создан."

class CreateVoiceChannelTool(BaseTool):
    name = "create_voice_channel"
    async def execute(self, ctx: ToolContext, args: Dict[str, Any]) -> Any:
        if not check_perms(ctx.user, manage_channels=True):
            return "⛔ ОШИБКА: У вас нет прав на управление каналами в Discord."
        name = args.get('name')
        if not name: return "⛔ ОШИБКА: Не указано имя канала."
        cat_ref = args.get('category_name', '')
        cat = ctx.guild.get_channel(int(cat_ref)) if str(cat_ref).isdigit() else discord.utils.get(ctx.guild.categories, name=cat_ref)
        overwrites = build_overwrites(ctx.guild, args.get('permissions'))
        ch = await ctx.guild.create_voice_channel(name, category=cat, overwrites=overwrites or None)
        return f"Голосовой канал '{name}' (ID: {ch.id}) создан."

class EditChannelTool(BaseTool):
    name = "edit_channel"
    async def execute(self, ctx: ToolContext, args: Dict[str, Any]) -> Any:
        if not check_perms(ctx.user, manage_channels=True):
            return "⛔ ОШИБКА: У вас нет прав на управление каналами в Discord."
        old, new = args.get('old_name'), args.get('new_name')
        ch = ctx.guild.get_channel(int(old)) if str(old).isdigit() else discord.utils.get(ctx.guild.channels, name=old)
        if ch: 
            await ch.edit(name=new)
            return f"Канал успешно переименован в '{new}'."
        return "Канал не найден."

class CreateForumChannelTool(BaseTool):
    name = "create_forum_channel"
    async def execute(self, ctx: ToolContext, args: Dict[str, Any]) -> Any:
        if not check_perms(ctx.user, manage_channels=True):
            return "⛔ ОШИБКА: У вас нет прав на управление каналами в Discord."
        name = args.get('name')
        if not name: return "⛔ ОШИБКА: Не указано имя форума."
        cat_ref = args.get('category_name', '')
        cat = ctx.guild.get_channel(int(cat_ref)) if str(cat_ref).isdigit() else discord.utils.get(ctx.guild.categories, name=cat_ref)
        overwrites = build_overwrites(ctx.guild, args.get('permissions'))
        tags = [discord.ForumTag(name=t) for t in (args.get('tags') or [])]
        topic = args.get('topic', '') or args.get('Topic', '')
        forum = await ctx.guild.create_forum(
            name=name, 
            category=cat, 
            topic=topic, 
            overwrites=overwrites or None, 
            available_tags=tags
        )
        return f"Форум '{forum.name}' создан."

class DeleteChannelTool(BaseTool):
    name = "delete_channel"
    async def execute(self, ctx: ToolContext, args: Dict[str, Any]) -> Any:
        if not check_perms(ctx.user, manage_channels=True):
            return "⛔ ОШИБКА: У вас нет прав на удаление каналов."
        ch_ref = args.get('name')
        ch = ctx.guild.get_channel(int(ch_ref)) if str(ch_ref).isdigit() else discord.utils.get(ctx.guild.channels, name=ch_ref)
        if ch: 
            await ch.delete()
            return f"Канал {ch_ref} удален."
        return "Канал не найден."

class DeleteAllChannelsTool(BaseTool):
    name = "delete_all_channels"
    async def execute(self, ctx: ToolContext, args: Dict[str, Any]) -> Any:
        if not check_perms(ctx.user, manage_channels=True):
            return "⛔ ОШИБКА: У вас нет прав на массовое удаление каналов."
        
        # Check bot's own permissions
        bot_member = ctx.guild.me
        if not bot_member.guild_permissions.manage_channels:
            return "⛔ ОШИБКА: У самого бота нет прав 'Управление каналами' на этом сервере."

        count = 0
        cat_ref = args.get('category_name')
        
        # Filter channels to delete
        to_delete = []
        target_desc = ""

        if cat_ref:
            cat = ctx.guild.get_channel(int(cat_ref)) if str(cat_ref).isdigit() else discord.utils.get(ctx.guild.categories, name=cat_ref)
            if not cat: return f"Категория '{cat_ref}' не найдена."
            to_delete = list(cat.channels)
            target_desc = f"в категории '{cat.name}'"
        else:
            confirm = args.get('confirm_full_wipe', False)
            if not confirm:
                return "⛔ ОШИБКА: Для удаления ВСЕХ каналов на сервере укажите confirm_full_wipe=True в аргументах."
            to_delete = list(ctx.guild.channels)
            target_desc = "на всем сервере"

        if not to_delete:
            return f"Инфо: На сервере '{ctx.guild.name}' нет каналов для удаления {target_desc}."

        errors = 0
        deleted_names = []
        
        # Sequential deletion to avoid heavy rate limits, but we can try small batches
        # Actually Discord rate limits are ~2 per second for channel deletion
        for ch in to_delete:
            try:
                name = ch.name
                await ch.delete(reason="Wizards protocol: Mass wipe")
                count += 1
                deleted_names.append(name)
            except discord.Forbidden:
                errors += 1
            except Exception as e:
                print(f"[ERROR] Failed to delete {ch.name}: {e}")
                errors += 1
        
        status = "💀 ПОЛНАЯ ЗИЧИСТКА" if not cat_ref else "🗑️ ОЧИСТКА"
        err_msg = f" (Ошибок: {errors})" if errors > 0 else ""
        return f"{status}: Удалено {count} каналов {target_desc} на сервере '{ctx.guild.name}'{err_msg}."

class SetChannelPermissionsTool(BaseTool):
    name = "set_channel_permissions"
    async def execute(self, ctx: ToolContext, args: Dict[str, Any]) -> Any:
        if not check_perms(ctx.user, manage_roles=True):
            return "⛔ ОШИБКА: У вас нет прав на управление правами каналов."
        target = args.get('channel_id', '')
        ch = ctx.guild.get_channel(int(target)) if str(target).isdigit() else discord.utils.get(ctx.guild.channels, name=target)
        if not ch: return "Канал не найден."
        
        from src.core.utils.discord_utils import PERM_MAP, resolve_role
        
        for entry in args.get('permissions', []):
            role = resolve_role(ctx.guild, entry.get('target', ''))
            if not role: continue
            overwrite = ch.overwrites_for(role)
            for p in (entry.get('allow') or []):
                attr = PERM_MAP.get(p.lower())
                if attr: setattr(overwrite, attr, True)
            for p in (entry.get('deny') or []):
                attr = PERM_MAP.get(p.lower())
                if attr: setattr(overwrite, attr, False)
            await ch.set_permissions(role, overwrite=overwrite)
        return "Права применены."

# Registering tools
registry.register(CreateCategoryTool())
registry.register(CreateTextChannelTool())
registry.register(CreateVoiceChannelTool())
registry.register(EditChannelTool())
registry.register(CreateForumChannelTool())
class MoveChannelTool(BaseTool):
    name = "move_channel"
    async def execute(self, ctx: ToolContext, args: Dict[str, Any]) -> Any:
        if not check_perms(ctx.user, manage_channels=True):
            return "⛔ ОШИБКА: У вас нет прав на перемещение каналов."
        ch_id = args.get('channel_id')
        ch = ctx.guild.get_channel(int(ch_id)) if str(ch_id).isdigit() else discord.utils.get(ctx.guild.channels, name=ch_id)
        if not ch: return "Канал не найден."
        
        edit_kwargs = {}
        if 'category_id' in args:
            cat_id = args['category_id']
            cat = ctx.guild.get_channel(int(cat_id)) if str(cat_id).isdigit() else discord.utils.get(ctx.guild.categories, name=cat_id)
            if cat: edit_kwargs['category'] = cat
        
        if 'position' in args:
            edit_kwargs['position'] = args['position']
            
        if not edit_kwargs:
            return "Не указаны параметры для перемещения (category_id или position)."
            
        await ch.edit(**edit_kwargs)
        return f"Канал '{ch.name}' перемещен."

registry.register(DeleteChannelTool())
registry.register(DeleteAllChannelsTool())
registry.register(MoveChannelTool())
registry.register(SetChannelPermissionsTool())
