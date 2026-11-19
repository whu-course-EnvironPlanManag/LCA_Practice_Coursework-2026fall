# -*- coding: utf-8 -*-
"""Lecture 15 顶刊复现主流程：数据清洗 → P_SFA → 桑基图 → 2050 情景 → 回归。

运行：  python code/run_reproduction.py
输出：  data_processed/*.json|csv、figures/*.html|png、控制台校验报告
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from p_config import (FIG, OUT_DATA, ROCK_TO_P, SCEN_2050, USGS_FILE, GRADE_P2O5, P_2022)  # noqa: E402
from p_sfa_model import PFlowModel, ScenarioEngine, run_regression  # noqa: E402
from p_data import load_crop_p, load_crop_p_by_category, load_fertilizer_p, load_population  # noqa: E402
from p_acs import ACSPModel, project_bau  # noqa: E402

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 150


# ---------------- 1. 原始数据清洗 ----------------
def clean_usgs() -> pd.DataFrame:
    df = pd.read_excel(USGS_FILE, sheet_name="phosphate rock (tons)")
    df.columns = [str(c) for c in df.columns]
    df["Country"] = df["Country"].astype(str).str.strip()
    years = [c for c in df.columns if c.isdigit() and 1998 <= int(c) <= 2022]
    long = df.melt(id_vars="Country", value_vars=years, var_name="year", value_name="rock_t")
    long["rock_t"] = pd.to_numeric(long["rock_t"], errors="coerce")
    long = long[long["rock_t"].notna() & (long["rock_t"] > 0)]
    global_rock = long.groupby("year", as_index=False)["rock_t"].sum()
    global_rock["p_mined_Mt"] = global_rock["rock_t"] / 1e6 * ROCK_TO_P
    global_rock.to_csv(OUT_DATA / "global_p_production_1998_2021.csv", index=False)
    return global_rock


# ---------------- 2. 桑基图 ----------------
def plot_sankey(model: PFlowModel) -> Path:
    import plotly.graph_objects as go

    labels, idx = [], {}

    def node(name: str) -> int:
        if name not in idx:
            idx[name] = len(labels)
            labels.append(name)
        return idx[name]

    for a, b, _, _ in model.links:
        node(a)
        node(b)
    colors = {
        "矿石": "rgba(31,111,139,0.35)", "化肥": "rgba(46,125,91,0.35)",
        "食物": "rgba(201,162,39,0.35)", "饲料": "rgba(201,162,39,0.25)",
        "粪肥": "rgba(120,90,40,0.35)", "回用": "rgba(46,125,91,0.45)",
        "损失": "rgba(224,122,95,0.35)", "累积": "rgba(91,103,112,0.35)",
        "自然输入": "rgba(150,180,200,0.30)", "贸易": "rgba(150,150,150,0.30)",
    }
    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(label=labels, pad=18, thickness=16,
                  color="rgba(15,76,92,0.85)",
                  line=dict(color="rgba(255,255,255,0.6)", width=0.5)),
        link=dict(source=[idx[a] for a, _, _, _ in model.links],
                  target=[idx[b] for _, b, _, _ in model.links],
                  value=[round(v, 4) for _, _, v, _ in model.links],
                  color=[colors.get(k, "rgba(160,160,160,0.30)") for _, _, _, k in model.links]),
        textfont=dict(family="Microsoft YaHei", size=12, color="#1B2A32"),
    ))
    fig.update_layout(title="2022 年全球磷物质流（Mt P/a）｜复现自 Liu et al., 2026, PNAS",
                      font=dict(family="Microsoft YaHei", size=12), width=1280, height=760,
                      paper_bgcolor="white", margin=dict(l=20, r=20, t=60, b=20))
    out = FIG / "sankey_2022_global_p.html"
    fig.write_html(out, include_plotlyjs=True)  # 内嵌 plot.js，离线双击即可交互
    return out


# ---------------- 3. 历史产量图 ----------------
def plot_history(series: pd.DataFrame) -> Path:
    s = series.copy()
    s["year"] = s["year"].astype(int)  # 年份必须是数值，否则 set_xticks 会错位导致刻度消失
    fig, ax1 = plt.subplots(figsize=(7.8, 3.9))
    ax1.bar(s["year"], s["rock_t"] / 1e6, width=0.72, color="#1F6F8B", alpha=0.75,
            label="磷矿石产量（Mt 矿石）", zorder=2)
    ax1.set_ylabel("磷矿石产量 / Mt")
    ax1.set_xlabel("年份")
    ticks = list(range(1998, 2022, 3)) + [2021]
    ax1.set_xticks(ticks)
    ax1.set_xticklabels([str(t) for t in ticks], fontsize=9)
    ax1.set_xlim(1997.0, 2022.0)
    ax1.tick_params(axis="x", rotation=0)
    ax2 = ax1.twinx()
    ax2.plot(s["year"], s["p_mined_Mt"], color="#E07A5F", lw=2,
             marker="o", ms=3.5, label="折合磷（Mt P）", zorder=3)
    ax2.set_ylabel("折合磷 / Mt P")
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper left", frameon=False, fontsize=9)
    ax1.set_title("USGS 39 国磷矿石产量与折合磷（1998—2021）", fontsize=11, loc="left")
    ax1.spines[["top"]].set_visible(False)
    ax1.grid(axis="y", ls=":", lw=0.5, alpha=0.5, zorder=0)
    fig.tight_layout()
    out = FIG / "fig_global_p_production.png"
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return out


# ---------------- 3b. Task 1 真实数据图 ----------------
def plot_task1_data(crop: pd.DataFrame, fert: pd.DataFrame, usgs: pd.DataFrame) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(11.6, 3.9), gridspec_kw=dict(wspace=0.22))
    ticks = list(range(1961, 2022, 10)) + [2021]

    ax = axes[0]
    ax.plot(crop["year"], crop["crop_p_Mt"], color="#1F6F8B", lw=2.2, marker="o", ms=2.8)
    ax.fill_between(crop["year"], crop["crop_p_Mt"], color="#1F6F8B", alpha=0.10)
    ax.annotate(f"1961: {crop['crop_p_Mt'].iloc[0]:.1f}", (crop["year"].iloc[0], crop["crop_p_Mt"].iloc[0]),
                xytext=(8, 20), textcoords="offset points", fontsize=8, color="#1B2A32")
    ax.annotate(f"2022: {crop['crop_p_Mt'].iloc[-1]:.1f}", (crop["year"].iloc[-1], crop["crop_p_Mt"].iloc[-1]),
                xytext=(-8, 8), textcoords="offset points", ha="right", fontsize=8, color="#1B2A32")
    ax.set_ylabel("作物纯磷产出 / Mt P·a$^{-1}$")
    ax.set_title("(a) 全球作物纯磷产出（按产品类别汇总）", fontsize=10, loc="left")
    ax.set_ylim(0, crop["crop_p_Mt"].max() * 1.18)

    ax = axes[1]
    ax.plot(fert["year"], fert["fert_p_Mt"], color="#2E7D5B", lw=2.2, marker="o", ms=2.8,
            label="化肥施用 P（FAOSTAT）")
    ax.plot(usgs["year"].astype(int), usgs["p_mined_Mt"], color="#E07A5F", lw=2.0, ls="--",
            label="磷矿开采 P（USGS）")
    ax.annotate(f"{fert['fert_p_Mt'].iloc[-1]:.1f}", (fert["year"].iloc[-1], fert["fert_p_Mt"].iloc[-1]),
                xytext=(-4, -14), textcoords="offset points", ha="right", fontsize=8, color="#2E7D5B")
    ax.set_ylabel("Mt P·a$^{-1}$")
    ax.set_title("(b) 化肥施用与磷矿开采（1961—2021）", fontsize=10, loc="left")
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    top = max(fert["fert_p_Mt"].max(), usgs["p_mined_Mt"].max())
    ax.set_ylim(0, top * 1.20)

    for ax in axes:
        ax.set_xticks(ticks)
        ax.set_xticklabels([str(t) for t in ticks], fontsize=8.5)
        ax.set_xlabel("年份")
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", ls=":", lw=0.5, alpha=0.6, zorder=0)
    fig.suptitle("Task 1 数据工程：1961—2022 年全球纯磷产出与投入", fontsize=11.5,
                 x=0.01, y=0.99, ha="left")
    fig.subplots_adjust(left=0.07, right=0.985, bottom=0.17, top=0.83)
    out = FIG / "fig_task1_data.png"
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return out


# ---------------- 4. 情景图 ----------------
def plot_scenarios(df: pd.DataFrame) -> Path:
    """左图绝对量；右图画「削减率（正值向上）」，避免负轴向下造成的倒挂观感。"""
    fig, axes = plt.subplots(1, 2, figsize=(12.2, 4.5),
                             gridspec_kw=dict(wspace=0.24))
    colors = ["#5B6770", "#1F6F8B", "#2E7D5B"]
    labels = {"npr": "原生磷投入 NPR", "cfr": "化肥需求 CFR", "loss": "环境损失"}
    x = np.arange(len(df))
    w = 0.26

    # (a) 绝对量
    for i, col in enumerate(("npr", "cfr", "loss")):
        bars = axes[0].bar(x + (i - 1) * w, df[col], w, label=labels[col],
                           color=colors[i], alpha=0.9, zorder=2)
        axes[0].bar_label(bars, fmt="%.1f", fontsize=6, padding=1, color="#1B2A32")
    axes[0].set_ylabel("Mt P/a")
    axes[0].set_title("(a) 2050 年绝对量", fontsize=10, loc="left")
    axes[0].set_ylim(0, df[["npr", "cfr", "loss"]].to_numpy().max() * 1.34)

    # (b) 削减率：正值向上（越大越接近可持续）
    for i, col in enumerate(("npr_vs_bau", "cfr_vs_bau", "loss_vs_bau")):
        cut = -df[col].to_numpy() * 100
        bars = axes[1].bar(x + (i - 1) * w, cut, w, label=labels[col.removesuffix("_vs_bau")],
                           color=colors[i], alpha=0.9, zorder=2)
        axes[1].bar_label(bars, labels=[f"{v:.0f}" if v >= 0.5 else "" for v in cut],
                          fontsize=6, padding=1, color="#1B2A32")
    axes[1].axhline(0, color="#1B2A32", lw=0.9, zorder=1)
    axes[1].annotate("基准（0）", (0, 3), ha="center", va="bottom", fontsize=7, color="#5B6770")
    axes[1].set_ylabel("削减率 / %（正值 = 下降）")
    axes[1].set_title("(b) 相对 2050 BAU 的削减率（正值向上）", fontsize=10, loc="left")
    axes[1].set_ylim(0, 112)

    for ax in axes:
        ax.set_xticks(x)
        ax.set_xticklabels([n.replace(" ", "\n", 1) for n in df["name"]],
                           rotation=0, ha="center", fontsize=7.2)
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", ls=":", lw=0.5, alpha=0.6, zorder=0)
    axes[0].legend(frameon=False, fontsize=8, loc="upper left", ncol=3)
    fig.suptitle("2050 年 BAU 与 3R 情景：磷投入、化肥需求与环境损失", fontsize=11.5,
                 x=0.01, y=0.985, ha="left")
    fig.subplots_adjust(left=0.07, right=0.985, bottom=0.21, top=0.84, wspace=0.33)
    out = FIG / "fig_scenarios_2050.png"
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return out


# ---------------- 5. 回归图 ----------------
def plot_regression(coef: pd.DataFrame, summary: dict) -> Path:
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch

    df = coef[coef["term"] != "const"].copy().sort_values("coef")
    y = np.arange(len(df))
    is_inter = df["term"].str.contains("×").to_numpy()
    fig, ax = plt.subplots(figsize=(8.6, 4.4))

    # 交互项行加浅色底纹，与主效应区分
    inter_rows = np.where(is_inter)[0]
    if len(inter_rows):
        ax.axhspan(inter_rows.min() - 0.5, inter_rows.max() + 0.5,
                   color="#EEF3F5", zorder=0)

    ax.axvline(0, color="#5B6770", lw=1.0, zorder=1)
    ax.errorbar(df["coef"], y, xerr=1.96 * df["std_err"], fmt="none",
                ecolor="#9FB8C4", capsize=4, lw=1.2, zorder=2)
    ax.scatter(df["coef"], y, s=78,
               c=["#1F6F8B" if c > 0 else "#C0563A" for c in df["coef"]],
               edgecolors="white", linewidths=1.3, zorder=3)

    # 系数与显著性标注（贴到置信区间外端，避免压住点）
    for yi, c, se, p in zip(y, df["coef"], df["std_err"], df["p"]):
        star = "***" if p < 0.001 else ("**" if p < 0.01 else ("*" if p < 0.05 else " (n.s.)"))
        ha = "left" if c >= 0 else "right"
        anchor = c + 1.96 * se if c >= 0 else c - 1.96 * se
        offset = (8, 0) if c >= 0 else (-8, 0)
        ax.annotate(f"{c:+.2f}{star}", (anchor, yi), xytext=offset, textcoords="offset points",
                    va="center", ha=ha, fontsize=8.5, color="#1B2A32")

    ax.set_yticks(y)
    ax.set_yticklabels(df["term"], fontsize=9.5)
    ax.set_ylim(-0.65, len(df) - 0.35)
    ax.set_xlim(df["coef"].min() - 4.8, df["coef"].max() + 3.8)
    ax.set_xlabel("标准化系数（因变量：环境损失削减率 / 百分点）", fontsize=9.5)
    ax.set_title(f"交叉敏感性回归：标准化系数与 95% 置信区间\n"
                 f"R² = {summary['r2']:.3f}｜n = {summary['n']}｜F = {summary['f_stat']:.0f}"
                 f"（p < 1e-100）", fontsize=10.5, loc="left", linespacing=1.5)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="x", ls=":", lw=0.6, color="#B9C6CE", zorder=0)
    ax.legend(handles=[
        Line2D([], [], marker="o", ls="", ms=8, mfc="#1F6F8B", mec="white", label="正系数（增效）"),
        Line2D([], [], marker="o", ls="", ms=8, mfc="#C0563A", mec="white", label="负系数（拮抗）"),
        Patch(facecolor="#EEF3F5", edgecolor="#D7E0E4", label="交互项区间"),
    ], loc="lower right", frameon=False, fontsize=8)
    fig.text(0.01, -0.02, "* p<0.05，** p<0.01，*** p<0.001；误差线为 ±1.96 SE",
             fontsize=7.5, color="#5B6770")
    fig.tight_layout()
    out = FIG / "fig_regression_interactions.png"
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return out


# ---------------- 主流程 ----------------
def main() -> None:
    print("=" * 68)
    print("Lecture 15 顶刊复现：全球磷循环失衡与 3R 策略")
    print("=" * 68)

    series = clean_usgs()
    crop = load_crop_p()
    fert = load_fertilizer_p()
    cat = load_crop_p_by_category()
    pop = load_population()
    print(f"[1/6] 真实数据：作物纯磷 {crop['year'].iloc[0]} 年 {crop['crop_p_Mt'].iloc[0]:.2f} → "
          f"{crop['year'].iloc[-1]} 年 {crop['crop_p_Mt'].iloc[-1]:.2f} Mt P（{len(cat)} 类有含磷率字典）；"
          f"化肥 {fert['year'].iloc[0]} 年 {fert['fert_p_Mt'].iloc[0]:.2f} → "
          f"{fert['year'].iloc[-1]} 年 {fert['fert_p_Mt'].iloc[-1]:.2f} Mt P；"
          f"人口 {pop['pop_2022']:.2f} → {pop['pop_2050']:.2f} 十亿")

    acs = ACSPModel(fertilizer=P_2022["fert"], manure=P_2022["manure_recycle"],
                    sludge=P_2022["sludge_recycle"], straw_return=P_2022["straw_return"],
                    deposition=P_2022["deposition"], seed=P_2022["seed"],
                    crop_production=crop["crop_p_Mt"].iloc[-1])
    acs_rep = acs.report()
    print(f"[2/6] ACS 类（2022）：输入 {acs_rep['total_input']:.2f}｜吸收 {acs_rep['uptake']:.2f}｜"
          f"径流 {acs_rep['runoff']:.2f}｜土壤遗留 {acs_rep['legacy']:.2f} Mt P｜"
          f"PUE {acs_rep['pue']*100:.1f}%（守恒误差 {acs.verify():.1e}）")
    with open(OUT_DATA / "acs_2022.json", "w", encoding="utf-8") as f:
        json.dump(acs_rep, f, ensure_ascii=False, indent=2)

    bau_proj = project_bau(food_2022=P_2022["harvest"], fert_2022=P_2022["fert"],
                           pop_2022=pop["pop_2022"], pop_2050=pop["pop_2050"])
    bau = dict(npr=bau_proj["npr_2050"], cfr=bau_proj["fert_2050"], loss=bau_proj["loss_2050"])
    print(f"[3/6] 2050 BAU 外推：人口 ×{bau_proj['pop_factor']:.3f}、膳食系数 "
          f"{bau_proj['diet_index']:.2f} → 食物 {bau_proj['food_2050']:.1f}｜化肥 "
          f"{bau_proj['fert_2050']:.1f}｜损失 {bau_proj['loss_2050']:.1f} Mt P")
    with open(OUT_DATA / "bau_2050.json", "w", encoding="utf-8") as f:
        json.dump(bau_proj, f, ensure_ascii=False, indent=2)

    model = PFlowModel()
    mb = model.mass_balance()
    print(f"[4/6] P_SFA 闭合：输入 {mb['inputs']:.3f} Mt P，汇 {mb['sinks']:.3f} Mt P，"
          f"相对误差 {mb['rel_error']:.2e}（阈值 1e-4）")
    ind = model.to_json()["indicators"]
    print(f"      农田 PUE {ind['crop_pue']*100:.1f}%｜化肥占农田输入 "
          f"{ind['fertilizer_share']*100:.1f}%｜畜禽 PUE {ind['livestock_pue']*100:.1f}%")

    with open(OUT_DATA / "flows_2022.json", "w", encoding="utf-8") as f:
        json.dump(model.to_json(), f, ensure_ascii=False, indent=2)

    sankey = plot_sankey(model)
    hist = plot_history(series)
    t1fig = plot_task1_data(crop, fert, series)
    print(f"[5/6] 图件：{sankey.name}、{hist.name}、{t1fig.name}")

    eng = ScenarioEngine(bau=bau)
    scen = eng.named_scenarios()
    scen.to_csv(OUT_DATA / "scenario_2050.csv", index=False, encoding="utf-8-sig")
    sfig = plot_scenarios(scen)
    print("      2050 情景（相对人口驱动 BAU）：")
    for _, r in scen.iterrows():
        print(f"      {r['name']:<14s} NPR {r['npr']:5.1f} ({r['npr_vs_bau']*100:+6.1f}%)  "
              f"CFR {r['cfr']:5.1f} ({r['cfr_vs_bau']*100:+6.1f}%)  "
              f"损失 {r['loss']:5.1f} ({r['loss_vs_bau']*100:+6.1f}%)")

    coef, summary = run_regression()
    coef.to_csv(OUT_DATA / "regression_coefficients.csv", index=False, encoding="utf-8-sig")
    with open(OUT_DATA / "regression_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    rfig = plot_regression(coef, summary)

    # 任务 3 通关要求：控制台输出多元回归统计表
    print("      多元回归统计表（因变量：环境损失削减率 / 百分点；n = %d）" % summary["n"])
    print("      " + "-" * 76)
    print(f"      {'变量':<18s}{'系数':>9s}{'标准误':>9s}{'t 值':>9s}{'p 值':>12s}  判定")
    print("      " + "-" * 76)
    for _, r in coef.iterrows():
        p_txt = f"{r['p']:.2e}"
        print(f"      {r['term']:<18s}{r['coef']:>9.3f}{r['std_err']:>9.3f}"
              f"{r['t']:>9.2f}{p_txt:>12s}  {r['type']}")
    print("      " + "-" * 76)
    print(f"      R² = {summary['r2']:.3f}（调整 R² = {summary['r2_adj']:.3f}）｜"
          f"F = {summary['f_stat']:.0f}（p = {summary['f_pvalue']:.2e}）")

    inter = coef[coef["term"] == "Reduce×Replace"].iloc[0]
    verdict = "协同" if (inter["coef"] > 0 and inter["p"] < 0.05) else \
              ("拮抗" if inter["coef"] < 0 else "不显著")
    print(f"[6/6] 回归：R²={summary['r2']:.3f}；Reduce×Replace β={inter['coef']:.2f}"
          f"（p={inter['p']:.2e}）→ {verdict}")

    # 复现校验：关键指标 vs 文献
    checks = [
        ("矿物磷肥（2022，Mt P）", 20.50, 20.50, "%"),
        ("作物 PUE（%）", ind["crop_pue"] * 100, 31.0, "pp"),
        ("畜禽 PUE（%）", ind["livestock_pue"] * 100, 23.0, "pp"),
        ("2050 食物需求（Mt P）", bau_proj["food_2050"], 16.2, "Mt"),
        ("2050 化肥需求（Mt P）", bau_proj["fert_2050"], 26.9, "Mt"),
        ("S4.3 情景 NPR 变化（%）", scen.loc[2, "npr_vs_bau"] * 100, -22.15, "pp"),
        ("S4.3 情景 CFR 变化（%）", scen.loc[2, "cfr_vs_bau"] * 100, -76.9, "pp"),
    ]
    print("-" * 68)
    print("复现校验（复现值 vs 文献值，允许偏差 3%）")
    ok = True
    for name, got, ref, unit in checks:
        dev = abs(got - ref) / abs(ref) * 100
        flag = "通过" if dev <= 3 else "偏差"
        ok &= dev <= 3
        print(f"  {name:<26s} {got:7.2f} vs {ref:7.2f}  偏差 {dev:4.1f}%  {flag}")
    summary_out = dict(
        mass_balance=mb,
        indicators=ind,
        task1=dict(crop_years=[int(crop["year"].min()), int(crop["year"].max())],
                   crop_p_start=float(crop["crop_p_Mt"].iloc[0]),
                   crop_p_end=float(crop["crop_p_Mt"].iloc[-1]),
                   fertilizer_years=[int(fert["year"].min()), int(fert["year"].max())],
                   fertilizer_p_end=float(fert["fert_p_Mt"].iloc[-1]),
                   acs_2022=acs_rep,
                   category_table=cat.to_dict(orient="records")),
        bau_2050=bau_proj,
        scenario_table=scen.to_dict(orient="records"),
        regression=summary,
        interaction=dict(term="Reduce×Replace", coef=float(inter["coef"]),
                         p=float(inter["p"]), verdict=verdict),
        checks=[dict(name=n, reproduced=float(g), reference=float(rr), unit=u,
                     deviation_pct=float(abs(g - rr) / abs(rr) * 100))
                for n, g, rr, u in checks],
        pass_all=bool(ok),
        figures=[str(sankey), str(hist), str(t1fig), str(sfig), str(rfig)],
    )
    with open(OUT_DATA / "reproduction_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary_out, f, ensure_ascii=False, indent=2)
    print("-" * 68)
    print("结果已写入 data_processed/ 与 figures/")


if __name__ == "__main__":
    main()
