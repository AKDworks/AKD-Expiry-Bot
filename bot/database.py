from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import sqlite3
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

_UNSET = object()


@dataclass(frozen=True)
class ExpiryItem:
    id: int
    user_id: int
    title: str
    category: str
    expires_on: str
    date_precision: str
    note: str | None
    reminder_offsets: tuple[int, ...]


@dataclass(frozen=True)
class DueReminder:
    item: ExpiryItem
    offset_days: int
    reminder_date: str


DEFAULT_REMINDER_HOUR = 9
DEFAULT_TIMEZONE = "Asia/Qyzylorda"
ALLOWED_REMINDER_HOURS = (9, 12, 18)
TIMEZONE_OPTIONS = {
    "Казахстан UTC+5": "Asia/Qyzylorda",
    "Москва UTC+3": "Europe/Moscow",
    "Минск UTC+3": "Europe/Minsk",
    "Баку UTC+4": "Asia/Baku",
    "Тбилиси UTC+4": "Asia/Tbilisi",
    "Ереван UTC+4": "Asia/Yerevan",
    "Ташкент UTC+5": "Asia/Tashkent",
    "Бишкек UTC+6": "Asia/Bishkek",
    "Новосибирск UTC+7": "Asia/Novosibirsk",
    "Владивосток UTC+10": "Asia/Vladivostok",
}


def init_db(database_path: str) -> None:
    path = Path(database_path)
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS expiry_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                expires_on TEXT NOT NULL,
                date_precision TEXT NOT NULL DEFAULT 'day',
                note TEXT,
                reminder_offsets TEXT NOT NULL DEFAULT '30,7,1,0',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        _ensure_column(
            connection,
            table_name="expiry_items",
            column_name="date_precision",
            definition="date_precision TEXT NOT NULL DEFAULT 'day'",
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_expiry_items_user_id
            ON expiry_items (user_id)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_expiry_items_expires_on
            ON expiry_items (expires_on)
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS sent_reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                offset_days INTEGER NOT NULL,
                reminder_date TEXT NOT NULL,
                sent_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (item_id, offset_days, reminder_date)
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_sent_reminders_lookup
            ON sent_reminders (item_id, offset_days, reminder_date)
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                reminder_hour INTEGER NOT NULL DEFAULT 9,
                timezone TEXT NOT NULL DEFAULT 'Asia/Qyzylorda',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        _ensure_column(
            connection,
            table_name="user_settings",
            column_name="timezone",
            definition="timezone TEXT NOT NULL DEFAULT 'Asia/Qyzylorda'",
        )


def add_item(
    database_path: str,
    user_id: int,
    title: str,
    category: str,
    expires_on: str,
    reminder_offsets: tuple[int, ...],
    date_precision: str = "day",
    note: str | None = None,
) -> int:
    offsets = _serialize_reminder_offsets(reminder_offsets)

    with sqlite3.connect(database_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO expiry_items (
                user_id,
                title,
                category,
                expires_on,
                date_precision,
                note,
                reminder_offsets
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, title, category, expires_on, date_precision, note, offsets),
        )
        return int(cursor.lastrowid)


def list_items(database_path: str, user_id: int) -> list[ExpiryItem]:
    with _connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                user_id,
                title,
                category,
                expires_on,
                date_precision,
                note,
                reminder_offsets
            FROM expiry_items
            WHERE user_id = ?
            ORDER BY expires_on ASC, id ASC
            """,
            (user_id,),
        ).fetchall()

    return [_row_to_item(row) for row in rows]


def get_item(database_path: str, user_id: int, item_id: int) -> ExpiryItem | None:
    with _connect(database_path) as connection:
        row = connection.execute(
            """
            SELECT
                id,
                user_id,
                title,
                category,
                expires_on,
                date_precision,
                note,
                reminder_offsets
            FROM expiry_items
            WHERE user_id = ? AND id = ?
            """,
            (user_id, item_id),
        ).fetchone()

    if row is None:
        return None

    return _row_to_item(row)


def delete_item(database_path: str, user_id: int, item_id: int) -> bool:
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            DELETE FROM sent_reminders
            WHERE user_id = ? AND item_id = ?
            """,
            (user_id, item_id),
        )
        cursor = connection.execute(
            """
            DELETE FROM expiry_items
            WHERE user_id = ? AND id = ?
            """,
            (user_id, item_id),
        )
        return cursor.rowcount > 0


def update_item(
    database_path: str,
    user_id: int,
    item_id: int,
    *,
    title: str | None = None,
    category: str | None = None,
    expires_on: str | None = None,
    date_precision: str | None = None,
    note: str | None | object = _UNSET,
    reminder_offsets: tuple[int, ...] | None = None,
) -> bool:
    updates: list[str] = []
    values: list[object] = []

    if title is not None:
        updates.append("title = ?")
        values.append(title)

    if category is not None:
        updates.append("category = ?")
        values.append(category)

    if expires_on is not None:
        updates.append("expires_on = ?")
        values.append(expires_on)

    if date_precision is not None:
        updates.append("date_precision = ?")
        values.append(date_precision)

    if note is not _UNSET:
        updates.append("note = ?")
        values.append(note)

    if reminder_offsets is not None:
        updates.append("reminder_offsets = ?")
        values.append(_serialize_reminder_offsets(reminder_offsets))

    if not updates:
        return False

    values.extend([user_id, item_id])

    with sqlite3.connect(database_path) as connection:
        cursor = connection.execute(
            f"""
            UPDATE expiry_items
            SET {", ".join(updates)}
            WHERE user_id = ? AND id = ?
            """,
            values,
        )

        if cursor.rowcount <= 0:
            return False

        if expires_on is not None or reminder_offsets is not None:
            connection.execute(
                """
                DELETE FROM sent_reminders
                WHERE user_id = ? AND item_id = ?
                """,
                (user_id, item_id),
            )

        return True


