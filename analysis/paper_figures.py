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

rcParams['font.sans-serif'] = ['Microsoft YaHei', 'DejaVu Sans']
rcParams['axes.unicode_minus'] = False

BASE = os.path.dirname(os.path.abspath(__file__))
EVENTS_DIR = os.path.join(BASE, 'events')
OUT = os.path.join(BASE, 'figures')

df = pd.read_csv(os.path.join(BASE, 'clean_segments_summary.csv'))
scenes_df = pd.read_csv(os.path.join(BASE, 'scene_summary.csv'))
SR = 99.43

# ============ FIGURE 1: baseline vs train pass (main finding) ============

fig = plt.figure(figsize=(15, 9))
gs = fig.add_gridspec(2, 3, hspace=0.35, wspace=0.3)

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
ax1.set_ylabel('去均值 RMS |a| (m/s²)')
ax1.set_title('(a) 本底 vs 过车：RMS 对比')
ax1.legend(fontsize=8, loc='upper left')
ax1.grid(alpha=0.3, axis='y')

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
ax2.set_title('(b) 峰均比：过车使结构模态"尖锐化"')
ax2.grid(alpha=0.3, axis='y')

# Panel C: Dominant frequency distribution
ax3 = fig.add_subplot(gs[0, 2])
for i, (loc, kind, label, color) in enumerate(cats):
    sub = df[(df['location'] == loc) & (df['type'] == kind)]
    xs = np.full(len(sub), i) + np.random.uniform(-0.1, 0.1, len(sub))
    ax3.scatter(xs, sub['dom_freq'], color=color, alpha=0.9, edgecolor='black', s=65)
ax3.axhspan(30, 45, color='#f59e0b', alpha=0.12, label='结构模态集中频段')
ax3.set_xticks(range(len(cats)))
ax3.set_xticklabels([c[2] for c in cats], rotation=20, ha='right')
ax3.set_ylabel('主频 (Hz)')
ax3.set_title('(c) 主频：过车与本底共享结构模态')
ax3.legend(fontsize=9)
ax3.grid(alpha=0.3, axis='y')
ax3.set_ylim(0, 50)

# Panel D: Average PSD per class
ax4 = fig.add_subplot(gs[1, 0])
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
ax4.set_xlabel('频率 (Hz)')
ax4.set_ylabel('PSD (m²/s⁴/Hz)')
ax4.set_title('(d) 平均 PSD：过车在同频点能量升高')
ax4.legend(fontsize=9)
ax4.grid(alpha=0.3, which='both')

# Panel E: Scene comparison (using scene_summary for platform + subway)
ax5 = fig.add_subplot(gs[1, 1])
# service desk baseline mean
sd_rms = df[(df['location']=='service_desk') & (df['type']=='clean_bgnd')]['rms_centered'].mean()
gf_rms = df[(df['location']=='ground_floor') & (df['type']=='clean_bgnd')]['rms_centered'].mean()
# platform: from scene_summary (use scene entries for platform)
pf = scenes_df[scenes_df['scene_type']=='platform']
sw = scenes_df[scenes_df['scene_type']=='subway_onboard']

# For platform/subway, compute centered RMS from npz
def centered_rms_from_npz(npz_path):
    d = np.load(npz_path)
    x = d['abs_acc']
    return np.sqrt(np.mean((x - np.mean(x))**2))

scene_rms = []
scene_labels = []
scene_colors = []
# Baselines (clean marked)
scene_rms += [sd_rms, gf_rms]
scene_labels += ['服务台本底', '地面本底']
scene_colors += ['#d4a373', '#9fb9aa']
# Platform scenes
for _, r in pf.iterrows():
    scene_rms.append(centered_rms_from_npz(r['npz_path']))
    scene_labels.append('站台' + ('(候车)' if '候车' in r['scene_desc'] else '(近轨)'))
    scene_colors.append('#a78bfa')
# (Subway on-board scenes omitted — paper focuses on station only)

