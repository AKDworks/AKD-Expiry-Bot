import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.config import load_config
from bot.database import init_db
from bot.handlers import router
from bot.reminders import send_due_reminders


async def health_check(request: web.Request) -> web.Response:
    return web.Response(text="AKD Expiry Bot is running")


async def start_health_server() -> web.AppRunner:
    port = int(os.getenv("PORT", "10000"))
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    logging.info("Health server started on port %s", port)
    return runner


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    config = load_config()
    init_db(config.database_path)

    bot = Bot(token=config.bot_token)
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        send_due_reminders,
        trigger="cron",
        hour=config.reminder_hour,
        minute=config.reminder_minute,
        args=(bot, config.database_path),
    )
    scheduler.start()

    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher["database_path"] = config.database_path
    dispatcher["project_github_url"] = config.project_github_url
    dispatcher.include_router(router)

    await send_due_reminders(bot, config.database_path)

    health_runner = None
    if os.getenv("PORT"):
        health_runner = await start_health_server()

    try:
        await dispatcher.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        if health_runner is not None:
            await health_runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
