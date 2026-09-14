"""
Shahanshahi (شاهنشاهی) — Telegram RPG bot.

Entrypoint. Run with: python bot.py
"""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database import db
from game.heroes import spawn_hero
from game.quests import quest_seed_rows

from handlers import start, profile, fight, heroes, quests, shop, group, admin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("shahanshahi")

HERO_EVENT_INTERVAL = 24 * 60 * 60  # seconds


async def seed_quests():
    for row in quest_seed_rows():
        await db.upsert_quest(*row)


async def hero_event_scheduler(bot: Bot):
    """Spawns a new Hero Event every 24h if none is currently active."""
    while True:
        try:
            active = await db.get_active_hero_event()
            if not active:
                hero = spawn_hero()
                await db.create_hero_event(
                    hero["name"], hero["hp"], hero["power"], hero["rarity"]
                )
                logger.info("Spawned hero event: %s (%s)", hero["name"], hero["rarity"])
        except Exception:
            logger.exception("Hero event scheduler failed")
        await asyncio.sleep(HERO_EVENT_INTERVAL)


async def main():
    await db.connect()
    await seed_quests()

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(start.router)
    dp.include_router(profile.router)
    dp.include_router(fight.router)
    dp.include_router(heroes.router)
    dp.include_router(quests.router)
    dp.include_router(shop.router)
    dp.include_router(group.router)
    dp.include_router(admin.router)

    asyncio.create_task(hero_event_scheduler(bot))

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
