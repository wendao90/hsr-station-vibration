"""
Generate paper-ready schematic of 湖州南浔站 with measurement points.

Position convention (per user clarification):
  - M1 (service desk) and M2 (ground floor rear) are both slightly LEFT of center axis
  - M1-M2 connecting line is parallel to the central N-S axis
  - M1 is on the NORTH side (plaza-facing), M2 is on the SOUTH side (track-facing)
  - M3 is on the platform

Style notes:
  - No uncertain numeric dimensions
  - Colour block style
  - Section view uses EW direction (track direction along the page)
    because that is more intuitive for showing train motion + bridge piers + roof
"""
import os, sys, io
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
except Exception:
    pass
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch, Polygon, Ellipse, Circle
from matplotlib.patches import FancyBboxPatch
from matplotlib import rcParams

rcParams['font.sans-serif'] = ['Microsoft YaHei', 'DejaVu Sans']
rcParams['axes.unicode_minus'] = False

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, 'figures')
os.makedirs(OUT, exist_ok=True)

# ============================================================
# FIGURE 1: PLAN VIEW (top-down)
# ============================================================
fig, ax = plt.subplots(1, 1, figsize=(11, 8))
ax.set_aspect('equal')

STATION_W = 20
STATION_D = 5

# Station square (plaza) - north side
plaza = Rectangle((-STATION_W*0.65, STATION_D/2), STATION_W*1.3, 6,
                    facecolor='#d4e5d0', edgecolor='#7a8d75', linewidth=0.8)
ax.add_patch(plaza)
ax.text(0, STATION_D/2 + 3, '站前广场', ha='center', va='center', fontsize=11, color='#4a5d45')

# Main building with curved north face
nx = np.linspace(-STATION_W/2, STATION_W/2, 40)
ny = STATION_D/2 + 0.8 * np.sin(np.pi * (nx + STATION_W/2) / STATION_W)
building_top = list(zip(nx, ny))
building_pts = [(STATION_W/2, -STATION_D/2)] + building_top[::-1] + [(-STATION_W/2, -STATION_D/2)]
building = Polygon(building_pts, facecolor='#f0ece3', edgecolor='#8b7d6b', linewidth=1.2, zorder=3)
ax.add_patch(building)

ax.text(3.5, 0, '候车大厅\n(Waiting Hall)', ha='center', va='center',
        fontsize=11, color='#4a4a4a', weight='bold', zorder=4)

# Central axis
ax.plot([0, 0], [-STATION_D/2 + 0.1, STATION_D/2 - 0.1], ':', color='#aaa', linewidth=0.8)
ax.text(0.15, STATION_D/2 - 0.4, '中心线', fontsize=7, color='#888', zorder=4)

# M1 and M2 both slightly left of center, on a common N-S line
axis_x = -1.5
m1_x, m1_y = axis_x, 1.3
m2_x, m2_y = axis_x, -1.3

ax.plot([m1_x, m2_x], [m1_y, m2_y], '--', color='#555', linewidth=0.8, alpha=0.6, zorder=4)
ax.text(m1_x - 0.3, 0, 'M1-M2\n连线', fontsize=7, color='#555', ha='right', va='center',
         rotation=90, zorder=4, alpha=0.8)

# M1
ax.plot(m1_x, m1_y, 'o', markersize=20, markerfacecolor='#f0a050',
         markeredgecolor='#8b4513', markeredgewidth=2, zorder=5)
ax.text(m1_x, m1_y, 'M1', ha='center', va='center', fontsize=10, weight='bold', color='white', zorder=6)
ax.annotate('服务台测点 M1\n(Service desk, 近广场)',
             xy=(m1_x, m1_y), xytext=(m1_x - 7, m1_y + 1.5),
             fontsize=9, ha='left',
             arrowprops=dict(arrowstyle='->', color='#8b4513', lw=1.2),
             bbox=dict(boxstyle='round', facecolor='#fff5e0', edgecolor='#f0a050'))

# M2
ax.plot(m2_x, m2_y, 'o', markersize=20, markerfacecolor='#78c896',
         markeredgecolor='#2d5540', markeredgewidth=2, zorder=5)
ax.text(m2_x, m2_y, 'M2', ha='center', va='center', fontsize=10, weight='bold', color='white', zorder=6)
ax.annotate('地面测点 M2\n(Ground floor, 近站台/服务台正后方)',
             xy=(m2_x, m2_y), xytext=(m2_x - 9, m2_y - 2),
             fontsize=9, ha='left',
             arrowprops=dict(arrowstyle='->', color='#2d5540', lw=1.2),
             bbox=dict(boxstyle='round', facecolor='#e0f0e4', edgecolor='#78c896'))

