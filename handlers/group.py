"""
Group-context features: group menu, per-group leaderboard/stats, plus the
global (bot-wide) leaderboard screens.
"""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, ChatMemberUpdated
from aiogram.filters import ChatMemberUpdatedFilter, JOIN_TRANSITION

from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import db
from utils.keyboards import main_menu_group, back_kb, leaderboard_kb

router = Router(name="group")

LB_TITLES = {
    "level": "⭐ Highest Level",
    "power": "⚔️ Highest Power",
    "coins": "💰 Richest",
    "wins": "🏅 Most Wins",
}

MEDALS = ["🥇", "🥈", "🥉"]


@router.message(Command("shahanshahi"))
@router.message(Command("menu"))
async def group_menu_command(message: Message):
    if message.chat.type not in ("group", "supergroup"):
        return
    await db.ensure_group(message.chat.id, message.chat.title)
    await message.answer("👑 <b>شاهنشاهی</b>", reply_markup=main_menu_group())


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION))
async def on_bot_added_to_group(event: ChatMemberUpdated):
    if event.chat.type in ("group", "supergroup"):
        await db.ensure_group(event.chat.id, event.chat.title)


@router.callback_query(F.data == "menu:group_leaderboard")
async def group_leaderboard(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    rows = await db.group_leaderboard(chat_id)
    if not rows:
        text = "🏆 <b>لیدربورد گپ</b>\n\nهنوز مبارزه‌ای ثبت نشده."
        await callback.message.edit_text(text, reply_markup=back_kb("menu:main"))
        return

    lines = ["🏆 <b>لیدربورد گپ</b>\n"]
    for i, row in enumerate(rows):
        medal = MEDALS[i] if i < 3 else f"{i + 1}."
        lines.append(f"{medal} {row['name']} — {row['wins']} Wins")
    text = "\n".join(lines)

    # Let players challenge the top 3 directly from the leaderboard.
    b = InlineKeyboardBuilder()
    for row in rows[:3]:
        if row["user_id"] != callback.from_user.id:
            b.button(text=f"⚔️ چالش {row['name']}", callback_data=f"challenge:{row['user_id']}")
    b.adjust(1)
    b.row(*back_kb("menu:main").inline_keyboard[0])
    await callback.message.edit_text(text, reply_markup=b.as_markup())


@router.callback_query(F.data == "menu:group_stats")
async def group_stats(callback: CallbackQuery):
    character = await db.get_character(callback.from_user.id)
    if not character:
        await callback.answer("ابتدا باید در پیوی /start بزنید.", show_alert=True)
        return
    stats = await db.group_stats(callback.message.chat.id, callback.from_user.id)
    wins = stats["wins"] or 0
    losses = stats["losses"] or 0
    total = stats["total"] or 0
    win_rate = round((wins / total) * 100, 1) if total else 0.0

    text = (
        f"📊 <b>آمار گروه</b>\n\n"
        f"👤 {character['name']}\n"
        f"🏆 Wins: {wins}\n"
        f"💀 Losses: {losses}\n"
        f"⚔️ Total Fights: {total}\n"
        f"📈 Win Rate: {win_rate}%"
    )
    await callback.message.edit_text(text, reply_markup=back_kb("menu:main"))


# ---------- global (bot-wide) leaderboard ----------

@router.callback_query(F.data == "menu:leaderboard")
async def show_leaderboard_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "🏆 <b>لیدربورد</b>\n\nیک دسته را انتخاب کن:", reply_markup=leaderboard_kb()
    )


@router.callback_query(F.data.startswith("lb:"))
async def show_leaderboard(callback: CallbackQuery):
    key = callback.data.split(":", 1)[1]
    rows = await db.leaderboard(key)
    title = LB_TITLES.get(key, "🏆 Leaderboard")

    if not rows:
        text = f"{title}\n\nهنوز داده‌ای وجود ندارد."
    else:
        lines = [f"{title}\n"]
        for i, row in enumerate(rows):
            medal = MEDALS[i] if i < 3 else f"{i + 1}."
            if key == "coins":
                value = f"{row['coins']} 💰"
            elif key == "power":
                value = f"{row['power']} ⚔️"
            elif key == "wins":
                value = f"{row['wins']} 🏆"
            else:
                value = f"Level {row['level']}"
            lines.append(f"{medal} {row['name']} ({row['territory']}) — {value}")
        text = "\n".join(lines)

    await callback.message.edit_text(text, reply_markup=leaderboard_kb())
