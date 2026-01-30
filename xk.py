import telebot
import sqlite3
import random
import time
from telebot import types
import requests
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация
API_TOKEN = '8552583065:AAEsgF1Go8C8J15UjjiqFE-dQjdSFqv57VY'
ADMIN_IDS = {292373003, 8341143841}

# Инициализация
bot = telebot.TeleBot(API_TOKEN, threaded=False)

# База данных
conn = sqlite3.connect('bot.db', check_same_thread=False, isolation_level=None)
cursor = conn.cursor()

# Таблица для каналов
cursor.execute('''
    CREATE TABLE IF NOT EXISTS channels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_id TEXT UNIQUE,
        link TEXT,
        added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

# Таблица для админов
cursor.execute('''
    CREATE TABLE IF NOT EXISTS admins (
        user_id INTEGER UNIQUE
    )
''')

# Таблица для пользователей
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER UNIQUE,
        requests INTEGER DEFAULT 0,
        last_request_date TEXT
    )
''')

conn.commit()

# Загружаем админов
cursor.execute("SELECT user_id FROM admins")
db_admins = cursor.fetchall()
logger.info(f"Загруженные админы из БД: {db_admins}")
for row in db_admins:
    ADMIN_IDS.add(row[0])
logger.info(f"Все админы: {ADMIN_IDS}")

def is_admin(user_id):
    is_adm = user_id in ADMIN_IDS
    logger.info(f"Проверка админа {user_id}: {is_adm}")
    return is_adm

def get_channels():
    cursor.execute("SELECT channel_id, link FROM channels ORDER BY id")
    channels = cursor.fetchall()
    logger.info(f"Каналы в БД: {channels}")
    return channels

def check_subscription(user_id):
    channels = get_channels()
    logger.info(f"Проверка подписки для {user_id}, каналов: {len(channels)}")
    
    if not channels:
        return True
    
    not_subscribed = []
    for channel_id, link in channels:
        try:
            logger.info(f"Проверяем канал {channel_id}")
            member = bot.get_chat_member(channel_id, user_id)
            logger.info(f"Статус в канале {channel_id}: {member.status}")
            if member.status in ['left', 'kicked']:
                not_subscribed.append((channel_id, link))
                logger.info(f"Не подписан на {channel_id}")
        except Exception as e:
            logger.error(f"Ошибка проверки канала {channel_id}: {e}")
            not_subscribed.append((channel_id, link))
    
    return len(not_subscribed) == 0

def create_subscription_keyboard():
    channels = get_channels()
    logger.info(f"Создание клавиатуры с {len(channels)} каналами")
    
    keyboard = []
    for i, (channel_id, link) in enumerate(channels):
        emoji = ["🔴", "🔵", "🟢", "🟡", "🟣"][i % 5]
        keyboard.append([types.InlineKeyboardButton(f"{emoji} СПОНСОР {i+1}", url=link)])
    
    if keyboard:
        keyboard.append([types.InlineKeyboardButton("✅ Проверить подписку", callback_data="check_sub")])
    
    return types.InlineKeyboardMarkup(keyboard)

def create_main_menu():
    keyboard = [
        [types.InlineKeyboardButton("⛔️ SN#S", callback_data="sns_action")],
        [
            types.InlineKeyboardButton("🔐 СП#М", callback_data="spam_action"),
            types.InlineKeyboardButton("❄️ AnFreez", callback_data="anfreez_action")
        ]
    ]
    return types.InlineKeyboardMarkup(keyboard)

