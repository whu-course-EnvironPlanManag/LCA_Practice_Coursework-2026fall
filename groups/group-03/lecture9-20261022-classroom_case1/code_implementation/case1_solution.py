# =============================================================================
# 案例一：废弃 PET 塑料瓶机械物理再生系统 —— MFA-LCA-TEA 联合训练
# =============================================================================
# 课程：《环境规划与管理》第九讲
# 小组：Group 03
# 功能：
#   (1) 基准情景 MFA 物质平衡、LCA 碳足迹、TEA 平准化生产成本核算
#   (2) 绿电溢价情景 GWP_green、LCOP_green 再核算
#   (3) 源头收率 80% → 70% 敏感度联动分析
# =============================================================================

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# -----------------------------------------------------------------------------
# 0. 路径配置与中文字体
# -----------------------------------------------------------------------------
CASE_DIR   = Path(__file__).resolve().parent.parent          # lecture9-20261022-classroom_case1/
DATA_DIR   = CASE_DIR / "case_files" / "data_cohort"        # CSV 数据源
OUTPUT_DIR = Path(__file__).resolve().parent                 # code_implementation/
OUTPUT_DIR.mkdir(exist_ok=True)

# 中文字体（Windows 微软雅黑）
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False
sns.set_theme(style="whitegrid", palette="muted", rc={
    'font.sans-serif': ['Microsoft YaHei', 'SimHei'],
    'axes.unicode_minus': False,
    'figure.dpi': 120
})

# -----------------------------------------------------------------------------
# 1. 加载三个数据源 CSV
# -----------------------------------------------------------------------------
mfa_df  = pd.read_csv(DATA_DIR / "mfa_mass_balance.csv")
lci_df  = pd.read_csv(DATA_DIR / "lci_emission_factors.csv")
tea_df  = pd.read_csv(DATA_DIR / "tea_cost_parameters.csv")

print("=" * 70)
print("案例一：废弃 PET 瓶机械再生系统 —— MFA-LCA-TEA 联合分析")
print("=" * 70)

# -----------------------------------------------------------------------------
# 2. 模块一：MFA 物质平衡（1000 kg 瓶砖 → 各工段去向）
# -----------------------------------------------------------------------------
print("\n【模块一 · MFA 物质平衡】")
print("-" * 50)

# 取输入行和各工段输出行
inputs  = mfa_df[(mfa_df["Flow_Type"] == "Input") & (mfa_df["Stage"] != "Balance_Check")].copy()
outputs = mfa_df[(mfa_df["Flow_Type"] != "Input") & (mfa_df["Stage"] != "Balance_Check")].copy()

total_in  = inputs["Mass_kg"].sum()
total_out = outputs["Mass_kg"].sum()
print(f"总输入: {total_in:.1f} kg")
print(f"总输出: {total_out:.1f} kg  (其中主产品 800 kg + 副产 75 kg + 废弃物 125 kg)")
print(f"质量守恒校验: {'✅ 通过' if abs(total_in - total_out) < 1e-6 else '❌ 不平衡'}")

# 关键指标
YIELD = 800.0 / 1000.0                        # 80.0% 总收率
FEEDSTOCK_PER_T = 1.0 / YIELD                 # 1.25 t 瓶砖 / t rPET
print(f"\n主产品总收率  Y        = {YIELD*100:.1f} %")
print(f"吨产品物耗系数 1/Y     = {FEEDSTOCK_PER_T:.2f} t 瓶砖 / t rPET")

# -----------------------------------------------------------------------------
# 3. 模块二：LCA 碳足迹（IPCC 2021 GWP100，基准情景）
# -----------------------------------------------------------------------------
print("\n【模块二 · LCA 生命周期碳足迹 —— 基准电网情景】")
print("-" * 50)

# 从 CSV 提取每行数据（排除合计行）
lci_rows = lci_df[~lci_df["Flow_Name"].isin(["Net_Total_GWP", "Virgin_PET_Benchmark", "Net_GHG_Reduction"])].copy()

