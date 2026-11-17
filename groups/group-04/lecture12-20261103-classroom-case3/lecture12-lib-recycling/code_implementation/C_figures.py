# -*- coding: utf-8 -*-
"""
C_figures.py —— 生成汇报稿第 16—22 页对应的 7 张 300 dpi 图

  fig1_env_performance.png       P16 环境绩效：原生 / 全网电 / 拐点 / 100% 绿电
  fig2_water_carbon.png          P17 水—碳权衡：三种电网结构 × 0—100% 绿电
  fig3_gwp_breakdown.png         P18 碳足迹拆解：电力 70.1% / 试剂 14.2% / 热能 13.8% / 运输 1.9%
  fig4_pareto_front.png          P19 帕累托前沿与 A/B/C 锚点
  fig5_cost_revenue.png          P21 成本 8 项 / 收入 4 项
  fig6_npv_utilization.png       P20 利用率—NPV—回收期
  fig7_sensitivity.png           P22 四因子敏感性区间 + 蒙特卡洛 90% 区间

用法：python C_figures.py（先运行对应 C 模块计算脚本）
"""
import csv
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from C_env_econ_core import DATA, FIG

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["axes.edgecolor"] = "#B8C2C8"
plt.rcParams["axes.linewidth"] = 0.8

C_TEAL, C_GREEN, C_ORANGE, C_GREY = "#0F4C5C", "#2E7D5B", "#E07A5F", "#5B6770"
C_BLUE, C_RED, C_LIGHT = "#4C78A8", "#C0392B", "#E8EEF1"


