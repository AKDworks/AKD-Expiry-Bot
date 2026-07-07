from bot.database import DueReminder, ExpiryItem, TIMEZONE_OPTIONS
from bot.keyboards import REMINDER_OPTIONS


START_TEXT = (
    "AKD Expiry помогает заранее помнить о сроках.\n\n"
    "Можно отслеживать документы, страховки, домены, лицензии, договоры "
    "и другие важные даты.\n\n"
    "Не отправляйте номера документов, персональные идентификаторы, адреса и другие чувствительные данные. "
    "Достаточно названия, категории и даты окончания."
)

CANCELLED_TEXT = "Действие отменено."
TITLE_REQUIRED_TEXT = "Введите название текстом."
TITLE_TOO_LONG_TEXT = "Слишком длинно. Лучше до 80 символов."
CATEGORY_REQUIRED_TEXT = "Выберите категорию кнопкой."
DATE_INVALID_TEXT = "Не понял дату. Введите в формате ДД.ММ.ГГГГ или ММ.ГГГГ."
DATE_PAST_TEXT = "Дата уже прошла. Введите будущую дату или сегодняшнюю."
NOTE_REQUIRED_TEXT = "Введите заметку текстом или нажмите «Пропустить»."
NOTE_TOO_LONG_TEXT = "Слишком длинно. Лучше до 300 символов."
REMINDER_REQUIRED_TEXT = "Выберите хотя бы одно напоминание."
REMINDER_UNKNOWN_TEXT = "Выберите вариант кнопкой или нажмите «Готово»."
NO_ITEMS_TEXT = "Записей пока нет."
ITEMS_LIST_TEXT = "Ваши записи:"
ITEM_NOT_FOUND_TEXT = "Запись не найдена."
ITEM_OPEN_FAILED_TEXT = "Не получилось открыть запись."
ITEM_DELETE_OPEN_FAILED_TEXT = "Не получилось открыть удаление."
ITEM_DELETE_FAILED_TEXT = "Не получилось удалить запись."
ITEM_DELETED_TEXT = "Запись удалена."
UNKNOWN_MESSAGE_TEXT = "Я пока понимаю /start и кнопки меню."
ITEM_UPDATED_TEXT = "Запись обновлена."
SETTINGS_OPEN_FAILED_TEXT = "Не получилось открыть настройки."
EDIT_MENU_TEXT = "Что изменить?"
EDIT_TITLE_TEXT = "Введите новое название записи."
EDIT_CATEGORY_TEXT = "Выберите новую категорию."
EDIT_DATE_TEXT = (
    "Введите новую дату окончания.\n\n"
    "Точная дата: 31.12.2026\n"
    "Или месяц и год: 12.2026"
)
EDIT_NOTE_TEXT = "Введите новую заметку или нажмите «Пропустить», чтобы очистить её."
EDIT_REMINDERS_TEXT = (
    "Выберите новые напоминания.\n\n"
    "Можно выбрать несколько вариантов, затем нажать «Готово»."
)

ASK_TITLE_TEXT = (
    "Введите название записи.\n\n"
    "Например: паспорт, страховка, домен, SSL-сертификат.\n"
    "Не указывайте номера документов и другие чувствительные данные."
)

ASK_CATEGORY_TEXT = "Выберите категорию."

ASK_DATE_TEXT = (
    "Введите дату окончания.\n\n"
    "Можно указать точную дату: 31.12.2026\n"
    "Или только месяц и год: 12.2026"
)

ASK_NOTE_TEXT = (
    "Добавьте заметку, если нужно.\n\n"
    "Например: проверить продление в личном кабинете.\n"
    "Не пишите номера документов, персональные идентификаторы, адреса и другие чувствительные данные."
)

ASK_REMINDERS_TEXT = (
    "Когда напомнить?\n\n"
    "Можно выбрать несколько вариантов, затем нажать «Готово»."
)

SETTINGS_TEXT = (
    "Настройки\n\n"
    "Здесь можно выбрать время ежедневной проверки напоминаний и часовой пояс."
)
REMINDER_TIME_SETTINGS_TEXT = "Выберите время напоминаний."
TIMEZONE_SETTINGS_TEXT = "Выберите часовой пояс."


def settings_text(reminder_hour: int, timezone: str) -> str:
    return (
        f"{SETTINGS_TEXT}\n\n"
        f"Время: {format_reminder_time(reminder_hour)}\n"
        f"Часовой пояс: {format_timezone(timezone)}"
    )


