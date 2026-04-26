import discord
import time
import asyncio
from discord import app_commands
from discord.ext import commands
from typing import Dict, Any

from src.core.managers.discord_manager import DiscordManager
from src.core.managers.billing_manager import billing_manager
from src.bot.ui.components import render_progress_board, PlanConfirmationView

class AICommands(commands.Cog):
    """Cog for core AI functionality: prompt, plan, consult."""
    
    def __init__(self, bot):
        self.bot = bot
        self.mgmt_perms = {
            "administrator", "manage_guild", "manage_channels", 
            "manage_roles", "manage_messages", "kick_members", 
            "ban_members", "manage_nicknames"
        }

    def _check_access(self, interaction: discord.Interaction) -> bool:
        user_perms = {p for p, v in interaction.user.guild_permissions if v}
        is_owner = interaction.user.id == self.bot.admin_id
        return bool(user_perms & self.mgmt_perms or is_owner)

    @app_commands.command(name="prompt", description="Запустить ИИ без планирования (быстро)")
    async def prompt_cmd(self, interaction: discord.Interaction, query: str):
        # 1. Мгновенно бронируем взаимодействие (лимит 3 сек)
        use_channel_fallback = False
        try:
            await interaction.response.defer()
        except discord.errors.NotFound:
            print(f"[WARN] interaction.response.defer() 404. Falling back to channel.send for {interaction.user}")
            use_channel_fallback = True

        # fallback_message will track the sent message if interaction fails
        fallback_msg = None

        # 2. Проверяем права после defer
        if not self._check_access(interaction):
            if use_channel_fallback:
                await interaction.channel.send("⛔ Доступ ограничен.")
            else:
                await interaction.followup.send("⛔ Доступ ограничен.", ephemeral=True)
            return

        user_db = await billing_manager.get_user(interaction.user.id)
        is_owner = interaction.user.id == self.bot.admin_id
        if not is_owner and not user_db['is_admin'] and user_db['tokens'] <= 0:
            msg = "⛔ У вас недостаточно токенов для выполнения этой команды."
            if use_channel_fallback:
                await interaction.channel.send(msg)
            else:
                await interaction.edit_original_response(content=msg)
            return

        manager = DiscordManager(interaction.guild, self.bot, interaction)
        
        # Используем оригинальный ответ для борда прогресса (надежнее чем followup)
        try:
            await interaction.edit_original_response(content="```\n[ WIZARDBOT ] Инициализация...\n```")
        except: pass
        
        board = {}
        last_render = [0.0]

        async def status_cb(spec, text, nid, pid=None, status="running"):
            nonlocal fallback_msg
            if nid not in board: 
                board[nid] = {"spec": spec, "text": text, "tick": time.time(), "status": status, "pid": pid}
            else: 
                board[nid].update({"text": text, "status": status, "pid": pid})
            
            # Рендерим не чаще чем раз в секунду
            if time.time() - last_render[0] > 1.2 or status == "done":
                last_render[0] = time.time()
                try: 
                    if use_channel_fallback:
                         if not fallback_msg:
                             fallback_msg = await interaction.channel.send(content=render_progress_board(board))
                         else:
                             await fallback_msg.edit(content=render_progress_board(board))
                    else:
                        await interaction.edit_original_response(content=render_progress_board(board))
                except discord.HTTPException as e:
                    if e.code in (50027, 10015): # Invalid Token / Unknown Webhook
                        pass # Просто игнорируем обновление статуса, если токен сдох
                    else:
                        print(f"[DEBUG] Status update failed: {e}")

        active_perms = [p for p, v in interaction.user.guild_permissions if v]
        perms_str = ",".join(active_perms)

        is_done = False
        
        async def animation_loop():
            nonlocal fallback_msg
            while not is_done:
                try:
                    if use_channel_fallback:
                        if fallback_msg:
                            await fallback_msg.edit(content=render_progress_board(board))
                    else:
                        await interaction.edit_original_response(content=render_progress_board(board))
                except: pass
                await asyncio.sleep(2.0) # Замедляем, чтобы не спамить в API и не забивать канал

        # Запускаем цикл анимации в фоне
        anim_task = asyncio.create_task(animation_loop())

        try:
            usage = {"total": 0}
            res = await self.bot.ai.processed_prompt(
                query, manager, status_cb, 
                usage_context=usage, user_perms=perms_str, mode="prompt"
            )
            
            is_done = True
            anim_task.cancel()
            
            # Финальное обновление борда
            try:
                for k in board: board[k].update({"status": "done", "text": "Завершено"})
                if use_channel_fallback:
                    if fallback_msg:
                        await fallback_msg.edit(content=render_progress_board(board))
                else:
                    await interaction.edit_original_response(content=render_progress_board(board))
            except: pass
            
            # Отправка премиум-отчета
            await manager.send_premium_report(res)
            
            if usage["total"] > 0 and not is_owner and not user_db['is_admin']:
                await billing_manager.deduct_tokens(interaction.user.id, usage["total"])
        except Exception as e:
            is_done = True
            anim_task.cancel()
            # Если это не ошибка токена, логируем как критическую
            if not isinstance(e, discord.HTTPException) or e.code not in (50027, 10015):
                await self.bot.notify_admin_error(e, "PROMPT", user_info=str(interaction.user), query=query)
            
            try:
                await interaction.followup.send("⚠️ Произошла ошибка при выполнении.", ephemeral=True)
            except: pass

    @app_commands.command(name="consult", description="Запустить ИИ в режиме консультации")
    async def consult_cmd(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()
        
        if not self._check_access(interaction):
            await interaction.followup.send("⛔ Доступ ограничен.", ephemeral=True)
            return
        manager = DiscordManager(interaction.guild, self.bot, interaction)
        
        try:
            await interaction.edit_original_response(content="🔍 Исследую вопрос...")
        except: pass

        async def status_cb(spec, text, nid=None, pid=None, status="running"):
            try: 
                await interaction.edit_original_response(content=f"🔍 **[{spec}]** {text}...")
            except discord.HTTPException as e:
                if e.code in (50027, 10015): pass
                else: print(f"[DEBUG] Consult status failed: {e}")
            except: pass

        try:
            active_perms = [p for p, v in interaction.user.guild_permissions if v]
            res = await self.bot.ai.processed_prompt(query, manager, status_cb, usage_context=usage, user_perms=",".join(active_perms), mode="consult")
            await manager.send_premium_report(res)
        except Exception as e:
            await interaction.followup.send(f"Ошибка: {e}")

    @app_commands.command(name="plan", description="Запустить планирование")
    async def plan_cmd(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()
        
        if not self._check_access(interaction):
            await interaction.followup.send("⛔ Доступ ограничен.", ephemeral=True)
            return
        manager = DiscordManager(interaction.guild, self.bot, interaction)
        
        try:
            await interaction.edit_original_response(content="Preparing plan...")
        except: pass

        async def progress_cb(plan_text: str):
            view = PlanConfirmationView(interaction.user.id)
            try:
                await interaction.edit_original_response(content=f"📑 **План действий:**\n```text\n{plan_text}\n```", view=view)
            except:
                try: await interaction.followup.send(content=f"📑 **План действий:**\n```text\n{plan_text}\n```", view=view)
                except: return False # Fatal
            
            await view.wait()
            return bool(view.confirmed)

        try:
            res = await self.bot.ai.process_with_plan(query, manager, progress_cb, mode="plan")
            if res != "CANCELLED": await manager.send_premium_report(res)
        except Exception as e:
            await interaction.followup.send(f"Ошибка: {e}")

async def setup(bot):
    await bot.add_cog(AICommands(bot))
