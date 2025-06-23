from pathlib import Path

import cv2
import numpy as np
import mediapipe as mp
import time
import matplotlib.pyplot as plt


LEFT_EYE_INDICES   = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_INDICES  = [263, 385, 387, 362, 380, 373]

async def compute_ear(landmarks, eye_idxs):
    pts = np.array([landmarks[i] for i in eye_idxs])
    A = np.linalg.norm(pts[1] - pts[5])
    B = np.linalg.norm(pts[2] - pts[4])
    C = np.linalg.norm(pts[0] - pts[3])
    return (A + B) / (2.0 * C)


async def extract_ear_sequence(video_path):
    mp_face = mp.solutions.face_mesh
    with mp_face.FaceMesh(
        static_image_mode=False,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    ) as face_mesh:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise IOError(f"Не удалось открыть видео: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        ear_values = []

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            h, w = frame.shape[:2]
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(rgb)
            if results.multi_face_landmarks:
                lm = results.multi_face_landmarks[0].landmark
                pts = [(int(p.x * w), int(p.y * h)) for p in lm]
                ear_l = compute_ear(pts, LEFT_EYE_INDICES)
                ear_r = compute_ear(pts, RIGHT_EYE_INDICES)
                ear_values.append((ear_l + ear_r) / 2.0)
        cap.release()
    return ear_values, fps


async def plot_ear_histogram(ear_open, ear_blink, threshold):
    plt.figure(figsize=(8,4))
    plt.hist(ear_open, bins=50, alpha=0.6, label='Open')
    plt.hist(ear_blink, bins=50, alpha=0.6, label='Blink')
    plt.axvline(threshold, color='red', linestyle='--', label=f'TH={threshold:.3f}')
    plt.legend()
    plt.title('Калибровка порога EAR')
    plt.xlabel('EAR')
    plt.ylabel('Частота')
    plt.show()


async def calibrate_threshold(open_video, blink_video):
    print(open_video,blink_video)
    ear_open, _ = extract_ear_sequence(open_video)
    ear_blink, fps = extract_ear_sequence(blink_video)

    mean_open = np.mean(ear_open)
    mean_closed = np.min(ear_blink)

    ear_threshold = (mean_open + mean_closed) / 2.0
    print(f"[CALIBRATION] mean_open={mean_open:.3f}, mean_closed={mean_closed:.3f}, EAR_THRESHOLD={ear_threshold:.3f}")

    return ear_threshold, fps


async def analyze_video(video_path, ear_threshold, fps, consec_frames=2):
    mp_face = mp.solutions.face_mesh
    with mp_face.FaceMesh(
        static_image_mode=False,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    ) as face_mesh:
        cap = cv2.VideoCapture(video_path)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if not cap.isOpened():
            raise IOError(f"Не удалось открыть видео: {video_path}")

        blink_count = 0
        consec = 0
        blink_start = None
        durations = []
        frame_idx = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            h, w = frame.shape[:2]
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(rgb)

            if results.multi_face_landmarks:
                lm = results.multi_face_landmarks[0].landmark
                pts = [(int(p.x * w), int(p.y * h)) for p in lm]
                ear = np.mean([compute_ear(pts, LEFT_EYE_INDICES), compute_ear(pts, RIGHT_EYE_INDICES)])

                if ear < ear_threshold:
                    consec += 1
                    if consec == consec_frames:
                        blink_start = frame_idx
                else:
                    if blink_start is not None:
                        frames = frame_idx - blink_start
                        duration_ms = frames * (1000.0 / fps)
                        durations.append(duration_ms)
                        blink_count += 1
                        print(f"[BLINK] #{blink_count}: duration {duration_ms:.1f} ms")
                    consec = 0
                    blink_start = None
            frame_idx += 1

        cap.release()

    duration_sec = frame_count / fps if fps > 0 else 0
    duration_min = duration_sec / 60
    blink_rate = blink_count / duration_min if duration_min > 0 else 0
    avg_dur = np.mean(durations) if durations else 0

    print(f"[ANALYSIS] Blink count: {blink_count}")
    print(f"[ANALYSIS] Blink rate: {blink_rate:.3f} blinks/min")
    print(f"[ANALYSIS] Avg duration: {avg_dur:.3f} ms")

    return blink_count, blink_rate, avg_dur


if __name__ == '__main__':
    open_video = Path.cwd().parent / 'videos/open_eyes.mp4' # 5-10 секунд
    # blink_video = Path.cwd().parent / 'videos/blink_sequence.mp4' # 5-10 раз
    blink_video = Path.cwd().parent / 'videos/video3.mp4'

    # Шаг 1: Калибровка
    EAR_THRESHOLD, fps = calibrate_threshold(open_video, blink_video)
    analyze_video(blink_video, EAR_THRESHOLD, fps)
