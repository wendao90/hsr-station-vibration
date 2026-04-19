"""
Analyze each extracted event:
- Time-domain: peak, RMS, envelope
- Frequency-domain: PSD (power spectral density) of abs acc
- Vibration dose: ISO-weighted RMS (approximation)
- Baseline comparison
Outputs: per-event plots + summary CSV + summary figures
"""
import os, json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import rcParams
from scipy import signal
from scipy.fft import rfft, rfftfreq
import pandas as pd

rcParams['font.sans-serif'] = ['SimSun', 'Microsoft YaHei', 'DejaVu Sans']
rcParams['font.serif']      = ['Times New Roman', 'SimSun']
rcParams['mathtext.fontset'] = 'stix'
rcParams['axes.unicode_minus'] = True
rcParams['axes.spines.top']    = False
rcParams['axes.spines.right']  = False
rcParams['xtick.direction']    = 'in'
rcParams['ytick.direction']    = 'in'
rcParams['legend.frameon']     = False
rcParams['axes.linewidth']     = 0.8
rcParams['xtick.major.width']  = 0.8
rcParams['ytick.major.width']  = 0.8
rcParams['font.size']          = 14
rcParams['axes.titlesize']     = 14
rcParams['axes.labelsize']     = 13
rcParams['xtick.labelsize']    = 12
rcParams['ytick.labelsize']    = 12
rcParams['legend.fontsize']    = 12
rcParams['axes.grid']          = False

BASE = os.path.dirname(os.path.abspath(__file__))
EVENTS_DIR = os.path.join(BASE, 'events')
OUT_DIR = os.path.join(BASE, 'figures')
os.makedirs(OUT_DIR, exist_ok=True)

with open(os.path.join(EVENTS_DIR, 'events_catalog.json'), 'r', encoding='utf-8') as f:
    catalog = json.load(f)

SR = 99.43  # vibration sample rate (measured earlier)

# Storage for comparison
summary_rows = []
all_psds = {}  # event_id -> (freqs, psd_abs)

def compute_event_features(data, ev_start, ev_end, sr):
    """Compute features inside the event window and a baseline before."""
    t = data['time']
    abs_acc = data['abs_acc']
    ax, ay, az = data['ax'], data['ay'], data['az']
    # Event mask (original event range, without padding)
    mask = (t >= ev_start) & (t <= ev_end)
    ev_abs = abs_acc[mask]
    ev_t = t[mask]
    # Linear acceleration magnitude (gravity-free): use ax, ay, az
    ev_lin_mag = np.sqrt(ax[mask]**2 + ay[mask]**2 + az[mask]**2)

    features = {}
    features['peak'] = float(np.max(ev_abs))
    features['mean'] = float(np.mean(ev_abs))
    features['rms'] = float(np.sqrt(np.mean(ev_abs**2)))
    features['std'] = float(np.std(ev_abs))
    features['lin_peak'] = float(np.max(ev_lin_mag))
    features['lin_rms'] = float(np.sqrt(np.mean(ev_lin_mag**2)))
    features['duration'] = float(ev_t.max() - ev_t.min()) if len(ev_t) > 1 else 0

    # Baseline before event
    baseline_mask = (t >= ev_start - 3) & (t < ev_start - 0.5)
    if np.sum(baseline_mask) > 20:
        bl_abs = abs_acc[baseline_mask]
        features['baseline_mean'] = float(np.mean(bl_abs))
        features['baseline_rms'] = float(np.sqrt(np.mean(bl_abs**2)))
        features['snr_db'] = float(20 * np.log10(features['rms'] / features['baseline_rms'])) if features['baseline_rms'] > 0 else None
    else:
        features['baseline_mean'] = None
        features['baseline_rms'] = None
        features['snr_db'] = None

    # PSD (Welch) on absolute acceleration during event (zero-mean)
    if len(ev_abs) >= 64:
        nperseg = min(256, len(ev_abs))
        freqs, psd = signal.welch(ev_abs - np.mean(ev_abs), fs=sr, nperseg=nperseg)
        features['psd_freqs'] = freqs
        features['psd'] = psd
        # Dominant frequency
        idx_max = np.argmax(psd)
        features['dominant_freq'] = float(freqs[idx_max])
        # Frequency band powers
        def band_power(f_lo, f_hi):
            m = (freqs >= f_lo) & (freqs < f_hi)
            if np.any(m):
                return float(np.trapz(psd[m], freqs[m]))
            return 0
        features['pwr_0_5hz'] = band_power(0, 5)
        features['pwr_5_15hz'] = band_power(5, 15)
        features['pwr_15_30hz'] = band_power(15, 30)
        features['pwr_30plus'] = band_power(30, freqs.max())
    return features


