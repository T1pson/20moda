
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Кнопки при поиске профиля через админ-меню
open_profile_inl = InlineKeyboardMarkup()
inn = InlineKeyboardButton(text = '💵 Пополнить BTC',callback_data="user_btc")
input_kb = InlineKeyboardButton(text="💵 Пополнить", callback_data="user_input")
mybuy_kb = InlineKeyboardButton(text="🛒 Мои покупки", callback_data="my_buy")
open_profile_inl.add(input_kb,inn)
open_profile_inl.add(mybuy_kb)

# Кнопка с возвратом к профилю
to_profile_inl = InlineKeyboardMarkup()
to_profile_inl.add(InlineKeyboardButton(text="📱 Профиль", callback_data="user_profile"))

# Кнопка канала
start_inn = InlineKeyboardMarkup()
start_inn.add(InlineKeyboardButton(text="📘 Группа с новостями!", url="instagram.com/shop20moda21.ua"))
