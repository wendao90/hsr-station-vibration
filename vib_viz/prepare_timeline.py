"""
Generate timeline_data.json: waveform peaks for all audio files + acceleration peaks for all xls files.
All aligned to absolute time axis (seconds since midnight).
"""
import json, os, subprocess, wave, struct
import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
VIB_DIR = os.path.join(PROJECT_DIR, "vib_data")
SOUND_DIR = os.path.join(PROJECT_DIR, "sound")

try:
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except ImportError:
    FFMPEG = "ffmpeg"

PIXELS_PER_SEC_AUDIO = 4   # audio: 4 bins/sec (enough for waveform shape)
PIXELS_PER_SEC_VIB = 50    # vib: 50 bins/sec (enough to see knock impulses ~0.1s wide)
PIXELS_PER_SEC = PIXELS_PER_SEC_AUDIO  # back-compat

def time_str_to_sec(ts):
    """HH:MM:SS -> seconds since midnight"""
    p = ts.split(':')
    return int(p[0]) * 3600 + int(p[1]) * 60 + (int(p[2]) if len(p) > 2 else 0)

def process_audio_files():
    """Generate peaks from the pre-converted WAV files in audio_wav/.
    This ensures browser playback duration matches our displayed waveform exactly."""
    import re, time as _time
    WAV_DIR = os.path.join(BASE_DIR, 'audio_wav')
    results = []
    for f in sorted(os.listdir(SOUND_DIR)):
        if not f.endswith('.m4a'):
            continue
        m4a_path = os.path.join(SOUND_DIR, f)
        wav_name = f.replace('.m4a', '.wav')
        wav_path = os.path.join(WAV_DIR, wav_name)
        if not os.path.exists(wav_path):
            print(f'  [SKIP] WAV missing for {f} - run convert_audio.py first')
            continue
        m = re.search(r'(\d+)点(\d+)分', f)
        if not m:
            continue
        start_sec = int(m.group(1)) * 3600 + int(m.group(2)) * 60

        try:
            wf = wave.open(wav_path, 'rb')
            sr = wf.getframerate()
            nframes = wf.getnframes()
            raw = wf.readframes(nframes)
            wf.close()
            samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0

            # Browser-decode-based duration. Some m4a files may fail mid-file in Chrome;
            # by using WAV as the playback source, duration is exact and reliable.
            # But we still need to account for the possibility that Chrome couldn't decode
            # some part. Since we now serve WAV directly, Chrome gets full content.
            duration = nframes / sr
            num_bins = max(1, int(duration * PIXELS_PER_SEC))
            spb = max(1, len(samples) // num_bins)
            actual_bins = len(samples) // spb
            # Effective duration covered by bins (exactly)
            effective_duration = actual_bins * spb / sr

            pos, neg = [], []
            for i in range(actual_bins):
                chunk = samples[i * spb:(i + 1) * spb]
                pos.append(round(float(np.max(chunk)), 3))
                neg.append(round(float(np.min(chunk)), 3))

            results.append({
                'name': f,  # keep m4a name as ID, but playback uses WAV (handled in JS)
                'wavName': wav_name,
                'startSec': start_sec,
                'endSec': start_sec + effective_duration,
                'duration': effective_duration,  # full precision, exactly matches bins
                'pos': pos,
                'neg': neg,
            })
            print(f'  Audio: {f}  {effective_duration:.3f}s  {actual_bins} bins  spb={spb}')
        except Exception as e:
            print(f'  Audio ERROR: {f}: {e}')

    return results

def process_vib_files():
    import time as _time
    results = []
    xls_files = [f for f in sorted(os.listdir(VIB_DIR), key=lambda x: os.path.getmtime(os.path.join(VIB_DIR, x)))
                 if f.endswith('.xls') and not f.startswith('.pending') and os.path.getsize(os.path.join(VIB_DIR, f)) > 0]

    for f in xls_files:
        path = os.path.join(VIB_DIR, f)
        mtime = os.path.getmtime(path)
        mt = _time.localtime(mtime)
        end_sec = mt.tm_hour * 3600 + mt.tm_min * 60 + mt.tm_sec

        df = pd.read_excel(path)
        abs_col = 'Absolute acceleration (m/s^2)'
        x_col = 'Linear Acceleration x (m/s^2)'
        y_col = 'Linear Acceleration y (m/s^2)'
        z_col = 'Linear Acceleration z (m/s^2)'
        duration = df['Time (s)'].max()
        start_sec = end_sec - duration

        num_bins = max(1, int(duration * PIXELS_PER_SEC_VIB))
        # Ensure spb >= 2 so min/max envelope differs and draws visibly
        spb = max(2, len(df) // num_bins)
        actual_bins = len(df) // spb

        abs_peaks = []
        # For each axis: record both max positive and max negative (most extreme values)
        x_pos, x_neg = [], []
        y_pos, y_neg = [], []
        z_pos, z_neg = [], []
        for i in range(actual_bins):
            s = i * spb
            e = (i + 1) * spb
            abs_peaks.append(round(float(df[abs_col].iloc[s:e].max()), 4))
            xc = df[x_col].iloc[s:e]
            yc = df[y_col].iloc[s:e]
            zc = df[z_col].iloc[s:e]
            x_pos.append(round(float(xc.max()), 4))
            x_neg.append(round(float(xc.min()), 4))
            y_pos.append(round(float(yc.max()), 4))
            y_neg.append(round(float(yc.min()), 4))
            z_pos.append(round(float(zc.max()), 4))
            z_neg.append(round(float(zc.min()), 4))

        results.append({
            'name': f,
            'startSec': round(start_sec, 1),
            'endSec': round(end_sec, 1),
            'duration': round(duration, 1),
            'peaks': abs_peaks,
            'xPos': x_pos, 'xNeg': x_neg,
            'yPos': y_pos, 'yNeg': y_neg,
            'zPos': z_pos, 'zNeg': z_neg,
        })
        print(f'  Vib: {f}  {duration:.0f}s  {actual_bins} bins')

    return results

def main():
    print('Processing audio files...')
    audio = process_audio_files()
    print(f'\nProcessing vibration files...')
    vib = process_vib_files()

    data = {'audio': audio, 'vib': vib, 'pixelsPerSec': PIXELS_PER_SEC}
    out = os.path.join(BASE_DIR, 'timeline_data.json')
    with open(out, 'w') as f:
        json.dump(data, f)
    sz = os.path.getsize(out)
    print(f'\nSaved timeline_data.json ({sz/1024:.0f} KB)')

if __name__ == '__main__':
    main()
