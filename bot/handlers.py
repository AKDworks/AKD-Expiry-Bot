from calendar import monthrange
from datetime import date, datetime

from aiogram import F, Router
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from bot.database import (
    add_item,
    delete_item,
    get_item,
    get_user_reminder_hour,
    list_items,
    set_user_reminder_hour,
    update_item,
)
from bot.keyboards import (
    ADD_ITEM_TEXT,
    ABOUT_BOT_TEXT,
    CANCEL_TEXT,
    CATEGORIES,
    DONE_TEXT,
    MY_ITEMS_TEXT,
    REMINDER_OPTIONS,
    REMINDER_TIME_OPTIONS,
    SETTINGS_TEXT,
    SKIP_TEXT,
    cancel_keyboard,
    category_keyboard,
    confirm_delete_keyboard,
    edit_item_keyboard,
    item_actions_keyboard,
    items_keyboard,
    main_menu_keyboard,
    reminder_time_keyboard,
    reminders_keyboard,
    skip_note_keyboard,
)
from bot.texts import START_TEXT
from bot import texts

router = Router()


class AddItemStates(StatesGroup):
    title = State()
    category = State()
    expires_on = State()
    note = State()
    reminders = State()


class EditItemStates(StatesGroup):
    title = State()
    category = State()
    expires_on = State()
    note = State()
    reminders = State()


@router.message(CommandStart())
async def start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        START_TEXT,
        reply_markup=main_menu_keyboard(),
    )


@router.message(F.text.casefold().in_({"start", "старт"}))
async def start_text_alias(message: Message, state: FSMContext) -> None:
    await start(message, state)


@router.message(Command("cancel"))
@router.message(StateFilter("*"), F.text.casefold() == CANCEL_TEXT.casefold())
async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        texts.CANCELLED_TEXT,
        reply_markup=main_menu_keyboard(),
    )


@router.message(F.text == ADD_ITEM_TEXT)
async def add_entry_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(AddItemStates.title)
    await message.answer(
        texts.ASK_TITLE_TEXT,
        reply_markup=cancel_keyboard(),
    )


@router.message(AddItemStates.title)
async def add_entry_title(message: Message, state: FSMContext) -> None:
    title = _clean_text(message.text)

    if not title:
        await message.answer(texts.TITLE_REQUIRED_TEXT)
        return

    if len(title) > 80:
        await message.answer(texts.TITLE_TOO_LONG_TEXT)
        return

    await state.update_data(title=title)
    await state.set_state(AddItemStates.category)
    await message.answer(
        texts.ASK_CATEGORY_TEXT,
        reply_markup=category_keyboard(),
    )


@router.message(AddItemStates.category)
async def add_entry_category(message: Message, state: FSMContext) -> None:
    category = _clean_text(message.text)

    if category not in CATEGORIES:
        await message.answer(texts.CATEGORY_REQUIRED_TEXT)
        return

    await state.update_data(category=category)
    await state.set_state(AddItemStates.expires_on)
    await message.answer(
        texts.ASK_DATE_TEXT,
        reply_markup=cancel_keyboard(),
    )


@router.message(AddItemStates.expires_on)
async def add_entry_expires_on(message: Message, state: FSMContext) -> None:
    parsed_date = _parse_date(_clean_text(message.text))

    if parsed_date is None:
        await message.answer(texts.DATE_INVALID_TEXT)
        return

    expires_on, date_precision = parsed_date

    if expires_on < date.today():
        await message.answer(texts.DATE_PAST_TEXT)
        return

    await state.update_data(
        expires_on=expires_on.isoformat(),
        date_precision=date_precision,
    )
    await state.set_state(AddItemStates.note)
    await message.answer(
        texts.ASK_NOTE_TEXT,
        reply_markup=skip_note_keyboard(),
    )


