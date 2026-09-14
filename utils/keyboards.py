"""
All inline keyboard builders in one place, so menu layout changes
never require touching handler logic.
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import CHANNEL_LINK


def join_channel_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📢 عضویت در کانال", url=CHANNEL_LINK)
    b.button(text="✅ بررسی عضویت", callback_data="check_membership")
    b.adjust(1)
    return b.as_markup()


def gender_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="👨 مرد", callback_data="gender:مرد")
    b.button(text="👩 زن", callback_data="gender:زن")
    b.adjust(2)
    return b.as_markup()


def territory_kb(territories) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for t in territories:
        b.button(text=f"{t['emoji']} {t['name']}", callback_data=f"territory:{t['name']}")
    b.adjust(2)
    return b.as_markup()


def city_kb(cities, fallback_territory: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if cities:
        for c in cities:
            b.button(text=c["name"], callback_data=f"city:{c['name']}")
    else:
        # No predefined cities yet — let the capital city name equal territory
        b.button(text=f"پایتخت {fallback_territory}", callback_data=f"city:{fallback_territory}")
    b.adjust(2)
    return b.as_markup()


def main_menu_private() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="👤 پروفایل", callback_data="menu:profile")
    b.button(text="🏛 قلمرو من", callback_data="menu:territory")
    b.button(text="⚔️ فایت", callback_data="menu:fight")
    b.button(text="🃏 قهرمانان", callback_data="menu:heroes")
    b.button(text="📜 مأموریت‌ها", callback_data="menu:quests")
    b.button(text="🛒 فروشگاه", callback_data="menu:shop")
    b.button(text="🎒 کوله‌پشتی", callback_data="menu:inventory")
    b.button(text="🏆 لیدربورد", callback_data="menu:leaderboard")
    b.button(text="📰 اخبار", callback_data="menu:news")
    b.button(text="⚙️ تنظیمات", callback_data="menu:settings")
    b.adjust(2)
    return b.as_markup()


def main_menu_group() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="⚔️ فایت", callback_data="menu:fight")
    b.button(text="🏆 لیدربورد", callback_data="menu:group_leaderboard")
    b.button(text="🃏 قهرمان", callback_data="menu:hero_event")
    b.button(text="📊 آمار گروه", callback_data="menu:group_stats")
    b.adjust(2)
    return b.as_markup()


def back_kb(target: str = "menu:main") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🔙 بازگشت", callback_data=target)
    return b.as_markup()


def challenge_kb(target_user_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="⚔️ Challenge", callback_data=f"challenge:{target_user_id}")
    return b.as_markup()


def quest_choice_kb(quest_code: str, choices: list[str]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for i, choice in enumerate(choices):
        b.button(text=choice, callback_data=f"quest:{quest_code}:{i}")
    b.adjust(1)
    b.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu:quests"))
    return b.as_markup()


def shop_kb(items) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for item in items:
        b.button(text=f"{item['emoji']} {item['name']} — {item['price']} 💰",
                  callback_data=f"buy:{item['id']}")
    b.adjust(1)
    b.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu:main"))
    return b.as_markup()


def leaderboard_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="⭐ Level", callback_data="lb:level")
    b.button(text="⚔️ Power", callback_data="lb:power")
    b.button(text="💰 Richest", callback_data="lb:coins")
    b.button(text="🏅 Wins", callback_data="lb:wins")
    b.adjust(2)
    b.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu:main"))
    return b.as_markup()


def admin_panel_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📊 Statistics", callback_data="admin:stats")
    b.button(text="📢 Broadcast", callback_data="admin:broadcast")
    b.button(text="👥 Find User", callback_data="admin:finduser")
    b.button(text="🚫 Ban", callback_data="admin:ban")
    b.button(text="✅ Unban", callback_data="admin:unban")
    b.adjust(2)
    return b.as_markup()
