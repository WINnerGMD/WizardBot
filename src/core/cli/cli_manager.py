import asyncio
import sys
from src.core.cli.cli_session import CLISession
from src.core.managers.cli_user_manager import cli_users

class CLIManager:
    def __init__(self, bot):
        self.bot = bot
        self.running = False
        user = cli_users.get_user("admin")
        if not user: # Fallback in case admin was entirely deleted somehow
            cli_users.create_user("admin", "admin", "admin")
            user = cli_users.get_user("admin")
            
        async def output_cb(text):
            print(text)
            
        self.session = CLISession(bot, user, output_cb, is_discord=False)
        self.session.user['login'] = 'local_admin' # used to identify local

    async def start(self):
        self.running = True
        print("\n\033[1;35m" + "╔══════════════════════════════════════════════════════╗")
        print("║             🔮  WIZARD CONTROL TERMINAL              ║")
        print("║                [ VERSION 2.6.0-CORE ]                ║")
        print("╠══════════════════════════════════════════════════════╣")
        print("║  System: ONLINE                                      ║")
        print("║  AI Bridge: DISCONNECTED (ADMIN MODE)                ║")
        print("╚══════════════════════════════════════════════════════╝" + "\033[0m")
        print("Введите 'help' для списка доступных команд.\n")
        
        asyncio.create_task(self.cli_loop())

    async def cli_loop(self):
        loop = asyncio.get_event_loop()
        while self.running:
            try:
                line = await loop.run_in_executor(None, input, "\033[1;34m🧙 [WIZARD-CORE]> \033[0m")
                await self.session.handle_input(line)
            except EOFError:
                break
            except Exception as e:
                print(f"⚠️ Ошибка консоли: {e}")
                await asyncio.sleep(1)
