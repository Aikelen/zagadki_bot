import json
import os
import random
import asyncpg
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# ---------- ФАЙЛ ЗАГАДОК ----------
RIDDLES_FILE = "riddles.json"
with open(RIDDLES_FILE, "r", encoding="utf-8") as f:
    riddles = json.load(f)

current_riddle = {}  # user_id: (question, correct_answer)
DB_URL = os.getenv("DATABASE_URL")

# ---------- ФУНКЦИИ ДЛЯ РАБОТЫ С БАЗОЙ ----------

async def get_score(user_id):
    conn = await asyncpg.connect(DB_URL)
    row = await conn.fetchrow("SELECT score FROM scores WHERE user_id = $1", user_id)
    await conn.close()
    return row["score"] if row else 0

async def update_score(user_id, username, correct=True):
    score = await get_score(user_id)
    new_score = score + 1 if correct else score

    conn = await asyncpg.connect(DB_URL)
    await conn.execute("""
        INSERT INTO scores (user_id, username, score)
        VALUES ($1, $2, $3)
        ON CONFLICT (user_id) DO UPDATE
        SET username = $2, score = $3
    """, user_id, username, new_score)
    await conn.close()

async def get_top_scores(limit=3):
    conn = await asyncpg.connect(DB_URL)
    rows = await conn.fetch("""
        SELECT username, score FROM scores
        ORDER BY score DESC
        LIMIT $1
    """, limit)
    await conn.close()
    return rows

# ---------- КОМАНДЫ ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Нажми /riddle — я загадаю загадку с вариантами 😉")

async def riddle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question, correct_answer = random.choice(list(riddles.items()))
    all_answers = list(riddles.values())
    options = random.sample([a for a in all_answers if a != correct_answer], 3) + [correct_answer]
    random.shuffle(options)

    keyboard = [[InlineKeyboardButton(opt, callback_data=opt)] for opt in options]
    reply_markup = InlineKeyboardMarkup(keyboard)

    current_riddle[update.effective_user.id] = (question, correct_answer)
    await update.message.reply_text(f"Загадка:\n{question}", reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    selected = query.data.lower()

    if user_id not in current_riddle:
        await query.edit_message_text("Загадка не найдена. Напиши /riddle.")
        return

    question, correct = current_riddle[user_id]
    name = query.from_user.username or query.from_user.first_name

    try:
        if selected == correct.lower():
            await update_score(user_id, name, correct=True)
            score = await get_score(user_id)
            await query.edit_message_text(
                f"🎉 Верно! Твой счёт: {score}\nНапиши /riddle для следующей."
            )
        else:
            await query.edit_message_text("❌ Неверно. Попробуй снова /riddle.")
    except Exception as e:
        await query.edit_message_text(f"⚠️ Ошибка: {e}")

    # Удаляем загадку независимо от ответа
    del current_riddle[user_id]
async def score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    score = await get_score(user_id)
    await update.message.reply_text(f"🏆 Твой счёт: {score}")

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top_users = await get_top_scores()
    if not top_users:
        await update.message.reply_text("Тут пока никого нет. Будь первым! 🥇")
        return

    msg = "🏆 Топ игроков:\n"
    for i, row in enumerate(top_users, start=1):
        msg += f"{i}. {row['username']} — {row['score']} очков\n"

    await update.message.reply_text(msg)

# ---------- ЗАПУСК ----------

def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("❌ Переменная BOT_TOKEN не найдена!")

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("riddle", riddle))
    app.add_handler(CommandHandler("score", score))
    app.add_handler(CommandHandler("top", top))
    app.add_handler(CallbackQueryHandler(button))

    print("Бот с базой данных запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
