import logging

from aiogram import Bot

from bot import texts
from bot.database import list_due_reminders, mark_reminder_sent

logger = logging.getLogger(__name__)


async def send_due_reminders(bot: Bot, database_path: str) -> None:
    due_reminders = list_due_reminders(database_path)

    if not due_reminders:
        logger.info("No due reminders found.")
        return

    logger.info("Found %s due reminders.", len(due_reminders))

    for reminder in due_reminders:
        try:
            await bot.send_message(
                chat_id=reminder.item.user_id,
                text=texts.format_reminder_text(reminder),
            )
        except Exception:
            logger.exception(
                "Failed to send reminder for item_id=%s.",
                reminder.item.id,
            )
            continue

        mark_reminder_sent(
            database_path=database_path,
            item_id=reminder.item.id,
            user_id=reminder.item.user_id,
            offset_days=reminder.offset_days,
            reminder_date=reminder.reminder_date,
        )
