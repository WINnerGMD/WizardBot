import discord
import re
from typing import Any, Dict
from src.tools.base import BaseTool, ToolContext, registry
from src.core.utils.discord_utils import (
    parse_color, build_role_permissions, resolve_role, 
    resolve_member, check_perms, can_touch_role
)

class CreateRoleTool(BaseTool):
    name = "create_role"
    async def execute(self, ctx: ToolContext, args: Dict[str, Any]) -> Any:
        if not check_perms(ctx.user, manage_roles=True):
            return "⛔ ОШИБКА: У вас нет прав на управление ролями в Discord."
        color = parse_color(args.get('color_hex'))
        perms = build_role_permissions(args.get('permissions'))
        role = await ctx.guild.create_role(
            name=args['name'], 
            color=color, 
            hoist=args.get('hoist', False), 
            mentionable=args.get('mentionable', False), 
            permissions=perms
        )
        return f"Роль '{role.name}' (ID: {role.id}) создана."

class EditRoleTool(BaseTool):
    name = "edit_role"
    async def execute(self, ctx: ToolContext, args: Dict[str, Any]) -> Any:
        if not check_perms(ctx.user, manage_roles=True):
            return "⛔ ОШИБКА: У вас нет прав на управление ролями в Discord."
        ref = args.get('role_id', '')
        role = await resolve_role(ctx.guild, ref)
        if not role: return "Роль не найдена."
        if not can_touch_role(ctx.user, role):
            return f"⛔ ОШИБКА: Роль '{role.name}' выше или равна вашей по иерархии."
        
        kwargs = {}
        if 'name' in args: kwargs['name'] = args['name']
        if 'color_hex' in args: kwargs['color'] = parse_color(args['color_hex'])
        if 'hoist' in args: kwargs['hoist'] = args['hoist']
        if 'mentionable' in args: kwargs['mentionable'] = args['mentionable']
        if 'permissions' in args: kwargs['permissions'] = build_role_permissions(args['permissions'])
        
        await role.edit(**kwargs)
        return f"Роль обновлена."

class DeleteRoleTool(BaseTool):
    name = "delete_role"
    async def execute(self, ctx: ToolContext, args: Dict[str, Any]) -> Any:
        if not check_perms(ctx.user, manage_roles=True):
            return "⛔ ОШИБКА: У вас нет прав на управление ролями в Discord."
        role = await resolve_role(ctx.guild, args['name'])
        if role: 
            if not can_touch_role(ctx.user, role):
                return f"⛔ ОШИБКА: Роль '{role.name}' выше или равна вашей по иерархии."
            await role.delete()
            return "Роль удалена."
        return "Роль не найдена."

class AssignRoleToUserTool(BaseTool):
    name = "assign_role_to_user"
    async def execute(self, ctx: ToolContext, args: Dict[str, Any]) -> Any:
        if not check_perms(ctx.user, manage_roles=True):
            return "⛔ ОШИБКА: У бота нет прав на управление ролями."
        
        r_query = args.get('role_name_or_id')
        u_query = args.get('user_name_or_id')
        
        role = await resolve_role(ctx.guild, r_query)
        if not role:
            try:
                role = await ctx.guild.create_role(name=r_query, reason="Авто-создание по запросу")
            except Exception as e:
                return f"❌ Не удалось создать роль '{r_query}': {e}"

        cache = getattr(ctx.manager, '_member_cache', None)
        member, matches = await resolve_member(ctx.guild, u_query, cache=cache)
        
        if not member:
            if len(matches) > 1:
                options = [f"{m.display_name} ({m.id})" for m in matches[:25]]
                choice = await ctx.manager.ask_user_clarification(
                    f"Нашел несколько человек по запросу '{u_query}'. Кто из них?", 
                    "select", 
                    options
                )
                if "Timed out" in choice or "Cancelled" in choice: return "Отменено."
                mid = int(re.search(r'\((\d+)\)', choice).group(1))
                member = ctx.guild.get_member(mid)
            else:
                choice = await ctx.manager.ask_user_clarification(f"Участник '{u_query}' не найден. Выберите вручную:", "user_select")
                if "Timed out" in choice or "Cancelled" in choice: return "Отменено."
                member = ctx.guild.get_member(int(choice))

        if role and member:
            if not can_touch_role(ctx.user, role):
                return f"⚠️ ОШИБКА: Роль '{role.name}' выше бота в иерархии."
            await member.add_roles(role)
            return f"✅ Роль '{role.name}' выдана {member.display_name}."
        return "Ошибка: не удалось определить участника или роль."

