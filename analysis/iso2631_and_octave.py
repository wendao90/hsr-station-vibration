"""
Standard rail-vibration metrics:
1. ISO 2631-1 frequency-weighted RMS (W_k vertical; W_d horizontal)
2. 1/3 octave band spectrum (for comparison with published building vibration data)

These are the standard metrics used in rail/bridge-building integrated station papers.
"""
import os, glob, json, sys, io
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
except Exception:
    pass
import numpy as np
import pandas as pd
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
SR = 99.43  # phone sample rate


# =============================================================
# ISO 2631-1 frequency weighting filters (simplified)
# Reference: ISO 2631-1:1997, Annex A
# =============================================================
def iso2631_weighting_gain(f, kind='Wk'):
    """Return magnitude response at frequencies f (Hz) for ISO 2631-1 weighting filter.

    Wk: vertical axis for seated/standing person (most relevant for station floor)
    Wd: horizontal axes

    Simplified formula based on ISO 2631-1 Annex A band-limiting + asymptotic approximation.
    """
    # High-pass at 0.4 Hz (2nd order)
    # Low-pass at 100 Hz (2nd order)
    # Upward step/band shaping characteristic
    if kind == 'Wk':
        # Wk filter: principal parameters
        f1, f2, f3, f4, Q1, Q2 = 0.4, 100, 12.5, 12.5, 0.63, 0.91
        # Asymptotic: gain ≈ 1 between 4-8 Hz (peak), rolls off
        # Simplified with piecewise:
        def g(freq):
            if freq <= 0: return 0
            # HP at f1
            hp = freq**2 / np.sqrt(freq**4 + (freq**2 - f1**2)**2)
            # Band-pass shaping
            if freq <= 8:
                return hp
            elif freq <= 80:
                # Roll-off with -6 dB/oct
                return hp * (8 / freq)
            else:
                return hp * (8 / freq) * (80 / freq)
    elif kind == 'Wd':
        # Wd: horizontal weighting, lower band emphasis
        def g(freq):
            if freq <= 0: return 0
            if freq <= 2:
                return freq / 2  # low-freq rise
            elif freq <= 8:
                return 1.0
            else:
                return 8 / freq
    else:
        def g(freq): return 1.0
    return np.array([g(x) for x in np.atleast_1d(f)])


def iso2631_weighted_rms(signal_data, fs, kind='Wk'):
    """Compute frequency-weighted RMS using FFT-domain weighting."""
    x = signal_data - np.mean(signal_data)
    n = len(x)
    X = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(n, d=1/fs)
    W = iso2631_weighting_gain(freqs, kind=kind)
    X_weighted = X * W
    x_weighted = np.fft.irfft(X_weighted, n=n)
    return float(np.sqrt(np.mean(x_weighted**2)))


# =============================================================
# 1/3 octave band analysis
# =============================================================
# Standard center frequencies (IEC 61260) in the relevant range
THIRD_OCTAVE_CENTERS = np.array([
    1.0, 1.25, 1.6, 2.0, 2.5, 3.15, 4.0, 5.0, 6.3, 8.0,
    10.0, 12.5, 16.0, 20.0, 25.0, 31.5, 40.0, 50.0
])

def third_octave_rms(signal_data, fs):
    """Return RMS in each 1/3 octave band (from FFT)."""
    x = signal_data - np.mean(signal_data)
    n = len(x)
    freqs = np.fft.rfftfreq(n, d=1/fs)
    X = np.fft.rfft(x)
    psd_per_bin = (np.abs(X)**2) * (2.0 / (fs * n))
    psd_per_bin[0] /= 2  # DC
    if n % 2 == 0:
        psd_per_bin[-1] /= 2  # Nyquist
    df = freqs[1] - freqs[0] if len(freqs) > 1 else 1.0

    band_rms = []
    for fc in THIRD_OCTAVE_CENTERS:
        f_lo = fc / (2 ** (1/6))  # lower edge
        f_hi = fc * (2 ** (1/6))  # upper edge
        if f_hi > fs / 2:
            band_rms.append(np.nan)
            continue
        m = (freqs >= f_lo) & (freqs < f_hi)
        power = np.sum(psd_per_bin[m]) * df
        band_rms.append(float(np.sqrt(max(power, 0))))
    return np.array(band_rms)


# =============================================================
# Process all clean_bgnd and train_pass segments (from user-marked)
# Also process the scene segments
# =============================================================
df_seg = pd.read_csv(os.path.join(BASE, 'clean_segments_summary.csv'))
df_scene = pd.read_csv(os.path.join(BASE, 'scene_summary.csv'))