bars = ax5.bar(range(len(scene_rms)), scene_rms, color=scene_colors, edgecolor='black')
for i, v in enumerate(scene_rms):
    ax5.text(i, v + 0.003, f'{v:.4f}', ha='center', fontsize=8)
ax5.axhline(0.015, color='#6b7280', linestyle=':', linewidth=1, label='感知阈 ≈ 0.015')
ax5.axhline(0.030, color='#6b7280', linestyle='--', linewidth=1, label='可察觉 ≈ 0.03')
ax5.axhline(0.080, color='#6b7280', linestyle='-.', linewidth=1, label='不适 ≈ 0.08')
ax5.set_xticks(range(len(scene_labels)))
ax5.set_xticklabels(scene_labels, rotation=35, ha='right', fontsize=8)
ax5.set_ylabel('去均值 RMS (m/s²)')
ax5.set_title('(e) 站房场景谱：旅客活动区 RMS 水平')
ax5.legend(fontsize=8, loc='upper left')
ax5.grid(alpha=0.3, axis='y')

# Panel F: Band energy breakdown for service desk (bgn vs train)
ax6 = fig.add_subplot(gs[1, 2])
bands = ['pwr_0_5hz', 'pwr_5_15hz', 'pwr_15_30hz', 'pwr_30_50hz']
band_labels = ['0-5', '5-15', '15-30', '30-50 Hz']
cat_for_bands = [('service_desk', 'clean_bgnd', '服务台本底', '#d4a373'),
                  ('service_desk', 'train_pass', '服务台过车', '#f0a050'),
                  ('ground_floor', 'clean_bgnd', '地面本底', '#9fb9aa'),
                  ('ground_floor', 'train_pass', '地面过车', '#78c896')]
x = np.arange(len(bands))
w = 0.2
for i, (loc, kind, label, color) in enumerate(cat_for_bands):
    sub = df[(df['location'] == loc) & (df['type'] == kind)]
    means = [sub[b].mean() for b in bands]
    ax6.bar(x + (i-1.5)*w, means, w, label=label, color=color)
ax6.set_xticks(x); ax6.set_xticklabels(band_labels)
ax6.set_ylabel('平均能量')
ax6.set_title('(f) 频带能量：过车主要增强 15-50 Hz')
ax6.legend(fontsize=8)
ax6.grid(alpha=0.3, axis='y')

plt.suptitle('湖州南浔站车致振动实测分析  (n=18 本底 + n=9 过车 + 站台场景)', y=0.995, fontsize=13)
plt.savefig(os.path.join(OUT, 'paper_main_figure.png'), dpi=140, bbox_inches='tight')
plt.close()
print(f'[OK] {os.path.join(OUT, "paper_main_figure.png")}')

# Print key stats for caption writing
print('\n=== Key numbers for paper ===')
print(f'服务台 本底 RMS = {sd_rms:.4f} m/s² (n=12)')
print(f'服务台 过车 RMS = {df[(df.location=="service_desk")&(df.type=="train_pass")].rms_centered.mean():.4f} m/s² (n=7)')
print(f'服务台 过车/本底 = {df[(df.location=="service_desk")&(df.type=="train_pass")].rms_centered.mean() / sd_rms:.2f}x')
print(f'服务台 过车 峰均比 = {df[(df.location=="service_desk")&(df.type=="train_pass")].peak_mean_ratio.mean():.2f} (vs 本底 {df[(df.location=="service_desk")&(df.type=="clean_bgnd")].peak_mean_ratio.mean():.2f})')
print()
print(f'地面 本底 RMS = {gf_rms:.4f} m/s² (n=6)')
print(f'地面 过车 RMS = {df[(df.location=="ground_floor")&(df.type=="train_pass")].rms_centered.mean():.4f} m/s² (n=2)')
print()
for _, r in pf.iterrows():
    print(f'站台 ({r.scene_desc}) 全程 RMS = {centered_rms_from_npz(r.npz_path):.4f} m/s²')
for _, r in sw.iterrows():
    print(f'地铁车内 ({r.scene_desc}) 全程 RMS = {centered_rms_from_npz(r.npz_path):.4f} m/s²')