# 检票口 1A / 1B
for gx, gy, lbl in [(-2, -STATION_D/2 + 0.4, '1A'), (2, -STATION_D/2 + 0.4, '1B')]:
    ax.plot(gx, gy, 's', markersize=9, color='#7aa2d2', zorder=4)
    ax.text(gx, gy - 0.5, lbl + '检票口', ha='center', va='top', fontsize=8, color='#4a6680')

# Platforms and tracks
plat_y_top = -STATION_D/2 - 0.5
plat = Rectangle((-STATION_W/2 - 1, plat_y_top - 4), STATION_W + 2, 4,
                   facecolor='#e8e8e8', edgecolor='#8a8a8a', linewidth=0.8)
ax.add_patch(plat)

n_tracks = 5
y_tracks_top = plat_y_top - 0.4
for i in range(n_tracks):
    y_t = y_tracks_top - i * 0.7
    ax.plot([-STATION_W/2 - 0.5, STATION_W/2 + 0.5], [y_t, y_t], '-',
             color='#555', linewidth=1.2)
    for x_tie in np.linspace(-STATION_W/2, STATION_W/2, 25):
        ax.plot([x_tie, x_tie], [y_t - 0.08, y_t + 0.08], '-', color='#8a6d48', linewidth=0.6)

ax.text(-STATION_W/2 - 1.8, plat_y_top - 0.8, '侧式站台', rotation=90, fontsize=8, ha='center', va='center')
ax.text(-STATION_W/2 - 1.8, plat_y_top - 2.5, '岛式站台', rotation=90, fontsize=8, ha='center', va='center')

# M3 站台测点
pt_x, pt_y = 3, plat_y_top - 1.3
ax.plot(pt_x, pt_y, 'o', markersize=20, markerfacecolor='#a78bfa',
         markeredgecolor='#4c3585', markeredgewidth=2, zorder=5)
ax.text(pt_x, pt_y, 'M3', ha='center', va='center', fontsize=10, weight='bold', color='white', zorder=6)
ax.annotate('站台测点 M3\n(Platform)',
             xy=(pt_x, pt_y), xytext=(pt_x + 3, pt_y - 1.2),
             fontsize=9, ha='left',
             arrowprops=dict(arrowstyle='->', color='#4c3585', lw=1.2),
             bbox=dict(boxstyle='round', facecolor='#ece5ff', edgecolor='#a78bfa'))

# Train direction arrows
for i, y_off in enumerate([-0.3, -3.5]):
    ax.annotate('', xy=(STATION_W/2 + 2, y_tracks_top + y_off),
                xytext=(STATION_W/2 + 0.2, y_tracks_top + y_off),
                arrowprops=dict(arrowstyle='->', color='#c54a4a', lw=1.5))
ax.text(STATION_W/2 + 1.8, y_tracks_top - 1.5, '列车方向', fontsize=9, color='#a54545')

# Compass
ax.plot([STATION_W/2 + 3.5, STATION_W/2 + 3.5], [0, 2], '-', color='#333', linewidth=1.5)
ax.annotate('', xy=(STATION_W/2 + 3.5, 2.5), xytext=(STATION_W/2 + 3.5, 0),
             arrowprops=dict(arrowstyle='->', color='#333', lw=2))
ax.text(STATION_W/2 + 3.5, 2.8, 'N', fontsize=11, ha='center', weight='bold')

ax.text(0, STATION_D/2 + 7.4, '湖州南浔站  平面示意图', ha='center', fontsize=13, weight='bold')
ax.text(0, STATION_D/2 + 6.6, '(沪苏湖高铁, 线正下+局部线侧下式, 桥建合一)',
         ha='center', fontsize=10, style='italic', color='#666')

# Legend
legend_x = -STATION_W/2 - 3
legend_y = STATION_D/2 + 5.5
legends = [
    ('#f0a050', 'M1 服务台测点'),
    ('#78c896', 'M2 地面测点(正后方)'),
    ('#a78bfa', 'M3 站台测点'),
]
for i, (col, lbl) in enumerate(legends):
    ax.plot(legend_x, legend_y - i*0.5, 'o', markersize=10, markerfacecolor=col, markeredgecolor='black')
    ax.text(legend_x + 0.5, legend_y - i*0.5, lbl, fontsize=9, va='center')

ax.set_xlim(-STATION_W/2 - 7, STATION_W/2 + 6)
ax.set_ylim(plat_y_top - 5, STATION_D/2 + 9)
ax.set_xticks([]); ax.set_yticks([])
for spine in ax.spines.values(): spine.set_visible(False)

plt.tight_layout()
plt.savefig(os.path.join(OUT, 'schematic_plan.png'), dpi=150, bbox_inches='tight')
plt.close()
print(f'[OK] {os.path.join(OUT, "schematic_plan.png")}')


