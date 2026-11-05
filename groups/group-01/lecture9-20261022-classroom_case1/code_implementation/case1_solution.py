#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
第九讲 案例一：废弃 PET 瓶机械物理再生系统
MFA-LCA-TEA 联合核算 + 绿电情景 + 收率敏感度分析

运行:
    python case1_solution.py

输出:
    case1_solution_report.md   （自动生成的作业报告）
"""

from pathlib import Path
import sys

import pandas as pd

# Windows 控制台中文输出
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


# ----------------------------------------------------------------------------
# 0. 定位数据目录（兼容“复制到小组目录”与“直接读 starter_materials”两种情形）
# ----------------------------------------------------------------------------
def locate_data_dir() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        # 情形 A：本脚本与 case_files 同级（复制了完整任务包）
        p = parent / "case_files" / "data_cohort"
        if (p / "mfa_mass_balance.csv").exists():
            return p
        # 情形 B：仍在 starter_materials 下
        p = parent / "starter_materials" / "lecture9-20261022-classroom_case1" / "case_files" / "data_cohort"
        if (p / "mfa_mass_balance.csv").exists():
            return p
    raise FileNotFoundError("未找到 data_cohort 数据目录，请确认 case_files/data_cohort 是否存在")


DATA = locate_data_dir()
mfa = pd.read_csv(DATA / "mfa_mass_balance.csv")
lci = pd.read_csv(DATA / "lci_emission_factors.csv")
tea = pd.read_csv(DATA / "tea_cost_parameters.csv")

# 把 TEA 参数表转成字典，便于按键取值
T = dict(zip(tea["Parameter_Name"], tea["Value"]))
T_unit = dict(zip(tea["Parameter_Name"], tea["Unit"]))


# ----------------------------------------------------------------------------
# 1. 基准情景参数（讲义给定 + 数据表校验）
# ----------------------------------------------------------------------------
FEEDSTOCK_PER_T = 1.25          # t 瓶砖 / t rPET（Y=80%）
TRANSPORT_KM = 100.0            # 运输距离 km
ANNUAL_OUTPUT = float(T["Plant_Annual_Capacity"])       # 16,000 t/a
ANNUAL_FEED = float(T["Feedstock_Annual_Demand"])       # 20,000 t/a
TOTAL_CAPEX = float(T["Total_Capital_Investment"])      # 28,000,000 RMB

# 讲义中的“综合定额”：水+烧碱+辅助药剂合计 115.0 元/t
# 注：按 CSV 单价直接算 2.5 m3 水 + 15 kg 碱 = 59.25 元/t，
#     余下部分为讲义归并的辅助药剂与定额调剂，用综合值才能复现官方 6153.4 元/t。
WATER_CHEM_COMPOSITE = 115.0
MGMT_INS_DEP = 196.4            # 管理、保险及折旧化成本 元/t
BYPRODUCT_KG = 93.75            # 副产 HDPE kg / t rPET

# 基准 LCI 各分项（活动量 × 排放因子）
GHG_TRANSPORT = FEEDSTOCK_PER_T * 1000 * 0.12   # 1250 kg × 0.12 = 150.0
GHG_ELECTRICITY = 850.0 * 0.55                  # 467.5
GHG_STEAM = 2.0 * 65.0                          # 130.0
GHG_NAOH = 15.0 * 2.10                          # 31.5
GHG_WATER = 2.5 * 0.38                          # 0.95
GHG_WASTEWATER = 2.2 * 2.75                      # 6.05
GHG_HDPE_CREDIT = -BYPRODUCT_KG * 1.60          # -150.0

GWP_BASE = (GHG_TRANSPORT + GHG_ELECTRICITY + GHG_STEAM + GHG_NAOH
            + GHG_WATER + GHG_WASTEWATER + GHG_HDPE_CREDIT)
VIRGIN_PET_GWP = 2250.0

# 基准 TEA 分项
COST_FEEDSTOCK = FEEDSTOCK_PER_T * 4200.0       # 5250.0
COST_ELECTRICITY = 850.0 * 0.65                 # 552.5
COST_STEAM = 2.0 * 85.0                         # 170.0
COST_WATER_CHEM = WATER_CHEM_COMPOSITE          # 115.0
COST_SOLID_WASTE = 0.081 * 250.0                # 20.25
COST_LABOR = 3500000.0 / ANNUAL_OUTPUT          # 218.75
COST_MAINTENANCE = TOTAL_CAPEX * 0.03 / ANNUAL_OUTPUT   # 52.5
COST_MGMT = MGMT_INS_DEP                        # 196.4
COST_BYPRODUCT = -BYPRODUCT_KG / 1000 * 4500.0  # -421.875

LCOP_BASE = (COST_FEEDSTOCK + COST_ELECTRICITY + COST_STEAM + COST_WATER_CHEM
             + COST_SOLID_WASTE + COST_LABOR + COST_MAINTENANCE + COST_MGMT
             + COST_BYPRODUCT)

# 变动成本 / 固定成本拆分（用于收率敏感度分析）
VARIABLE_COST = (COST_FEEDSTOCK + COST_ELECTRICITY + COST_STEAM
                 + COST_WATER_CHEM + COST_SOLID_WASTE + COST_BYPRODUCT)
FIXED_COST = COST_LABOR + COST_MAINTENANCE + COST_MGMT


# ----------------------------------------------------------------------------
# 2. 任务 1.1：绿电情景 LCA 再核算
# ----------------------------------------------------------------------------
GRID_EF = 0.55          # 基准电网 kg CO2e/kWh
GREEN_EF = 0.03         # 绿电 kg CO2e/kWh
ELECTRICITY_KWH = 850.0

GHG_ELEC_GREEN = ELECTRICITY_KWH * GREEN_EF
GWP_GREEN = GWP_BASE - GHG_ELECTRICITY + GHG_ELEC_GREEN

REDUCTION_BASE = (VIRGIN_PET_GWP - GWP_BASE) / VIRGIN_PET_GWP * 100
REDUCTION_GREEN = (VIRGIN_PET_GWP - GWP_GREEN) / VIRGIN_PET_GWP * 100


# ----------------------------------------------------------------------------
# 3. 任务 1.2：绿电情景 TEA 与绿色溢价
# ----------------------------------------------------------------------------
ELEC_PRICE_BASE = 0.65
ELEC_PRICE_GREEN = 0.70
COST_ELECTRICITY_GREEN = ELECTRICITY_KWH * ELEC_PRICE_GREEN

LCOP_GREEN = LCOP_BASE - COST_ELECTRICITY + COST_ELECTRICITY_GREEN
LCOP_INC = LCOP_GREEN - LCOP_BASE
LCOP_INC_PCT = LCOP_INC / LCOP_BASE * 100

SELLING_PRICE = 7600.0
MARGIN_BASE = SELLING_PRICE - LCOP_BASE
MARGIN_GREEN = SELLING_PRICE - LCOP_GREEN


# ----------------------------------------------------------------------------
# 4. 任务 1.3：收率 80% → 70% 的连锁效应
# ----------------------------------------------------------------------------
Y_BASE, Y_LOW = 0.80, 0.70
SCALE = Y_BASE / Y_LOW          # 1.142857：单吨产品需处理更多原料

# 口径一（主口径）：所有“按吨产品计”的物耗均随收率反比放大
GWP_LOW = GWP_BASE * SCALE
LCOP_LOW = LCOP_BASE * SCALE
GWP_GREEN_LOW = GWP_GREEN * SCALE
LCOP_GREEN_LOW = LCOP_GREEN * SCALE

# 口径二（对照）：公用工程按吨产品保持不变，仅原料运输与副产信用随进料放大
GWP_LOW_ALT = (GWP_BASE - GHG_TRANSPORT - GHG_HDPE_CREDIT
               + GHG_TRANSPORT * SCALE + GHG_HDPE_CREDIT * SCALE)
LCOP_LOW_ALT = FIXED_COST + VARIABLE_COST * SCALE


# ----------------------------------------------------------------------------
# 5. 基准复核（与讲义/CSV 对照）
# ----------------------------------------------------------------------------
mass_in = float(mfa.loc[mfa["Stage"] == "Input", "Mass_kg"].iloc[0])
mass_out = float(mfa.loc[mfa["Stage"] == "Balance_Check", "Mass_kg"].iloc[1])
mass_products = float(mfa.loc[mfa["Flow_Type"].isin(["Main_Product", "Co_Product"]), "Mass_kg"].sum())
mass_wastes = float(mfa.loc[mfa["Flow_Type"] == "Waste", "Mass_kg"].sum())


# ----------------------------------------------------------------------------
# 6. 控制台输出
# ----------------------------------------------------------------------------
def line(k, v, unit=""):
    print(f"  {k:<34}{v:>12,.2f} {unit}")


print("=" * 72)
print("MFA 物质平衡复核")
print("=" * 72)
line("输入总量", mass_in, "kg")
line("输出总量", mass_out, "kg")
line("产品合计(主+副)", mass_products, "kg")
line("废弃物合计", mass_wastes, "kg")
print(f"  质量守恒校验: {'通过' if abs(mass_in - mass_out) < 1e-9 else '不通过'}")

print("\n" + "=" * 72)
print("基准情景复核（目标: GWP=636.0, LCOP=6153.4）")
print("=" * 72)
line("净碳足迹 GWP_base", GWP_BASE, "kg CO2e/t")
line("平准化成本 LCOP_base", LCOP_BASE, "元/t")
line("相对原生 PET 减碳率", REDUCTION_BASE, "%")

print("\n" + "=" * 72)
print("任务 1.1  绿电情景 LCA")
print("=" * 72)
line("电力碳足迹（绿电）", GHG_ELEC_GREEN, "kg CO2e")
line("净碳足迹 GWP_green", GWP_GREEN, "kg CO2e/t")
line("相对原生 PET 减碳率", REDUCTION_GREEN, "%")
line("较基准情景再降", GWP_BASE - GWP_GREEN, "kg CO2e/t")

print("\n" + "=" * 72)
print("任务 1.2  绿电情景 TEA")
print("=" * 72)
line("电力成本（绿电）", COST_ELECTRICITY_GREEN, "元/t")
line("LCOP_green", LCOP_GREEN, "元/t")
line("LCOP 增加额", LCOP_INC, "元/t")
line("LCOP 增幅", LCOP_INC_PCT, "%")
line("吨产品毛利（基准）", MARGIN_BASE, "元/t")
line("吨产品毛利（绿电）", MARGIN_GREEN, "元/t")

print("\n" + "=" * 72)
print("任务 1.3  收率 80% → 70% 连锁效应")
print("=" * 72)
line("原料需求倍数", SCALE, "倍")
line("GWP（主口径）", GWP_LOW, "kg CO2e/t")
line("GWP 增幅", (GWP_LOW / GWP_BASE - 1) * 100, "%")
line("LCOP（主口径）", LCOP_LOW, "元/t")
line("LCOP 增幅", (LCOP_LOW / LCOP_BASE - 1) * 100, "%")
line("GWP（绿电+低收率）", GWP_GREEN_LOW, "kg CO2e/t")
line("LCOP（绿电+低收率）", LCOP_GREEN_LOW, "元/t")
line("GWP（对照口径）", GWP_LOW_ALT, "kg CO2e/t")
line("LCOP（对照口径）", LCOP_LOW_ALT, "元/t")


# ----------------------------------------------------------------------------
# 7. 自动生成 Markdown 报告
# ----------------------------------------------------------------------------
report = f"""# 案例一作业：废弃 PET 瓶机械物理再生系统 MFA-LCA-TEA 核算

