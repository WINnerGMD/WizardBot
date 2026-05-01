import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

from src.core.managers.billing_manager import billing_manager
from src.core.managers.discord_manager import DiscordManager

class AdminCommands(commands.Cog):
    """Cog for administrative and billing management."""
    
    def __init__(self, bot):
        self.bot = bot

    def is_admin():
        async def predicate(ctx):
            return ctx.author.id == ctx.bot.admin_id
        return commands.check(predicate)

    @app_commands.command(name="billing", description="Проверить баланс токенов")
    async def billing_slash(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_db = await billing_manager.get_user(interaction.user.id)
        embed = discord.Embed(title="💳 Биллинг WizardBot", color=0x9B59B6)
        if user_db['is_admin'] or interaction.user.id == self.bot.admin_id:
            balance = "Безлимит ♾️"
        else:
            balance = f"{user_db['tokens']} токенов"
        
        embed.add_field(name="Баланс", value=f"`{balance}`", inline=False)
        embed.add_field(name="Пополнение", value="Обратитесь к администратору.", inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @commands.command(name="billing")
    async def billing_text(self, ctx):
        user_db = await billing_manager.get_user(ctx.author.id)
        embed = discord.Embed(title="💳 Биллинг WizardBot", color=0x9B59B6)
        balance = "Безлимит ♾️" if (user_db['is_admin'] or ctx.author.id == self.bot.admin_id) else f"{user_db['tokens']} токенов"
        embed.add_field(name="Баланс", value=f"`{balance}`", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="sync")
    @commands.is_owner()
    async def sync_cmd(self, ctx):
        await self.bot.tree.sync()
        await ctx.send("🔄 Слэш-команды синхронизированы!")

    @commands.command(name="addtokens")
    async def addtokens_text(self, ctx, user: discord.User, amount: int):
        if ctx.author.id != self.bot.admin_id: return
        await billing_manager.add_tokens(user.id, amount)
        await ctx.send(f"✅ Добавлено `{amount}` токенов {user.display_name}.")

    @commands.command(name="w")
    async def w_cmd(self, ctx, *, query: str):
        """Prefix command for AI execution (legacy support)."""
        if not ctx.guild:
            await ctx.send("⛔ Команда доступна только на серверах.")
            return

        # Gatekeeper
        mgmt_perms = {"administrator", "manage_guild", "manage_channels", "manage_roles", "manage_messages", "kick_members", "ban_members", "manage_nicknames"}
        if not ({p for p, v in ctx.author.guild_permissions if v} & mgmt_perms): return

        user_db = await billing_manager.get_user(ctx.author.id)
        is_owner = ctx.author.id == self.bot.admin_id
        if not is_owner and not user_db['is_admin'] and user_db['tokens'] <= 0:
            await ctx.send("⛔ У вас закончились токены!")
            return

        msg = await ctx.send("Wizardbot думает…")
        async def scb(spec, text, nid=None, pid=None, status="running"): 
            try: await msg.edit(content=f"🛠️ **[{spec}]** {text}...")
            except: pass

        manager = DiscordManager(ctx.guild, self.bot)
        manager.interaction = ctx # Mocking for report delivery
        
        perms = ctx.author.guild_permissions
        perms_str = f"Admin: {perms.administrator}, Manage Guild: {perms.manage_guild}"

        try:
            usage = {"total": 0}
            result = await self.bot.ai.processed_prompt(query, manager, scb, usage_context=usage, user_perms=perms_str)
            await ctx.send(result)
            if usage["total"] > 0 and not is_owner and not user_db['is_admin']:
                await billing_manager.deduct_tokens(ctx.author.id, usage["total"])
        except Exception as e:
            await ctx.send(f"Ошибка: {e}")

    @app_commands.command(name="permissions", description="Показать ваши права и доступ к боту")
    async def permissions_slash(self, interaction: discord.Interaction):
        await self._show_permissions(interaction)

    @app_commands.command(name="perms", description="Показать ваши права и доступ к боту (коротко)")
    async def perms_slash(self, interaction: discord.Interaction):
        await self._show_permissions(interaction)

    @commands.command(name="perms")
    async def perms_text(self, ctx):
        await self._show_permissions(ctx)

    async def _show_permissions(self, target):
        """Internal helper to show permissions for both slash and text commands."""
        is_interaction = isinstance(target, discord.Interaction)
        user = target.user if is_interaction else target.author
        guild = target.guild
        
        if is_interaction:
            await target.response.defer(ephemeral=True)
            
        user_db = await billing_manager.get_user(user.id)
        is_owner = user.id == self.bot.admin_id
        is_bot_admin = user_db['is_admin']
        
        mgmt_perms = {
            "administrator", "manage_guild", "manage_channels", 
            "manage_roles", "manage_messages", "kick_members", 
            "ban_members", "manage_nicknames"
        }
        
        user_actual_perms = {p for p, v in user.guild_permissions if v}
        has_mgmt = bool(user_actual_perms & mgmt_perms)
        
        # Determine internal role
        if is_owner:
            role_name = "👑 Владелец WizardBot"
            role_color = 0xFFD700 # Gold
        elif is_bot_admin:
            role_name = "🛡️ Администратор WizardBot"
            role_color = 0xE74C3C # Red
        elif has_mgmt:
            role_name = "⚙️ Менеджер Сервера"
            role_color = 0x3498DB # Blue
        else:
            role_name = "👤 Пользователь"
            role_color = 0x95A5A6 # Gray
            
        embed = discord.Embed(title="🔐 Ваши права в WizardBot", color=role_color)
        embed.set_thumbnail(url=user.display_avatar.url)
        
        embed.add_field(name="Ваша роль", value=f"**{role_name}**", inline=False)
        
        # Token balance detail
        balance = "Безлимит ♾️" if (is_bot_admin or is_owner) else f"{user_db['tokens']} токенов"
        embed.add_field(name="Баланс", value=f"`{balance}`", inline=True)
        
        # Server Access
        access_status = "✅ Полный доступ" if (has_mgmt or is_owner or is_bot_admin) else "⚠️ Ограничен (нужны права менеджера)"
        embed.add_field(name="Доступ к ИИ", value=access_status, inline=True)
        
        # Discord Perms list
        relevant_perms = [p.replace('_', ' ').capitalize() for p in (user_actual_perms & mgmt_perms)]
        perms_list_str = "\n".join([f"• {p}" for p in relevant_perms]) if relevant_perms else "Нет специальных прав"
        
        embed.add_field(name="Разрешения Discord (на этом сервере)", value=f"```\n{perms_list_str}\n```", inline=False)
        
        if is_interaction:
            await target.followup.send(embed=embed, ephemeral=True)
        else:
            await target.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))
