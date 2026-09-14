"""
Fight system. Works in both private chat (/fight @username) and groups
(/fight as a reply to a player's message, or /fight @username), plus the
⚔️ Challenge inline button which encodes the target's user id.
"""
import time

from aiogram import Router, F, Bot
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, CallbackQuery

from config import FIGHT_COOLDOWN
from database import db
from game.battles import resolve_fight, is_protected
from game.levels import XP_REWARDS
from handlers.profile import sync_level
from utils.helpers import cooldown_remaining, format_cooldown, hero_bonus_for
from utils.keyboards import challenge_kb, back_kb

router = Router(name="fight")


async def resolve_target_id(message: Message, command: CommandObject, bot: Bot) -> int | None:
    """Figure out who the defender is: reply > @username arg."""
    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user.id

    if command.args:
        arg = command.args.strip().lstrip("@")
        if arg.isdigit():
            return int(arg)
        try:
            chat = await bot.get_chat(f"@{arg}")
            return chat.id
        except Exception:
            return None

    return None


async def do_fight(message_or_callback, attacker_id: int, defender_id: int, chat_id: int | None, answer_func):
    if attacker_id == defender_id:
        await answer_func("❌ نمی‌توانی با خودت مبارزه کنی.")
        return

    if await db.is_banned(attacker_id):
        await answer_func("🚫 شما از شاهنشاهی اخراج شده‌اید و نمی‌توانید مبارزه کنید.")
        return

    attacker = await db.get_character(attacker_id)
    defender = await db.get_character(defender_id)

    if not attacker:
        await answer_func("ابتدا باید با /start شخصیت بسازی.")
        return
    if not defender:
        await answer_func("❌ حریف هنوز در شاهنشاهی شخصیتی نساخته است.")
        return
    if await db.is_banned(defender_id):
        await answer_func("❌ این بازیکن بن شده و قابل مبارزه نیست.")
        return

    remaining = cooldown_remaining(attacker["last_fight_at"], FIGHT_COOLDOWN)
    if remaining > 0:
        await answer_func(f"⏳ باید {format_cooldown(remaining)} دیگر صبر کنی.")
        return

    attacker_heroes = await db.get_heroes(attacker_id)
    defender_heroes = await db.get_heroes(defender_id)

    outcome = resolve_fight(
        attacker_stats={
            "power": attacker["power"], "defense": attacker["defense"],
            "level": attacker["level"], "rank": attacker["rank"],
            "hero_bonus": hero_bonus_for(attacker_heroes),
        },
        defender_stats={
            "power": defender["power"], "defense": defender["defense"],
            "level": defender["level"], "rank": defender["rank"],
            "hero_bonus": hero_bonus_for(defender_heroes),
        },
    )

    winner_id = attacker_id if outcome["attacker_wins"] else defender_id
    loser_id = defender_id if outcome["attacker_wins"] else attacker_id
    loser = defender if outcome["attacker_wins"] else attacker

    coins_reward = outcome["coins_reward"]
    loser_penalty = coins_reward // 2
    if is_protected(loser["level"]):
        loser_penalty = loser_penalty // 2

    await db.add_coins(winner_id, coins_reward, "fight_win")
    await db.add_coins(loser_id, -loser_penalty, "fight_loss")
    await db.add_xp(winner_id, XP_REWARDS["fight_win"])
    await db.add_xp(loser_id, XP_REWARDS["fight_loss"])

    await db.update_character(
        winner_id,
        wins=(attacker["wins"] + 1) if winner_id == attacker_id else (defender["wins"] + 1),
    )
    await db.update_character(
        loser_id,
        losses=(attacker["losses"] + 1) if loser_id == attacker_id else (defender["losses"] + 1),
    )
    await db.set_last_fight(attacker_id, int(time.time()))

    battle_id = await db.record_battle(
        attacker_id, defender_id, winner_id, coins_reward, XP_REWARDS["fight_win"], chat_id
    )

    for uid in (attacker_id, defender_id):
        c = await db.get_character(uid)
        await sync_level(c)

    winner_name = attacker["name"] if winner_id == attacker_id else defender["name"]
    loser_name = attacker["name"] if loser_id == attacker_id else defender["name"]

    text = (
        f"⚔️ <b>{attacker['name']}</b> در برابر <b>{defender['name']}</b>\n\n"
        f"🏆 Winner: {winner_name}\n"
        f"💀 Loser: {loser_name}\n\n"
        f"💰 +{coins_reward} Coins برای برنده\n"
        f"✨ +{XP_REWARDS['fight_win']} XP برای برنده"
    )
    await answer_func(text)


@router.message(Command("fight"))
async def cmd_fight(message: Message, command: CommandObject, bot: Bot):
    defender_id = await resolve_target_id(message, command, bot)
    if defender_id is None:
        await message.answer(
            "برای مبارزه:\nروی پیام حریف Reply بزن و /fight را بفرست،\n"
            "یا بنویس: /fight @username"
        )
        return

    chat_id = message.chat.id if message.chat.type in ("group", "supergroup") else None
    if chat_id:
        await db.ensure_group(chat_id, message.chat.title)

    await do_fight(message, message.from_user.id, defender_id, chat_id, message.answer)


@router.callback_query(F.data.startswith("challenge:"))
async def cb_challenge(callback: CallbackQuery):
    defender_id = int(callback.data.split(":", 1)[1])
    chat_id = callback.message.chat.id if callback.message.chat.type in ("group", "supergroup") else None

    async def answer_func(text):
        await callback.message.answer(text)

    await callback.answer()
    await do_fight(callback, callback.from_user.id, defender_id, chat_id, answer_func)


@router.callback_query(F.data == "menu:fight")
async def menu_fight(callback: CallbackQuery):
    await callback.message.edit_text(
        "⚔️ <b>فایت</b>\n\n"
        "برای مبارزه در گروه، روی پیام حریف Reply بزن و بنویس /fight\n"
        "یا در هر جا بنویس: /fight @username",
        reply_markup=back_kb(),
    )