> 功能单位：生产 1 t 瓶级 rPET 颗粒（Cradle-to-Gate）
> 数据来源：`case_files/data_cohort/` 三个 CSV + 讲师讲义基准值

## 一、基准情景复核

| 指标 | 本脚本计算值 | 讲义/CSV 基准 | 结论 |
|---|---|---|---|
| 净碳足迹 GWP | {GWP_BASE:.1f} kg CO₂e/t | 636.0 | 一致 |
| 平准化成本 LCOP | {LCOP_BASE:.1f} 元/t | 6153.4 | 一致（舍入差 {abs(LCOP_BASE - 6153.4):.1f}） |
| 原料投入 | {mass_in:.0f} kg | 1000.0 | 一致 |
| 产品产出 | {mass_products:.0f} kg | 875.0 | 一致 |
| 废弃物 | {mass_wastes:.0f} kg | 125.0 | 一致 |

物质平衡：输入 {mass_in:.0f} kg = 输出 {mass_out:.0f} kg，质量守恒成立。

## 二、任务 1.1 绿电情景 LCA 净碳足迹

仅电力一项的排放因子由 **0.55 → 0.03 kg CO₂e/kWh**，其余清单项不变。

| 过程分项 | 活动量 | 排放因子 | 碳足迹 (kg CO₂e) |
|---|---|---|---|
| 原料运输 | 1.25 t × 100 km | 0.12 kg CO₂e/kg | {GHG_TRANSPORT:.2f} |
| 电力（绿电） | 850 kWh | 0.03 kg CO₂e/kWh | {GHG_ELEC_GREEN:.2f} |
| 蒸汽 | 2.0 GJ | 65.0 kg CO₂e/GJ | {GHG_STEAM:.2f} |
| 烧碱 | 15 kg | 2.10 kg CO₂e/kg | {GHG_NAOH:.2f} |
| 新鲜水 | 2.5 m³ | 0.38 kg CO₂e/m³ | {GHG_WATER:.2f} |
| 污水处理 | 2.2 m³ | 2.75 kg CO₂e/m³ | {GHG_WASTEWATER:.2f} |
| HDPE 副产信用 | -93.75 kg | 1.60 kg CO₂e/kg | {GHG_HDPE_CREDIT:.2f} |
| **净碳足迹 GWP_green** | — | — | **{GWP_GREEN:.2f}** |

