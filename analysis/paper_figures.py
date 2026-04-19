"""
Paper-ready figures using the rigorous clean_bgnd vs train_pass comparison.
"""
import os, glob
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import rcParams
from scipy import signal
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
rcParams['font.size']          = 12
rcParams['axes.titlesize']     = 12
rcParams['axes.labelsize']     = 11
rcParams['xtick.labelsize']    = 10
rcParams['ytick.labelsize']    = 10
rcParams['legend.fontsize']    = 10
rcParams['axes.grid']          = False

from matplotlib.ticker import FuncFormatter
_LOG_FMT = FuncFormatter(lambda v, pos: r'$10^{%d}$' % int(round(np.log10(v))) if v > 0 else '')

BASE = os.path.dirname(os.path.abspath(__file__))
EVENTS_DIR = os.path.join(BASE, 'events')
OUT = os.path.join(BASE, 'figures')

df = pd.read_csv(os.path.join(BASE, 'clean_segments_summary.csv'))
scenes_df = pd.read_csv(os.path.join(BASE, 'scene_summary.csv'))
SR = 99.43

# ============ FIGURE 1: baseline vs train pass (main finding) ============

fig = plt.figure(figsize=(12, 9))
gs = fig.add_gridspec(2, 2, hspace=0.38, wspace=0.28)

# Panel A: RMS_centered strip plot
ax1 = fig.add_subplot(gs[0, 0])
cats = [('service_desk', 'clean_bgnd', '服务台本底', '#d4a373'),
        ('service_desk', 'train_pass', '服务台过车', '#f0a050'),
        ('ground_floor', 'clean_bgnd', '地面本底', '#9fb9aa'),
        ('ground_floor', 'train_pass', '地面过车', '#78c896')]
for i, (loc, kind, label, color) in enumerate(cats):
    sub = df[(df['location'] == loc) & (df['type'] == kind)]
    xs = np.full(len(sub), i) + np.random.uniform(-0.1, 0.1, len(sub))
    ax1.scatter(xs, sub['rms_centered'], color=color, alpha=0.9, edgecolor='black', s=65, label=f'{label} (n={len(sub)})')
    ax1.hlines(sub['rms_centered'].mean(), i-0.3, i+0.3, color=color, linewidth=3)
ax1.axhline(0.015, color='#6b7280', linestyle=':', linewidth=1, label='感知阈 ≈ 0.015')
ax1.axhline(0.030, color='#6b7280', linestyle='--', linewidth=1, label='可察觉 ≈ 0.03')
ax1.set_xticks(range(len(cats)))
ax1.set_xticklabels([c[2] for c in cats], rotation=20, ha='right')
ax1.set_ylabel(r'去均值 RMS |a|/(m·s$^{-2}$)')
ax1.set_title('（a） 本底 vs 过车：RMS 对比')
ax1.legend(loc='best')
# Panel B: Peak-to-mean ratio (more sensitive indicator)
ax2 = fig.add_subplot(gs[0, 1])
for i, (loc, kind, label, color) in enumerate(cats):
    sub = df[(df['location'] == loc) & (df['type'] == kind)]
    xs = np.full(len(sub), i) + np.random.uniform(-0.1, 0.1, len(sub))
    ax2.scatter(xs, sub['peak_mean_ratio'], color=color, alpha=0.9, edgecolor='black', s=65)
    ax2.hlines(sub['peak_mean_ratio'].mean(), i-0.3, i+0.3, color=color, linewidth=3)
ax2.set_xticks(range(len(cats)))
ax2.set_xticklabels([c[2] for c in cats], rotation=20, ha='right')
ax2.set_ylabel('频谱峰均比')
ax2.set_title('（b） 峰均比：过车使结构模态"尖锐化"')
# Panel C: Dominant frequency distribution
ax3 = fig.add_subplot(gs[1, 0])
for i, (loc, kind, label, color) in enumerate(cats):
    sub = df[(df['location'] == loc) & (df['type'] == kind)]
    xs = np.full(len(sub), i) + np.random.uniform(-0.1, 0.1, len(sub))
    ax3.scatter(xs, sub['dom_freq'], color=color, alpha=0.9, edgecolor='black', s=65)
ax3.axhspan(30, 45, color='#f59e0b', alpha=0.12, label='结构模态集中频段')
ax3.set_xticks(range(len(cats)))
ax3.set_xticklabels([c[2] for c in cats], rotation=20, ha='right')
ax3.set_ylabel('主频/Hz')
ax3.set_title('（c） 主频：过车与本底共享结构模态')
ax3.legend(loc='best')
ax3.set_ylim(0, 50)

# Panel D: Average PSD per class
ax4 = fig.add_subplot(gs[1, 1])
def avg_psd(loc, kind):
    sub = df[(df['location'] == loc) & (df['type'] == kind)]
    psds = []
    for _, r in sub.iterrows():
        d = np.load(r['npz_path'])
        s = d['abs_acc'] - np.mean(d['abs_acc'])
        if len(s) < 64: continue
        f, p = signal.welch(s, fs=SR, nperseg=min(256, len(s)))
        psds.append(p)
    if not psds: return None, None
    return f, np.mean(psds, axis=0)

for loc, kind, label, color in cats:
    f, p = avg_psd(loc, kind)
    if f is None: continue
    ax4.semilogy(f, p, color=color, linewidth=1.5, label=label)
ax4.set_xlim(0, 50)
ax4.set_xlabel('频率/Hz')
ax4.set_ylabel(r'PSD/(m$^{2}$·s$^{-4}$·Hz$^{-1}$)')
ax4.set_title('（d） 平均 PSD：过车在同频点能量升高')
ax4.yaxis.set_major_formatter(_LOG_FMT)
ax4.legend(loc='best')
# Panels （e） 站房场景谱 and （f） 频带能量 have been dropped:
#   （e） is redundant with （a） as both compare per-scenario RMS;
#   （f） overlaps with 图 7 (1/3 倍频程谱) which conveys the same info at finer
#   resolution. Retained （a）–（d） in a 2×2 layout to give each panel more area.
plt.savefig(os.path.join(OUT, 'paper_main_figure.png'), dpi=140, bbox_inches='tight')
plt.close()
print(f'[OK] {os.path.join(OUT, "paper_main_figure.png")}')

# Print key stats for caption writing
sd_rms = df[(df['location']=='service_desk') & (df['type']=='clean_bgnd')]['rms_centered'].mean()
gf_rms = df[(df['location']=='ground_floor') & (df['type']=='clean_bgnd')]['rms_centered'].mean()
print('\n=== Key numbers for paper ===')
print(f'服务台 本底 RMS = {sd_rms:.4f} m/s² (n=12)')
print(f'服务台 过车 RMS = {df[(df.location=="service_desk")&(df.type=="train_pass")].rms_centered.mean():.4f} m/s² (n=7)')
print(f'服务台 过车/本底 = {df[(df.location=="service_desk")&(df.type=="train_pass")].rms_centered.mean() / sd_rms:.2f}x')
print(f'服务台 过车 峰均比 = {df[(df.location=="service_desk")&(df.type=="train_pass")].peak_mean_ratio.mean():.2f} (vs 本底 {df[(df.location=="service_desk")&(df.type=="clean_bgnd")].peak_mean_ratio.mean():.2f})')
print(f'地面 本底 RMS = {gf_rms:.4f} m/s² (n=6)')
print(f'地面 过车 RMS = {df[(df.location=="ground_floor")&(df.type=="train_pass")].rms_centered.mean():.4f} m/s² (n=2)')
