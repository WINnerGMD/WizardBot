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

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))
