import os
import sqlite3
from datetime import datetime
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN")
DB = "expenses.db"

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            category TEXT,
            note TEXT,
            created_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS budgets (
            user_id INTEGER PRIMARY KEY,
            amount REAL
        )
    """)
    conn.commit()
    conn.close()

async def start(update: Update, context):
    await update.message.reply_text(
        "សូមស្វាគមន៍មកកាន់ Bot តាមដានការចំណាយ! 💰\n"
        "ខ្ញុំអាចជួយអ្នកកត់ត្រាការចំណាយ និងគ្រប់គ្រងថវិកា។\n\n"
        "សូមវាយ /help ដើម្បីមើលពាក្យបញ្ជាទាំងអស់។"
    )

async def help_command(update: Update, context):
    await update.message.reply_text(
        "ពាក្យបញ្ជាដែលអាចប្រើបាន៖\n"
        "/start - ចាប់ផ្តើម\n"
        "/expense <ចំនួន> <ប្រភេទ> [កំណត់សម្គាល់] - កត់ត្រាការចំណាយ\n"
        "ឧទាហរណ៍៖ /expense 5 អាហារ បាយថ្ងៃត្រង់\n"
        "/budget <ចំនួន> - កំណត់ថវិកាប្រចាំខែ\n"
        "/report - បង្ហាញរបាយការណ៍ចំណាយ\n"
        "/reset - លុបទិន្នន័យទាំងអស់"
    )

async def expense(update: Update, context):
    user_id = update.effective_user.id
    args = context.args

    if len(args) < 2:
        await update.message.reply_text(
            "សូមប្រើ៖ /expense <ចំនួន> <ប្រភេទ> [កំណត់សម្គាល់]"
        )
        return

    try:
        amount = float(args[0])
    except ValueError:
        await update.message.reply_text("ចំនួនទឹកប្រាក់មិនត្រឹមត្រូវ។ សូមបញ្ចូលជាលេខ។")
        return

    category = args[1]
    note = " ".join(args[2:]) if len(args) > 2 else ""

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        "INSERT INTO expenses (user_id, amount, category, note, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, note, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

    await update.message.reply_text(f"បានកត់ត្រា៖ {amount} ដុល្លារ សម្រាប់ {category} ✅")

async def budget(update: Update, context):
    user_id = update.effective_user.id
    args = context.args

    if len(args) != 1:
        await update.message.reply_text("សូមប្រើ៖ /budget <ចំនួន>")
        return

    try:
        amount = float(args[0])
    except ValueError:
        await update.message.reply_text("ចំនួនទឹកប្រាក់មិនត្រឹមត្រូវ។")
        return

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO budgets (user_id, amount) VALUES (?, ?)", (user_id, amount))
    conn.commit()
    conn.close()

    await update.message.reply_text(f"បានកំណត់ថវិកាប្រចាំខែ៖ {amount} ដុល្លារ ✅")

async def report(update: Update, context):
    user_id = update.effective_user.id
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT SUM(amount) FROM expenses WHERE user_id = ?", (user_id,))
    total = c.fetchone()[0] or 0

    c.execute("SELECT category, SUM(amount) FROM expenses WHERE user_id = ? GROUP BY category", (user_id,))
    rows = c.fetchall()

    c.execute("SELECT amount FROM budgets WHERE user_id = ?", (user_id,))
    budget_row = c.fetchone()
    budget = budget_row[0] if budget_row else None

    conn.close()

    msg = f"📊 របាយការណ៍ចំណាយ\n\nសរុប៖ {total:.2f} ដុល្លារ\n"

    if budget:
        remaining = budget - total
        msg += f"ថវិកា៖ {budget:.2f} ដុល្លារ\nនៅសល់៖ {remaining:.2f} ដុល្លារ\n"

    if rows:
        msg += "\nតាមប្រភេទ៖\n"
        for cat, amt in rows:
            msg += f"- {cat}: {amt:.2f} ដុល្លារ\n"
    else:
        msg += "\nមិនទាន់មានការចំណាយទេ។"

    await update.message.reply_text(msg)

async def reset(update: Update, context):
    user_id = update.effective_user.id
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM expenses WHERE user_id = ?", (user_id,))
    c.execute("DELETE FROM budgets WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

    await update.message.reply_text("បានលុបទិន្នន័យរបស់អ្នកទាំងអស់ ✅")

async def set_commands(app: Application):
    await app.bot.set_my_commands([
        BotCommand("start", "ចាប់ផ្តើម"),
        BotCommand("help", "ជំនួយ"),
        BotCommand("expense", "កត់ត្រាការចំណាយ"),
        BotCommand("budget", "កំណត់ថវិកា"),
        BotCommand("report", "របាយការណ៍"),
        BotCommand("reset", "លុបទិន្នន័យ"),
    ])

def main():
    init_db()
    app = Application.builder().token(TOKEN).post_init(set_commands).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("expense", expense))
    app.add_handler(CommandHandler("budget", budget))
    app.add_handler(CommandHandler("report", report))
    app.add_handler(CommandHandler("reset", reset))

    app.run_polling()

if __name__ == "__main__":
    main()
