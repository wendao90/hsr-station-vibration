"""
Extract user-marked clean_bgnd segments + paired train_pass events.
Compute proper centered RMS and PSD for each, enabling rigorous comparison:
  - Clean baseline RMS (ambient + sensor noise)
  - Train pass RMS (above baseline)
  - Spectral signature: peaks vs flat-noise pattern
"""
import os, json
import numpy as np
import pandas as pd
from scipy import signal

BASE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(BASE)
OUT_DIR = os.path.join(BASE, 'events')
VIB_DIR = os.path.join(PROJECT, 'vib_data')
os.makedirs(OUT_DIR, exist_ok=True)

ALIGN_JSON = os.path.join(PROJECT, 'vib_viz', 'alignment_2026-04-18-16-29-22.json')
SR = 99.43


def time_str_to_sec(ts):
    p = ts.split(':')
    return int(p[0]) * 3600 + int(p[1]) * 60 + float(p[2]) if len(p) == 3 else int(p[1]) * 60 + float(p[1])


def compute_centered_stats(abs_acc, ax, ay, az, sr=SR):
    """Compute RMS etc on the centered (mean-removed) acceleration."""
    if len(abs_acc) < 10:
        return None
    centered = abs_acc - np.mean(abs_acc)
    s = {
        'n': len(abs_acc),
        'rms_centered': float(np.sqrt(np.mean(centered**2))),
        'rms_raw': float(np.sqrt(np.mean(abs_acc**2))),
        'peak': float(np.max(abs_acc)),
        'peak_centered': float(np.max(np.abs(centered))),
        'mean': float(np.mean(abs_acc)),
    }
    # linear vector magnitude
    lin = np.sqrt(ax**2 + ay**2 + az**2)
    s['lin_rms_centered'] = float(np.sqrt(np.mean((lin - np.mean(lin))**2)))
    # x, y, z component RMS (centered)
    for a, lbl in [(ax,'x'), (ay,'y'), (az,'z')]:
        s[f'rms_{lbl}'] = float(np.sqrt(np.mean((a - np.mean(a))**2)))
    # Welch PSD
    if len(centered) >= 64:
        nperseg = min(256, len(centered))
        f, psd = signal.welch(centered, fs=sr, nperseg=nperseg)
        s['psd_freqs'] = f
        s['psd'] = psd
        idx = np.argmax(psd)
        s['dom_freq'] = float(f[idx])
        # Peak to mean (above 5 Hz, below 45 Hz - avoid DC and aliasing)
        m = (f >= 5) & (f <= 45)
        if np.any(m):
            s['peak_mean_ratio'] = float(psd[m].max() / psd[m].mean())
        def bp(a, b):
            m = (f >= a) & (f < b)
            return float(np.trapz(psd[m], f[m])) if np.any(m) else 0
        s['pwr_0_5hz']   = bp(0, 5)
        s['pwr_5_15hz']  = bp(5, 15)
        s['pwr_15_30hz'] = bp(15, 30)
        s['pwr_30_50hz'] = bp(30, 50)
    return s


with open(ALIGN_JSON, 'r', encoding='utf-8') as f:
    align = json.load(f)

catalog = []

# XLS metadata cache
_xls_cache = {}
def load_xls(name):
    if name in _xls_cache: return _xls_cache[name]
    path = os.path.join(VIB_DIR, name)
    if not os.path.exists(path): return None
    df = pd.read_excel(path)
    _xls_cache[name] = df
    return df

# For each audio, for each event (clean_bgnd or train_pass) with xls mapping, extract
for audio_name, s in align.get('summary', {}).items():
    if '19点59分' in audio_name:
        loc = 'service_desk'
        loc_desc = '服务台'
    elif '20点57分' in audio_name:
        loc = 'ground_floor'
        loc_desc = '地面(正后方)'
    else:
        loc = 'other'; loc_desc = '其他'

    for ev in s.get('events', []):
        vib_files = ev.get('vibFiles', {})
        if not vib_files:
            continue
        for xls_name, rng in vib_files.items():
            df = load_xls(xls_name)
            if df is None: continue
            t = df['Time (s)'].values
            mask = (t >= rng['vibStartSec']) & (t <= rng['vibEndSec'])
            if np.sum(mask) < 10: continue
            abs_acc = df['Absolute acceleration (m/s^2)'].values[mask]
            ax = df['Linear Acceleration x (m/s^2)'].values[mask]
            ay = df['Linear Acceleration y (m/s^2)'].values[mask]
            az = df['Linear Acceleration z (m/s^2)'].values[mask]
            stats = compute_centered_stats(abs_acc, ax, ay, az)
            if stats is None: continue

            kind = ev['type']
            tag = f"{kind}_{len(catalog):03d}"
            npz_path = os.path.join(OUT_DIR, f'clean_{tag}.npz')
            np.savez(npz_path, time=t[mask], abs_acc=abs_acc, ax=ax, ay=ay, az=az)
            entry = {
                'tag': tag,
                'type': kind,
                'label': ev['label'],
                'location': loc, 'location_desc': loc_desc,
                'audio': audio_name, 'xls': xls_name,
                'abs_start': ev['absStartTime'], 'abs_end': ev['absEndTime'],
                'duration': ev['durationSec'],
                'vib_start_sec': rng['vibStartSec'], 'vib_end_sec': rng['vibEndSec'],
                'rms_centered': stats['rms_centered'],
                'rms_raw': stats['rms_raw'],
                'peak': stats['peak'],
                'peak_centered': stats['peak_centered'],
                'dom_freq': stats.get('dom_freq'),
                'peak_mean_ratio': stats.get('peak_mean_ratio'),
                'pwr_0_5hz': stats.get('pwr_0_5hz', 0),
                'pwr_5_15hz': stats.get('pwr_5_15hz', 0),
                'pwr_15_30hz': stats.get('pwr_15_30hz', 0),
                'pwr_30_50hz': stats.get('pwr_30_50hz', 0),
                'rms_x': stats.get('rms_x'), 'rms_y': stats.get('rms_y'), 'rms_z': stats.get('rms_z'),
                'npz_path': npz_path,
            }
            catalog.append(entry)

df_out = pd.DataFrame(catalog)
print(f'Total segments extracted: {len(df_out)}')
print(f'  clean_bgnd: {(df_out["type"]=="clean_bgnd").sum()}')
print(f'  train_pass: {(df_out["type"]=="train_pass").sum()}')
print()

# Statistics comparison: clean_bgnd vs train_pass per location
for loc in ['service_desk', 'ground_floor']:
    sub = df_out[df_out['location'] == loc]
    if len(sub) == 0: continue
    print(f'--- {loc} ---')
    for kind in ['clean_bgnd', 'train_pass']:
        s2 = sub[sub['type'] == kind]
        if len(s2) == 0: continue
        print(f'  {kind:12s}  n={len(s2):2d}  RMS_centered={s2["rms_centered"].mean():.4f}±{s2["rms_centered"].std():.4f}  ' +
              f'peak_mean_ratio={s2["peak_mean_ratio"].mean():.2f}  dom_freq_median={s2["dom_freq"].median():.1f}Hz')
    print()

df_out.to_csv(os.path.join(BASE, 'clean_segments_summary.csv'), index=False, encoding='utf-8-sig')
print(f'[OK] Saved: {os.path.join(BASE, "clean_segments_summary.csv")}')
