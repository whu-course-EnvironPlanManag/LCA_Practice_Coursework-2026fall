# -*- coding: utf-8 -*-
"""
重绘：工业园区 10 万吨/年绿色甲醇系统 MFA-EFA 拓扑图（直线/90° 折线版）
要求：流程线路不弯曲、简洁明了；保留原图信息与配色。
输出：figures_output/fig1_mfa_process_flow_rect.png
"""

import sys
import io
import os

if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Noto Sans CJK SC']
plt.rcParams['axes.unicode_minus'] = False

# 配色（与原图一致）
C_CO2   = '#d97706'; F_CO2   = '#fff3e8'; T_CO2   = '#713f12'
C_H2    = '#25834b'; F_H2    = '#eaf7ef'; T_H2    = '#174b2d'
C_WATER = '#2879a5'; F_WATER = '#eaf4fb'; T_WATER = '#174d69'
C_PROC  = '#45616b'; F_PROC  = '#f3f6f7'; T_PROC  = '#19313a'
C_PROD  = '#8a4c9e'; F_PROD  = '#f6eff8'; T_PROD  = '#542b64'
C_PURGE = '#c43d3d'; F_PURGE = '#fff0ef'; T_PURGE = '#742626'
C_RECY  = '#148a78'
C_MAIN  = '#536a73'
TITLE_C = '#19313a'

fig, ax = plt.subplots(figsize=(16, 9))
ax.set_xlim(0, 100)
ax.set_ylim(0, 56.25)
ax.axis('off')


def box(x0, y0, x1, y1, edge, fill, lw=1.8):
    """圆角矩形节点框"""
    w, h = x1 - x0, y1 - y0
    b = FancyBboxPatch((x0, y0), w, h,
                       boxstyle='round,pad=0.25,rounding_size=1.0',
                       linewidth=lw, edgecolor=edge, facecolor=fill, zorder=2)
    ax.add_patch(b)


def lines(pts, color, lw, ls='-'):
    """多段 90° 折线（不带箭头）"""
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    ax.plot(xs, ys, color=color, lw=lw, ls=ls, zorder=1,
           solid_capstyle='butt', dash_capstyle='butt')


def arrow_to(prev, end, color, lw, ls='-'):
    """末端箭头（在最后一段上加箭头）"""
    ax.annotate('', xy=end, xytext=prev, zorder=3,
                arrowprops=dict(arrowstyle='-|>', color=color, lw=lw,
                                linestyle=ls, shrinkA=0, shrinkB=0,
                                mutation_scale=16))


def flow(pts, color, lw, ls='-'):
    """折线 + 末端箭头"""
    lines(pts, color, lw, ls)
    if len(pts) >= 2:
        arrow_to(pts[-2], pts[-1], color, lw, ls)


def label(x, y, text, size=10.5, color=TITLE_C, ha='left', weight='normal', z=4, bg=False):
    bbox = None
    if bg:
        bbox = dict(boxstyle='square,pad=0.12', facecolor='white', edgecolor='none')
    ax.text(x, y, text, fontsize=size, color=color, ha=ha, va='center',
            zorder=z, fontweight=weight, bbox=bbox)


def inside(x_center, y_top, lines_txt, size=9.5, color=TITLE_C, lh=2.6):
    """框内自上而下多行文本"""
    n = len(lines_txt)
    y = y_top - 1.4
    for i, t in enumerate(lines_txt):
        ax.text(x_center, y - i * lh, t, fontsize=size, color=color,
                ha='center', va='center', zorder=4)


# ================= 标题与副标题 =================
label(50, 54.6, '工业园区 10 万吨/年绿色甲醇系统物质与能量流向拓扑图（MFA-EFA）',
      size=19, ha='center', weight='bold')
label(50, 51.6, '锚点 B：绿电 100.00% ｜ 驰放比 2.16% ｜ 年产 100,000 t ｜ 全厂电耗 10.926 亿 kWh/a ｜ 碳利用率 93.92%',
      size=12, ha='center', color='#3d5560')

# ================= 主流程节点（中排） =================
# ① 碳捕集
box(10, 24, 30, 40, C_CO2, F_CO2)
label(20, 38.1, '① 碳捕集', size=13, color=T_CO2, ha='center', weight='bold')
inside(20, 36.0, ['烟气 CO2 捕集与压缩单元',
                  'MEA 化学吸收 + 三级压缩（5.0 MPa）',
                  '电耗：0.262 亿 kWh/a（2.4%）'], size=9.5, color=T_CO2)
