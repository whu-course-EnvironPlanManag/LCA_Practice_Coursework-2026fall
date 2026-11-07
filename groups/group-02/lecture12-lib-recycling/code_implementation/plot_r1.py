#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lecture12 案例三 · 成员 A：R1 背景情景（2026-11-04）图表。

产出（300 DPI，全部由 data_cohort/a_group_r1_scenario_20261104.json 驱动）：
    fig5_r1_split_flow.png    [已停用] 旧版 R1 分流示意图（与 fig1/fig01 重叠，不再输出）
    fig6_r1_future_dmfa.png   R1 未来 2026—2040 首装/替换流入 + 校核年退出/收集

图注纪律：
    - q=0.90 / y=0.97 / SOH=0.80 / 增长率 5%/a / c=0.80 均为**情景假设**，非本地实测；
    - 弃用回流 1,079.50 t/a 返回再生线，与 59,500 原情景**并列不取平均**；
    - 未来退出量与收集量是条件情景值，未扣梯次与其他企业分流，供需量比≠园区进料。

运行：python code_implementation/plot_r1.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

CODE_DIR = Path(__file__).resolve().parent
WORKDIR = CODE_DIR.parent
R1_JSON = WORKDIR / "data_cohort" / "a_group_r1_scenario_20261104.json"
FIG_DIR = WORKDIR / "figures_output"
DPI = 300

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

COLOR_ARROW = "#3d4a5c"
COLOR_HEAD = "#8c96a1"
COLOR_BODY = "#f4f6f8"
COLOR_REUSE = "#e8f1f8"
COLOR_RECYCLE = "#f6f2ea"
COLOR_WARN = "#b3261e"
COLOR_LFP = "#2f6f9f"
COLOR_NMC = "#8fa8bb"
COLOR_FIRST = "#1f6f8b"
COLOR_REPLACE = "#c9772e"
COLOR_EXIT = "#2f3e4e"
COLOR_COLLECT = "#7a4b8c"


def load_r1(path: Path = R1_JSON) -> dict:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _box(ax, x, y, w, h, title, lines, fc=COLOR_BODY, ec="#c9d3dd", title_fs=11, body_fs=8.2):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04,rounding_size=0.08",
                                linewidth=1.4, edgecolor=ec, facecolor=fc))
    ax.add_patch(FancyBboxPatch((x, y + h - 0.42), w, 0.42, boxstyle="round,pad=0.04,rounding_size=0.08",
                                linewidth=0, facecolor=COLOR_HEAD))
    ax.text(x + 0.13, y + h - 0.27, title, fontsize=title_fs, color="white", fontweight="bold", va="center")
    for k, line in enumerate(lines):
        ax.text(x + 0.13, y + h - 0.72 - k * 0.42, line, fontsize=body_fs, color="#243244",
                va="top", linespacing=1.35)


def _arrow(ax, p0, p1, label=None, lx=0, ly=0, color=COLOR_ARROW, fs=8.0, style="-|>"):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle=style, mutation_scale=14,
                                 linewidth=1.6, color=color))
    if label:
        mx, my = (p0[0] + p1[0]) / 2 + lx, (p0[1] + p1[1]) / 2 + ly
        ax.text(mx, my, label, fontsize=fs, color=color, ha="center", va="bottom")


