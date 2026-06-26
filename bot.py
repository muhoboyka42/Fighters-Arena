from http.client import responses
import telebot
from telebot import types
import sqlite3
from main import start_chat, init_db, DB_NAME, add_player_to_queue

tocen = "token"
bot = telebot.TeleBot(tocen)
user_sessions = {}
@bot.message_handler(commands=["start"])
def send_welcome(message):
    chat_id = message.chat.id
    user_sessions[chat_id] = []
    bot.reply_to(message, "[ СИСТЕМА ИНИЦИАЛИЗИРОВАНА ] 🤖⚡️\n\n"
        "Приветствую, боец! Ты подключился к Battle-AI v1.0. \n"
        "Я генерирую виртуальные бои в реальном времени. Ты даешь героя — я создаю ему смертоносного противника. 💀\n\n"
        "📈 ВВОД ДАННЫХ ПЕРСОНАЖА:\n"
        "Отправь параметры в кодировке:\n"
        "ИМЯ:ХП:СИЛА\n\n"
        "---------------------------\n"
        "📝 Пример:\n"
        "Кибер-Самурай:100:85\n"
        "---------------------------\n\n"
        "Вводи данные и начнем симуляцию! 👇")

@bot.message_handler(commands=["search"])
def search(message):
    chat_id = message.chat.id
    with sqlite3.connect(DB_NAME) as db:
        cursor = db.cursor()
        cursor.execute("SELECT user_id FROM queue LIMIT 1")
        rows = cursor.fetchall()
        if rows:
            opponent_id = rows[0][0]
            if opponent_id == chat_id:
                bot.send_message(chat_id, "Ты уже в очереди")
                return
            cursor.execute("DELETE FROM queue WHERE user_id = ?", (opponent_id,))
            cursor.execute("INSERT INTO session (p1, p2) VALUES (?, ?) ", (chat_id, opponent_id))
            db.commit()
            start_messeage = "Противник найден"
            bot.send_message(chat_id, start_messeage)
            bot.send_message(opponent_id, start_messeage)
        else:
            cursor.execute("INSERT OR IGNORE INTO queue (user_id) VALUES (?) ", (chat_id,))
            db.commit()
            bot.send_message(chat_id, "Противник еще не найден \n Ожидайте")
@bot.message_handler(content_types=["text"])
@bot.message_handler(content_types=["text"])
def AI_dialog(message):
    chat_id = message.chat.id
    user_text = message.text

    with sqlite3.connect(DB_NAME) as db:
        cursor = db.cursor()
        cursor.execute("SELECT session_id, p1, p2, p1_context, p2_context FROM session WHERE p1 = ? OR p2 = ?",(chat_id, chat_id))
        session = cursor.fetchone()
        if not session:
            bot.reply_to(message, "Ты еще не в бою, напиши /search")
            return
        session_id, p1, p2, p1_context, p2_context = session
        if chat_id == p1:
            cursor.execute("UPDATE session SET p1_context = ? WHERE session_id = ?", (user_text, session_id))
            p1_context = user_text
        else:
            cursor.execute("UPDATE session SET p2_context = ? WHERE session_id = ?", (user_text, session_id))
            p2_context = user_text
        db.commit()
        if p1_context and p2_context:
            bot.send_message(p1, "ИИ рассчитывает раунд...")
            bot.send_message(p2, "ИИ рассчитывает раунд...")
            combined_input = f"Игрок 1 делает: {p1_context}. Игрок 2 делает: {p2_context}"
            responses_text = start_chat(session_id, combined_input)
            cursor.execute("UPDATE session SET p1_context = NULL, p2_context = NULL WHERE session_id = ?",
                           (session_id,))
            db.commit()
            bot.send_message(p1, responses_text)
            bot.send_message(p2, responses_text)
        else:
            bot.send_message(chat_id, "Ход принят, ждем противника...")
if __name__ == "__main__":
    init_db()
    add_player_to_queue()
    bot.polling(none_stop=True)