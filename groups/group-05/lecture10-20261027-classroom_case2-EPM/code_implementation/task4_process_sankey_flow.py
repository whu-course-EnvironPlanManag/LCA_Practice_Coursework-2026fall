# -*- coding: utf-8 -*-
"""Generate the anchor-B material and energy flow diagram."""

import io
import os
import sys

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import pandas as pd

try:
    from task3_pareto_frontier_decision import (
        extract_pareto_frontier_and_anchors,
        simulate_park_methanol_system,
    )
except ImportError:
    from code_implementation.task3_pareto_frontier_decision import (
        extract_pareto_frontier_and_anchors,
        simulate_park_methanol_system,
    )

plt.rcParams["font.sans-serif"] = [
    "Microsoft YaHei",
    "SimHei",
    "Arial Unicode MS",
    "DejaVu Sans",
]
plt.rcParams["axes.unicode_minus"] = False


def get_figures_output_dir():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.abspath(os.path.join(current_dir, "..", "figures_output"))
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def draw_mfa_process_flow(output_filename="fig1_mfa_process_flow.png"):
    scenarios = pd.DataFrame(
        [
            simulate_park_methanol_system(f_green, r_purge)
            for f_green in np.linspace(0.0, 1.0, 60)
            for r_purge in np.linspace(0.004, 0.045, 50)
        ]
    )
    _, anchors = extract_pareto_frontier_and_anchors(scenarios)
    anchor_b = anchors["Anchor_B_Knee_Point"]

    annual_meoh_ton = 100000.0
    scale_to_wan_ton = annual_meoh_ton / 1e7
    co2_wan_ton = anchor_b["fresh_co2_kg"] * scale_to_wan_ton
    h2_wan_ton = anchor_b["fresh_h2_kg"] * scale_to_wan_ton
    purge_wan_ton = 46.0 * (anchor_b["r_purge"] / 0.010) * scale_to_wan_ton
    recycle_wan_ton = (4686.0 - 46.0 * (anchor_b["r_purge"] / 0.010)) * scale_to_wan_ton
    oxygen_wan_ton = anchor_b["oxygen_kg"] * scale_to_wan_ton
    water_reuse_wan_ton = 575.0 * scale_to_wan_ton
    power_wan_kwh = anchor_b["e_total_kwh"] * annual_meoh_ton / 1e8
    stage_power = {
        "捕集压缩": 255.0 * anchor_b["fresh_co2_kg"] / 1423.0 / 1000.0,
        "电解制氢": anchor_b["fresh_h2_kg"] * 52.0 / 1000.0,
        "循环压缩": 155.0 * (0.010 / anchor_b["r_purge"]) ** 0.65 / 1000.0,
        "精馏冷却": 120.0 / 1000.0,
    }

    fig, ax = plt.subplots(figsize=(16, 9), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    ax.text(
        50,
        96,
        "工业园区绿色甲醇系统物质与能量流向图（锚点 B）",
        fontsize=17,
        fontweight="bold",
        ha="center",
        color="#182b3a",
    )
    ax.text(
        50,
        92.5,
        f"年产能 100,000 t | 绿电 {anchor_b['f_green']:.1%} | 驰放比 "
        f"{anchor_b['r_purge']:.2%} | 综合用电 {power_wan_kwh:.3f} 亿 kWh/a | "
        f"模型碳利用率 {anchor_b['eta_carbon']:.2f}%",
        fontsize=10.5,
        ha="center",
        color="#455a64",
    )

    colors = {
        "co2": "#d97706",
        "h2": "#16804a",
        "water": "#2471a3",
        "product": "#7d3c98",
        "recycle": "#148f77",
        "purge": "#b03a2e",
        "unit": "#2c3e50",
    }

    def unit(x, y, width, height, title, detail, energy=""):
        ax.add_patch(
            patches.FancyBboxPatch(
                (x, y),
                width,
                height,
                boxstyle="round,pad=0.6,rounding_size=1.2",
                facecolor="#f5f8fa",
                edgecolor=colors["unit"],
                linewidth=1.7,
                zorder=2,
            )
        )
        ax.text(x + width / 2, y + height * 0.70, title, ha="center", va="center",
                fontsize=10.5, fontweight="bold", color=colors["unit"], zorder=3)
        ax.text(x + width / 2, y + height * 0.43, detail, ha="center", va="center",
                fontsize=8.5, color="#34495e", zorder=3)
        if energy:
            ax.text(x + width / 2, y + height * 0.17, energy, ha="center", va="center",
                    fontsize=8, fontweight="bold", color="#c0392b", zorder=3)

    def arrow(start, end, color, label, label_xy, rad=0.0, width=2.2):
        ax.add_patch(
            patches.FancyArrowPatch(
                start,
                end,
                arrowstyle="-|>",
                mutation_scale=15,
                linewidth=width,
                color=color,
                connectionstyle=f"arc3,rad={rad}",
                zorder=4,
            )
        )
        ax.text(
            label_xy[0],
            label_xy[1],
            label,
            ha="center",
            va="center",
            fontsize=8.3,
            color=color,
            bbox={"boxstyle": "round,pad=0.22", "facecolor": "white", "edgecolor": "none", "alpha": 0.92},
            zorder=5,
        )

    unit(3, 67, 20, 15, "CO2捕集与压缩", "烟气预处理、吸收再生\n压缩至 5.0 MPa",
         f"用电 {stage_power['捕集压缩']:.3f} 亿 kWh/a")
    unit(3, 34, 20, 16, "PEM电解水制氢", "可再生电力制氢\n产品氢气 3.0 MPa",
         f"用电 {stage_power['电解制氢']:.3f} 亿 kWh/a")
    unit(31, 53, 16, 15, "混合与预热", "新鲜原料与循环气\n升温至反应条件")
    unit(52, 53, 19, 15, "甲醇合成反应器", "铜基催化剂固定床\n单程转化率约 25%")
    unit(76, 53, 21, 15, "冷凝分离与分流", f"循环回路驰放比\n{anchor_b['r_purge']:.2%}",
         f"用电 {stage_power['循环压缩']:.3f} 亿 kWh/a")
    unit(76, 18, 21, 15, "双塔精馏", "脱轻与脱水\n甲醇纯度 ≥99.85 wt%",
         f"用电 {stage_power['精馏冷却']:.3f} 亿 kWh/a")

    arrow((23, 75), (31, 63), colors["co2"], f"捕集 CO2 {co2_wan_ton:.2f} 万吨/a", (26, 72))
    arrow((23, 41), (31, 57), colors["h2"], f"绿氢 {h2_wan_ton:.2f} 万吨/a", (27, 44))
    arrow((47, 60), (52, 60), colors["unit"], "混合进料", (49.5, 65), width=2.0)
    arrow((71, 60), (76, 60), colors["unit"], "反应气", (73.5, 65), width=2.0)
    arrow((79, 69), (39, 69), colors["recycle"],
          f"未反应气循环 {recycle_wan_ton:.2f} 万吨/a", (59, 82), rad=0.28, width=2.7)
    arrow((94, 68), (99, 78), colors["purge"],
          f"驰放气 {purge_wan_ton:.2f} 万吨/a", (91, 82), width=1.8)
    arrow((86.5, 53), (86.5, 33), colors["product"],
          "粗甲醇液相 15.75 万吨/a", (91, 43), width=2.4)
    arrow((97, 23), (100, 23), colors["product"],
          "精甲醇 10.00 万吨/a", (87, 15), width=2.5)
    arrow((77, 20), (13, 20), colors["water"],
          f"副产水回用 {water_reuse_wan_ton:.2f} 万吨/a", (50, 25), rad=0.0, width=2.0)
    arrow((13, 20), (13, 34), colors["water"], "", (0, 0), width=2.0)
    arrow((1, 39), (3, 39), colors["water"], "", (0, 0), width=2.0)
    ax.text(26.5, 37, "新鲜脱盐水\n13.85 万吨/a", fontsize=8, color=colors["water"],
            ha="center", va="center")
    arrow((4, 34), (2, 27), "#148f77", "", (0, 0), width=1.8)
    ax.text(5, 26, f"副产氧外售\n{oxygen_wan_ton:.2f} 万吨/a", fontsize=8,
            color="#148f77", ha="left")

    panel = patches.FancyBboxPatch(
        (3, 3),
        94,
        8,
        boxstyle="round,pad=0.5,rounding_size=1",
        facecolor="#ffffff",
        edgecolor="#aeb6bf",
        linewidth=1.0,
        zorder=1,
    )
    ax.add_patch(panel)
    metrics = [
        f"净取水模型值 {anchor_b['fresh_water_t']:.3f} t/t；除盐水净补水基准 13.85 万吨/a",
        f"水回用 {water_reuse_wan_ton:.2f} 万吨/a；副产氧 {oxygen_wan_ton:.2f} 万吨/a",
        f"碳利用率 {anchor_b['eta_carbon']:.2f}%；产品产能 10.00 万吨/a",
        f"全厂综合用电 {power_wan_kwh:.3f} 亿 kWh/a",
    ]
    for index, text in enumerate(metrics):
        ax.text(5 + index * 23, 7, text, fontsize=7.6, va="center", color="#34495e")

    fig.tight_layout()
    output_path = os.path.join(get_figures_output_dir(), output_filename)
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(
        f"[成功] 锚点 B（绿电 {anchor_b['f_green']:.1%}，驰放比 "
        f"{anchor_b['r_purge']:.2%}）工艺拓扑图已保存至: {output_path}"
    )


if __name__ == "__main__":
    draw_mfa_process_flow()