label(4.9, 36.6, '新鲜 CO2\n14.62 万吨/a', size=9.5, color=T_CO2, ha='center', bg=True)
label(4.9, 28.6, '工业点源烟气\nCO2 原料', size=9.5, color=T_CO2, ha='center', bg=True)

# 预热器
box(33, 24, 49, 40, C_PROC, F_PROC)
label(41, 38.1, '反应进料混合预热器', size=11.5, color=T_PROC, ha='center', weight='bold')
inside(41, 35.4, ['新鲜进料+循环气 230℃，5.0 MPa'], size=9.5, color=T_PROC)

# 反应器
box(53, 24, 67, 40, C_PROC, F_PROC)
label(60, 38.1, '③ 催化合成', size=11.5, color=T_PROC, ha='center', weight='bold')
inside(60, 35.4, ['固定床甲醇合成反应器',
                  'Cu/ZnO/Al2O3 催化剂',
                  '单程转化率 25%'], size=9.5, color=T_PROC)

# 分离器
box(71, 24, 86, 40, C_PROC, F_PROC)
label(78.5, 38.1, '冷凝分离与循环分流器', size=11.5, color=T_PROC, ha='center', weight='bold')
inside(78.5, 35.4, ['气液闪蒸分离',
                    '质量循环比 2.76:1 ｜驰放 2.16%',
                    '电耗：0.094 亿 kWh/a（0.9%）'], size=9.5, color=T_PROC)

# 双塔精馏
box(88, 19.5, 99, 34, C_PROD, F_PROD)
label(93.5, 31.8, '④ 双塔精馏', size=12, color=T_PROD, ha='center', weight='bold')
inside(93.5, 29.8, ['双塔精馏分离系统',
                    '常压脱轻 + 加压脱水塔',
                    '甲醇纯度 ≥ 99.85 wt%',
                    '电耗：0.120 亿 kWh/a（1.1%）'], size=9, color=T_PROD, lh=2.4)

# ================= 制氢分支（下排，与底部汇总框保持分离） =================
box(10, 6.5, 29, 16.5, C_WATER, F_WATER)
label(19.5, 14.7, '园区新鲜脱盐水', size=11, color=T_WATER, ha='center', weight='bold')
inside(19.5, 12.3, ['13.85 万吨/a（71.1%）'], size=9.5, color=T_WATER)

box(35, 6.5, 53, 20.5, C_H2, F_H2)
label(44, 18.6, '② PEM 电解水制氢站', size=12, color=T_H2, ha='center', weight='bold')
inside(44, 17.0, ['PEM 电解槽总进水 19.47 万吨/a',
                  '[新鲜水 71.1% + 回用水 28.9%]',
                  '质子交换膜阵列（3.0 MPa）',
                  '电耗：10.450 亿 kWh/a（95.6%）'], size=8.8, color=T_H2, lh=2.4)

box(58, 6.5, 70, 16.5, C_H2, F_H2)
label(64, 14.9, '阳极副产纯氧（外售）', size=10, color=T_H2, ha='center', weight='bold')
inside(64, 12.3, ['15.84 万吨/a'], size=9.5, color=T_H2)

# 产品
box(88, 8.5, 99, 17.5, C_PROD, F_PROD)
label(93.5, 15.5, '聚合级精甲醇', size=11.5, color=T_PROD, ha='center', weight='bold')
inside(93.5, 13.6, ['10.00 万吨/a（≥99.85%）'], size=9.5, color=T_PROD)

# 驰放尾气
box(74, 43, 87, 49, C_PURGE, F_PURGE)
label(80.5, 47.4, '驰放尾气（2.16%）', size=10.5, color=T_PURGE, ha='center', weight='bold')
inside(80.5, 46.0, ['1.011 万吨/a 送末端处置'], size=9, color=T_PURGE)

# ================= 流程连线（全部直线/90° 折线） =================
# 1. 烟气 → 碳捕集（CO₂ 橙色）
flow([(2.2, 31.2), (10, 31.2)], C_CO2, 4.0)

# 2. 碳捕集 → 预热器（CO₂）
flow([(30, 33), (33, 33)], C_CO2, 4.0)
label(20, 43.2, '捕集 CO2 14.62 万吨/a', size=10, color=T_CO2, ha='center', bg=True)