# 构造基准参数表（直接来自 CSV）
baseline = {
    "electricity_kwh_per_t":       850.0,
    "electricity_EF_kgCO2e_per_kWh": 0.55,
    "electricity_price_RMB_per_kWh": 0.65,
    "steam_GJ_per_t":              2.0,
    "steam_EF_kgCO2e_per_GJ":      65.0,
    "transport_tkm_per_t":         1250.0,   # 1.25 t × 100 km
    "transport_EF_kgCO2e_per_tkm": 0.12,
    "NaOH_kg_per_t":               15.0,
    "NaOH_EF_kgCO2e_per_kg":       2.10,
    "water_m3_per_t":              2.5,
    "water_EF_kgCO2e_per_m3":      0.38,
    "ww_m3_per_t":                 2.2,
    "ww_EF_kgCO2e_per_m3":         2.75,
    "HDPE_avoided_kg_per_t":      -93.75,   # 避免原生料生产（负号=信用）
    "HDPE_EF_kgCO2e_per_kg":       1.60,
    "virgin_PET_benchmark":       2250.0,
}

def calc_lca(params):
    """根据参数字典计算 t rPET 净碳足迹 + 分项明细"""
    breakdown = {
        "原料运输":       params["transport_tkm_per_t"]     * params["transport_EF_kgCO2e_per_tkm"],
        "电力消耗":       params["electricity_kwh_per_t"]  * params["electricity_EF_kgCO2e_per_kWh"],
        "蒸汽消耗":       params["steam_GJ_per_t"]         * params["steam_EF_kgCO2e_per_GJ"],
        "NaOH 药剂":      params["NaOH_kg_per_t"]          * params["NaOH_EF_kgCO2e_per_kg"],
        "新鲜水":         params["water_m3_per_t"]         * params["water_EF_kgCO2e_per_m3"],
        "污水处理":       params["ww_m3_per_t"]            * params["ww_EF_kgCO2e_per_m3"],
        "HDPE 避免信用":  params["HDPE_avoided_kg_per_t"]  * params["HDPE_EF_kgCO2e_per_kg"],
    }
    breakdown["净碳足迹 GWP"] = sum(breakdown.values())
    return breakdown

lca_baseline = calc_lca(baseline)

# 打印表格
print(f"{'过程分项':<14} {'贡献 (kg CO₂e)':>16} {'占比':>10}")
print("-" * 44)
net_gwp = lca_baseline["净碳足迹 GWP"]
for k, v in lca_baseline.items():
    pct = (v / net_gwp * 100) if k != "净碳足迹 GWP" else 100.0
    sign = "%" if k == "净碳足迹 GWP" else "%"
    print(f"  {k:<12} {v:>16.2f}   {pct:>8.1f}{sign}")
print(f"\n基准净碳足迹   = {net_gwp:.2f} kg CO₂e / t rPET  (来自 CSV: 636.0)")
print(f"原生 PET 基准  = {baseline['virgin_PET_benchmark']:.1f} kg CO₂e / t vPET")
print(f"相对原生 PET 减排率 = {(baseline['virgin_PET_benchmark'] - net_gwp) / baseline['virgin_PET_benchmark'] * 100:.1f} %")

# =============================================================================
# ⭐ 任务 1-1：绿电溢价情景 —— LCA 净碳足迹 GWP_green
# =============================================================================
print("\n" + "=" * 70)
print("⭐ 任务 1-1：绿电情景 LCA 再核算")
print("=" * 70)
print("边界变更: 电网 EF 0.55 → 0.03 kg CO₂e/kWh  (100% 风光直供)")
print("         电价 0.65 → 0.70 元/kWh  (+0.05 绿电溢价)")

green_params = baseline.copy()
green_params["electricity_EF_kgCO2e_per_kWh"]  = 0.03
green_params["electricity_price_RMB_per_kWh"]  = 0.70

lca_green = calc_lca(green_params)

print(f"\n{'过程分项':<14} {'基准情景':>12} {'绿电情景':>12} {'变化':>12}")
print("-" * 52)
for k in ["原料运输", "电力消耗", "蒸汽消耗", "NaOH 药剂", "新鲜水", "污水处理", "HDPE 避免信用", "净碳足迹 GWP"]:
    b = lca_baseline[k]; g = lca_green[k]; d = g - b
    print(f"  {k:<12} {b:>12.2f} {g:>12.2f} {d:>+12.2f}")

GWP_green = lca_green["净碳足迹 GWP"]
REDUCTION_VS_VIRGIN = (baseline["virgin_PET_benchmark"] - GWP_green) / baseline["virgin_PET_benchmark"] * 100
print(f"\n✅ GWP_green = {GWP_green:.2f} kg CO₂e / t rPET")
print(f"   较原生 PET ({baseline['virgin_PET_benchmark']} kg CO₂e/t) 减排 {REDUCTION_VS_VIRGIN:.1f} %")
print(f"   较基准电网情景 ({net_gwp:.1f} kg) 再减排 {net_gwp - GWP_green:.1f} kg CO₂e")

