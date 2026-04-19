"""
Extract additional data categories beyond the already-annotated train-pass events:
- Platform (站台): g(15), g(16) — full duration as scene
- Subway on-board (地铁车内): g(17), g(18) — full duration as scene
- Baseline (静默段): first 30s of each xls (or whatever is available before activity)
- Knock references (敲击人致振动): short windows around knock times (from alignment pairs)

Outputs:
- scene_catalog.json: metadata for all scene segments
- NPZ files per scene segment in events/ dir
- Also computes statistics per category (peak, RMS, SNR vs sensor noise floor, PSD)
"""
import os, json
import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(BASE)
OUT_DIR = os.path.join(BASE, 'events')
VIB_DIR = os.path.join(PROJECT, 'vib_data')
os.makedirs(OUT_DIR, exist_ok=True)

# Additional categories: {xls_file: (scene_type, scene_desc)}
ADDITIONAL = {
    'g (15).xls': ('platform',     '站台(候车)'),
    'g (16).xls': ('platform',     '站台(靠近轨道/上车)'),
    'g (17)地铁数据_杭州西站出发.xls': ('subway_onboard', '地铁车内(出发)'),
    'g (18)地铁数据_到海创园.xls':    ('subway_onboard', '地铁车内(到站)'),
}

def compute_stats(abs_acc, ax, ay, az, sr=99.43, freq_bands=None):
    from scipy import signal
    stats = {}
    stats['n'] = len(abs_acc)
    stats['peak'] = float(np.max(abs_acc))
    stats['rms'] = float(np.sqrt(np.mean(abs_acc**2)))
    stats['mean'] = float(np.mean(abs_acc))
    stats['std'] = float(np.std(abs_acc))
    # Linear (gravity-removed) magnitude
    lin_mag = np.sqrt(ax**2 + ay**2 + az**2)
    stats['lin_rms'] = float(np.sqrt(np.mean(lin_mag**2)))
    stats['lin_peak'] = float(np.max(lin_mag))

    # PSD on centered abs_acc
    if len(abs_acc) >= 64:
        nperseg = min(256, len(abs_acc))
        centered = abs_acc - np.mean(abs_acc)
        freqs, psd = signal.welch(centered, fs=sr, nperseg=nperseg)
        stats['psd_freqs'] = freqs
        stats['psd'] = psd
        idx = np.argmax(psd)
        stats['dominant_freq'] = float(freqs[idx])
        def bp(f0, f1):
            m = (freqs >= f0) & (freqs < f1)
            return float(np.trapz(psd[m], freqs[m])) if np.any(m) else 0
        stats['pwr_0_5hz'] = bp(0, 5)
        stats['pwr_5_15hz'] = bp(5, 15)
        stats['pwr_15_30hz'] = bp(15, 30)
        stats['pwr_30plus'] = bp(30, freqs.max())
    return stats


scene_entries = []
scene_idx = 0

# --- Process additional full-segment scenes ---
for xls_name, (scene_type, scene_desc) in ADDITIONAL.items():
    scene_idx += 1
    xls_path = os.path.join(VIB_DIR, xls_name)
    if not os.path.exists(xls_path):
        print(f'[MISS] {xls_name}')
        continue
    df = pd.read_excel(xls_path)
    t = df['Time (s)'].values
    abs_acc = df['Absolute acceleration (m/s^2)'].values
    ax = df['Linear Acceleration x (m/s^2)'].values
    ay = df['Linear Acceleration y (m/s^2)'].values
    az = df['Linear Acceleration z (m/s^2)'].values

    # Save as NPZ
    npz_id = f'scene_{scene_idx:02d}_{scene_type}'
    npz_path = os.path.join(OUT_DIR, f'{npz_id}.npz')
    np.savez(npz_path, time=t, ax=ax, ay=ay, az=az, abs_acc=abs_acc)
    stats = compute_stats(abs_acc, ax, ay, az)

    entry = {
        'scene_id': npz_id,
        'scene_type': scene_type,
        'scene_desc': scene_desc,
        'source_xls': xls_name,
        'duration_sec': float(t.max() - t.min()),
        'peak': stats['peak'],
        'rms': stats['rms'],
        'mean': stats['mean'],
        'std': stats['std'],
        'lin_peak': stats['lin_peak'],
        'lin_rms': stats['lin_rms'],
        'dominant_freq': stats.get('dominant_freq'),
        'pwr_0_5hz': stats.get('pwr_0_5hz', 0),
        'pwr_5_15hz': stats.get('pwr_5_15hz', 0),
        'pwr_15_30hz': stats.get('pwr_15_30hz', 0),
        'pwr_30plus': stats.get('pwr_30plus', 0),
        'npz_path': npz_path,
    }
    scene_entries.append(entry)
    print(f'{npz_id} [{scene_desc}]  peak={stats["peak"]:.3f}  rms={stats["rms"]:.4f}  dom={stats.get("dominant_freq",0):.1f}Hz  dur={entry["duration_sec"]:.1f}s')