@router.message(AddItemStates.note)
async def add_entry_note(message: Message, state: FSMContext) -> None:
    note = _clean_text(message.text)

    if note == SKIP_TEXT:
        note = None
    elif not note:
        await message.answer(texts.NOTE_REQUIRED_TEXT)
        return
    elif len(note) > 300:
        await message.answer(texts.NOTE_TOO_LONG_TEXT)
        return

    await state.update_data(note=note, reminder_offsets=[])
    await state.set_state(AddItemStates.reminders)
    await message.answer(
        texts.ASK_REMINDERS_TEXT,
        reply_markup=reminders_keyboard(),
    )


@router.message(AddItemStates.reminders)
async def add_entry_reminders(
    message: Message,
    state: FSMContext,
    database_path: str,
) -> None:
    text = _clean_text(message.text)
    data = await state.get_data()
    selected_offsets = list(data.get("reminder_offsets", []))

    if text == DONE_TEXT:
        if not selected_offsets:
            await message.answer(texts.REMINDER_REQUIRED_TEXT)
            return

        item_id = add_item(
            database_path=database_path,
            user_id=message.from_user.id,
            title=data["title"],
            category=data["category"],
            expires_on=data["expires_on"],
            reminder_offsets=tuple(sorted(selected_offsets, reverse=True)),
            date_precision=data["date_precision"],
            note=data["note"],
        )
        await state.clear()
        await message.answer(
            texts.item_created_text(
                item_id=item_id,
                title=data["title"],
                category=data["category"],
                expires_on=data["expires_on"],
                date_precision=data["date_precision"],
                note=data["note"],
                selected_offsets=selected_offsets,
            ),
            reply_markup=main_menu_keyboard(),
        )
        return

    if text not in REMINDER_OPTIONS:
        await message.answer(texts.REMINDER_UNKNOWN_TEXT)
        return

    offset = REMINDER_OPTIONS[text]
    if offset in selected_offsets:
        selected_offsets.remove(offset)
        action_text = "Убрано"
    else:
        selected_offsets.append(offset)
        action_text = "Добавлено"

    await state.update_data(reminder_offsets=selected_offsets)
    await message.answer(
        f"{action_text}: {text}\n"
        f"Сейчас выбрано: {texts.format_reminders(selected_offsets)}",
        reply_markup=reminders_keyboard(),
    )


@router.message(F.text == MY_ITEMS_TEXT)
async def list_entries(message: Message, database_path: str) -> None:
    items = list_items(database_path, message.from_user.id)

    if not items:
        await message.answer(texts.NO_ITEMS_TEXT)
        return

    await message.answer(
        texts.ITEMS_LIST_TEXT,
        reply_markup=items_keyboard(items),
    )


@router.message(F.text == SETTINGS_TEXT)
async def settings(message: Message, database_path: str) -> None:
    reminder_hour = get_user_reminder_hour(database_path, message.from_user.id)
    await message.answer(
        texts.settings_text(reminder_hour),
        reply_markup=reminder_time_keyboard(reminder_hour),
    )


@router.message(F.text == ABOUT_BOT_TEXT)
async def about_bot(message: Message, project_github_url: str) -> None:
    await message.answer(
        texts.about_bot_text(project_github_url),
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )


@router.callback_query(F.data.startswith("settings:reminder_hour:"))
async def change_reminder_hour(callback: CallbackQuery, database_path: str) -> None:
    reminder_hour = _parse_callback_reminder_hour(callback.data)

    if reminder_hour is None or callback.message is None:
        await callback.answer(texts.SETTINGS_OPEN_FAILED_TEXT)
        return

    set_user_reminder_hour(
        database_path=database_path,
        user_id=callback.from_user.id,
        reminder_hour=reminder_hour,
    )

    await callback.message.edit_text(
        texts.settings_text(reminder_hour),
        reply_markup=reminder_time_keyboard(reminder_hour),
    )
    await callback.answer(texts.reminder_time_updated_text(reminder_hour))


