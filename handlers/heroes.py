"""
Hero events (spawn every 24h via bot.py's scheduler) and player Hero Cards.

Damage is computed server-side from the player's Power stat (plus a
random factor) rather than trusting a user-typed number — letting the
client dictate damage would be an obvious exploit.
"""
import random
import time

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import db
from game.heroes import (
    RARITY_EMOJI, RARITY_BONUS, WINNER_COINS, WINNER_XP,
    CONSOLATION_COINS, CONSOLATION_XP,
)
from game.levels import XP_REWARDS
from utils.helpers import hero_bonus_for
from utils.keyboards import back_kb

router = Router(name="heroes")

ATTACK_COOLDOWN = 60  # seconds between hits on the same hero event
_last_attack: dict[tuple[int, int], float] = {}  # (user_id, event_id) -> ts, in-memory throttle


def hero_event_text(event) -> str:
    emoji = RARITY_EMOJI.get(event["rarity"], "⭐")
    return (
        f"⚔️ <b>قهرمان افسانه‌ای پدیدار شد!</b>\n\n"
        f"🃏 {event['name']}\n"
        f"❤️ HP: {event['hp_current']}/{event['hp_max']}\n"
        f"⚔️ Power: {event['power']}\n"
        f"{emoji} {event['rarity']}"
    )


def hero_event_kb(event_id: int):
    b = InlineKeyboardBuilder()
    b.button(text="⚔️ حمله", callback_data=f"hero_attack:{event_id}")
    b.button(text="🔙 بازگشت", callback_data="menu:main")
    b.adjust(1)
    return b.as_markup()


@router.callback_query(F.data.in_({"menu:heroes", "menu:hero_event"}))
async def show_hero_menu(callback: CallbackQuery):
    character = await db.get_character(callback.from_user.id)
    if not character:
        await callback.answer("ابتدا باید /start بزنید.", show_alert=True)
        return

    event = await db.get_active_hero_event()
    if event:
        await callback.message.edit_text(hero_event_text(event), reply_markup=hero_event_kb(event["id"]))
        return

    heroes = await db.get_heroes(callback.from_user.id)
    if not heroes:
        text = "🃏 هیچ قهرمانی در حال حاضر ظاهر نشده و کارت قهرمانی هم نداری."
    else:
        lines = ["🃏 <b>قهرمانان تو</b>\n"]
        for h in heroes:
            emoji = RARITY_EMOJI.get(h["rarity"], "⭐")
            lines.append(f"{emoji} {h['name']} — {h['rarity']} (Power +{h['bonus']})")
        text = "\n".join(lines)
    await callback.message.edit_text(text, reply_markup=back_kb())


@router.callback_query(F.data.startswith("hero_attack:"))
async def attack_hero(callback: CallbackQuery):
    event_id = int(callback.data.split(":", 1)[1])
    event = await db.get_active_hero_event()

    if not event or event["id"] != event_id or event["status"] != "active":
        await callback.answer("این قهرمان دیگر فعال نیست.", show_alert=True)
        return

    key = (callback.from_user.id, event_id)
    now = time.time()
    if key in _last_attack and now - _last_attack[key] < ATTACK_COOLDOWN:
        left = int(ATTACK_COOLDOWN - (now - _last_attack[key]))
        await callback.answer(f"⏳ {left} ثانیه دیگر صبر کن.", show_alert=True)
        return

    character = await db.get_character(callback.from_user.id)
    if not character:
        await callback.answer("ابتدا باید /start بزنید.", show_alert=True)
        return

    heroes = await db.get_heroes(callback.from_user.id)
    base_damage = character["power"] + hero_bonus_for(heroes) * 2
    damage = int(base_damage * random.uniform(0.8, 1.3))

    await db.apply_hero_damage(event_id, callback.from_user.id, damage)
    _last_attack[key] = now

    event = await db.get_active_hero_event()
    await callback.answer(f"💥 {damage} آسیب وارد کردی!")

    if event["hp_current"] <= 0:
        await finish_hero_event(callback, event_id)
        return

    await callback.message.edit_text(hero_event_text(event), reply_markup=hero_event_kb(event_id))


async def finish_hero_event(callback: CallbackQuery, event_id: int):
    event_row = await db.get_active_hero_event()
    ranking = await db.hero_event_damage_ranking(event_id)
    await db.finish_hero_event(event_id)

    if not ranking:
        await callback.message.edit_text("قهرمان بدون هیچ آسیبی ناپدید شد.", reply_markup=back_kb())
        return

    winner_id = ranking[0]["user_id"]

    await db.add_hero(
        winner_id,
        name=event_row["name"] if event_row else "قهرمان",
        rarity=event_row["rarity"] if event_row else "Common",
        power=event_row["power"] if event_row else 0,
        defense=0,
        bonus=RARITY_BONUS.get(event_row["rarity"] if event_row else "Common", 10),
    )
    await db.add_coins(winner_id, WINNER_COINS, "hero_event_winner")
    await db.add_xp(winner_id, WINNER_XP)

    for row in ranking[1:]:
        await db.add_coins(row["user_id"], CONSOLATION_COINS, "hero_event_participation")
        await db.add_xp(row["user_id"], CONSOLATION_XP)

    winner_char = await db.get_character(winner_id)
    winner_name = winner_char["name"] if winner_char else str(winner_id)

    await callback.message.edit_text(
        f"🎉 قهرمان شکست خورد!\n\n"
        f"🃏 برنده: <b>{winner_name}</b>\n"
        f"💰 +{WINNER_COINS} Coins و ✨ +{WINNER_XP} XP\n\n"
        f"سایر شرکت‌کنندگان پاداش کوچک‌تری دریافت کردند.",
        reply_markup=back_kb(),
    )