def plot_event(ev_id, label, group_desc, data, ev_start, ev_end, sr, features):
    """Plot time series + PSD + spectrogram for one event."""
    fig, axes = plt.subplots(3, 1, figsize=(6.5, 6))
    t = data['time']
    abs_acc = data['abs_acc']
    ax_plot = axes[0]
    ax_plot.plot(t, abs_acc, color='#a78bfa', linewidth=0.8)
    ax_plot.axvspan(ev_start, ev_end, color='#60a5fa', alpha=0.15, label='事件段')
    ax_plot.axhline(features.get('baseline_mean') or 0, color='#6b7280', linestyle=':', linewidth=1, label='本底均值')
    ax_plot.set_xlabel('时间/s')
    ax_plot.set_ylabel(r'|a|/(m·s$^{-2}$)')
    ax_plot.set_title(f'（a） {ev_id} {label} — 峰值 {features["peak"]:.3f} m·s$^{{-2}}$，RMS {features["rms"]:.4f} m·s$^{{-2}}$，SNR {features.get("snr_db",0):.1f} dB')
    ax_plot.legend(loc='upper right')

    # PSD
    ax_psd = axes[1]
    if 'psd' in features:
        ax_psd.semilogy(features['psd_freqs'], features['psd'], color='#3b82f6')
        ax_psd.set_xlim(0, sr/2)
        ax_psd.set_xlabel('频率/Hz')
        ax_psd.set_ylabel(r'PSD/(m$^{2}$·s$^{-4}$·Hz$^{-1}$)')
        ax_psd.set_title(f'（b） 功率谱密度（主频 ≈ {features["dominant_freq"]:.1f} Hz）')
        ax_psd.axvline(features['dominant_freq'], color='#f59e0b', linestyle='--', linewidth=1)
        # Force mathtext rendering on log ticks so the negative exponent
        # sign always shows (the default LogFormatterSciNotation sometimes
        # drops the minus under stix+SimSun fallback).
        from matplotlib.ticker import FuncFormatter
        ax_psd.yaxis.set_major_formatter(FuncFormatter(
            lambda v, pos: r'$10^{%d}$' % int(round(np.log10(v))) if v > 0 else ''))

    # Spectrogram
    ax_spec = axes[2]
    mask = (t >= ev_start - 1) & (t <= ev_end + 1)
    seg = abs_acc[mask] - np.mean(abs_acc[mask])
    t_seg = t[mask]
    if len(seg) > 32:
        nperseg = min(64, len(seg))
        noverlap = nperseg // 2
        f, tt, Sxx = signal.spectrogram(seg, fs=sr, nperseg=nperseg, noverlap=noverlap)
        ax_spec.pcolormesh(tt + t_seg[0], f, 10*np.log10(Sxx + 1e-12), cmap='magma')
        ax_spec.set_xlabel('时间/s')
        ax_spec.set_ylabel('频率/Hz')
        ax_spec.set_title('（c） 时频谱（dB）')
        ax_spec.axvline(ev_start, color='#60a5fa', linestyle='--', linewidth=1, alpha=0.7)
        ax_spec.axvline(ev_end, color='#60a5fa', linestyle='--', linewidth=1, alpha=0.7)

    plt.tight_layout()
    out_path = os.path.join(OUT_DIR, f'{ev_id}.png')
    plt.savefig(out_path, dpi=110)
    plt.close()
    return out_path


