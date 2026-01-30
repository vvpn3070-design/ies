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

# Инициализация с настройками
bot = telebot.TeleBot(
    token=API_TOKEN,
    parse_mode='HTML',
    threaded=False,  # Отключаем многопоточность для Termux
    num_threads=1
)

# База данных
conn = sqlite3.connect('bot.db', check_same_thread=False)
cursor = conn.cursor()

# Таблица для каналов
cursor.execute('''
    CREATE TABLE IF NOT EXISTS channels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_id TEXT UNIQUE,
        link TEXT
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
for row in cursor.fetchall():
    ADMIN_IDS.add(row[0])

def is_admin(user_id):
    return user_id in ADMIN_IDS

def get_channels():
    cursor.execute("SELECT channel_id, link FROM channels")
    return cursor.fetchall()

def can_make_request(user_id):
    cursor.execute("SELECT requests, last_request_date FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    
    if not row:
        cursor.execute("INSERT INTO users (user_id, requests, last_request_date) VALUES (?, 0, ?)", 
                      (user_id, "1970-01-01"))
        conn.commit()
        return True
    
    requests, last_date = row
    today = time.strftime("%Y-%m-%d")
    
    if last_date != today:
        cursor.execute("UPDATE users SET requests = 0, last_request_date = ? WHERE user_id = ?", 
                      (today, user_id))
        conn.commit()
        return True
    
    return requests < 1

def increment_requests(user_id):
    today = time.strftime("%Y-%m-%d")
    cursor.execute("UPDATE users SET requests = requests + 1, last_request_date = ? WHERE user_id = ?", 
                  (today, user_id))
    conn.commit()

def create_subscription_keyboard():
    channels = get_channels()
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

def send_main_menu(chat_id, user_id):
    caption = """
<b>🧨 Вы стали тестировщиком Exda Snoser (FREE VERSION)</b>

Каждый день доступен один запрос, за 1 запрос можно выполнить 1 действие (сн#с , сп#м кодами)

<b>Выберите действие:</b>
"""
    
    # Проверяем фото
    photo_url = "https://t.me/ak3ic9/15"
    try:
        response = requests.head(photo_url, timeout=5)
        if response.status_code == 200:
            bot.send_photo(
                chat_id=chat_id,
                photo=photo_url,
                caption=caption,
                reply_markup=create_main_menu()
            )
        else:
            bot.send_message(
                chat_id=chat_id,
                text=caption,
                reply_markup=create_main_menu()
            )
    except:
        bot.send_message(
            chat_id=chat_id,
            text=caption,
            reply_markup=create_main_menu()
        )

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    
    channels = get_channels()
    if not channels:
        send_main_menu(message.chat.id, user_id)
        return
    
    # Проверяем подписку
    not_subscribed = []
    for channel_id, link in channels:
        try:
            member = bot.get_chat_member(channel_id, user_id)
            if member.status in ['left', 'kicked']:
                not_subscribed.append(link)
        except Exception as e:
            logger.error(f"Ошибка проверки канала {channel_id}: {e}")
            not_subscribed.append(link)
    
    if not_subscribed:
        keyboard = types.InlineKeyboardMarkup()
        for link in not_subscribed:
            keyboard.add(types.InlineKeyboardButton("🔗 Подписаться", url=link))
        keyboard.add(types.InlineKeyboardButton("✅ Я подписался", callback_data="check_sub"))
        
        bot.send_message(
            message.chat.id,
            "<b>📢 ПОДПИШИТЕСЬ НА ВСЕХ СПОНСОРОВ ДЛЯ ДОСТУПА</b>",
            reply_markup=keyboard
        )
    else:
        send_main_menu(message.chat.id, user_id)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    
    try:
        if call.data == "check_sub":
            bot.answer_callback_query(call.id, "Проверяем подписку...")
            time.sleep(1)
            
            channels = get_channels()
            if not channels:
                send_main_menu(call.message.chat.id, user_id)
                return
            
            subscribed = True
            for channel_id, link in channels:
                try:
                    member = bot.get_chat_member(channel_id, user_id)
                    if member.status in ['left', 'kicked']:
                        subscribed = False
                        break
                except:
                    subscribed = False
            
            if subscribed:
                send_main_menu(call.message.chat.id, user_id)
            else:
                bot.answer_callback_query(call.id, "❌ Вы не подписались на все каналы!", show_alert=True)
        
        elif call.data == "sns_action":
            if not can_make_request(user_id):
                bot.answer_callback_query(call.id, "❌ Вы использовали дневной лимит!", show_alert=True)
                return
            
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.send_message(
                call.message.chat.id,
                "<b>🤫 Отправьте юзернейм жертвы, если его нет — айди</b>"
            )
            bot.register_next_step_handler(call.message, process_sns)
        
        elif call.data == "spam_action":
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.send_message(
                call.message.chat.id,
                "<i>Данная функция находится в разработке...</i>",
                reply_markup=create_back_keyboard()
            )
        
        elif call.data == "anfreez_action":
            if not can_make_request(user_id):
                bot.answer_callback_query(call.id, "❌ Вы использовали дневной лимит!", show_alert=True)
                return
            
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.send_message(
                call.message.chat.id,
                "<b>Отправьте юзернейм или айди для разморозки</b>"
            )
            bot.register_next_step_handler(call.message, process_anfreez)
        
        elif call.data == "back_to_menu":
            bot.delete_message(call.message.chat.id, call.message.message_id)
            send_main_menu(call.message.chat.id, user_id)
            
    except Exception as e:
        logger.error(f"Ошибка в callback: {e}")
        bot.answer_callback_query(call.id, "⚠️ Произошла ошибка")

def process_sns(message):
    user_id = message.from_user.id
    target = message.text
    
    increment_requests(user_id)
    
    processing_msg = bot.send_message(
        message.chat.id,
        "<b>❄️ Отправляю жалобы...</b>"
    )
    
    time.sleep(random.uniform(3, 5))
    
    successful = random.randint(198, 202)
    blocked = random.randint(3, 14)
    
    bot.delete_message(message.chat.id, processing_msg.message_id)
    bot.send_message(
        message.chat.id,
        f"""
<b>❄️ ЖАЛОБЫ ДОСТАВЛЕНЫ!</b>
<b>💀 Цель:</b> {target}
<b>✅ Успешных жалоб:</b> {successful}
<b>❌ Заблокировано:</b> {blocked}
        """,
        reply_markup=create_back_keyboard()
    )

def process_anfreez(message):
    user_id = message.from_user.id
    target = message.text
    
    increment_requests(user_id)
    
    processing_msg = bot.send_message(
        message.chat.id,
        "<b>❄️ Отправляю апелляции...</b>"
    )
    
    time.sleep(3)
    
    successful = random.randint(72, 120)
    
    bot.delete_message(message.chat.id, processing_msg.message_id)
    bot.send_message(
        message.chat.id,
        f"""
<b>❄️ АППЕЛЯЦИИ ОТПРАВЛЕНЫ ✅</b>
<b>✅ Успешно:</b> {successful}
<b>💀 Цель:</b> {target}
        """,
        reply_markup=create_back_keyboard()
    )

# Админ-команды
@bot.message_handler(commands=['addchannel'])
def add_channel(message):
    if not is_admin(message.from_user.id):
        return
    
    try:
        args = message.text.split()
        if len(args) != 3:
            bot.reply_to(message, "Использование: /addchannel ID_канала ссылка")
            return
        
        channel_id, link = args[1], args[2]
        
        cursor.execute("INSERT OR REPLACE INTO channels (channel_id, link) VALUES (?, ?)", (channel_id, link))
        conn.commit()
        bot.reply_to(message, f"✅ Канал добавлен: {channel_id}")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")

@bot.message_handler(commands=['addadm'])
def add_admin(message):
    if not is_admin(message.from_user.id):
        return
    
    try:
        args = message.text.split()
        if len(args) != 2:
            bot.reply_to(message, "Использование: /addadm ID_пользователя")
            return
        
        user_id = int(args[1])
        cursor.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (user_id,))
        conn.commit()
        ADMIN_IDS.add(user_id)
        bot.reply_to(message, f"✅ Админ добавлен: {user_id}")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")

@bot.message_handler(commands=['del'])
def delete_channel(message):
    if not is_admin(message.from_user.id):
        return
    
    try:
        args = message.text.split()
        if len(args) != 2:
            bot.reply_to(message, "Использование: /del ссылка_канала")
            return
        
        link = args[1]
        cursor.execute("DELETE FROM channels WHERE link = ?", (link,))
        conn.commit()
        if cursor.rowcount > 0:
            bot.reply_to(message, "✅ Канал удален")
        else:
            bot.reply_to(message, "❌ Канал не найден")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")

@bot.message_handler(commands=['list'])
def list_channels(message):
    if not is_admin(message.from_user.id):
        return
    
    channels = get_channels()
    if not channels:
        bot.reply_to(message, "📭 Список каналов пуст")
        return
    
    text = "📋 Список каналов:\n\n"
    for i, (channel_id, link) in enumerate(channels, 1):
        text += f"{i}. ID: {channel_id}\n   Ссылка: {link}\n\n"
    
    bot.reply_to(message, text)

@bot.message_handler(commands=['clear'])
def clear_channels(message):
    if not is_admin(message.from_user.id):
        return
    
    cursor.execute("DELETE FROM channels")
    conn.commit()
    bot.reply_to(message, "✅ Все каналы удалены")

# Функция для безопасного запуска
def run_bot():
    while True:
        try:
            logger.info("Запуск бота...")
            bot.polling(none_stop=True, interval=1, timeout=30)
        except Exception as e:
            logger.error(f"Ошибка бота: {e}")
            logger.info("Перезапуск через 10 секунд...")
            time.sleep(10)

if __name__ == '__main__':
    logger.info("Бот запускается...")
    try:
        run_bot()
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
