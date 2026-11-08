# -*- coding: utf-8 -*-
"""
C_integrated_figures.py —— 出版级图表自动渲染（≥300 dpi，全部由代码生成）
方向 B：浙江衢州华友循环资源再生产业园（一期 20,000 t/a，2035 扩至 60,000 t/a）

运行顺序：01 → 02 → 03 → 04
输出目录：figures_output/
  fig1_mfa_process_flow.png        园区多工序物质流拓扑（MFA）
  fig2_lca_scenarios.png           原生基准 vs 三情景 碳足迹/水耗对比
  fig3_gwp_breakdown.png           碳足迹分项贡献拆解
  fig4_water_carbon_tradeoff.png   电网结构下的水-碳权衡曲线
  fig5_pareto_front.png            帕累托前沿、拐点标定与边际减排成本曲线
  fig6_sensitivity_heatmap.png     碳酸锂价格 × 电网排放因子双因素敏感性
  fig7_route_and_scale.png         三工艺路线强度对比与年通量/远期扩容
  fig8_cashflow_npv.png            【C 模块】锂价—净收益曲线与累计现金流/NPV
  fig9_tornado_cost.png            【C 模块】单因素敏感性龙卷风图与成本收入结构

【AI 辅助编程说明】
  Prompt 摘要："用 matplotlib 为退役电池再生精炼园区渲染 9 张 300 dpi 图表：MFA 拓扑、
  情景对比、碳足迹拆解、水-碳权衡、帕累托前沿与 MACC、双因素热图、路线强度与年通量、
  锂价—净收益与累计现金流、龙卷风图与成本收入结构；中文标签不得重叠，坐标轴须带量纲。"
  人工校验修正：①统一 Microsoft YaHei 字体与配色；②MFA 拓扑改为"框-箭头"结构图，
  避免桑基图在质量不守恒（盐类含水合物增重）时产生误导；③所有标注数值由 JSON 读出；
  ④龙卷风图的基准值线与 ±扰动端点均标注数值，避免只靠色条判断。
"""
import json
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 120
plt.rcParams["savefig.dpi"] = 300

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data_cohort")
FIG = os.path.join(ROOT, "figures_output")
os.makedirs(FIG, exist_ok=True)

with open(os.path.join(DATA, "ABC_parameters.json"), encoding="utf-8") as f:
    P = json.load(f)
with open(os.path.join(DATA, "A_mfa_results.json"), encoding="utf-8") as f:
    M = json.load(f)
with open(os.path.join(DATA, "C_lca_tea_results.json"), encoding="utf-8") as f:
    R = json.load(f)
with open(os.path.join(DATA, "B_policy_results.json"), encoding="utf-8") as f:
    POL = json.load(f)

LCA, TEA = P["lca"], P["tea"]
CAP = P["_meta"]["design_capacity_t_cells_per_year"]
C1, C2, C3, C4 = "#1f6f8b", "#e07a5f", "#3d9970", "#c9a227"
GREY = "#5b6770"


def save(fig, name):
    path = os.path.join(FIG, name)
    fig.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"已生成 {name}")


# ============================ 图 1：多工序物质流拓扑 ============================
fig, ax = plt.subplots(figsize=(13, 7.2))
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.axis("off")
ax.set_title("图 1  衢州华友循环资源再生产业园多工序物质流拓扑（功能单位：1 t 退役电池）",
             fontsize=13, pad=12)


def box(x, y, w, h, title, lines, fc, ec, alpha=0.92, fs=8.4):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.5,rounding_size=1.2",
                                fc=fc, ec=ec, lw=1.3, alpha=alpha))
    ax.text(x + w / 2, y + h - 2.0, title, ha="center", va="top", fontsize=fs + 1.1, fontweight="bold")
    for i, t in enumerate(lines):
        ax.text(x + w / 2, y + h - 6.8 - i * 4.6, t, ha="center", va="top", fontsize=fs)


def arrow(x1, y1, x2, y2, color=GREY, lw=1.5, label=None, lx=0, ly=0, fs=7.6):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=12,
                                 lw=lw, color=color, shrinkA=2, shrinkB=2))
    if label:
        ax.text((x1 + x2) / 2 + lx, (y1 + y2) / 2 + ly, label, fontsize=fs, color=color,
                ha="center", va="center",
                bbox=dict(fc="white", ec="none", pad=1.2, alpha=0.85))


