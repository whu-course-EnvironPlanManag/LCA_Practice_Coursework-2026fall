# -*- coding: utf-8 -*-
"""成员 C 条件演示图：纯湿法 297 工况的「仅锂盐回款口径」部分覆盖差额。

输出：figures_output/fig_b4c_pure_hydro_conditional_lcor.png
严格遵循 C 的 README 约束：单独演示图、不标注政策可行、不与全路线帕累托混画、
不覆盖正式 LCOR（lcor_rmb_per_t）。
"""
from __future__ import annotations

import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

# 中文字体支持（Windows 常见 CJK 字体回退）
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

_BASE = os.path.dirname(os.path.abspath(__file__))
_RESULTS = os.path.join(_BASE, "..", "data_cohort", "scenario_results.csv")
_FIG = os.path.join(_BASE, "..", "figures_output")


def main() -> int:
    if not os.path.exists(_RESULTS):
        print("缺少 scenario_results.csv，请先运行 scenario_analysis.py")
        return 1

    df = pd.read_csv(_RESULTS, encoding="utf-8")
    sub = df[(df["process_mix"] == 0.0) & df["partial_lcor_conditional_CNY_t_LCE"].notna()].copy()
    if sub.empty:
        print("纯湿法条件部分 LCOR 为空，跳过条件演示图")
        return 0

    os.makedirs(_FIG, exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8))

    # 1) 部分覆盖差额 vs 绿电比例（按能效着色）
    sc = axes[0].scatter(
        sub["green_ratio"], sub["partial_lcor_conditional_CNY_t_LCE"],
        c=sub["energy_efficiency"], cmap="viridis", s=18)
    axes[0].set_xlabel("green_ratio (绿电消纳比例)")
    axes[0].set_ylabel("partial LCOR (元/t LCE)")
    axes[0].set_title("绿电比例 vs 部分覆盖差额")

    # 2) 部分覆盖差额 vs 锂价（按能效着色）
    sc = axes[1].scatter(
        sub["lithium_price_usd"], sub["partial_lcor_conditional_CNY_t_LCE"],
        c=sub["energy_efficiency"], cmap="viridis", s=18)
    axes[1].set_xlabel("lithium_price_usd (USD/t)")
    axes[1].set_ylabel("partial LCOR (元/t LCE)")
    axes[1].set_title("锂价(USD→CNY×7.2) vs 部分覆盖差额")

    # 3) 部分覆盖差额 vs GWP（按绿电着色）
    sc = axes[2].scatter(
        sub["gwp_kgco2e"], sub["partial_lcor_conditional_CNY_t_LCE"],
        c=sub["green_ratio"], cmap="cividis", s=18)
    axes[2].set_xlabel("GWP100 (kg CO2e/t LCE)")
    axes[2].set_ylabel("partial LCOR (元/t LCE)")
    axes[2].set_title("GWP vs 部分覆盖差额")

    for ax, sci in ((axes[0], sc), (axes[1], sc), (axes[2], sc)):
        fig.colorbar(sci, ax=ax)

    fig.suptitle(
        "条件演示（仅锂盐回款口径 · 纯湿法 297 工况 · 非政策可行 · CONDITIONAL_PARTIAL_LCOR_NOT_FINAL）",
        fontsize=11)
    out = os.path.join(_FIG, "fig_b4c_pure_hydro_conditional_lcor.png")
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(out, dpi=300)
    plt.close(fig)
    print(f"已生成条件演示图：{os.path.abspath(out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())