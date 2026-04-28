import os
import logging
from telegram.ext import ApplicationBuilder, CommandHandler

MANAGER_TOKEN = os.environ.get('MANAGER_TOKEN')

async def start(update, context):
    await update.message.reply_text("سڵاو سایە گیان! بۆتەکەم ئیش دەکات ✅")

if __name__ == '__main__':
    app = ApplicationBuilder().token(MANAGER_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("Bot is running...")
    app.run_polling()