- 减排率：({VIRGIN_PET_GWP:.0f} − {GWP_GREEN:.1f}) / {VIRGIN_PET_GWP:.0f} = **{REDUCTION_GREEN:.1f}%**
- 较基准情景（636.0）再降 **{GWP_BASE - GWP_GREEN:.1f} kg CO₂e/t**，降幅 {(GWP_BASE - GWP_GREEN) / GWP_BASE * 100:.1f}%。
- 关键结论：基准情景中电力占总碳足迹 73.5%，是唯一决定性热点；绿电替换后，**运输（150.0）与蒸汽（130.0）跃升为主要排放源**，下一步减排应转向运输电动化与蒸汽电气化。

## 三、任务 1.2 绿电情景 TEA 与绿色溢价

绿电单价 0.65 → 0.70 元/kWh（+0.05 元/kWh 绿色溢价），耗电量不变。

| 项目 | 数值 |
|---|---|
| 电力成本 | {COST_ELECTRICITY:.1f} → {COST_ELECTRICITY_GREEN:.1f} 元/t（+{LCOP_INC:.1f}） |
| **LCOP_green** | **{LCOP_GREEN:.1f} 元/t** |
| LCOP 增加额 | +{LCOP_INC:.1f} 元/t |
| LCOP 增幅 | +{LCOP_INC_PCT:.2f}% |
| 吨产品毛利（售价 7600） | {MARGIN_BASE:.1f} → {MARGIN_GREEN:.1f} 元/t |