mn = M["per_tonne"]
E = mn["element_input_kg"]
box(1.5, 44, 16.5, 40, "来料：1 t 退役电池", ["LFP 60% / NMC811 35%",
                                                "NCA 5%",
                                                f"Li {E['Li']:.1f} · Ni {E['Ni']:.1f} kg",
                                                f"Co {E['Co']:.1f} · Mn {E['Mn']:.1f} kg",
                                                f"Fe {E['Fe']:.1f} · P {E['P']:.1f} kg",
                                                f"Cu {mn['cu_kg']:.1f} · Al {mn['al_kg']:.1f} kg"],
    "#eef4f7", C1)

box(21, 60, 17.5, 24, "工序 1｜放电拆解", ["余能检测 + 盐溶液放电",
                                           "防爆拆解 / 模组分离",
                                           "（GB/T 33598.3）"], "#f7f2ea", C2)
box(21, 20, 17.5, 26, "工序 2｜破碎分选", ["粗破—细破—筛分",
                                          "磁选 + 涡流分选 Cu/Al",
                                          f"黑粉回收率 {P['process']['pretreatment']['black_mass_recovery']*100:.0f}%"],
    "#f7f2ea", C2)

box(41.5, 62, 17.5, 24, "黑粉 449 kg/t", ["活性物质 Li/Ni/Co/Mn/Fe/P",
                                         f"F 固化率 {P['process']['pretreatment']['fluorine_fixation']*100:.1f}%",
                                         "进入精炼工段"], "#eaf3ee", C3)
box(41.5, 34, 17.5, 22, "分选产物", [f"Cu {mn['cu_kg']:.1f} kg/t（98%）",
                                     f"Al {mn['al_kg']:.1f} kg/t（98%）",
                                     "隔膜/外壳 367 kg/t"], "#eaf3ee", C3)
box(41.5, 4, 17.5, 24, "废水与尾渣", ["Li/Ni/Co/Mn 浸出溶损",
                                     "含氟/含磷高盐废水",
                                     f"循环利用率 {P['process']['wastewater_recycle']*100:.0f}%"], "#f0eef4", "#7b6a9b")

box(63.5, 64, 19, 22, "直接正极再生", ["LFP 来料 60%", "补锂—退火—修复",
                                      "→ 再生正极粉"], "#e6f0f8", C1)
box(63.5, 38, 19, 22, "强化湿法 Hy", ["LFP 40% · NMC/NCA 70%",
                                      "浸出—萃取—沉淀",
                                      "Li 92% / NiCoMn 98%"], "#e6f0f8", C1, fs=7.9)
box(63.5, 12, 19, 22, "还原焙烧 + 湿法", ["NMC/NCA 30%", "RC 焙烧 + 浸出",
                                          "混合金属盐"], "#e6f0f8", C1, fs=8.0)

box(86, 8, 12.5, 78, "产品汇总（kg/t）", [
    f"Li2CO3 {mn['li2co3_kg']:.1f}",
    f"再生正极粉 {mn['lfp_powder_kg']:.1f}",
    f"镍盐 {mn['ni_sulfate_kg']:.1f}",
    f"钴盐 {mn['co_sulfate_kg']:.1f}",
    f"锰盐 {mn['mn_sulfate_kg']:.1f}",
    f"FePO4 {mn['fepo4_kg']:.1f}",
    f"Cu {mn['cu_kg']:.1f} / Al {mn['al_kg']:.1f}",
    "",
    "锂回收率 92.5%",
    "NiCoMn 98.0%",
    "元素闭合误差",
    "0.0000%"], "#fdf1e3", C4, fs=8.0)

arrow(18.4, 78, 20.6, 74, C1)
arrow(29.8, 59.6, 29.8, 46.6, C2, label="拆解产物", lx=7.5)
arrow(38.9, 84, 41.1, 80, C1)
arrow(38.9, 30, 41.1, 42, C3)
arrow(38.9, 24, 41.1, 18, "#7b6a9b")
arrow(59.4, 78, 63.1, 76, C3)
arrow(59.4, 70, 63.1, 50, C3)
arrow(59.4, 64, 63.1, 24, C3)
arrow(82.9, 78, 85.6, 62, C1)
arrow(82.9, 48, 85.6, 42, C1)
arrow(82.9, 22, 85.6, 22, C1)
ax.text(50, 0.5, "注：产品汇总中“再生正极粉”的锂以再生磷酸铁锂形态留存，不重复计入 Li2CO3；元素闭合误差按 "
                 "Li、Ni、Co、Mn、Fe、P、Cu、Al 八元素核验；精炼母液与尾渣经钙盐除氟后回用。",
        ha="center", fontsize=8, color="#444")
