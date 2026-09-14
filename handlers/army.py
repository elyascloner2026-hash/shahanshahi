"""Army shop, army status and two-charge full heal system."""
import time
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import db
from game.army import UNITS, UNIT_FAMILIES
from utils.keyboards import back_kb

router = Router(name="army")
HEAL_COOLDOWN = 600



def family_kb():
    b = InlineKeyboardBuilder()
    for family, (name, emoji, *_rest) in UNIT_FAMILIES.items():
        b.button(text=f"{emoji} {name} 🪖", callback_data=f"army_family:{family}")
    b.adjust(1)
    b.row(InlineKeyboardButton(text="💚 هیل ۱", callback_data="army_heal:1"), InlineKeyboardButton(text="💚 هیل ۲", callback_data="army_heal:2"))
    b.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu:main"))
    return b.as_markup()


def level_kb(family):
    b = InlineKeyboardBuilder()
    for level in range(1, 16):
        u = UNITS[f"{family}_{level}"]
        b.button(text=f"سطح {level} — {u.power}⚔️/{u.defense}🛡 — {u.price}💰", callback_data=f"army_buy:{u.code}")
    b.adjust(1)
    b.row(InlineKeyboardButton(text="🔙 انواع ارتش", callback_data="menu:army"))
    return b.as_markup()


def army_text(rows, slots, now):
    lines = ["⚔️ <b>ارتش من</b>", ""]
    total = 0
    for r in rows:
        u = UNITS.get(r["unit_code"])
        if not u: continue
        total += r["quantity"]
        lines.append(f"{u.emoji} {u.name}: <b>{r['quantity']}</b> | ⚔️{u.power} | 🛡{u.defense}")
    lines += ["", f"👥 تعداد کل: <b>{total}</b>"]
    for i in (1,2):
        used = slots[f"heal_{i}_used_at"] if slots else 0
        if not used:
            status = "✅ آماده"
        else:
            left = max(0, HEAL_COOLDOWN - (now-used))
            status = "⏳ آماده در %d:%02d" % (left//60, left%60) if left else "✅ آماده"
        lines.append(f"💚 هیل {i}: {status}")
    return "\n".join(lines)


async def refresh_army_message(callback):
    rows = await db.get_all_army(callback.from_user.id)
    slots = await db.get_heal_slots(callback.from_user.id)
    await callback.message.edit_text(army_text(rows, slots, int(time.time())), reply_markup=family_kb())


@router.callback_query(F.data == "menu:army")
async def show_army(callback: CallbackQuery):
    await refresh_army_message(callback)
    await callback.answer()


@router.callback_query(F.data.startswith("army_family:"))
async def show_family(callback: CallbackQuery):
    family = callback.data.split(":",1)[1]
    if family not in UNIT_FAMILIES:
        await callback.answer("❌ نوع ارتش نامعتبر است.", show_alert=True); return
    name, emoji, *_ = UNIT_FAMILIES[family]
    await callback.message.edit_text(
        f"{emoji} <b>{name}</b> — انتخاب سطح\n\n"
        "هرچه سطح بالاتر باشد، قدرت و دفاع سرباز بیشتر و قیمت آن بالاتر است.\n"
        "حداکثر سطح: <b>۱۵</b>",
        reply_markup=level_kb(family),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("army_buy:"))
async def buy_unit(callback: CallbackQuery):
    code = callback.data.split(":",1)[1]
    unit = UNITS.get(code)
    c = await db.get_character(callback.from_user.id)
    if not unit or not c:
        await callback.answer("❌ خطا", show_alert=True); return
    price = int(unit.price * (0.80 if await db.has_premium(c["user_id"], "royal_army") else 1.0))
    if c["coins"] < price:
        await callback.answer(f"💰 سکه کافی نداری. قیمت: {price}", show_alert=True); return
    await db.add_coins(c["user_id"], -price, f"army_buy:{code}")
    await db.add_units(c["user_id"], code, 1)
    await callback.answer(f"✅ یک {unit.name} خریدی! (-{price} سکه)")
    rows = await db.get_all_army(c["user_id"]); slots = await db.get_heal_slots(c["user_id"])
    await callback.message.edit_text(army_text(rows, slots, int(time.time())), reply_markup=family_kb())


@router.callback_query(F.data.startswith("army_heal:"))
async def heal_army(callback: CallbackQuery):
    slot = int(callback.data.split(":",1)[1])
    if slot not in (1,2):
        await callback.answer("❌ هیل نامعتبر است.", show_alert=True); return
    now = int(time.time())
    cooldown = 300 if await db.has_premium(callback.from_user.id, "rapid_heal") else HEAL_COOLDOWN
    slots = await db.get_heal_slots(callback.from_user.id)
    used = slots[f"heal_{slot}_used_at"] if slots else 0
    if used and now-used < cooldown:
        left = cooldown-(now-used)
        await callback.answer(f"⏳ این هیل {left//60}:{left%60:02d} دیگر آماده می‌شود.", show_alert=True); return
    await db.heal_army(callback.from_user.id)
    await db.use_heal_slot(callback.from_user.id, slot, now)
    await callback.answer("💚 کل ارتش کامل هیل شد! این هیل ۱۰ دقیقه بعد برمی‌گردد.")
    rows = await db.get_all_army(callback.from_user.id); slots = await db.get_heal_slots(callback.from_user.id)
    await callback.message.edit_text(army_text(rows, slots, now), reply_markup=family_kb())
