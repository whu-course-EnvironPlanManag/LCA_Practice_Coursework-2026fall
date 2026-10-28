# -*- coding: utf-8 -*-
"""
任务1：MFA-LCA-TEA 跨维联动与绿电溢价核算
案例：废弃PET塑料瓶机械物理再生系统

作者: Group-04
日期: 2026-10-22
"""

import pandas as pd
import numpy as np

# ============================================================
# 一、基础参数设定（Baseline Scenario）
# ============================================================

# MFA 基础参数
INPUT_MASS = 1000.0  # kg 废瓶砖输入
PRODUCT_YIELD = 0.80  # 主产品收率 80%
PRODUCT_MASS = INPUT_MASS * PRODUCT_YIELD  # 800 kg rPET颗粒

# LCA 基础参数（原情景）
ELECTRICITY_CONSUMPTION = 850.0  # kWh/t rPET
GRID_ELECTRICITY_PRICE = 0.65  # 元/kWh
GRID_EMISSION_FACTOR = 0.55  # kg CO2e/kWh (华中区域电网)

# 绿电情景参数
GREEN_ELECTRICITY_PRICE = 0.70  # 元/kWh (增加0.05元绿色溢价)
GREEN_EMISSION_FACTOR = 0.03  # kg CO2e/kWh (绿色电力)

# TEA 基础参数
ORIGINAL_LCOP = 6153.4  # 元/t rPET
VIRGIN_PET_FOOTPRINT = 2250.0  # kg CO2e/t (原生PET基准)

# ============================================================
# 二、任务1.1：LCA 净碳足迹再核算（绿电情景）
# ============================================================

print("=" * 70)
print("任务1.1：LCA 净碳足迹再核算（100%绿电驱动）")
print("=" * 70)

# 原情景 LCA 清单
lca_baseline = {
    '原料瓶砖运输': 150.0,      # kg CO2e (1.25t × 100km × 0.12)
    '生产电力消耗': 467.5,      # kg CO2e (850kWh × 0.55)
    '热洗蒸汽能耗': 130.0,      # kg CO2e (2.0GJ × 65)
    '氢氧化钠药剂': 31.5,       # kg CO2e (15kg × 2.10)
    '新鲜水消耗': 0.95,         # kg CO2e (2.5m³ × 0.38)
    '污水处理负荷': 6.05,       # kg CO2e (2.2m³ × 2.75)
    '副产HDPE替代信用': -150.0  # kg CO2e (-93.75kg × 1.60)
}

# 绿电情景 LCA 清单
lca_green = lca_baseline.copy()

# 电力排放重新计算
electricity_green = ELECTRICITY_CONSUMPTION * GREEN_EMISSION_FACTOR
lca_green['生产电力消耗'] = electricity_green

# 计算净碳足迹
baseline_total = sum(lca_baseline.values())
green_total = sum(lca_green.values())

print("\n【原情景 LCA 清单】（华中区域电网 0.55 kg CO2e/kWh）")
for item, value in lca_baseline.items():
    print(f"  {item}: {value:>10.2f} kg CO2e")
print(f"  {'─' * 45}")
print(f"  净碳足迹合计: {baseline_total:.2f} kg CO2e/t rPET")

print("\n【绿电情景 LCA 清单】（绿色电力 0.03 kg CO2e/kWh）")
for item, value in lca_green.items():
    print(f"  {item}: {value:>10.2f} kg CO2e")
print(f"  {'─' * 45}")
print(f"  净碳足迹合计: {green_total:.2f} kg CO2e/t rPET")

# 减排效益评估
reduction_vs_virgin = (VIRGIN_PET_FOOTPRINT - green_total) / VIRGIN_PET_FOOTPRINT * 100
carbon_reduction = baseline_total - green_total
reduction_rate = carbon_reduction / baseline_total * 100

print("\n【绿电减排效益评估】")
print(f"  相较于原生PET基准 ({VIRGIN_PET_FOOTPRINT} kg CO2e/t):")
print(f"    减碳幅度 = ({VIRGIN_PET_FOOTPRINT} - {green_total:.2f}) / {VIRGIN_PET_FOOTPRINT} × 100%")
print(f"             = {reduction_vs_virgin:.2f}%")
print(f"\n  相较于原电网情景 ({baseline_total} kg CO2e/t):")
print(f"    电力碳减排 = {carbon_reduction:.2f} kg CO2e/t")
print(f"    减排率 = {reduction_rate:.2f}%")

# ============================================================
# 三、任务1.2：TEA 平准化成本变化核算
# ============================================================

print("\n" + "=" * 70)
print("任务1.2：TEA 平准化成本变化核算（绿电溢价影响）")
print("=" * 70)