**核心判断：成本增幅仅 {LCOP_INC_PCT:.2f}%，而碳足迹下降 {(GWP_BASE - GWP_GREEN) / GWP_BASE * 100:.1f}%，绿色溢价的“环境性价比”极高。**

定价与营销建议：
1. **溢价定价**：在 7600 元/t 基础上加价 1%~2%（76~152 元/t），即可完全覆盖 42.5 元/t 的绿电增量成本，并留有 33.5~109.5 元/t 的净收益。
2. **价值锚定**：对国际饮料品牌按“每吨 rPET 减少 442 kg CO₂e”出具碳足迹声明（PCF），把绿电成本转译为品牌 Scope 3 减排资产。
3. **长约锁定**：与品牌方签 3~5 年绿电 rPET 采购协议（PPA 联动），用销量确定性对冲绿电溢价波动。
4. **风险提示**：绿电溢价仅占成本 0.69%，但 rPET 售价受原生 PET（6800 元/t）价格牵制，溢价空间最终取决于品牌方的 ESG 支付意愿，而非成本本身。

## 四、任务 1.3 收率 80% → 70% 的连锁效应

收率下降意味着**每吨产品需多投入 {SCALE:.4f} 倍的原料**（1/0.7 = {1 / 0.7:.4f} t 瓶砖/t rPET）。

