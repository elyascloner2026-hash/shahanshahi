"""
Shop (buy equipment) and inventory display.
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery

from database import db
from utils.keyboards import shop_kb, back_kb

router = Router(name="shop")


@router.callback_query(F.data == "menu:shop")
async def show_shop(callback: CallbackQuery):
    character = await db.get_character(callback.from_user.id)
    if not character:
        await callback.answer("ابتدا باید /start بزنید.", show_alert=True)
        return
    items = await db.list_items()
    await callback.message.edit_text(
        f"🛒 <b>فروشگاه</b>\n\n💰 Coins شما: {character['coins']}",
        reply_markup=shop_kb(items),
    )


@router.callback_query(F.data.startswith("buy:"))
async def buy_item(callback: CallbackQuery):
    item_id = int(callback.data.split(":", 1)[1])
    character = await db.get_character(callback.from_user.id)
    item = await db.get_item(item_id)

    if not character or not item:
        await callback.answer("خطا در خرید.", show_alert=True)
        return

    if character["coins"] < item["price"]:
        await callback.answer("💰 سکه کافی نداری.", show_alert=True)
        return

    await db.add_coins(callback.from_user.id, -item["price"], f"shop_buy:{item['name']}")
    await db.add_inventory_item(callback.from_user.id, item_id)
    await db.update_character(
        callback.from_user.id,
        power=character["power"] + item["power_bonus"],
        defense=character["defense"] + item["defense_bonus"],
    )

    await callback.answer(f"✅ {item['name']} خریداری شد!")
    items = await db.list_items()
    character = await db.get_character(callback.from_user.id)
    await callback.message.edit_text(
        f"🛒 <b>فروشگاه</b>\n\n💰 Coins شما: {character['coins']}",
        reply_markup=shop_kb(items),
    )


@router.callback_query(F.data == "menu:inventory")
async def show_inventory(callback: CallbackQuery):
    character = await db.get_character(callback.from_user.id)
    if not character:
        await callback.answer("ابتدا باید /start بزنید.", show_alert=True)
        return

    inventory = await db.get_inventory(callback.from_user.id)
    heroes = await db.get_heroes(callback.from_user.id)

    lines = ["🎒 <b>کوله‌پشتی</b>\n"]
    lines.append(f"🃏 Hero Cards: {len(heroes)}")
    if inventory:
        lines.append("\n⚔️ Equipment:")
        for row in inventory:
            lines.append(f"{row['emoji']} {row['name']} x{row['quantity']}")
    else:
        lines.append("\n⚔️ Equipment: خالی")

    await callback.message.edit_text("\n".join(lines), reply_markup=back_kb())
