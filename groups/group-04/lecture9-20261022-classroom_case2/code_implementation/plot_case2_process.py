#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""案例二 任务 3：CO2 捕集 + 绿氢合成绿色甲醇 工艺物质流程图。

采用 matplotlib 手工排布（无 Graphviz / schemdraw 系统依赖），
输出 case2_process_flow.png（300 dpi）与 .svg。
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False

HERE = Path(__file__).resolve().parent

INK = "#1F2937"
MUTED = "#6B7280"
LINE = "#475569"
FEED_FACE, FEED_EDGE = "#EEF2FF", "#4F46E5"
UNIT_FACE, UNIT_EDGE = "#F8FAFC", "#94A3B8"
PROD_FACE, PROD_EDGE = "#ECFDF5", "#059669"
BYPROD_FACE, BYPROD_EDGE = "#EFF6FF", "#2563EB"
PURGE_FACE, PURGE_EDGE = "#FEF2F2", "#DC2626"
RECYCLE = "#059669"


def box(ax, x, y, w, h, title, sub, face, edge, tcolor=INK, subcolor=MUTED):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle="round,pad=1.2,rounding_size=3.2",
                                facecolor=face, edgecolor=edge, lw=1.5, zorder=3))
    ax.text(x + w / 2, y + h * 0.63, title, ha="center", va="center",
            fontsize=10.5, color=tcolor, weight="bold", zorder=4)
    ax.text(x + w / 2, y + h * 0.27, sub, ha="center", va="center",
            fontsize=7.8, color=subcolor, linespacing=1.35, zorder=4)


def poly_arrow(ax, pts, color=LINE, lw=1.5, ls="-"):
    if len(pts) > 2:
        ax.plot([p[0] for p in pts[:-1]], [p[1] for p in pts[:-1]],
                color=color, lw=lw, ls=ls, solid_capstyle="round", zorder=1)
    ax.add_patch(FancyArrowPatch(pts[-2], pts[-1], arrowstyle="-|>",
                                 mutation_scale=13, color=color, lw=lw, linestyle=ls,
                                 shrinkA=0, shrinkB=0, zorder=2))


def tag(ax, x, y, text, color=MUTED, fontsize=8.2, ha="center", rotation=0):
    ax.text(x, y, text, ha=ha, va="center", fontsize=fontsize, color=color,
            rotation=rotation, zorder=5,
            bbox=dict(boxstyle="round,pad=0.18", facecolor="white",
                      edgecolor="none", alpha=0.9))


