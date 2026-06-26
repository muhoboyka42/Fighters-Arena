import os
import sqlite3
from openai import OpenAI

client = OpenAI(
    api_key="token",
    base_url="token"
)

instruction = """Ты — движок и ведущий текстовой RPG-игры «Виртуальные бои». Твоя цель — проводить динамичные, честные и интересные пошаговые сражения.

### СТАРТОВЫЕ ПАРАМЕТРЫ
- У каждого игрока на старте ВСЕГДА ровно 100 HP. Это неизменное базовое значение.

### ПРАВИЛА СОЗДАНИЯ ПРОТИВНИКА
Как только пользователь передаст Имя и Силу своего персонажа, ты обязан сгенерировать ему сбалансированного противника.
- Имя: Придумай уникальное имя.
- HP (Здоровье): Ровно 100 HP (как и у игрока).
- Сила (Урон): Рассчитай так, чтобы противник соответствовал силе игрока.

### ПРАВИЛА БАЛАНСА БОЯ (СТРОГОЕ СОБЛЮДЕНИЕ)
1. ЗАПРЕТ НА ВАНШОТЫ: Ни один персонаж (ни игрок, ни противник) не может погибнуть с одного удара в начале или середине боя. 
2. ОГРАНИЧЕНИЕ УРОНА: Максимальный урон за ОДИН ход (включая критические удары) категорически НЕ может превышать 25-30 HP. Бой должен длиться минимум 4-5 ходов.
3. Логика урона: Урон зависит от характеристики "Сила", но имеет случайный разброс (критический удар, скользящий удар, промах, блок).
4. Пошаговость: Один ход — это одно действие игрока и один ответный шаг противника.

### ИГРОВОЙ ПРОЦЕСС
1. Первый ход: Жди, пока пользователь введет Имя и Силу своего персонажа. Как только получил — зафиксируй ему 100 HP, создай противника (тоже 100 HP), опиши сцену начала боя и запроси первое действие.
2. Игровой цикл: Описывай последствия выбора игрока, рассчитывай урон, а затем описывай ответную атаку противника. После этого жди ввода пользователя. Не предлагай вариантов, игрок пишет сам.
3. Финал: Бой завершается ТОЛЬКО тогда, когда HP одного из участников падает до 0 или ниже. Опиши финальный исход.

### СТРОГИЙ ФОРМАТ ОТВЕТА
Каждое твое сообщение ОБЯЗАНО состоять из трех частей. Изменять структуру или пропускать блок "ХАРАКТЕРИСТИКИ" категорически запрещено.

[Часть 1: Художественное описание событий текущего хода, совершенных атак и полученного урона / Либо описание финала]

[Часть 2: Короткий вопрос пользователю о его следующем действии (если бой продолжается)]

ХАРАКТЕРИСТИКИ:
[ИМЯ_ИГРОКА]: HP [ТЕКУЩЕЕ_ХП]/100 | Сила [СИЛА]
[ИМЯ_ПРОТИВНИКА]: HP [ТЕКУЩЕЕ_ХП]/100 | Сила [СИЛА]"""

DB_NAME = "chat_history.db"


def init_db():
    with sqlite3.connect(DB_NAME) as db:
        cursor = db.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_ID INTEGER,
            role TEXT,
            character_name TEXT,
            p1 INTEGER,
            p2 INTEGER,
            HP INTEGER,
            POWER INTEGER,
            CONTEXT TEXT
        )
        """)
def add_player_to_queue():
    with sqlite3.connect(DB_NAME) as db:
        cursor = db.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS queue(user_ID INTEGER PRIMARY KEY)")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS session(
        session_id INTEGER PRIMARY KEY AUTOINCREMENT,
        playerid_1 INTEGER,
        playerid_2 INTEGER,
        p1 INTEGER,
        p2 INTEGER,
        p1_context TEXT DEFAULT NULL,
        p2_context TEXT DEFAULT NULL
        )
        """)

def add_message_to_history(user_ID, role, content, character_name=None, hp=0, power=0):
    with sqlite3.connect(DB_NAME) as db:
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO messages (user_ID, role, CONTEXT, POWER, HP, character_name) VALUES (?, ?, ?, ?, ?, ?)",
            (user_ID, role, content, power, hp, character_name)
        )


def get_user_history(user_ID):
    history = []
    with sqlite3.connect(DB_NAME) as db:
        cursor = db.cursor()
        cursor.execute("SELECT role, CONTEXT FROM messages WHERE user_ID=? ORDER BY id ASC", (user_ID,))
        rows = cursor.fetchall()
        for row in rows:
            history.append({"role": row[0], "content": row[1]})
    return history


def start_chat(user_ID, user_input):
    history_chat = get_user_history(user_ID)


    if not history_chat:
        add_message_to_history(user_ID, "system", instruction)
        history_chat.append({"role": "system", "content": instruction})

    add_message_to_history(user_ID, "user", user_input)
    history_chat.append({"role": "user", "content": user_input})

    try:
        chat_completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=history_chat,
            temperature=0.7
        )
        bot_response = chat_completion.choices[0].message.content
        items = bot_response.split("\n")
        stats = items[-1].split(":")
        print(stats)
        if len(stats) == 3:
            character_name = stats[0]
            HP = stats[1]
            POWER = stats[2]
            add_message_to_history(user_ID, "system", f"Победил {character_name}, ХП: {HP}, СИЛА: {POWER}", character_name, hp=HP, power=POWER)
            print(character_name, HP, POWER)
        add_message_to_history(user_ID, "assistant", bot_response)
        return bot_response

    except Exception as e:
        print(f"Ошибка: {e}")
        return "Произошла ошибка при обращении к ИИ."
