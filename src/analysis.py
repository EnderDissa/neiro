import json
import cv2
import mediapipe as mp
import ffmpeg
import librosa
import numpy as np

async def calibrate_video(file_path, needs):
    EAR_THRESHOLD = 0
    blink_count = 0
    blink_rate = 0
    avg_dur = 0


    user_path = file_path[:-31]
    calibration_file = f"{user_path}calibration_data.json"
    audio_path = file_path.replace('.mp4', '.wav')
    (
        ffmpeg
        .input(file_path)
        .output(audio_path, format='wav', acodec='pcm_s16le', ac=1, ar='16000')
        .overwrite_output()
        .run()
    )
    if needs==2:
        needs=0
    EAR_THRESHOLD = 10 #TODO магия
    if needs==0:
        calibration_data = {
            'first_video': file_path,
            'second_video': "None",
            'EAR_THRESHOLD': EAR_THRESHOLD,
            'blink_count': blink_count,
            'blink_rate': blink_rate,
            'avg_dur': avg_dur
        }

        with open(calibration_file, 'w+') as f:
            json.dump(calibration_data, f, indent=4)
        return f"Первый этап калибровки завершён. Отправь мне ещё один кружок: нужно поморгать 5-10 раз"

    blink_count = 5 #TODO и тут магия
    blink_rate = 2
    avg_dur = 1
    if needs==1:
        with open(calibration_file, 'r') as f:
            calibration_data = json.load(f)

        calibration_data['second_video'] = file_path
        calibration_data['blink_count'] = blink_count
        calibration_data['blink_rate'] = blink_rate
        calibration_data['avg_dur'] = avg_dur

        with open(calibration_file, 'w+') as f:
            json.dump(calibration_data, f, indent=4)
        return f"Калибровка завершена. Теперь вы можете отправлять новые кружочки, они будут сравниваться с оригиналом. Чтобы откалибровать скрипт заново, пропишите команду /recalibrate"

async def analyze_video(file_path):
    audio_path = file_path.replace('.mp4', '.wav')
    (
        ffmpeg
        .input(file_path)
        .output(audio_path, format='wav', acodec='pcm_s16le', ac=1, ar='16000')
        .overwrite_output()
        .run()
    )
    try:
        audio, sr = librosa.load(audio_path, sr=16000)
        mfccs = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=13)
        mfcc_mean = np.mean(mfccs, axis=1)

        #TODO сравнивать с базовым профилем или ML моделью для детекции усталости


        cap = cv2.VideoCapture(file_path)
        mp_face_mesh = mp.solutions.face_mesh
        blink_count = 0
        frame_count = 0

        with mp_face_mesh.FaceMesh(min_detection_confidence=0.5, min_tracking_confidence=0.5) as face_mesh:
            while cap.isOpened():
                success, frame = cap.read()
                if not success:
                    break

                frame_count += 1
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = face_mesh.process(rgb_frame)

                #TODO Добавить реализацию вычисления Eye Aspect Ratio сюда.
        cap.release()
    except Exception as ex:
        return f"Анализ пока невозможен. Ошибка " + str(ex)

    return f"Анализ завершен. Морганий обнаружено: {blink_count}. Средние MFCC аудио: {mfcc_mean[:3]}"