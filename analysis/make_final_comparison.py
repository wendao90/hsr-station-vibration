"""
Final comparison figure across all scene categories, for the paper.
"""
import os, json
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
OUT = os.path.join(BASE, 'figures')
EVENTS_DIR = os.path.join(BASE, 'events')

# Load all data
events_df = pd.read_csv(os.path.join(BASE, 'combined_summary.csv'))
scenes_df = pd.read_csv(os.path.join(BASE, 'scene_summary.csv'))

# Build unified dataset: each row = one observation window
rows = []

# Train-pass events (already analyzed)
for _, r in events_df.iterrows():
    rows.append({
        'category': '过车-' + r['group_desc'],
        'label': r['event_id'],
        'duration': r['duration'],
        'rms': r['rms'],
        'peak': r['peak'],
        'dominant_freq': r['dominant_freq'],
        'kind': 'event',
        'group_desc': r['group_desc'],
    })

# Additional scenes
for _, r in scenes_df.iterrows():
    if r['scene_type'].startswith('baseline_'):
        # Rename baseline
        cat = '本底-' + r['scene_desc'].replace('本底','')
        kind = 'baseline'
    else:
        cat = r['scene_desc'].split('(')[0]  # e.g. 站台, 地铁车内
        kind = 'scene'
    rows.append({
        'category': cat,
        'label': r['scene_id'],
        'duration': r['duration_sec'],
        'rms': r['rms'],
        'peak': r['peak'],
        'dominant_freq': r['dominant_freq'],
        'kind': kind,
        'group_desc': r['scene_desc'],
    })

all_df = pd.DataFrame(rows)
print(all_df.to_string())

# Category order for plotting (station-city continuum)
cat_order = [
    '本底-服务台', '过车-服务台', '本底-地面', '过车-地面(正后方)',
    '本底-站台', '站台',
    '本底-地铁车内', '地铁车内',
]
cat_colors = {
    '本底-服务台':       '#d4a373',
    '过车-服务台':       '#f0a050',
    '本底-地面':         '#9fb9aa',
    '过车-地面(正后方)': '#78c896',
    '本底-站台':         '#bcbcf5',
    '站台':              '#a78bfa',
    '本底-地铁车内':     '#efc0c0',
    '地铁车内':          '#e87060',
}

# --- Main figure: RMS comparison by scene ---
fig = plt.figure(figsize=(16, 9))
gs = fig.add_gridspec(2, 3, hspace=0.45, wspace=0.3)

# Panel A: RMS box/strip plot by category
ax1 = fig.add_subplot(gs[0, :2])
for i, cat in enumerate(cat_order):
    sub = all_df[all_df['category'] == cat]
    if len(sub) == 0: continue
    xs = np.full(len(sub), i) + np.random.uniform(-0.12, 0.12, len(sub))
    ax1.scatter(xs, sub['rms'], color=cat_colors.get(cat, '#888'), alpha=0.9, edgecolor='black', s=60)
    # Mean bar
    ax1.hlines(sub['rms'].mean(), i-0.3, i+0.3, color=cat_colors.get(cat, '#888'), linewidth=3)

# ISO 2631 thresholds
ax1.axhline(0.015, color='#6b7280', linestyle=':', linewidth=1, label='感知阈值 ≈ 0.015')
ax1.axhline(0.030, color='#6b7280', linestyle='--', linewidth=1, label='可察觉 ≈ 0.03')
ax1.axhline(0.080, color='#6b7280', linestyle='-.', linewidth=1, label='可能不适 ≈ 0.08')
ax1.axhline(0.315, color='#6b7280', linestyle='-', linewidth=0.7, label='不舒适 ≈ 0.315')
ax1.set_yscale('log')
ax1.set_xticks(range(len(cat_order)))
ax1.set_xticklabels(cat_order, rotation=35, ha='right')
ax1.set_ylabel('RMS |a| (m/s²,  对数坐标)')
ax1.set_title('(a) 各场景振动 RMS 分布  vs  ISO 2631 舒适度等级')
ax1.legend(fontsize=8, loc='lower right')
ax1.grid(alpha=0.3, which='both')

# Panel B: Peak comparison
ax2 = fig.add_subplot(gs[0, 2])
for i, cat in enumerate(cat_order):
    sub = all_df[all_df['category'] == cat]
    if len(sub) == 0: continue
    xs = np.full(len(sub), i) + np.random.uniform(-0.12, 0.12, len(sub))
    ax2.scatter(xs, sub['peak'], color=cat_colors.get(cat, '#888'), alpha=0.9, edgecolor='black', s=60)
    ax2.hlines(sub['peak'].mean(), i-0.3, i+0.3, color=cat_colors.get(cat, '#888'), linewidth=3)
ax2.set_yscale('log')
ax2.set_xticks(range(len(cat_order)))
ax2.set_xticklabels([c.split('-')[-1][:4] for c in cat_order], rotation=35, ha='right')
ax2.set_ylabel('Peak |a| (m/s²)')
ax2.set_title('(b) 峰值分布')
ax2.grid(alpha=0.3, which='both')

# Panel C: PSD overlay for scene types
ax3 = fig.add_subplot(gs[1, 0])
ax4 = fig.add_subplot(gs[1, 1], sharey=ax3)
ax5 = fig.add_subplot(gs[1, 2], sharey=ax3)

def plot_psd_group(ax, glob_pattern, title, color_base):
    import glob
    for fp in glob.glob(os.path.join(EVENTS_DIR, glob_pattern)):
        d = np.load(fp)
        abs_acc = d['abs_acc']
        if len(abs_acc) < 64: continue
        centered = abs_acc - np.mean(abs_acc)
        f, psd = signal.welch(centered, fs=99.43, nperseg=min(256, len(centered)))
        lbl = os.path.basename(fp).replace('.npz','').replace('scene_','').replace('baseline_','BL ')
        ax.semilogy(f, psd, color=color_base, alpha=0.6, linewidth=1, label=lbl[:14])
    ax.set_title(title)
    ax.set_xlabel('Frequency (Hz)')
    ax.set_xlim(0, 50)
    ax.grid(alpha=0.3, which='both')
    ax.legend(fontsize=7)

plot_psd_group(ax3, 'ev0*.npz', '(c) 车致振动 (n=9 events)', '#f0a050')
plot_psd_group(ax4, 'scene_*platform*.npz', '(d) 站台环境 (n=2)', '#a78bfa')
plot_psd_group(ax5, 'scene_*subway*.npz', '(e) 地铁车内 (n=2)', '#e87060')
ax3.set_ylabel('PSD (m²/s⁴/Hz)')

plt.suptitle('站城融合场景振动谱分析（湖州南浔站）', y=0.995, fontsize=14)
plt.savefig(os.path.join(OUT, '_scene_final.png'), dpi=130, bbox_inches='tight')
plt.close()
print(f'\nFinal figure: {os.path.join(OUT, "_scene_final.png")}')

# --- Text summary of group means ---
print('\n=== Group statistics (RMS, Peak, Duration, Dominant freq) ===')
summary = all_df.groupby(['category', 'kind']).agg(
    n=('rms', 'count'),
    rms_mean=('rms', 'mean'),
    rms_std=('rms', 'std'),
    peak_mean=('peak', 'mean'),
    dom_freq_median=('dominant_freq', 'median'),
).round(4)
print(summary.to_string())
summary.to_csv(os.path.join(BASE, 'final_group_summary.csv'), encoding='utf-8-sig')
