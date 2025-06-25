import os
import numpy as np
import librosa
import scipy.signal as sps
import parselmouth
from parselmouth.praat import call
import speech_recognition as sr_module
import subprocess
import soundfile as sf
import matplotlib.pyplot as plt

def load_audio_from_video(video_path, sr_target=22050):
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Видео-файл не найден: {video_path}")

    wav_path = "temp_audio.wav"
    cmd = [
        "ffmpeg",
        "-y",
        "-i", video_path,
        "-vn",
        "-ac", "1",
        "-ar", str(sr_target),
        "-f", "wav",
        wav_path
    ]

    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg error:\n{result.stderr.decode('utf-8')}")

    y, sr = librosa.load(wav_path, sr=sr_target)
    os.remove(wav_path)
    return y, sr

def bandpass_filter(y, sr, low=80, high=8000, order=4):
    nyq = sr / 2
    b, a = sps.butter(order, [low/nyq, high/nyq], btype='band')
    return sps.filtfilt(b, a, y)

def apply_vad(y, sr, top_db=30):
    intervals = librosa.effects.split(y, top_db=top_db)
    return np.concatenate([y[start:end] for start, end in intervals])


def compute_spectral_features(y, sr, frame_length=2048, hop_length=512):
    centroids = librosa.feature.spectral_centroid(y=y, sr=sr,
                                                  n_fft=frame_length,
                                                  hop_length=hop_length)[0]
    S = np.abs(librosa.stft(y, n_fft=frame_length, hop_length=hop_length))
    S_norm = S / np.sum(S, axis=0, keepdims=True)
    flux = np.sqrt(np.sum((np.diff(S_norm, axis=1))**2, axis=0))
    flux = np.concatenate([[0], flux])
    return centroids, flux

def compute_rms_db(y, frame_length=2048, hop_length=512):
    rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
    rms_db = librosa.amplitude_to_db(rms, ref=np.max)
    return rms_db

def compute_pitch_jitter_shimmer(y, sr):
    snd = parselmouth.Sound(y, sampling_frequency=sr)
    pitch = snd.to_pitch()
    f0_values = pitch.selected_array['frequency']
    f0_values = f0_values[f0_values > 0]
    f0_mean = np.mean(f0_values) if len(f0_values) else 0

    point_process = call(snd, "To PointProcess (periodic, cc)", 75, 500)
    jitter_local = call(point_process, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3)  # %
    shimmer_local = call([snd, point_process], "Get shimmer (local)", 0, 0, 0.0001, 0.02, 1.3, 1.6)  # dB

    return f0_mean, jitter_local, shimmer_local

def compute_speech_rate(y, sr, language):
    wav = "temp_sr.wav"
    sf.write(wav, y, sr)

    recognizer = sr_module.Recognizer()
    with sr_module.AudioFile(wav) as source:
        audio = recognizer.record(source)
    try:
        text = recognizer.recognize_google(audio, language=language)
    except Exception:
        text = ""
    os.remove(wav)

    words = len(text.split())
    duration_min = len(y) / sr / 60.0
    wpm = words / duration_min if duration_min > 0 else 0.0
    return wpm

def analyze_audio(video_file):
    y, sr = load_audio_from_video(video_file)
    y = bandpass_filter(y, sr)
    y = apply_vad(y, sr)

    centroids, flux = compute_spectral_features(y, sr)
    rms_db = compute_rms_db(y)
    f0_mean, jitter_local, shimmer_local = compute_pitch_jitter_shimmer(y, sr)
    wpm = compute_speech_rate(y, sr, language="ru-RU")

    features = {
        'spectral_centroid_mean': float(np.mean(centroids)),
        'spectral_flux_mean': float(np.mean(flux)),
        'rms_db_mean': float(np.mean(rms_db)),
        'f0_mean_hz': float(f0_mean),
        'jitter_percent': float(jitter_local),
        'shimmer_db': float(shimmer_local),
        'speech_rate_wpm': float(wpm)
    }

    # plot(centroids, flux, sr, rms_db)

    return features

def plot(cent, flux, sr, rms_db):
    hop_length = 512
    times = np.arange(len(cent)) * hop_length / sr

    plt.figure(figsize=(10, 6))
    plt.subplot(3, 1, 1)
    plt.plot(times, cent, label='Centroid')
    plt.xlabel('Время (с)')
    plt.ylabel('Частота (Гц)')
    plt.legend()
    plt.title('Spectral Centroid')
    plt.subplot(3, 1, 2)
    plt.plot(times, flux, label='Flux')
    plt.legend()
    plt.subplot(3, 1, 3)
    plt.plot(times, rms_db, label='RMS dB')
    plt.legend()
    plt.title('Loudness')
    plt.tight_layout()
    plt.show()

    return

if __name__ == '__main__':
    video = '/Users/admin/ITMO/Projects/Neurotechnology and biometrics/src/videos/407154220/20250625_052140.mp4'
    feats = analyze_audio(video)
    for k, v in feats.items():
        print(f"{k}: {v}")