def create_back_keyboard():
    keyboard = [[types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
    return types.InlineKeyboardMarkup(keyboard)

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    logger.info(f"Команда /start от {user_id}")
    
    if check_subscription(user_id):
        caption = """
<b>🧨 Вы стали тестировщиком Exda Snoser (FREE VERSION)</b>

Каждый день доступен один запрос, за 1 запрос можно выполнить 1 действие (сн#с , сп#м кодами)

<b>Выберите действие:</b>
"""
        bot.send_message(
            message.chat.id,
            caption,
            parse_mode='HTML',
            reply_markup=create_main_menu()
        )
    else:
        bot.send_message(
            message.chat.id,
            "<b>📢 ПОДПИШИТЕСЬ НА ВСЕХ СПОНСОРОВ ДЛЯ ДОСТУПА</b>",
            parse_mode='HTML',
            reply_markup=create_subscription_keyboard()
        )

# АДМИН КОМАНДЫ
@bot.message_handler(commands=['addchannel'])
def add_channel(message):
    user_id = message.from_user.id
    logger.info(f"Команда /addchannel от {user_id}")
    logger.info(f"Текст сообщения: {message.text}")
    
    if not is_admin(user_id):
        bot.reply_to(message, "❌ Недостаточно прав.")
        return
    
    try:
        args = message.text.split()
        logger.info(f"Аргументы: {args}")
        
        if len(args) != 3:
            bot.reply_to(message, "Использование: /addchannel ID_канала ссылка")
            return
        
        channel_id = args[1]
        link = args[2]
        
        logger.info(f"Добавляем канал: ID={channel_id}, ссылка={link}")
        
        # Проверяем существующие каналы
        cursor.execute("SELECT COUNT(*) FROM channels")
        count = cursor.fetchone()[0]
        logger.info(f"Текущее количество каналов: {count}")
        
        # Добавляем канал
        cursor.execute("INSERT OR REPLACE INTO channels (channel_id, link) VALUES (?, ?)", (channel_id, link))
        conn.commit()
        
        cursor.execute("SELECT COUNT(*) FROM channels")
        new_count = cursor.fetchone()[0]
        logger.info(f"Новое количество каналов: {new_count}")
        
        # Проверяем что канал добавился
        cursor.execute("SELECT channel_id, link FROM channels WHERE channel_id = ?", (channel_id,))
        added = cursor.fetchone()
        logger.info(f"Добавленный канал: {added}")
        
        if added:
            bot.reply_to(message, f"✅ Канал добавлен!\nID: {channel_id}\nСсылка: {link}\nВсего каналов: {new_count}")
        else:
            bot.reply_to(message, "❌ Ошибка: канал не добавлен в БД")
            
    except sqlite3.Error as e:
        logger.error(f"Ошибка SQLite: {e}")
        bot.reply_to(message, f"❌ Ошибка базы данных: {e}")
    except Exception as e:
        logger.error(f"Общая ошибка: {e}")
        bot.reply_to(message, f"❌ Ошибка: {e}")

@bot.message_handler(commands=['list'])
def list_channels(message):
    user_id = message.from_user.id
    logger.info(f"Команда /list от {user_id}")
    
    if not is_admin(user_id):
        bot.reply_to(message, "❌ Недостаточно прав.")
        return
    
    channels = get_channels()
    logger.info(f"Получено каналов для /list: {channels}")
    
    if not channels:
        bot.reply_to(message, "📭 Список каналов пуст")
        return
    
    text = "📋 Список каналов:\n\n"
    for i, (channel_id, link) in enumerate(channels, 1):
        text += f"{i}. ID: {channel_id}\n   Ссылка: {link}\n\n"
    
    text += f"Всего: {len(channels)} канал(ов)"
    bot.reply_to(message, text)

@bot.message_handler(commands=['test'])
def test_db(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    text = "📊 Тест БД:\n\n"
    text += f"Таблицы: {tables}\n\n"
    
    cursor.execute("SELECT * FROM channels")
    channels = cursor.fetchall()
    text += f"Каналы (сырые данные): {channels}\n\n"
    
    cursor.execute("SELECT COUNT(*) FROM channels")
    count = cursor.fetchone()[0]
    text += f"Количество каналов: {count}"
    
    bot.reply_to(message, text)

@bot.message_handler(commands=['clear'])
def clear_channels(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        return
    
    cursor.execute("DELETE FROM channels")
    conn.commit()
    bot.reply_to(message, "✅ Все каналы удалены. БД очищена.")

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    try:
        if call.data == "check_sub":
            user_id = call.from_user.id
            if check_subscription(user_id):
                caption = """
<b>🧨 Вы стали тестировщиком Exda Snoser (FREE VERSION)</b>

Каждый день доступен один запрос, за 1 запрос можно выполнить 1 действие (сн#с , сп#м кодами)

<b>Выберите действие:</b>
"""
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=caption,
                    parse_mode='HTML',
                    reply_markup=create_main_menu()
                )
            else:
                bot.answer_callback_query(call.id, "❌ Вы не подписались на все каналы!", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка в callback: {e}")

logger.info("=" * 50)
logger.info("БОТ ЗАПУЩЕН")
logger.info(f"Токен: {API_TOKEN[:10]}...")
logger.info(f"Админы: {ADMIN_IDS}")
logger.info("=" * 50)

bot.polling(none_stop=True, interval=1)
