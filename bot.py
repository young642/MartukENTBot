import os
from threading import Thread
from flask import Flask

# Сервер, чтобы Render не закрывал бота на бесплатном тарифе
app = Flask('')


@app.route('/')
def home():
  return 'Bot is alive!'


def run():
  port = int(os.environ.get('PORT', 8080))
  app.run(host='0.0.0.0', port=port)


def keep_alive():
  t = Thread(target=run)
  t.daemon = True
  t.start()


# Запускаем фейковый веб-сервер
keep_alive()
import random
import time
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from data import (
    PHYSICS_QUESTIONS, MATH_QUESTIONS, 
    PHYSICS_MATERIALS, MATH_MATERIALS, 
    PHYSICS_TOPICS, MATH_TOPICS
)

# ==================== БАЗА ДАННЫХ (SQLite) ====================

DB_NAME = "bot_stats.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS test_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            subject TEXT,
            topic TEXT,
            score INTEGER,
            total INTEGER,
            percent INTEGER,
            elapsed_sec INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_result(user_id, subject, topic, score, total, percent, elapsed_sec):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO test_results (user_id, subject, topic, score, total, percent, elapsed_sec)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, subject, topic, score, total, percent, elapsed_sec))
    conn.commit()
    conn.close()

def get_user_stats(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*), AVG(percent) FROM test_results WHERE user_id = ?', (user_id,))
    total_tests, avg_percent = cursor.fetchone()
    
    cursor.execute('''
        SELECT subject, topic, score, total, percent, elapsed_sec 
        FROM test_results WHERE user_id = ? ORDER BY id DESC LIMIT 1
    ''', (user_id,))
    last_test = cursor.fetchone()
    
    conn.close()
    return total_tests, avg_percent, last_test

