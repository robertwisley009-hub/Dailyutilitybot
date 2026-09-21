import os
import logging
import asyncio
import ast
import operator
from datetime import datetime, timedelta
from collections import defaultdict

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# In-memory storage
todos = defaultdict(list)

# Safe calculator operators
OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}

def safe_eval(expr: str):
    """Safely evaluate a mathematical expression."""
    def _eval(node):
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.BinOp):
            return OPS[type(node.op)](_eval(node.left), _eval(node.right))
        elif isinstance(node, ast.UnaryOp):
            return OPS[type(node.op)](_eval(node.operand))
        else:
            raise ValueError("Unsupported expression")
    tree = ast.parse(expr, mode="eval")
    return _eval(tree.body)

# ---------- Command Handlers ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"Hi {user.first_name}! 👋\n\n"
        "I'm **DailyUtilityBot** — your all-in-one assistant for reminders, planning, calculations, and productivity.\n\n"
        "Use /help to see what I can do.",
        parse_mode="Markdown",
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "*Available Commands:*\n\n"
        "🚀 /start - Welcome message\n"
        "❓ /help - Show this help\n"
        "⏰ /remind `<seconds> <message>` - Set a reminder\n"
        "🧮 /calc `<expression>` - Calculate a math expression\n"
        "📝 /todo `<item>` - Add to your to-do list\n"
        "📋 /list - View your to-do list\n"
        "🗑️ /clear - Clear your to-do list\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def remind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Usage: `/remind <seconds> <message>`", parse_mode="Markdown")
        return

    try:
        delay = int(context.args[0])
        if delay <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Please provide a valid positive number of seconds.")
        return

    reminder_text = " ".join(context.args[1:])
    chat_id = update.effective_chat.id

    await update.message.reply_text(f"⏰ Reminder set for {delay} seconds from now.")

    async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=chat_id, text=f"🔔 Reminder: {reminder_text}")

    context.job_queue.run_once(send_reminder, delay, name=f"remind_{chat_id}")

async def calc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: `/calc <expression>`\nExample: `/calc 2+2*10`", parse_mode="Markdown")
        return

    expr = " ".join(context.args)
    try:
        result = safe_eval(expr)
        await update.message.reply_text(f"🧮 `{expr}` = *{result}*", parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("❌ Invalid expression. Only numbers and + - * / ** are allowed.")

async def todo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: `/todo <item>`", parse_mode="Markdown")
        return
    item = " ".join(context.args)
    user_id = update.effective_user.id
    todos[user_id].append(item)
    await update.message.reply_text(f"✅ Added: *{item}*", parse_mode="Markdown")

async def list_todos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_todos = todos.get(user_id, [])
    if not user_todos:
        await update.message.reply_text("📭 Your to-do list is empty.")
        return
    lines = [f"{i+1}. {t}" for i, t in enumerate(user_todos)]
    await update.message.reply_text("📋 *Your To-Do List:*\n\n" + "\n".join(lines), parse_mode="Markdown")

async def clear_todos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    todos[user_id] = []
    await update.message.reply_text("🗑️ Your to-do list has been cleared.")

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Unknown command. Use /help to see what I can do.")

# ---------- Main ----------

def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set.")
        return

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("remind", remind))
    application.add_handler(CommandHandler("calc", calc))
    application.add_handler(CommandHandler("todo", todo))
    application.add_handler(CommandHandler("list", list_todos))
    application.add_handler(CommandHandler("clear", clear_todos))

    logger.info("Starting DailyUtilityBot with long polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