# 原电力成本
original_electricity_cost = ELECTRICITY_CONSUMPTION * GRID_ELECTRICITY_PRICE
# 绿电成本
green_electricity_cost = ELECTRICITY_CONSUMPTION * GREEN_ELECTRICITY_PRICE
# 成本增加额
electricity_cost_increase = green_electricity_cost - original_electricity_cost

# 新 LCOP
new_lcop = ORIGINAL_LCOP + electricity_cost_increase
lcop_increase_rate = electricity_cost_increase / ORIGINAL_LCOP * 100

print(f"\n【电力成本变化】")
print(f"  原工业电价成本: {ELECTRICITY_CONSUMPTION} kWh × {GRID_ELECTRICITY_PRICE} 元/kWh = {original_electricity_cost:.2f} 元/t")
print(f"  绿电价格成本:   {ELECTRICITY_CONSUMPTION} kWh × {GREEN_ELECTRICITY_PRICE} 元/kWh = {green_electricity_cost:.2f} 元/t")
print(f"  电力成本增加额: {electricity_cost_increase:.2f} 元/t")

print(f"\n【平准化生产成本 (LCOP) 变化】")
print(f"  原 LCOP:  {ORIGINAL_LCOP:.2f} 元/t rPET")
print(f"  新 LCOP:  {new_lcop:.2f} 元/t rPET")
print(f"  增加额:   {electricity_cost_increase:.2f} 元/t")
print(f"  增幅比例: {lcop_increase_rate:.2f}%")

# 经济效益分析
PRODUCT_PRICE = 7600.0  # 元/t rPET
original_profit = PRODUCT_PRICE - ORIGINAL_LCOP
green_profit = PRODUCT_PRICE - new_lcop
profit_decrease = original_profit - green_profit

print(f"\n【利润影响分析】")
print(f"  产品售价: {PRODUCT_PRICE:.2f} 元/t")
print(f"  原吨利润: {original_profit:.2f} 元/t")
print(f"  新吨利润: {green_profit:.2f} 元/t")
print(f"  利润减少: {profit_decrease:.2f} 元/t")

print(f"\n【绿色溢价定价策略建议】")
print(f"  为实现碳中和目标，品牌商可接受一定程度的绿色溢价。")
print(f"  建议定价区间: {PRODUCT_PRICE:.0f} ~ {PRODUCT_PRICE + electricity_cost_increase * 2:.0f} 元/t")
print(f"  对应绿色溢价率: 0% ~ {(electricity_cost_increase * 2 / PRODUCT_PRICE * 100):.2f}%")

# ============================================================
# 四、任务1.3：源头敏感度分析（收率降至70%）
# ============================================================

print("\n" + "=" * 70)
print("任务1.3：源头敏感度分析（产品收率由80%降至70%）")
print("=" * 70)

NEW_YIELD = 0.70
NEW_INPUT_COEFFICIENT = 1 / NEW_YIELD  # 1.4286 t/t
ORIGINAL_INPUT_COEFFICIENT = 1 / PRODUCT_YIELD  # 1.25 t/t
SCALING_FACTOR = NEW_INPUT_COEFFICIENT / ORIGINAL_INPUT_COEFFICIENT  # 1.1429

print(f"\n【MFA 物质平衡变化】")
print(f"  原收率 80%: 吨产品需 {ORIGINAL_INPUT_COEFFICIENT:.4f} t 瓶砖")
print(f"  新收率 70%: 吨产品需 {NEW_INPUT_COEFFICIENT:.4f} t 瓶砖")
print(f"  物耗增幅:   {SCALING_FACTOR:.4f} 倍 (+{(SCALING_FACTOR-1)*100:.2f}%)")

# LCA 敏感度分析（电网情景）
print(f"\n【LCA 碳足迹敏感度分析（收率70%，电网情景）】")

lca_yield_70 = {}
lca_yield_70['原料瓶砖运输'] = NEW_INPUT_COEFFICIENT * 100 * 0.12  # 运输增加
lca_yield_70['生产电力消耗'] = ELECTRICITY_CONSUMPTION * SCALING_FACTOR * GRID_EMISSION_FACTOR
lca_yield_70['热洗蒸汽能耗'] = 2.0 * SCALING_FACTOR * 65.0
lca_yield_70['氢氧化钠药剂'] = 15.0 * SCALING_FACTOR * 2.10
lca_yield_70['新鲜水消耗'] = 2.5 * SCALING_FACTOR * 0.38
lca_yield_70['污水处理负荷'] = 2.2 * SCALING_FACTOR * 2.75

