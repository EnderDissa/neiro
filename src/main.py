import os
import json
from pathlib import Path
from datetime import datetime
# from telegram import Update
# from telegram.error import TimedOut
# from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes, CommandHandler
from src.blinks_analysis import *
from src.analysis import *
import telebot

from dotenv import load_dotenv

from src.fatigue_calc import calculate_fatigue
from src.sound_analysis import analyze_audio

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
VIDEO_DIR = Path.cwd() / "videos"
bot = telebot.TeleBot(TOKEN)

def load_user_calibration(user_id: int):
    calibration_file = VIDEO_DIR / str(user_id) / "calibration_data.json"
    if not calibration_file.exists():
        raise FileNotFoundError("Пользователь не прошёл калибровку")
    with open(calibration_file, "r") as f:
        data = json.load(f)
    threshold = data.get("EAR_THRESHOLD")
    fps = data.get("FPS")
    if threshold is None:
        raise KeyError("В calibration_data.json нет поля EAR_THRESHOLD")
    return threshold, fps

def needs_calibration(user_id: int) -> int:
    calibration_file = f"videos/{user_id}/calibration_data.json"
    if not os.path.exists(calibration_file):
        return 0
    with open(calibration_file, 'r') as f:
        calibration_data = json.load(f)
        if calibration_data['first_video']=="None": return 0
        if calibration_data['second_video']=="None": return 1
        return 2