def reminder_time_updated_text(reminder_hour: int) -> str:
    return f"Время напоминаний изменено: {format_reminder_time(reminder_hour)}"


def timezone_updated_text(timezone: str) -> str:
    return f"Часовой пояс изменён: {format_timezone(timezone)}"


def about_bot_text(project_github_url: str) -> str:
    github_url = project_github_url or "https://github.com/AKDworks"

    return (
        "О боте\n\n"
        "AKD Expiry создан, чтобы спокойно отслеживать сроки действия документов, "
        "услуг и обязательств.\n\n"
        "Он хранит только данные, нужные для напоминаний: название записи, "
        "категорию, дату окончания, заметку по желанию и настройки напоминаний.\n\n"
        "Не отправляйте в бот номера документов, персональные идентификаторы, полный адрес, данные карт "
        "и другую чувствительную информацию.\n\n"
        f'Автор проекта: <a href="{github_url}">AKDworks</a>.'
    )


def item_created_text(
    item_id: int,
    title: str,
    category: str,
    expires_on: str,
    date_precision: str,
    note: str | None,
    selected_offsets: list[int],
) -> str:
    return (
        "Запись добавлена.\n\n"
        f"ID: {item_id}\n"
        f"Название: {title}\n"
        f"Категория: {category}\n"
        f"Дата окончания: {format_date(expires_on, date_precision)}\n"
        f"Заметка: {format_note(note)}\n"
        f"Напоминания: {format_reminders(selected_offsets)}"
    )


def item_details_text(item: ExpiryItem) -> str:
    return "\n".join(
        [
            item.title,
            "",
            f"Категория: {item.category}",
            f"Дата окончания: {format_date(item.expires_on, item.date_precision)}",
            f"Заметка: {format_note(item.note)}",
            f"Напоминания: {format_reminders(item.reminder_offsets)}",
        ]
    )


def delete_confirmation_text(item: ExpiryItem) -> str:
    return (
        "Удалить запись?\n\n"
        f"{item.title}\n"
        f"{item.category}, до {format_date(item.expires_on, item.date_precision)}"
    )


def item_deleted_empty_text() -> str:
    return f"{ITEM_DELETED_TEXT}\n\n{NO_ITEMS_TEXT}"


def item_deleted_list_text() -> str:
    return f"{ITEM_DELETED_TEXT}\n\n{ITEMS_LIST_TEXT}"


def format_reminder_text(reminder: DueReminder) -> str:
    item = reminder.item
    lines = [
        "Напоминание",
        "",
        item.title,
        f"Категория: {item.category}",
        f"Истекает: {format_date(item.expires_on, item.date_precision)}",
        f"Срок: {_format_reminder_offset(reminder.offset_days)}",
    ]

    if item.note:
        lines.append(f"Заметка: {item.note}")

    return "\n".join(lines)


def format_date(value: str, precision: str = "day") -> str:
    from datetime import datetime

    parsed = datetime.strptime(value, "%Y-%m-%d")

    if precision == "month":
        return parsed.strftime("%m.%Y")

    return parsed.strftime("%d.%m.%Y")


def format_note(note: str | None) -> str:
    return note if note else "нет"


def format_reminders(offsets: list[int] | tuple[int, ...]) -> str:
    if not offsets:
        return "не выбрано"

    labels_by_offset = {
        offset: label
        for label, offset in REMINDER_OPTIONS.items()
    }

    return ", ".join(
        labels_by_offset[offset]
        for offset in sorted(offsets, reverse=True)
    )


def format_reminder_time(reminder_hour: int) -> str:
    return f"{reminder_hour:02d}:00"


def format_timezone(timezone: str) -> str:
    labels_by_timezone = {
        value: label
        for label, value in TIMEZONE_OPTIONS.items()
    }

    return labels_by_timezone.get(timezone, timezone)


def _format_reminder_offset(offset_days: int) -> str:
    if offset_days == 0:
        return "сегодня"

    return f"через {offset_days} {_plural_days(offset_days)}"


def _plural_days(value: int) -> str:
    if 11 <= value % 100 <= 14:
        return "дней"

    if value % 10 == 1:
        return "день"

    if 2 <= value % 10 <= 4:
        return "дня"

    return "дней"