def list_due_reminders(
    database_path: str,
    now: datetime | None = None,
) -> list[DueReminder]:
    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)

    due_reminders: list[DueReminder] = []

    with _connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT
                expiry_items.id,
                expiry_items.user_id,
                expiry_items.title,
                expiry_items.category,
                expiry_items.expires_on,
                expiry_items.date_precision,
                expiry_items.note,
                expiry_items.reminder_offsets,
                COALESCE(user_settings.reminder_hour, ?) AS reminder_hour,
                COALESCE(user_settings.timezone, ?) AS timezone
            FROM expiry_items
            LEFT JOIN user_settings
                ON user_settings.user_id = expiry_items.user_id
            ORDER BY expiry_items.expires_on ASC, expiry_items.id ASC
            """,
            (DEFAULT_REMINDER_HOUR, DEFAULT_TIMEZONE),
        ).fetchall()

        for row in rows:
            item = _row_to_item(row)
            expires_on = date.fromisoformat(item.expires_on)
            user_now = _localize_time(current_time, row["timezone"])
            target_date = user_now.date()

            if expires_on < target_date:
                continue

            if int(row["reminder_hour"]) != user_now.hour:
                continue

            for offset_days in item.reminder_offsets:
                expected_reminder_date = expires_on - timedelta(days=offset_days)
                if expected_reminder_date != target_date:
                    continue

                already_sent = _is_reminder_sent(
                    connection=connection,
                    item_id=item.id,
                    offset_days=offset_days,
                    reminder_date=target_date.isoformat(),
                )
                if already_sent:
                    continue

                due_reminders.append(
                    DueReminder(
                        item=item,
                        offset_days=offset_days,
                        reminder_date=target_date.isoformat(),
                    )
                )

    return due_reminders


def get_user_settings(database_path: str, user_id: int) -> tuple[int, str]:
    with _connect(database_path) as connection:
        row = connection.execute(
            """
            SELECT reminder_hour, timezone
            FROM user_settings
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

    if row is None:
        return DEFAULT_REMINDER_HOUR, DEFAULT_TIMEZONE

    return int(row["reminder_hour"]), row["timezone"]


def get_user_reminder_hour(database_path: str, user_id: int) -> int:
    reminder_hour, _timezone = get_user_settings(database_path, user_id)
    return reminder_hour


def set_user_reminder_hour(database_path: str, user_id: int, reminder_hour: int) -> None:
    if reminder_hour not in ALLOWED_REMINDER_HOURS:
        raise ValueError("Unsupported reminder hour.")

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO user_settings (user_id, reminder_hour, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                reminder_hour = excluded.reminder_hour,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, reminder_hour),
        )


def set_user_timezone(database_path: str, user_id: int, timezone: str) -> None:
    if timezone not in TIMEZONE_OPTIONS.values():
        raise ValueError("Unsupported timezone.")

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO user_settings (user_id, timezone, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                timezone = excluded.timezone,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, timezone),
        )


def mark_reminder_sent(
    database_path: str,
    item_id: int,
    user_id: int,
    offset_days: int,
    reminder_date: str,
) -> None:
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT OR IGNORE INTO sent_reminders (
                item_id,
                user_id,
                offset_days,
                reminder_date
            )
            VALUES (?, ?, ?, ?)
            """,
            (item_id, user_id, offset_days, reminder_date),
        )


def _connect(database_path: str) -> sqlite3.Connection:
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def _ensure_column(
    connection: sqlite3.Connection,
    table_name: str,
    column_name: str,
    definition: str,
) -> None:
    columns = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    existing_columns = {column[1] for column in columns}

    if column_name not in existing_columns:
        connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {definition}")


def _is_reminder_sent(
    connection: sqlite3.Connection,
    item_id: int,
    offset_days: int,
    reminder_date: str,
) -> bool:
    row = connection.execute(
        """
        SELECT 1
        FROM sent_reminders
        WHERE item_id = ?
          AND offset_days = ?
          AND reminder_date = ?
        LIMIT 1
        """,
        (item_id, offset_days, reminder_date),
    ).fetchone()

    return row is not None


def _serialize_reminder_offsets(reminder_offsets: tuple[int, ...]) -> str:
    return ",".join(str(offset) for offset in reminder_offsets)


def _parse_reminder_offsets(value: str) -> tuple[int, ...]:
    if not value:
        return tuple()

    return tuple(int(offset) for offset in value.split(","))


def _localize_time(current_time: datetime, timezone: str) -> datetime:
    try:
        zone = ZoneInfo(timezone)
    except ZoneInfoNotFoundError:
        zone = ZoneInfo(DEFAULT_TIMEZONE)

    return current_time.astimezone(zone)


def _row_to_item(row: sqlite3.Row) -> ExpiryItem:
    return ExpiryItem(
        id=row["id"],
        user_id=row["user_id"],
        title=row["title"],
        category=row["category"],
        expires_on=row["expires_on"],
        date_precision=row["date_precision"],
        note=row["note"],
        reminder_offsets=_parse_reminder_offsets(row["reminder_offsets"]),
    )
