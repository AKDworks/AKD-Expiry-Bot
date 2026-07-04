from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
import sqlite3

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
    reminder_date: date | None = None,
) -> list[DueReminder]:
    target_date = reminder_date or date.today()
    due_reminders: list[DueReminder] = []

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
            WHERE expires_on >= ?
            ORDER BY expires_on ASC, id ASC
            """,
            (target_date.isoformat(),),
        ).fetchall()

        for row in rows:
            item = _row_to_item(row)
            expires_on = date.fromisoformat(item.expires_on)

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