def jload(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as fh:
        return json.load(fh)


def cload(name):
    with open(os.path.join(DATA, name), encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def save(fig, name):
    path = os.path.join(FIG, name)
    fig.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  → {name}")


def clean(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(colors=C_GREY, labelsize=9)
    ax.grid(axis="y", color=C_LIGHT, linewidth=0.8)
    ax.set_axisbelow(True)


# ---------------- fig1 环境绩效 ----------------
d = jload("C_supplement_env_performance.json")
labels = ["原生精炼", "全网电（绿电 0%）", "拐点（绿电 55%）", "100% 绿电"]
gwp = [d["primary"]["gwp_kg_per_t"], d["grid_only"]["gwp_kg_per_t"],
       d["knee"]["gwp_kg_per_t"], d["green100"]["gwp_kg_per_t"]]
water = [d["primary"]["water_m3_per_t"], d["grid_only"]["water_m3_per_t"],
         d["knee"]["water_m3_per_t"], d["green100"]["water_m3_per_t"]]

fig, ax = plt.subplots(figsize=(8.8, 4.4))
bars = ax.bar(labels, gwp, width=0.52, color=[C_GREY, C_LIGHT, C_TEAL, C_GREEN], edgecolor="white")
for b, v in zip(bars, gwp):
    ax.text(b.get_x() + b.get_width() / 2, v + 300, f"{v:,.0f}", ha="center", va="bottom", fontsize=9.5, color="#1B2A32")
ax.set_ylabel("GWP  kg CO$_2$e / t 电池", fontsize=9.5, color="#1B2A32")
ax.set_ylim(0, max(gwp) * 1.18)
clean(ax)
ax2 = ax.twinx()
ax2.plot(labels, water, marker="o", color=C_ORANGE, linewidth=2, markersize=6, label="水耗")
for x, v in zip(range(len(water)), water):
    if x == 0:
        ax2.text(x + 0.12, v - 1.2, f"{v:.2f} m³", fontsize=8.5, color=C_ORANGE, ha="left", va="center")
    else:
        ax2.text(x, v + 0.75, f"{v:.2f} m³", fontsize=8.5, color=C_ORANGE, ha="center", va="bottom")
ax2.set_ylim(6.5, 29.5)
ax.set_xlim(-0.55, 3.55)
ax2.set_ylabel("水耗  m³ / t 电池", fontsize=9.5, color=C_ORANGE)
ax2.tick_params(colors=C_ORANGE, labelsize=9)
for s in ("top", "left"):
    ax2.spines[s].set_visible(False)
ax.set_title(f"P16 环境绩效：较原生基准减碳 {d['reduction']['gwp_pct']:.1f}%、减水 {d['reduction']['water_pct']:.1f}%",
             fontsize=12, color="#1B2A32", pad=12, loc="left")
save(fig, "fig1_env_performance.png")

# ---------------- fig2 水—碳权衡 ----------------
rows = cload("C_supplement_water_carbon_curve.csv")
keys = sorted({(r["grid_ef"], r["grid_water_m3_per_kwh"]) for r in rows}, key=lambda x: float(x[0]))
name_map = {"0.3140": "低排放电网（水核为主）", "0.5366": "中排放电网（全国平均基线）", "0.7488": "高排放电网（煤电为主）"}
colors = [C_BLUE, C_TEAL, C_RED]
fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.2))
for (ef, gw), c in zip(keys, colors):
    sub = [r for r in rows if r["grid_ef"] == ef]
    g = [float(r["green_share"]) * 100 for r in sub]
    lab = name_map.get(f"{float(ef):.4f}", f"EF {ef}")
    axes[0].plot(g, [float(r["gwp_kg_per_t"]) for r in sub], color=c, linewidth=1.8, label=lab)
    axes[1].plot(g, [float(r["water_m3_per_t"]) for r in sub], color=c, linewidth=1.8, label=lab)
for ax, title, ylab in zip(axes, ["GWP 随绿电比例下降", "水耗随绿电比例下降"],
                           ["kg CO$_2$e / t", "m³ / t"]):
    ax.axvline(55, color=C_GREY, linestyle="--", linewidth=0.9)
    ax.set_xlabel("绿电比例 %", fontsize=9, color="#1B2A32")
    ax.set_ylabel(ylab, fontsize=9, color="#1B2A32")
    ax.set_title(title, fontsize=10.5, color="#1B2A32", loc="left")
    clean(ax)
axes[1].legend(fontsize=8, frameon=False, loc="upper right")
axes[0].annotate("拐点 55%", xy=(55, d["knee"]["gwp_kg_per_t"]), xytext=(62, 1650),
                 fontsize=8, color=C_GREY, arrowprops=dict(arrowstyle="->", color=C_GREY, lw=0.8))
fig.suptitle("P17 同等绿电比例下，低排放电网反而更耗水（直再 60% 不变）", fontsize=12, x=0.01, ha="left")
fig.tight_layout()
save(fig, "fig2_water_carbon.png")

# ---------------- fig3 碳足迹拆解 ----------------
bk = d["knee"]["breakdown_kg"]
pct = d["knee"]["breakdown_pct"]
items = [("电力（2,972 kWh×0.269）", "electricity", C_TEAL),
         ("试剂上游", "reagent", C_ORANGE),
         ("热能 / 天然气", "heat", C_BLUE),
         ("收集运输（200 km）", "transport", C_GREY)]
vals = [bk[k] for _, k, _ in items]
fig, ax = plt.subplots(figsize=(8.8, 3.6))
y = np.arange(len(items))[::-1]
ax.barh(y, vals, color=[c for _, _, c in items], height=0.55)
for yy, v, (lab, k, _) in zip(y, vals, items):
    ax.text(v + 12, yy, f"{v:.0f} kg · {pct[k]:.1f}%", va="center", fontsize=9, color="#1B2A32")
ax.set_yticks(y)
ax.set_yticklabels([lab for lab, _, _ in items], fontsize=9)
ax.set_xlim(0, max(vals) * 1.35)
ax.set_xlabel("kg CO$_2$e / t 电池", fontsize=9, color="#1B2A32")
ax.grid(axis="x", color=C_LIGHT, linewidth=0.8)
ax.set_axisbelow(True)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.tick_params(axis="y", length=0, colors="#1B2A32")
ax.set_title(f"P18 碳足迹拆解：合计 {d['knee']['gwp_kg_per_t']:,.0f} kg CO$_2$e/t，电力占 {pct['electricity']:.1f}%",
             fontsize=11.5, loc="left", color="#1B2A32")
save(fig, "fig3_gwp_breakdown.png")

# ---------------- fig4 帕累托前沿 ----------------
pj = jload("C_supplement_pareto.json")
grid = cload("C_supplement_pareto_grid.csv")
front = cload("C_supplement_pareto_front.csv")
fig, ax = plt.subplots(figsize=(8.8, 5.0))
feas = [r for r in grid if r["policy_ok"] == "1"]
ax.scatter([float(r["gwp"]) for r in feas], [float(r["lcor"]) for r in feas],
           s=12, color=C_LIGHT, edgecolor="none",
           label=f"政策可行工况（{pj['feasible_single_price']} 组 × 3 档锂价 = {pj['feasible_total_3_prices']}）")
ax.plot([float(r["gwp"]) for r in front], [float(r["lcor"]) for r in front],
        color=C_TEAL, linewidth=1.6, marker="o", markersize=3.5,
        label=f"非支配前沿（d = 60%，{pj['front']} 组）")
anch = pj["anchors"]
pts = [("A 成本最优", anch["A_cost_optimal"], (-14, 16), "right"),
       ("B 拐点", anch["B_knee"], (12, 16), "left"),
       ("C 碳最优", anch["C_carbon_optimal"], (12, 14), "left")]
for lab, p, off, ha in pts:
    ax.scatter(p["gwp"], p["lcor"], s=90, marker="*", color=C_ORANGE, zorder=5)
    ax.annotate(f"{lab}\n({p['gwp']:,.0f}, {p['lcor']:,.0f})", (p["gwp"], p["lcor"]),
                xytext=off, textcoords="offset points", fontsize=8.2, color="#1B2A32", ha=ha)
ax.set_xlim(380, 2080)
ax.set_ylim(-6080, -4480)
ax.set_xlabel("GWP  kg CO$_2$e / t", fontsize=9.5, color="#1B2A32")
ax.set_ylabel("LCOR  元 / t（负值=净收益）", fontsize=9.5, color="#1B2A32")
clean(ax)
ax.legend(fontsize=8, frameon=False, loc="lower left")
ax.set_title(f"P19 多目标寻优：{pj['feasible_total_3_prices']} 组可行、{pj['front']} 组非支配，拐点 "
             f"MAC {pj['knee']['mac']:,.0f} 元/t CO$_2$e", fontsize=11.5, loc="left", color="#1B2A32")
save(fig, "fig4_pareto_front.png")

# ---------------- fig5 成本 / 收入 ----------------
cr = cload("C_supplement_cost_revenue.csv")
costs = [r for r in cr if r["type"] == "cost"]
revs = [r for r in cr if r["type"] == "revenue"]
fig, axes = plt.subplots(1, 2, figsize=(10.6, 4.4))
yc = np.arange(len(costs))[::-1]
axes[0].barh(yc, [float(r["yuan_per_t"]) for r in costs], color=C_TEAL, height=0.55)
for yy, r in zip(yc, costs):
    axes[0].text(float(r["yuan_per_t"]) + 250, yy, f"{float(r['yuan_per_t']):,.0f}", va="center", fontsize=8.5)
axes[0].set_yticks(yc)
axes[0].set_yticklabels([r["item"] for r in costs], fontsize=8.5)
axes[0].set_xlim(0, 19000)
axes[0].set_title(f"成本合计 {sum(float(r['yuan_per_t']) for r in costs):,.0f} 元/t", fontsize=10.5, loc="left")
axes[0].set_xlabel("元 / t", fontsize=9)
yr = np.arange(len(revs))[::-1]
axes[1].barh(yr, [float(r["yuan_per_t"]) for r in revs], color=C_GREEN, height=0.55)
for yy, r in zip(yr, revs):
    axes[1].text(float(r["yuan_per_t"]) + 250, yy, f"{float(r['yuan_per_t']):,.0f}", va="center", fontsize=8.5)
axes[1].set_yticks(yr)
axes[1].set_yticklabels([r["item"] for r in revs], fontsize=8.5)
axes[1].set_xlim(0, 13000)
axes[1].set_title(f"收入合计 {sum(float(r['yuan_per_t']) for r in revs):,.0f} 元/t", fontsize=10.5, loc="left")
axes[1].set_xlabel("元 / t", fontsize=9)
for ax in axes:
    ax.grid(axis="x", color=C_LIGHT, linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis="y", length=0, colors="#1B2A32")
te = jload("C_supplement_techenomics.json")
fig.suptitle(f"P21 技术经济：LCOR {te['lcor_yuan_per_t']:,.0f} 元/t、MAC {te['mac_yuan_per_t_co2e']:,.0f} 元/t CO$_2$e",
             fontsize=11.5, x=0.01, ha="left")
fig.tight_layout()
save(fig, "fig5_cost_revenue.png")

# ---------------- fig6 利用率—NPV — 回收期 ----------------
fin = cload("C_supplement_finance_utilization.csv")
u = [float(r["util_pct"]) for r in fin]
npv = [float(r["npv_yi"]) for r in fin]
pb_raw = [float(r["payback_a"]) if r["payback_a"] not in ("inf", "-inf", "nan") else 33.0 for r in fin]
pb = [min(v, 20.5) for v in pb_raw]
fig, ax = plt.subplots(figsize=(8.8, 4.6))
bars = ax.bar([f"{v:.0f}%" for v in u], npv, color=[C_RED if v < 0 else C_GREEN for v in npv], width=0.5)
for b, v in zip(bars, npv):
    ax.text(b.get_x() + b.get_width() / 2, v + (0.25 if v >= 0 else -0.45), f"{v:.2f}", ha="center",
            fontsize=9, color="#1B2A32")
ax.axhline(0, color="#1B2A32", linewidth=0.8)
ax.set_ylabel("NPV  亿元", fontsize=9.5, color="#1B2A32")
ax.set_xlabel("全园进料利用率（20,000 t/a = 100%）", fontsize=9.5, color="#1B2A32")
clean(ax)
ax2 = ax.twinx()
ax2.plot([f"{v:.0f}%" for v in u], pb, marker="o", color=C_ORANGE, linewidth=1.8)
for x, (v, raw) in enumerate(zip(pb, pb_raw)):
    ax2.text(x + 0.1, v + 0.35, ">20" if raw > 20 else f"{raw:.1f}", fontsize=8.3, color=C_ORANGE)
ax2.set_ylabel("静态回收期  年", fontsize=9.5, color=C_ORANGE)
ax2.set_ylim(0, 22)
ax2.tick_params(colors=C_ORANGE)
for s in ("top", "left"):
    ax2.spines[s].set_visible(False)
fj = jload("C_supplement_finance.json")
ax.set_title(f"P20 财务可行性：满负荷 NPV {fj['utilization_rows'][-1]['npv_yi']:.1f} 亿元、"
             f"{fj['utilization_rows'][-1]['payback_a']:.1f} 年回本（盈亏平衡 {fj['break_even_util']*100:.0f}%）",
             fontsize=11.5, loc="left", color="#1B2A32")
save(fig, "fig6_npv_utilization.png")

# ---------------- fig7 敏感性 ----------------
sj = jload("C_supplement_sensitivity.json")
mc = sj["monte_carlo"]
base_gwp, base_lcor = sj["base"]["gwp"], sj["base"]["lcor"]

fig, axes = plt.subplots(1, 2, figsize=(10.6, 4.2))
gwp_bars = [("蒙特卡洛 90%", mc["gwp_p05"], mc["gwp_p95"], C_GREY),
            ("电网结构", sj["grid_structure"]["low"]["gwp"], sj["grid_structure"]["high"]["gwp"], C_TEAL),
            ("直再 60→45%", base_gwp, sj["direct_share"]["d45"]["gwp"], C_ORANGE)]
labels_g = [b[0] for b in gwp_bars]
for i, (lab, lo, hi, c) in enumerate(gwp_bars):
    y = len(gwp_bars) - i - 1
    axes[0].broken_barh([(lo, hi - lo)], (y - 0.28, 0.56), color=c, alpha=0.9)
    axes[0].text(hi + 25, y, f"{lo:,.0f}—{hi:,.0f}", va="center", fontsize=8.3)
axes[0].axvline(base_gwp, color="#1B2A32", linestyle="--", linewidth=0.9)
axes[0].set_yticks(range(len(gwp_bars))[::-1])
axes[0].set_yticklabels(labels_g, fontsize=9)
axes[0].set_xlim(700, 1650)
axes[0].set_xlabel("GWP  kg CO$_2$e / t", fontsize=9)
axes[0].set_title("GWP 变动区间（基准 1,141）", fontsize=10.5, loc="left")

lcor_bars = [("蒙特卡洛 90%", mc["lcor_p05"], mc["lcor_p95"], C_GREY),
             ("锂价 10k→50k", sj["lithium_price"]["high"]["lcor"], sj["lithium_price"]["low"]["lcor"], C_TEAL),
             ("直再 60→45%", sj["direct_share"]["d45"]["lcor"], base_lcor, C_ORANGE),
             ("溢价线性化（满绿电）", sj["green_premium_linear"]["lcor_at_100"], base_lcor, C_BLUE)]
labels_l = [b[0] for b in lcor_bars]
for i, (lab, lo, hi, c) in enumerate(lcor_bars):
    y = len(lcor_bars) - i - 1
    axes[1].broken_barh([(lo, hi - lo)], (y - 0.28, 0.56), color=c, alpha=0.9)
    axes[1].text(hi + 130, y, f"{lo:,.0f}—{hi:,.0f}", va="center", ha="left", fontsize=8.3)
axes[1].axvline(base_lcor, color="#1B2A32", linestyle="--", linewidth=0.9)
axes[1].set_yticks(range(len(lcor_bars))[::-1])
axes[1].set_yticklabels(labels_l, fontsize=9)
axes[1].set_xlim(-10400, -3300)
axes[1].set_xlabel("LCOR  元 / t（负值=净收益）", fontsize=9)
axes[1].set_title("LCOR 变动区间（基准 −5,726）", fontsize=10.5, loc="left")
for ax in axes:
    ax.grid(axis="x", color=C_LIGHT, linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis="y", length=0, colors="#1B2A32")
fig.suptitle("P22 敏感性：电网结构最影响碳、锂价最影响收益；90% 区间为情景区间（非统计置信区间）",
             fontsize=11.5, x=0.01, ha="left")
fig.tight_layout()
save(fig, "fig7_sensitivity.png")

print("全部图已生成到 figures_output/")