rows = []

def process_npz(npz_path, label_info):
    d = np.load(npz_path)
    abs_acc = d['abs_acc']
    ax, ay, az = d['ax'], d['ay'], d['az']

    # ISO 2631 weighted RMS
    # Use Z for Wk (vertical = phone Z axis when flat on surface)
    # Use X, Y vector for Wd
    wk_rms = iso2631_weighted_rms(az, SR, kind='Wk')
    wd_rms_x = iso2631_weighted_rms(ax, SR, kind='Wd')
    wd_rms_y = iso2631_weighted_rms(ay, SR, kind='Wd')
    wd_rms = np.sqrt(wd_rms_x**2 + wd_rms_y**2)
    # Total weighted RMS (VDV-like, not proper VDV but useful comparison)
    total_weighted = np.sqrt(1.4**2 * wd_rms**2 + wk_rms**2)  # ISO 2631 combination factor

    # 1/3 octave bands on abs_acc
    oct_rms = third_octave_rms(abs_acc, SR)

    row = {**label_info,
           'wk_z_rms': wk_rms,
           'wd_xy_rms': wd_rms,
           'iso_total': total_weighted}
    for fc, r in zip(THIRD_OCTAVE_CENTERS, oct_rms):
        row[f'oct_{fc:.2f}Hz'] = r
    return row


# User-marked segments
for _, r in df_seg.iterrows():
    info = {
        'segment_id': r['tag'],
        'category': r['type'] + '_' + r['location'],
        'label': r['label'],
        'location': r['location_desc'],
        'kind': r['type'],
        'duration': r['duration'],
    }
    try:
        rows.append(process_npz(r['npz_path'], info))
    except Exception as e:
        print(f'[ERR] {r["tag"]}: {e}')

# Scene segments (full-segment platform, subway)
for _, r in df_scene.iterrows():
    info = {
        'segment_id': r['scene_id'],
        'category': r['scene_type'],
        'label': r['scene_desc'],
        'location': r['scene_desc'],
        'kind': 'scene' if not r['scene_type'].startswith('baseline_') else 'baseline_scene',
        'duration': r['duration_sec'],
    }
    try:
        rows.append(process_npz(r['npz_path'], info))
    except Exception as e:
        print(f'[ERR] {r["scene_id"]}: {e}')

df_iso = pd.DataFrame(rows)
df_iso.to_csv(os.path.join(BASE, 'iso2631_and_octave.csv'), index=False, encoding='utf-8-sig')

print('\n=== ISO 2631 weighted RMS (W_k on Z vertical axis) ===')
print(f'{"类别":<30s} {"n":>3s} {"Wk_z (m/s²)":>12s} {"Wd_xy":>10s} {"ISO total":>10s}')
cats_to_show = [
    ('clean_bgnd_service_desk', '服务台-本底'),
    ('train_pass_service_desk', '服务台-过车'),
    ('clean_bgnd_ground_floor', '地面-本底'),
    ('train_pass_ground_floor', '地面-过车'),
    ('platform', '站台-全程'),
    ('subway_onboard', '地铁车内-全程'),
]
for cat_id, cat_name in cats_to_show:
    sub = df_iso[df_iso['category'] == cat_id]
    if len(sub) == 0: continue
    print(f'{cat_name:<26s} {len(sub):>4d} {sub["wk_z_rms"].mean():>10.5f}  {sub["wd_xy_rms"].mean():>10.5f}  {sub["iso_total"].mean():>10.5f}')

# ============ Figure: 1/3 octave band comparison ============
fig, axes = plt.subplots(1, 2, figsize=(14, 5.5), sharey=True)

def plot_cat(ax, cat_id, label, color, linestyle='-'):
    sub = df_iso[df_iso['category'] == cat_id]
    if len(sub) == 0: return
    oct_cols = [c for c in df_iso.columns if c.startswith('oct_')]
    values = sub[oct_cols].mean()
    std = sub[oct_cols].std()
    ax.plot(THIRD_OCTAVE_CENTERS, values, color=color, linewidth=1.8, label=f'{label} (n={len(sub)})', linestyle=linestyle, marker='o', markersize=4)
    if len(sub) > 1:
        ax.fill_between(THIRD_OCTAVE_CENTERS, values - std, values + std, color=color, alpha=0.15)