def draw() -> None:
    fig, ax = plt.subplots(figsize=(9.2, 10.8))
    fig.patch.set_facecolor("white")
    ax.set_xlim(0, 222)
    ax.set_ylim(0, 300)
    ax.axis("off")

    ax.text(111, 292, "CO2 捕集 + 绿氢合成绿色甲醇 工艺物质流（MFA）",
            ha="center", va="center", fontsize=16, weight="bold", color=INK)
    ax.text(111, 283,
            "功能单位 1 t 精甲醇  ·  单程转化率 25%  ·  循环 99% / 驰放 1%  ·  循环比 3.8:1",
            ha="center", va="center", fontsize=9, color=MUTED)

    # ---------------- 左侧：原料与电解 ----------------
    box(ax, 8, 246, 62, 30, "烟气 CO2 捕集", "MEA 化学吸收 + 三级压缩\n1 423 kg  ·  32.33 kmol",
        FEED_FACE, FEED_EDGE)
    box(ax, 8, 202, 62, 30, "新鲜绿氢", "PEM 电解水 · 25 ℃ · 3.0 MPa\n198 kg  ·  98.21 kmol",
        FEED_FACE, FEED_EDGE)
    box(ax, 8, 128, 62, 38, "PEM 电解槽 130 MW",
        "2H2O → 2H2 + O2\n52 kWh/kg H2  ·  总进水 1 960 kg",
        UNIT_FACE, UNIT_EDGE)
    box(ax, 8, 84, 62, 24, "除盐纯水", "净补水 1 385 kg", FEED_FACE, FEED_EDGE)
    box(ax, 8, 34, 62, 24, "副产高纯 O2", "1 584 kg  ·  49.50 kmol\n外售替代空分",
        BYPROD_FACE, BYPROD_EDGE, tcolor="#1E3A8A")

    # ---------------- 中部：反应与精馏 ----------------
    box(ax, 92, 232, 62, 28, "混合预热器", "230 ℃  ·  5.0 MPa\n进气 6 261 kg",
        UNIT_FACE, UNIT_EDGE)
    box(ax, 92, 180, 62, 36, "固定床合成反应器",
        "Cu/ZnO/Al2O3  ·  250 ℃  ·  5.0 MPa\nCO2 单程转化率 25%  ·  出料 6 261 kg",
        UNIT_FACE, UNIT_EDGE)
    box(ax, 92, 124, 62, 34, "冷却冷凝 + 高压分离",
        "45 ℃  ·  4.8 MPa\n粗甲醇 1 575 kg  |  气相 4 686 kg",
        UNIT_FACE, UNIT_EDGE)
    box(ax, 92, 66, 62, 32, "双塔精馏",
        "常压脱轻 + 加压脱水\n产品纯度 > 99.85 wt%",
        UNIT_FACE, UNIT_EDGE)
    box(ax, 92, 14, 62, 26, "主产品：精甲醇",
        "1 000 kg  ·  31.21 kmol\n碳利用率 96.5%",
        PROD_FACE, PROD_EDGE, tcolor="#14532D", subcolor="#166534")

    # ---------------- 主流程箭头 ----------------
    poly_arrow(ax, [(70, 259), (92, 251)], color=LINE)
    tag(ax, 79, 261, "1 423 kg", ha="right")
    poly_arrow(ax, [(70, 215), (92, 240)], color=LINE)
    tag(ax, 79, 224, "198 kg", ha="right")

    poly_arrow(ax, [(123, 232), (123, 216)])
    tag(ax, 123, 224, "6 261 kg")
    poly_arrow(ax, [(123, 180), (123, 158)])
    tag(ax, 123, 169, "6 261 kg")
    poly_arrow(ax, [(123, 124), (123, 98)])
    tag(ax, 123, 110, "粗甲醇 1 575 kg")
    poly_arrow(ax, [(123, 66), (123, 40)])
    tag(ax, 123, 52, "1 000 kg")

    # 电解槽 → 氢气
    poly_arrow(ax, [(39, 166), (39, 202)], color=FEED_EDGE)
    tag(ax, 45, 184, "H2 198 kg", color=FEED_EDGE, ha="left")
    # 纯水 → 电解槽
    poly_arrow(ax, [(39, 108), (39, 128)], color=FEED_EDGE)
    tag(ax, 45, 118, "1 385 kg", color=FEED_EDGE, ha="left")
    # 电解槽 → 副产氧（右侧绕行）
    poly_arrow(ax, [(70, 135), (75, 135), (75, 46), (70, 46)], color=BYPROD_EDGE)
    tag(ax, 80, 62, "O2 1 584 kg", color=BYPROD_EDGE, ha="left", fontsize=8)

    # 精馏生成水回流电解槽（左侧绕行）
    poly_arrow(ax, [(92, 82), (80, 82), (80, 147), (70, 147)], color=FEED_EDGE, ls=(0, (5, 3)))
    tag(ax, 86.5, 112, "生成水 575 kg 回流", color=FEED_EDGE, rotation=90, fontsize=7.8)

    # ---------------- 循环气回路 ----------------
    poly_arrow(ax, [(154, 150), (200, 150), (200, 246), (154, 246)],
               color=RECYCLE, lw=2.0, ls=(0, (6, 3)))
    tag(ax, 211, 198, "循环气 4 640 kg\n99% 回流\n365.12 kmol", color=RECYCLE,
        rotation=90, fontsize=8.2)
    tag(ax, 180, 252, "未反应气循环 Recycle Loop", color=RECYCLE, fontsize=8.4)

    # 分离器气相分流点
    ax.scatter([166], [150], s=22, color=RECYCLE, zorder=6)
    poly_arrow(ax, [(166, 150), (166, 122), (176, 122)], color=PURGE_EDGE, lw=1.6)
    box(ax, 176, 108, 40, 28, "驰放气 46 kg",
        "1% 分流 · 3.97 kmol\n送厂内锅炉燃烧", PURGE_FACE, PURGE_EDGE, tcolor="#991B1B")
    tag(ax, 171, 136, "1%", color=PURGE_EDGE, fontsize=8)

    # ---------------- 图例与注释 ----------------
    legend = [
        ("原料/公用工程", FEED_FACE, FEED_EDGE),
        ("工艺单元", UNIT_FACE, UNIT_EDGE),
        ("主产品", PROD_FACE, PROD_EDGE),
        ("副产品", BYPROD_FACE, BYPROD_EDGE),
        ("驰放/损失", PURGE_FACE, PURGE_EDGE),
    ]
    x = 12
    for label, face, edge in legend:
        ax.add_patch(FancyBboxPatch((x, 6), 6, 4, boxstyle="round,pad=0.3,rounding_size=1",
                                    facecolor=face, edgecolor=edge, lw=1.2))
        ax.text(x + 8, 8, label, ha="left", va="center", fontsize=8, color=MUTED)
        x += 42

    ax.text(111, 0.4,
            "质量守恒：1 423 + 198 + 4 640 = 6 261 kg 进反应器；6 261 = 1 575 + 4 686；"
            "4 686 = 4 640 + 46；1 575 = 1 000 + 575",
            ha="center", va="bottom", fontsize=7.8, color=MUTED)

    for suffix, dpi in (("png", 300), ("svg", None)):
        fig.savefig(HERE / f"case2_process_flow.{suffix}", dpi=dpi,
                    facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print("已输出 case2_process_flow.png / case2_process_flow.svg")


if __name__ == "__main__":
    draw()

