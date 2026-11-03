"""
========================================================================
Case2 任务 2: LCA 绿电悖论 & TEA 电价敏感性分析
========================================================================
- 绘制电价 (0.05~0.60 元/kWh) → LCOM / 绿色溢价 / MAC 联动折线图
- 输出全国碳价 100 元/吨下的商业自平衡临界电价阈值
- 对比 100% 绿电 vs 区域电网情景的 GWP 差距（绿电悖论可视化）
========================================================================
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# ===================== 全局样式 =====================
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'STSong']
plt.rcParams['axes.unicode_minus'] = False
sns.set_style("whitegrid")

OUTPUT_DIR = Path(__file__).parent
DATA_DIR   = Path(__file__).parent.parent / "case_files" / "data_cohort"

# ===================== 读取数据 =====================
df_tea = pd.read_csv(DATA_DIR / "tea_lcom_sensitivity_data.csv")
df_lca = pd.read_csv(DATA_DIR / "lca_grid_scenarios_lci.csv")

print("=" * 70)
print("【Case2 任务 2】LCA-TEA 敏感性分析")
print("=" * 70)
print(f"\nTEA 数据行数: {len(df_tea)}  |  电价范围: {df_tea['electricity_price_rmb_per_kwh'].min()} ~ {df_tea['electricity_price_rmb_per_kwh'].max()}")

# ============================================================
# 图 1: 电价 → LCOM / 绿色溢价 / MAC 联动响应三线图
# ============================================================

fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 12), sharex=True)
fig.suptitle('绿色甲醇 TEA 敏感性分析: 电价 → LCOM / 绿色溢价 / MAC 联动响应', 
             fontsize=14, fontweight='bold', y=0.98)

prices = df_tea['electricity_price_rmb_per_kwh']

# --- 子图 1: LCOM ---
ax1.plot(prices, df_tea['lcom_rmb_per_t'], 'o-', color='#2196F3', linewidth=2.5, markersize=6, label='LCOM')
ax1.axhline(y=2500, color='gray', linestyle='--', alpha=0.7, label='煤制甲醇基准价 2500 元/t')
ax1.fill_between(prices, 2500, df_tea['lcom_rmb_per_t'], 
                 where=(df_tea['lcom_rmb_per_t'] > 2500), alpha=0.15, color='red', label='绿色溢价区')
ax1.fill_between(prices, 2500, df_tea['lcom_rmb_per_t'], 
                 where=(df_tea['lcom_rmb_per_t'] <= 2500), alpha=0.15, color='green', label='低于基准区')
ax1.set_ylabel('LCOM (元/t)', fontsize=11)
ax1.legend(loc='upper left', fontsize=9)
ax1.set_title('① 平准化甲醇成本 LCOM vs 电价', fontsize=12)

# --- 子图 2: 绿色溢价 ---
ax2.plot(prices, df_tea['green_premium_rmb_per_t'], 's-', color='#FF5722', linewidth=2.5, markersize=6)
ax2.axhline(y=0, color='gray', linestyle='-', alpha=0.5)
ax2.fill_between(prices, 0, df_tea['green_premium_rmb_per_t'], 
                 where=(df_tea['green_premium_rmb_per_t'] >= 0), alpha=0.2, color='#FF5722')
ax2.fill_between(prices, 0, df_tea['green_premium_rmb_per_t'], 
                 where=(df_tea['green_premium_rmb_per_t'] < 0), alpha=0.2, color='#4CAF50')
ax2.set_ylabel('绿色溢价 (元/t)', fontsize=11)
ax2.set_title('② 绿色溢价 vs 电价 (正值=成本倒挂, 负值=低于基准)', fontsize=12)

# --- 子图 3: MAC ---
ax3.plot(prices, df_tea['mac_rmb_per_tCO2e'], 'D-', color='#9C27B0', linewidth=2.5, markersize=6)
ax3.axhline(y=100, color='#E91E63', linestyle='--', alpha=0.8, label='全国碳市场参考价 ≈ 100 元/t CO₂e')
# 找出 MAC ≈ 100 对应的电价
cross_idx = np.argmin(np.abs(df_tea['mac_rmb_per_tCO2e'] - 100))
cross_price = df_tea.iloc[cross_idx]['electricity_price_rmb_per_kwh']
cross_mac   = df_tea.iloc[cross_idx]['mac_rmb_per_tCO2e']
ax3.axvline(x=cross_price, color='#E91E63', linestyle=':', alpha=0.6)
ax3.scatter([cross_price], [cross_mac], color='#E91E63', s=100, zorder=5)
ax3.annotate(f'临界电价 ≈ {cross_price:.2f} 元/kWh\n(MAC ≈ {cross_mac:.1f} 元/t CO₂e)',
             xy=(cross_price, cross_mac), xytext=(cross_price+0.03, cross_mac+150),
             arrowprops=dict(arrowstyle='->', color='#E91E63'), fontsize=10, color='#E91E63')
ax3.set_xlabel('工业电价 (元/kWh)', fontsize=12)
ax3.set_ylabel('MAC (元/t CO₂e)', fontsize=11)
ax3.legend(loc='upper left', fontsize=9)
ax3.set_title('③ 边际减排成本 MAC vs 电价 (碳价 100 元为自平衡阈值)', fontsize=12)

plt.tight_layout(rect=[0, 0, 1, 0.96])
fig1_path = OUTPUT_DIR / "tea_lcom_mac_sensitivity.png"
plt.savefig(fig1_path, dpi=300, bbox_inches='tight')
print(f"\n✅ 图 1 已保存: {fig1_path}")
plt.close()

# ============================================================
# 图 2: 绿电悖论可视化 —— 情景 A vs B 的 GWP 对比
# ============================================================

fig, axes = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle('【绿电悖论】100% 绿电 vs 区域网电 —— 全生命周期碳足迹对比', 
             fontsize=14, fontweight='bold')

# --- 子图 1: 堆叠柱状图 ---
categories = ['CO₂捕集信用\n(-1423)', '生产用电', '基建/逸散', '副产O₂信用', '净GWP合计']
gwp_A = [-1423, 378.9, 95.0, -95.0, -1044.1]
gwp_B = [-1423, 5954.3, 95.0, -95.0, 4531.3]

x = np.arange(len(categories))
width = 0.35
bars1 = axes[0].bar(x - width/2, gwp_A, width, label='情景 A: 100% 绿电\n(EF=0.035)', color='#4CAF50', alpha=0.8)
bars2 = axes[0].bar(x + width/2, gwp_B, width, label='情景 B: 区域网电\n(EF=0.550)', color='#F44336', alpha=0.8)
axes[0].axhline(y=0, color='black', linewidth=0.5)
axes[0].axhline(y=2600, color='gray', linestyle='--', alpha=0.6, label='煤制甲醇基准 2600')
axes[0].set_xticks(x)
axes[0].set_xticklabels(categories, fontsize=9)
axes[0].set_ylabel('GWP (kg CO₂e / t 甲醇)', fontsize=11)
axes[0].set_title('① 全生命周期分项排放对比', fontsize=12)
axes[0].legend(fontsize=9)

# --- 子图 2: 减排率对比 ---
reductions = [-140.2, 74.3]  # % vs 煤基基准
colors = ['#4CAF50', '#F44336']
bars = axes[1].bar(['情景 A: 100%绿电', '情景 B: 区域网电'], reductions, color=colors, width=0.5)
axes[1].axhline(y=0, color='black', linewidth=0.5)
axes[1].set_ylabel('相对煤制甲醇减排率 (%)', fontsize=11)
axes[1].set_title('② 绿电悖论: 网电情景比煤基更糟!', fontsize=12)
axes[1].annotate('净负碳 -1044 kg CO₂e\n减排 140.2%', xy=(0, -140.2), xytext=(-0.25, -110),
                 arrowprops=dict(arrowstyle='->', color='#4CAF50'), fontsize=11, fontweight='bold', color='#2E7D32')
axes[1].annotate('反向增排 +4531 kg CO₂e\n比煤基高 74.3%!', xy=(1, 74.3), xytext=(0.55, 95),
                 arrowprops=dict(arrowstyle='->', color='#F44336'), fontsize=11, fontweight='bold', color='#C62828')

plt.tight_layout(rect=[0, 0, 1, 0.95])
fig2_path = OUTPUT_DIR / "lca_green_power_paradox.png"
plt.savefig(fig2_path, dpi=300, bbox_inches='tight')
print(f"✅ 图 2 已保存: {fig2_path}")
plt.close()

# ============================================================
# 关键结论输出
# ============================================================

print(f"\n{'='*70}")
print("🎯 任务 2 关键结论")
print("=" * 70)

# 临界电价更精确地搜索
# MAC 公式: MAC = (LCOM - 2500) / ΔGHG, 其中 ΔGHG = 2600 - (-1044.12) = 3644.12 kg CO₂e/t
# 令 MAC = 100 → LCOM = 2500 + 100 * 3644.12/1000 = 2500 + 364.4 = 2864.4 元/t
# 而 LCOM = electricity_price * 10826 + 1238.37
# → price = (2864.4 - 1238.37) / 10826 ≈ 0.1502 元/kWh

total_power = 10826.0  # kWh/t
non_power_cost = 1238.37  # 元/t
ΔGHG = 3644.12  # kg CO₂e/t (100%绿电相对煤基的净减排量)

critical_lcom = 2500 + 100 * ΔGHG / 1000  # MAC=100 时的 LCOM
critical_price = (critical_lcom - non_power_cost) / total_power

print(f"\n📊 全国碳价 100 元/吨 CO₂e 下:")
print(f"   净减排潜力 ΔGHG (100%绿电) = {ΔGHG:.1f} kg CO₂e / t 甲醇")
print(f"   碳信用额可抵消溢价 = {100 * ΔGHG/1000:.1f} 元/t")
print(f"   临界 LCOM        ≈ {critical_lcom:.1f} 元/t")
print(f"   👉 临界电价阈值   ≈ {critical_price:.3f} 元/kWh")
print(f"   (即电价 ≤ {critical_price:.2f} 元/度时，绿色甲醇可通过碳市场实现商业自平衡)")

# 各电价情景
print(f"\n📈 关键电价情景快览:")
for price in [0.05, 0.15, 0.20, 0.35, 0.55]:
    row = df_tea[df_tea['electricity_price_rmb_per_kwh'] == price].iloc[0]
    print(f"   电价 {price:.2f} 元/度 → LCOM={row['lcom_rmb_per_t']:>8.1f} 元/t, "
          f"绿色溢价={row['green_premium_rmb_per_t']:>+8.1f}, MAC={row['mac_rmb_per_tCO2e']:>7.1f} 元/t CO₂e")

print(f"\n{'='*70}")