# 3. PEM → 预热器（绿氢，90° 折线）
flow([(44, 20.5), (44, 23.2), (39, 23.2), (39, 24)], C_H2, 2.2)
label(50.5, 22.2, '电解绿氢 2.01 万吨/a', size=10, color=T_H2, ha='center', bg=True)

# 4. 预热器 → 反应器（主工艺流）
flow([(49, 33), (53, 33)], C_MAIN, 4.0)
label(49, 41.5, '反应器入口 62.49', size=9.5, color=T_PROC, ha='center', bg=True)

# 5. 反应器 → 分离器（主工艺流）
flow([(67, 33), (71, 33)], C_MAIN, 4.0)
label(65.6, 41.5, '反应器出口 62.49', size=9.5, color=T_PROC, ha='center', bg=True)

# 6. 分离器 → 精馏（粗甲醇，紫色）
flow([(86, 30), (88, 30)], C_PROD, 4.0)
label(93.5, 36.2, '粗甲醇液相 15.62 万吨/a', size=9.5, color=T_PROD, ha='center', bg=True)

# 7. 精馏 → 产品（甲醇）
flow([(93.5, 20), (93.5, 17.5)], C_PROD, 4.0)

# 8. 分离器 → 驰放（红色）
flow([(78.5, 40), (78.5, 43)], C_PURGE, 2.2)

# 9. 循环气回流（青色虚线，90° 折线：上→左→下，与入口/出口标签保持间距）
flow([(72.5, 40), (72.5, 44), (41, 44), (41, 40)], C_RECY, 5.0, ls='--')
label(59.5, 47.6, '未反应气体循环回流（97.84%）45.86 万吨/a', size=10.5, color='#0e6156', ha='center', bg=True)

# 10. 精馏产水回用（蓝色虚线，90° 折线：左→下）
flow([(88, 20), (53, 20), (53, 20.5)], C_WATER, 2.6, ls='--')
label(70, 18.7, '精馏产水回用至电解槽（28.9%）5.62 万吨/a', size=10, color=T_WATER, ha='center', bg=True)

# 11. 脱盐水 → PEM
flow([(29, 11.5), (35, 11.5)], C_WATER, 3.5)

# 12. PEM → 副产氧
flow([(53, 11.5), (58, 11.5)], C_H2, 2.2)

# ================= 图例（右上） =================
legend_items = [
    ('—', C_CO2, 'CO2 质量流'),
    ('—', C_WATER, '水质量流'),
    ('—', C_PROD, '甲醇物流'),
    ('—', C_H2, 'H2 质量流'),
    ('- -', C_RECY, '未反应气回流'),
    ('—', C_PURGE, '驰放流'),
]
lx, ly = 89.5, 53.5
label(lx, ly, '图例', size=10, color=TITLE_C, weight='bold', ha='left')
for i, (sym, col, txt) in enumerate(legend_items):
    yy = ly - 1.7 - i * 1.9
    ax.plot([lx, lx + 2.6], [yy, yy], color=col, lw=2.2, ls='solid' if sym == '—' else 'dashed', zorder=1)
    label(lx + 3.1, yy, txt, size=9, color=TITLE_C, ha='left')
label(lx, ly - 1.7 - 6 * 1.9, '质量流线宽与通量成正比', size=9, color='#3d5560', ha='left')

# ================= 底部汇总（与流程图主体分离） =================
box(2, 0.2, 98, 5.2, '#b8c8ce', '#fafcfd', lw=1.2)
label(3, 3.75, '【锚点 B：10 万吨/年主物流与能耗】', size=10.5, color=TITLE_C, weight='bold', ha='left')
label(33, 3.75, 'CO2 捕集 14.62 ｜ 绿氢 2.01 ｜ 新鲜水 13.85 ｜ 精馏水回用 5.62 ｜ 循环气 45.86 ｜ 驰放气 1.011 ｜ 副产氧 15.84 万吨/a',
      size=10, color=TITLE_C, ha='left')
label(3, 1.5, '总电耗 10.926 亿 kWh/a（分项：捕集 0.262 ｜ 制氢 10.450 ｜ 循环 0.094 ｜ 精馏 0.120 亿 kWh/a）',
      size=10, color=TITLE_C, ha='left')

# ================= 保存 =================
out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'figures_output')
out_dir = os.path.abspath(out_dir)
out_path = os.path.join(out_dir, 'fig1_mfa_process_flow_rect.png')
fig.savefig(out_path, dpi=300, bbox_inches='tight', facecolor='white')
print('saved:', out_path)
