from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import db
from game.premium import PREMIUM
from game.gem_shop import is_admin
from config import ADMIN_IDS
from utils.keyboards import back_kb

router = Router(name="premium")


@router.callback_query(F.data == "menu:gems")
async def show_premium_menu(callback: CallbackQuery):
    character = await db.get_character(callback.from_user.id)

    if not character:
        await callback.answer("ابتدا باید /start بزنید.", show_alert=True)
        return

    unlocked = await db.get_premium(callback.from_user.id)

    await callback.message.edit_text(
        premium_text(character, unlocked),
        reply_markup=premium_kb(unlocked),
    )

    await callback.answer()


def premium_kb(unlocked):
    b = InlineKeyboardBuilder()
    for code, item in PREMIUM.items():
        mark = "✅" if code in unlocked else "💎"
        b.button(text=f"{mark} {item['name']} — {item['price']} جم", callback_data=f"gem_buy:{code}")
    b.adjust(1)
    b.button(text="🔙 بازگشت", callback_data="menu:main")
    return b.as_markup()


def premium_text(c, unlocked):
    lines = [f"💎 <b>خزانه جم</b>", f"موجودی: <b>{c['gems']} 💎</b>", "", "قابلیت‌های زیر فقط با جم باز می‌شوند:"]
    for code, item in PREMIUM.items():
        status = "✅ باز شده" if code in unlocked else f"💎 {item['price']} جم"
        lines.append(f"• <b>{item['name']}</b> — {item['desc']} ({status})")
    lines.append("\n💎 جم توسط شاهنشاه به بازیکن‌ها انتقال داده می‌شود؛ بازیکن‌ها جم رایگان از سیستم دریافت نمی‌کنند.")
    return "\n".join(lines)


@router.callback_query(F.data.startswith("gem_buy:"))
async def gem_buy(callback: CallbackQuery):
    code = callback.data.split(":", 1)[1]
    item = PREMIUM.get(code)
    if not item:
        await callback.answer("❌ قابلیت نامعتبر.", show_alert=True)
        return
    if await db.has_premium(callback.from_user.id, code):
        await callback.answer("✅ این قابلیت قبلاً باز شده.", show_alert=True)
        return
    ok = await db.unlock_premium(callback.from_user.id, code, item["price"])
    if not ok:
        await callback.answer("💎 جم کافی نداری؛ اول از شاهنشاه جم بخر.", show_alert=True)
        return
    c = await db.get_character(callback.from_user.id)
    unlocked = await db.get_premium(callback.from_user.id)
    await callback.message.edit_text(premium_text(c, unlocked), reply_markup=premium_kb(unlocked))
    await callback.answer(f"🎉 {item['name']} باز شد!")

@router.message(F.text.regexp(r"^/gemtransfer(?:@\\w+)?\\s+\\d+$"))
async def gem_transfer(message):
    """Transfer owned Gems by replying to the recipient's message."""
    if not message.reply_to_message or not message.reply_to_message.from_user:
        await message.answer("💎 برای انتقال جم، روی پیام شخص موردنظر ریپلای کن و بنویس: /gemtransfer 100")
        return
    try:
        amount = int((message.text or "").split()[-1])
    except (ValueError, IndexError):
        await message.answer("❌ مقدار جم نامعتبر است.")
        return
    sender_id = message.from_user.id
    receiver_id = message.reply_to_message.from_user.id
    if amount <= 0:
        await message.answer("❌ مقدار جم باید بیشتر از صفر باشد.")
        return
    if receiver_id == sender_id:
        await message.answer("❌ نمی‌توانی جم را به خودت منتقل کنی.")
        return
    receiver = await db.get_character(receiver_id)
    sender = await db.get_character(sender_id)
    if not sender or not receiver:
        await message.answer("❌ هر دو نفر باید اول بازی را شروع کرده باشند.")
        return
    if is_admin(receiver_id):
        await message.answer("👑 جم خزانه شاهنشاه قابل انتقال به بازیکن نیست.")
        return
    ok = await db.transfer_gems(sender_id, receiver_id, amount)
    if not ok:
        await message.answer("❌ جم کافی نداری یا انتقال انجام نشد.")
        return
    await message.answer(
        f"💎 انتقال انجام شد!\n{amount:,} جم به <b>{receiver['name']}</b> منتقل شد."
    )
