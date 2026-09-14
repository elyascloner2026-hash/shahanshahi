"""Shahanshahi (شاهنشاهی) — Telegram RPG bot, Render webhook entrypoint."""
import asyncio
import logging
import os

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Update
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database import db
from game.heroes import spawn_hero
from game.quests import quest_seed_rows
from handlers import start, profile, fight, army, heroes, quests, shop, group, admin, premium

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("shahanshahi")

HERO_EVENT_INTERVAL = 24 * 60 * 60
WEBHOOK_PATH = "/telegram/webhook"


async def seed_quests():
    for row in quest_seed_rows():
        await db.upsert_quest(*row)


async def hero_event_scheduler(bot: Bot):
    while True:
        try:
            active = await db.get_active_hero_event()
            if not active:
                hero = spawn_hero()
                event_id = await db.create_hero_event(
                    hero["name"], hero["hp"], hero["power"], hero["rarity"]
                )
                event = await db.get_active_hero_event()
                logger.info("Spawned hero event: %s (%s)", hero["name"], hero["rarity"])
                if event:
                    await heroes.announce_hero_to_groups(bot, event)
        except Exception:
            logger.exception("Hero event scheduler failed")
        await asyncio.sleep(HERO_EVENT_INTERVAL)


async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set")

    await db.connect()
    await seed_quests()

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(start.router)
    dp.include_router(profile.router)
    dp.include_router(fight.router)
    dp.include_router(army.router)
    dp.include_router(heroes.router)
    dp.include_router(premium.router)
    dp.include_router(quests.router)
    dp.include_router(shop.router)
    dp.include_router(group.router)
    dp.include_router(admin.router)

    external_url = os.getenv("WEBHOOK_URL") or os.getenv("RENDER_EXTERNAL_URL")
    if not external_url:
        raise RuntimeError("WEBHOOK_URL or RENDER_EXTERNAL_URL is required")
    webhook_url = external_url.rstrip("/") + WEBHOOK_PATH
    secret = os.getenv("WEBHOOK_SECRET") or None

    await bot.set_webhook(
        url=webhook_url,
        secret_token=secret,
        drop_pending_updates=False,
    )
    logger.info("Webhook set: %s", webhook_url)

    scheduler = asyncio.create_task(hero_event_scheduler(bot))

    async def health(_request):
        return web.Response(text="ok")

    async def telegram_webhook(request):
        if secret and request.headers.get("X-Telegram-Bot-Api-Secret-Token") != secret:
            return web.Response(status=403, text="forbidden")
        data = await request.json()
        update = Update.model_validate(data, context={"bot": bot})
        await dp.feed_update(bot, update)
        return web.Response(text="ok")

    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    app.router.add_post(WEBHOOK_PATH, telegram_webhook)

    port = int(os.getenv("PORT", "10000"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info("HTTP server listening on %s", port)

    try:
        await asyncio.Event().wait()
    finally:
        scheduler.cancel()
        await runner.cleanup()
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
