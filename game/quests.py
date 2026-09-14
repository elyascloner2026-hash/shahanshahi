"""
Static quest definitions.

Quests are simple: a title, a short scene, and 2-3 choices each with
their own coin/xp reward multiplier. Loaded into the DB on startup via
database.upsert_quest so editing this file is enough to add content.
"""
import json

DAILY_QUESTS = [
    {
        "code": "caravan_parseh",
        "title": "📜 کاروان پارس",
        "description": "یک کاروان در مسیر پارسه قرار دارد.",
        "choices": {
            "🛡 محافظت": {"coins": 60, "xp": 25},
            "💰 دریافت مالیات": {"coins": 90, "xp": 10},
            "🤝 همکاری": {"coins": 40, "xp": 40},
        },
        "reward_coins": 0,  # actual reward comes from the chosen option
        "reward_xp": 0,
    },
    {
        "code": "border_patrol",
        "title": "🛡 گشت مرزی",
        "description": "مرزهای قلمرو نیاز به گشت‌زنی دارند.",
        "choices": {
            "🐎 گشت سریع": {"coins": 50, "xp": 30},
            "🏕 اردوی شبانه": {"coins": 70, "xp": 15},
        },
        "reward_coins": 0,
        "reward_xp": 0,
    },
]

STORY_QUESTS = [
    {
        "code": "story_the_first_flame",
        "title": "📖 نخستین شعله",
        "description": "کاتب دربار داستانی از آغاز شاهنشاهی برایت بازگو می‌کند.",
        "choices": {
            "📖 ادامه بده": {"coins": 100, "xp": 80},
        },
        "reward_coins": 0,
        "reward_xp": 0,
    },
]


def quest_seed_rows():
    rows = []
    for q in DAILY_QUESTS:
        rows.append((q["code"], "daily", q["title"], q["description"],
                      json.dumps(q["choices"], ensure_ascii=False),
                      q["reward_coins"], q["reward_xp"]))
    for q in STORY_QUESTS:
        rows.append((q["code"], "story", q["title"], q["description"],
                      json.dumps(q["choices"], ensure_ascii=False),
                      q["reward_coins"], q["reward_xp"]))
    return rows