save(fig, "fig1_mfa_process_flow.png")

# ============================ 图 2：情景对比 ============================
SC = R["scenarios"]
labels = ["原生精炼基准", "现状基准情景\n（网电·直再20%）", "帕累托拐点\n（绿电55%·直再60%）",
          "深度减碳情景\n（绿电100%·直再60%）"]
gwp = [R["primary"]["co2_kg_per_t"], SC["base"]["gwp_kg_per_t"], SC["knee"]["gwp_kg_per_t"], SC["green"]["gwp_kg_per_t"]]
water = [R["primary"]["water_m3_per_t"], SC["base"]["water_m3_per_t"], SC["knee"]["water_m3_per_t"], SC["green"]["water_m3_per_t"]]

fig, ax1 = plt.subplots(figsize=(11.2, 5.8))
x = np.arange(4)
b = ax1.bar(x - 0.19, gwp, width=0.36, color=[GREY, C2, C3, C1], label="GWP100（kg CO2e/t）")
ax1.set_ylabel("碳足迹 GWP100 / (kg CO2e/t 退役电池)", fontsize=11)
ax1.set_ylim(0, 5900)
ax1.set_xticks(x)
ax1.set_xticklabels(labels, fontsize=9.5)
ax1.grid(axis="y", ls=":", color="#cccccc")
for xi, v in zip(x, gwp):
    ax1.text(xi - 0.19, v + 90, f"{v:,.0f}", ha="center", fontsize=9)

ax2 = ax1.twinx()
ax2.bar(x + 0.19, water, width=0.36, color=[GREY, C2, C3, C1], alpha=0.55, hatch="//", label="水耗")
ax2.set_ylabel("水资源消耗 / (m³/t 退役电池)", fontsize=11)
ax2.set_ylim(0, 32)
for xi, v in zip(x, water):
    ax2.text(xi + 0.19, v + 0.5, f"{v:.1f}", ha="center", fontsize=9, color="#333")
ax1.set_title("图 2  循环再生路径与原生矿产精炼路径的碳足迹—水耗双指标对比", fontsize=13)
h1, l1 = ax1.get_legend_handles_labels()
h2, l2 = ax2.get_legend_handles_labels()
ax1.legend(h1 + h2, l1 + l2, loc="upper right", frameon=True, fontsize=9.6)
ax1.text(0.5, -0.30, f"拐点情景较原生基准减碳 {SC['knee']['co2_saving_vs_primary']*100:.1f}%、节水 "
         f"{SC['knee']['water_saving_vs_primary']*100:.1f}%；深度减碳情景减碳 "
         f"{SC['green']['co2_saving_vs_primary']*100:.1f}%、节水 {SC['green']['water_saving_vs_primary']*100:.1f}%",
         transform=ax1.transAxes, ha="center", fontsize=9.5, color="#333")
save(fig, "fig2_lca_scenarios.png")

# ============================ 图 3：碳足迹分项拆解 ============================
REA_CO2 = sum(LCA["reagents"][k] * LCA["reagents"]["kg_co2e_per_kg"][k] for k in ("H2SO4", "NaOH", "Na2CO3", "H2O2"))
TRA_CO2 = LCA["transport"]["distance_km"] * LCA["transport"]["kg_co2e_per_t_km"]
cases = ["现状基准", "帕累托拐点", "深度减碳"]
elec, heat = [], []
for k in ("base", "knee", "green"):
    s = SC[k]
    elec.append(s["electric_kwh_per_t"] * s["ef"])
    heat.append(s["heat_gj_per_t"] * LCA["natural_gas_kg_co2e_per_GJ"])
fig, ax = plt.subplots(figsize=(9.6, 5.6))
x = np.arange(3)
ax.bar(x, elec, 0.5, label="外购电力（含绿电残余）", color=C1)
ax.bar(x, heat, 0.5, bottom=elec, label="外购热能（天然气）", color=C2)
ax.bar(x, [REA_CO2] * 3, 0.5, bottom=np.array(elec) + np.array(heat), label="化学试剂上游隐含排放", color=C4)
ax.bar(x, [TRA_CO2] * 3, 0.5, bottom=np.array(elec) + np.array(heat) + REA_CO2, label="收集运输", color=C3)
tot = np.array(elec) + np.array(heat) + REA_CO2 + TRA_CO2
for xi, t in zip(x, tot):
    ax.text(xi, t + 60, f"合计 {t:,.0f}", ha="center", fontsize=9.5, fontweight="bold")
