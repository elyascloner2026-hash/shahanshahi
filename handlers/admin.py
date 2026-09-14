"""
Admin panel. Only user IDs in config.ADMIN_IDS (from .env) may use this.
Every mutating action is written to admin_logs.
"""
from aiogram import Router, F, Bot
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import db
from utils.helpers import is_admin
from utils.keyboards import admin_panel_kb, back_kb

router = Router(name="admin")


class AdminStates(StatesGroup):
    waiting_broadcast = State()
    waiting_finduser = State()
    waiting_ban = State()
    waiting_unban = State()


def _admin_guard(user_id: int) -> bool:
    return is_admin(user_id)


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not _admin_guard(message.from_user.id):
        return
    await message.answer("👑 <b>پنل ادمین</b>", reply_markup=admin_panel_kb())


@router.callback_query(F.data == "admin:stats")
async def admin_stats(callback: CallbackQuery):
    if not _admin_guard(callback.from_user.id):
        await callback.answer("⛔️ دسترسی ندارید.", show_alert=True)
        return
    stats = await db.stats_summary()
    text = (
        "📊 <b>Statistics</b>\n\n"
        f"👥 Users: {stats['users']}\n"
        f"👤 Characters: {stats['characters']}\n"
        f"⚔️ Battles: {stats['battles']}\n"
        f"🃏 Heroes minted: {stats['heroes']}"
    )
    await callback.message.edit_text(text, reply_markup=back_kb("admin:panel"))


@router.callback_query(F.data == "admin:panel")
async def admin_panel_back(callback: CallbackQuery):
    if not _admin_guard(callback.from_user.id):
        await callback.answer("⛔️ دسترسی ندارید.", show_alert=True)
        return
    await callback.message.edit_text("👑 <b>پنل ادمین</b>", reply_markup=admin_panel_kb())


@router.callback_query(F.data == "admin:broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext):
    if not _admin_guard(callback.from_user.id):
        await callback.answer("⛔️ دسترسی ندارید.", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_broadcast)
    await callback.message.edit_text("📢 متن پیام Broadcast را بفرست:")


@router.message(AdminStates.waiting_broadcast)
async def admin_broadcast_send(message: Message, state: FSMContext, bot: Bot):
    if not _admin_guard(message.from_user.id):
        return
    await state.clear()
    user_ids = await db.all_user_ids()
    sent, failed = 0, 0
    for uid in user_ids:
        try:
            await bot.send_message(uid, f"📢 <b>اطلاعیه شاهنشاهی</b>\n\n{message.text}")
            sent += 1
        except Exception:
            failed += 1
    await db.log_admin_action(message.from_user.id, "broadcast", details=message.text[:200])
    await message.answer(f"✅ ارسال شد به {sent} کاربر. ({failed} ناموفق)")


@router.callback_query(F.data == "admin:finduser")
async def admin_finduser_start(callback: CallbackQuery, state: FSMContext):
    if not _admin_guard(callback.from_user.id):
        await callback.answer("⛔️ دسترسی ندارید.", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_finduser)
    await callback.message.edit_text("👥 Telegram User ID بازیکن را بفرست:")


@router.message(AdminStates.waiting_finduser)
async def admin_finduser_result(message: Message, state: FSMContext):
    if not _admin_guard(message.from_user.id):
        return
    await state.clear()
    if not message.text or not message.text.strip().isdigit():
        await message.answer("❌ باید یک عدد (User ID) بفرستی.")
        return
    target_id = int(message.text.strip())
    character = await db.get_character(target_id)
    banned = await db.is_banned(target_id)
    if not character:
        await message.answer("❌ این کاربر شخصیتی نساخته است.")
        return

    text = (
        f"👤 {character['name']} (ID: {target_id})\n"
        f"🏛 {character['territory']} — 🏙 {character['city']}\n"
        f"🎖 {character['rank']} — ⭐ Level {character['level']}\n"
        f"💰 Coins: {character['coins']}\n"
        f"⚔️ Power: {character['power']} 🛡 Defense: {character['defense']}\n"
        f"🏆 Wins: {character['wins']} 💀 Losses: {character['losses']}\n"
        f"🚫 Banned: {'بله' if banned else 'خیر'}\n\n"
        f"برای تغییر:\n"
        f"/addcoins {target_id} <مقدار>\n"
        f"/addxp {target_id} <مقدار>\n"
        f"/ban {target_id}\n"
        f"/unban {target_id}"
    )
    await message.answer(text)


@router.message(Command("addcoins"))
async def admin_addcoins(message: Message, command: CommandObject):
    if not _admin_guard(message.from_user.id):
        return
    parts = (command.args or "").split()
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].lstrip("-").isdigit():
        await message.answer("استفاده: /addcoins <user_id> <amount>")
        return
    target_id, amount = int(parts[0]), int(parts[1])
    if not await db.get_character(target_id):
        await message.answer("❌ کاربر شخصیت ندارد.")
        return
    await db.add_coins(target_id, amount, "admin_adjust")
    await db.log_admin_action(message.from_user.id, "addcoins", target_id, str(amount))
    await message.answer(f"✅ {amount} Coins به کاربر {target_id} اضافه شد.")