# ============================================================
# FIGURE 2: SECTION VIEW — EW DIRECTION (track direction along the page)
# Bridge piers, train, curved roof all in the original (EW) orientation.
# M1 and M2 are NS-aligned, so in this section they project to ~same horizontal position;
# shown as two markers close together at ground level, with M2 indicated as "behind" M1.
# ============================================================
fig, ax = plt.subplots(1, 1, figsize=(12, 6.5))

# Ground
ground_y = 0
ax.fill_between([-12, 12], -1, ground_y, color='#c9b98d', alpha=0.6)
ax.plot([-12, 12], [ground_y, ground_y], '-', color='#8b7355', linewidth=1.5)
ax.text(-11.5, -0.6, '地面', fontsize=9, color='#6b5a45')

# Station building
bldg_x_left, bldg_x_right = -8, 8
floor1_y = 4
ax.plot([bldg_x_left, bldg_x_left], [0, floor1_y], '-', color='#8b7d6b', linewidth=1.5)
ax.plot([bldg_x_right, bldg_x_right], [0, floor1_y], '-', color='#8b7d6b', linewidth=1.5)
ax.plot([bldg_x_left, bldg_x_right], [floor1_y, floor1_y], '-', color='#8b7d6b', linewidth=2.5)
ax.fill_between([bldg_x_left, bldg_x_right], 0, floor1_y, color='#faf7f0', alpha=0.5)

ax.text(0, floor1_y/2 + 0.8, '候车大厅 (1F)', ha='center', fontsize=12, weight='bold')
ax.text(0, floor1_y/2 + 0.1, 'Waiting Hall  @ 地面层', ha='center', fontsize=9, style='italic', color='#666')

# Platform level (2F) slab
plat_y_bot = floor1_y
plat_y_top = floor1_y + 0.3
ax.fill_between([bldg_x_left - 2, bldg_x_right + 2], plat_y_bot, plat_y_top, color='#777', alpha=0.7)
for x in np.arange(bldg_x_left, bldg_x_right + 1, 0.3):
    ax.plot([x, x], [plat_y_bot, plat_y_top], '-', color='#555', linewidth=0.3, alpha=0.6)

# Tracks on top
track_y = plat_y_top + 0.05
ax.plot([bldg_x_left - 2, bldg_x_right + 2], [track_y, track_y], '-', color='#333', linewidth=1.5)
ax.plot([bldg_x_left - 2, bldg_x_right + 2], [track_y + 0.15, track_y + 0.15], '-', color='#333', linewidth=1.5)
for x in np.arange(bldg_x_left - 1.5, bldg_x_right + 1.5, 0.4):
    ax.plot([x, x], [track_y - 0.08, track_y + 0.23], '-', color='#6b5a45', linewidth=0.5)

# Train (moves along the page)
train_x = 2
train = FancyBboxPatch((train_x, track_y + 0.2), 3.5, 0.7,
                        boxstyle='round,pad=0.02', facecolor='#c54a4a',
                        edgecolor='#883030', linewidth=1.5)
ax.add_patch(train)
ax.text(train_x + 1.75, track_y + 0.55, 'HSR 列车', ha='center', fontsize=9, color='white', weight='bold')
for wx in np.arange(train_x + 0.2, train_x + 3.3, 0.5):
    ax.add_patch(Rectangle((wx, track_y + 0.45), 0.3, 0.2, facecolor='#ffeecc', edgecolor='#883030', linewidth=0.3))

# Platform walkway indicator
ax.plot([bldg_x_left - 2, bldg_x_right + 2], [plat_y_top + 0.6, plat_y_top + 0.6], ':', color='#888', linewidth=0.8)
ax.text(-6, plat_y_top + 0.75, '站台面', fontsize=8, color='#666')

# Bridge piers (supporting the track slab)
for pier_x in [-6, -2, 2, 6]:
    col = Rectangle((pier_x - 0.3, 0), 0.6, floor1_y,
                     facecolor='#a89070', edgecolor='#6b5a45', linewidth=1)
    ax.add_patch(col)
ax.text(-6, 2, '桥\n墩', ha='center', va='center', fontsize=7, color='#6b5a45', alpha=0.8)

# Curved roof (EW direction, as originally)
roof_x = np.linspace(bldg_x_left - 1, bldg_x_right + 1, 50)
roof_y_top = plat_y_top + 3
roof_y = roof_y_top - 0.8 * np.sin(np.pi * (roof_x - bldg_x_left + 1) / (bldg_x_right - bldg_x_left + 2))
ax.fill_between(roof_x, plat_y_top + 1.5, roof_y, color='#d6d2c8', alpha=0.5)
ax.plot(roof_x, roof_y, '-', color='#6b5a45', linewidth=1.5)
ax.text(0, plat_y_top + 2.5, '弧形屋面 (泛舟水乡造型)', ha='center', fontsize=8, color='#6b5a45', style='italic')

