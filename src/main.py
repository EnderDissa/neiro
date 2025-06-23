import os
import json
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes, CommandHandler
from src.analysis import *

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
VIDEO_DIR = "./videos"


def needs_calibration(user_id: int) -> int:
    calibration_file = f"videos/{user_id}/calibration_data.json"
    if not os.path.exists(calibration_file):
        return 0
    with open(calibration_file, 'r') as f:
        calibration_data = json.load(f)
        if not 'EAR_THRESHOLD' in calibration_data: return 0
        if calibration_data['second_video']=="None": return 1
        return 2

async def handle_video_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_dir = os.path.join(VIDEO_DIR, str(user_id))
    needs = needs_calibration(user_id)
    if needs_calibration(user_id)<2:
        if not os.path.exists(user_dir):
            os.makedirs(user_dir)

        video = update.message.video_note
        file = await context.bot.get_file(video.file_id)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = os.path.join(user_dir, f"calibration_{timestamp}.mp4")

        await file.download_to_drive(file_path)

        calibration_result = await calibrate_video(file_path, needs)

        await update.message.reply_text(f"{calibration_result}")
        return


    if not os.path.exists(user_dir):
        os.makedirs(user_dir)

    video_note = update.message.video_note
    file = await context.bot.get_file(video_note.file_id)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(user_dir, f"{timestamp}.mp4")

    await file.download_to_drive(file_path)
    await update.message.reply_text("Видео получено и сохранено. Начинаю анализ...")

    result = await analyze_video(file_path)

    await update.message.reply_text(result)


async def recalibrate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if needs_calibration(user_id)>0:
        await update.message.reply_text("Калибровка уже проводилась. Начнём заново: отправь два калибровочных видео")
    else:
        await update.message.reply_text("Первичный запуск калибровки... Пожалуйста, отправьте калибровочное видео: нужно смотреть в камеру 5-10 секунд, не моргая.")
    calibration_file = f"videos/{user_id}/calibration_data.json"
    os.remove(calibration_file)
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(MessageHandler(filters.VIDEO_NOTE, handle_video_note))


    app.add_handler(CommandHandler("recalibrate", recalibrate))

    print("Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