@router.message(Command("addxp"))
async def admin_addxp(message: Message, command: CommandObject):
    if not _admin_guard(message.from_user.id):
        return
    parts = (command.args or "").split()
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].lstrip("-").isdigit():
        await message.answer("استفاده: /addxp <user_id> <amount>")
        return
    target_id, amount = int(parts[0]), int(parts[1])
    if not await db.get_character(target_id):
        await message.answer("❌ کاربر شخصیت ندارد.")
        return
    await db.add_xp(target_id, amount)
    await db.log_admin_action(message.from_user.id, "addxp", target_id, str(amount))
    await message.answer(f"✅ {amount} XP به کاربر {target_id} اضافه شد.")


@router.callback_query(F.data == "admin:ban")
async def admin_ban_start(callback: CallbackQuery, state: FSMContext):
    if not _admin_guard(callback.from_user.id):
        await callback.answer("⛔️ دسترسی ندارید.", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_ban)
    await callback.message.edit_text("🚫 User ID بازیکنی که می‌خواهی Ban کنی را بفرست:")


@router.message(AdminStates.waiting_ban)
async def admin_ban_apply(message: Message, state: FSMContext):
    if not _admin_guard(message.from_user.id):
        return
    await state.clear()
    if not message.text or not message.text.strip().isdigit():
        await message.answer("❌ باید یک عدد (User ID) بفرستی.")
        return
    target_id = int(message.text.strip())
    await db.set_banned(target_id, True)
    await db.log_admin_action(message.from_user.id, "ban", target_id)
    await message.answer(f"🚫 کاربر {target_id} بن شد.")


@router.callback_query(F.data == "admin:unban")
async def admin_unban_start(callback: CallbackQuery, state: FSMContext):
    if not _admin_guard(callback.from_user.id):
        await callback.answer("⛔️ دسترسی ندارید.", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_unban)
    await callback.message.edit_text("✅ User ID بازیکنی که می‌خواهی Unban کنی را بفرست:")


@router.message(AdminStates.waiting_unban)
async def admin_unban_apply(message: Message, state: FSMContext):
    if not _admin_guard(message.from_user.id):
        return
    await state.clear()
    if not message.text or not message.text.strip().isdigit():
        await message.answer("❌ باید یک عدد (User ID) بفرستی.")
        return
    target_id = int(message.text.strip())
    await db.set_banned(target_id, False)
    await db.log_admin_action(message.from_user.id, "unban", target_id)
    await message.answer(f"✅ کاربر {target_id} از حالت بن خارج شد.")


@router.message(Command("news"))
async def admin_news(message: Message, command: CommandObject):
    if not _admin_guard(message.from_user.id):
        return
    if not command.args or "|" not in command.args:
        await message.answer("استفاده: /news عنوان | متن خبر")
        return
    title, content = command.args.split("|", 1)
    await db.add_news(title.strip(), content.strip(), message.from_user.id)
    await db.log_admin_action(message.from_user.id, "news", details=title.strip())
    await message.answer("✅ خبر منتشر شد.")