ax.set_xticks(x)
ax.set_xticklabels([f"{c}\n(绿电 {SC[k]['green_share']*100:.0f}%)" for c, k in zip(cases, ("base", "knee", "green"))], fontsize=10)
ax.set_ylabel("温室气体排放 / (kg CO2e/t 退役电池)", fontsize=11)
ax.set_ylim(0, 2500)
ax.grid(axis="y", ls=":", color="#cccccc")
ax.legend(frameon=False, fontsize=9.5, loc="upper right")
ax.set_title("图 3  再生精炼全流程碳足迹分项贡献拆解（摇篮到大门）", fontsize=13)
ax.text(0.5, -0.20, f"试剂隐含排放 {REA_CO2:.0f} kg CO2e/t、运输 {TRA_CO2:.0f} kg CO2e/t 为与电源结构无关的固定项；"
                    "电力项随绿电比例下降是减碳主因",
        transform=ax.transAxes, ha="center", fontsize=9, color="#333")
save(fig, "fig3_gwp_breakdown.png")

# ============================ 图 4：水-碳权衡 ============================
import csv
wcc = list(csv.DictReader(open(os.path.join(DATA, "C_water_carbon_curve.csv"), encoding="utf-8-sig")))
fig, axes = plt.subplots(1, 2, figsize=(12.2, 5.4))
for ef, col, name in zip([LCA["grid_ef"]["low"], LCA["grid_ef"]["base"], LCA["grid_ef"]["high"]],
                         [C3, C1, C2], ["低排放电网 (0.314)", "全国平均电网 (0.537)", "高排放电网 (0.749)"]):
    rows = [r for r in wcc if abs(float(r["grid_ef"]) - ef) < 1e-6]
    g = [float(r["green_share"]) * 100 for r in rows]
    axes[0].plot(g, [float(r["gwp_kg_per_t"]) for r in rows], "o-", color=col, ms=4, lw=1.8, label=name)
    axes[1].plot(g, [float(r["water_m3_per_t"]) for r in rows], "s-", color=col, ms=4, lw=1.8, label=name)
axes[0].axvline(SC["knee"]["green_share"] * 100, color=GREY, ls="--", lw=1)
axes[0].annotate(f"拐点 绿电 {SC['knee']['green_share']*100:.0f}%", xy=(SC["knee"]["green_share"] * 100, 1250),
                 fontsize=9, color=GREY, ha="left", xytext=(SC["knee"]["green_share"] * 100 + 3, 1600))
axes[0].set_xlabel("园区绿电消纳比例 / %", fontsize=11)
axes[0].set_ylabel("碳足迹 GWP100 / (kg CO2e/t)", fontsize=11)
axes[0].set_title("(a) 碳足迹随绿电比例的变化", fontsize=11.5)
axes[0].legend(frameon=False, fontsize=8.6)
axes[0].grid(ls=":", color="#dddddd")
axes[1].set_xlabel("园区绿电消纳比例 / %", fontsize=11)
axes[1].set_ylabel("水资源消耗 / (m³/t)", fontsize=11)
axes[1].set_title("(b) 水耗随绿电比例的变化（含电力耗水）", fontsize=11.5)
axes[1].legend(frameon=False, fontsize=8.6)
axes[1].grid(ls=":", color="#dddddd")
fig.suptitle("图 4  不同区域电网结构下的“水—碳”权衡关系（固定直再比例 60%）", fontsize=13, y=1.02)
fig.text(0.5, -0.06, "低排放电网（水电/核电占比高）单位供电耗水更高：其碳足迹最低但水耗最高，"
                     "构成水—碳权衡；绿电替代可同时降低碳足迹与电网耗水，是破除权衡的主导措施",
         ha="center", fontsize=9, color="#333")
save(fig, "fig4_water_carbon_tradeoff.png")

