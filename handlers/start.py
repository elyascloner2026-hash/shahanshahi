"""
/start handler: channel-membership gate, then character creation.
"""
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from database import db
from utils.helpers import is_channel_member, validate_name
from utils.keyboards import (
    join_channel_kb, gender_kb, territory_kb, city_kb, main_menu_private, main_menu_group,
)

router = Router(name="start")


class CharacterCreation(StatesGroup):
    waiting_name = State()
    waiting_gender = State()
    waiting_territory = State()
    waiting_city = State()


WELCOME_GATE = (
    "🏛 <b>به شاهنشاهی خوش آمدید</b>\n\n"
    "برای ورود به قلمرو شاهنشاهی\n"
    "ابتدا باید در کانال رسمی بازی عضو شوید."
)

WELCOME_NEW_CHARACTER = (
    "👑 <b>شاهنشاهی</b>\n\n"
    "دروازه‌های قلمرو برایت گشوده شد.\n"
    "برای آغاز، نام شخصیتت را بنویس:"
)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, bot: Bot):
    is_group = message.chat.type in ("group", "supergroup")

    if is_group:
        await db.ensure_group(message.chat.id, message.chat.title)

    await db.ensure_user(message.from_user.id, message.from_user.username)

    if await db.is_banned(message.from_user.id):
        await message.answer("🚫 شما از شاهنشاهی اخراج شده‌اید.")
        return

    if not await is_channel_member(bot, message.from_user.id):
        await message.answer(WELCOME_GATE, reply_markup=join_channel_kb())
        return

    await enter_game(message, state)


@router.callback_query(F.data == "check_membership")
async def check_membership(callback: CallbackQuery, state: FSMContext, bot: Bot):
    if await is_channel_member(bot, callback.from_user.id):
        await callback.message.delete()
        await enter_game(callback.message, state, user_id=callback.from_user.id, username=callback.from_user.username)
    else:
        await callback.answer("❌ هنوز عضو کانال نشده‌اید.", show_alert=True)


async def enter_game(message: Message, state: FSMContext, user_id: int | None = None, username: str | None = None):
    user_id = user_id or message.from_user.id
    character = await db.get_character(user_id)
    if character:
        await state.clear()
        await message.answer(
            f"👑 خوش آمدی، {character['name']}!",
            reply_markup=main_menu_group() if message.chat.type in ("group", "supergroup") else main_menu_private(),
        )
        return

    await state.set_state(CharacterCreation.waiting_name)
    await message.answer(WELCOME_NEW_CHARACTER)


@router.message(StateFilter(CharacterCreation.waiting_name))
async def receive_name(message: Message, state: FSMContext):
    name = (message.text or "").strip()
    if not validate_name(name):
        await message.answer("❌ نام نامعتبر است. نامی بین ۲ تا ۲۰ کاراکتر وارد کن.")
        return
    await state.update_data(name=name)
    await state.set_state(CharacterCreation.waiting_gender)
    await message.answer("جنسیت شخصیتت را انتخاب کن:", reply_markup=gender_kb())


@router.callback_query(StateFilter(CharacterCreation.waiting_gender), F.data.startswith("gender:"))
async def receive_gender(callback: CallbackQuery, state: FSMContext):
    gender = callback.data.split(":", 1)[1]
    await state.update_data(gender=gender)
    territories = await db.list_territories()
    await state.set_state(CharacterCreation.waiting_territory)
    await callback.message.edit_text(
        "قلمرو خود را برگزین:", reply_markup=territory_kb(territories)
    )


@router.callback_query(StateFilter(CharacterCreation.waiting_territory), F.data.startswith("territory:"))
async def receive_territory(callback: CallbackQuery, state: FSMContext):
    territory = callback.data.split(":", 1)[1]
    await state.update_data(territory=territory)
    cities = await db.list_cities(territory)
    await state.set_state(CharacterCreation.waiting_city)
    await callback.message.edit_text(
        f"شهر خود در {territory} را برگزین:", reply_markup=city_kb(cities, territory)
    )


@router.callback_query(StateFilter(CharacterCreation.waiting_city), F.data.startswith("city:"))
async def receive_city(callback: CallbackQuery, state: FSMContext):
    city = callback.data.split(":", 1)[1]
    data = await state.get_data()
    await db.create_character(
        user_id=callback.from_user.id,
        name=data["name"],
        gender=data["gender"],
        territory=data["territory"],
        city=city,
    )
    await state.clear()
    await callback.message.edit_text(
        f"🎉 شخصیت {data['name']} از {data['territory']} ساخته شد!\n\n"
        "به شاهنشاهی خوش آمدی."
    )
    await callback.message.answer(
        "منوی اصلی:",
        reply_markup=main_menu_group() if callback.message.chat.type in ("group", "supergroup") else main_menu_private(),
    )