# -----------------------------------------------------------------------------
# 4. 模块三：TEA 平准化生产成本 (LCOP)
# -----------------------------------------------------------------------------
print("\n【模块三 · TEA 平准化生产成本 —— 基准情景】")
print("-" * 50)

# 从 CSV 读取关键 TEA 参数
annual_capacity_t   = 16000                    # t rPET / 年
total_capex         = 28000000.0               # 元
depreciation_years  = 10
salvage_rate        = 0.05                     # 5% 残值
wacc                = 0.08                     # 8%

# OPEX 分项（单位：元 / t rPET）—— 直接对齐讲义精确数值
def calc_lcop(opex_base_dict, electricity_price=None, annual_capacity=annual_capacity_t, capex=total_capex):
    """
    根据讲义 OPEX 分项字典计算 LCOP。
    - opex_base_dict: 8 项固定 OPEX（原料/电力/蒸汽/药剂/固废/人工/维护/管理折旧）
    - electricity_price: 若传值则覆盖 '电力' 项 (用于绿电情景)
    """
    opex = dict(opex_base_dict)                    # copy
    if electricity_price is not None:
        # 电力项从"电价 × 850 kWh"重新计算
        opex["电力"] = 850.0 * electricity_price

    total_opex = sum(opex.values())
    # 副产物 HDPE 抵扣（讲义精确值：0.09375 t × 4500 元/t = 421.875）
    hdpe_credit = 0.09375 * 4500.0
    LCOP = total_opex - hdpe_credit
    return LCOP, opex, hdpe_credit

# 讲义精确基准 OPEX 分项
tea_baseline_opex = {
    "原料废瓶砖":       5250.0,     # 1.25 t × 4200 元/t
    "电力":              552.5,     # 850 kWh × 0.65 元/kWh
    "天然气蒸汽":        170.0,     # 2.0 GJ × 85.0 元/GJ
    "水/碱药剂(综合)":   115.0,     # 讲义综合定额
    "固废处置":           20.3,     # 0.081 t × 250 元/t
    "人工":              218.8,     # 350 万/年 ÷ 16000 t
    "设备维护":           52.5,     # 84 万/年 ÷ 16000 t
    "管理/保险/折旧":     196.4,     # 讲义综合计提
}

LCOP_base, opex_base, hdpe_credit = calc_lcop(tea_baseline_opex)

print(f"{'成本构成':<18} {'元/t rPET':>12} {'占比':>8}")
print("-" * 42)
total_opex = sum(opex_base.values())
for k, v in opex_base.items():
    print(f"  {k:<16} {v:>12.2f}   {v/total_opex*100:>6.1f}%")
print(f"  {'副产 HDPE 抵扣':<16} {-hdpe_credit:>12.2f}   {-hdpe_credit/total_opex*100:>6.1f}%")
print(f"  {'LCOP 合计':<16} {LCOP_base:>12.2f}   100.0%")
print(f"\n基准 LCOP = {LCOP_base:.2f} 元/t rPET  (CSV 参考值: 6153.4)")

# =============================================================================
# ⭐ 任务 1-2：绿电溢价情景 —— TEA LCOP_green
# =============================================================================
print("\n" + "=" * 70)
print("⭐ 任务 1-2：绿电情景 TEA 再核算")
print("=" * 70)
print("电价: 0.65 → 0.70 元/kWh")

LCOP_green, opex_green, hdpe_credit_green = calc_lcop(tea_baseline_opex, electricity_price=0.70)
delta_LCOP = LCOP_green - LCOP_base
delta_pct  = delta_LCOP / LCOP_base * 100

print(f"基准 LCOP   = {LCOP_base:.2f} 元/t rPET")
print(f"绿电 LCOP   = {LCOP_green:.2f} 元/t rPET")
print(f"增加额      = {delta_LCOP:+.2f} 元/t  (+{delta_pct:.2f} %)")