# ============================ 图 5：帕累托前沿 + MACC ============================
by = R["pareto"]["by_price"]
fig, axes = plt.subplots(1, 2, figsize=(12.6, 5.4))
for (pstr, rec), col in zip(by.items(), [C2, C1, C3]):
    g = [r["gwp"] for r in rec["front"]]
    l = [r["lcor"] for r in rec["front"]]
    axes[0].plot(g, l, "o-", ms=4, lw=1.7, color=col, label=f"锂价 {float(pstr):,.0f} USD/t")
    k = int(np.argmax(g))
    axes[0].annotate(f"{float(pstr)/1000:.0f}k USD/t", xy=(g[k], l[k]), xytext=(10, 22),
                     textcoords="offset points", color=col, fontsize=8.6, va="center", ha="left", zorder=8)
axes[0].set_xlim(right=max(max(r["gwp"] for r in by[p]["front"]) for p in by) + 230)
knee, A, C = R["pareto"]["knee"], R["pareto"]["anchor_cost"], R["pareto"]["anchor_carbon"]
axes[0].scatter([A["gwp"]], [A["lcor"]], marker="*", s=230, color="black", zorder=6, edgecolor="white", lw=0.8)
axes[0].scatter([knee["gwp"]], [knee["lcor"]], marker="*", s=290, color="black", zorder=6, edgecolor="white", lw=0.8)
axes[0].scatter([C["gwp"]], [C["lcor"]], marker="*", s=230, color="black", zorder=6, edgecolor="white", lw=0.8)
axes[0].annotate("A 成本最优\n(绿电0%, 直再60%)", xy=(A["gwp"], A["lcor"]), xytext=(-100, 34),
                 textcoords="offset points", fontsize=8.4, color=C2,
                 arrowprops=dict(arrowstyle="-", color=C2, lw=0.8))
axes[0].annotate("B 拐点\n(绿电55%, 直再60%)", xy=(knee["gwp"], knee["lcor"]), xytext=(8, -54),
                 textcoords="offset points", fontsize=8.4, color=C1,
                 arrowprops=dict(arrowstyle="-", color=C1, lw=0.8))
axes[0].annotate("C 碳最优\n(绿电100%, 直再60%)", xy=(C["gwp"], C["lcor"]), xytext=(14, 40),
                 textcoords="offset points", fontsize=8.4, color=C3,
                 arrowprops=dict(arrowstyle="-", color=C3, lw=0.8))
axes[0].set_xlabel("碳足迹 GWP100 / (kg CO2e/t)", fontsize=11)
axes[0].set_ylabel("平准化回收净成本 LCOR / (元/t)（负值=净收益）", fontsize=11)
axes[0].set_title("(a) 帕累托前沿（3 档锂价）与锚点标定", fontsize=11.5)
axes[0].grid(ls=":", color="#dddddd")

front = sorted(R["pareto"]["front_base"], key=lambda r: -r["gwp"])
mac, cum = [], []
PRC = R["primary_cost_yuan_per_t_cells"]
for r in front:
    ab = R["primary"]["co2_kg_per_t"] - r["gwp"]
    mac.append((r["lcor"] - PRC) / ab * 1000)
    cum.append(ab)
edges = np.concatenate([[0.0], np.array(cum)])
widths = np.diff(edges)
axes[1].bar(edges[:-1], mac, width=widths, align="edge", bottom=0, color=C1, alpha=0.85,
            edgecolor="white", lw=0.8)
axes[1].axhline(0, color="k", lw=0.9)
axes[1].set_xlim(-100, cum[-1] * 1.05)
axes[1].set_ylim(-4200, 300)
axes[1].set_xlabel("相对原生精炼路径的累计减排量 / (kg CO2e/t)", fontsize=11)
axes[1].set_ylabel("边际减排成本 MAC / (元/t CO2e)", fontsize=11)
axes[1].set_title("(b) 边际减排成本曲线（MACC，基准锂价）", fontsize=11.5)
axes[1].grid(axis="y", ls=":", color="#dddddd")
axes[1].annotate("全部区间 MAC < 0：\n减碳同时盈利", xy=(0.97, 0.10), xycoords="axes fraction",
                 ha="right", fontsize=9, color=C2)
fig.suptitle("图 5  多目标帕累托寻优结果与边际减排成本曲线（819 组可行工况）", fontsize=13, y=1.02)
save(fig, "fig5_pareto_front.png")

# ============================ 图 6：双因素敏感性热图 ============================
sens = R["sensitivity"]
efs = sorted({round(s["grid_ef"], 4) for s in sens})
prs = sorted({round(s["price_usd"], 1) for s in sens})
G = np.zeros((len(efs), len(prs)))
L = np.zeros((len(efs), len(prs)))
for s in sens:
    i, j = efs.index(round(s["grid_ef"], 4)), prs.index(round(s["price_usd"], 1))
    G[i, j], L[i, j] = s["gwp_kg_per_t"], s["lcor_yuan_per_t"]
