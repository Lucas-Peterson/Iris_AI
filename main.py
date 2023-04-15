import logging
from aiogram import Bot, Dispatcher, types, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3

API_TOKEN = '6023656375:AAE7d_7qn782FQPZkTXx_154cmQKA2DzyNA'
ADMINS = [707305173]
bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

conn = sqlite3.connect('users.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""CREATE TABLE IF NOT EXISTS users 
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                nickname TEXT NOT NULL,
                banned BOOLEAN DEFAULT FALSE);""")
conn.commit()


class ForwardStates(StatesGroup):
    forward = State()


# Обработка команды /start
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    nickname = message.from_user.username
    cursor.execute(f"INSERT INTO users (user_id, nickname) VALUES ('{user_id}', '{nickname}');")
    conn.commit()

    if user_id in ADMINS:
        await message.answer("Ваш бот предложка к вашим услугам, ждите первых сообщений!")
    else:
        await message.answer("Привет! Я бот-предложка, используй команду /forward для отправки своего предложения.")


# Обработка команды /forward
@dp.message_handler(Command('forward'))
async def cmd_forward(message: types.Message):
    await message.answer("Введите ваше предложение для пересылки:")
    await ForwardStates.forward.set()

# Пересылка сообщения администраторам
@dp.message_handler(state=ForwardStates.forward)
async def forward_message(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['forward_message'] = message.text
    for admin in ADMINS:
        forward_message = f"<b>Новое предложение от {message.from_user.username},:</b>\n\n{message.text}"
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(InlineKeyboardButton('Ban', callback_data='ban'),
                     InlineKeyboardButton('Delete', callback_data='delete'))
        await bot.send_message(chat_id=admin, text=forward_message, reply_markup=keyboard)
    await state.finish()

# Обработка нажатий на кнопки

@dp.callback_query_handler(lambda c: c.data in ['ban', 'delete'])
async def process_callback_button(callback_query: types.CallbackQuery):
    reply_to_message = callback_query.message.reply_to_message
    if not reply_to_message:
        return
    user_id = reply_to_message.forward_from.id
    if callback_query.data == 'ban':
        cursor.execute(f"UPDATE users SET banned = TRUE WHERE user_id = {user_id}")
        conn.commit()
        await callback_query.answer(text=f"Пользователь {reply_to_message.from_user.username} заблокирован.")
    elif callback_query.data == 'delete':
        await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
        await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.reply_to_message.message_id)


# Обработка ответа администратора
@dp.message_handler(lambda message: message.reply_to_message and message.reply_to_message.from_user.id in ADMINS)
async def reply_to_user(message: types.Message):
    user_id = message.reply_to_message.forward_from.id
    await bot.send_message(chat_id=user_id, text=f"Ответ администрации: {message.text}")

# Запуск бота
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    executor.start_polling(dp, skip_updates=True)

