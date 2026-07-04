from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from bot.database import ExpiryItem


CANCEL_TEXT = "Отмена"
ADD_ITEM_TEXT = "Добавить запись"
MY_ITEMS_TEXT = "Мои записи"
ABOUT_BOT_TEXT = "О боте"
DONE_TEXT = "Готово"
SKIP_TEXT = "Пропустить"

CATEGORIES = (
    "Документы",
    "Авто",
    "Финансы",
    "Сайт и домен",
    "Работа",
    "Другое",
)

REMINDER_OPTIONS = {
    "За 30 дней": 30,
    "За 7 дней": 7,
    "За 1 день": 1,
    "В день окончания": 0,
}


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=ADD_ITEM_TEXT)],
            [KeyboardButton(text=MY_ITEMS_TEXT)],
            [KeyboardButton(text=ABOUT_BOT_TEXT)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
    )


def cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=CANCEL_TEXT)]],
        resize_keyboard=True,
    )


def skip_note_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=SKIP_TEXT)],
            [KeyboardButton(text=CANCEL_TEXT)],
        ],
        resize_keyboard=True,
    )


def category_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=category)]
            for category in CATEGORIES
        ]
        + [[KeyboardButton(text=CANCEL_TEXT)]],
        resize_keyboard=True,
        input_field_placeholder="Выберите категорию",
    )


def reminders_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="За 30 дней"), KeyboardButton(text="За 7 дней")],
            [KeyboardButton(text="За 1 день"), KeyboardButton(text="В день окончания")],
            [KeyboardButton(text=DONE_TEXT), KeyboardButton(text=CANCEL_TEXT)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите напоминания",
    )


def remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


def items_keyboard(items: list[ExpiryItem]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{item.title} — {item.category}",
                    callback_data=f"item:view:{item.id}",
                )
            ]
            for item in items
        ]
    )


def item_actions_keyboard(item_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Редактировать",
                    callback_data=f"item:edit:{item_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Удалить",
                    callback_data=f"item:delete:{item_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Назад к списку",
                    callback_data="item:list",
                )
            ],
        ]
    )


def edit_item_keyboard(item_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Название",
                    callback_data=f"item:edit_title:{item_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Категория",
                    callback_data=f"item:edit_category:{item_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Дата",
                    callback_data=f"item:edit_date:{item_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Заметка",
                    callback_data=f"item:edit_note:{item_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Напоминания",
                    callback_data=f"item:edit_reminders:{item_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Назад",
                    callback_data=f"item:view:{item_id}",
                )
            ],
        ]
    )


def confirm_delete_keyboard(item_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Да, удалить",
                    callback_data=f"item:delete_confirm:{item_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Отмена",
                    callback_data=f"item:view:{item_id}",
                )
            ],
        ]
    )