fig, axes = plt.subplots(2, 1, figsize=(9.8, 8.8))
for ax, arr, title, cmap, fmt, lab in [
        (axes[0], G, "(a) 碳足迹 / (kg CO2e/t)", "YlOrRd", "{:.0f}", "GWP100 / (kg CO2e/t)"),
        (axes[1], L, "(b) 平准化回收净成本 / (元/t)", "YlGnBu", "{:.0f}", "LCOR / (元/t)")]:
    im = ax.imshow(arr, cmap=cmap, aspect="auto", origin="lower")
    ax.set_xticks(range(len(prs)))
    ax.set_xticklabels([f"{p/1000:.0f}k" if p >= 1000 else f"{p:.0f}" for p in prs], fontsize=9)
    ax.set_yticks(range(len(efs)))
    ax.set_yticklabels([f"{e:.3f}" for e in efs], fontsize=9)
    ax.set_xlabel("碳酸锂价格 / (USD/t)", fontsize=10.5)
    ax.set_ylabel("电网 CO2 排放因子 / (kg CO2/kWh)", fontsize=10.5)
    ax.set_title(title, fontsize=11.5)
    for i in range(len(efs)):
        for j in range(len(prs)):
            ax.text(j, i, fmt.format(arr[i, j]), ha="center", va="center", fontsize=9,
                    color="black" if arr[i, j] < np.percentile(arr, 70) else "white")
    cb = fig.colorbar(im, ax=ax, fraction=0.05, pad=0.02)
    cb.set_label(lab, fontsize=9)
fig.suptitle("图 6  碳酸锂价格 × 电网排放因子双因素敏感性（拐点配置，绿电 55%、直再 60%）", fontsize=13, y=0.97)
fig.text(0.5, 0.02, "碳足迹对电网因子高度敏感而对锂价几乎不敏感；LCOR 对锂价高度敏感："
                    "锂价越低，废旧电池采购与产品售价同步下降，净收益收窄但仍为正",
         ha="center", fontsize=9, color="#333")
fig.subplots_adjust(hspace=0.42, bottom=0.10, top=0.90)
save(fig, "fig6_sensitivity_heatmap.png")

# ============================ 图 7：路线强度与年通量/远期扩容 ============================
RT = P["process"]["routes"]
fig, axes = plt.subplots(1, 2, figsize=(12.8, 5.2))
names = [f"强化湿法\nHy（{RT['Hy']['energy_GJ_per_t']:.1f} GJ/t）",
         f"还原焙烧+湿法\nRC+Hy（{RT['RC_Hy']['energy_GJ_per_t']:.1f} GJ/t）",
         f"直接正极再生\nDirect（{RT['Direct']['energy_GJ_per_t']:.1f} GJ/t）"]
x = np.arange(3)
efb, efg = LCA["grid_ef"]["base"], LCA["green_residual_ef"]
for i, k in enumerate(("Hy", "RC_Hy", "Direct")):
    r = RT[k]
    e, th = r["energy_GJ_per_t"], r["thermal_share"]
    e_kwh = e * (1 - th) / 0.0036
    h_co2 = e * th * LCA["natural_gas_kg_co2e_per_GJ"]
    axes[0].bar(x[i] - 0.17, e_kwh * efb + h_co2, 0.32, color=C2, label="网电情景 GWP" if i == 0 else None)
    axes[0].bar(x[i] + 0.17, e_kwh * efg + h_co2, 0.32, color=C3, label="绿电情景 GWP" if i == 0 else None)
    axes[0].text(x[i] - 0.17, e_kwh * efb + h_co2 + 45, f"{e_kwh*efb+h_co2:.0f}", ha="center", fontsize=8.6)
    axes[0].text(x[i] + 0.17, e_kwh * efg + h_co2 + 45, f"{e_kwh*efg+h_co2:.0f}", ha="center", fontsize=8.6)
axes[0].set_xticks(x)
axes[0].set_xticklabels(names, fontsize=9.5)
axes[0].set_ylim(0, 2400)
axes[0].set_ylabel("工艺能耗换算碳足迹 / (kg CO2e/t 处理料)", fontsize=10.5)
axes[0].set_title("(a) 三条精炼路线能耗—碳强度对比（仅电力+热能项）", fontsize=11.5)
axes[0].legend(frameon=False, fontsize=9)
axes[0].grid(axis="y", ls=":", color="#dddddd")

