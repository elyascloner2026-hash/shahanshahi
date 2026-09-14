# 👑 شاهنشاهی | SHAHANSHAHI

یک بازی متنی/استراتژیک تلگرامی، ساخته‌شده با aiogram 3.x و SQLite.

- 🤖 Bot: [@ShahanshahiRPGBot](https://t.me/ShahanshahiRPGBot)
- 📢 Channel: [@ShahanshahiGameBot](https://t.me/ShahanshahiGameBot)

## امکانات نسخه اول

👤 Character · ⭐ Level/XP · 🎖 Rank · 🏛 Territory · 💰 Coins · ⚔️ Fight ·
👥 Group Fight · 🃏 Heroes · 📜 Quests · 🛒 Shop · 🎒 Inventory ·
🏆 Leaderboard · 👑 Admin Panel

## نصب

### ۱. نصب Python

نسخه 3.11 یا بالاتر لازم است:

```bash
python3 --version
```

اگر نصب نیست، از [python.org](https://www.python.org/downloads/) دانلود کن.

### ۲. کلون یا کپی پروژه و نصب Dependencies

```bash
cd shahanshahi
python3 -m venv venv
source venv/bin/activate   # ویندوز: venv\Scripts\activate
pip install -r requirements.txt
```

### ۳. ساخت Bot با BotFather و گرفتن Token

1. در تلگرام به [@BotFather](https://t.me/BotFather) پیام بده.
2. دستور `/newbot` را بفرست و نام/یوزرنیم بات را وارد کن (یوزرنیم باید `ShahanshahiRPGBot` باشد تا با پروژه هماهنگ باشد).
3. توکنی که BotFather می‌دهد را کپی کن — **این توکن را جایی جز فایل `.env` قرار نده.**

### ۴. تنظیم `.env`

فایل `.env.example` را کپی کن:

```bash
cp .env.example .env
```

و مقادیر را پر کن:

```
BOT_TOKEN=توکن_واقعی_بات_شما
ADMIN_IDS=7224258053
CHANNEL_USERNAME=@ShahanshahiGameBot
DATABASE_PATH=shahanshahi.db
FIGHT_COOLDOWN=300
```

- `ADMIN_IDS` می‌تواند چند آیدی با کاما جدا شده داشته باشد: `111,222,333`
- `.env` هرگز نباید داخل Git کامیت شود (در `.gitignore` قرار دارد).

### ۵. تنظیم کانال

1. ربات را به کانال `@ShahanshahiGameBot` (یا کانال خودت) به‌عنوان **ادمین** اضافه کن — بدون این کار، بررسی عضویت کاربران کار نمی‌کند.
2. مطمئن شو `CHANNEL_USERNAME` در `.env` دقیقاً با یوزرنیم کانال یکی است.

### ۶. تنظیم Admin ID

آیدی عددی تلگرام خودت را (نه یوزرنیم) در `ADMIN_IDS` قرار بده. برای گرفتن آیدی عددی می‌توانی از [@userinfobot](https://t.me/userinfobot) کمک بگیری.

### ۷. اجرای Bot

```bash
python bot.py
```

اگر همه‌چیز درست باشد، بات شروع به Polling می‌کند و آماده دریافت پیام است.

### ۸. اضافه‌کردن Bot به گروه

1. بات را به گروه/سوپرگروه اضافه کن.
2. برای فعال شدن کامل قابلیت‌های Fight در گروه، بهتر است بات ادمین گروه باشد (لازم برای خواندن پیام‌های Reply و غیره در برخی تنظیمات حریم خصوصی گروه).
3. در گروه بنویس `/menu` تا منوی گروهی باز شود.

## دستورات اصلی

| دستور | توضیح |
|---|---|
| `/start` | ورود به بازی / ساخت شخصیت (فقط پیوی) |
| `/profile` | مشاهده پروفایل |
| `/fight @username` یا Reply + `/fight` | مبارزه |
| `/menu` یا `/shahanshahi` | منوی گروه |
| `/admin` | پنل ادمین (فقط برای Admin IDs) |

## اجرای تست‌ها

```bash
pytest
```

## مشکلات رایج

**بات به پیام‌ها پاسخ نمی‌دهد:**
- بررسی کن `BOT_TOKEN` در `.env` درست است.
- بررسی کن پروسه `python bot.py` در حال اجراست و خطایی در ترمینال چاپ نشده.

**بررسی عضویت کانال همیشه شکست می‌خورد:**
- بات باید در کانال **ادمین** باشد تا بتواند وضعیت عضویت را بخواند.
- `CHANNEL_USERNAME` در `.env` باید دقیقاً با `@` شروع شود.

**`/fight` در گروه کار نمی‌کند:**
- هر دو بازیکن باید قبلاً در پیوی بات `/start` زده و شخصیت ساخته باشند.
- مطمئن شو با خودت مبارزه نمی‌کنی و Cooldown تمام شده.

**دیتابیس پاک شد / اطلاعات از بین رفت:**
- فایل SQLite مشخص‌شده در `DATABASE_PATH` را حذف یا جابه‌جا نکن؛ برای بکاپ‌گیری کافیست همین فایل را کپی کنی.

## ساختار پروژه

```
shahanshahi/
├── bot.py              # نقطه ورود
├── config.py            # خواندن تنظیمات از .env
├── database.py          # لایه SQLite (schema + queries)
├── requirements.txt
├── .env.example
├── handlers/             # پردازش دستورات و کال‌بک‌ها
│   ├── start.py
│   ├── profile.py
│   ├── fight.py
│   ├── heroes.py
│   ├── quests.py
│   ├── shop.py
│   ├── group.py
│   └── admin.py
├── game/                 # فرمول‌ها و منطق خالص بازی (بدون DB)
│   ├── levels.py
│   ├── ranks.py
│   ├── battles.py
│   ├── heroes.py
│   └── quests.py
├── utils/
│   ├── keyboards.py
│   └── helpers.py
└── tests/
```

## یادداشت طراحی

- آسیب به Hero Event بر اساس Power شخصیت (به‌علاوه تصادفی‌بودن) در سمت سرور محاسبه می‌شود، نه عددی که کاربر تایپ می‌کند — تا از تقلب جلوگیری شود.
- تمام مقادیر Coins هرگز منفی نمی‌شوند.
- Cooldown مبارزه کاملاً سمت سرور (در دیتابیس) بررسی می‌شود.
