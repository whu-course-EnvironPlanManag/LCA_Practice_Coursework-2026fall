#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lecture12 案例三 · 宜昌市域 dMFA 图表（成员 A）

产出（300 DPI，均由 dmfa_yichang.py 的同一套计算驱动，图内数值自动取算得结果）：
    fig3_dmfa_retirement_collection.png   年度退役量 vs 三情景正规收集量（2010—2040）
    fig4_dmfa_stock_and_li.png           在用整包存量（分体系）与 LFP 在用锂存量/退役锂

图注纪律：
    - 2026 年之后只画"既有队列剩余释放"，不画未来新增（未来首装未建模，见 D06/D04 阻断）；
    - 图上 Li 只标 LFP，未细分三元整列为 null，不做 622/811 平均；
    - 收集量 ≠ 进入再生 ≠ 进入园区（M01、D-PARK-LINK 未解锁），图上不出现园区进料。

AI 辅助说明：
    提示词摘要："用 dmfa_yichang.py 的 records 画两张 dMFA 图：退役/收集时序、存量与锂存量；
    历史段与既有队列释放段用底色区分，不要在图上补未来装机或园区来料"。人工复核：成员 A 核对峰值年份与量级。

运行：python code_implementation/plot_dmfa.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dmfa_yichang import (  # noqa: E402
    CHEM_LFP,
    CHEM_NMC,
    DATASET_JSON,
    LIFETIME_CHEM,
    WORKDIR,
    cohort_inflows,
    load_dataset,
    prepare,
    run_case,
)

FIG_DIR = WORKDIR / "figures_output"
DPI = 300
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

COLOR_RETIRED = "#2f3e4e"
COLOR_CASE = {"C065": "#c9772e", "C085": "#1f6f8b", "C100": "#7a4b8c"}
COLOR_LFP = "#2f6f9f"
COLOR_NMC = "#8fa8bb"
COLOR_LI = "#b3261e"
COLOR_HIST = "#eef4f9"
COLOR_REL = "#f6f2ea"


def thousand(v: float, _pos=None) -> str:
    return f"{v:,.0f}"


def total_of(rec, key: str, year: int) -> float:
    return sum(rec["by_chem"][c][key][year] for c in LIFETIME_CHEM)


def draw_retirement(records) -> Path:
    fig, ax = plt.subplots(figsize=(15.5, 8.2))
    years = records[0]["years_all"]
    hist_end = records[0]["years_hist"][-1]
    retired = [total_of(records[0], "retired", y) for y in years]

    ax.axvspan(years[0], hist_end, color=COLOR_HIST, zorder=0)
    ax.axvspan(hist_end, years[-1], color=COLOR_REL, zorder=0)
    ax.axvline(hist_end + 0.5, color="#8c96a1", ls="--", lw=1.2, zorder=1)

    ax.plot(years, retired, color=COLOR_RETIRED, lw=2.8, label="首次退役量 R(t)（全部情景相同）", zorder=3)
    for rec in records:
        col = COLOR_CASE[rec["case"]["collection_scenario_id"]]
        ax.plot(years, [total_of(rec, "collected", y) for y in years], color=col, lw=2.0,
                label=f"正规收集量 C(t) · {rec['case']['collection_scenario_id']}（c={rec['c_rate']:.2f}）",
                zorder=2)

    peak_y = max(years, key=lambda y: total_of(records[0], "retired", y))
    peak_v = total_of(records[0], "retired", peak_y)
    ax.annotate(f"退役峰值 {peak_y} 年 ≈ {peak_v:,.0f} t/a\n（寿命尾部保留、未重归一化）",
                xy=(peak_y, peak_v), xytext=(peak_y - 8.5, peak_v * 1.32),
                fontsize=10.5, color=COLOR_RETIRED,
                arrowprops=dict(arrowstyle="->", color=COLOR_RETIRED, lw=1.2))

    lines = []
    for rec in records:
        cum = sum(total_of(rec, "collected", y) for y in years)
        tag = "（c=1，与退役量重合）" if rec["c_rate"] >= 1.0 else ""
        lines.append(f"{rec['case']['collection_scenario_id']}：累计收集 {cum:,.0f} t{tag}（2010—2040）")
    ax.text(0.015, 0.97, "\n".join(lines), transform=ax.transAxes, va="top", ha="left", fontsize=10,
            family="Microsoft YaHei",
            bbox=dict(boxstyle="round,pad=0.45", fc="white", ec="#c3ccd6", alpha=0.95))

    ax.text(years[0] + 1.2, peak_v * 0.16, "首装队列条件重建段\n（2010—2025 新增车辆）", fontsize=10.5,
            color="#41505f", ha="left", va="bottom")
    ax.text(hist_end + 2.0, peak_v * 0.16, "既有队列剩余释放段\n（2026—2040 无新增，非全市预测）", fontsize=10.5,
            color="#6a5a45", ha="left", va="bottom")

    ax.set_title("宜昌市域动力电池退役量与正规收集量（首装队列 dMFA，2010—2040）", fontsize=14, pad=12)
    ax.set_xlabel("年份")
    ax.set_ylabel("t 整包 / a")
    ax.yaxis.set_major_formatter(FuncFormatter(thousand))
    ax.set_xlim(years[0], years[-1])
    ax.set_ylim(0, peak_v * 1.55)
    ax.grid(axis="y", color="#dde3e9", lw=0.8)
    ax.legend(loc="upper left", bbox_to_anchor=(0.015, 0.80), fontsize=9.5, frameon=False)
    fig.text(0.01, 0.012,
             "注释：正规收集量 = c × 首次退役量，c 只影响收集、不影响退役；收集≠进入再生≠进入园区"
             "（梯次分流 M01 与市域→园区链接未解锁）；未细分三元含 Li 未解，图上不出现其锂量。",
             fontsize=8.6, color="#5b6672")
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    out = FIG_DIR / "fig3_dmfa_retirement_collection.png"
    fig.savefig(out, dpi=DPI)
    plt.close(fig)
    return out


