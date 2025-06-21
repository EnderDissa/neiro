import os
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
VIDEO_DIR = "./videos"

async def handle_video_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_dir = os.path.join(VIDEO_DIR, str(user_id))

    if not os.path.exists(user_dir):
        os.makedirs(user_dir)

    video_note = update.message.video_note
    file = await context.bot.get_file(video_note.file_id)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(user_dir, f"{timestamp}.mp4")

    await file.download_to_drive(file_path)
    await update.message.reply_text("Видео получено и сохранено для обработки.")

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(MessageHandler(filters.VIDEO_NOTE, handle_video_note))

    print("Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