def draw_split_flow(r1: dict) -> Path:
    s = r1["reuse_recycling_split"]
    ru = r1["reuse_test_capacity"]
    q, y, soh = s["screen_pass_mass_fraction_q"], s["repack_yield_y"], s["retained_soh"]
    ret = s["reuse_retained_pack_equiv_t_a"]
    rec = s["recycling_pack_equiv_t_a"]

    fig, ax = plt.subplots(figsize=(14, 9.6))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 9.7)
    ax.axis("off")

    ax.text(0.5, 9.32, "R1 背景情景 · 梯次分流与再生入口示意图（成员 A）", fontsize=18, fontweight="bold", color="#1f2d3d")
    ax.text(0.5, 8.98, "情境假设：q=0.90 / y=0.97 / SOH=0.80；弃用回流返回再生，再生入口 59,500 → 60,579.50 t/a（与 59,500 原情景并列，不取平均）",
            fontsize=9.6, color="#4a5568")

    # 顶部总进料
    _box(ax, 4.6, 8.05, 4.8, 0.72, "实际进料整包当量", ["68,000 t/a（设计 80,000 × 负荷 0.85）"], fc="#fbfcfd")
    _arrow(ax, (7.0, 8.05), (3.1, 7.85), "59,500（直接再生）", lx=-1.4, ly=0.14)
    _arrow(ax, (7.0, 8.05), (10.9, 7.85), "8,500（梯次候选）", lx=1.4, ly=0.14)

    # 左：直接再生
    _box(ax, 0.8, 7.05, 4.6, 0.80, "直接再生来料", ["59,500 t/a（组内 0.85 负荷分配）"], fc=COLOR_RECYCLE)

    # 右：梯次线
    _box(ax, 8.7, 7.05, 4.6, 0.80, "梯次候选来料", ["8,500 t/a（梯次能力 10,000 × 0.85）"], fc=COLOR_REUSE)
    _arrow(ax, (11.0, 7.05), (11.0, 6.02), f"筛选 q={q:g}", ly=0.0)
    _box(ax, 8.7, 5.25, 4.6, 0.76, "筛选通过", ["7,650 t/a = 8,500 × 0.90"], fc=COLOR_REUSE)
    _arrow(ax, (8.7, 5.63), (5.35, 2.70), "弃用 850 = 8,500×(1−q)", lx=0.45, ly=0.30, color=COLOR_WARN)
    _arrow(ax, (11.0, 5.25), (11.0, 4.22), f"重组 y={y:g}", ly=0.0)
    _box(ax, 8.7, 3.45, 4.6, 0.76, "重组保留", ["7,420.50 t/a = 7,650 × 0.97"], fc=COLOR_REUSE)
    _arrow(ax, (8.7, 3.83), (6.45, 2.70), "弃用 229.50 = 7,650×(1−y)", lx=0.45, ly=0.10, color=COLOR_WARN)
    _arrow(ax, (11.0, 3.45), (11.0, 2.62), f"保留 SOH={soh:g}", ly=0.0)
    _box(ax, 8.7, 1.85, 4.6, 0.76, "梯次保留整包当量", ["7,420.50 t/a（非重组后成品质量）"], fc=COLOR_REUSE)
    _arrow(ax, (11.0, 1.85), (11.0, 1.02), "交付容量", ly=0.0)
    _box(ax, 8.7, 0.22, 4.6, 0.79, "梯次交付可用容量（SOH=0.80）",
         [f"{ru['deliver_usable_kwh_a']:,.1f} kWh/a = 7,420.50 × 118 × 0.80"], fc=COLOR_REUSE)

    # 弃用回流合计
    _box(ax, 4.35, 1.85, 3.1, 0.76, "弃用回流合计", ["850 + 229.50 = 1,079.50 t/a"], fc="#fdf3f1")
    _arrow(ax, (5.9, 1.85), (5.9, 0.98), "回流入再生", lx=0.45, color=COLOR_WARN)

    # 再生入口合并
    _arrow(ax, (3.1, 7.05), (3.1, 0.98), "59,500", lx=-0.55, ly=1.6)
    _box(ax, 1.35, 0.02, 5.3, 0.94, "再生入口整包当量",
         [f"{rec:,.2f} t/a = 59,500 + 1,079.50（弃用回流）"], fc=COLOR_RECYCLE, ec="#5b7f9e")

    fig.text(0.01, 0.012,
             "注释：q/y/SOH 无匹配本园区口径的文献实测，均为情景假设；7,420.50 t/a 是保留旧电池整包当量，不是加壳重组后的成品质量；"
             "弃用回流保持 0.60/0.40 组成，故再生入口再分体系为 LFP 60% = 36,347.70 t/a、未细分三元 40% = 24,231.80 t/a。",
             fontsize=8.2, color="#5b6672")
    fig.tight_layout(rect=(0, 0.028, 1, 1))
    # 旧版 R1 分流示意图（fig5_r1_split_flow）与 fig1/fig01 重叠，保留绘制但不写盘
    plt.close(fig)
    return None


