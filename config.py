"""
Configuration loader for Shahanshahi bot.
All secrets are read from environment variables (.env) — never hardcoded.
"""
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

_admin_ids_raw = os.getenv("ADMIN_IDS", "")
ADMIN_IDS: set[int] = {
    int(x.strip()) for x in _admin_ids_raw.split(",") if x.strip().isdigit()
}

CHANNEL_USERNAME: str = os.getenv("CHANNEL_USERNAME", "@ShahanshahiGameBot")
DATABASE_PATH: str = os.getenv("DATABASE_PATH", "shahanshahi.db")
FIGHT_COOLDOWN: int = int(os.getenv("FIGHT_COOLDOWN", "300"))

BOT_USERNAME: str = "ShahanshahiRPGBot"
CHANNEL_LINK: str = f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}"

if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN is not set. Copy .env.example to .env and fill in your token."
    )

if not ADMIN_IDS:
    raise RuntimeError("ADMIN_IDS is not set in .env")
