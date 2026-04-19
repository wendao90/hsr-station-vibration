"""Create the overall summary figure for the paper."""
import os, json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import rcParams
import pandas as pd

rcParams['font.sans-serif'] = ['Microsoft YaHei', 'DejaVu Sans']
rcParams['axes.unicode_minus'] = False

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, 'figures')

df = pd.read_csv(os.path.join(BASE, 'combined_summary.csv'))

# ISO 2631 reference lines (vibration perception, approximate for 5-80 Hz band)
ISO_PERCEPTION = 0.015  # m/s² RMS
ISO_NOTABLE = 0.030
ISO_UNCOMFORTABLE = 0.080

fig = plt.figure(figsize=(14, 8))
gs = fig.add_gridspec(2, 3, hspace=0.4, wspace=0.3)

# --- Panel 1: RMS vs perception thresholds ---
ax1 = fig.add_subplot(gs[0, 0])
colors = df['group_desc'].map({'服务台': '#f0a050', '地面(正后方)': '#78c896'})
ax1.bar(df['event_id'], df['rms'], color=colors)
ax1.axhline(ISO_PERCEPTION, color='#78c896', linestyle='--', linewidth=1, label=f'感知阈值 ≈ {ISO_PERCEPTION}')
ax1.axhline(ISO_NOTABLE, color='#f59e0b', linestyle='--', linewidth=1, label=f'可察觉 ≈ {ISO_NOTABLE}')
ax1.axhline(ISO_UNCOMFORTABLE, color='#e87060', linestyle='--', linewidth=1, label=f'不适 ≈ {ISO_UNCOMFORTABLE}')
ax1.set_ylabel('RMS |a| (m/s²)')
ax1.set_title('(a) 振动RMS vs ISO2631 感知等级')
ax1.legend(fontsize=8, loc='upper right')
ax1.tick_params(axis='x', rotation=45)
ax1.grid(alpha=0.3, axis='y')

# --- Panel 2: Peak distribution ---
ax2 = fig.add_subplot(gs[0, 1])
ax2.bar(df['event_id'], df['peak'], color=colors)
ax2.set_ylabel('Peak |a| (m/s²)')
ax2.set_title('(b) 振动峰值')
ax2.tick_params(axis='x', rotation=45)
ax2.grid(alpha=0.3, axis='y')

# --- Panel 3: SNR comparison (vibration vs audio) ---
ax3 = fig.add_subplot(gs[0, 2])
x = np.arange(len(df))
w = 0.4
ax3.bar(x - w/2, df['snr_db'], w, label='振动SNR', color='#a78bfa')
ax3.bar(x + w/2, df['audio_snr_db'], w, label='音频SNR', color='#f0a050')
ax3.axhline(0, color='#6b7280', linewidth=0.5)
ax3.set_xticks(x)
ax3.set_xticklabels(df['event_id'], rotation=45)
ax3.set_ylabel('SNR (dB vs pre-event 3s)')
ax3.set_title('(c) 振动 vs 音频信噪比')
ax3.legend(fontsize=8)
ax3.grid(alpha=0.3, axis='y')

# --- Panel 4: Dominant frequency for vibration and audio ---
ax4 = fig.add_subplot(gs[1, 0])
df_sorted = df.sort_values('event_id').reset_index(drop=True)
# Filter out unrealistic 0.4 Hz dominant (likely DC/drift)
dom_vib_clean = df_sorted['dominant_freq'].where(df_sorted['dominant_freq'] > 5, np.nan)
ax4.scatter(range(len(df_sorted)), dom_vib_clean, color='#a78bfa', label='振动主频', s=80)
ax4.scatter(range(len(df_sorted)), df_sorted['audio_dom_hz'], color='#f0a050', label='音频主频', s=80, marker='s')
ax4.set_yscale('log')
ax4.set_xticks(range(len(df_sorted)))
ax4.set_xticklabels(df_sorted['event_id'], rotation=45)
ax4.set_ylabel('主频 (Hz, 对数)')
ax4.set_title('(d) 振动 vs 音频主频')
ax4.legend(fontsize=8)
ax4.grid(alpha=0.3, which='both')

# --- Panel 5: Vibration frequency band power ---
ax5 = fig.add_subplot(gs[1, 1])
bands = ['pwr_0_5hz', 'pwr_5_15hz', 'pwr_15_30hz', 'pwr_30plus']
band_labels = ['0-5 Hz', '5-15 Hz', '15-30 Hz', '30+ Hz']
colors_bands = ['#ef4444', '#f59e0b', '#10b981', '#3b82f6']
x = np.arange(len(df))
bottom = np.zeros(len(df))
for i, (b, lbl, c) in enumerate(zip(bands, band_labels, colors_bands)):
    ax5.bar(x, df[b], bottom=bottom, label=lbl, color=c)
    bottom += df[b]
ax5.set_xticks(x)
ax5.set_xticklabels(df['event_id'], rotation=45)
ax5.set_ylabel('PSD 能量')
ax5.set_title('(e) 振动频带能量分布')
ax5.legend(fontsize=8)
ax5.grid(alpha=0.3, axis='y')

# --- Panel 6: Summary stats by group ---
ax6 = fig.add_subplot(gs[1, 2])
group_stats = df.groupby('group_desc').agg({
    'peak': 'mean',
    'rms': 'mean',
    'snr_db': 'mean',
    'audio_snr_db': 'mean',
    'duration': 'mean',
}).reset_index()
metrics = ['peak', 'rms', 'snr_db', 'audio_snr_db', 'duration']
metrics_labels = ['Peak(m/s²)', 'RMS(m/s²)', 'Vib SNR(dB)', 'Audio SNR(dB)', 'Dur(s)']
x = np.arange(len(metrics_labels))
w = 0.35
for i, (_, row) in enumerate(group_stats.iterrows()):
    vals = [row[m] for m in metrics]
    ax6.bar(x + (i - 0.5) * w, vals, w, label=row['group_desc'],
            color='#f0a050' if '服务台' in row['group_desc'] else '#78c896')
ax6.set_xticks(x)
ax6.set_xticklabels(metrics_labels, rotation=30)
ax6.set_title('(f) 均值对比：服务台 vs 地面')
ax6.legend(fontsize=8)
ax6.grid(alpha=0.3, axis='y')

plt.suptitle('桥建合一高铁站车致振动-音频分析（杭州西站, 10次过车事件）', y=0.995, fontsize=13)
plt.savefig(os.path.join(OUT, '_summary_figure.png'), dpi=120, bbox_inches='tight')
plt.close()
print('Summary figure:', os.path.join(OUT, '_summary_figure.png'))

# Text summary
print('\n=== Group means ===')
print(group_stats.to_string())