def draw_future_dmfa(r1: dict) -> Path:
    d = r1["dmfa_future_2026_2040"]
    rows = d["annual_inflow_t_pack_a_rows"]
    years = [r["year"] for r in rows]
    first = [r["LFP_first"] + r["NMC_first"] for r in rows]
    replace = [r["LFP_replace"] + r["NMC_replace"] for r in rows]
    inflow = [f + r for f, r in zip(first, replace)]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14.5, 10.2), sharex=True,
                                   gridspec_kw={"height_ratios": [1.15, 1]})

    ax1.bar(years, first, color=COLOR_FIRST, width=0.66, label="首装流入（LFP+未细分三元，5%/a）", zorder=3)
    ax1.bar(years, replace, bottom=first, color=COLOR_REPLACE, width=0.66,
            label="替换流入（存续车辆失效立即同体系同质量换包）", zorder=3)
    ax1.plot(years, inflow, color=COLOR_EXIT, lw=2.4, marker="o", ms=4, label="合计年流入（首装+替换）", zorder=4)
    ax1.set_title("R1 未来 2026—2040 年度电池流入（首装 + 替换，情景假设）", fontsize=12.5, loc="left")
    ax1.set_ylabel("t 整包 / a")
    ax1.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax1.grid(axis="y", color="#dde3e9", lw=0.8)
    ax1.legend(loc="upper left", fontsize=9.3, frameon=False)

    # 校核年退出 / 收集（数据仅在 2030/2035/2040 年给出）
    chk = {c["year"]: c for c in d["check_rows"]}
    col = {c["year"]: c for c in d["collection_results"]}
    chk_years = [c["year"] for c in d["check_rows"]]
    exit_v = [chk[y]["total_battery_exit_t_pack_a"] for y in chk_years]
    coll_years = [c["year"] for c in d["collection_results"]]
    coll_v = [c["collected_t_pack_a"] for c in d["collection_results"]]

    ax2.plot(chk_years, exit_v, color=COLOR_EXIT, lw=2.6, marker="o", ms=5, label="电池退出量（随车报废+换下）", zorder=3)
    ax2.plot(coll_years, coll_v, color=COLOR_COLLECT, lw=2.2, marker="s", ms=6,
             label="正规收集量 C(t) = 退出 × c（c=0.80）", zorder=3)
    for y_, v in zip(chk_years, exit_v):
        ax2.annotate(f"{v:,.1f}", (y_, v), textcoords="offset points", xytext=(0, 8),
                     ha="center", fontsize=9, color=COLOR_EXIT)
    for y_, v in zip(coll_years, coll_v):
        ax2.annotate(f"{v:,.1f}", (y_, v), textcoords="offset points", xytext=(0, -15),
                     ha="center", fontsize=9, color=COLOR_COLLECT)

    # 存量（校核年）
    for y_ in chk_years:
        st = chk[y_]["year_end_total_stock_t_pack"]
        ax2.text(y_, exit_v[chk_years.index(y_)] * 1.30, f"年末存量\n{st:,.1f} t",
                 ha="center", fontsize=8.6, color="#41505f")

    ax2.set_title("R1 未来 校核年退出 / 收集与供需量比（条件情景，非园区进料）", fontsize=12.5, loc="left")
    ax2.set_xlabel("年份")
    ax2.set_ylabel("t 整包 / a")
    ax2.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax2.grid(axis="y", color="#dde3e9", lw=0.8)
    ax2.legend(loc="upper left", fontsize=9.3, frameon=False)
    ax2.set_xlim(2025.4, 2040.6)
    plt.setp(ax1.get_xticklabels(), visible=True)  # 上图柱状也显示年份刻度

    ratio_txt = "；".join(
        f"{y_} 供需量比 {col[y_]['demand_ratio_vs_68000']*100:.1f}%" for y_ in coll_years)
    fig.text(0.01, 0.012,
             f"注释：首装增长率 5%/a、车辆与电池寿命相互独立、失效包立即替换均为本研究新增情景假设；"
             f"退出量未乘收集率之外的任何分流（梯次、其他企业）；{ratio_txt}，仅为条件比例，不等于园区进料。",
             fontsize=8.4, color="#5b6672")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    out = FIG_DIR / "fig6_r1_future_dmfa.png"
    fig.savefig(out, dpi=DPI, facecolor="white")
    plt.close(fig)
    return out


def main() -> int:
    r1 = load_r1()
    p1 = draw_split_flow(r1)
    p2 = draw_future_dmfa(r1)
    print("生成 R1 图表（DPI=%d）：" % DPI)
    for p in (p1, p2):
        if p is None:
            continue
        print(f"    {p.relative_to(WORKDIR)}  {p.stat().st_size / 1024:,.0f} KB  {DPI} DPI")
    print("完成：两张 R1 图来自 a_group_r1_scenario_20261104.json，图上情景假设均已标注。")
    return 0


if __name__ == "__main__":
    sys.exit(main())