# HDPE副产物信用（按新输入量计算）
hdpe_per_ton_input = 75.0 / 1000.0  # 7.5%
hdpe_new = NEW_INPUT_COEFFICIENT * 1000 * hdpe_per_ton_input  # kg
lca_yield_70['副产HDPE替代信用'] = -hdpe_new * 1.60

yield_70_total = sum(lca_yield_70.values())

print(f"  各分项碳足迹:")
for item, value in lca_yield_70.items():
    print(f"    {item}: {value:>10.2f} kg CO2e")
print(f"  {'─' * 45}")
print(f"  净碳足迹: {yield_70_total:.2f} kg CO2e/t rPET")
print(f"  较原情景增加: {yield_70_total - baseline_total:.2f} kg CO2e (+{(yield_70_total/baseline_total-1)*100:.2f}%)")

# LCA 敏感度分析（绿电情景）
print(f"\n【LCA 碳足迹敏感度分析（收率70%，绿电情景）】")

lca_yield_70_green = lca_yield_70.copy()
lca_yield_70_green['生产电力消耗'] = ELECTRICITY_CONSUMPTION * SCALING_FACTOR * GREEN_EMISSION_FACTOR

yield_70_green_total = sum(lca_yield_70_green.values())

print(f"  净碳足迹: {yield_70_green_total:.2f} kg CO2e/t rPET")
print(f"  较原绿电情景增加: {yield_70_green_total - green_total:.2f} kg CO2e (+{(yield_70_green_total/green_total-1)*100:.2f}%)")

# TEA 敏感度分析
print(f"\n【TEA 成本敏感度分析（收率70%）】")

# 原料成本增加
raw_material_price = 4200.0  # 元/t
original_raw_cost = ORIGINAL_INPUT_COEFFICIENT * raw_material_price
new_raw_cost = NEW_INPUT_COEFFICIENT * raw_material_price
raw_cost_increase = new_raw_cost - original_raw_cost

# 其他变动成本同比例增加
other_variable_costs = 552.5 + 170.0 + 115.0 + 20.3  # 电力+蒸汽+水+固废
new_other_costs = other_variable_costs * SCALING_FACTOR
other_cost_increase = new_other_costs - other_variable_costs

total_cost_increase = raw_cost_increase + other_cost_increase
new_lcop_yield_70 = ORIGINAL_LCOP + total_cost_increase

# 副产物收入增加
original_byproduct_revenue = 93.75 / 1000 * 4500  # 按原输入计算
new_byproduct_revenue = hdpe_new / 1000 * 4500
byproduct_revenue_increase = new_byproduct_revenue - original_byproduct_revenue

net_cost_increase = total_cost_increase - byproduct_revenue_increase
final_lcop_yield_70 = ORIGINAL_LCOP + net_cost_increase

print(f"  原料成本增加: {raw_cost_increase:.2f} 元/t")
print(f"  其他变动成本增加: {other_cost_increase:.2f} 元/t")
print(f"  副产物收入增加: -{byproduct_revenue_increase:.2f} 元/t")
print(f"  净成本增加: {net_cost_increase:.2f} 元/t")
print(f"  新 LCOP: {final_lcop_yield_70:.2f} 元/t rPET")
print(f"  较原情景增幅: {(final_lcop_yield_70/ORIGINAL_LCOP-1)*100:.2f}%")

# ============================================================
# 五、汇总对比表
# ============================================================

print("\n" + "=" * 70)
print("【情景对比汇总表】")
print("=" * 70)

summary_data = {
    '情景': ['原情景(80%收率+电网)', '绿电情景(80%收率+绿电)', '收率70%+电网', '收率70%+绿电'],
    '碳足迹(kg CO2e/t)': [baseline_total, green_total, yield_70_total, yield_70_green_total],
    'LCOP(元/t)': [ORIGINAL_LCOP, new_lcop, final_lcop_yield_70, final_lcop_yield_70 + electricity_cost_increase * SCALING_FACTOR],
    '较原生PET减排率(%)': [
        (VIRGIN_PET_FOOTPRINT - baseline_total) / VIRGIN_PET_FOOTPRINT * 100,
        (VIRGIN_PET_FOOTPRINT - green_total) / VIRGIN_PET_FOOTPRINT * 100,
        (VIRGIN_PET_FOOTPRINT - yield_70_total) / VIRGIN_PET_FOOTPRINT * 100,
        (VIRGIN_PET_FOOTPRINT - yield_70_green_total) / VIRGIN_PET_FOOTPRINT * 100
    ]
}

summary_df = pd.DataFrame(summary_data)
print(summary_df.to_string(index=False))

print("\n" + "=" * 70)
print("计算完成！")
print("=" * 70)
