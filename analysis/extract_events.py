"""
Extract annotated event intervals from aligned data:
- Slices vibration data (xls) per event
- Slices audio (m4a/wav) per event
- Saves to analysis/events/ as numpy arrays and wav files
"""
import os, json, subprocess, wave
import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(BASE)
OUT_DIR = os.path.join(BASE, 'events')
os.makedirs(OUT_DIR, exist_ok=True)

ALIGN_JSON = os.path.join(PROJECT, 'vib_viz', 'alignment_2026-04-18-12-03-13.json')
VIB_DIR = os.path.join(PROJECT, 'vib_data')
WAV_DIR = os.path.join(PROJECT, 'vib_viz', 'audio_wav')

try:
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except ImportError:
    FFMPEG = 'ffmpeg'


def time_str_to_sec(ts):
    p = ts.split(':')
    return int(p[0]) * 3600 + int(p[1]) * 60 + float(p[2]) if len(p) == 3 else int(p[1]) * 60 + float(p[1])


with open(ALIGN_JSON, 'r', encoding='utf-8') as f:
    align = json.load(f)

events_catalog = []  # list of event metadata dicts

event_idx = 0
for audio_name, audio_sum in align.get('summary', {}).items():
    events = audio_sum.get('events', [])
    if not events:
        continue
    print(f'\n=== {audio_name} ===')
    wav_name = audio_name.replace('.m4a', '.wav')
    wav_path = os.path.join(WAV_DIR, wav_name)

    # Which group is this (for later location-based analysis)?
    if '19点59分' in audio_name:
        group = 'service_desk'
        group_desc = '服务台'
    elif '20点57分' in audio_name:
        group = 'ground_floor'
        group_desc = '地面(正后方)'
    else:
        group = 'other'
        group_desc = '其他'

    for ev_i, ev in enumerate(events):
        event_idx += 1
        event_id = f'ev{event_idx:02d}'
        ev_abs_start = time_str_to_sec(ev['absStartTime'])
        ev_abs_end = time_str_to_sec(ev['absEndTime'])
        duration = ev['durationSec']

        # --- Audio slice ---
        audio_start_sec = ev.get('audioFileStartSec')
        audio_end_sec = ev.get('audioFileEndSec')
        audio_clip_path = None
        if audio_start_sec is not None and audio_end_sec is not None and os.path.exists(wav_path):
            # Pad 1 second before/after for context
            pad = 1.0
            s = max(0, audio_start_sec - pad)
            e = audio_end_sec + pad
            clip_path = os.path.join(OUT_DIR, f'{event_id}_audio.wav')
            cmd = [FFMPEG, '-y', '-ss', str(s), '-t', str(e - s),
                   '-i', wav_path, '-acodec', 'pcm_s16le', clip_path]
            r = subprocess.run(cmd, capture_output=True)
            if r.returncode == 0:
                audio_clip_path = clip_path

        # --- Vibration slice (per xls) ---
        vib_slices = {}
        for xls_name, vib_range in ev.get('vibFiles', {}).items():
            xls_path = os.path.join(VIB_DIR, xls_name)
            if not os.path.exists(xls_path):
                print(f'   [MISS] {xls_name}')
                continue
            df = pd.read_excel(xls_path)
            t = df['Time (s)'].values
            # Pad 1 second
            pad = 1.0
            t_start = max(0, vib_range['vibStartSec'] - pad)
            t_end = vib_range['vibEndSec'] + pad
            mask = (t >= t_start) & (t <= t_end)
            sub = df[mask].reset_index(drop=True)
            if len(sub) == 0:
                continue
            npz_path = os.path.join(OUT_DIR, f'{event_id}_{xls_name.replace(".xls","").replace(" ","_").replace("(","").replace(")","")}.npz')
            np.savez(npz_path,
                     time=sub['Time (s)'].values,
                     ax=sub['Linear Acceleration x (m/s^2)'].values,
                     ay=sub['Linear Acceleration y (m/s^2)'].values,
                     az=sub['Linear Acceleration z (m/s^2)'].values,
                     abs_acc=sub['Absolute acceleration (m/s^2)'].values,
                     ev_start=vib_range['vibStartSec'],
                     ev_end=vib_range['vibEndSec'])
            vib_slices[xls_name] = {
                'path': npz_path,
                'n_samples': len(sub),
                'peak_abs': float(sub['Absolute acceleration (m/s^2)'].max()),
                'mean_abs': float(sub['Absolute acceleration (m/s^2)'].mean()),
                'rms_abs': float(np.sqrt((sub['Absolute acceleration (m/s^2)']**2).mean())),
            }

        catalog_entry = {
            'id': event_id,
            'type': ev['type'],
            'label': ev['label'],
            'group': group,
            'group_desc': group_desc,
            'audio_name': audio_name,
            'abs_start': ev['absStartTime'],
            'abs_end': ev['absEndTime'],
            'duration_sec': duration,
            'audio_clip': audio_clip_path,
            'audio_range_in_file': [audio_start_sec, audio_end_sec],
            'vib_slices': vib_slices,
            'note': ev.get('note'),
        }
        events_catalog.append(catalog_entry)
        xls_list = list(vib_slices.keys())
        print(f'   {event_id} {ev["absStartTime"]}~{ev["absEndTime"]} ({duration:.1f}s) [{group_desc}] xls={xls_list}')
        for xname, s in vib_slices.items():
            print(f'     {xname}: peak={s["peak_abs"]:.3f}, mean={s["mean_abs"]:.4f}, rms={s["rms_abs"]:.4f}  ({s["n_samples"]} samples)')

catalog_path = os.path.join(OUT_DIR, 'events_catalog.json')
with open(catalog_path, 'w', encoding='utf-8') as f:
    json.dump(events_catalog, f, indent=2, ensure_ascii=False)
print(f'\n[OK] Extracted {len(events_catalog)} events -> {OUT_DIR}')
print(f'Catalog: {catalog_path}')
