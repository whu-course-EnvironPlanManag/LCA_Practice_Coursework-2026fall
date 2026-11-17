#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
第九讲 案例二 任务 3：含未反应气循环回路（Recycle Loop）的工艺物质流程图

图的三大信息层：
  1. 主物流链：烟气 CO2 捕集 → 三级压缩 → 混合预热 → 固定床合成 → 冷凝气液分离 → 双塔精馏 → 精甲醇
  2. 内循环控制体：分离器顶气 4,686 kg → 分流器 99% 循环 / 1% 驰放 → 循环压缩机 → 回到混合器
  3. 公用工程耦合：PEM 电解槽（H2 上行、O2 外售、精馏釜水回流补水）

运行：
    python plot_case2_process.py
输出：
    process_flow_diagram_case2.png  (300 dpi)
    process_flow_diagram_case2.svg  (矢量)
"""

from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.lines import Line2D

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "SimSun", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["svg.fonttype"] = "none"

OUT = Path(__file__).resolve().parent

C_MAIN = "#2c5f8d"      # 气相主物流
C_LIQ = "#1f7a5c"       # 液相物流
C_LOOP = "#b5651d"      # 循环回路
C_UTIL = "#8d2c5f"      # 公用工程 / 副产
C_TEXT = "#22303c"

FILL = {"gas": "#eaf2fa", "liq": "#e8f4ee", "loop": "#fdf0e2",
        "util": "#f8ecf3", "prod": "#eef4e5", "dark": "#e6e9ee"}


def box(ax, x, y, w, h, text, kind="gas", fs=10.5, bold=False):
    ax.add_patch(FancyBboxPatch(
        (x - w / 2, y - h / 2), w, h,
        boxstyle="round,pad=0.05,rounding_size=0.14",
        linewidth=1.5, edgecolor=C_TEXT, facecolor=FILL[kind], zorder=3))
    ax.text(x, y, text, ha="center", va="center", fontsize=fs, color=C_TEXT,
            zorder=4, linespacing=1.45,
            fontweight="bold" if bold else "normal")


def arrow(ax, p0, p1, color=C_MAIN, lw=1.9, ls="-", zorder=2):
    ax.add_patch(FancyArrowPatch(
        p0, p1, arrowstyle="-|>", mutation_scale=15,
        linewidth=lw, color=color, linestyle=ls,
        shrinkA=0, shrinkB=0, zorder=zorder))


def flow_label(ax, x, y, text, color=C_TEXT, fs=9.5, ha="center", va="center", rot=0):
    ax.text(x, y, text, fontsize=fs, color=color, ha=ha, va=va, rotation=rot,
            zorder=6, linespacing=1.35,
            bbox=dict(boxstyle="round,pad=0.22", facecolor="white",
                      edgecolor="none", alpha=0.92))


fig, ax = plt.subplots(figsize=(18.4, 9.8))
ax.set_xlim(0.0, 19.2)
ax.set_ylim(1.5, 11.2)
ax.axis("off")

# ---------------------------------------------------------------- 主物流链
box(ax, 2.3, 7.6, 2.6, 1.9,
    "烟气 CO$_2$ 捕集\n(MEA 化学吸收 + 提纯)\n纯度 > 99.5%", "gas")
box(ax, 5.3, 7.6, 2.2, 1.9,
    "三级压缩\n5.0 MPa\n超临界进料", "gas")
box(ax, 8.0, 7.6, 2.0, 1.9,
    "混合器\n+ 预热器 230 ℃", "gas")
box(ax, 10.9, 7.6, 2.7, 2.1,
    "固定床合成反应器\nCu/ZnO/Al$_2$O$_3$, 250 ℃, 5.0 MPa\n单程转化率 $X_{sp}$ = 25%", "gas", fs=9.5)
box(ax, 13.8, 7.6, 2.4, 2.1,
    "冷凝器 +\n高压气液分离器\n45 ℃, 4.8 MPa", "gas")
box(ax, 16.9, 5.0, 2.5, 2.0,
    "双塔精馏\n脱轻塔 + 加压脱水塔\n纯度 > 99.85%", "liq")

# ---------------------------------------------------------------- 公用工程
box(ax, 5.3, 4.3, 2.9, 1.9,
    "PEM 电解水制氢\n130 MW, 52 kWh/kg H$_2$\nH$_2$ 198 kg/t", "util")
box(ax, 8.6, 4.3, 2.6, 1.4,
    "副产高纯 O$_2$\n1,584 kg/t（外售）", "util", fs=10)
box(ax, 16.2, 2.85, 2.5, 1.1,
    "精甲醇产品\n1,000 kg/t", "prod", fs=10.5, bold=True)

# ---------------------------------------------------------------- 循环回路
box(ax, 13.8, 10.4, 1.9, 1.0, "分流器\n99% 循环 / 1% 驰放", "loop", fs=9.5)
box(ax, 10.6, 10.4, 2.2, 1.0, "循环压缩机", "loop")
box(ax, 17.3, 10.4, 2.7, 1.0, "厂内锅炉\n驰放气燃烧供热", "dark", fs=9.5)

# ---------------------------------------------------------------- 主链箭头
arrow(ax, (0.9, 7.6), (1.0, 7.6), C_MAIN)
flow_label(ax, 1.15, 8.85, "烟气 CO$_2$\n1,423 kg/t", C_MAIN, 9.5, ha="left")
arrow(ax, (3.6, 7.6), (4.2, 7.6), C_MAIN)
arrow(ax, (6.4, 7.6), (7.0, 7.6), C_MAIN)
arrow(ax, (9.0, 7.6), (9.7, 7.6), C_MAIN)
arrow(ax, (12.1, 7.6), (12.6, 7.6), C_MAIN)
flow_label(ax, 10.4, 8.95, "反应器入口混合气  6,261 kg/t", C_LOOP, 9.5)

# ---------------------------------------------------------------- 分离器 → 分流器（气相）
arrow(ax, (13.8, 8.65), (13.8, 9.9), C_LOOP)
flow_label(ax, 14.95, 9.25, "未冷凝气相\n4,686 kg/t", C_LOOP, 9.5, ha="left")

# 循环气：分流器 → 循环压缩机 → 混合器
arrow(ax, (12.85, 10.4), (11.7, 10.4), C_LOOP)
flow_label(ax, 12.28, 10.72, "循环气\n4,640 kg/t", C_LOOP, 9)
arrow(ax, (9.5, 10.4), (8.0, 10.4), C_LOOP)
arrow(ax, (8.0, 10.4), (8.0, 8.55), C_LOOP)
flow_label(ax, 6.55, 10.4, "循环比（入口气/新鲜气）≈ 3.8 : 1", C_LOOP, 10, ha="right")

# 驰放气：分流器 → 锅炉
arrow(ax, (14.75, 10.4), (15.95, 10.4), "#8a3b12")
flow_label(ax, 15.35, 10.78, "驰放 1%\n46 kg/t", "#8a3b12", 9)

# ---------------------------------------------------------------- 分离器 → 精馏（液相粗甲醇）
arrow(ax, (13.8, 6.55), (13.8, 5.0), C_LIQ)
arrow(ax, (13.8, 5.0), (15.65, 5.0), C_LIQ)
flow_label(ax, 13.1, 5.42, "粗甲醇\n1,575 kg/t", C_LIQ, 9.5, ha="right")

# 精馏 → 产品
arrow(ax, (16.9, 4.0), (16.9, 3.42), C_LIQ)
flow_label(ax, 17.9, 3.75, "1,000 kg/t\n99.85 wt%", C_LIQ, 9.5, ha="left")

# ---------------------------------------------------------------- 电解槽 → 混合器（H2）
arrow(ax, (5.3, 5.25), (5.3, 6.55), C_UTIL)
arrow(ax, (5.3, 6.55), (8.0, 6.55), C_UTIL)
arrow(ax, (8.0, 6.55), (8.0, 6.65), C_UTIL)
flow_label(ax, 6.35, 6.18, "绿氢 H$_2$ 198 kg/t", C_UTIL, 9.5)

# 纯水进料
arrow(ax, (0.9, 4.3), (3.85, 4.3), C_LIQ)
flow_label(ax, 1.0, 4.85, "除盐纯水 1,960 kg/t\n净补水 1,385 + 回流 575", C_LIQ, 9, ha="left")

# 电解槽 → 副产 O2
arrow(ax, (6.75, 4.15), (7.3, 4.15), C_UTIL)

# 精馏釜水 → 回流电解槽
arrow(ax, (18.15, 5.0), (18.5, 5.0), C_LIQ)
arrow(ax, (18.5, 5.0), (18.5, 2.05), C_LIQ)
arrow(ax, (18.5, 2.05), (5.3, 2.05), C_LIQ)
arrow(ax, (5.3, 2.05), (5.3, 3.35), C_LIQ)
flow_label(ax, 11.5, 2.32, "生成水 575 kg/t 回流至电解槽进水池（闭环，不外排）", C_LIQ, 9.5)

# ---------------------------------------------------------------- 图例与标题
handles = [
    Line2D([0], [0], color=C_MAIN, lw=2.2, label="气相主物流"),
    Line2D([0], [0], color=C_LIQ, lw=2.2, label="液相物流 / 水系统"),
    Line2D([0], [0], color=C_LOOP, lw=2.2, label="未反应气循环回路"),
    Line2D([0], [0], color=C_UTIL, lw=2.2, label="电解制氢 / 副产"),
    Line2D([0], [0], color="#8a3b12", lw=2.2, ls=(0, (4, 2)),
           label="驰放气（分流比 1%，碳损耗 3.5%）"),
]
ax.legend(handles=handles, loc="lower left", fontsize=9.5, frameon=True,
          framealpha=0.95, edgecolor="#cccccc", ncol=2,
          bbox_to_anchor=(0.002, 0.008))

ax.set_title("绿氢合成绿色甲醇（Power-to-Methanol）工艺物质流程图\n"
             "功能单位：1 t 聚合级精甲醇  |  万吨级装置：100,000 t/a，8,000 h/a  |  单程转化率 25%，循环比 3.8:1，总碳利用率 96.0%",
             fontsize=14.5, fontweight="bold", color=C_TEXT, pad=18)

fig.savefig(OUT / "process_flow_diagram_case2.png", dpi=300, bbox_inches="tight",
            facecolor="white")
fig.savefig(OUT / "process_flow_diagram_case2.svg", bbox_inches="tight",
            facecolor="white")
plt.close(fig)
print("已输出: %s" % (OUT / "process_flow_diagram_case2.png"))
print("已输出: %s" % (OUT / "process_flow_diagram_case2.svg"))