# ==================== ХЕНДЛЕРЫ БОТА ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📐 Математика", callback_data="math"), InlineKeyboardButton("⚡ Физика", callback_data="physics")],
        [InlineKeyboardButton("📊 Моя статистика (БД)", callback_data="stats")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text("Добро пожаловать в ЕНТ Бот! Выбери предмет:", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.edit_message_text("Добро пожаловать в ЕНТ Бот! Выбери предмет:", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id

    if data == "main_menu":
        await start(update, context)

    # --- СТАТИСТИКА ИЗ SQLite ---
    elif data == "stats":
        total_tests, avg_percent, last_test = get_user_stats(user_id)
        
        if not total_tests or total_tests == 0:
            text = "📊 В базе данных пока нет твоих результатов.\nПройди хотя бы один тест!"
        else:
            avg_p = int(avg_percent) if avg_percent else 0
            subject, topic, score, total, percent, sec = last_test
            mins, secs = sec // 60, sec % 60
            time_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"
            
            text = (
                f"💾 ТВОЯ ВЕЧНАЯ СТАТИСТИКА (SQLite)\n\n"
                f"• Всего тестов сдано: {total_tests}\n"
                f"• Средний процент: {avg_p}%\n\n"
                f"📌 Последний тест:\n"
                f"• Предмет: {subject} ({topic})\n"
                f"• Результат: {score}/{total} ({percent}%)\n"
                f"• Время: {time_str}"
            )
            
        keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    # --- МЕНЮ ФИЗИКИ ---
    elif data == "physics":
        keyboard = [
            [InlineKeyboardButton("📝 Выбрать тему и начать тест", callback_data="select_phys_topic")],
            [InlineKeyboardButton("📖 Шпаргалки", callback_data="phys_materials_menu")],
            [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
        ]
        await query.edit_message_text("Раздел: ⚡ Физика\nЧто будем делать?", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "select_phys_topic":
        keyboard = []
        for top_code, top_name in PHYSICS_TOPICS.items():
            keyboard.append([InlineKeyboardButton(top_name, callback_data=f"start_test_phys_{top_code}")])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="physics")])
        await query.edit_message_text("Выбери тему для теста по Физике:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "phys_materials_menu":
        keyboard = [
            [InlineKeyboardButton("🚗 Механика", callback_data="phys_mat_mechanics")],
            [InlineKeyboardButton("🔥 Термодинамика", callback_data="phys_mat_thermo")],
            [InlineKeyboardButton("🔙 Назад в Физику", callback_data="physics")]
        ]
        await query.edit_message_text("Выбери тему шпаргалок по Физике:", reply_markup=InlineKeyboardMarkup(keyboard))

    # --- МЕНЮ МАТЕМАТИКИ ---
    elif data == "math":
        keyboard = [
            [InlineKeyboardButton("📝 Выбрать тему и начать тест", callback_data="select_math_topic")],
            [InlineKeyboardButton("📖 Шпаргалки", callback_data="math_materials_menu")],
            [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
        ]
        await query.edit_message_text("Раздел: 📐 Математика\nЧто будем делать?", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "select_math_topic":
        keyboard = []
        for top_code, top_name in MATH_TOPICS.items():
            keyboard.append([InlineKeyboardButton(top_name, callback_data=f"start_test_math_{top_code}")])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="math")])
        await query.edit_message_text("Выбери тему для теста по Математике:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "math_materials_menu":
        keyboard = [
            [InlineKeyboardButton("📐 Алгебра", callback_data="math_mat_algebra")],
            [InlineKeyboardButton("📐 Геометрия", callback_data="math_mat_geom")],
            [InlineKeyboardButton("🔙 Назад в Математику", callback_data="math")]
        ]
        await query.edit_message_text("Выбери тему шпаргалок по Математике:", reply_markup=InlineKeyboardMarkup(keyboard))

    # --- ВЫВОД ШПАРГАЛОК ---
    elif data in PHYSICS_MATERIALS or data in MATH_MATERIALS:
        text = PHYSICS_MATERIALS.get(data) or MATH_MATERIALS.get(data)
        back_target = "phys_materials_menu" if data in PHYSICS_MATERIALS else "math_materials_menu"
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=back_target)]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    # --- ЗАПУСК ТЕСТА С ВЫБОРОМ ТЕМЫ ---
    elif data.startswith("start_test_"):
        parts = data.split("_")
        subject_code = parts[2] # phys или math
        topic_code = parts[3]   # all, mechanics, thermo, algebra, geom
        
        if subject_code == "phys":
            subject_name = "⚡ Физика"
            raw_questions = PHYSICS_QUESTIONS
            topic_title = PHYSICS_TOPICS.get(topic_code, "Тест")
        else:
            subject_name = "📐 Математика"
            raw_questions = MATH_QUESTIONS
            topic_title = MATH_TOPICS.get(topic_code, "Тест")

        # Фильтруем вопросы по теме
        if topic_code == "all":
            selected_q = raw_questions.copy()
        else:
            selected_q = [q for q in raw_questions if q['topic'] == topic_code]

        if not selected_q:
            await query.edit_message_text("В этой теме пока нет вопросов!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data=subject_code)]]))
            return

        context.user_data['score'] = 0
        context.user_data['q_index'] = 0
        context.user_data['subject_name'] = subject_name
        context.user_data['topic_title'] = topic_title
        context.user_data['questions'] = random.sample(selected_q, len(selected_q))
        context.user_data['start_time'] = time.time()

        await send_question(update, context)

    elif data == "next_q":
        context.user_data['q_index'] += 1
        await send_question(update, context)

    elif data.startswith("ans_"):
        selected_index = int(data.split("_")[1])
        q_index = context.user_data.get('q_index', 0)
        user_questions = context.user_data.get('questions', [])
        
        correct_index = user_questions[q_index]['correct']

        if selected_index == correct_index:
            context.user_data['score'] += 1
            result_text = "✅ Правильно!\n\n"
        else:
            result_text = "❌ Неправильно!\n\n"
            
        explanation = user_questions[q_index]['exp']
        full_text = f"{result_text}Объяснение:\n{explanation}"

        if q_index == len(user_questions) - 1:
            keyboard = [[InlineKeyboardButton("🎉 Показать результаты", callback_data="show_results")]]
        else:
            keyboard = [[InlineKeyboardButton("➡️ Следующий вопрос", callback_data="next_q")]]
            
        await query.edit_message_text(full_text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "show_results":
        score = context.user_data.get('score', 0)
        user_questions = context.user_data.get('questions', [])
        subject_name = context.user_data.get('subject_name', 'Тест')
        topic_title = context.user_data.get('topic_title', 'Общая')
        total = len(user_questions)
        percent = int((score / total) * 100)
        
        start_time = context.user_data.get('start_time', time.time())
        elapsed_sec = int(time.time() - start_time)
        mins, secs = elapsed_sec // 60, elapsed_sec % 60
        time_str = f"{mins} мин {secs} сек" if mins > 0 else f"{secs} сек"
        
        # ЗАПИСЬ В БАЗУ ДАННЫХ SQLite
        save_result(user_id, subject_name, topic_title, score, total, percent, elapsed_sec)
        
        text = (
            f"🎉 Тест завершён!\n"
            f"• Предмет: {subject_name}\n"
            f"• Тема: {topic_title}\n\n"
            f"Правильных ответов: {score}/{total}\n"
            f"Процент: {percent}%\n"
            f"⏱ Время: {time_str}\n\n"
            f"💾 Результат сохранен в базу данных!"
        )
        keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")]]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    q_index = context.user_data.get('q_index', 0)
    user_questions = context.user_data.get('questions', [])
    topic_title = context.user_data.get('topic_title', 'Тест')
    question_data = user_questions[q_index]
    
    text = f"📌 Тема: {topic_title}\nВопрос {q_index + 1}/{len(user_questions)}\n\n{question_data['q']}"
    
    letters = ["A", "B", "C", "D"]
    keyboard = []
    for i, option in enumerate(question_data['options']):
        button_text = f"{letters[i]}) {option}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"ans_{i}")])
        
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

if __name__ == '__main__':
    # Инициализация базы данных
    init_db()
    
    # ВСТАВЬ СВОЙ ТОКЕН НИЖЕ
    app = ApplicationBuilder().token("8112456035:AAGuKVsFiqnqZZuS_6oAeN-vCB6lSXRVQ10").build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("Бот запущен с базой данных SQLite. Нажми Ctrl+C для остановки.")
    app.run_polling()