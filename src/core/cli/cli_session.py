import asyncio
import datetime
import sys
from src.core.managers.key_manager import key_manager

class CLISession:
    def __init__(self, bot, user, output_callback, is_discord=False):
        self.bot = bot
        self.user = user  # dict from cli_users
        self.output_callback = output_callback  # async def (text)
        self.is_discord = is_discord
        self.mode = "normal"
        self.chat_channel_id = None
        self.specialist_name = None
        self.logs_enabled = False

    def f(self, ansi_str: str, plain_str: str) -> str:
        """Вспомогательная функция для форматирования в зависимости от того, локальная это консоль или дискорд."""
        if self.is_discord:
            return plain_str
        return ansi_str

    async def handle_input(self, line: str):
        if not line or not line.strip():
            return
            
        line = line.strip()
        
        if self.mode == "chatting":
            if line.lower() == "/exit":
                self.mode = "normal"
                self.chat_channel_id = None
                await self.output_callback(self.f("🔌 \033[1;33mРежим чата отключен.\033[0m", "🔌 **Режим чата отключен.**"))
                return
            await self._send_to_chat(line)
            return

        if self.mode == "specialist":
            if line.lower() == "/exit":
                self.mode = "normal"
                self.specialist_name = None
                await self.output_callback(self.f("🔌 \033[1;33mРежим специалиста отключен.\033[0m", "🔌 **Режим специалиста отключен.**"))
                return
            await self._handle_specialist_input(line)
            return

        parts = line.split()
        cmd = parts[0].lower()
        if cmd.startswith('/'):
            cmd = cmd[1:]
        args = parts[1:]
        
        try:
            if cmd == "help":
                await self._cmd_help()
            elif cmd in ["servers", "guilds"]:
                await self._cmd_servers()
            elif cmd == "status":
                await self._cmd_status()
            elif cmd == "keys":
                await self._cmd_keys()
            elif cmd == "addkey":
                await self._cmd_addkey(args)
            elif cmd == "connect":
                await self._cmd_specialist(args)
            elif cmd == "unfreeze":
                await self._cmd_unfreeze()
            elif cmd == "guild":
                await self._cmd_guild(args)
            elif cmd == "channels":
                await self._cmd_channels(args)
            elif cmd == "send":
                await self._cmd_send(args)
            elif cmd == "broadcast":
                await self._cmd_broadcast(args)
            elif cmd == "logs":
                self.logs_enabled = not self.logs_enabled
                state = "ВКЛЮЧЕНЫ" if self.logs_enabled else "ВЫКЛЮЧЕНЫ"
                await self.output_callback(self.f(f"📜 \033[1;36mЛоги {state}\033[0m", f"📜 **Логи {state}**"))
            elif cmd == "chatting":
                await self._cmd_chatting(args)
            elif cmd in ["specialist", "connect"]:
                await self._cmd_specialist(args)
            elif cmd in ["exit", "quit", "stop"]:
                if self.is_discord:
                    await self.output_callback("🔌 Сессия завершена.")
                    return "exit" # Signal to caller to close session
                else:
                    await self.output_callback(self.f("\033[1;31mЗавершение работы системы...\033[0m", "Завершение..."))
                    await self.bot.close()
                    sys.exit(0)
            else:
                await self.output_callback(f"❓ Неизвестная команда: {cmd}. Введите 'help' для справки.")
        except Exception as e:
            await self.output_callback(f"⚠️ Ошибка выполнения: {e}")
            
    async def log(self, tag: str, message: str):
        if not self.logs_enabled: return
        await self.output_callback(self.f(f"📜 \033[1;30m[{tag}]\033[0m {message}", f"`[{tag}]` {message}"))
        
    async def chat_msg_received(self, message):
        if self.mode != "chatting":
            return
            
        is_match = False
        if getattr(self, 'chat_target_type', 'channel') == 'user':
            if message.author.id == self.chat_channel_id:
                is_match = True
        else:
            if message.channel.id == self.chat_channel_id:
                is_match = True
                
        if is_match:
            author_str = str(message.author)
            content = message.content
            await self.output_callback(self.f(f"\n💬 \033[1;36m[{author_str}]\033[0m {content}", f"**[{author_str}]**: {content}"))

    async def _send_to_chat(self, text: str):
        if not self.chat_channel_id: return
        try:
            if getattr(self, 'chat_target_type', 'channel') == 'user':
                target = self.bot.get_user(self.chat_channel_id)
                if not target:
                    try:
                        target = await self.bot.fetch_user(self.chat_channel_id)
                    except:
                        pass
            else:
                target = self.bot.get_channel(self.chat_channel_id)
                
            if not target:
                await self.output_callback("❌ Цель (Канал / Пользователь) недоступна.")
                return
            await target.send(text)
        except Exception as e:
            await self.output_callback(f"❌ Ошибка отправки: {e}")

    async def _cmd_help(self):
        msg = []
        msg.append(self.f("\n\033[1;36m--- СПРАВКА ПО КОМАНДАМ ---\033[0m", "```\n--- СПРАВКА ПО КОМАНДАМ ---"))
        cmds = [
            ("status", "Общий статус системы и пула ключей"),
            ("servers/guilds", "Список всех подключенных серверов"),
            ("guild <id>", "Детальная информация о сервере"),
            ("channels <id>", "Список текстовых каналов сервера"),
            ("keys", "Состояние пула API ключей (Gemini)"),
            ("addkey <key>", "Добавить новый ключ в базу"),
            ("unfreeze", "Разморозить все ключи (кроме BANNED)"),
            ("send <cid> <t>", "Отправить сообщение в канал по ID"),
            ("broadcast <t>", "Объявление на все серверы"),
            ("logs", "Включить/выключить логи в реальном времени"),
            ("chatting <cid>", "Войти в режим чата с каналом/юзером"),
            ("connect [name]", "Войти в режим управления субагентом (без аргументов — список)"),
            ("exit/quit", "Завершить работу/сессию")
        ]
        for cmd, d in cmds:
            msg.append(self.f(f"  \033[1;33m{cmd.ljust(15)}\033[0m - {d}", f"/{cmd.ljust(15)} - {d}"))
        msg.append(self.f("\033[1;36m---------------------------\033[0m\n", "```"))
        await self.output_callback("\n".join(msg))

    async def _cmd_servers(self):
        msg = [self.f(f"\n\033[1;32m--- ПОДКЛЮЧЕННЫЕ СЕРВЕРЫ ({len(self.bot.guilds)}) ---\033[0m", f"```\n--- ПОДКЛЮЧЕННЫЕ СЕРВЕРЫ ({len(self.bot.guilds)}) ---")]
        for g in self.bot.guilds:
            name = (g.name[:25] + '..') if len(g.name) > 25 else g.name.ljust(25)
            msg.append(self.f(f" • \033[1;37m{name}\033[0m | ID: \033[1;30m{g.id}\033[0m | Юзеров: {g.member_count}", f" • {name} | ID: {g.id} | Юзеров: {g.member_count}"))
        msg.append(self.f("\033[1;32m-----------------------------------------------\033[0m\n", "```"))
        await self.output_callback("\n".join(msg))

    async def _cmd_status(self):
        stats = await key_manager.get_stats()
        msg = [
            self.f("\n\033[1;35m--- СТАТУС СИСТЕМЫ ---\033[0m", "```\n--- СТАТУС СИСТЕМЫ ---"),
            self.f(f"📡 Discord:  \033[1;32m[ CONNECTED ]\033[0m", f"Discord:  [ CONNECTED ]"),
            f"🏘️ Серверов: {len(self.bot.guilds)}",
            f"⚙️ Субагенты: {getattr(self.bot.ai, 'active_agents', 0)}",
            self.f(f"🔑 Ключи:     \033[1;32m{stats['active']} OK\033[0m / \033[1;33m{stats['frozen']} Frozen\033[0m / \033[1;31m{stats['banned']} Banned\033[0m", f"Ключи:    {stats['active']} OK / {stats['frozen']} Frozen / {stats['banned']} Banned"),
            f"📈 Запросов: {stats['total_requests']}",
            self.f("\033[1;35m----------------------\033[0m\n", "```")
        ]
        await self.output_callback("\n".join(msg))

    async def _cmd_keys(self):
        stats = await key_manager.get_stats()
        msg = [self.f(f"\n\033[1;34m--- ПУЛ КЛЮЧЕЙ: {stats['total_keys']} ВСЕГО ---\033[0m", f"```\n--- ПУЛ КЛЮЧЕЙ: {stats['total_keys']} ВСЕГО ---")]
        async with key_manager.pool.acquire() as conn:
            rows = await conn.fetch("SELECT key_string, status, unfreeze_time, total_requests FROM api_keys ORDER BY status DESC, unfreeze_time ASC NULLS LAST")
        for r in rows:
            icon = "✅" if r['status'] == 'ACTIVE' else ("⏳" if r['status'] in ['DAILY_LIMIT', 'RATE_LIMITED'] else "💀")
            unfreeze = ""
            if r['unfreeze_time'] and r['unfreeze_time'] > datetime.datetime.now():
                rem = r['unfreeze_time'] - datetime.datetime.now()
                unfreeze = f" (wait {int(rem.total_seconds())}s)"
            key_disp = f"{r['key_string'][:8]}...{r['key_string'][-4:]}"
            msg.append(self.f(f" {icon} \033[1;37m{key_disp}\033[0m | {r['status'].ljust(12)} | Req: {str(r['total_requests']).ljust(5)}{unfreeze}", f"{icon} {key_disp} | {r['status'].ljust(12)} | Req: {str(r['total_requests']).ljust(5)}{unfreeze}"))
        msg.append(self.f("\033[1;34m---------------------------------------\033[0m\n", "```"))
        await self.output_callback("\n".join(msg))

    async def _cmd_addkey(self, args):
        if not args:
            await self.output_callback("❌ Ошибка: Укажите строку ключа.")
            return
        await key_manager.add_key(args[0])
        await self.output_callback(self.f(f"✅ Ключ \033[1;37m{args[0][:10]}...\033[0m успешно добавлен.", f"✅ Ключ `{args[0][:10]}...` успешно добавлен."))

    async def _cmd_unfreeze(self):
        async with key_manager.pool.acquire() as conn:
            await conn.execute("UPDATE api_keys SET status = 'ACTIVE', unfreeze_time = NULL WHERE status != 'BANNED'")
        await self.output_callback("🔓 Все ключи (кроме забаненных) разморожены.")

    async def _cmd_guild(self, args):
        if not args:
            await self.output_callback("❌ Ошибка: Укажите ID сервера.")
            return
        try:
            gid = int(args[0])
            guild = self.bot.get_guild(gid)
            if not guild:
                await self.output_callback(self.f(f"❌ Сервер \033[1;31m{gid}\033[0m не найден.", f"❌ Сервер `{gid}` не найден."))
                return
            msg = [
                self.f(f"\n\033[1;36m--- ИНФО О СЕРВЕРЕ: {guild.name} ---\033[0m", f"```\n--- ИНФО О СЕРВЕРЕ: {guild.name} ---"),
                f"🆔 ID:       {guild.id}",
                f"👑 Владелец: {guild.owner} (ID: {guild.owner_id})",
                f"👥 Участники: {guild.member_count}",
                f"📅 Создан:   {guild.created_at.strftime('%Y-%m-%d')}",
                f"📂 Каналов:  {len(guild.channels)}",
                f"🎖️ Ролей:    {len(guild.roles)}",
                self.f("\033[1;36m--------------------------------------\033[0m\n", "```")
            ]
            await self.output_callback("\n".join(msg))
        except ValueError:
            await self.output_callback("❌ Ошибка: Неверный формат ID.")

    async def _cmd_channels(self, args):
        if not args:
            await self.output_callback("❌ Ошибка: Укажите ID сервера.")
            return
        try:
            gid = int(args[0])
            guild = self.bot.get_guild(gid)
            if not guild:
                await self.output_callback(self.f(f"❌ Сервер \033[1;31m{gid}\033[0m не найден.", f"❌ Сервер `{gid}` не найден."))
                return
            msg = [self.f(f"\n\033[1;33m--- КАНАЛЫ СЕРВЕРА: {guild.name} ---\033[0m", f"```\n--- КАНАЛЫ СЕРВЕРА: {guild.name} ---")]
            for ch in guild.text_channels:
                msg.append(self.f(f" # \033[1;37m{ch.name.ljust(20)}\033[0m | ID: \033[1;30m{ch.id}\033[0m", f" # {ch.name.ljust(20)} | ID: {ch.id}"))
            msg.append(self.f("\033[1;33m------------------------------------\033[0m\n", "```"))
            await self.output_callback("\n".join(msg))
        except ValueError:
            await self.output_callback("❌ Ошибка: Неверный формат ID.")

    async def _cmd_send(self, args):
        if len(args) < 2:
            await self.output_callback(self.f("📝 Использование: \033[1;33msend <channel_id> <текст>\033[0m", "📝 Использование: `send <channel_id> <текст>`"))
            return
        try:
            cid = int(args[0])
            text = " ".join(args[1:])
            channel = self.bot.get_channel(cid)
            if not channel:
                await self.output_callback(self.f(f"❌ Канал \033[1;31m{cid}\033[0m не найден или недоступен.", f"❌ Канал `{cid}` не найден или недоступен."))
                return
            await channel.send(text)
            await self.output_callback(self.f(f"✅ Отправлено в \033[1;36m#{channel.name}\033[0m (\033[1;37m{channel.guild.name}\033[0m)", f"✅ Отправлено в `#{channel.name}` (`{channel.guild.name}`)"))
        except Exception as e:
            await self.output_callback(f"❌ Ошибка отправки: {e}")

    async def _cmd_broadcast(self, args):
        if not args:
            await self.output_callback(self.f("📝 Использование: \033[1;33mbroadcast <текст>\033[0m", "📝 Использование: `broadcast <текст>`"))
            return
        text = " ".join(args)
        count = 0
        await self.output_callback("📢 Рассылка запущена...")
        for guild in self.bot.guilds:
            targets = []
            if guild.system_channel: targets.append(guild.system_channel)
            targets.extend(guild.text_channels)
            for ch in targets:
                if ch.permissions_for(guild.me).send_messages:
                    try:
                        await ch.send(f"🔮 **[ОБЪЯВЛЕНИЕ]** {text}")
                        count += 1
                        break
                    except:
                        continue
        await self.output_callback(f"✅ Рассылка завершена. Охвачено серверов: {count}")

    async def _cmd_chatting(self, args):
        if not args:
            await self.output_callback("❌ Укажите ID канала (или -u <id> для пользователя) для чата.")
            return
            
        is_user = False
        target_id_str = args[0]
        
        if args[0] == "-u":
            if len(args) < 2:
                await self.output_callback("❌ Укажите ID пользователя после -u.")
                return
            is_user = True
            target_id_str = args[1]

        try:
            target_id = int(target_id_str)
            if is_user:
                target = self.bot.get_user(target_id)
                if not target:
                    try:
                        target = await self.bot.fetch_user(target_id)
                    except:
                        pass
                
                if not target:
                    await self.output_callback("❌ Пользователь не найден.")
                    return
                    
                self.mode = "chatting"
                self.chat_channel_id = target_id
                self.chat_target_type = "user"
                name_disp = f"@{target.name}"
            else:
                target = self.bot.get_channel(target_id)
                if not target:
                    await self.output_callback("❌ Канал не найден.")
                    return
                self.mode = "chatting"
                self.chat_channel_id = target_id
                self.chat_target_type = "channel"
                name_disp = f"#{target.name}"
                
            await self.output_callback(self.f(f"🎯 \033[1;32mВход в режим чата с {name_disp}\033[0m\n(Введите /exit для выхода)", f"🎯 **Вход в режим чата с {name_disp}**\n*(Введите /exit для выхода)*"))
        except ValueError:
            await self.output_callback("❌ Неверный формат ID. Должны быть цифры.")
    async def _cmd_specialist(self, args):
        from src.ai.specialists import SPECIALISTS
        if not args:
            msg = [self.f("\n\033[1;36m--- ДОСТУПНЫЕ СПЕЦИАЛИСТЫ ---\033[0m", "```\n--- ДОСТУПНЫЕ СПЕЦИАЛИСТЫ ---")]
            for name, spec in SPECIALISTS.items():
                msg.append(self.f(f" • \033[1;33m{name.ljust(25)}\033[0m | {spec.get('name')}", f" • {name.ljust(25)} | {spec.get('name')}"))
            msg.append(self.f("\n\033[1;30mИспользуйте: connect <имя>\033[0m", "\nИспользуйте: /connect <имя>"))
            msg.append(self.f("\033[1;36m------------------------------\033[0m\n", "```"))
            await self.output_callback("\n".join(msg))
            return
        
        spec_name = args[0]
        if spec_name not in SPECIALISTS:
            await self.output_callback(f"❌ Специалист '{spec_name}' не найден. Введите 'connect' для списка.")
            return
        
        self.mode = "specialist"
        self.specialist_name = spec_name
        name_up = spec_name.upper()
        await self.output_callback(self.f(
            f"🛠️ \033[1;32mВход в режим управления: {name_up}\033[0m\nКоманды: \033[1;37m/tools, /info, /call <name> <json>, <текст для ИИ>\033[0m\n(Введите /exit для выхода)",
            f"🛠️ **Вход в режим управления: {name_up}**\nКоманды: `/tools`, `/info`, `/call <name> <json>`, `<текст для ИИ>`\n*(Введите /exit для выхода)*"
        ))

    async def _handle_specialist_input(self, line: str):
        line = line.strip()
        parts = line.split(maxsplit=2)
        cmd = parts[0].lower()
        
        # Support both 'tools' and '/tools'
        if cmd in ["tools", "/tools"]:
            from src.ai.specialists import SPECIALISTS
            tools = SPECIALISTS[self.specialist_name].get("tools", [])
            if not tools:
                await self.output_callback(f"ℹ️ У специалиста {self.specialist_name} нет инструментов.")
                return
            msg = [self.f(f"📋 \033[1;36mДоступные инструменты для {self.specialist_name}:\033[0m", f"📋 **Доступные инструменты для {self.specialist_name}:**")]
            for t in tools: msg.append(f"  - {t}")
            await self.output_callback("\n".join(msg))
            return

        if cmd == "/info":
            from src.ai.specialists import SPECIALISTS
            spec = SPECIALISTS[self.specialist_name]
            msg = [
                self.f(f"🛠️ \033[1;32mИНФО: {self.specialist_name.upper()}\033[0m", f"🛠️ **ИНФО: {self.specialist_name.upper()}**"),
                f"📝 Инструкция: {spec['instruction'][:200]}...",
                f"🧠 Модель: {spec.get('model', 'default')}"
            ]
            await self.output_callback("\n".join(msg))
            return
            
        if cmd in ["call", "/call"]:
            if len(parts) < 2:
                await self.output_callback("❌ Ошибка: /call <имя_инструмента> <опциональный_json>")
                return
            t_name = parts[1]
            t_args_raw = parts[2] if len(parts) > 2 else "{}"
            try:
                import json
                t_args = json.loads(t_args_raw)
                await self.output_callback(self.f(f"⚙️ \033[1;30mПрямой вызов {t_name}...\033[0m", f"⚙️ *Прямой вызов {t_name}...*"))
                
                from src.core.managers.discord_manager import DiscordManager
                guild = self.bot.guilds[0] if self.bot.guilds else None
                if not guild:
                    await self.output_callback("❌ Ошибка: Бот не подключен ни к одному серверу.")
                    return
                manager = DiscordManager(guild, bot=self.bot)
                
                res = await manager.execute_tool(t_name, t_args)
                await self.output_callback(self.f(f"✅ \033[1;32mРезультат:\033[0m {res}", f"✅ **Результат:** {res}"))
            except Exception as e:
                await self.output_callback(f"❌ Ошибка вызова: {e}")
            return
                
        # AI Inference Mode
        await self.output_callback(self.f(f"🧠 \033[1;30m{self.specialist_name} думает...\033[0m", f"🧠 *{self.specialist_name} думает...*"))
        from src.ai.handlers.timeweb import TimewebHandler
        from src.core.managers.discord_manager import DiscordManager
        
        handler = TimewebHandler()
        guild = self.bot.guilds[0] if self.bot.guilds else None
        if not guild:
            await self.output_callback("❌ Ошибка: Бот не подключен ни к одному серверу.")
            return
        manager = DiscordManager(guild, bot=self.bot)
        
        usage = {"total": 0}
        res = await handler._run_agent(self.specialist_name, line, manager, usage_context=usage)
        
        content = res.get('content', '')
        reports = res.get('reports', [])
        
        out = [content]
        if reports:
            out.append(self.f("\n\033[1;36m--- ОТЧЕТ ВЫПОЛНЕНИЯ ---\033[0m", "\n**--- ОТЧЕТ ВЫПОЛНЕНИЯ ---**"))
            for r in reports:
                out.append(f" • {r}")
                
        out.append(self.f(f"\n\033[1;30m📊 {usage['total']} tokens.\033[0m", f"\n*📊 {usage['total']} tokens.*"))
        await self.output_callback("\n".join(out))
