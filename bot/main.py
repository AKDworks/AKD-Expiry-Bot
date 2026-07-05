import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.config import load_config
from bot.database import init_db
from bot.handlers import router
from bot.reminders import send_due_reminders


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

    try:
        await dispatcher.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)


if __name__ == "__main__":
    asyncio.run(main())
