import json
import os
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# ---------- ФАЙЛЫ ----------
RIDDLES_FILE = "riddles.json"
SCORES_FILE = "scores.json"

# ---------- ЗАГАДКИ ----------
def load_riddles():
    with open(RIDDLES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

riddles = load_riddles()
current_riddle = {}  # user_id: (question, correct_answer)

# ---------- СЧЁТ ----------
def save_scores():
    with open(SCORES_FILE, "w", encoding="utf-8") as f:
        json.dump(user_scores, f, ensure_ascii=False, indent=2)

def load_scores():
    if os.path.exists(SCORES_FILE):
        with open(SCORES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

user_scores = load_scores()

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

    if user_id in current_riddle:
        _, correct = current_riddle[user_id]
        name = query.from_user.username or query.from_user.first_name

        if str(user_id) not in user_scores:
            user_scores[str(user_id)] = {"score": 0, "name": name}

        if selected == correct.lower():
            user_scores[str(user_id)]["score"] += 1
            save_scores()
            await query.edit_message_text(f"🎉 Верно! Твой счёт: {user_scores[str(user_id)]['score']}\nНапиши /riddle для следующей.")
        else:
            await query.edit_message_text("❌ Неверно. Попробуй снова /riddle.")
        del current_riddle[user_id]
    else:
        await query.edit_message_text("Загадка не найдена. Напиши /riddle.")

async def score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    score = user_scores.get(user_id, {}).get("score", 0)
    await update.message.reply_text(f"🏆 Твой счёт: {score}")

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not user_scores:
        await update.message.reply_text("Тут пока никого нет. Будь первым! 🥇")
        return

    top_users = sorted(user_scores.items(), key=lambda x: x[1]["score"], reverse=True)[:3]

    msg = "🏆 Топ игроков:\n"
    for i, (uid, data) in enumerate(top_users, start=1):
        msg += f"{i}. {data['name']} — {data['score']} очков\n"

    await update.message.reply_text(msg)

# ---------- ЗАПУСК ----------
def main():
    app = ApplicationBuilder().token("7531045833:AAEAu4YV2-c8Ut0T6wiAE66zlEEEs1_7AJE").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("riddle", riddle))
    app.add_handler(CommandHandler("score", score))
    app.add_handler(CommandHandler("top", top))
    app.add_handler(CallbackQueryHandler(button))

    print("Бот с очками и топом запущен...")
    print("TOKEN:", os.getenv("BOT_TOKEN"))

    app.run_polling()

if __name__ == "__main__":
    main()