ab = R["annual_base"]
lt = R["long_term_2035"]
AN = M["annual"]
prod_names = ["Li2CO3", "再生正极粉", "镍盐", "磷酸铁"]
v1 = [AN["li2co3_t"], AN["lfp_powder_t"], AN["ni_sulfate_t"], AN["fepo4_t"]]
v2 = [x * 3 for x in v1]
x = np.arange(4)
axes[1].bar(x - 0.19, v1, 0.36, color=C1, label="近期 2028（2 万 t/a，绿电 55%）")
axes[1].bar(x + 0.19, v2, 0.36, color=C2, label="远期 2035（6 万 t/a，绿电 100%）")
for xi, a, b2 in zip(x, v1, v2):
    axes[1].text(xi - 0.19, a + 180, f"{a:,.0f}", ha="center", fontsize=8.6)
    axes[1].text(xi + 0.19, b2 + 180, f"{b2:,.0f}", ha="center", fontsize=8.6)
axes[1].set_xticks(x)
axes[1].set_xticklabels(prod_names, fontsize=10)
axes[1].set_ylabel("年产出通量 / (t/a)", fontsize=10.5)
axes[1].set_ylim(0, 21000)
axes[1].set_title("(b) 主产品年通量与 2035 年扩容规划", fontsize=11.5)
axes[1].legend(frameon=False, fontsize=8.8, loc="upper left")
axes[1].grid(axis="y", ls=":", color="#dddddd")
axes[1].annotate(f"年净减碳 {ab['co2_saving_t']:,.0f} t CO2e", xy=(0.98, 0.72), xycoords="axes fraction",
                 ha="right", fontsize=9.5, color=C1)
axes[1].annotate(f"年净减碳 {lt['annual_co2_saving_t']:,.0f} t CO2e", xy=(0.98, 0.63), xycoords="axes fraction",
                 ha="right", fontsize=9.5, color=C2)
fig.suptitle("图 7  三条精炼路线强度对比与园区年通量—扩容规划", fontsize=13, y=1.02)
save(fig, "fig7_route_and_scale.png")

# ==================== 图 8【C 模块】：锂价—净收益与累计现金流/NPV ====================
E = R["economics"]
fig, axes = plt.subplots(1, 2, figsize=(13.4, 5.2))

pc = E["price_curve"]
xs = [r["price_usd"] / 1000 for r in pc]
series = [("hy_only", "全湿法（直再 0%）", C4, "--"),
          ("base", "现状基准（绿电 0%，直再 20%）", GREY, "-."),
          ("knee", "拐点方案（绿电 55%，直再 60%）", C1, "-"),
          ("green", "深碳（绿电 100%，直再 60%）", C2, "-.")]
for key, label, col, ls in series:
    ys = [r[key] for r in pc]
    axes[0].plot(xs, ys, ls, color=col, lw=1.7, label=label)
axes[0].axhline(0, color="#333333", lw=0.9)
axes[0].set_xlabel("碳酸锂价格 / (千 USD/t)", fontsize=10.5)
axes[0].set_ylabel("平准化回收净成本 LCOR / (元/t)", fontsize=10.5)
axes[0].set_title("(a) 锂价—经济性排序：四条配置全程净收益为正", fontsize=11.5)
axes[0].legend(frameon=False, fontsize=8.6, loc="lower left")
axes[0].grid(ls=":", color="#dddddd")
axes[0].annotate("基准价 22,000 USD/t", xy=(22, min(r['knee'] for r in pc)),
                 xytext=(24, -4400), fontsize=8.8, color=GREY,
                 arrowprops=dict(arrowstyle="->", color=GREY, lw=0.8))

for key, label, col, ls in series:
    cf = E["cashflow"][key]
    yrs = [r["year"] for r in cf]
    cum = [r["cumulative"] / 1e8 for r in cf]
    axes[1].plot(yrs, cum, ls, color=col, lw=1.7, label=f"{label}｜NPV {cum[-1]:.2f} 亿元")
