# =============================================================
# 案例二 任务 2：LCA 绿电悖论 + TEA LCOM 电价敏感性 + MAC
# 输出: scenario_lca_tea.png 折线图
# 碳价阈值: 当前全国碳价 ≈ 100 元/吨 下的临界电价
# =============================================================
import warnings
from pathlib import Path
warnings.filterwarnings('ignore')
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

DATA_DIR = Path(__file__).resolve().parent.parent / "case_files" / "data_cohort"
OUT_DIR  = Path(__file__).resolve().parent
assert DATA_DIR.exists(), f"❌ {DATA_DIR} 不存在"

# ---- 中文字体 ----
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False
sns.set_theme(style="whitegrid", rc={'figure.dpi': 120})

# ---- 读数据 ----
df_lci  = pd.read_csv(DATA_DIR / "lca_grid_scenarios_lci.csv")
df_tea  = pd.read_csv(DATA_DIR / "tea_lcom_sensitivity_data.csv")

print("=" * 70)
print("案例二 · 绿电悖论 LCA + TEA LCOM 电价敏感性分析")
print("=" * 70)

# ---- 1. LCA 绿电悖论两情景 ----
sc_a_green  = df_lci['gwp_scenario_a_kgCO2e'].sum()
sc_b_grid   = df_lci['gwp_scenario_b_kgCO2e'].sum()
fossil_ctm  = df_lci.loc[df_lci['lci_inventory_item']=='Fossil_Benchmark_CtM', 'gwp_scenario_a_kgCO2e'].values[0]
reduction_a = (fossil_ctm - sc_a_green) / fossil_ctm * 100
reduction_b = (fossil_ctm - sc_b_grid) / fossil_ctm * 100

print()
print("📍 LCA 绿电悖论核心对比")
print("-" * 50)
print(f"  情景 A (100% 绿电) 净碳足迹 = {sc_a_green:.1f} kg CO2e/t  {'净负碳!' if sc_a_green<0 else ''}")
print(f"  情景 B (区域电网)   净碳足迹 = {sc_b_grid:.1f} kg CO2e/t")
print(f"  煤制甲醇基准                = {fossil_ctm:.1f} kg CO2e/t")
print(f"  情景 A 减排率               = {reduction_a:.1f}%")
print(f"  情景 B 较基准              = {reduction_b:+.1f}%  ⚠️ 反向增排!")

# ---- 2. TEA 敏感性折线图 ----
fig, ax1 = plt.subplots(figsize=(12, 6))

ax1.plot(df_tea['electricity_price_rmb_per_kwh'], df_tea['lcom_rmb_per_t'],
         'b-o', linewidth=2, markersize=6, label='LCOM 平准化甲醇成本', zorder=3)
ax1.plot(df_tea['electricity_price_rmb_per_kwh'], df_tea['green_premium_rmb_per_t'],
         'g--s', linewidth=2, markersize=5, label='绿色溢价 Green Premium', alpha=0.8)
ax1.axhline(y=2500, color='gray', linestyle=':', linewidth=1.5, label='煤制甲醇市场基准 2500 元/t')
ax1.set_xlabel('工业电价 (元/kWh)', fontsize=12)
ax1.set_ylabel('LCOM / 绿色溢价 (元/t 甲醇)', fontsize=12, color='b')
ax1.tick_params(axis='y', labelcolor='b')

ax2 = ax1.twinx()
ax2.plot(df_tea['electricity_price_rmb_per_kwh'], df_tea['mac_rmb_per_tCO2e'],
         'r-^', linewidth=2, markersize=6, label='MAC 边际减排成本', zorder=3)
ax2.set_ylabel('MAC 边际减排成本 (元/吨 CO2e)', fontsize=12, color='r')
ax2.tick_params(axis='y', labelcolor='r')
ax2.axhline(y=100, color='r', linestyle=':', linewidth=1.2, alpha=0.6, label='全国碳价 ≈ 100 元/吨')
ax2.fill_between(df_tea['electricity_price_rmb_per_kwh'], 0, 100, color='green', alpha=0.08)

# 组合图例
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=10, framealpha=0.9)