@router.callback_query(F.data == "item:list")
async def list_entries_callback(callback: CallbackQuery, database_path: str) -> None:
    items = list_items(database_path, callback.from_user.id)

    if callback.message is None:
        await callback.answer()
        return

    if not items:
        await callback.message.edit_text(texts.NO_ITEMS_TEXT)
        await callback.answer()
        return

    await callback.message.edit_text(
        texts.ITEMS_LIST_TEXT,
        reply_markup=items_keyboard(items),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("item:view:"))
async def view_entry(callback: CallbackQuery, database_path: str) -> None:
    item_id = _parse_callback_item_id(callback.data)

    if item_id is None or callback.message is None:
        await callback.answer(texts.ITEM_OPEN_FAILED_TEXT)
        return

    item = get_item(database_path, callback.from_user.id, item_id)
    if item is None:
        await callback.answer(texts.ITEM_NOT_FOUND_TEXT)
        return

    await callback.message.edit_text(
        texts.item_details_text(item),
        reply_markup=item_actions_keyboard(item.id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("item:edit:"))
async def edit_entry_menu(callback: CallbackQuery, database_path: str) -> None:
    item_id = _parse_callback_item_id(callback.data)

    if item_id is None or callback.message is None:
        await callback.answer(texts.ITEM_OPEN_FAILED_TEXT)
        return

    item = get_item(database_path, callback.from_user.id, item_id)
    if item is None:
        await callback.answer(texts.ITEM_NOT_FOUND_TEXT)
        return

    await callback.message.edit_text(
        texts.EDIT_MENU_TEXT,
        reply_markup=edit_item_keyboard(item.id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("item:edit_title:"))
async def edit_entry_title_start(callback: CallbackQuery, state: FSMContext) -> None:
    item_id = _parse_callback_item_id(callback.data)

    if item_id is None or callback.message is None:
        await callback.answer(texts.ITEM_OPEN_FAILED_TEXT)
        return

    await state.clear()
    await state.update_data(item_id=item_id)
    await state.set_state(EditItemStates.title)
    await callback.message.answer(
        texts.EDIT_TITLE_TEXT,
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.message(EditItemStates.title)
async def edit_entry_title(
    message: Message,
    state: FSMContext,
    database_path: str,
) -> None:
    title = _clean_text(message.text)

    if not title:
        await message.answer(texts.TITLE_REQUIRED_TEXT)
        return

    if len(title) > 80:
        await message.answer(texts.TITLE_TOO_LONG_TEXT)
        return

    data = await state.get_data()
    item_id = data["item_id"]
    updated = update_item(
        database_path=database_path,
        user_id=message.from_user.id,
        item_id=item_id,
        title=title,
    )
    await _finish_edit(message, state, database_path, item_id, updated)


@router.callback_query(F.data.startswith("item:edit_category:"))
async def edit_entry_category_start(callback: CallbackQuery, state: FSMContext) -> None:
    item_id = _parse_callback_item_id(callback.data)

    if item_id is None or callback.message is None:
        await callback.answer(texts.ITEM_OPEN_FAILED_TEXT)
        return

    await state.clear()
    await state.update_data(item_id=item_id)
    await state.set_state(EditItemStates.category)
    await callback.message.answer(
        texts.EDIT_CATEGORY_TEXT,
        reply_markup=category_keyboard(),
    )
    await callback.answer()


@router.message(EditItemStates.category)
async def edit_entry_category(
    message: Message,
    state: FSMContext,
    database_path: str,
) -> None:
    category = _clean_text(message.text)

    if category not in CATEGORIES:
        await message.answer(texts.CATEGORY_REQUIRED_TEXT)
        return

    data = await state.get_data()
    item_id = data["item_id"]
    updated = update_item(
        database_path=database_path,
        user_id=message.from_user.id,
        item_id=item_id,
        category=category,
    )
    await _finish_edit(message, state, database_path, item_id, updated)


@router.callback_query(F.data.startswith("item:edit_date:"))
async def edit_entry_date_start(callback: CallbackQuery, state: FSMContext) -> None:
    item_id = _parse_callback_item_id(callback.data)

    if item_id is None or callback.message is None:
        await callback.answer(texts.ITEM_OPEN_FAILED_TEXT)
        return

    await state.clear()
    await state.update_data(item_id=item_id)
    await state.set_state(EditItemStates.expires_on)
    await callback.message.answer(
        texts.EDIT_DATE_TEXT,
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.message(EditItemStates.expires_on)
async def edit_entry_date(
    message: Message,
    state: FSMContext,
    database_path: str,
) -> None:
    parsed_date = _parse_date(_clean_text(message.text))

    if parsed_date is None:
        await message.answer(texts.DATE_INVALID_TEXT)
        return

    expires_on, date_precision = parsed_date

    if expires_on < date.today():
        await message.answer(texts.DATE_PAST_TEXT)
        return

    data = await state.get_data()
    item_id = data["item_id"]
    updated = update_item(
        database_path=database_path,
        user_id=message.from_user.id,
        item_id=item_id,
        expires_on=expires_on.isoformat(),
        date_precision=date_precision,
    )
    await _finish_edit(message, state, database_path, item_id, updated)


@router.callback_query(F.data.startswith("item:edit_note:"))
async def edit_entry_note_start(callback: CallbackQuery, state: FSMContext) -> None:
    item_id = _parse_callback_item_id(callback.data)

    if item_id is None or callback.message is None:
        await callback.answer(texts.ITEM_OPEN_FAILED_TEXT)
        return

    await state.clear()
    await state.update_data(item_id=item_id)
    await state.set_state(EditItemStates.note)
    await callback.message.answer(
        texts.EDIT_NOTE_TEXT,
        reply_markup=skip_note_keyboard(),
    )
    await callback.answer()


@router.message(EditItemStates.note)
async def edit_entry_note(
    message: Message,
    state: FSMContext,
    database_path: str,
) -> None:
    note = _clean_text(message.text)

    if note == SKIP_TEXT:
        note = None
    elif not note:
        await message.answer(texts.NOTE_REQUIRED_TEXT)
        return
    elif len(note) > 300:
        await message.answer(texts.NOTE_TOO_LONG_TEXT)
        return

    data = await state.get_data()
    item_id = data["item_id"]
    updated = update_item(
        database_path=database_path,
        user_id=message.from_user.id,
        item_id=item_id,
        note=note,
    )
    await _finish_edit(message, state, database_path, item_id, updated)


@router.callback_query(F.data.startswith("item:edit_reminders:"))
async def edit_entry_reminders_start(
    callback: CallbackQuery,
    state: FSMContext,
    database_path: str,
) -> None:
    item_id = _parse_callback_item_id(callback.data)

    if item_id is None or callback.message is None:
        await callback.answer(texts.ITEM_OPEN_FAILED_TEXT)
        return

    item = get_item(database_path, callback.from_user.id, item_id)
    if item is None:
        await callback.answer(texts.ITEM_NOT_FOUND_TEXT)
        return

    await state.clear()
    await state.update_data(
        item_id=item_id,
        reminder_offsets=list(item.reminder_offsets),
    )
    await state.set_state(EditItemStates.reminders)
    await callback.message.answer(
        texts.EDIT_REMINDERS_TEXT,
        reply_markup=reminders_keyboard(),
    )
    await callback.answer()


@router.message(EditItemStates.reminders)
async def edit_entry_reminders(
    message: Message,
    state: FSMContext,
    database_path: str,
) -> None:
    text = _clean_text(message.text)
    data = await state.get_data()
    item_id = data["item_id"]
    selected_offsets = list(data.get("reminder_offsets", []))

    if text == DONE_TEXT:
        if not selected_offsets:
            await message.answer(texts.REMINDER_REQUIRED_TEXT)
            return

        updated = update_item(
            database_path=database_path,
            user_id=message.from_user.id,
            item_id=item_id,
            reminder_offsets=tuple(sorted(selected_offsets, reverse=True)),
        )
        await _finish_edit(message, state, database_path, item_id, updated)
        return

    if text not in REMINDER_OPTIONS:
        await message.answer(texts.REMINDER_UNKNOWN_TEXT)
        return

    offset = REMINDER_OPTIONS[text]
    if offset in selected_offsets:
        selected_offsets.remove(offset)
        action_text = "Убрано"
    else:
        selected_offsets.append(offset)
        action_text = "Добавлено"

    await state.update_data(reminder_offsets=selected_offsets)
    await message.answer(
        f"{action_text}: {text}\n"
        f"Сейчас выбрано: {texts.format_reminders(selected_offsets)}",
        reply_markup=reminders_keyboard(),
    )


@router.callback_query(F.data.startswith("item:delete:"))
async def ask_delete_entry(callback: CallbackQuery, database_path: str) -> None:
    item_id = _parse_callback_item_id(callback.data)

    if item_id is None or callback.message is None:
        await callback.answer(texts.ITEM_DELETE_OPEN_FAILED_TEXT)
        return

    item = get_item(database_path, callback.from_user.id, item_id)
    if item is None:
        await callback.answer(texts.ITEM_NOT_FOUND_TEXT)
        return

    await callback.message.edit_text(
        texts.delete_confirmation_text(item),
        reply_markup=confirm_delete_keyboard(item.id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("item:delete_confirm:"))
async def delete_entry(callback: CallbackQuery, database_path: str) -> None:
    item_id = _parse_callback_item_id(callback.data)

    if item_id is None or callback.message is None:
        await callback.answer(texts.ITEM_DELETE_FAILED_TEXT)
        return

    deleted = delete_item(database_path, callback.from_user.id, item_id)
    if not deleted:
        await callback.answer(texts.ITEM_NOT_FOUND_TEXT)
        return

    items = list_items(database_path, callback.from_user.id)
    if not items:
        await callback.message.edit_text(texts.item_deleted_empty_text())
        await callback.answer()
        return

    await callback.message.edit_text(
        texts.item_deleted_list_text(),
        reply_markup=items_keyboard(items),
    )
    await callback.answer()


@router.message()
async def unknown_message(message: Message) -> None:
    await message.answer(
        texts.UNKNOWN_MESSAGE_TEXT,
        reply_markup=main_menu_keyboard(),
    )


def _clean_text(value: str | None) -> str:
    if value is None:
        return ""

    return value.strip()


def _parse_date(value: str) -> tuple[date, str] | None:
    try:
        return datetime.strptime(value, "%d.%m.%Y").date(), "day"
    except ValueError:
        pass

    try:
        month_date = datetime.strptime(value, "%m.%Y").date()
    except ValueError:
        return None

    last_day = monthrange(month_date.year, month_date.month)[1]
    return date(month_date.year, month_date.month, last_day), "month"


async def _finish_edit(
    message: Message,
    state: FSMContext,
    database_path: str,
    item_id: int,
    updated: bool,
) -> None:
    await state.clear()

    if not updated:
        await message.answer(
            texts.ITEM_NOT_FOUND_TEXT,
            reply_markup=main_menu_keyboard(),
        )
        return

    item = get_item(database_path, message.from_user.id, item_id)
    if item is None:
        await message.answer(
            texts.ITEM_NOT_FOUND_TEXT,
            reply_markup=main_menu_keyboard(),
        )
        return

    await message.answer(
        texts.ITEM_UPDATED_TEXT,
        reply_markup=main_menu_keyboard(),
    )
    await message.answer(
        texts.item_details_text(item),
        reply_markup=item_actions_keyboard(item.id),
    )


def _parse_callback_item_id(callback_data: str | None) -> int | None:
    if callback_data is None:
        return None

    try:
        return int(callback_data.rsplit(":", maxsplit=1)[1])
    except (IndexError, ValueError):
        return None


def _parse_callback_reminder_hour(callback_data: str | None) -> int | None:
    if callback_data is None:
        return None

    try:
        reminder_hour = int(callback_data.rsplit(":", maxsplit=1)[1])
    except (IndexError, ValueError):
        return None

    if reminder_hour not in REMINDER_TIME_OPTIONS.values():
        return None

    return reminder_hour