def draw_stock_li(records) -> Path:
    rec = records[0]
    years = rec["years_all"]
    hist_end = rec["years_hist"][-1]
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15.0, 11.4), sharex=True,
                                   gridspec_kw={"height_ratios": [1.15, 1]})

    lfp = [rec["by_chem"][CHEM_LFP]["stock"][y] for y in years]
    nmc = [rec["by_chem"][CHEM_NMC]["stock"][y] for y in years]
    ax1.stackplot(years, lfp, nmc, colors=[COLOR_LFP, COLOR_NMC],
                  labels=["LFP 在用存量", "未细分三元在用存量"], alpha=0.95)
    total = [a + b for a, b in zip(lfp, nmc)]
    ax1.plot(years, total, color="#2f3e4e", lw=2.2, label="在用整包存量合计 S(t)")
    ax1.axvline(hist_end + 0.5, color="#8c96a1", ls="--", lw=1.2)
    ax1.annotate(f"{hist_end} 年末 {total[years.index(hist_end)]:,.0f} t",
                 xy=(hist_end, total[years.index(hist_end)]),
                 xytext=(hist_end - 6.5, total[years.index(hist_end)] * 0.72), fontsize=10,
                 arrowprops=dict(arrowstyle="->", color="#2f3e4e", lw=1.1))
    ax1.set_title("在用整包存量（按体系堆叠）与合计", fontsize=12.5, loc="left")
    ax1.set_ylabel("t 整包")
    ax1.yaxis.set_major_formatter(FuncFormatter(thousand))
    ax1.grid(axis="y", color="#dde3e9", lw=0.8)
    ax1.legend(loc="upper left", fontsize=9.5, frameon=False)
    ax1.set_xlim(years[0], years[-1])

    li_stock_t = [rec["li"]["stock"][y] / 1000.0 for y in years]
    li_ret_t = [rec["li"]["retired"][y] / 1000.0 for y in years]
    ax2.plot(years, li_stock_t, color=COLOR_LI, lw=2.6, zorder=4, label="LFP 在用锂存量（t Li，左轴）")
    ax2b = ax2.twinx()
    ax2b.bar(years, li_ret_t, color="#d99a94", width=0.68, alpha=0.9, edgecolor="#c4706a", lw=0.5,
             zorder=2, label="LFP 年退役锂（t Li/a，右轴）")
    ax2.axvline(hist_end + 0.5, color="#8c96a1", ls="--", lw=1.2)
    ax2.set_title("LFP 在用锂存量与年退役锂（未细分三元 Li 未解，保持 null）", fontsize=12.5, loc="left")
    ax2.set_xlabel("年份")
    ax2.set_ylabel("t Li")
    ax2b.set_ylabel("t Li / a")
    ax2.grid(axis="y", color="#dde3e9", lw=0.8)
    h1, l1 = ax2.get_legend_handles_labels()
    h2, l2 = ax2b.get_legend_handles_labels()
    ax2.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=9.5, frameon=False)

    peak_l = max(range(len(years)), key=lambda i: li_stock_t[i])
    ax2.text(0.985, 0.06, f"LFP 锂存量峰值 {years[peak_l]} 年 {li_stock_t[peak_l]:,.0f} t Li",
             transform=ax2.transAxes, ha="right", fontsize=10, color=COLOR_LI,
             bbox=dict(boxstyle="round,pad=0.35", fc="white", ec="#d8c7c4", alpha=0.95))

    fig.text(0.01, 0.012,
             "注释：锂量按车型配套强度（BEV/PHEV 10.266、公交 10.875、中卡 13.659 kg Li/t 整包）自 LFP 首装队列推算，"
             "属 LFP 部分口径；未细分三元不取 622/811 平均，故整体锂量不完整。",
             fontsize=8.6, color="#5b6672")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    out = FIG_DIR / "fig4_dmfa_stock_and_li.png"
    fig.savefig(out, dpi=DPI)
    plt.close(fig)
    return out


def main() -> int:
    raw = load_dataset(DATASET_JSON)
    prepare(raw)
    inflows = cohort_inflows(raw)
    records = [run_case(raw, case, inflows) for case in raw["conditional_case_definitions"]]
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    p3 = draw_retirement(records)
    p4 = draw_stock_li(records)
    for p in (p3, p4):
        print(f"  → {p.relative_to(WORKDIR)}  ({p.stat().st_size / 1024:.1f} KB)")
    print("完成：dMFA 两张图已生成（300 DPI）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