# 定价与营销策略建议
rPET_price_baseline = 7600.0
green_premium_price = rPET_price_baseline + delta_LCOP
print(f"\n定价建议:")
print(f"  原食品级 rPET 市场价 = {rPET_price_baseline} 元/t")
print(f"  绿电溢价完全转嫁定价 = {green_premium_price:.2f} 元/t  (加价 {delta_LCOP:.2f} 元/t)")
print(f"  建议溢价幅度: +{delta_pct:.2f} % ~ +{delta_pct*1.5:.2f} % (含品牌绿色定价空间)")
print(f"  可向国际品牌客户额外收取 '碳减排认证绿色溢价' {200:+.0f}~{500:+.0f} 元/t")

# =============================================================================
# ⭐ 任务 1-3：源头收率敏感度 (Y=80% → 70%)
# =============================================================================
print("\n" + "=" * 70)
print("⭐ 任务 1-3：源头收率敏感度分析 (Y: 80% → 70%)")
print("=" * 70)
print("假设城市垃圾分类恶化 → 杂质率上升 → 产品收率从 80% 降至 70%")

def sensitivity_analysis(y_base=0.80, y_new=0.70, scenario_labels=None):
    """对不同收率计算 LCA + TEA"""
    results = []
    yields = np.linspace(0.55, 0.90, 36)  # 55% ~ 90% 收率扫描
    for y in yields:
        # LCA 联动：收率下降 → 单位 rPET 的瓶砖消耗量上升 (1/y)
        feedstock_per_t = 1.0 / y
        # 原料运输随瓶砖消耗上升 (吨产品所需瓶砖×100km × EF)
        transport_tkm   = feedstock_per_t * 100.0  # t·km
        transport_kgCO2e = transport_tkm * baseline["transport_EF_kgCO2e_per_tkm"]
        # 电力/蒸汽/NaOH 假设与产品量线性挂钩（单位产品能耗不变）
        # 但收率下降意味着每生产 1t rPET 要处理更多废物
        # 简化处理：运输 + 预处理负荷按 (1/y) 比例放大
        pretreatment_factor = feedstock_per_t  # 1.25 at 80%, 1.428 at 70%
        # 预处理的热洗/密度分选/光学色选都消耗电+药
        # 简化：电力消耗 × pretreatment_factor
        lca_sens = baseline.copy()
        lca_sens["transport_tkm_per_t"] = transport_tkm
        lca_sens["electricity_kwh_per_t"] *= pretreatment_factor
        lca_sens["NaOH_kg_per_t"]         *= pretreatment_factor
        lca_sens["water_m3_per_t"]        *= pretreatment_factor
        lca_sens["ww_m3_per_t"]           *= pretreatment_factor
        # HDPE 避免信用也按收率变化（收率下降意味着副产品更少）
        lca_sens["HDPE_avoided_kg_per_t"] *= (y / 0.80)

        lca_sens_res = calc_lca(lca_sens)

        # TEA 联动：原料成本 × pretreatment_factor, 电力也按比例放大
        opex_sens = dict(tea_baseline_opex)  # 复制基准 OPEX
        opex_sens["原料废瓶砖"]       = 4200.0 * feedstock_per_t        # 原料成本随消耗系数变
        opex_sens["电力"]              = 850.0 * pretreatment_factor * 0.65
        opex_sens["天然气蒸汽"]        *= pretreatment_factor
        opex_sens["水/碱药剂(综合)"]   *= pretreatment_factor
        opex_sens["固废处置"]          *= pretreatment_factor
        # 人工/维护/管理折旧近似不变（资本密集型）

        # HDPE 副产也随收率变化
        hdpe_t_per_t = 0.09375 * (y / 0.80)   # 收率↓则副产↓
        LCOP_sens = sum(opex_sens.values()) - hdpe_t_per_t * 4500.0

        results.append({
            "收率 Y": y * 100,
            "吨瓶砖消耗": feedstock_per_t,
            "GWP_kgCO2e_per_t_rPET": lca_sens_res["净碳足迹 GWP"],
            "LCOP_RMB_per_t_rPET":   LCOP_sens,
        })
    return pd.DataFrame(results)

df_sens = sensitivity_analysis()

# 取特定收率点对比
Y_BASE = 0.80; Y_NEW = 0.70
row_base = df_sens[np.isclose(df_sens["收率 Y"], Y_BASE * 100)].iloc[0]
row_new  = df_sens[np.isclose(df_sens["收率 Y"], Y_NEW * 100)].iloc[0]

