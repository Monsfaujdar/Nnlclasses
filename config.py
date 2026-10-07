# Configuration for the Telegram bot
# Keep all secrets in Render environment variables. Do not commit them here.

import os


def env_bool(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


# Login feature
LOGIN_SYSTEM = env_bool("LOGIN_SYSTEM", True)
STRING_SESSION = os.getenv("STRING_SESSION") if not LOGIN_SYSTEM else None

# Telegram credentials - required in Render
BOT_TOKEN = os.environ["BOT_TOKEN"]
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]

# Bot owner/admin
ADMINS = int(os.environ["ADMINS"])

# Channel where the bot uploads content
CHANNEL_ID = os.getenv("CHANNEL_ID", "")

# MongoDB
DB_URI = os.environ["DB_URI"]
DB_NAME = os.getenv("DB_NAME", "downbot")

# Runtime settings
WAITING_TIME = int(os.getenv("WAITING_TIME", "20"))
ERROR_MESSAGE = env_bool("ERROR_MESSAGE", True)
