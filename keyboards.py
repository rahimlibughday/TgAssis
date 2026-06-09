from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

def get_check_admin_keyboard() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.button(text="Готово ✅", callback_data="check_admin_rights")
    return builder.as_markup()

def get_topic_keyboard() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.button(text="Оставить выбор на ИИ 💡", callback_data="topic_ai_choose")
    return builder.as_markup()

def start_make_content_plan_keyboard() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.button(text="Создание контент плана 🚀", callback_data="start_content_plan")
    return builder.as_markup()

def start_work_on_channel_keyboard() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.button(text="Начать работу над каналом 🎬", callback_data="start_work_on_channel")
    return builder.as_markup()

def main_menu_keyboard() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.button(text="Статистика канала 📊", callback_data="channel_stats")
    return builder.as_markup()