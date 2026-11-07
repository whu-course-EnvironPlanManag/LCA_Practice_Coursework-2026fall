# -*- coding: utf-8 -*-
"""
成员 B · 任务四：敏感性分析与帕累托多目标寻优
=========================================================
1. 读取 scenario_results.csv；
2. 单因素敏感性分析（.对 GWP 与 LCOR 的摆幅 tornado）；
3. 可行域内以 (min GWP, min LCOR) 为双目标提取帕累托前沿，按
   归一化理想点欧氏距离最小化准则标定拐点（Knee Point）为推荐方案 B，
   并给出成本最优锚点 A 与环境最优锚点 C；
4. 生成 4 张出版级图表（300 DPI）至 figures_output/。

外部情景（grid_ef / lithium_price / energy_efficiency）与
可调决策变量（green_ratio / process_mix）严格分离：敏感性仅展示
各维度的边际影响，寻优仅在可行域的非支配解上标定锚点。
"""

from __future__ import annotations

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from lca_model import LCAModel
from scenario_analysis import build_activities as _ba
import literature_override

_BASE = os.path.dirname(os.path.abspath(__file__))
_RESULTS = os.path.join(_BASE, "..", "data_cohort", "scenario_results.csv")
_FIG = os.path.join(_BASE, "..", "figures_output")

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

DECISION_VARS = ["green_ratio", "process_mix"]
SCENARIO_VARS = ["grid_ef", "lithium_price_usd", "energy_efficiency"]