| 指标 | 基准 Y=80% | 低收率 Y=70% | 变化 |
|---|---|---|---|
| 原料需求 | 1.25 t/t | {1 / 0.7:.4f} t/t | +{((1 / 0.7) / 1.25 - 1) * 100:.1f}% |
| GWP（主口径） | {GWP_BASE:.1f} | {GWP_LOW:.1f} | +{(GWP_LOW / GWP_BASE - 1) * 100:.1f}% |
| LCOP（主口径） | {LCOP_BASE:.1f} | {LCOP_LOW:.1f} | +{(LCOP_LOW / LCOP_BASE - 1) * 100:.1f}% |
| GWP（绿电叠加） | {GWP_GREEN:.1f} | {GWP_GREEN_LOW:.1f} | +{(GWP_GREEN_LOW / GWP_GREEN - 1) * 100:.1f}% |
| LCOP（绿电叠加） | {LCOP_GREEN:.1f} | {LCOP_GREEN_LOW:.1f} | +{(LCOP_GREEN_LOW / LCOP_GREEN - 1) * 100:.1f}% |

对照口径（公用工程按吨产品不变，仅运输与副产信用随进料放大）：GWP = {GWP_LOW_ALT:.1f} kg CO₂e/t，LCOP = {LCOP_LOW_ALT:.1f} 元/t。

**连锁机理**：前端分类不纯 → 杂质率上升 → 分选收率下降 → 单吨产品原料需求上升 → 运输与预处理负荷加重（LCA 恶化），同时原料采购成本与固废处置量同步上升（TEA 恶化）。二者同向放大，说明**源头分类是同时决定环境绩效与经济性的共同杠杆**，这正是环境规划中“前端治理优先于末端补救”的量化依据。

## 五、结论

1. 绿电可把净碳足迹从 636.0 降至 **{GWP_GREEN:.1f} kg CO₂e/t**，减碳率由 71.7% 提升至 **{REDUCTION_GREEN:.1f}%**，是当前成本最低的深度减排手段。
2. 绿电溢价仅使 LCOP 上升 **{LCOP_INC_PCT:.2f}%**，环境收益远大于经济代价，具备商业可行性。
3. 收率由 80% 降至 70%，GWP 与 LCOP 同步恶化约 **{(SCALE - 1) * 100:.1f}%**，源头分类质量是系统韧性的关键变量。

## 六、假设与口径说明

- 收率敏感度主口径假定：所有按吨产品计的物耗、公用工程与固定成本分摊均随收率反比变化（年进料 20,000 t 不变，年产量降至 14,000 t）。对照口径假定公用工程强度不变，结果一并列出以便比较。
- 水与烧碱采用讲义“综合定额”115.0 元/t；若按 CSV 单价直接核算为 59.25 元/t，差额为讲义归并的辅助药剂与定额调剂。
- 运输排放按 CSV 口径（0.12 kg CO₂e/kg 原料，运距 100 km）计算，与讲义 150.0 kg 一致。
- 副产 HDPE 采用避免负荷法计入 -150.0 kg CO₂e/t 信用。
"""

out_md = Path(__file__).with_name("case1_solution_report.md")
out_md.write_text(report, encoding="utf-8")
print(f"\n报告已生成: {out_md}")
