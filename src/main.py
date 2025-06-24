import os
import json
from pathlib import Path
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes, CommandHandler
from src.blinks_analysis import *
from src.analysis import *

# from dotenv import load_dotenv
#
# load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
VIDEO_DIR = Path.cwd() / "videos"


def needs_calibration(user_id: int) -> int:
    calibration_file = f"videos/{user_id}/calibration_data.json"
    if not os.path.exists(calibration_file):
        return 0
    with open(calibration_file, 'r') as f:
        calibration_data = json.load(f)
        if calibration_data['first_video']=="None": return 0
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
        calibration_file = os.path.join(user_dir,"calibration_data.json")
        if needs==0:
            file_path = os.path.join(user_dir,"calibration_open.mp4")
            await file.download_to_drive(file_path)
            calibration_data = {
                'first_video': file_path,
                'second_video': "None",
                'EAR_THRESHOLD': 0,
                'blink_count': 0,
                'blink_rate': 0,
                'avg_dur': 0
            }
            with open(calibration_file, 'w+') as f:
                json.dump(calibration_data, f, indent=4)
            await update.message.reply_text(f"Первый этап калибровки завершён. Отправьте мне ещё один кружок: нужно поморгать 5-10 раз")
        else:
            file_path = os.path.join(user_dir, "calibration_blink.mp4")
            print(file_path)
            await update.message.reply_text(f"Ожидайте. Финальный этап калибровки займёт некоторое время.")


            with open(calibration_file, 'r') as f:
                calibration_data = json.load(f)
                print(calibration_data)

            await file.download_to_drive(file_path)
            ear_threshold, fps = calibrate_threshold(os.path.join(user_dir, f"calibration_open.mp4"), os.path.join(user_dir, f"calibration_blink.mp4"))
            calibration_data['EAR_THRESHOLD'] = ear_threshold
            blink_count, blink_rate, avg_dur = analyze_video(file_path, ear_threshold, fps)
            calibration_data['second_video'] = file_path
            calibration_data['blink_count'] = blink_count
            calibration_data['blink_rate'] = blink_rate
            calibration_data['avg_dur'] = avg_dur
            with open(calibration_file, 'w+') as f:
                json.dump(calibration_data, f, indent=4)
            await update.message.reply_text(f"Калибровка успешна. Теперь вы можете отправлять видео для проверки")
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
        calibration_file = f"videos/{user_id}/calibration_data.json"
        os.remove(calibration_file)
    else:
        await update.message.reply_text("Первичный запуск калибровки... Пожалуйста, отправьте калибровочное видео: нужно смотреть в камеру 5-10 секунд, не моргая.")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.VIDEO_NOTE, handle_video_note))


    app.add_handler(CommandHandler("recalibrate", recalibrate))

    print("Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
