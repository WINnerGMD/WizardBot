import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
TIMEWEB_API_KEY = os.getenv('TIMEWEB_API_KEY')
COMMAND_PREFIX = '!'