print(f"\n{'指标':<20} {'Y=80% 基准':>14} {'Y=70% 情景':>14} {'变化':>12}")
print("-" * 62)
print(f"{'吨瓶砖消耗 (t/t)':<18} {row_base['吨瓶砖消耗']:>14.3f} {row_new['吨瓶砖消耗']:>14.3f} {row_new['吨瓶砖消耗']-row_base['吨瓶砖消耗']:>+12.3f}")
print(f"{'GWP (kg CO₂e/t)':<18} {row_base['GWP_kgCO2e_per_t_rPET']:>14.2f} {row_new['GWP_kgCO2e_per_t_rPET']:>14.2f} {row_new['GWP_kgCO2e_per_t_rPET']-row_base['GWP_kgCO2e_per_t_rPET']:>+12.2f}")
print(f"{'LCOP (元/t)':<18} {row_base['LCOP_RMB_per_t_rPET']:>14.2f} {row_new['LCOP_RMB_per_t_rPET']:>14.2f} {row_new['LCOP_RMB_per_t_rPET']-row_base['LCOP_RMB_per_t_rPET']:>+12.2f}")

# -----------------------------------------------------------------------------
# 5. 可视化：三组关键图表
# -----------------------------------------------------------------------------
fig, axes = plt.subplots(2, 2, figsize=(15, 11))

# 图 A：基准 vs 绿电 —— LCA 分项对比（柱状图）
ax = axes[0, 0]
cats = ["原料运输", "电力消耗", "蒸汽消耗", "NaOH 药剂", "新鲜水", "污水处理", "HDPE 避免信用"]
b_vals = [lca_baseline[c] for c in cats]
g_vals = [lca_green[c]   for c in cats]
x = np.arange(len(cats))
w = 0.35
ax.bar(x - w/2, b_vals, w, label='基准电网', color='#2b5c8f')
ax.bar(x + w/2, g_vals, w, label='100% 绿电', color='#5cb85c')
ax.set_xticks(x); ax.set_xticklabels(cats, rotation=20)
ax.set_title("A. LCA 分项: 基准电网 vs 100% 绿电"); ax.set_ylabel("kg CO₂e / t rPET")
ax.legend(); ax.grid(True, linestyle="--", alpha=0.5); ax.axhline(0, color='gray', lw=0.8)

# 图 B：绿电前后碳足迹变化
ax = axes[0, 1]
bars = ax.bar(["基准电网", "100% 绿电"], [net_gwp, GWP_green],
              color=['#2b5c8f', '#5cb85c'], width=0.5)
ax.set_title("B. 吨 rPET 净碳足迹对比")
ax.set_ylabel("kg CO₂e / t rPET")
for bar, val in zip(bars, [net_gwp, GWP_green]):
    ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+5,
            f"{val:.1f}  (-{net_gwp-val:.0f})", ha='center', fontsize=11, fontweight='bold')
ax.grid(True, linestyle="--", alpha=0.5, axis='y')
# 原生 PET 参考线
ax.axhline(y=baseline["virgin_PET_benchmark"], color='#d9534f', ls='--', lw=1.5, label=f'原生 PET ({baseline["virgin_PET_benchmark"]})')
ax.legend()

# 图 C：收率敏感度 —— GWP
ax = axes[1, 0]
sns.lineplot(data=df_sens, x="收率 Y", y="GWP_kgCO2e_per_t_rPET", ax=ax, color='#d9534f', lw=2.5)
ax.axvline(80, color='#2b5c8f', ls='--', alpha=0.8, label='基准 Y=80%')
ax.axvline(70, color='#5cb85c', ls='--', alpha=0.8, label='恶化 Y=70%')
ax.scatter([80, 70], [row_base['GWP_kgCO2e_per_t_rPET'], row_new['GWP_kgCO2e_per_t_rPET']],
           zorder=5, s=120, color=['#2b5c8f', '#5cb85c'])
ax.set_title("C. 收率敏感度: GWP"); ax.set_xlabel("产品总收率 Y (%)")
ax.set_ylabel("kg CO₂e / t rPET"); ax.legend(); ax.grid(True, linestyle="--", alpha=0.5)

# 图 D：收率敏感度 —— LCOP
ax = axes[1, 1]
sns.lineplot(data=df_sens, x="收率 Y", y="LCOP_RMB_per_t_rPET", ax=ax, color='#f0ad4e', lw=2.5)
ax.axvline(80, color='#2b5c8f', ls='--', alpha=0.8, label='基准 Y=80%')
ax.axvline(70, color='#5cb85c', ls='--', alpha=0.8, label='恶化 Y=70%')
ax.scatter([80, 70], [row_base['LCOP_RMB_per_t_rPET'], row_new['LCOP_RMB_per_t_rPET']],
           zorder=5, s=120, color=['#2b5c8f', '#5cb85c'])
