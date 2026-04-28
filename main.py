import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from flask import Flask
from threading import Thread

# بۆ UptimeRobot
app = Flask('')
@app.route('/')
def home(): return "Bot Manager is alive!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# داتابەیس
user_bots = {} # {user_id: {token: {'sections': [], 'videos': [], 'channels': []}}}
running_bots = {} # {token: application}

ADD_TOKEN = 1
ADD_SECTION = 2
ADD_VIDEO = 3
ADD_CHANNEL = 4

# ========== بۆتی سەرەکی - Manager Bot ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("➕ زیادکردنی بۆتی نوێ", callback_data='add_bot')],
        [InlineKeyboardButton("🤖 بۆتەکانم", callback_data='my_bots')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = """سڵاو 👋
بەخێرهاتی بۆ بەڕێوەبەری بۆتەکان.

لێرە دەتوانیت بۆتی نوێ زیاد بکەیت. دوای زیادکردن، بۆتەکە خۆی هەڵدەستێت و ئەم کردارانەی دەبێت:
- ناوی بەش زیاد بکات
- ڤیدیۆ زیاد/بسڕێتەوە
- کەناڵ بەڕێوەببات

تکایە یەکێک هەڵبژێرە 👇"""

    await update.message.reply_text(text, reply_markup=reply_markup)

async def manager_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == 'add_bot':
        await query.edit_message_text("تۆکینی بۆتەکەت بنێرە:\n\nبۆتەکە دوای زیادکردن خۆی هەڵدەستێت و ئامادە دەبێت ✅")
        return ADD_TOKEN

    elif query.data == 'my_bots':
        bots = user_bots.get(user_id, {})
        if not bots:
            await query.edit_message_text("هیچ بۆتێکت زیاد نەکردووە ❌")
        else:
            text = "🤖 بۆتەکانت:\n\n"
            for i, token in enumerate(bots.keys(), 1):
                status = "🟢 ئیش دەکات" if token in running_bots else "🔴 وەستاوە"
                text += f"{i}. Bot_{token.split(':')[0]}... {status}\n"
            await query.edit_message_text(text)

async def receive_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    token = update.message.text.strip()

    if ':' not in token or len(token) < 40:
        await update.message.reply_text("❌ تۆکین هەڵەیە!")
        return ADD_TOKEN

    if user_id not in user_bots:
        user_bots[user_id] = {}

    user_bots[user_id][token] = {'sections': [], 'videos': [], 'channels': []}

    # بۆتە نوێیەکە هەڵبخە
    await start_child_bot(token, user_id)

    await update.message.reply_text(f"✅ بۆت زیادکرا و هەڵبەسترایەوە!\n\nئێستا بچۆ Telegram و لەو بۆتە /start بکە.\nID: {token.split(':')[0]}...")
    return ConversationHandler.END

# ========== بۆتە منداڵەکان - Child Bots ==========
async def start_child_bot(token, owner_id):
    if token in running_bots:
        return

    try:
        app_child = ApplicationBuilder().token(token).build()

        # هەر بۆتێک داتای خۆی هەبێت
        app_child.bot_data['owner_id'] = owner_id
        app_child.bot_data['token'] = token

        app_child.add_handler(CommandHandler('start', child_start))
        app_child.add_handler(CallbackQueryHandler(child_button))
        app_child.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, child_message))

        running_bots[token] = app_child
        await app_child.initialize()
        await app_child.start()
        asyncio.create_task(app_child.updater.start_polling())
        print(f"Child bot {token.split(':')[0]} started")

    except Exception as e:
        print(f"Error starting bot: {e}")

async def child_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📁 زیادکردنی بەش", callback_data='add_section')],
        [InlineKeyboardButton("🎬 ڤیدیۆکانم", callback_data='videos')],
        [InlineKeyboardButton("📢 کەناڵەکەم", callback_data='channels')],
        [InlineKeyboardButton("📋 بەشەکانم", callback_data='list_sections')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "بەخێربێیت! ئەمە بۆتی تایبەتی تۆیە 🤖\n\nلێرە دەتوانیت بەش و ڤیدیۆ و کەناڵ بەڕێوەببەیت:",
        reply_markup=reply_markup
    )

async def child_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    token = context.bot_data['token']
    owner_id = context.bot_data['owner_id']

    if query.data == 'add_section':
        context.user_data['action'] = 'add_section'
        await query.edit_message_text("ناوی بەشی نوێ بنێرە:")

    elif query.data == 'videos':
        context.user_data['action'] = 'add_video'
        await query.edit_message_text("لینکی ڤیدیۆکە یان ناوی بنێرە:")

    elif query.data == 'channels':
        context.user_data['action'] = 'add_channel'
        await query.edit_message_text("یوزەرنەیمی کەناڵەکە بنێرە: @example")

    elif query.data == 'list_sections':
        sections = user_bots[owner_id][token]['sections']
        if not sections:
            text = "هیچ بەشێکت نییە ❌"
        else:
            text = "📁 بەشەکانت:\n\n" + "\n".join([f"{i+1}. {s}" for i, s in enumerate(sections)])
        await query.edit_message_text(text)

async def child_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    token = context.bot_data['token']
    owner_id = context.bot_data['owner_id']
    action = context.user_data.get('action')
    text = update.message.text

    if action == 'add_section':
        user_bots[owner_id][token]['sections'].append(text)
        await update.message.reply_text(f"✅ بەشی '{text}' زیادکرا")

    elif action == 'add_video':
        user_bots[owner_id][token]['videos'].append(text)
        await update.message.reply_text(f"✅ ڤیدیۆ زیادکرا")

    elif action == 'add_channel':
        user_bots[owner_id][token]['channels'].append(text)
        await update.message.reply_text(f"✅ کەناڵی {text} زیادکرا")

    context.user_data['action'] = None

# ========== Run ==========
MANAGER_TOKEN = "8695142612:AAHHgJUUJvm7-oiO0lCwT6Eg-aU3E4MWXA4   "

if __name__ == '__main__':
    keep_alive()
    application = ApplicationBuilder().token(MANAGER_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(manager_button, pattern='^add_bot$')],
        states={ADD_TOKEN: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_token)]},
        fallbacks=[CommandHandler('cancel', lambda u,c: ConversationHandler.END)]
    )

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(manager_button))
    application.add_handler(conv_handler)

    print("Manager Bot started...")
    application.run_polling()