# ---------------------------------------------------------------------------
# 帕累托非支配排序
# ---------------------------------------------------------------------------
def pareto_front(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """返回 (min x, min y) 双目标下的非支配解下标。"""
    n = len(x)
    idx = np.arange(n)
    front = []
    for i in range(n):
        dom = ((x <= x[i]) & (y <= y[i]) & ((x < x[i]) | (y < y[i])))
        if not dom.any():
            front.append(i)
    return np.array(front)


def sensitivity_range(df: pd.DataFrame, var: str, target: str) -> float:
    """单因素摆幅：参数各水平下目标均值的极差。"""
    by = df.groupby(var)[target].mean()
    return by.max() - by.min()


def _reference_row(df: pd.DataFrame) -> pd.Series:
    """选取基准参考工况（80%绿电 / 50%直接再生占比 / 网电0.556 / 基准能效）；
    网格中不存在该组合时回退到 GWP 中位工况。仅用于环境贡献拆解的展示锚点。"""
    cond = (
        (df["green_ratio"] == 0.8)
        & (df["process_mix"] == 0.5)
        & (df["grid_ef"] == 0.556)
        & (df["energy_efficiency"] == 1.0)
    )
    idx = df.index[cond]
    if len(idx):
        return df.loc[idx[0]]
    return df.loc[(df["gwp_kgco2e"] - df["gwp_kgco2e"].median()).abs().idxmin()]


def _plot_env_contribution(res, subtitle: str) -> None:
    """环境贡献拆解图（GWP100 与水耗），不依赖 LCOR。"""
    bd = res.breakdown.sort_values("gwp_kgco2e", ascending=True)
    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    axes[0].barh(bd["item"], bd["gwp_kgco2e"], color="#15803d")
    axes[0].set_title(f"GWP100 环境贡献拆解（{subtitle}）")
    axes[0].set_xlabel("kg CO2e/t Li2CO3")
    bd2 = res.breakdown.sort_values("water_l", ascending=True)
    axes[1].barh(bd2["item"], bd2["water_l"] / 1000, color="#0369a1")
    axes[1].set_title(f"水耗贡献拆解（{subtitle}）")
    axes[1].set_xlabel("m3/t Li2CO3")
    for ax in axes:
        ax.grid(alpha=0.3, axis="x")
    fig.tight_layout()
    fig.savefig(os.path.join(_FIG, "fig_b1_environmental_contribution.png"), dpi=300)
    plt.close(fig)


def _plot_gwp_sensitivity(df: pd.DataFrame) -> None:
    """GWP100 单因素敏感性摆幅（全工况，不依赖 LCOR）。"""
    gwp_sens = {v: sensitivity_range(df, v, "gwp_kgco2e")
                for v in DECISION_VARS + SCENARIO_VARS}
    names = list(gwp_sens.keys())
    vals = [gwp_sens[k] for k in names]
    order = np.argsort(vals)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh([names[i] for i in order], [vals[i] for i in order], color="#16a34a")
    ax.set_title("GWP100 单因素敏感性摆幅")
    ax.set_xlabel("kg CO2e/t Li2CO3 摆幅")
    ax.grid(alpha=0.3, axis="x")
    fig.tight_layout()
    # 旧版 GWP 敏感性图（fig_b3_sensitivity）已被 final_20261104 图件取代，保留计算但不写盘
    plt.close(fig)


def _plot_literature_diagnostic() -> str:
    """文献迁移「文献值 vs 2024 规范阈值」诊断图（忠实情景无可行解的原因可视化）。"""
    rows = literature_override.diagnostic_rows()
    labels = [r["label"] for r in rows]
    lit = [r["literature"] for r in rows]
    thr = [r["threshold"] for r in rows]
    y = np.arange(len(labels))[::-1]  # 顶部显示第一个
    h = 0.36
    colors = ["#16a34a" if l >= t else "#dc2626" for l, t in zip(lit, thr)]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(y + h / 2, lit, height=h, color=colors, label="文献值")
    ax.barh(y - h / 2, thr, height=h, color="#cbd5e1", label="2024 规范阈值")
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlim(0, 1.0)
    ax.set_xlabel("回收率 / 捕集率（fraction）")
    ax.set_title("文献迁移忠实值 vs 2024 规范阈值（红=低于阈值）")
    for yi, l, t in zip(y, lit, thr):
        ax.text(l + 0.02, yi + h / 2, f"{l:.3g}", va="center", fontsize=8)
    ax.legend(loc="lower right", fontsize=8)
    ax.grid(alpha=0.3, axis="x")
    fig.tight_layout()
    p = os.path.join(_FIG, "fig_b4_literature_vs_threshold.png")
    fig.savefig(p, dpi=300)
    plt.close(fig)
    return p


def make_charts(df: pd.DataFrame, model: LCAModel) -> dict:
    os.makedirs(_FIG, exist_ok=True)
    # 正式结果资格：仅认「非合成LCOR 且 非阈值试填政策」的行（formal_result_eligible）。
    # 旧 CSV 无该列或全为 False 时 feas 为空 → 仅输出环境维度图，不生成 B-4 帕累托前沿。
    if "formal_result_eligible" in df.columns:
        feas = df[df["formal_result_eligible"]].reset_index(drop=True)
    else:
        feas = pd.DataFrame()
    # 试算完成模式（USE_ALL_A_DATA）下 result_grade=provisional_all_a，B-4 标题需明示试算性质。
    _provisional = ("result_grade" in df.columns
                    and (df["result_grade"] == "provisional_all_a").any())
    # 文献迁移模式（USE_LITERATURE_OVERRIDE）下 literature_scenario 非空，B-4 标「文献迁移 literature」。
    _literature = ("literature_scenario" in df.columns
                   and (df["literature_scenario"] != "").any())
    out = {}

    # 文献迁移忠实情景的「文献值 vs 阈值」诊断图（独立于可行域/LCOR，诚实呈现无可行解原因）。
    if _literature:
        out["literature_diagnostic"] = _plot_literature_diagnostic()

    # 图2 水碳权衡（不依赖可行域与LCOR）
    fig, ax = plt.subplots(figsize=(9, 6))
    sc = ax.scatter(df["water_l"] / 1000, df["gwp_kgco2e"], c=df["grid_ef"],
                    cmap="viridis", s=8, alpha=0.7)
    fig.colorbar(sc, ax=ax, label="区域电网碳强度 (kg CO2e/kWh)")
    ax.set_xlabel("水资源消耗（m3/t Li2CO3）")
    ax.set_ylabel("GWP100（kg CO2e/t Li2CO3）")
    ax.set_title("水耗—碳排放权衡（颜色=电网碳强度）")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    p_trade = os.path.join(_FIG, "fig_b2_water_carbon_tradeoff.png")
    fig.savefig(p_trade, dpi=300)
    plt.close(fig)
    out["tradeoff"] = p_trade

    if feas.empty or feas["lcor_rmb_per_t"].notna().sum() == 0:
        # 尚无正式可行结果（formal_result_eligible=False 或正式 LCOR 未就绪）：
        # 仍输出环境维度的贡献拆解（基准参考工况）与 GWP 敏感性，
        # 帕累托前沿与锚点依赖正式政策 PASS + 成员 C 完整 TEA；合成/试填结果不进入前沿。
        ref = _reference_row(df)
        ref_acts = _ba(ref["process_mix"], ref["energy_efficiency"])
        ref_res = model.compute(activities=ref_acts, green_ratio=ref["green_ratio"],
                                grid_ef=ref["grid_ef"])
        subtitle = (f"基准参考工况：绿电{ref['green_ratio']:.0%} / "
                    f"直接再生占比{ref['process_mix']:.0%}")
        _plot_env_contribution(ref_res, subtitle)
        _plot_gwp_sensitivity(df)
        out["contribution"] = os.path.join(_FIG, "fig_b1_environmental_contribution.png")
        out["sensitivity"] = None  # 旧版图已并入 final_20261104，不写盘
        print("[寻优] 无正式可行结果：已输出环境贡献拆解(基准参考工况)与 GWP 敏感性；"
              "帕累托前沿/锚点待正式政策指标与成员 C 完整 TEA（合成/试填结果已排除）。")
        return out, None

    feas = feas[feas["lcor_rmb_per_t"].notna()].reset_index(drop=True)

    # 帕累托前沿与锚点
    gwp = feas["gwp_kgco2e"].to_numpy()
    lcor = feas["lcor_rmb_per_t"].to_numpy()
    pf = pareto_front(gwp, lcor)
    pf = pf[np.argsort(gwp[pf])]

    # 归一化（min-max）后欧氏距离标定拐点
    g_min, g_max = gwp[pf].min(), gwp[pf].max()
    l_min, l_max = lcor[pf].min(), lcor[pf].max()
    gspan = (g_max - g_min) or 1.0
    lspan = (l_max - l_min) or 1.0
    gn = (gwp[pf] - g_min) / gspan
    ln = (lcor[pf] - l_min) / lspan
    dist = np.sqrt(gn ** 2 + ln ** 2)
    knee_local = int(np.argmin(dist))

    anchor_a = feas["lcor_rmb_per_t"].idxmin()        # 成本最优
    anchor_c = feas["gwp_kgco2e"].idxmin()            # 环境最优
    anchor_b = feas.index[pf[knee_local]]             # 拐点（推荐）

    # 图4 帕累托前沿
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.scatter(gwp, lcor, s=10, c="#cbd5e1", label="可行工况")
    ax.plot(gwp[pf], lcor[pf], "o-", color="#16a34a", ms=4, lw=1.2, label="帕累托前沿")
    for tag, ii in [("A 成本最优", anchor_a), ("B 拐点/推荐", anchor_b), ("C 环境最优", anchor_c)]:
        ax.scatter(feas.loc[ii, "gwp_kgco2e"], feas.loc[ii, "lcor_rmb_per_t"],
                   s=140, zorder=5, edgecolors="black", label=tag)
    ax.set_xlabel("全生命周期 GWP100（kg CO2e/t Li2CO3）")
    ax.set_ylabel("平准化回收净成本 LCOR（元/t Li2CO3）")
    _title_suffix = "（文献迁移 literature）" if _literature else ("（试算 PROVISIONAL）" if _provisional else "")
    ax.set_title("政策约束下回收路径帕累托前沿与拐点标定" + _title_suffix)
    ax.legend(loc="best", fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    # 旧版 B-4 帕累托图（fig_b4_pareto_frontier）已被 final_20261104/fig07_pareto 取代，保留计算但不写盘
    plt.close(fig)
    out["pareto"] = None

    # 图3 敏感性 tornado
    gwp_sens = {v: sensitivity_range(feas, v, "gwp_kgco2e")
                for v in DECISION_VARS + SCENARIO_VARS}
    lcor_sens = {v: sensitivity_range(feas, v, "lcor_rmb_per_t")
                 for v in DECISION_VARS + SCENARIO_VARS}
    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    for ax, sens, title, unit in [
        (axes[0], gwp_sens, "GWP100 敏感性", "kg CO2e/t"),
        (axes[1], lcor_sens, "LCOR 敏感性", "元/t"),
    ]:
        names = list(sens.keys())
        vals = [sens[k] for k in names]
        order = np.argsort(vals)
        ax.barh([names[i] for i in order], [vals[i] for i in order], color="#16a34a")
        ax.set_title(title)
        ax.set_xlabel(unit + " 摆幅")
        ax.grid(alpha=0.3, axis="x")
    fig.tight_layout()
    # 旧版敏感性图（fig_b3_sensitivity）已被 final_20261104 图件取代，保留计算但不写盘
    plt.close(fig)
    out["sensitivity"] = None

    # 图1 环境贡献拆解（推荐方案 B）
    b_row = feas.loc[anchor_b]
    acts = _ba(b_row["process_mix"], b_row["energy_efficiency"])
    res = model.compute(activities=acts, green_ratio=b_row["green_ratio"],
                        grid_ef=b_row["grid_ef"])
    bd = res.breakdown.sort_values("gwp_kgco2e", ascending=True)
    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    axes[0].barh(bd["item"], bd["gwp_kgco2e"], color="#15803d")
    axes[0].set_title("环境贡献拆解（GWP100，推荐方案 B）")
    axes[0].set_xlabel("kg CO2e/t Li2CO3")
    bd2 = res.breakdown.sort_values("water_l", ascending=True)
    axes[1].barh(bd2["item"], bd2["water_l"] / 1000, color="#0369a1")
    axes[1].set_title("水耗贡献拆解（推荐方案 B）")
    axes[1].set_xlabel("m3/t Li2CO3")
    for ax in axes:
        ax.grid(alpha=0.3, axis="x")
    fig.tight_layout()
    p_contrib = os.path.join(_FIG, "fig_b1_environmental_contribution.png")
    fig.savefig(p_contrib, dpi=300)
    plt.close(fig)
    out["contribution"] = p_contrib

    anchors = {
        "A": feas.loc[anchor_a],
        "B": feas.loc[anchor_b],
        "C": feas.loc[anchor_c],
    }
    return out, anchors


def main() -> None:
    df = pd.read_csv(_RESULTS, encoding="utf-8")
    model = LCAModel()
    figs, anchors = make_charts(df, model)
    print("[寻优] 已生成图表：")
    for k, v in figs.items():
        print(f"  {k}: {os.path.basename(v) if v else '（已停写盘）'}")

    if anchors is None:
        print("\n[推荐方案] 尚未标定：正式政策引擎无PASS工况或LCOR未就绪，"
              "待成员A年度数量与成员C经济证据补齐后重跑。")
        return

    print("\n[推荐方案锚点对比]")
    cols = ["case_id", "green_ratio", "process_mix", "grid_ef",
            "lithium_price_usd", "energy_efficiency", "li_recovery",
            "gwp_kgco2e", "water_l", "lcor_rmb_per_t"]
    for tag, row in anchors.items():
        print(f"  锚点 {tag}: " + ", ".join(f"{c}={row[c]:,.3g}" for c in cols))

    print("\n[推荐方案 B 唯一编号]" )
    b = anchors["B"]
    print(f"  case_id = {int(b['case_id'])}  （完整参数见上表及 data_cohort/scenario_results.csv）")


if __name__ == "__main__":
    main()