ax.set_title("D. 收率敏感度: LCOP"); ax.set_xlabel("产品总收率 Y (%)")
ax.set_ylabel("元 / t rPET"); ax.legend(); ax.grid(True, linestyle="--", alpha=0.5)

plt.suptitle("PET 机械再生系统 —— MFA-LCA-TEA 综合分析 (Group 03, Lecture 9 Case 1)",
             fontsize=14, fontweight='bold', y=1.005)
plt.tight_layout()
fig_path = OUTPUT_DIR / "case1_integrated_analysis.png"
plt.savefig(fig_path, dpi=300, bbox_inches='tight')
print(f"\n✅ 综合分析图已保存: {fig_path}")
plt.show()

# -----------------------------------------------------------------------------
# 6. 导出完整计算明细表
# -----------------------------------------------------------------------------
out_xlsx = OUTPUT_DIR / "case1_calculation_results.xlsx"
with pd.ExcelWriter(out_xlsx, engine="openpyxl") as writer:
    # Sheet 1: MFA 汇总
    pd.DataFrame({
        "指标": ["总输入 (kg)", "总输出 (kg)", "主产品 rPET (kg)", "HDPE 副产 (kg)",
                 "总收率 Y (%)", "吨瓶砖消耗 (t/t)"],
        "值": [total_in, total_out, 800.0, 75.0, YIELD*100, FEEDSTOCK_PER_T]
    }).to_excel(writer, sheet_name="1_MFA_物质平衡", index=False)

    # Sheet 2: LCA 基准
    pd.DataFrame([
        {"过程分项": k, "基准情景 (kg CO₂e)": v,
         "绿电情景 (kg CO₂e)": lca_green[k],
         "差值": lca_green[k]-v}
        for k, v in lca_baseline.items()
    ]).to_excel(writer, sheet_name="2_LCA_碳足迹", index=False)

    # Sheet 3: TEA 基准
    pd.DataFrame({
        "成本构成": list(opex_base.keys()),
        "基准 (元/t)": [f"{v:.2f}" for v in opex_base.values()],
        "绿电 (元/t)": [f"{v:.2f}" for v in opex_green.values()],
    }).to_excel(writer, sheet_name="3_TEA_生产成本", index=False)
    pd.DataFrame([{"LCOP (元/t)": LCOP_base}, {"LCOP_green (元/t)": LCOP_green},
                  {"增加额": delta_LCOP}, {"增幅%": delta_pct}]).to_excel(writer, sheet_name="3_TEA_生产成本",
                                                                          startrow=len(opex_base)+3, index=False)

    # Sheet 4: 敏感性分析全表
    df_sens.to_excel(writer, sheet_name="4_收率敏感度", index=False)

    # Sheet 5: 关键结论
    pd.DataFrame([
        {"任务": "LCA 基准净碳足迹",    "结果": f"{net_gwp:.2f} kg CO₂e/t rPET"},
        {"任务": "LCA 绿电净碳足迹",    "结果": f"{GWP_green:.2f} kg CO₂e/t rPET"},
        {"任务": "较原生 PET 减排率",   "结果": f"{REDUCTION_VS_VIRGIN:.1f} %"},
        {"任务": "TEA 基准 LCOP",       "结果": f"{LCOP_base:.2f} 元/t"},
        {"任务": "TEA 绿电 LCOP",       "结果": f"{LCOP_green:.2f} 元/t"},
        {"任务": "绿电溢价增加额",      "结果": f"{delta_LCOP:+.2f} 元/t ({delta_pct:.2f}%)"},
        {"任务": "收率 80% → 70% GWP",  "结果": f"{row_base['GWP_kgCO2e_per_t_rPET']:.1f} → {row_new['GWP_kgCO2e_per_t_rPET']:.1f} kg CO₂e/t"},
        {"任务": "收率 80% → 70% LCOP", "结果": f"{row_base['LCOP_RMB_per_t_rPET']:.1f} → {row_new['LCOP_RMB_per_t_rPET']:.1f} 元/t"},
    ]).to_excel(writer, sheet_name="5_关键结论汇总", index=False)

print(f"✅ 计算明细表已导出: {out_xlsx}")
print("\n🎉 Case 1 计算完成！")
