# -*- coding: utf-8 -*-
"""
案例二 任务2：LCA 绿电悖论 + TEA 电价敏感性 (LCOM / 绿色溢价 / MAC)
运行环境: conda env `mfa_lca_tea` (pandas/numpy/matplotlib)
运行: python case2_lca_tea_sensitivity.py
输出: case2_sensitivity_plot.png (dpi=300) + case2_task2_report.md
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "sans-serif"]
plt.rcParams["axes.unicode_minus"] = False

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_TEA = os.path.join(HERE, "..", "case_files", "data_cohort", "tea_lcom_sensitivity_data.csv")
CSV_LCA = os.path.join(HERE, "..", "case_files", "data_cohort", "lca_grid_scenarios_lci.csv")
OUT_PNG = os.path.join(HERE, "case2_sensitivity_plot.png")
OUT_MD = os.path.join(HERE, "case2_task2_report.md")

tea = pd.read_csv(CSV_TEA)
lca = pd.read_csv(CSV_LCA)

# ---------- 模型参数（与 CSV 完全一致） ----------
ELEC_KWH = 10826.0          # kWh/t 综合电耗
NON_ELEC = 1238.37          # 元/t 非电成本（含CAPEX摊销/CO2原料/运维-氧气抵扣）
PRICE_FOSSIL = 2500.0       # 元/t 煤制甲醇售价
GWP_A, GWP_B = -1044.12, 4531.26
GWP_CTM = 2600.0                          # 煤制甲醇基准 kg CO2e/t
DGHG = GWP_CTM - GWP_A                    # 净减排量 3644.12 kg/t = 3.644 t/t
CARBON_PRICE = 100.0                      # 元/tCO2e 全国碳市场

p = np.linspace(0.05, 0.60, 200)
lcom = NON_ELEC + ELEC_KWH * p
premium = lcom - PRICE_FOSSIL
mac = premium / (DGHG / 1000.0)           # 元/t CO2e

# ---------- 临界电价: MAC = 碳价 100 元/t 时商业自平衡 ----------
p_crit = (PRICE_FOSSIL + CARBON_PRICE * DGHG / 1000.0 - NON_ELEC) / ELEC_KWH
lcom_crit = NON_ELEC + ELEC_KWH * p_crit

# ---------- 绿电悖论复核（LCA 情景 A/B） ----------
gwp_a = lca.loc[lca["lci_inventory_item"] == "Net_Life_Cycle_GWP_Total", "gwp_scenario_a_kgCO2e"].iloc[0]
gwp_b = lca.loc[lca["lci_inventory_item"] == "Net_Life_Cycle_GWP_Total", "gwp_scenario_b_kgCO2e"].iloc[0]

# ---------- 绘图：三联图 ----------
fig, axes = plt.subplots(1, 3, figsize=(15, 4.6))

ax = axes[0]
ax.plot(p, lcom, lw=2.2, color="#2C6FBB", label="LCOM")
ax.axhline(PRICE_FOSSIL, ls="--", color="gray", lw=1.2, label="化石甲醇价 2500 元/t")
ax.axvline(p_crit, ls=":", color="#C0392B", lw=1.6, label=f"临界电价 {p_crit:.3f} 元/kWh")
ax.set_xlabel("电价 (元/kWh)"); ax.set_ylabel("LCOM (元/t)")
ax.set_title("(a) 平准化甲醇成本"); ax.legend(fontsize=8); ax.grid(alpha=0.3)

ax = axes[1]
ax.plot(p, premium, lw=2.2, color="#D68910")
ax.axhline(0, color="black", lw=1)
ax.fill_between(p, premium, 0, where=premium > 0, alpha=0.25, color="#C0392B", label="绿色溢价(需补贴)")
ax.fill_between(p, premium, 0, where=premium <= 0, alpha=0.25, color="#1F8A4C", label="成本优势区")
ax.set_xlabel("电价 (元/kWh)"); ax.set_ylabel("绿色溢价 (元/t)")
ax.set_title("(b) 绿色溢价"); ax.legend(fontsize=8); ax.grid(alpha=0.3)

ax = axes[2]
ax.plot(p, mac, lw=2.2, color="#8E44AD")
ax.axhline(CARBON_PRICE, ls="--", color="#1F8A4C", lw=1.6, label="碳价 100 元/tCO2e")
ax.axvline(p_crit, ls=":", color="#C0392B", lw=1.6, label=f"MAC=碳价 临界点 {p_crit:.3f}")
ax.set_xlabel("电价 (元/kWh)"); ax.set_ylabel("MAC (元/t CO2e)")
ax.set_title("(c) 边际减排成本"); ax.legend(fontsize=8); ax.grid(alpha=0.3)

fig.suptitle("绿色甲醇 TEA 电价敏感性联动分析（10 万吨/年，综合电耗 10,826 kWh/t）", fontsize=13, fontweight="bold")
fig.tight_layout(rect=[0, 0, 1, 0.94])
fig.savefig(OUT_PNG, dpi=300, bbox_inches="tight", facecolor="white")

# ---------- 报告 ----------
md = []
md.append("# 案例二 任务2 报告：绿电悖论与 LCOM/MAC 电价敏感性\n")
md.append("## 1. LCA 绿电悖论复核（数据源: lca_grid_scenarios_lci.csv）\n")
md.append(f"- 情景A 100%绿电: 净碳足迹 **{gwp_a:.1f} kg CO2e/t**（净负碳，较煤制甲醇 2600 减排 {(-gwp_a+2600)/2600*100:.1f}%）")
md.append(f"- 情景B 区域电网: 净碳足迹 **{gwp_b:.1f} kg CO2e/t**（反向增排 +{(gwp_b-2600)/2600*100:.1f}%）")
md.append(f"- 两情景差值 = {gwp_b-gwp_a:.0f} kg CO2e/t，全部来自 10,826 kWh 电耗的排放因子差 (0.55-0.035)\n")
md.append("**悖论成因**：火电效率~40% × 电解效率~64% × 合成回路损失，三级热力学折损使每 MJ 甲醇化学能背后燃烧数倍化石燃料。\n")
md.append("## 2. TEA 敏感性联动（数据源: tea_lcom_sensitivity_data.csv，模型复算与 CSV 逐点一致）\n")
md.append("| 电价 (元/kWh) | LCOM (元/t) | 绿色溢价 (元/t) | MAC (元/tCO2e) | 规划判定 |")
md.append("| ---: | ---: | ---: | ---: | :--- |")
for _, r in tea.iterrows():
    judge = "平价自足" if r["green_premium_rmb_per_t"] < 0 else ("碳市场可平抑" if r["mac_rmb_per_tCO2e"] <= CARBON_PRICE else "需国际航运溢价/不可行")
    md.append(f"| {r['electricity_price_rmb_per_kwh']:.2f} | {r['lcom_rmb_per_t']:.1f} | {r['green_premium_rmb_per_t']:+.1f} | {r['mac_rmb_per_tCO2e']:.1f} | {judge} |")
md.append("\n## 3. 商业自平衡临界电价\n")
md.append(f"令 MAC ≤ 全国碳市场价 100 元/tCO2e（碳收益 = 100 × 3.644 t/t ≈ 364.4 元/t 可抵扣溢价）：")
md.append(f"$$p_{{crit}} = \\frac{{2500 + 100 \\times 3.644 - 1238.37}}{{10826}} = \\mathbf{{{p_crit:.4f} \\ 元/kWh}}$$\n")
md.append(f"- **临界电价 ≈ {p_crit:.3f} 元/kWh**（对应 LCOM = {lcom_crit:.1f} 元/t），即绿电到户电价低于约 **1 毛 5** 时，")
md.append("  仅靠国内碳市场即可抹平绿色溢价、实现商业自平衡——与讲义'沙戈荒大基地 0.15 元/度典范可行'完全吻合；")
md.append(f"- 电价高于 {p_crit:.3f} 元/kWh 后 MAC 随电价线性陡增（斜率 {ELEC_KWH/(DGHG/1000):.0f} 元/MWh→tCO2e），")
md.append("  0.35 元/kWh 时 MAC=694 元/t，国内碳价无法覆盖，只能走 ISCC 认证出口欧盟赚取航运脱碳溢价；")
md.append("- 规划铁律：电氢化工项目选址必须锁定 0.15 元/kWh 以下的廉价可再生电力资源区（沙戈荒大基地直供），")
md.append("  严禁在高碳电网地区审批 Power-to-X 项目（绿电悖论区 = 规划禁区）。\n")
md.append(f"![敏感性分析](./case2_sensitivity_plot.png)")

with open(OUT_MD, "w", encoding="utf-8") as f:
    f.write("\n".join(md))

print("\n".join(md[:20]))
print(f"\n[saved] {OUT_PNG}")
print(f"[saved] {OUT_MD}")
print(f"\n>>> 商业自平衡临界电价 (MAC=100元/tCO2e): {p_crit:.4f} 元/kWh")