class RemoveRoleFromUserTool(BaseTool):
    name = "remove_role_from_user"
    async def execute(self, ctx: ToolContext, args: Dict[str, Any]) -> Any:
        if not check_perms(ctx.user, manage_roles=True):
            return "⛔ ОШИБКА: У вас нет прав на управление ролями в Discord."
        role = await resolve_role(ctx.guild, args.get('role_name_or_id'))
        q = args.get('user_name_or_id')
        cache = getattr(ctx.manager, '_member_cache', None)
        member, matches = await resolve_member(ctx.guild, q, cache=cache)

        if not member:
            if len(matches) > 1:
                options = [f"{m.display_name} ({m.id})" for m in matches[:25]]
                choice = await ctx.manager.ask_user_clarification(f"Найдено несколько '{q}'. Выберите:", "select", options)
                if "Timed out" in choice: return "Отмена."
                mid = int(re.search(r'\((\d+)\)', choice).group(1))
                member = ctx.guild.get_member(mid)
            else:
                choice = await ctx.manager.ask_user_clarification(f"Участник '{q}' не найден. Выберите вручную:", "user_select")
                if "Timed out" in choice: return "Отмена."
                member = ctx.guild.get_member(int(choice))

        if role and member: 
            if not can_touch_role(ctx.user, role):
                return f"⛔ ОШИБКА: Роль '{role.name}' выше или равна вашей по иерархии."
            await member.remove_roles(role)
            return f"✅ Роль '{role.name}' снята с {member.display_name}."
        return "Не удалось найти роль или юзера."

class AssignRoleToAllUsersTool(BaseTool):
    name = "assign_role_to_all_users"
    async def execute(self, ctx: ToolContext, args: Dict[str, Any]) -> Any:
        if not check_perms(ctx.user, manage_roles=True):
            return "⛔ ОШИБКА: У вас нет прав на управление ролями в Discord."
        role = await resolve_role(ctx.guild, args['role_name_or_id'])
        if not role: return "Роль не найдена."
        if not can_touch_role(ctx.user, role):
            return f"⛔ ОШИБКА: Роль '{role.name}' выше или равна вашей по иерархии."
        count = 0
        for m in ctx.guild.members:
            if not m.bot and role not in m.roles:
                try: 
                    await m.add_roles(role)
                    count += 1
                except: 
                    continue
        return f"Роль выдана {count} участникам."

class RemoveAllRolesFromUserTool(BaseTool):
    name = "remove_all_roles_from_user"
    async def execute(self, ctx: ToolContext, args: Dict[str, Any]) -> Any:
        if not check_perms(ctx.user, manage_roles=True):
            return "⛔ ОШИБКА: У вас нет прав на управление ролями."
        user_ref = args.get('user_name_or_id')
        member = ctx.guild.get_member(int(user_ref)) if str(user_ref).isdigit() else None
        if member:
            rs = [r for r in member.roles if not r.is_default()]
            if rs: 
                # Фильтруем те, что мы можем трогать
                touchable = [r for r in rs if can_touch_role(ctx.user, r)]
                if touchable:
                    await member.remove_roles(*touchable)
                    return f"Роли ({len(touchable)}) удалены у {member.name}."
                return "Нет ролей, доступных для удаления (иерархия)."
            return "Ролей нет."
        return "Юзер не найден."

class DeleteAllRolesTool(BaseTool):
    name = "delete_all_roles"
    async def execute(self, ctx: ToolContext, args: Dict[str, Any]) -> Any:
        if not check_perms(ctx.user, manage_roles=True):
            return "⛔ ОШИБКА: У вас нет прав на управление ролями."
        
        # Фильтруем роли: не managed (интеграции), не @everyone
        roles = [r for r in ctx.guild.roles if not r.managed and not r.is_default()]
        count = 0
        errors = 0
        for r in roles:
            if can_touch_role(ctx.user, r):
                try:
                    await r.delete()
                    count += 1
                except:
                    errors += 1
            else:
                errors += 1
        
        return f"Удалено {count} ролей. Ошибок (иерархия/права): {errors}."

# Registering tools
registry.register(CreateRoleTool())
registry.register(EditRoleTool())
registry.register(DeleteRoleTool())
registry.register(AssignRoleToUserTool())
registry.register(RemoveRoleFromUserTool())
registry.register(AssignRoleToAllUsersTool())
registry.register(RemoveAllRolesFromUserTool())
registry.register(DeleteAllRolesTool())