# Train direction arrow (on track, pointing along track)
ax.annotate('', xy=(bldg_x_right + 2.3, track_y + 0.55), xytext=(bldg_x_right + 0.5, track_y + 0.55),
             arrowprops=dict(arrowstyle='->', color='#c54a4a', lw=2))
ax.text(bldg_x_right + 1.5, track_y + 0.95, '列车方向', ha='center', fontsize=9, color='#a54545')

# --- Measurement points ---
# M1/M2 are NS-aligned (different positions in the page-perpendicular direction),
# so in this section they collapse to ~same horizontal position (slightly left of center).
# Show them as two stacked (front/back) markers with a note.
m_x_sec = -1.5  # slightly left of center
# M1 (closer to viewer = front) and M2 (farther from viewer = back)
m1_sec_y = 0.3
m2_sec_y = 0.3  # same height

# Draw M2 first (behind, slightly lighter) - offset a bit up-left to suggest "behind"
ax.plot(m_x_sec - 0.15, m2_sec_y + 0.05, 'o', markersize=20, markerfacecolor='#78c896',
         markeredgecolor='#2d5540', markeredgewidth=2, zorder=9, alpha=0.7)
ax.text(m_x_sec - 0.15, m2_sec_y + 0.05, 'M2', ha='center', va='center',
         fontsize=9, weight='bold', color='white', zorder=10, alpha=0.9)

# Draw M1 in front
ax.plot(m_x_sec + 0.15, m1_sec_y - 0.05, 'o', markersize=20, markerfacecolor='#f0a050',
         markeredgecolor='#8b4513', markeredgewidth=2, zorder=10)
ax.text(m_x_sec + 0.15, m1_sec_y - 0.05, 'M1', ha='center', va='center',
         fontsize=9, weight='bold', color='white', zorder=11)

# Combined annotation
ax.annotate('M1 服务台 / M2 地面正后方\n(均位于地面层；在剖面方向上\n投影至近似同一点)',
             xy=(m_x_sec, m1_sec_y),
             xytext=(m_x_sec - 7, m1_sec_y + 1.5),
             fontsize=9, ha='left',
             arrowprops=dict(arrowstyle='->', color='#555', lw=1.2),
             bbox=dict(boxstyle='round', facecolor='#f7f3ec', edgecolor='#888'))

# M3 站台
m3_x, m3_y = -3.5, plat_y_top + 0.55
ax.plot(m3_x, m3_y, 'o', markersize=20, markerfacecolor='#a78bfa',
         markeredgecolor='#4c3585', markeredgewidth=2, zorder=10)
ax.text(m3_x, m3_y, 'M3', ha='center', va='center', fontsize=10, weight='bold', color='white', zorder=11)
ax.annotate('站台测点 M3', xy=(m3_x, m3_y), xytext=(m3_x - 2.5, m3_y + 2.3),
             fontsize=10, ha='left',
             arrowprops=dict(arrowstyle='->', color='#4c3585', lw=1.2),
             bbox=dict(boxstyle='round', facecolor='#ece5ff', edgecolor='#a78bfa'))

# Vibration transmission arrows (from train down through slab + piers)
for xx in [train_x + 0.5, train_x + 2.0, train_x + 3.0]:
    ax.annotate('', xy=(xx, 0.6), xytext=(xx, track_y),
                 arrowprops=dict(arrowstyle='wedge,tail_width=0.3', color='#e87060', alpha=0.35))
ax.text(train_x + 1.75, 2.0, '车致振动\n传导路径', ha='center', fontsize=9,
         color='#883030', style='italic', alpha=0.8)

# Title
ax.text(0, roof_y_top + 0.9, '湖州南浔站  剖面示意图 (线正下式桥建合一)',
         ha='center', fontsize=13, weight='bold')
ax.text(0, roof_y_top + 0.25, 'Section schematic — tracks above, waiting hall directly below',
         ha='center', fontsize=9, style='italic', color='#666')

ax.set_xlim(-14, 14)
ax.set_ylim(-1.5, roof_y_top + 2)
ax.set_aspect('equal')
ax.set_xticks([]); ax.set_yticks([])
for spine in ax.spines.values(): spine.set_visible(False)

plt.tight_layout()
plt.savefig(os.path.join(OUT, 'schematic_section.png'), dpi=150, bbox_inches='tight')
plt.close()
print(f'[OK] {os.path.join(OUT, "schematic_section.png")}')
