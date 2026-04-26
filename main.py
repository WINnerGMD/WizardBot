import os
from dotenv import load_dotenv
import logging
from src.bot.bot import WizardBot

# Logger setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    load_dotenv()
    
    token = os.getenv("DISCORD_TOKEN")
    admin_id = int(os.getenv("ADMIN_ID", "0"))
    
    if not token:
        print("❌ Error: DISCORD_TOKEN not found in .env")
        return

    # Initialize and run the bot
    bot = WizardBot(admin_id=admin_id)
    
    try:
        bot.run(token)
    except Exception as e:
        print(f"❌ Bot failed to start: {e}")

if __name__ == "__main__":
    main()
