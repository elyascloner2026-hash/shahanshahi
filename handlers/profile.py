"""
Profile screen + general main-menu navigation (main, territory, settings, news).
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message

from database import db
from game.levels import level_from_xp
from game.ranks import rank_for_level
from utils.helpers import hero_bonus_for
from utils.keyboards import main_menu_private, back_kb

router = Router(name="profile")


def format_profile(character, heroes_count: int) -> str:
    level, xp_in_level, xp_needed = level_from_xp(character["xp"])
    rank = rank_for_level(level)
    return (
        f"👤 {character['name']}\n"
        f"🏛 {character['territory']}\n"
        f"🏙 {character['city']}\n\n"
        f"🎖 {rank}\n"
        f"⭐ Level {level}\n"
        f"✨ XP: {xp_in_level}/{xp_needed}\n\n"
        f"💰 Coins: {character['coins']}\n"
        f"⚔️ Power: {character['power']}\n"
        f"🛡 Defense: {character['defense']}\n\n"
        f"🏆 Wins: {character['wins']}\n"
        f"💀 Losses: {character['losses']}\n"
        f"🃏 Heroes: {heroes_count}"
    )


async def sync_level(character):
    """Recompute level/rank from cumulative XP and persist if changed."""
    level, _, _ = level_from_xp(character["xp"])
    rank = rank_for_level(level)
    if level != character["level"] or rank != character["rank"]:
        await db.update_character(character["user_id"], level=level, rank=rank)
    return level, rank


@router.callback_query(F.data == "menu:profile")
async def show_profile(callback: CallbackQuery):
    character = await db.get_character(callback.from_user.id)
    if not character:
        await callback.answer("ابتدا باید /start بزنید.", show_alert=True)
        return
    await sync_level(character)
    character = await db.get_character(callback.from_user.id)
    heroes_count = await db.count_heroes(callback.from_user.id)
    await callback.message.edit_text(
        format_profile(character, heroes_count), reply_markup=back_kb()
    )


@router.message(F.text == "/profile")
async def profile_command(message: Message):
    character = await db.get_character(message.from_user.id)
    if not character:
        await message.answer("ابتدا باید /start بزنید.")
        return
    await sync_level(character)
    character = await db.get_character(message.from_user.id)
    heroes_count = await db.count_heroes(message.from_user.id)
    await message.answer(format_profile(character, heroes_count))


@router.callback_query(F.data == "menu:main")
async def back_to_main(callback: CallbackQuery):
    await callback.message.edit_text("منوی اصلی:", reply_markup=main_menu_private())


@router.callback_query(F.data == "menu:territory")
async def show_territory(callback: CallbackQuery):
    character = await db.get_character(callback.from_user.id)
    if not character:
        await callback.answer("ابتدا باید /start بزنید.", show_alert=True)
        return
    territories = await db.list_territories()
    territory_row = next((t for t in territories if t["name"] == character["territory"]), None)
    emoji = territory_row["emoji"] if territory_row else "🏛"
    await callback.message.edit_text(
        f"{emoji} <b>{character['territory']}</b>\n\n"
        f"🏙 شهر: {character['city']}\n"
        f"👤 حاکم: {character['name']}",
        reply_markup=back_kb(),
    )


@router.callback_query(F.data == "menu:settings")
async def show_settings(callback: CallbackQuery):
    await callback.message.edit_text(
        "⚙️ تنظیمات\n\nدر نسخه فعلی تنظیمات خاصی وجود ندارد.",
        reply_markup=back_kb(),
    )


@router.callback_query(F.data == "menu:news")
async def show_news(callback: CallbackQuery):
    news_rows = await db.latest_news(5)
    if not news_rows:
        text = "📰 اخبار شاهنشاهی\n\nهنوز خبری منتشر نشده است."
    else:
        parts = ["📰 <b>اخبار شاهنشاهی</b>\n"]
        for n in news_rows:
            parts.append(f"\n<b>{n['title']}</b>\n{n['content']}")
        text = "\n".join(parts)
    await callback.message.edit_text(text, reply_markup=back_kb())
