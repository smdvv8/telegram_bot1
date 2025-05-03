import sqlite3
import random
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums.parse_mode import ParseMode
from aiogram.filters import Command

# --- НАСТРОЙКИ ---
TOKEN = '8048001614:AAHRlJR5JMBtepAAy19vZL9AO6AHBYBUZ1k'
ADMIN_ID = 123456789  # Замените на свой Telegram user ID

# --- БОТ И ДИСПЕТЧЕР ---
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# --- БАЗА ДАННЫХ ---
conn = sqlite3.connect('bot.db')
c = conn.cursor()
c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        has_access INTEGER DEFAULT 0,
        game TEXT,
        mines_count INTEGER DEFAULT 3
    )
""")
c.execute("""
    CREATE TABLE IF NOT EXISTS signals_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        game TEXT,
        prediction TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
""")
conn.commit()

# --- КЛАВИАТУРЫ ---
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎮 Выбрать игру")],
        [KeyboardButton(text="✉️ Получить сигнал")],
        [KeyboardButton(text="📜 История сигналов")]
    ],
    resize_keyboard=True
)

select_game_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="💣 Mines", callback_data="game_mines")],
    [InlineKeyboardButton(text="🚀 Lucky Jet", callback_data="game_luckyjet")]
])

mines_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text=f"{i} мины", callback_data=f"mines_{i}")] for i in range(1, 6)
])

# --- ПРОГНОЗЫ ---
mines_predictions = {
    i: [f"Стратегия {i}.{j}" for j in range(1, 11)] for i in range(1, 6)
}

luckyjet_predictions = [
    f"Сигнал на Lucky Jet #{i}: выход при X={round(random.uniform(1.3, 2.2), 2)}"
    for i in range(1, 51)
]

def generate_mines_prediction(mines_count):
    return random.choice(mines_predictions.get(mines_count, ["Осторожная стратегия. Поставь минимально."]))

def generate_luckyjet_prediction():
    return random.choice(luckyjet_predictions)

# --- ОБРАБОТЧИКИ ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    c.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    welcome_text = (
        "💸 <b>Добро пожаловать в бота</b> <b>1WIN PRO PREDICTOR 💯</b>\n\n"
        "📊 Этот бот генерирует самые прибыльные сигналы для игр 1win: <b>Mines</b> и <b>Lucky Jet</b>.\n"
        "🔐 Для получения доступа — перейдите по ссылке ниже, зарегистрируйтесь и пополните счёт.\n\n"
        "<a href='https://1wzyuh.com/casino/list?open=register&p=vwm0'>🔗 Зарегистрироваться с бонусом</a>\n\n"
        "💡 После пополнения отправьте чек/ID, и админ выдаст доступ.\n"
        "🎮 Выберите игру, затем получите прогноз с высокой точностью!"
    )
    await message.answer(welcome_text, reply_markup=main_kb, disable_web_page_preview=True)

@dp.message(Command("access"))
async def access_cmd(message: types.Message):
    await message.answer("🔗 Пополните счёт через ссылку: https://1wzyuh.com/casino/list?open=register&p=vwm0\n"
                         "После этого отправьте чек или ID сюда для активации.")

@dp.message(F.text == "🎮 Выбрать игру")
async def choose_game(message: types.Message):
    await message.answer("🎲 Выберите игру для получения прогноза:", reply_markup=select_game_kb)

@dp.callback_query(F.data.startswith("game_"))
async def game_selected(call: types.CallbackQuery):
    game = call.data.split("_")[1]
    user_id = call.from_user.id
    c.execute("UPDATE users SET game = ? WHERE user_id = ?", (game, user_id))
    conn.commit()
    game_name = "Mines" if game == "mines" else "Lucky Jet"
    if game == "mines":
        await call.message.answer(f"✅ Игра <b>{game_name}</b> выбрана. Выберите количество мин:", reply_markup=mines_kb)
    else:
        await call.message.answer(f"✅ Игра <b>{game_name}</b> выбрана. Нажмите 'Получить сигнал' для прогноза.")
    await call.answer()

@dp.callback_query(F.data.startswith("mines_"))
async def select_mines_count(call: types.CallbackQuery):
    count = int(call.data.split("_")[1])
    user_id = call.from_user.id
    c.execute("UPDATE users SET mines_count = ? WHERE user_id = ?", (count, user_id))
    conn.commit()
    await call.message.answer(f"✅ Установлено количество мин: <b>{count}</b>. Теперь нажмите 'Получить сигнал'.")
    await call.answer()

@dp.message(F.text == "✉️ Получить сигнал")
async def get_signal(message: types.Message):
    user_id = message.from_user.id
    c.execute("SELECT has_access, game, mines_count FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    if row:
        access, game, mines_count = row
        if access:
            if game:
                if game == "mines":
                    prediction = generate_mines_prediction(mines_count)
                    await message.answer(f"📢 Сигнал на Mines (мин: {mines_count}): {prediction}")
                elif game == "luckyjet":
                    prediction = generate_luckyjet_prediction()
                    await message.answer(f"🚀 Сигнал на Lucky Jet: <b>{prediction}</b>")
                c.execute("INSERT INTO signals_history (user_id, game, prediction) VALUES (?, ?, ?)", (user_id, game, prediction))
                conn.commit()
            else:
                await message.answer("⚠️ Сначала выберите игру.")
        else:
            await message.answer("🔒 Доступ закрыт. Пополните счёт и отправьте чек через /access")
    else:
        await message.answer("Пожалуйста, введите /start сначала.")

@dp.message(F.text == "📜 История сигналов")
async def signal_history(message: types.Message):
    user_id = message.from_user.id
    c.execute("SELECT game, prediction, timestamp FROM signals_history WHERE user_id = ? ORDER BY timestamp DESC LIMIT 5", (user_id,))
    rows = c.fetchall()
    if rows:
        text = "<b>🕓 История сигналов:</b>\n\n"
        for game, prediction, timestamp in rows:
            game_name = "Mines" if game == "mines" else "Lucky Jet"
            text += f"🕒 <i>{timestamp}</i>\n🎮 <b>{game_name}</b>\n🔮 {prediction}\n\n"
        await message.answer(text)
    else:
        await message.answer("❌ История сигналов пуста.")

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("🛠️ Админ панель:\n/giveaccess <user_id> — выдать доступ")

@dp.message(Command("giveaccess"))
async def give_access(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        try:
            user_id = int(message.text.split()[1])
            c.execute("UPDATE users SET has_access = 1 WHERE user_id = ?", (user_id,))
            conn.commit()
            await message.answer(f"✅ Доступ выдан пользователю {user_id}.")
            await bot.send_message(user_id, "✅ Доступ к прогнозам открыт! Выберите игру и получите сигнал.")
        except:
            await message.answer("Ошибка. Используйте: /giveaccess <user_id>")

@dp.message(F.content_type.in_({'photo', 'text'}))
async def handle_payment(message: types.Message):
    if message.chat.type == 'private' and message.from_user.id != ADMIN_ID:
        await bot.send_message(ADMIN_ID, f"📥 Запрос на доступ от @{message.from_user.username or message.from_user.id} ({message.from_user.id})")
        await message.forward(ADMIN_ID)
        await message.answer("🕒 Чек отправлен. Ожидайте активации.")

# --- ЗАПУСК БОТА ---
async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
