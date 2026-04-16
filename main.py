import os
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
from arcaina_bot import ArcainaBot
from dotenv import load_dotenv

load_dotenv()

# Configuration
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY")
DEBUG_USER_ID = os.getenv("DEBUG_USER_ID") # Telegram User ID for backups

# Initialize Bot Logic with Backup Callback
def trigger_backup(filepath, message=None):
    # This needs to be run in the event loop since it's an async operation
    if DEBUG_USER_ID and app:
        prefix = "[[ ARCAINA ADMINISTRATOR LOG ]]\n"
        log_msg = f"{prefix}{message}" if message else f"{prefix}Database update detected."
        asyncio.create_task(app.bot.send_document(
            chat_id=DEBUG_USER_ID, 
            document=open(filepath, 'rb'), 
            caption=log_msg
        ))

bot_logic = ArcainaBot(api_key=GEMINI_API_KEY, backup_callback=trigger_backup)
app = None # Placeholder for global application object

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_msg = update.message.text or ""
    has_image = False
    
    # Check if message is a photo
    if update.message.photo:
        has_image = True
        user_msg = update.message.caption or "Login Photo"

    print(f"[DEBUG] Pesan masuk dari {update.effective_user.first_name} (ID: {update.effective_user.id}): {user_msg} (Image: {has_image})", flush=True)

    # Process via Arcaina Logic
    try:
        # Check if it's a general AI chat (not a suspected command)
        is_command = user_msg.strip().lower() in ["status open", "arcaina rest", "arcaina quest", "arcaina command"]
        
        placeholder = None
        if not is_command and not has_image:
            placeholder = await update.message.reply_text("[+] Arcaina Ask Mode", parse_mode=ParseMode.MARKDOWN)

        response_text = bot_logic.process_message(user_msg, has_image=has_image)
        print(f"[DEBUG] Respon Arcaina: {response_text[:50]}...", flush=True)
        
        try:
            if placeholder:
                await placeholder.edit_text(response_text, parse_mode=ParseMode.MARKDOWN)
            else:
                await update.message.reply_text(response_text, parse_mode=ParseMode.MARKDOWN)
        except Exception as parse_error:
            print(f"[WARNING] Markdown parse error: {parse_error}. Falling back to plain text.")
            if placeholder:
                await placeholder.edit_text(response_text)
            else:
                await update.message.reply_text(response_text)
            
    except Exception as e:
        print(f"[ERROR] Error saat memproses pesan: {e}", flush=True)
        error_msg = "[+] Arcaina Ask Mode Error\nMaf Master, terjadi kesalahan internal."
        if 'placeholder' in locals() and placeholder:
            await placeholder.edit_text(error_msg)
        else:
            await update.message.reply_text(error_msg)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "Master, Saya adalah Arcaina. Asisten yang diciptakan untuk mengukur level Anda di dunia nyata.\n\n"
        "Berikut adalah command yang bisa Anda gunakan:\n"
        "• Status Open - Melihat status Anda\n"
        "• Arcaina Rest - Menandai besok sebagai hari libur\n"
        "• Arcaina Quest - Melihat quest harian\n"
        "• Arcaina Command - Melihat daftar command\n\n"
        "Kirimkan foto antara jam 4-6 pagi untuk melakukan login harian."
    )
    await update.message.reply_text(welcome_text)

if __name__ == '__main__':
    print("Arcaina Telegram Bot is starting...", flush=True)
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))
    
    app.run_polling()
