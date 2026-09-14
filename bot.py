import asyncio
import logging
import os

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Update

from config import BOT_TOKEN
from database import db
from game.heroes import spawn_hero
from game.quests import quest_seed_rows

from handlers import start, profile, fight, heroes, quests, shop, group, admin


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

                await db.create_hero_event(
                    hero["name"],
                    hero["hp"],
                    hero["power"],
                    hero["rarity"],
                )

                logger.info(
                    "Spawned hero event: %s (%s)",
                    hero["name"],
                    hero["rarity"],
                )

        except Exception:
            logger.exception("Hero event scheduler failed")

        await asyncio.sleep(HERO_EVENT_INTERVAL)


def build_dispatcher():
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(start.router)
    dp.include_router(profile.router)
    dp.include_router(fight.router)
    dp.include_router(heroes.router)
    dp.include_router(quests.router)
    dp.include_router(shop.router)
    dp.include_router(group.router)
    dp.include_router(admin.router)

    return dp


async def create_app():
    await db.connect()
    await seed_quests()

    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = build_dispatcher()

    webhook_base = (
        os.getenv("WEBHOOK_URL")
        or os.getenv("RENDER_EXTERNAL_URL")
        or ""
    ).rstrip("/")

    if not webhook_base.startswith("https://"):
        raise RuntimeError(
            "WEBHOOK_URL must be a public HTTPS URL"
        )

    webhook_url = webhook_base + WEBHOOK_PATH
    webhook_secret = os.getenv("WEBHOOK_SECRET", "").strip()

    async def health(request):
        return web.json_response({"status": "ok"})

    async def telegram_webhook(request):
        if webhook_secret:
            received = request.headers.get(
                "X-Telegram-Bot-Api-Secret-Token",
                ""
            )

            if received != webhook_secret:
                raise web.HTTPForbidden(text="Forbidden")

        try:
            data = await request.json()
            update = Update.model_validate(data)

            await dp.feed_update(bot, update)

        except Exception:
            logger.exception(
                "Failed to process Telegram webhook update"
            )
            raise web.HTTPBadRequest(text="Invalid update")

        return web.Response(text="OK")

    app = web.Application()

    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    app.router.add_post(WEBHOOK_PATH, telegram_webhook)

    # Keep the webhook registered.
    # This is important because Render can sleep the service.
    await bot.set_webhook(
        url=webhook_url,
        secret_token=webhook_secret or None,
        drop_pending_updates=False,
    )

    logger.info("Telegram webhook set: %s", webhook_url)

    scheduler_task = asyncio.create_task(
        hero_event_scheduler(bot)
    )

    async def on_cleanup(app):
        scheduler_task.cancel()

        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass

        await db.close()
        await bot.session.close()

    app.on_cleanup.append(on_cleanup)

    return app


def main():
    port = int(os.getenv("PORT", "8080"))

    web.run_app(
        create_app(),
        host="0.0.0.0",
        port=port,
    )


if __name__ == "__main__":
    main()
