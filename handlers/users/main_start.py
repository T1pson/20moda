from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.builtin import CommandStart

from keyboards.inline import *
from filters import IsWork, IsUser
from filters.all_filters import IsBuy
from keyboards.default import check_user_out_func
from loader import dp, bot
from states import StorageUsers
from utils.db_api.sqlite import *
from utils.other_func import clear_firstname, get_dates
from data.config import admin_for_logs
prohibit_buy = ["xbuy_item", "not_buy_items", "buy_this_item", "buy_open_position", "back_buy_item_position",
                "buy_position_prevp", "buy_position_nextp", "buy_category_prevp", "buy_category_nextp",
                "back_buy_item_to_category", "buy_open_category"]

# Проверка на нахождение бота на технических работах
@dp.message_handler(IsWork(), state="*")
@dp.callback_query_handler(IsWork(), state="*")
async def send_work_message(message: types.Message, state: FSMContext):
    if "id" in message:
        await message.answer("🔴 Бот находится на технических работах.")
    else:
        await message.answer("<b>🔴 Бот находится на технических работах.</b>")


# Обработка кнопки "На главную" и команды "/start"
@dp.message_handler(text="⬅ На главную", state="*")
@dp.message_handler(CommandStart(), state="*")
async def bot_start(message: types.Message, state: FSMContext):
    arg = message.get_args()
    await state.finish()
    first_name = clear_firstname(message.from_user.first_name)
    get_user_id = get_userx(user_id=message.from_user.id)
    if get_user_id is None:
            if message.from_user.username is not None:
             await bot.send_message(admin_for_logs,text = f'<b>🔔 Новый пользователь!\n\n👤 Username: <a href="tg://user?id={message.from_user.id}">{first_name}</a>\n'
                                          f'🆔 Telegram ID: {message.from_user.id}</b>')#Лог_о_новом_пользователе
    if get_user_id is None:
        if arg != "":
            aa = 0
            if message.from_user.username is not None:
             await bot.send_message(arg, text = f'<b><i>✅ У вас новый реферал! <a href="tg://user?id={message.from_user.id}">{first_name}</a>\nТеперь вы будете получать 2% с его пополнений!</i></b>')
            get_user_login = get_userx(user_login=message.from_user.username)#Лог_о_новом_реферале
            if get_user_login is None:
                add_userxref(message.from_user.id, message.from_user.username.lower(), first_name, 0, 0, get_dates(),aa,arg)
                conn = sqlite3.connect("data/botBD.sqlite")
                cursor = conn.cursor()
                cursor.execute(f"UPDATE storage_users SET refkol = refkol+1 WHERE user_id = {arg}")
                conn.commit()
            else:
                delete_userx(user_login=message.from_user.username)
                add_userxref(message.from_user.id, message.from_user.username.lower(), first_name, 0, 0, get_dates(),aa,arg)
                conn = sqlite3.connect("data/botBD.sqlite")
                cursor = conn.cursor()
                cursor.execute(f"UPDATE storage_users SET refkol = refkol+1 WHERE user_id = {arg}")
                conn.commit()
            if message.from_user.username is not None:
                add_userx(message.from_user.id, message.from_user.username.lower(), first_name, 0, 0, get_dates())
            else:
                delete_userx(user_login=message.from_user.username)
                add_userx(message.from_user.id, message.from_user.username.lower(), first_name, 0, 0, get_dates())
        else:
            add_userx(message.from_user.id, message.from_user.username, first_name, 0, 0, get_dates())
    else:
        if first_name != get_user_id[3]:
            update_userx(get_user_id[1], user_name=first_name)
        if message.from_user.username is not None:
            if message.from_user.username.lower() != get_user_id[2]:
                update_userx(get_user_id[1], user_login=message.from_user.username.lower())
    with open("main_menu.jpg", "rb") as file:#Тут_вставить_название_картинки_для_приветствия
        data = file.read()
    await message.answer_photo(photo=data, caption=f'<b>👋🏻 Приветик, <code>{message.from_user.first_name}</code>!\n\n'
                                                   f'💙Добро пожаловать в самый лучший и отзывчивый магазин по продаже топовых вещей.</b>\n\n',reply_markup=check_user_out_func(message.from_user.id))

# Если профиля нету в бд
@dp.message_handler(IsUser(), state="*")
@dp.callback_query_handler(IsUser(), state="*")
async def send_user_message(message: types.Message, state: FSMContext):
    await state.finish()
    await bot.send_message(message.from_user.id,
                           "<b>👮🏻‍♀️ Твой профиль не найден.</b>\n"
                           "▶ Введи повторно /start")


# Проверка на доступность покупок
@dp.message_handler(IsBuy(), text="🎁 Купить", state="*")
@dp.message_handler(IsBuy(), state=StorageUsers.here_input_count_buy_item)
@dp.callback_query_handler(IsBuy(), text_startswith=prohibit_buy, state="*")
async def send_user_message(message, state: FSMContext):
    if "id" in message:
        await message.answer("🔴 Покупки в боте временно отключены", True)
    else:
        await message.answer("<b>🔴 Покупки в боте временно отключены</b>")