# Panel A: service desk + ground floor event vs baseline
plot_cat(axes[0], 'clean_bgnd_service_desk', '服务台 本底', '#d4a373')
plot_cat(axes[0], 'train_pass_service_desk', '服务台 过车', '#f0a050')
plot_cat(axes[0], 'clean_bgnd_ground_floor', '地面 本底',   '#9fb9aa')
plot_cat(axes[0], 'train_pass_ground_floor', '地面 过车',   '#78c896')
axes[0].set_xscale('log')
axes[0].set_yscale('log')
axes[0].set_xlabel('1/3 倍频程中心频率 (Hz)')
axes[0].set_ylabel('1/3 倍频程 RMS (m/s²)')
axes[0].set_title('(a) 站房区域: 1/3 倍频程谱对比')
axes[0].grid(alpha=0.3, which='both')
axes[0].legend(fontsize=9)
axes[0].set_xticks([1, 2, 5, 10, 20, 50])
axes[0].set_xticklabels(['1','2','5','10','20','50'])

# Panel B: station scenarios (service desk vs platform)
plot_cat(axes[1], 'clean_bgnd_service_desk', '服务台 本底', '#d4a373')
plot_cat(axes[1], 'train_pass_service_desk', '服务台 过车', '#f0a050')
plot_cat(axes[1], 'clean_bgnd_ground_floor', '地面 本底',   '#9fb9aa')
plot_cat(axes[1], 'platform',                '站台 全程',   '#a78bfa')
axes[1].set_xscale('log')
axes[1].set_yscale('log')
axes[1].set_xlabel('1/3 倍频程中心频率 (Hz)')
axes[1].set_title('(b) 站房 3 个场景对比')
axes[1].grid(alpha=0.3, which='both')
axes[1].legend(fontsize=9)
axes[1].set_xticks([1, 2, 5, 10, 20, 50])
axes[1].set_xticklabels(['1','2','5','10','20','50'])

plt.suptitle('湖州南浔站车致振动 1/3 倍频程分析', y=1.02, fontsize=13)
plt.tight_layout()
plt.savefig(os.path.join(OUT, 'paper_octave_bands.png'), dpi=140, bbox_inches='tight')
plt.close()

print(f'\n[OK] {os.path.join(OUT, "paper_octave_bands.png")}')

# ============ Figure: ISO 2631 weighted RMS bar chart ============
fig, ax = plt.subplots(1, 1, figsize=(10, 5))
cat_order = [
    ('clean_bgnd_service_desk', '服务台本底',  '#d4a373'),
    ('train_pass_service_desk', '服务台过车',  '#f0a050'),
    ('clean_bgnd_ground_floor', '地面本底',    '#9fb9aa'),
    ('train_pass_ground_floor', '地面过车',    '#78c896'),
    ('platform',                '站台全程',    '#a78bfa'),
]
x = np.arange(len(cat_order))
w = 0.3
wk_means = [df_iso[df_iso['category']==c].wk_z_rms.mean() for c, _, _ in cat_order]
wd_means = [df_iso[df_iso['category']==c].wd_xy_rms.mean() for c, _, _ in cat_order]
tot_means= [df_iso[df_iso['category']==c].iso_total.mean() for c, _, _ in cat_order]
ax.bar(x - w, wk_means, w, label='W_k 垂向(Z轴)', color='#3b82f6')
ax.bar(x,     wd_means, w, label='W_d 水平(XY)',  color='#10b981')
ax.bar(x + w, tot_means,w, label='总加权 (1.4·Wd + Wk)', color='#f59e0b')
ax.axhline(0.015, color='#6b7280', linestyle=':', linewidth=1, label='ISO 感知阈 0.015')
ax.axhline(0.030, color='#6b7280', linestyle='--', linewidth=1, label='ISO 可察觉 0.030')
ax.axhline(0.080, color='#6b7280', linestyle='-.', linewidth=1, label='ISO 可能不适 0.080')
ax.set_xticks(x)
ax.set_xticklabels([c[1] for c in cat_order], rotation=20, ha='right')
ax.set_ylabel('频率加权 RMS (m/s²)')
ax.set_yscale('log')
ax.set_title('ISO 2631-1 频率加权 RMS 对比')
ax.legend(fontsize=9, loc='upper left')
ax.grid(alpha=0.3, axis='y', which='both')
plt.tight_layout()
plt.savefig(os.path.join(OUT, 'paper_iso2631_rms.png'), dpi=140, bbox_inches='tight')
plt.close()

print(f'[OK] {os.path.join(OUT, "paper_iso2631_rms.png")}')
