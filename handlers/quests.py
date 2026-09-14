"""
Quests: simple daily and story quests with branching rewards.
"""
import json

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import db
from game.quests import DAILY_QUESTS, STORY_QUESTS
from utils.keyboards import back_kb, quest_choice_kb

router = Router(name="quests")


def quest_list_kb():
    b = InlineKeyboardBuilder()
    for q in DAILY_QUESTS:
        b.button(text=q["title"], callback_data=f"quest_open:{q['code']}")
    for q in STORY_QUESTS:
        b.button(text=q["title"], callback_data=f"quest_open:{q['code']}")
    b.adjust(1)
    b.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu:main"))
    return b.as_markup()


@router.callback_query(F.data == "menu:quests")
async def show_quests(callback: CallbackQuery):
    character = await db.get_character(callback.from_user.id)
    if not character:
        await callback.answer("ابتدا باید /start بزنید.", show_alert=True)
        return
    await callback.message.edit_text(
        "📜 <b>مأموریت‌ها</b>\n\nیکی را انتخاب کن:", reply_markup=quest_list_kb()
    )


@router.callback_query(F.data.startswith("quest_open:"))
async def open_quest(callback: CallbackQuery):
    code = callback.data.split(":", 1)[1]
    quest = await db.get_quest(code)
    if not quest:
        await callback.answer("این مأموریت در دسترس نیست.", show_alert=True)
        return

    if quest["quest_type"] == "daily" and await db.has_completed_quest_today(callback.from_user.id, quest["id"]):
        await callback.answer("✅ این مأموریت روزانه را امروز قبلاً انجام دادی.", show_alert=True)
        return
    if quest["quest_type"] == "story":
        # story quests can only be completed once, ever
        completed = await db.has_completed_quest_ever(callback.from_user.id, quest["id"])
        if completed:
            await callback.answer("✅ این داستان قبلاً به پایان رسیده.", show_alert=True)
            return

    choices = json.loads(quest["choices_json"])
    choice_labels = list(choices.keys())
    await callback.message.edit_text(
        f"{quest['title']}\n\n{quest['description']}",
        reply_markup=quest_choice_kb(code, choice_labels),
    )


@router.callback_query(F.data.startswith("quest:"))
async def resolve_quest(callback: CallbackQuery):
    _, code, index_str = callback.data.split(":", 2)
    quest = await db.get_quest(code)
    if not quest:
        await callback.answer("این مأموریت در دسترس نیست.", show_alert=True)
        return

    choices = json.loads(quest["choices_json"])
    labels = list(choices.keys())
    try:
        label = labels[int(index_str)]
    except (IndexError, ValueError):
        await callback.answer("انتخاب نامعتبر است.", show_alert=True)
        return

    reward = choices[label]
    await db.add_coins(callback.from_user.id, reward["coins"], f"quest:{code}")
    await db.add_xp(callback.from_user.id, reward["xp"])
    await db.complete_quest(callback.from_user.id, quest["id"], label)

    await callback.message.edit_text(
        f"{quest['title']}\n\n"
        f"انتخاب کردی: {label}\n\n"
        f"💰 +{reward['coins']} Coins\n"
        f"✨ +{reward['xp']} XP",
        reply_markup=back_kb("menu:quests"),
    )
