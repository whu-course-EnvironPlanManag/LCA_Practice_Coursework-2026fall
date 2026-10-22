#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
案例一任务 2：绘制废 PET 瓶机械物理再生工艺物质流程图（BFD）

采用 matplotlib 手工排布，不依赖系统级 Graphviz，输出：
    process_flow_diagram.png  (300 dpi)
    process_flow_diagram.svg

运行：
    python plot_mfa_process.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

BASE_DIR = Path(__file__).resolve().parent

# ---------------------------------------------------------------- 中文字体
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False

# ---------------------------------------------------------------- 配色
INK = "#1F2937"
MUTED = "#6B7280"
PROC_FACE, PROC_EDGE = "#F8FAFC", "#94A3B8"
WASTE_FACE, WASTE_EDGE = "#F5F5F4", "#D6D3D1"
PROD_FACE, PROD_EDGE = "#DCFCE7", "#16A34A"
COPRO_FACE, COPRO_EDGE = "#E0F2FE", "#0284C7"
IN_FACE, IN_EDGE = "#EEF2FF", "#6366F1"
ARROW = "#64748B"

# ---------------------------------------------------------------- 布局常量
X_MAIN, W_MAIN = 330, 290
X_BRANCH, W_BRANCH = 800, 600
H = 78
Y_INPUT, Y_OUT = 1290, 385
Y_P1, Y_P2, Y_P3, Y_P4, Y_P5 = 1145, 995, 845, 695, 545


def rounded_box(ax, x, y, w, h, face, edge, lw=1.4):
    ax.add_patch(
        FancyBboxPatch(
            (x, y - h / 2), w, h,
            boxstyle="round,pad=0,rounding_size=12",
            linewidth=lw, facecolor=face, edgecolor=edge, zorder=2,
        )
    )


def arrow(ax, x1, y1, x2, y2):
    ax.annotate(
        "", xy=(x2, y2), xytext=(x1, y1),
        arrowprops=dict(arrowstyle="-|>", color=ARROW, lw=1.5,
                        shrinkA=0, shrinkB=0, mutation_scale=14),
        zorder=1,
    )


def process_node(ax, y, title, subtitle):
    rounded_box(ax, X_MAIN, y, W_MAIN, H, PROC_FACE, PROC_EDGE)
    ax.text(X_MAIN + W_MAIN / 2, y + 11, title, ha="center", va="center",
            fontsize=10, color=INK)
    ax.text(X_MAIN + W_MAIN / 2, y - 13, subtitle, ha="center", va="center",
            fontsize=8, color=MUTED)


def branch_node(ax, y, title, subtitle, face=WASTE_FACE, edge=WASTE_EDGE, tcolor=INK):
    rounded_box(ax, X_BRANCH, y, W_BRANCH, H, face, edge)
    ax.text(X_BRANCH + 18, y + 12, title, ha="left", va="center",
            fontsize=9.5, color=tcolor)
    ax.text(X_BRANCH + 18, y - 14, subtitle, ha="left", va="center",
            fontsize=8, color=MUTED)


def mass_label(ax, y, text):
    ax.text(X_MAIN + 145 - 14, y, text, ha="right", va="center",
            fontsize=8.5, color=MUTED)


