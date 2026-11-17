#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
第九讲 案例一：废弃 PET 瓶机械物理再生 MFA 物质流流程图
输入基准：1000 kg 废 PET 瓶砖

运行:
    python plot_mfa_process.py

输出:
    process_flow_diagram.png   (300 dpi)
    process_flow_diagram.svg
"""

from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "SimSun", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["svg.fonttype"] = "none"

# ----------------------------------------------------------------------------
# 1. 数据（kg / 1000 kg 进料，严格对应 mfa_mass_balance.csv）
# ----------------------------------------------------------------------------
PROCESSES = [
    ("废 PET 瓶砖\n接收", 1.0, 5.0, 1.5, 1.1),
    ("拆包 / 干燥\nDe-baling", 3.2, 5.0, 1.6, 1.1),
    ("热水洗\nHot Washing", 5.4, 5.0, 1.6, 1.1),
    ("沉浮分选\nSink-Float", 7.6, 5.0, 1.6, 1.1),
    ("SSP 挤出\nSSP Extrusion", 9.8, 5.0, 1.6, 1.1),
]

# (起点x, 起点y, 终点x, 终点y, 标签, 颜色)
BRANCHES = [
    (2.60, 4.45, 2.60, 3.05, "标签薄膜\n20 kg (2.0%)", "#d95f02"),
    (3.70, 4.45, 3.70, 3.05, "表面泥沙\n25 kg (2.5%)", "#7570b3"),
    (5.40, 4.45, 5.40, 3.05, "胶黏剂残留\n35 kg (3.5%)", "#1b9e77"),
    (7.05, 4.45, 7.05, 3.05, "HDPE 片料\n75 kg (7.5%)", "#66a61e"),
    (8.15, 4.45, 8.15, 3.05, "细屑损失\n5 kg (0.5%)", "#a6761d"),
    (9.80, 4.45, 9.80, 3.05, "降级碎屑\n40 kg (4.0%)", "#e7298a"),
]

MAIN_ARROWS = [  # (x0, x1, 质量标签)
    (1.75, 2.40, "1000 kg"),
    (4.00, 4.60, "1000 kg"),
    (6.20, 6.80, "980 kg"),
    (8.40, 9.00, "945 kg"),
]


def box(ax, x, y, w, h, text, fc="#eef4fb", ec="#2c5f8d"):
    ax.add_patch(FancyBboxPatch(
        (x - w / 2, y - h / 2), w, h,
        boxstyle="round,pad=0.06,rounding_size=0.12",
        linewidth=1.4, facecolor=fc, edgecolor=ec, zorder=3))
    ax.text(x, y, text, ha="center", va="center", fontsize=11,
            color="#123a5c", zorder=4, linespacing=1.4)


def arrow(ax, p0, p1, color, lw=1.6, ls="-", zorder=2):
    ax.add_patch(FancyArrowPatch(
        p0, p1, arrowstyle="-|>", mutation_scale=13,
        linewidth=lw, linestyle=ls, color=color,
        shrinkA=0, shrinkB=0, zorder=zorder))


def main():
    fig, ax = plt.subplots(figsize=(16, 7.8))
    ax.set_xlim(0, 12.7)
    ax.set_ylim(1.55, 7.25)
    ax.axis("off")

    for name, x, y, w, h in PROCESSES:
        box(ax, x, y, w, h, name)

    for x0, x1, lab in MAIN_ARROWS:
        arrow(ax, (x0, 5.0), (x1, 5.0), "#1f77b4", lw=5.0)
        ax.text((x0 + x1) / 2, 6.16, lab, ha="center", fontsize=10, color="#1f77b4")

    for x0, y0, x1, y1, lab, c in BRANCHES:
        arrow(ax, (x0, y0), (x1, y1), c, lw=1.8, ls=(0, (4, 2)))
        ax.text(x1, y1 - 0.10, lab, ha="center", va="top", fontsize=9.5,
                color=c, linespacing=1.35)

    box(ax, 11.75, 5.0, 1.30, 1.1, "瓶级 rPET\n800 kg\n(80.0%)", fc="#d9f0d3", ec="#2e7d32")
    arrow(ax, (10.60, 5.0), (11.06, 5.0), "#1f77b4", lw=5.0)

    ax.add_patch(FancyBboxPatch((0.8, 1.90), 11.9, 0.60,
                                boxstyle="round,pad=0.05,rounding_size=0.1",
                                linewidth=1.0, facecolor="#f7f7f7",
                                edgecolor="#999999", zorder=3))
    ax.text(6.75, 2.20,
            "质量守恒：输入 1000 kg = 产品 875 kg（rPET 800 + HDPE 75）+ 废弃物 125 kg",
            ha="center", va="center", fontsize=11.5, color="#333333")

    ly = 6.80
    ax.plot([0.95, 1.40], [ly, ly], color="#1f77b4", lw=5.0)
    ax.text(1.52, ly, "主物料流", fontsize=10, va="center")
    ax.plot([2.75, 3.20], [ly, ly], color="#d95f02", lw=1.8, ls=(0, (4, 2)))
    ax.text(3.32, ly, "废弃物", fontsize=10, va="center")
    ax.plot([4.30, 4.75], [ly, ly], color="#66a61e", lw=1.8, ls=(0, (4, 2)))
    ax.text(4.87, ly, "副产品", fontsize=10, va="center")
    ax.add_patch(FancyBboxPatch((5.70, ly - 0.16), 0.45, 0.32,
                                boxstyle="round,pad=0.02,rounding_size=0.05",
                                facecolor="#eef4fb", edgecolor="#2c5f8d", lw=1.0))
    ax.text(6.25, ly, "处理工段", fontsize=10, va="center")

    ax.set_title("废弃 PET 瓶机械物理再生系统 物质流分析（MFA）\n"
                 "功能单位：1000 kg 废瓶砖进料  |  主产品 800 kg 瓶级 rPET",
                 fontsize=14, pad=14, color="#123a5c")

    here = Path(__file__).resolve().parent
    png, svg = here / "process_flow_diagram.png", here / "process_flow_diagram.svg"
    fig.savefig(png, dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(svg, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"已输出: {png}")
    print(f"已输出: {svg}")


if __name__ == "__main__":
    main()
