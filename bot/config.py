from dataclasses import dataclass
from os import getenv

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    bot_token: str
    database_path: str
    reminder_minute: int
    project_github_url: str


def load_config() -> Config:
    load_dotenv()

    bot_token = getenv("BOT_TOKEN", "").strip()
    database_path = getenv("DATABASE_PATH", "akdexpiry_bot.db").strip()
    reminder_minute = _get_int("REMINDER_MINUTE", 0)
    project_github_url = getenv("PROJECT_GITHUB_URL", "").strip()

    if not bot_token:
        raise RuntimeError("BOT_TOKEN is not set. Create .env from .env.example.")

    if not 0 <= reminder_minute <= 59:
        raise RuntimeError("REMINDER_MINUTE must be between 0 and 59.")

    return Config(
        bot_token=bot_token,
        database_path=database_path or "akdexpiry_bot.db",
        reminder_minute=reminder_minute,
        project_github_url=project_github_url,
    )


def _get_int(name: str, default: int) -> int:
    value = getenv(name, "").strip()
    if not value:
        return default

    try:
        return int(value)
    except ValueError as error:
        raise RuntimeError(f"{name} must be a number.") from error
