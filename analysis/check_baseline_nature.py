"""
Check whether the existing baselines look like:
- Sensor noise (typically: flat/white spectrum, very low amplitude, similar across devices)
- Structural noise (peaks at specific frequencies, depends on structure)

If baselines have DISTINCT spectral peaks and differ across locations,
they are environmental; sensor noise would be flat & location-independent.
"""
import os, json, glob
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import rcParams
from scipy import signal

rcParams['font.sans-serif'] = ['Microsoft YaHei', 'DejaVu Sans']
rcParams['axes.unicode_minus'] = False

BASE = os.path.dirname(os.path.abspath(__file__))
EVENTS_DIR = os.path.join(BASE, 'events')
OUT = os.path.join(BASE, 'figures')

fig, axes = plt.subplots(2, 2, figsize=(13, 8))

# Panel 1: Baseline PSDs per location group
ax = axes[0, 0]
cats = {
    'service_desk': ('#f0a050', '服务台本底'),
    'ground_floor': ('#78c896', '地面本底'),
    'platform':     ('#a78bfa', '站台本底'),
}
for loc_type, (color, label) in cats.items():
    files = glob.glob(os.path.join(EVENTS_DIR, f'baseline_*_{loc_type}.npz'))
    for fp in files:
        d = np.load(fp)
        abs_acc = d['abs_acc']
        centered = abs_acc - np.mean(abs_acc)
        if len(centered) < 64: continue
        f, psd = signal.welch(centered, fs=99.43, nperseg=min(256, len(centered)))
        ax.semilogy(f, psd, color=color, alpha=0.7, linewidth=1)
    # Dummy line for legend
    ax.plot([], [], color=color, label=label)
ax.set_xlabel('Frequency (Hz)')
ax.set_ylabel('PSD (m²/s⁴/Hz)')
ax.set_title('(a) 各位置"安静段"振动 PSD')
ax.set_xlim(0, 50)
ax.grid(alpha=0.3, which='both')
ax.legend(fontsize=9)

# Panel 2: PSD mean across each category, with "flat white noise" reference
ax = axes[0, 1]
for loc_type, (color, label) in cats.items():
    files = glob.glob(os.path.join(EVENTS_DIR, f'baseline_*_{loc_type}.npz'))
    psds = []
    for fp in files:
        d = np.load(fp)
        abs_acc = d['abs_acc']
        centered = abs_acc - np.mean(abs_acc)
        if len(centered) < 64: continue
        f, psd = signal.welch(centered, fs=99.43, nperseg=min(256, len(centered)))
        psds.append(psd)
    if psds:
        mean_psd = np.mean(psds, axis=0)
        ax.semilogy(f, mean_psd, color=color, linewidth=1.5, label=label + f' (n={len(psds)})')

# Reference: what a "flat white noise" PSD would look like
# Typical phone sensor noise floor: ~100-300 μg/√Hz = 1e-6 to 3e-6 m/s²/√Hz
# PSD = (1e-6)^2 = 1e-12 to 9e-12 m²/s⁴/Hz
ax.axhline(1e-11, color='#9ca3af', linestyle='--', label='参考: 手机传感器噪声量级 (~1e-11)')
ax.axhline(1e-10, color='#9ca3af', linestyle=':', label='参考: 10×传感器噪声 (~1e-10)')

ax.set_xlabel('Frequency (Hz)')
ax.set_ylabel('PSD (m²/s⁴/Hz)')
ax.set_title('(b) 类平均 PSD  vs  传感器噪声量级')
ax.set_xlim(0, 50)
ax.grid(alpha=0.3, which='both')
ax.legend(fontsize=9, loc='lower right')

# Panel 3: Narrow-band power comparison across baselines
# Integrate PSD in 3 bands: low 0-5Hz, mid 5-20Hz, high 20-50Hz
ax = axes[1, 0]
bl_files = sorted(glob.glob(os.path.join(EVENTS_DIR, 'baseline_*.npz')))
labels = []
low_p, mid_p, high_p = [], [], []
colors = []
for fp in bl_files:
    d = np.load(fp)
    abs_acc = d['abs_acc']
    centered = abs_acc - np.mean(abs_acc)
    f, psd = signal.welch(centered, fs=99.43, nperseg=min(256, len(centered)))
    def bp(f0, f1):
        m = (f >= f0) & (f < f1)
        return float(np.trapz(psd[m], f[m])) if np.any(m) else 0
    low_p.append(bp(0.5, 5))
    mid_p.append(bp(5, 20))
    high_p.append(bp(20, 50))
    name = os.path.basename(fp).replace('baseline_','').replace('.npz','')
    labels.append(name[:18])
    if 'service_desk' in fp: colors.append('#f0a050')
    elif 'ground_floor' in fp: colors.append('#78c896')
    elif 'platform' in fp: colors.append('#a78bfa')
    elif 'subway' in fp: colors.append('#e87060')
    else: colors.append('#888')
