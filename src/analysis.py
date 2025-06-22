import cv2
import mediapipe as mp
import ffmpeg
import librosa
import numpy as np

async def analyze_video(file_path):
    audio_path = file_path.replace('.mp4', '.wav')
    (
        ffmpeg
        .input(file_path)
        .output(audio_path, format='wav', acodec='pcm_s16le', ac=1, ar='16000')
        .overwrite_output()
        .run()
    )

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

    return f"Анализ завершен. Морганий обнаружено: {blink_count}. Средние MFCC аудио: {mfcc_mean[:3]}"