import numpy as np

def calculate_fatigue(calibration, current):
    params = {
        'blink_rate': {'weight': 0.15, 'direction': 1},
        'avg_dur': {'weight': 0.20, 'direction': 1},
        'spectral_centroid_mean': {'weight': 0.05, 'direction': -1},
        'spectral_flux_mean': {'weight': 0.05, 'direction': 1},
        'rms_db_mean': {'weight': 0.10, 'direction': -1},
        'f0_mean_hz': {'weight': 0.10, 'direction': -1},
        'jitter_percent': {'weight': 0.10, 'direction': 1},
        'shimmer_db': {'weight': 0.10, 'direction': 1},
        'speech_rate_wpm': {'weight': 0.15, 'direction': -1}
    }

    fatigue_score = 0
    contributions = {}
    for param, info in params.items():
        diff = current[param] - calibration[param]
        contribution = (info['direction'] * diff) / abs(calibration[param])
        contributions[param] = contribution
        fatigue_score += info['weight'] * contribution

    fatigue_score = min(1, max(0, fatigue_score))

    return fatigue_score

def fatigue_to_absolute_kss(fatigue_score, kss_baseline):

    kss_change = fatigue_score * 4
    absolute_kss = kss_baseline + kss_change

    absolute_kss = round(min(max(1, absolute_kss), 9))

    return absolute_kss