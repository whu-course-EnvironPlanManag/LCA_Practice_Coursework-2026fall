"""
案例二 任务2：LCA 绿电悖论与 TEA 平准化甲醇成本（LCOM）多情景敏感性分析
============================================================
绘制电价从 0.05~0.60 元/度变化时，LCOM、绿色溢价、边际减排成本的联动响应折线图，
并输出碳市场背景下绿色甲醇商业自平衡的最高临界电价阈值。
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False

# ============================================================
# 1. 读取数据
# ============================================================
base_dir = r"../case_files/data_cohort"

tea_df = pd.read_csv(f"{base_dir}/tea_lcom_sensitivity_data.csv")
lca_df = pd.read_csv(f"{base_dir}/lca_grid_scenarios_lci.csv")

print("=" * 70)
print("案例二 任务2：LCA 绿电悖论与 TEA LCOM 敏感性分析")
print("=" * 70)

# ============================================================
# 2. 关键参数
# ============================================================
TOTAL_ELECTRICITY = 10826.0  # kWh/t 总综合电耗
FOSSIL_PRICE = 2500.0        # 元/t 煤制甲醇基准价
FOSSIL_GWP = 2600.0          # kg CO2e/t 煤制甲醇碳足迹
CARBON_PRICE = 100.0         # 元/t CO2e 全国碳市场碳价

# CO2捕集固定信用 + O2替代信用
CO2_CAPTURE_CREDIT = -1423.0  # kg CO2e/t
O2_CREDIT = -95.0             # kg CO2e/t
INFRA_EMISSION = 95.0         # kg CO2e/t (基础设施+逸散)
NON_EMISSION = CO2_CAPTURE_CREDIT + O2_CREDIT + INFRA_EMISSION  # 非电力排放净值

print(f"\n关键参数:")
print(f"  总综合电耗:       {TOTAL_ELECTRICITY} kWh/t")
print(f"  煤制甲醇基准价:   {FOSSIL_PRICE} 元/t")
print(f"  煤制甲醇碳足迹:   {FOSSIL_GWP} kg CO2e/t")
print(f"  碳市场碳价:       {CARBON_PRICE} 元/t CO2e")
print(f"  非电力净排放:     {NON_EMISSION} kg CO2e/t")

# ============================================================
# 3. 电价敏感性计算
# ============================================================
electricity_prices = tea_df['electricity_price_rmb_per_kwh'].values
lcom_values = tea_df['lcom_rmb_per_t'].values
green_premium = tea_df['green_premium_rmb_per_t'].values
mac_values = tea_df['mac_rmb_per_tCO2e'].values

# 计算各电价下的净碳足迹 (情景A绿电: EF=0.035)
EF_GREEN = 0.035  # kg CO2e/kWh 绿电
GWP_GREEN = TOTAL_ELECTRICITY * EF_GREEN + NON_EMISSION  # 绿电情景净碳足迹

# 各电价下的净碳足迹 (加权)
# 假设不同电价对应不同电网碳因子
# 简化: 电价越低→绿电占比越高→碳因子越低
# 从数据反推: 0.15元→绿电(0.035), 0.35元→混合, 0.55元→网电(0.55)
gwp_values = []
for price in electricity_prices:
    # 线性插值碳因子: 电价0.05→EF=0.035, 电价0.55→EF=0.55
    if price <= 0.15:
        ef = 0.035
    elif price >= 0.55:
        ef = 0.55
    else:
        ef = 0.035 + (price - 0.15) / (0.55 - 0.15) * (0.55 - 0.035)
    gwp = TOTAL_ELECTRICITY * ef + NON_EMISSION
    gwp_values.append(gwp)

gwp_values = np.array(gwp_values)

# ============================================================
# 4. 计算临界电价 (MAC = 碳价时)
# ============================================================
# MAC = (LCOM - FOSSIL_PRICE) / (FOSSIL_GWP - GWP_GREEN)
# 当 MAC = CARBON_PRICE 时:
# LCOM = FOSSIL_PRICE + CARBON_PRICE * (FOSSIL_GWP - GWP_GREEN)
# electricity_cost = LCOM - non_electricity_cost
# electricity_price = electricity_cost / TOTAL_ELECTRICITY

delta_ghg = FOSSIL_GWP - GWP_GREEN  # 减排量 = 2600 - (-1044.1) = 3644.1 kg CO2e/t
non_elec_cost = 1238.37  # 非电力成本 (从CSV)

# 临界电价: MAC = CARBON_PRICE
# LCOM_critical = FOSSIL_PRICE + CARBON_PRICE * delta_ghg / 1000
lcom_critical = FOSSIL_PRICE + CARBON_PRICE * delta_ghg / 1000
elec_cost_critical = lcom_critical - non_elec_cost
price_critical = elec_cost_critical / TOTAL_ELECTRICITY

print(f"\n临界电价计算 (碳价 = {CARBON_PRICE} 元/t CO2e):")
print(f"  绿电情景净碳足迹: {GWP_GREEN:.1f} kg CO2e/t")
print(f"  相对煤化工减排量: {delta_ghg:.1f} kg CO2e/t = {delta_ghg/1000:.3f} t CO2e/t")
print(f"  临界 LCOM:        {lcom_critical:.1f} 元/t")
print(f"  临界电力成本:     {elec_cost_critical:.1f} 元/t")
print(f"  临界电价阈值:     {price_critical:.4f} 元/kWh")

# ============================================================
# 5. 绘图: 三轴联动响应曲线
# ============================================================
fig, ax1 = plt.subplots(figsize=(14, 8))

# 颜色方案
color_lcom = '#2196F3'
color_premium = '#FF9800'
color_mac = '#E91E63'
color_critical = '#4CAF50'

# 左轴: LCOM 和 绿色溢价
ax1.set_xlabel('电价 (元/kWh)', fontsize=14, fontweight='bold')
ax1.set_ylabel('LCOM / 绿色溢价 (元/t)', fontsize=14, color=color_lcom)
line_lcom = ax1.plot(electricity_prices, lcom_values, 'o-', color=color_lcom,
                     linewidth=2.5, markersize=6, label='平准化甲醇成本 LCOM')
line_premium = ax1.plot(electricity_prices, green_premium, 's--', color=color_premium,
                        linewidth=2, markersize=5, label='绿色溢价 Green Premium')

# 化石甲醇基准线
ax1.axhline(y=FOSSIL_PRICE, color='gray', linestyle=':', linewidth=1.5,
            label=f'煤制甲醇基准价 ({FOSSIL_PRICE} 元/t)')

ax1.tick_params(axis='y', labelcolor=color_lcom)
ax1.set_ylim(0, 8500)

# 右轴: MAC
ax2 = ax1.twinx()
ax2.set_ylabel('边际减排成本 MAC (元/t CO₂e)', fontsize=14, color=color_mac)
line_mac = ax2.plot(electricity_prices, mac_values, '^-', color=color_mac,
                    linewidth=2.5, markersize=6, label='边际减排成本 MAC')

# 碳价基准线
ax2.axhline(y=CARBON_PRICE, color=color_critical, linestyle='--', linewidth=2,
            label=f'全国碳市场碳价 ({CARBON_PRICE} 元/t)')

ax2.tick_params(axis='y', labelcolor=color_mac)
ax2.set_ylim(-300, 1600)

# 临界电价竖线
ax1.axvline(x=price_critical, color=color_critical, linestyle='-.', linewidth=2,
            alpha=0.7, label=f'临界电价 {price_critical:.3f} 元/kWh')

# 标注临界点
ax1.annotate(f'临界电价\n{price_critical:.3f} 元/kWh',
             xy=(price_critical, lcom_critical),
             xytext=(price_critical + 0.05, lcom_critical + 500),
             fontsize=11, fontweight='bold', color=color_critical,
             arrowprops=dict(arrowstyle='->', color=color_critical, lw=1.5),
             bbox=dict(boxstyle='round,pad=0.3', facecolor='lightyellow', edgecolor=color_critical))

# 合并图例
lines = line_lcom + line_premium + line_mac
labels = [l.get_label() for l in lines]
# 添加ax1和ax2中的额外线条
handles_ax1 = ax1.get_legend_handles_labels()[0]
labels_ax1 = ax1.get_legend_handles_labels()[1]
handles_ax2 = ax2.get_legend_handles_labels()[0]
labels_ax2 = ax2.get_legend_handles_labels()[1]
all_handles = handles_ax1 + handles_ax2
all_labels = labels_ax1 + labels_ax2
ax1.legend(all_handles, all_labels, loc='upper left', fontsize=10, framealpha=0.9)

ax1.set_title('绿色甲醇 LCOM·绿色溢价·边际减排成本 对电价的联动响应曲线',
              fontsize=16, fontweight='bold', pad=20)
ax1.grid(True, alpha=0.3, linestyle='--')

# 添加分区标注
ax1.axvspan(0.05, 0.15, alpha=0.08, color='green')
ax1.axvspan(0.15, 0.35, alpha=0.08, color='yellow')
ax1.axvspan(0.35, 0.60, alpha=0.08, color='red')

ax1.text(0.10, 8000, '理想区\n(弃风弃光)', ha='center', fontsize=10,
         color='green', fontweight='bold')
ax1.text(0.25, 8000, '大基地区\n(需碳交易支持)', ha='center', fontsize=10,
         color='#F57F17', fontweight='bold')
ax1.text(0.475, 8000, '禁区\n(经济+环境双输)', ha='center', fontsize=10,
         color='red', fontweight='bold')

plt.tight_layout()
output_path = r"lca_tea_sensitivity_chart.png"
plt.savefig(output_path, dpi=300, bbox_inches='tight')
print(f"\n图表已保存: {output_path}")
plt.show()

# ============================================================
# 6. 双情景对比: LCA 绿电悖论
# ============================================================
print(f"\n{'=' * 70}")
print("LCA 绿电悖论对比")
print(f"{'=' * 70}")

# 情景A: 100%绿电
GWP_A = -1044.1
# 情景B: 区域电网
GWP_B = 4531.3

print(f"情景A (100%绿电):  GWP = {GWP_A:.1f} kg CO2e/t (净负碳!)")
print(f"情景B (区域电网):  GWP = {GWP_B:.1f} kg CO2e/t (反向增排!)")
print(f"煤制甲醇基准:      GWP = {FOSSIL_GWP:.1f} kg CO2e/t")
print(f"")
print(f"情景A vs 煤化工:   减排 {(FOSSIL_GWP - GWP_A)/FOSSIL_GWP*100:.1f}%")
print(f"情景B vs 煤化工:   增排 {(GWP_B - FOSSIL_GWP)/FOSSIL_GWP*100:.1f}%")
print(f"")
print(f"结论: 在区域工业电网下, 绿氢制甲醇的碳排放比传统煤化工高出 74.3%!")
print(f"原因: 火电发电效率~40% × 电解效率~64% × 合成效率 → 三次热力学折损")
print(f"铁律: 严禁在未实现电力深度脱碳的地区规划电氢化工项目!")

# ============================================================
# 7. 输出汇总表格
# ============================================================
print(f"\n{'=' * 70}")
print("电价敏感性数据汇总")
print(f"{'=' * 70}")
print(f"{'电价(元/kWh)':>14} {'LCOM(元/t)':>12} {'绿色溢价(元/t)':>16} {'MAC(元/tCO2e)':>16} {'可行性':>10}")
print("-" * 70)
for i, price in enumerate(electricity_prices):
    feasibility = ""
    if price <= 0.10:
        feasibility = "极具竞争力"
    elif price <= 0.15:
        feasibility = "大基地可行"
    elif price <= 0.25:
        feasibility = "需政策支持"
    elif price <= 0.35:
        feasibility = "严重倒挂"
    else:
        feasibility = "规划禁区"
    print(f"{price:>14.2f} {lcom_values[i]:>12.1f} {green_premium[i]:>16.1f} {mac_values[i]:>16.1f} {feasibility:>10}")

print(f"\n临界电价 (碳价={CARBON_PRICE}元/t时): {price_critical:.4f} 元/kWh")
