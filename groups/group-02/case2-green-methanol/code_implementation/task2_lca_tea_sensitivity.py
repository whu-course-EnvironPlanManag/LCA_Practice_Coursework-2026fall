# -*- coding: utf-8 -*-
"""
任务 2：LCA「绿电悖论」与 TEA 平准化甲醇成本（LCOM）多情景敏感性分析
案例二 · 绿氢合成绿色甲醇

绘制 电价(0.05~0.60 元/度) -> LCOM / 绿色溢价(Green Premium) / MAC 三者联动折线图，
并在全国碳市场碳价约 100 元/吨背景下，求解绿甲醇实现商业自平衡的最高临界电价阈值。
"""

import csv
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "SimSun"]
plt.rcParams["axes.unicode_minus"] = False

BASE = os.path.join(os.path.dirname(__file__), "..", "case_files", "data_cohort")
LCA_CSV = os.path.join(BASE, "lca_grid_scenarios_lci.csv")
TEA_CSV = os.path.join(BASE, "tea_lcom_sensitivity_data.csv")


def read_lca_gwp():
    """读取净碳足迹与煤制甲醇基准，得到减排量 delta_GHG (t CO2e/t 甲醇)。"""
    with open(LCA_CSV, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row["lci_inventory_item"] == "Net_Life_Cycle_GWP_Total":
                gwp_a = float(row["gwp_scenario_a_kgCO2e"])   # -1044.12 (绿电)
                gwp_b = float(row["gwp_scenario_b_kgCO2e"])   # +4531.26 (网电)
            if row["lci_inventory_item"] == "Fossil_Benchmark_CtM":
                fossil = float(row["gwp_scenario_a_kgCO2e"])  # 2600.00
    delta_ghg = (fossil - gwp_a) / 1000.0                     # t CO2e / t 甲醇
    return gwp_a, gwp_b, fossil, delta_ghg


def read_tea():
    """读取电价-成本敏感度表。"""
    price, lcom, premium, mac = [], [], [], []
    with open(TEA_CSV, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            price.append(float(row["electricity_price_rmb_per_kwh"]))
            lcom.append(float(row["lcom_rmb_per_t"]))
            premium.append(float(row["green_premium_rmb_per_t"]))
            mac.append(float(row["mac_rmb_per_tCO2e"]))
    return np.array(price), np.array(lcom), np.array(premium), np.array(mac)


gwp_a, gwp_b, fossil, delta_ghg = read_lca_gwp()
price, lcom, premium, mac = read_tea()

# 成本结构：LCOM = 电价 * 吨产品电耗 + 非电成本
elec_kwh = 10826.0                       # 吨产品综合电耗 (kWh/t)
non_elec = lcom[0] - elec_kwh * price[0]  # 非电成本 1238.37 元/t
fossil_price = 2500.0                     # 煤制甲醇售价 2500 元/t

print("=" * 78)
print("任务 2 · LCA 绿电悖论与 TEA 平准化成本敏感性分析")
print("=" * 78)
print(f"\n[1] LCA 净碳足迹（kg CO2e/t 甲醇）")
print(f"    情景 A 100% 绿电       = {gwp_a:>10.2f}")
print(f"    情景 B 区域工业电网    = {gwp_b:>10.2f}")
print(f"    煤制甲醇基准           = {fossil:>10.2f}")
print(f"    绿电驱动净减排量 ΔGHG  = {delta_ghg:.4f} t CO2e/t 甲醇")
print(f"    减排率(情景A)          = {(fossil-gwp_a)/fossil:>9.2%}")
print(f"    增排率(情景B)          = {(gwp_b-fossil)/fossil:>9.2%}")

print(f"\n[2] TEA 成本结构识别：LCOM = 电价 x {elec_kwh:.0f} kWh + {non_elec:.2f} 元/t")

# ----------------------------------------------------------------------
# 临界电价阈值（MAC <= 100 元/t CO2e）——精确求解
#   MAC = (LCOM - 2500) / ΔGHG = (elec_kwh*p + non_elec - 2500)/ΔGHG = 100
# ----------------------------------------------------------------------
p_crit = (100.0 * delta_ghg + fossil_price - non_elec) / elec_kwh
lcom_crit = elec_kwh * p_crit + non_elec
premium_crit = lcom_crit - fossil_price
mac_crit = premium_crit / delta_ghg

print("\n[3] 最高临界电价阈值（MAC = 100 元/t CO2e 时）")
print(f"    方程：MAC(p) = ({elec_kwh:.0f}·p + {non_elec:.2f} - {fossil_price:.0f}) / {delta_ghg:.4f} = 100")
print(f"    求解得 p* = {p_crit:.4f} 元/kWh")
print(f"       -> LCOM = {lcom_crit:.2f} 元/t, 绿色溢价 = {premium_crit:.2f} 元/t, MAC = {mac_crit:.2f} 元/t CO2e")
print("    ✓ 即：当电价 <= 约 0.150 元/度时，绿甲醇可依托全国碳市场(约100元/吨)实现商业自平衡。")

# ----------------------------------------------------------------------
# 绘制联动折线图
# ----------------------------------------------------------------------
fig, ax1 = plt.subplots(figsize=(10, 6.5))

# 主轴（左）：LCOM 与 绿色溢价（元/t）
l1, = ax1.plot(price, lcom, "o-", color="#c0392b", linewidth=2.2, label="平准化甲醇成本 LCOM (元/t)")
l2, = ax1.plot(price, premium, "s--", color="#e67e22", linewidth=2.0, label="绿色溢价 Green Premium (元/t)")
ax1.axhline(fossil_price, color="gray", linestyle=":", linewidth=1.5)
ax1.text(0.052, fossil_price + 60, f"煤制甲醇基准 {fossil_price:.0f} 元/t",
         fontsize=9, color="gray")

# 副轴（右）：边际减排成本 MAC（元/t CO2e）
ax2 = ax1.twinx()
l3, = ax2.plot(price, mac, "^-", color="#2980b9", linewidth=2.2, label="边际减排成本 MAC (元/t CO2e)")
ax2.axhline(100.0, color="#16a085", linestyle="--", linewidth=1.6)
ax2.text(0.052, 100 + 8, "全国碳市场碳价约 100 元/t", fontsize=9, color="#16a085")

# 临界电价阈值标注
ax2.axvline(p_crit, color="#8e44ad", linestyle="--", linewidth=1.6)
ax1.annotate(f"临界电价 {p_crit:.3f} 元/度\n(MAC = 100 元/t)",
             xy=(p_crit, premium_crit + fossil_price), xytext=(p_crit + 0.04, 3500),
             fontsize=9.5, color="#8e44ad",
             arrowprops=dict(arrowstyle="->", color="#8e44ad", lw=1.4))

ax1.set_xlabel("工业电价 (元/kWh)", fontsize=12)
ax1.set_ylabel("单位甲醇成本 / 绿色溢价 (元/t)", fontsize=12, color="#c0392b")
ax2.set_ylabel("边际减排成本 MAC (元/t CO2e)", fontsize=12, color="#2980b9")
ax1.set_title("电价对绿色甲醇 LCOM / 绿色溢价 / MAC 的联动响应（0.05~0.60 元/度）",
              fontsize=13.5, pad=14)

ax1.grid(True, linestyle="--", alpha=0.35)
ax1.set_xlim(0.05, 0.60)
lines = [l1, l2, l3]
ax1.legend(lines, [x.get_label() for x in lines], loc="upper left", fontsize=10)

fig.tight_layout()

png = os.path.join(os.path.dirname(__file__), "task2_lcom_mac_sensitivity.png")
svg = os.path.join(os.path.dirname(__file__), "task2_lcom_mac_sensitivity.svg")
fig.savefig(png, dpi=300, bbox_inches="tight")
fig.savefig(svg, bbox_inches="tight")
print(f"\n[4] 已输出：\n    {png}\n    {svg}")

print("\n" + "=" * 78)
print("关键结论：")
print(f"  1. 绿电情景净碳足迹 -1044 kg/t（较煤化工减排 140.2%），而网电情景 +4531 kg/t")
print(f"     （反向增排 74.3%），印证『绿电悖论』——电网不脱碳则 Power-to-X 必然高排放。")
print(f"  2. LCOM / 绿色溢价 / MAC 均随电价线性上升，但 MAC 最陡（决定碳交易能否平抑溢价）。")
print(f"  3. 最高临界电价阈值 = {p_crit:.4f} 元/kWh（约 0.150 元/度），低于此价即可依托"
      f" 100 元/吨碳市场实现商业自平衡。")
print("=" * 78)