"""Hero events and player Hero Cards."""
import random
import time
from pathlib import Path

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import db
from game.heroes import (
    RARITY_EMOJI, RARITY_BONUS, WINNER_COINS, WINNER_XP,
    CONSOLATION_COINS, CONSOLATION_XP,
)
from utils.helpers import hero_bonus_for
from utils.keyboards import back_kb

router = Router(name="heroes")

ATTACK_COOLDOWN = 60
_last_attack: dict[tuple[int, int], float] = {}
ASSET_DIR = Path(__file__).resolve().parent.parent / "assets" / "heroes"


def hero_image(name: str) -> Path:
    path = ASSET_DIR / f"{name}.png"
    fallback = ASSET_DIR / "default.png"
    return path if path.exists() else fallback


def hero_event_text(event) -> str:
    emoji = RARITY_EMOJI.get(event["rarity"], "⭐")
    return (
        f"⚔️ <b>قهرمان افسانه‌ای پدیدار شد!</b>\n\n"
        f"🃏 <b>{event['name']}</b>\n"
        f"❤️ HP: {event['hp_current']}/{event['hp_max']}\n"
        f"⚔️ Power: {event['power']}\n"
        f"{emoji} {event['rarity']}\n\n"
        f"🔥 اولین کسی که شکستش بده، قهرمان را به دست می‌آورد!"
    )


def hero_event_kb(event_id: int):
    b = InlineKeyboardBuilder()
    b.button(text="⚔️ حمله", callback_data=f"hero_attack:{event_id}")
    b.button(text="🔙 بازگشت", callback_data="menu:main")
    b.adjust(1)
    return b.as_markup()


async def send_hero_photo(target, event, reply_markup=None):
    photo = FSInputFile(str(hero_image(event["name"])))
    return await target.answer_photo(
        photo=photo,
        caption=hero_event_text(event),
        reply_markup=reply_markup,
    )


@router.callback_query(F.data.in_({"menu:heroes", "menu:hero_event"}))
async def show_hero_menu(callback: CallbackQuery):
    character = await db.get_character(callback.from_user.id)
    if not character:
        await callback.answer("ابتدا باید /start بزنید.", show_alert=True)
        return

    event = await db.get_active_hero_event()
    if event:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await send_hero_photo(callback.message, event, hero_event_kb(event["id"]))
        await callback.answer()
        return

    heroes = await db.get_heroes(callback.from_user.id)
    if not heroes:
        await callback.message.edit_text(
            "🃏 هیچ قهرمانی در حال حاضر ظاهر نشده و کارت قهرمانی هم نداری.",
            reply_markup=back_kb(),
        )
        return

    await callback.message.edit_text("🃏 <b>قهرمانان تو</b>")
    for h in heroes:
        emoji = RARITY_EMOJI.get(h["rarity"], "⭐")
        caption = (
            f"🃏 <b>{h['name']}</b>\n"
            f"{emoji} {h['rarity']}\n"
            f"⚔️ Power: {h['power']}\n"
            f"🛡 Defense: {h['defense']}\n"
            f"✨ Bonus: +{h['bonus']}"
        )
        await callback.message.answer_photo(
            photo=FSInputFile(str(hero_image(h["name"]))),
            caption=caption,
        )
    await callback.message.answer("🔙", reply_markup=back_kb())


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

    # The world-boss hero retaliates against the attacker's army.
    # Stronger heroes deal a larger percentage of casualties.
    retaliation_ratio = min(0.20, 0.01 + event["power"] / 20000)
    if await db.has_premium(callback.from_user.id, "hero_shield"):
        retaliation_ratio *= 0.50
    army_before = await db.get_army(callback.from_user.id)
    if army_before:
        await db.lose_army(callback.from_user.id, retaliation_ratio)
    _last_attack[key] = now

    event = await db.get_active_hero_event()
    loss_pct = retaliation_ratio * 100
    await callback.answer(f"💥 {damage} آسیب زدی! 🩸 قهرمان به ارتشت {loss_pct:.1f}٪ ضربه زد.")

    if event["hp_current"] <= 0:
        await finish_hero_event(callback, event_id)
        return

    await callback.message.edit_caption(
        caption=hero_event_text(event),
        reply_markup=hero_event_kb(event_id),
    )


async def finish_hero_event(callback: CallbackQuery, event_id: int):
    event_row = await db.get_active_hero_event()
    ranking = await db.hero_event_damage_ranking(event_id)
    await db.finish_hero_event(event_id)

    if not ranking:
        await callback.message.edit_caption("قهرمان بدون هیچ آسیبی ناپدید شد.")
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
    result = (
        f"🎉 <b>قهرمان شکست خورد!</b>\n\n"
        f"🃏 برنده: <b>{winner_name}</b>\n"
        f"💰 +{WINNER_COINS} Coins و ✨ +{WINNER_XP} XP\n\n"
        f"سایر شرکت‌کنندگان پاداش کوچک‌تری دریافت کردند."
    )
    await callback.message.edit_caption(result, reply_markup=back_kb())


async def announce_hero_to_groups(bot: Bot, event):
    """Announce the active hero only in groups where the bot has been registered."""
    groups = await db.list_groups()
    for group in groups:
        try:
            await bot.send_photo(
                chat_id=group["chat_id"],
                photo=FSInputFile(str(hero_image(event["name"]))),
                caption=hero_event_text(event),
                reply_markup=hero_event_kb(event["id"]),
            )
        except Exception:
            # A group may have removed the bot or blocked its messages.
            # Keep the group record so a later interaction can re-register it.
            continue
