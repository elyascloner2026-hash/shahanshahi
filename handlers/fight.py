"""
Attack system.
Players can only attack by replying to another player's message
in a group and sending: حمله
"""
import time

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from config import FIGHT_COOLDOWN
from database import db
from game.battles import resolve_fight, is_protected
from game.army import army_strength
from game.levels import XP_REWARDS
from handlers.profile import sync_level
from utils.helpers import cooldown_remaining, format_cooldown, hero_bonus_for
from utils.keyboards import back_kb


router = Router(name="fight")


async def do_fight(
    message_or_callback,
    attacker_id: int,
    defender_id: int,
    chat_id: int | None,
    answer_func,
):
    if attacker_id == defender_id:
        await answer_func("❌ نمی‌توانی به خودت حمله کنی.")
        return

    if await db.is_banned(attacker_id):
        await answer_func("🚫 شما از شاهنشاهی اخراج شده‌اید و نمی‌توانید حمله کنید.")
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
        await answer_func("❌ این بازیکن بن شده و قابل حمله نیست.")
        return

    remaining = cooldown_remaining(attacker["last_fight_at"], FIGHT_COOLDOWN)
    if remaining > 0:
        await answer_func(f"⏳ باید {format_cooldown(remaining)} دیگر صبر کنی.")
        return

    attacker_heroes = await db.get_heroes(attacker_id)
    defender_heroes = await db.get_heroes(defender_id)

    attacker_army = await db.get_army(attacker_id)
    defender_army = await db.get_army(defender_id)

    a_army = army_strength(attacker_army)
    d_army = army_strength(defender_army)

    if a_army["total"] <= 0:
        await answer_func("🪖 ارتشت خالی است! از بخش «ارتش» سرباز بخر.")
        return

    if d_army["total"] <= 0:
        await answer_func("❌ حریف ارتش ندارد و فعلاً قابل حمله نیست.")
        return

    attacker_premium = await db.has_premium(attacker_id, "battle_mastery")
    defender_premium = await db.has_premium(defender_id, "battle_mastery")

    outcome = resolve_fight(
        attacker_stats={
            "power": attacker["power"],
            "defense": attacker["defense"],
            "level": attacker["level"],
            "rank": attacker["rank"],
            "hero_bonus": hero_bonus_for(attacker_heroes),
            "army_power": a_army["power"],
            "army_defense": a_army["defense"],
        },
        defender_stats={
            "power": defender["power"],
            "defense": defender["defense"],
            "level": defender["level"],
            "rank": defender["rank"],
            "hero_bonus": hero_bonus_for(defender_heroes),
            "army_power": d_army["power"],
            "army_defense": d_army["defense"],
        },
    )

    if attacker_premium:
        outcome["attacker_score"] = round(
            outcome["attacker_score"] * 1.15, 1
        )

    if defender_premium:
        outcome["defender_score"] = round(
            outcome["defender_score"] * 1.15, 1
        )

    outcome["attacker_wins"] = (
        outcome["attacker_score"] >= outcome["defender_score"]
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
        wins=(
            attacker["wins"] + 1
            if winner_id == attacker_id
            else defender["wins"] + 1
        ),
    )

    await db.update_character(
        loser_id,
        losses=(
            attacker["losses"] + 1
            if loser_id == attacker_id
            else defender["losses"] + 1
        ),
    )

    await db.set_last_fight(attacker_id, int(time.time()))

    await db.lose_army(
        attacker_id,
        0.10 if winner_id == attacker_id else 0.18,
    )

    await db.lose_army(
        defender_id,
        0.18 if winner_id == attacker_id else 0.10,
    )

    await db.record_battle(
        attacker_id,
        defender_id,
        winner_id,
        coins_reward,
        XP_REWARDS["fight_win"],
        chat_id,
    )

    for uid in (attacker_id, defender_id):
        c = await db.get_character(uid)
        await sync_level(c)

    winner_name = (
        attacker["name"]
        if winner_id == attacker_id
        else defender["name"]
    )

    loser_name = (
        attacker["name"]
        if loser_id == attacker_id
        else defender["name"]
    )

    text = (
        f"⚔️ <b>{attacker['name']}</b> در برابر "
        f"<b>{defender['name']}</b>\n\n"
        f"🏆 برنده: {winner_name}\n"
        f"💀 بازنده: {loser_name}\n\n"
        f"💰 +{coins_reward} سکه برای برنده\n"
        f"✨ +{XP_REWARDS['fight_win']} XP برای برنده\n\n"
        f"🪖 ارتش: {a_army['total']} نفر در برابر "
        f"{d_army['total']} نفر\n"
        f"⚔️ قدرت نبرد: {outcome['attacker_score']} در برابر "
        f"{outcome['defender_score']}"
    )

    await answer_func(text)


# ============================================================
# دستور «حمله» — فقط با Reply
# ============================================================

@router.message(F.text.regexp(r"^حمله$"))
async def cmd_attack(message: Message):

    if message.chat.type not in ("group", "supergroup"):
        await message.answer(
            "⚔️ حمله فقط داخل گروه انجام می‌شود."
        )
        return

    if not message.reply_to_message:
        await message.answer(
            "⚔️ برای حمله، روی پیام بازیکن موردنظر Reply کن "
            "و فقط بنویس: حمله"
        )
        return

    if not message.reply_to_message.from_user:
        await message.answer("❌ بازیکن موردنظر پیدا نشد.")
        return

    attacker_id = message.from_user.id
    defender_id = message.reply_to_message.from_user.id
    chat_id = message.chat.id

    await db.ensure_group(chat_id, message.chat.title)

    await do_fight(
        message,
        attacker_id,
        defender_id,
        chat_id,
        message.answer,
    )


@router.callback_query(F.data == "menu:fight")
async def menu_fight(callback: CallbackQuery):
    await callback.message.edit_text(
        "⚔️ <b>حمله</b>\n\n"
        "برای حمله داخل گروه:\n\n"
        "1️⃣ روی پیام بازیکن موردنظر Reply کن\n"
        "2️⃣ فقط بنویس: <code>حمله</code>\n\n"
        "❌ حمله با یوزرنیم امکان‌پذیر نیست.\n"
        "❌ دستور /fight هم لازم نیست.",
        reply_markup=back_kb(),
    )

    await callback.answer()