for ev in catalog:
    if not ev['vib_slices']:
        print(f'[SKIP] {ev["id"]}: no vib data')
        continue
    for xls_name, slice_info in ev['vib_slices'].items():
        data = np.load(slice_info['path'])
        ev_start = float(data['ev_start'])
        ev_end = float(data['ev_end'])
        features = compute_event_features(data, ev_start, ev_end, SR)
        features['event_id'] = ev['id']
        features['xls'] = xls_name
        features['label'] = ev['label']
        features['group'] = ev['group']
        features['group_desc'] = ev['group_desc']
        features['abs_start'] = ev['abs_start']
        features['abs_end'] = ev['abs_end']
        plot_path = plot_event(ev['id'], ev['label'], ev['group_desc'],
                                data, ev_start, ev_end, SR, features)
        print(f'{ev["id"]}  peak={features["peak"]:.3f}  rms={features["rms"]:.4f}  dom={features.get("dominant_freq",0):.1f}Hz  SNR={features.get("snr_db",0) or 0:.1f}dB  -> {os.path.basename(plot_path)}')
        summary_rows.append({k: v for k, v in features.items()
                              if not isinstance(v, np.ndarray)})
        # Also store PSD for comparison
        all_psds[ev['id']] = (features.get('psd_freqs'), features.get('psd'), ev['group_desc'], ev['label'])

# Save summary CSV
df = pd.DataFrame(summary_rows)
csv_cols = ['event_id','xls','label','group','group_desc','abs_start','abs_end','duration',
            'peak','rms','mean','std','lin_peak','lin_rms',
            'baseline_mean','baseline_rms','snr_db',
            'dominant_freq','pwr_0_5hz','pwr_5_15hz','pwr_15_30hz','pwr_30plus']
df = df[[c for c in csv_cols if c in df.columns]]
csv_path = os.path.join(BASE, 'events_summary.csv')
df.to_csv(csv_path, index=False, encoding='utf-8-sig')
print(f'\n[OK] Summary saved: {csv_path}')
print(df.to_string())

# --- Comparison figure: PSD overlay by group ---
fig, axs = plt.subplots(1, 2, figsize=(13, 5), sharey=True)
colors = plt.cm.viridis(np.linspace(0, 0.9, 10))
for i, (ev_id, (freqs, psd, group, label)) in enumerate(all_psds.items()):
    if freqs is None: continue
    ax_idx = 0 if '服务台' in group else 1
    axs[ax_idx].semilogy(freqs, psd, color=colors[i], linewidth=1, label=ev_id)
for i, ax in enumerate(axs):
    ax.set_title(['服务台 (n=7)', '地面/正后方 (n=2)'][i])
    ax.set_xlabel('Frequency (Hz)')
    ax.set_xlim(0, 50)
    ax.legend(ncol=2)
axs[0].set_ylabel('PSD (m²/s⁴/Hz)')
plt.suptitle('Train-pass vibration PSD comparison', y=1.02)
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, '_psd_comparison.png'), dpi=110, bbox_inches='tight')
plt.close()
print(f'PSD comparison plot: {os.path.join(OUT_DIR, "_psd_comparison.png")}')

# --- Summary bar chart: peak and RMS per event, colored by group ---
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
df_plot = df.copy()
df_plot['idx'] = range(len(df_plot))
colors_grp = df_plot['group'].map({'service_desk': '#f0a050', 'ground_floor': '#78c896'})
axes[0].bar(df_plot['event_id'], df_plot['peak'], color=colors_grp)
axes[0].set_ylabel('Peak |a| (m/s²)')
axes[0].set_title('Peak vibration per event')
axes[0].tick_params(axis='x', rotation=45)

axes[1].bar(df_plot['event_id'], df_plot['rms'], color=colors_grp)
axes[1].set_ylabel('RMS |a| (m/s²)')
axes[1].set_title('RMS vibration per event')
axes[1].tick_params(axis='x', rotation=45)

# Legend
import matplotlib.patches as mpatches
handles = [mpatches.Patch(color='#f0a050', label='服务台 (n=7)'),
           mpatches.Patch(color='#78c896', label='地面 (n=2)')]
axes[0].legend(handles=handles, loc='upper left')
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, '_peak_rms_comparison.png'), dpi=110, bbox_inches='tight')
plt.close()
print(f'Bar chart: {os.path.join(OUT_DIR, "_peak_rms_comparison.png")}')