x = np.arange(len(labels))
w = 0.27
ax.bar(x - w, low_p, w, label='0.5-5 Hz', color='#ef4444')
ax.bar(x, mid_p, w, label='5-20 Hz', color='#f59e0b')
ax.bar(x + w, high_p, w, label='20-50 Hz', color='#3b82f6')
ax.set_xticks(x); ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=8)
ax.set_ylabel('Band power')
ax.set_title('(c) 各本底段分频带能量')
ax.legend(fontsize=9)
ax.grid(alpha=0.3, axis='y')

# Panel 4: Compare baseline spectrum to event spectrum (same location)
ax = axes[1, 1]
# Pick an event from service desk and a baseline from service desk, overlay
ev_file = os.path.join(EVENTS_DIR, 'ev05_g_5.npz')  # ev05 is highest peak service desk event
bl_file = os.path.join(EVENTS_DIR, 'baseline_05_service_desk.npz')
if os.path.exists(ev_file) and os.path.exists(bl_file):
    dev = np.load(ev_file)
    dbl = np.load(bl_file)
    # Event window only
    ev_start = float(dev['ev_start'])
    ev_end = float(dev['ev_end'])
    mask = (dev['time'] >= ev_start) & (dev['time'] <= ev_end)
    ev_abs = dev['abs_acc'][mask]
    bl_abs = dbl['abs_acc']
    f1, p1 = signal.welch(ev_abs - np.mean(ev_abs), fs=99.43, nperseg=min(256, len(ev_abs)))
    f2, p2 = signal.welch(bl_abs - np.mean(bl_abs), fs=99.43, nperseg=min(256, len(bl_abs)))
    ax.semilogy(f1, p1, color='#f0a050', linewidth=1.5, label='过车事件 (ev05)')
    ax.semilogy(f2, p2, color='#9ca3af', linewidth=1.5, label='同位置本底')
    ax.fill_between(f1, p1, p2, where=(p1>p2), alpha=0.3, color='#f59e0b', label='事件增量')
ax.set_xlabel('Frequency (Hz)')
ax.set_ylabel('PSD (m²/s⁴/Hz)')
ax.set_title('(d) 服务台: 过车 vs 本底  (差值即为车致振动"纯"增量)')
ax.set_xlim(0, 50)
ax.grid(alpha=0.3, which='both')
ax.legend(fontsize=9)

plt.tight_layout()
plt.savefig(os.path.join(OUT, '_baseline_analysis.png'), dpi=130, bbox_inches='tight')
plt.close()
print('Saved:', os.path.join(OUT, '_baseline_analysis.png'))

# --- Text summary: is baseline consistent with sensor noise or structural? ---
print('\n=== Evidence that baseline is STRUCTURAL, not sensor noise ===')
print('If baseline were sensor noise, we expect:')
print('  (1) Flat/white spectrum')
print('  (2) Uniform RMS across all locations')
print('  (3) No peaks at specific frequencies')
print('\nLet us check:')

# Load all baselines and extract peak frequencies
print('\nBaseline dominant frequencies and RMS:')
for fp in bl_files:
    d = np.load(fp)
    abs_acc = d['abs_acc']
    centered = abs_acc - np.mean(abs_acc)
    f, psd = signal.welch(centered, fs=99.43, nperseg=min(256, len(centered)))
    idx = np.argmax(psd)
    dom_f = f[idx]
    dom_p = psd[idx]
    # Compare peak vs mean of spectrum above 5 Hz (estimate noise floor)
    mask = (f >= 5) & (f <= 45)
    mean_p = np.mean(psd[mask])
    peak_ratio = psd[mask].max() / mean_p
    rms = float(np.sqrt(np.mean(centered**2)))
    name = os.path.basename(fp).replace('baseline_','').replace('.npz','')
    print(f'  {name:30s}  RMS={rms:.4f}  dom={dom_f:5.1f}Hz  peak/mean={peak_ratio:5.2f}')