plt.title('图 2.1 LCOM / 绿色溢价 / MAC 对工业电价的联动敏感性', fontsize=14, fontweight='bold')
plt.tight_layout()
out1 = OUT_DIR / "case2_sensitivity_line.png"
plt.savefig(out1, dpi=300, bbox_inches='tight')
plt.close()
print(f"\n✅ 敏感性折线图: {out1}")

# ---- 3. LCOM vs 电价散点 + 碳价阈值 ----
fig2, ax = plt.subplots(figsize=(10, 6))

df_tea['可行? (碳价=100)'] = df_tea['green_premium_rmb_per_t'] < 100 * 3.644

colors = {'✅ 可行': '#2ecc71', '❌ 倒挂': '#e74c3c'}
df_tea['可行标签'] = df_tea['可行? (碳价=100)'].map({True: '✅ 可行', False: '❌ 倒挂'})

ax.scatter(df_tea['electricity_price_rmb_per_kwh'], df_tea['lcom_rmb_per_t'],
           c=df_tea['可行? (碳价=100)'].map({True: '#2ecc71', False: '#e74c3c'}),
           s=100, alpha=0.85, edgecolors='white', linewidth=1.5, zorder=3)
ax.plot(df_tea['electricity_price_rmb_per_kwh'], df_tea['lcom_rmb_per_t'],
        'gray', linestyle='--', alpha=0.5, label='LCOM 趋势')
ax.axhline(y=2500, color='gray', linestyle=':', alpha=0.6, label='化石基准 2500 元/t')

# 找到最高临界电价
critical_row = df_tea[df_tea['green_premium_rmb_per_t'] < 100 * 3.644].tail(1)
if len(critical_row) > 0:
    critical_price = critical_row['electricity_price_rmb_per_kwh'].values[0]
    ax.axvline(x=critical_price, color='green', linestyle='-', linewidth=1.5, alpha=0.7)
    ax.annotate(f'碳价 100 元/t 下\n最高临界电价 ≈ {critical_price:.2f} 元/kWh',
                xy=(critical_price, critical_row['lcom_rmb_per_t'].values[0]),
                xytext=(critical_price + 0.02, critical_row['lcom_rmb_per_t'].values[0] - 300),
                arrowprops=dict(arrowstyle='->', color='green'),
                fontsize=10, color='green', fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.4', fc='white', ec='green', alpha=0.9))

ax.set_xlabel('工业电价 (元/kWh)', fontsize=12)
ax.set_ylabel('LCOM (元/t)', fontsize=12)
ax.set_title('图 2.2 绿色甲醇商业自平衡区域 (全国碳价 100 元/t)', fontsize=14, fontweight='bold')
ax.legend(fontsize=10)
ax.grid(True, linestyle='--', alpha=0.5)
plt.tight_layout()
out2 = OUT_DIR / "case2_business_feasibility.png"
plt.savefig(out2, dpi=300, bbox_inches='tight')
plt.close()
print(f"✅ 商业可行散点图: {out2}")

# ---- 4. 随堂研讨: 绿电占比临界值 ----
print()
print("📍 随堂研讨: 绿电占比 x 临界值计算")
print("-" * 50)
print("  燃煤自备电 EF=0.75 kg CO2e/kWh,  屋顶光伏 EF=0.04 kg CO2e/kWh")
print("  总电耗 = 10826 kWh/t,  CO2 固定信用 = -1423 kg,  煤制基准 = 2600 kg")
print()
print("  联立方程: GWP(x) = 10826 × EF(x) - 1423 ≤ 2600")
print("  其中 EF(x) = 0.04x + 0.75(1-x) = 0.75 - 0.71x")
print()
print("  => 10826×(0.75-0.71x) ≤ 4023")
print("  => 8119.5 - 7686.5x  ≤ 4023")
print("  => 7686.5x ≥ 4096.5")

x_critical = (10826 * 0.75 - 4023) / (10826 * 0.71)
print(f"  => x ≥ {x_critical:.3f} = {x_critical*100:.1f}%")
print()
print(f"  🎯 绿电替代率必须 ≥ {x_critical*100:.1f}% 才能不发生反向增排")
print(f"  (讲义提示范围 50%-55% 内 ✅)")

print()
print("=" * 70)
print("🎉 任务 2 完成：绿电悖论推演 + 敏感性折线图 + 碳价阈值")
print("=" * 70)