# --- Baseline segments (first 10s of each major xls, where usually quiet) ---
BASELINE_SOURCES = {
    'g (1).xls':  ('服务台', 'service_desk'),
    'g (5).xls':  ('服务台', 'service_desk'),
    'g (9).xls':  ('服务台', 'service_desk'),
    'g (10).xls': ('地面',   'ground_floor'),
    'g (12).xls': ('地面',   'ground_floor'),
    'g (15).xls': ('站台',   'platform'),
    'g (17)地铁数据_杭州西站出发.xls': ('地铁车内', 'subway_onboard'),
}

for xls_name, (loc_desc, loc_type) in BASELINE_SOURCES.items():
    scene_idx += 1
    xls_path = os.path.join(VIB_DIR, xls_name)
    if not os.path.exists(xls_path):
        continue
    df = pd.read_excel(xls_path)
    t = df['Time (s)'].values
    # Take first 10s as baseline (for service desk / ground - usually quiet at start)
    # For subway/platform it's the beginning of journey which may or may not be quiet
    # We just take the first 5-10 seconds and call it "baseline sample"
    bl_dur = min(10.0, t.max())
    mask = t <= bl_dur
    abs_acc = df['Absolute acceleration (m/s^2)'].values[mask]
    ax = df['Linear Acceleration x (m/s^2)'].values[mask]
    ay = df['Linear Acceleration y (m/s^2)'].values[mask]
    az = df['Linear Acceleration z (m/s^2)'].values[mask]
    if len(abs_acc) < 50:
        continue
    stats = compute_stats(abs_acc, ax, ay, az)
    npz_id = f'baseline_{scene_idx:02d}_{loc_type}'
    npz_path = os.path.join(OUT_DIR, f'{npz_id}.npz')
    np.savez(npz_path, time=t[mask], ax=ax, ay=ay, az=az, abs_acc=abs_acc)
    entry = {
        'scene_id': npz_id,
        'scene_type': f'baseline_{loc_type}',
        'scene_desc': f'{loc_desc}本底',
        'source_xls': xls_name,
        'duration_sec': float(bl_dur),
        'peak': stats['peak'],
        'rms': stats['rms'],
        'mean': stats['mean'],
        'std': stats['std'],
        'lin_peak': stats['lin_peak'],
        'lin_rms': stats['lin_rms'],
        'dominant_freq': stats.get('dominant_freq'),
        'pwr_0_5hz': stats.get('pwr_0_5hz', 0),
        'pwr_5_15hz': stats.get('pwr_5_15hz', 0),
        'pwr_15_30hz': stats.get('pwr_15_30hz', 0),
        'pwr_30plus': stats.get('pwr_30plus', 0),
        'npz_path': npz_path,
    }
    scene_entries.append(entry)
    print(f'{npz_id} [{loc_desc}本底]  peak={stats["peak"]:.4f}  rms={stats["rms"]:.5f}')

# --- Save catalog ---
catalog_path = os.path.join(OUT_DIR, 'scene_catalog.json')
with open(catalog_path, 'w', encoding='utf-8') as f:
    json.dump(scene_entries, f, indent=2, ensure_ascii=False)
print(f'\n[OK] {len(scene_entries)} scene entries -> {catalog_path}')

# --- Write CSV summary ---
df = pd.DataFrame(scene_entries)
df.to_csv(os.path.join(BASE, 'scene_summary.csv'), index=False, encoding='utf-8-sig')
print(f'[OK] CSV: {os.path.join(BASE, "scene_summary.csv")}')
print(df[['scene_id','scene_desc','duration_sec','peak','rms','dominant_freq']].to_string())
