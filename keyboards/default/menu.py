from aiogram.types import ReplyKeyboardMarkup

from data.config import admins


def check_user_out_func(user_id):
    menu_default = ReplyKeyboardMarkup(resize_keyboard=True)
    menu_default.row("🛍 Товары", "👮🏻‍♀️ Профиль")
    menu_default.row("☎️ Поддержка", "📕 Правила")
    menu_default.row("🎁 Реферальная система")
    if str(user_id) in admins:
        menu_default.row("🎁 Управление товарами 🖍", "📰 Информация о боте")
        menu_default.row("⚙ Настройки", "🔆 Общие функции", "🔑 Платежные системы")
    return menu_default

all_back_to_main_default = ReplyKeyboardMarkup(resize_keyboard=True)
all_back_to_main_default.row("⬅ На главную")
