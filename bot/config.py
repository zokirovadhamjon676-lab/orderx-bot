import os
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_PASSWORD = os.getenv("BOT_PASSWORD")  # yangi qator
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))