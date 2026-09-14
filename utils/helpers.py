"""
Small shared helpers used across handlers.
"""
import time
import re

from aiogram import Bot

from config import CHANNEL_USERNAME, ADMIN_IDS

VALID_NAME_RE = re.compile(r"^[\w\u0600-\u06FF\s]{2,20}$")


async def is_channel_member(bot: Bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        # If the bot can't check (not admin in channel, user never started, etc.)
        # fail closed: treat as not-a-member so onboarding isn't silently skipped.
        return False


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def validate_name(name: str) -> bool:
    name = name.strip()
    return bool(VALID_NAME_RE.match(name))


def format_cooldown(seconds_left: int) -> str:
    minutes, seconds = divmod(max(0, seconds_left), 60)
    if minutes:
        return f"{minutes} دقیقه و {seconds} ثانیه"
    return f"{seconds} ثانیه"


def cooldown_remaining(last_action_ts: int, cooldown_seconds: int) -> int:
    elapsed = int(time.time()) - last_action_ts
    return max(0, cooldown_seconds - elapsed)


def hero_bonus_for(heroes_rows) -> int:
    """Sum of a player's owned Hero Card power bonuses."""
    return sum(h["bonus"] for h in heroes_rows) if heroes_rows else 0