def draw() -> None:
    fig, ax = plt.subplots(figsize=(11, 9.6))
    ax.set_xlim(0, 1520)
    ax.set_ylim(110, 1460)
    ax.axis("off")

    # 标题
    ax.text(760, 1415, "废 PET 瓶机械物理再生工艺物质流程图",
            ha="center", va="center", fontsize=17, color=INK, weight="bold")
    ax.text(760, 1372, "控制体基准：1 批 1,000 kg 打包瓶砖｜功能单位：1 t 瓶级 rPET 颗粒",
            ha="center", va="center", fontsize=9.5, color=MUTED)

    # 原料输入
    rounded_box(ax, X_MAIN, Y_INPUT, W_MAIN, H, IN_FACE, IN_EDGE)
    ax.text(X_MAIN + W_MAIN / 2, Y_INPUT + 11, "废 PET 瓶砖  1 000 kg",
            ha="center", va="center", fontsize=10.5, color=INK)
    ax.text(X_MAIN + W_MAIN / 2, Y_INPUT - 13, "含瓶盖、标签、泥沙与胶粘剂",
            ha="center", va="center", fontsize=8, color=MUTED)

    # 五个工段
    process_node(ax, Y_P1, "① 拆包 · 筛选 · 干式脱标", "脱除标签膜与表面泥沙")
    process_node(ax, Y_P2, "② 湿式粉碎 · 热碱洗", "85 °C，1.5% NaOH")
    process_node(ax, Y_P3, "③ 密度浮选分离", "水介质 ρ = 1.0 g/cm³")
    process_node(ax, Y_P4, "④ 光学色选 · 脱水干燥", "NIR 色选，剔除黄变片")
    process_node(ax, Y_P5, "⑤ 真空挤出造粒 · SSP", "270 °C 熔融 / 210 °C 增粘")

    # 主产品
    rounded_box(ax, X_MAIN, Y_OUT, W_MAIN, H, PROD_FACE, PROD_EDGE)
    ax.text(X_MAIN + W_MAIN / 2, Y_OUT + 11, "瓶级 rPET 颗粒  800 kg",
            ha="center", va="center", fontsize=10.5, color="#14532D", weight="bold")
    ax.text(X_MAIN + W_MAIN / 2, Y_OUT - 13, "主产品收率 Y = 80.0%",
            ha="center", va="center", fontsize=8, color="#166534")

    # 主干流
    chain = [
        (Y_INPUT, Y_P1, "1 000"),
        (Y_P1, Y_P2, "955"),
        (Y_P2, Y_P3, "920"),
        (Y_P3, Y_P4, "840"),
        (Y_P4, Y_P5, "800"),
        (Y_P5, Y_OUT, "800"),
    ]
    for y_from, y_to, label in chain:
        y_start = y_from - H / 2
        y_end = y_to + H / 2
        arrow(ax, X_MAIN + W_MAIN / 2, y_start, X_MAIN + W_MAIN / 2, y_end)
        mass_label(ax, (y_start + y_end) / 2, label)

    # 分支物流
    branches = [
        (Y_P1, "脱除杂质  45 kg", "废标签膜 20 kg + 泥沙 25 kg", WASTE_FACE, WASTE_EDGE, INK),
        (Y_P2, "洗涤废液  35 kg", "胶粘剂与溶解性 COD → 厂内污水站", WASTE_FACE, WASTE_EDGE, INK),
        (Y_P3, "副产 HDPE  75 kg", "瓶盖碎料外售；夹带损失 5 kg", COPRO_FACE, COPRO_EDGE, "#075985"),
        (Y_P4, "杂色片与细粉  40 kg", "降级造粒或外运焚烧处置", WASTE_FACE, WASTE_EDGE, INK),
    ]
    for y, title, subtitle, face, edge, tcolor in branches:
        arrow(ax, X_MAIN + W_MAIN, y, X_BRANCH, y)
        branch_node(ax, y, title, subtitle, face, edge, tcolor)

    # 图例
    legend_y = 250
    items = [
        (IN_FACE, IN_EDGE, "原料输入"),
        (PROC_FACE, PROC_EDGE, "工艺单元"),
        (PROD_FACE, PROD_EDGE, "主产品"),
        (COPRO_FACE, COPRO_EDGE, "副产品"),
        (WASTE_FACE, WASTE_EDGE, "废物 / 损失"),
    ]
    ax.text(120, legend_y, "图例：", ha="left", va="center", fontsize=9, color=MUTED)
    x_cursor = 190
    for face, edge, label in items:
        ax.add_patch(FancyBboxPatch((x_cursor, legend_y - 9), 22, 18,
                                    boxstyle="round,pad=0,rounding_size=4",
                                    linewidth=1.1, facecolor=face, edgecolor=edge))
        ax.text(x_cursor + 30, legend_y, label, ha="left", va="center",
                fontsize=8.5, color=MUTED)
        x_cursor += 30 + len(label) * 17 + 34

    # 质量守恒脚注
    ax.text(
        760, 180,
        "质量守恒：输入 1 000 kg = 主产品 800 kg + 副产品 75 kg + 废物 125 kg",
        ha="center", va="center", fontsize=9.5, color=INK,
        bbox=dict(boxstyle="round,pad=0.6", facecolor="#F1F5F9",
                  edgecolor="#CBD5E1", linewidth=1),
    )

    fig.savefig(BASE_DIR / "process_flow_diagram.png", dpi=300,
                bbox_inches="tight", facecolor="white")
    fig.savefig(BASE_DIR / "process_flow_diagram.svg",
                bbox_inches="tight", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    draw()
    print("已生成 process_flow_diagram.png (300 dpi) 与 process_flow_diagram.svg")