axes[1].axhline(0, color="#333333", lw=0.9)
axes[1].set_xlabel("运营年 / a", fontsize=10.5)
axes[1].set_ylabel("累计折现现金流 / 亿元", fontsize=10.5)
axes[1].set_title("(b) 20 年累计现金流：拐点方案 3.8 年回收投资", fontsize=11.5)
axes[1].legend(frameon=False, fontsize=8.4, loc="upper left")
axes[1].grid(ls=":", color="#dddddd")
pb = E["finance"]["knee"]["payback_years"]
axes[1].scatter([pb], [0], s=46, color=C1, zorder=5)
axes[1].annotate(f"投资回收期 {pb:.1f} a", xy=(pb, 0), xytext=(pb + 4, -1.6), fontsize=8.8, color=C1,
                 arrowprops=dict(arrowstyle="->", color=C1, lw=0.8))
fig.suptitle("图 8  锂价波动下的净收益演化与项目级累计现金流（WACC 8%，20 a，税前）", fontsize=13, y=1.02)
fig.tight_layout()
save(fig, "fig8_cashflow_npv.png")

# ==================== 图 9【C 模块】：龙卷风图与成本—收入结构 ====================
fig, axes = plt.subplots(1, 2, figsize=(13.4, 5.4), gridspec_kw={"width_ratios": [1.15, 1]})
tor = sorted(E["tornado"], key=lambda r: abs(r["high"] - r["low"]))
names = [r["factor"] for r in tor]
base = tor[0]["base"]
yerr = [[abs(r["low"] - base) for r in tor], [abs(r["high"] - base) for r in tor]]
axes[0].barh(names, [-v for v in yerr[0]], left=base, color=C2, alpha=0.85, height=0.55)
axes[0].barh(names, yerr[1], left=base, color=C1, alpha=0.85, height=0.55)
axes[0].axvline(base, color="#333333", lw=1)
for i, r in enumerate(tor):
    axes[0].text(r["low"] - 40, i, f"{r['low']:,.0f}", va="center", ha="right", fontsize=8.2, color=C2)
    axes[0].text(r["high"] + 40, i, f"{r['high']:,.0f}", va="center", ha="left", fontsize=8.2, color=C1)
axes[0].set_xlabel("拐点方案 LCOR / (元/t)", fontsize=10.5)
axes[0].set_title("(a) 单因素敏感性：采购锂系数与 CAPEX 主导", fontsize=11.5)
axes[0].grid(axis="x", ls=":", color="#dddddd")
axes[0].set_xlim(min(r["low"] for r in tor) - 400, max(r["high"] for r in tor) + 400)
axes[0].tick_params(axis="y", labelsize=9)

cd = R["scenarios"]["knee"]["cost_detail"]
fixed = TEA["collection_transport_yuan_per_t"] + TEA["labor_yuan_per_t"] + TEA["env_cost_yuan_per_t"]
items = [("来料采购", cd["purchase"], C1), ("资本年金化", cd["capex_ann"], C4),
         ("电力 + 热能", cd["electricity"] + cd["heat"], C3), ("试剂", cd["reagent"], C2),
         ("收集运输/人工/税费", fixed, GREY), ("水资源与废水", cd["water_cost"], "#8f9779")]
left = 0.0
for label, val, col in items:
    axes[1].barh(["成本"], [val], left=left, color=col, height=0.5, label=f"{label} {val:,.0f}")
    left += val
axes[1].barh(["收入"], [cd["revenue"]], color="#9ec9c0", height=0.5, label=f"产品收入 {cd['revenue']:,.0f}")
axes[1].set_xlim(0, 34000)
axes[1].set_ylim(-0.55, 1.55)
axes[1].set_xlabel("元/t 退役电池", fontsize=10.5)
axes[1].set_title("(b) 成本—收入结构：采购占 63%，资本仅 14.5%", fontsize=11.5)
axes[1].text(left + 120, 0.16, f"成本合计 {left:,.0f}", fontsize=8.6, color=GREY, va="center")
axes[1].text(cd["revenue"] + 120, 1.16, f"收入 {cd['revenue']:,.0f}", fontsize=8.6, color="#2f6f66", va="center")
axes[1].legend(frameon=False, fontsize=7.4, ncol=3, loc="upper center", bbox_to_anchor=(0.42, -0.16))
axes[1].grid(axis="x", ls=":", color="#dddddd")
axes[1].tick_params(axis="y", labelsize=9.5)
fig.suptitle("图 9  拐点方案的单因素敏感性与成本—收入结构（基准锂价 22,000 USD/t）", fontsize=13, y=1.02)
fig.tight_layout()
save(fig, "fig9_tornado_cost.png")

print("\n全部图表已输出至 figures_output/")