@bot.message_handler(content_types=['video_note'])
def handle_video_note(message):
    user_id = message.from_user.id
    user_dir = os.path.join(VIDEO_DIR, str(user_id))
    needs = needs_calibration(user_id)
    if needs_calibration(user_id)<2:
        if not os.path.exists(user_dir):
            os.makedirs(user_dir)

        video = message.video_note
        file = bot.get_file(video.file_id)
        calibration_file = os.path.join(user_dir,"calibration_data.json")
        if needs==0:
            file_path = os.path.join(user_dir,"calibration_open.mp4")
            downloaded_bytes = bot.download_file(file.file_path)
            with open(file_path, 'wb') as f:
                f.write(downloaded_bytes)
            calibration_data = {
                'first_video': file_path,
                'second_video': "None",
                'EAR_THRESHOLD': 0,
                'blink_rate': 0,
                'avg_dur': 0,
                'FPS' : 0,
                'spectral_centroid_mean': 0,
                'spectral_flux_mean': 0,
                'rms_db_mean': 0,
                'f0_mean_hz': 0,
                'jitter_percent': 0,
                'shimmer_db': 0,
                'speech_rate_wpm': 0
            }
            with open(calibration_file, 'w+') as f:
                json.dump(calibration_data, f, indent=4)
            bot.send_message(message.chat.id,f"Первый этап калибровки завершён. Отправьте мне ещё один кружок: проговорите текст на протяжении 15-20 секунд")
        else:
            file_path = os.path.join(user_dir, "calibration_blink.mp4")
            print(file_path)
            bot.send_message(message.chat.id,f"Ожидайте. Финальный этап калибровки займёт некоторое время.")


            with open(calibration_file, 'r') as f:
                calibration_data = json.load(f)
                print(calibration_data)

            downloaded_bytes = bot.download_file(file.file_path)
            with open(file_path, 'wb') as f:
                f.write(downloaded_bytes)
            ear_threshold, fps = calibrate_threshold(os.path.join(user_dir, f"calibration_open.mp4"), os.path.join(user_dir, f"calibration_blink.mp4"))
            calibration_data['EAR_THRESHOLD'] = ear_threshold
            blink_count, blink_rate, avg_dur = analyze_video(file_path, ear_threshold, fps)
            calibration_data['second_video'] = file_path
            # calibration_data['blink_count'] = blink_count
            calibration_data['blink_rate'] = blink_rate
            calibration_data['avg_dur'] = avg_dur
            calibration_data['FPS'] = fps
            features = analyze_audio(os.path.join(user_dir, f"calibration_blink.mp4"))
            calibration_data['spectral_centroid_mean'] = features['spectral_centroid_mean']
            calibration_data['spectral_flux_mean'] = features['spectral_flux_mean']
            calibration_data['rms_db_mean'] = features['rms_db_mean']
            calibration_data['f0_mean_hz'] = features['f0_mean_hz']
            calibration_data['jitter_percent'] = features['jitter_percent']
            calibration_data['shimmer_db'] = features['shimmer_db']
            calibration_data['speech_rate_wpm'] = features['speech_rate_wpm']
            with open(calibration_file, 'w+') as f:
                json.dump(calibration_data, f, indent=4)
            bot.send_message(message.chat.id,f"Калибровка успешна. Теперь вы можете отправлять видео для проверки")
        return


    if not os.path.exists(user_dir):
        os.makedirs(user_dir)

    video_note = message.video_note
    file = bot.get_file(video_note.file_id)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(user_dir, f"{timestamp}.mp4")

    downloaded_bytes = bot.download_file(file.file_path)
    with open(file_path, 'wb') as f:
        f.write(downloaded_bytes)

    bot.send_message(message.chat.id,"Видео получено и сохранено. Начинаю анализ...")

    ear_threshold, fps = load_user_calibration(user_id)
    blink_count, blink_rate, avg_dur = analyze_video(file_path, ear_threshold, fps)
    features = analyze_audio(file_path)
    bot.send_message(
        message.chat.id,
        f"Полученные результаты:\n"
        f"Видеоанализ:\n"
        f"blink_rate = {blink_rate}\n"
        f"avg_dur = {avg_dur}\n\n"
        f"Аудиоанализ:\n"
        f"spectral_centroid_mean = {features['spectral_centroid_mean']}\n"
        f"spectral_flux_mean = {features['spectral_flux_mean']}\n"
        f"rms_db_mean = {features['rms_db_mean']}\n"
        f"f0_mean_hz = {features['f0_mean_hz']}\n"
        f"jitter_percent = {features['jitter_percent']}\n"
        f"shimmer_db = {features['shimmer_db']}\n"
        f"speech_rate_wpm = {features['speech_rate_wpm']}"
    )
    print('Вычисление усталости, где 1 - полная усталость')

    calibration_file = os.path.join(VIDEO_DIR, str(user_id), "calibration_data.json")
    with open(calibration_file, 'r') as f:
        calibration_json = json.load(f)

    calibration = {
        'blink_rate': calibration_json['blink_rate'],
        'avg_dur': calibration_json['avg_dur'],
        'FPS': calibration_json['FPS'],
        'spectral_centroid_mean': calibration_json['spectral_centroid_mean'],
        'spectral_flux_mean': calibration_json['spectral_flux_mean'],
        'rms_db_mean': calibration_json['rms_db_mean'],
        'f0_mean_hz': calibration_json['f0_mean_hz'],
        'jitter_percent': calibration_json['jitter_percent'],
        'shimmer_db': calibration_json['shimmer_db'],
        'speech_rate_wpm': calibration_json['speech_rate_wpm']
    }

    current = {
        'blink_rate': blink_rate,
        'avg_dur': avg_dur,
        'FPS': fps,
        'spectral_centroid_mean': features['spectral_centroid_mean'],
        'spectral_flux_mean': features['spectral_flux_mean'],
        'rms_db_mean': features['rms_db_mean'],
        'f0_mean_hz': features['f0_mean_hz'],
        'jitter_percent': features['jitter_percent'],
        'shimmer_db': features['shimmer_db'],
        'speech_rate_wpm': features['speech_rate_wpm']
    }

    # print(f"Ваша степень усталости - {calculate_fatigue(calibration, current)}")
    bot.send_message(message.chat.id,f"Ваша степень усталости - {calculate_fatigue(calibration, current)}")

    # bot.send_message(message.chat.id,f"Полученные результаты:\n blink_count = {blink_count} \n blink_rate = {blink_rate} \n avg_dur = {avg_dur}")

@bot.message_handler(commands=['recalibrate'])
def recalibrate(message):
    user_id = message.from_user.id

    if needs_calibration(user_id)>0:
        bot.send_message(message.chat.id,"Калибровка уже проводилась. Начнём заново: отправь два калибровочных видео")
        calibration_file = f"videos/{user_id}/calibration_data.json"
        os.remove(calibration_file)
    else:
        bot.send_message(message.chat.id,"Первичный запуск калибровки... Пожалуйста, отправьте калибровочное видео: нужно смотреть в камеру 5-10 секунд, не моргая.")


def main():

    # app = ApplicationBuilder().token(TOKEN).build()
    #
    # app.add_handler(MessageHandler(filters.VIDEO_NOTE, handle_video_note))
    #
    #
    # app.add_handler(CommandHandler("recalibrate", recalibrate))
    print("Бот запущен!")
    bot.polling()



if __name__ == "__main__":
    main()
