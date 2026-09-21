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
            now = int(asyncio.get_running_loop().time())

            for group in await db.list_groups():
                chat_id = group["chat_id"]
                last_at = int(group["hero_event_last_at"] or 0)

                # A persistent timestamp in DB prevents Render restarts
                # from resetting the 24-hour schedule.
                wall_now = int(__import__("time").time())
                if last_at and wall_now - last_at < HERO_EVENT_INTERVAL:
                    continue

                active = await db.get_active_hero_event(chat_id)
                if active:
                    continue

                hero = spawn_hero()
                event_id = await db.create_hero_event(
                    hero["name"],
                    hero["hp"],
                    hero["power"],
                    hero["rarity"],
                    chat_id=chat_id,
                )
                await db.set_group_hero_event_time(chat_id, wall_now)

                event = await db.get_active_hero_event(chat_id)
                logger.info(
                    "Spawned hero event for group %s: %s (%s)",
                    chat_id,
                    hero["name"],
                    hero["rarity"],
                )

                if event:
                    await heroes.announce_hero_to_group(bot, event)

        except Exception:
            logger.exception("Hero event scheduler failed")

        await asyncio.sleep(60)


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
        try:
            if secret and request.headers.get("X-Telegram-Bot-Api-Secret-Token") != secret:
                return web.Response(status=403, text="forbidden")

            data = await request.json()
            logger.info("Telegram update received: %s", data.get("update_id"))

            update = Update.model_validate(data, context={"bot": bot})
            await dp.feed_update(bot, update)

            logger.info("Telegram update processed: %s", data.get("update_id"))
            return web.Response(text="ok")

        except Exception:
            logger.exception("WEBHOOK ERROR")
            return web.Response(status=500, text="internal error")

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
