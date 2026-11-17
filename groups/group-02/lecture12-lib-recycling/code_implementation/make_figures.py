# -*- coding: utf-8 -*-
"""C成员最终交付图件：物料去向、成本、GWP、敏感性、价格、Pareto与政策矩阵。

运行：python make_figures.py
输出：figures_output/final_20261104/*.png (300 dpi) + *.svg
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np

HERE = Path(__file__).resolve()
ROOT = HERE.parents[1]
DATA = ROOT / "data_cohort" / "final_20261104"
FIG = ROOT / "figures_output" / "final_20261104"
FIG.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(HERE.parent))

import lcor_mac_model as M  # noqa: E402
from policy_engine import evaluate_policy  # noqa: E402

plt.rcParams.update({
    "font.sans-serif": ["Microsoft YaHei", "SimHei"],
    "axes.unicode_minus": False,
    "figure.dpi": 120,
    "savefig.dpi": 300,
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.labelsize": 10,
})

C_GREEN = "#2E7D32"
C_BLUE = "#1565C0"
C_ORANGE = "#EF6C00"
C_RED = "#C62828"
C_GREY = "#9E9E9E"
C_TEAL = "#00838F"
C_PURPLE = "#6A1B9A"


def read_csv(name):
    with (DATA / name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def save(fig, name):
    fig.tight_layout()
    fig.savefig(FIG / f"{name}.png", bbox_inches="tight")
    fig.savefig(FIG / f"{name}.svg", bbox_inches="tight")
    plt.close(fig)


def fig_material_flow(m):
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 5.2),
                             gridspec_kw={"width_ratios": [1, 1.55]})
    ax = axes[0]
    labels = ["梯次保留", "LFP再生", "三元再生"]
    vals = [m["retained_pack_t"], m["lfp_pack_t"], m["nmc_pack_t"]]
    colors = [C_TEAL, C_GREEN, C_BLUE]
    bars = ax.barh(labels[::-1], vals[::-1], color=colors[::-1], height=0.55)
    for b, v in zip(bars, vals[::-1]):
        ax.text(v + 800, b.get_y() + b.get_height() / 2, f"{v:,.1f} t/a",
                va="center", fontsize=9)
    ax.set_xlim(0, 48000)
    ax.set_xlabel("整包质量，t/a")
    ax.set_title("(a) 68,000 t/a 整包分流")

    flow = read_csv("material_flow_R1.csv")
    pick = [f for f in flow if f["flow_id"] in
            ("F11", "F12", "F14", "F15", "F16", "F17", "F18", "F19", "F20",
             "F22", "F23", "F24", "F27", "F29")]
    pick = sorted(pick, key=lambda r: float(r["quantity_t"]), reverse=True)[:12]
    names = [r["stream"] for r in pick][::-1]
    qty = [float(r["quantity_t"]) for r in pick][::-1]
    dest = [r["destination"] for r in pick][::-1]
    palette = {"锂产品": C_GREEN, "铁磷产品": C_GREEN, "副产物": C_TEAL,
               "铜产品": C_ORANGE, "铝产品": C_ORANGE, "镍产品": C_BLUE,
               "钴产品": C_BLUE, "锰产品": C_BLUE, "一般固废": C_GREY,
               "危废": C_RED, "再生/资源化": C_PURPLE}
    cols = [palette.get(d, C_GREY) for d in dest]
    ax2 = axes[1]
    bars = ax2.barh(names, qty, color=cols, height=0.62)
    for b, v in zip(bars, qty):
        ax2.text(v + max(qty) * 0.01, b.get_y() + b.get_height() / 2,
                 f"{v:,.0f}", va="center", fontsize=8)
    ax2.set_xlabel("年度数量，t/a（湿基或商品量，见表注）")
    ax2.set_title("(b) 再生产品与残渣去向（前12项）")
    ax2.set_xlim(0, max(qty) * 1.18)
    handles = [Patch(color=c, label=k) for k, c in palette.items()]
    ax2.legend(handles=handles, fontsize=7, loc="lower right", frameon=False, ncol=2)
    save(fig, "fig01_material_flow")


def fig_cost(m):
    r = M.evaluate(m, feed_mode="value", linkage=0.80, recovery_case="improved",
                   rd_compliance=True, green_fraction=0.5)
    rows = sorted(r["costs"]["rows"], key=lambda x: -x["annual_CNY"])[:12]
    names = [x["item"] for x in rows][::-1]
    vals = [x["annual_CNY"] / 1e6 for x in rows][::-1]
    fig, ax = plt.subplots(figsize=(8.6, 5.4))
    bars = ax.barh(names, vals, color=C_BLUE, height=0.62)
    for b, v in zip(bars, vals):
        ax.text(v + max(vals) * 0.01, b.get_y() + b.get_height() / 2,
                f"{v:,.1f}", va="center", fontsize=8)
    ax.set_xlabel("年度费用，百万元/a（含税现金口径）")
    ax.set_title("推荐工况年费用构成（前12项）")
    ax.set_xlim(0, max(vals) * 1.2)
    save(fig, "fig02_cost_structure")

    rev = sorted(r["revenues"]["rows"], key=lambda x: -x["annual_CNY"])[:10]
    fig, ax = plt.subplots(figsize=(8.6, 4.8))
    names = [x["product"] for x in rev][::-1]
    vals = [x["annual_CNY"] / 1e6 for x in rev][::-1]
    bars = ax.barh(names, vals, color=C_GREEN, height=0.62)
    for b, v in zip(bars, vals):
        ax.text(v + max(vals) * 0.01, b.get_y() + b.get_height() / 2,
                f"{v:,.1f}", va="center", fontsize=8)
    ax.set_xlabel("情景结算价值，百万元/a（参考价×实现系数）")
    ax.set_title("推荐工况收入构成（前10项，非已核实合同收入）")
    ax.set_xlim(0, max(vals) * 1.2)
    save(fig, "fig03_revenue_structure")


def fig_gwp(m):
    r = M.evaluate(m, feed_mode="value", linkage=0.80, recovery_case="improved",
                   rd_compliance=True, green_fraction=1.0)
    items = []
    for row in r["environment"]["rows"]:
        items.append((row["item"], row["gwp_kg"] / 1000.0, "排放"))
    for row in r["credits"]["rows"]:
        items.append((row["product"] + "（抵扣）", -row["avoided_kg"] / 1000.0, "抵扣"))
    items = sorted(items, key=lambda x: -abs(x[1]))[:18]
    names = [x[0] for x in items][::-1]
    vals = [x[1] for x in items][::-1]
    kinds = [x[2] for x in items][::-1]
    colors = [C_GREEN if v < 0 else C_ORANGE for k, v in zip(kinds, vals)]
    fig, ax = plt.subplots(figsize=(9.6, 6.4))
    bars = ax.barh(names, vals, color=colors, height=0.62)
    span = max(abs(min(vals)), abs(max(vals)))
    for b, v in zip(bars, vals):
        ax.text(v + (span * 0.012 if v >= 0 else -span * 0.012),
                b.get_y() + b.get_height() / 2, f"{v:,.0f}",
                va="center", ha="left" if v >= 0 else "right", fontsize=8)
    ax.axvline(0, color="black", linewidth=0.9)
    ax.set_xlim(-span * 1.28, span * 1.28)
    ax.set_xlabel("t CO2e/a")
    ax.set_title(f"推荐工况温室气体清单：过程排放{r['gwp_gross_t']:,.0f} t，"
                 f"抵扣{r['credits']['avoided_kg']/1000:,.0f} t，"
                 f"净排放{r['gwp_net_t']:,.0f} t")
    handles = [Patch(color=C_ORANGE, label="过程排放"), Patch(color=C_GREEN, label="联产品抵扣")]
    ax.legend(handles=handles, frameon=False, loc="lower right")
    save(fig, "fig04_gwp_waterfall")


def fig_sensitivity():
    rows = read_csv("sensitivity_final.csv")
    base = next(float(r["lcor_CNY_per_t"]) for r in rows if r["parameter"] == "基准")
    pairs = {}
    for r in rows:
        if r["parameter"] in ("基准", "原生基准"):
            continue
        pairs.setdefault(r["parameter"], []).append((float(r["lcor_CNY_per_t"]), r["value"]))
    items = []
    for k, vals in pairs.items():
        if len(vals) >= 2:
            lo = min(vals, key=lambda x: x[0])
            hi = max(vals, key=lambda x: x[0])
            items.append((k, lo[0] - base, hi[0] - base, str(lo[1]), str(hi[1])))
    items.sort(key=lambda x: abs(x[2] - x[1]))
    fig, ax = plt.subplots(figsize=(9.6, 5.4))
    y = np.arange(len(items))
    for i, (name, dl, dh, ll, hl) in enumerate(items):
        ax.barh(i, dl, color=C_GREEN, height=0.55)
        ax.barh(i, dh, color=C_RED, height=0.55)
        ax.text(dl, i, f" {ll}", va="center", ha="right" if dl < 0 else "left",
                fontsize=7, color=C_GREEN)
        ax.text(dh, i, f" {hl}", va="center", ha="left" if dh > 0 else "right",
                fontsize=7, color=C_RED)
    ax.axvline(0, color="black", linewidth=0.9)
    ax.set_yticks(y)
    ax.set_yticklabels([x[0] for x in items])
    ax.set_xlabel("相对基准的LCOR变化，元/t LCE")
    ax.set_title("单因素敏感性（基准：合规工况，LCOR≈6元/t LCE）")
    save(fig, "fig05_lcor_tornado")


def fig_price():
    m = M.physical()
    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.4))
    prices = [80000, 100000, 120000, 133000, 160000, 200000, 250000]
    for link, color in [(0.75, C_GREEN), (0.80, C_BLUE), (0.85, C_RED)]:
        vals = []
        old = M.PRICES["lce"]
        for p in prices:
            M.PRICES["lce"] = (p, old[1])
            r = M.evaluate(m, linkage=link, recovery_case="improved", rd_compliance=True)
            vals.append(r["lcor_CNY_per_t"])
        M.PRICES["lce"] = old
        axes[0].plot([p / 1000 for p in prices], [v / 1000 for v in vals], marker="o",
                     color=color, label=f"采购价联动{int(link*100)}%")
    axes[0].axhline(0, color="black", linewidth=0.8)
    axes[0].set_xlabel("电池级碳酸锂价格，千元/t")
    axes[0].set_ylabel("LCOR，千元/t LCE")
    axes[0].set_title("(a) 锂价与采购联动对LCOR的影响")
    axes[0].legend(frameon=False, fontsize=8)

    links = np.linspace(0.60, 1.00, 17)
    vals = [M.evaluate(m, linkage=float(x), recovery_case="improved",
                       rd_compliance=True)["lcor_CNY_per_t"] / 1000 for x in links]
    axes[1].plot(links * 100, vals, marker="o", color=C_PURPLE)
    axes[1].axhline(0, color="black", linewidth=0.8)
    axes[1].axvline(80, color=C_GREY, linestyle="--", linewidth=0.9)
    axes[1].set_xlabel("采购价占可回收金属价值比例，%")
    axes[1].set_ylabel("LCOR，千元/t LCE")
    axes[1].set_title("(b) 采购价联动比例与保本点")
    save(fig, "fig06_price_impact")


def fig_pareto():
    rows = read_csv("scenarios_final.csv")
    pts = [r for r in rows
           if float(r["linkage"]) == 0.80 and float(r["li_realization"]) == 0.70
           and float(r["metal_realization"]) == 0.85
           and r["recovery_case"] == "improved" and r["energy_case"] == "R1"]
    fig, ax = plt.subplots(figsize=(8.8, 5.6))
    for r in pts:
        x = float(r["gwp_kg_per_t_lce"]) / 1000
        y = float(r["lcor_CNY_per_t"]) / 1000
        g = float(r["green_fraction"])
        color = C_BLUE if r["chemistry"] == "NMC622" else C_ORANGE
        ax.scatter(x, y, marker="o", s=40 + 180 * g, color=color, alpha=0.55,
                   edgecolor="black", linewidth=0.5, zorder=3)
    summary = json.loads((DATA / "summary.json").read_text(encoding="utf-8"))
    front = summary.get("pareto_nominal", [])
    fx = [p["gwp_kg_per_t_lce"] / 1000 for p in front]
    fy = [p["lcor_CNY_per_t"] / 1000 for p in front]
    if len(front) > 1:
        ax.plot(fx, fy, color=C_RED, linewidth=1.4, linestyle="--", zorder=2)
    knee = summary.get("knee_nominal")
    if knee:
        ax.scatter([knee["gwp_kg_per_t_lce"] / 1000], [knee["lcor_CNY_per_t"] / 1000],
                   marker="*", s=360, color=C_ORANGE, edgecolor="black", zorder=5)
    ax.axhline(0, color="grey", linewidth=0.7, linestyle="--")
    ax.set_ylim(-0.5, 2.0)
    ax.set_xlabel("净GWP，t CO2e/t LCE（负值表示净减排）")
    ax.set_ylabel("LCOR，千元/t LCE（负值表示净收益）")
    ax.set_title("名义工况GWP与LCOR：绿电提高同时改善两项指标")
    handles = [plt.Line2D([], [], marker="o", color="w", markerfacecolor=C_BLUE,
                          markeredgecolor="black", label="NMC622"),
               plt.Line2D([], [], marker="o", color="w", markerfacecolor=C_ORANGE,
                          markeredgecolor="black", label="NMC811"),
               plt.Line2D([], [], marker="*", color="w", markerfacecolor=C_ORANGE,
                          markeredgecolor="black", markersize=12,
                          label=f"膝点 {knee['case_id']}" if knee else "膝点")]
    ax.legend(handles=handles, frameon=False, fontsize=8, loc="lower left")
    save(fig, "fig07_pareto")


def fig_policy():
    m = M.physical()
    cases = []
    for cid, rec, rd in [("基准R1", "base", False), ("合规改进", "improved", True)]:
        r = M.evaluate(m, linkage=0.80, recovery_case=rec, rd_compliance=rd)
        pm = r["policy_metrics"]
        cj = {"case_id": cid, "route": "smelting", "evaluation_date": "2026-11-04",
              "metals_present": ["Li", "Ni", "Co", "Mn", "Cu", "Al"],
              "eu_material_recovery_scope": False, "eu_new_battery_scope": False,
              "produces_lithium_carbonate": True,
              "metrics": {k: v for k, v in pm.items() if v is not None}}
        cases.append((cid, evaluate_policy(cj)))
    rules = ["CN_LI", "CN_CU", "CN_AL", "CN_ENERGY", "CN_RD", "CN_WATER", "CN_POWDER"]
    names = {"CN_LI": "锂回收率≥90%", "CN_CU": "铜回收率≥98%", "CN_AL": "铝回收率≥98%",
             "CN_ENERGY": "碳酸锂能耗<2200", "CN_RD": "研发≥收入3%",
             "CN_WATER": "废水回用≥90%", "CN_POWDER": "粉料回收≥98%"}
    fig, ax = plt.subplots(figsize=(8.2, 3.8))
    colors = {"PASS": C_GREEN, "FAIL": C_RED, "UNKNOWN": C_GREY, "NOT_APPLICABLE": "#E0E0E0"}
    for j, (cid, res) in enumerate(cases):
        for i, rule in enumerate(rules):
            row = next((c for c in res["checks"] if c["rule_id"] == rule), None)
            status = row["status"] if row else "UNKNOWN"
            ax.add_patch(plt.Rectangle((i - 0.45, j - 0.4), 0.9, 0.8,
                                       color=colors.get(status, C_GREY)))
            ax.text(i, j, status, ha="center", va="center", fontsize=7,
                    color="white" if status in {"PASS", "FAIL"} else "black")
    ax.set_xlim(-0.6, len(rules) - 0.4)
    ax.set_ylim(-0.6, len(cases) - 0.4)
    ax.set_xticks(range(len(rules)))
    ax.set_xticklabels([names[r] for r in rules], rotation=25, ha="right", fontsize=8)
    ax.set_yticks(range(len(cases)))
    ax.set_yticklabels([c[0] for c in cases])
    ax.set_title("政策引擎逐项判定（2026-11-04，课程口径）")
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    save(fig, "fig08_policy_matrix")


def main():
    m = M.physical()
    fig_material_flow(m)
    fig_cost(m)
    fig_gwp(m)
    fig_sensitivity()
    fig_price()
    fig_pareto()
    fig_policy()
    print("figures ->", FIG)


if __name__ == "__main__":
    main()
