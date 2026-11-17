# -*- coding: utf-8 -*-
"""
案例一：废弃 PET 塑料瓶机械物理再生系统 MFA-LCA-TEA 联动计算
------------------------------------------------------------------
功能单位：1 t 瓶级 rPET 颗粒（Cradle-to-Gate）
数据来源：case_files/case1_documentation.md 第一～五部分
         以及 case_files/data_cohort/*.csv

运行：python mfa_lca_tea_calc.py
输出：results_summary.csv、scenario_comparison.png
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import rcParams

# 中文显示与负号修正
rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
rcParams["axes.unicode_minus"] = False

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

OUT_DIR = Path(__file__).resolve().parent

# ============================================================
# 一、基础参数（全部取自讲义第三、四部分，不做任何外部假设）
# ============================================================
Y_BASE = 0.80                 # 基准综合收率
FEED_BASE = 1 / Y_BASE        # 基准吨产品物耗系数 = 1.25 t 瓶砖/t rPET
BATCH_IN = 1000.0             # MFA 控制体：单批次进料 kg

# --- LCI 活动水平（吨 rPET）---
ELEC_KWH = 850.0              # 电力
STEAM_GJ = 2.0                # 热洗蒸汽
NAOH_KG = 15.0                # 烧碱
WATER_M3 = 2.5                # 新鲜水
WW_M3 = 2.2                   # 污水处理量
TRANSPORT_KG = 1250.0         # 原料运输量（1.25 t × 100 km，按 kg 计费）
HDPE_CREDIT_KG = 93.75        # 副产 HDPE 信用量（= 75 kg / 0.80）

# --- 背景排放因子 ---
EF_ELEC_GRID = 0.55           # kg CO2e/kWh（华中电网）
EF_ELEC_GREEN = 0.03          # kg CO2e/kWh（风光绿电）
EF_STEAM = 65.0               # kg CO2e/GJ
EF_NAOH = 2.10                # kg CO2e/kg
EF_WATER = 0.38               # kg CO2e/m3
EF_WW = 2.75                  # kg CO2e/m3
EF_TRANSPORT = 0.12           # kg CO2e/kg（等价于 100 km 的 t·km 因子）
EF_HDPE_VIRGIN = 1.60         # kg CO2e/kg
GWP_VIRGIN_PET = 2250.0       # kg CO2e/t 原生 PET 基准

# --- TEA 经济参数 ---
PRICE_FEED = 4200.0           # 元/t 废瓶砖
PRICE_ELEC_GRID = 0.65        # 元/kWh
PRICE_ELEC_GREEN = 0.70       # 元/kWh（含 0.05 元绿色溢价）
PRICE_STEAM = 85.0            # 元/GJ
CHEM_WATER = 115.0            # 元/t（讲义给定的"新鲜水+烧碱"综合定额）
PRICE_WASTE = 250.0           # 元/t 焚烧处置
PRICE_HDPE = 4500.0           # 元/t 副产 HDPE
WASTE_INCIN_BATCH = 65.0      # 每 1000 kg 进料需焚烧固废（标签 20 + HDPE 损失 5 + 超细粉 40）
CAPEX = 2800.0                # 万元
FIXED_ANNUAL = 350.0 + 84.0 + 314.24   # 万元/年（人工+维保+管理/保险/折旧）
Q_BASE = 16000.0              # t/a 基准年产量
FEED_SUPPLY = 20000.0         # t/a 废瓶砖年收购量（产能约束）
PRICE_RPET = 7600.0           # 元/t 售价


# ============================================================
# 二、MFA：物质平衡
# ============================================================
def mfa(y):
    """按收率 y 推算吨产品物质流（与讲义质量守恒结构一致）"""
    feed = 1 / y                                   # t 瓶砖/t rPET
    # 以 1000 kg 进料为控制体：主产品 = 1000*y，副产 HDPE 按 7.5% 进料比例
    pet_out = BATCH_IN * y
    hdpe_out = BATCH_IN * 0.075
    waste_out = BATCH_IN - pet_out - hdpe_out
    return {
        "feed_t_per_t": feed,
        "pet_kg": pet_out,
        "hdpe_kg": hdpe_out,
        "waste_kg": waste_out,
    }


# ============================================================
# 三、LCA：门到门碳足迹
# ============================================================
def lca(y, ef_elec):
    """返回清单分项与净碳足迹（kg CO2e/t rPET）

    与原料投入成正比的前端负荷按 f = (1/y)/(1/0.8) 线性缩放；
    造粒电力按吨产品定额保持不变（与产量相关而非与原料量相关）。
    """
    f = (1 / y) / FEED_BASE
    items = {
        "原料瓶砖运输": TRANSPORT_KG * f * EF_TRANSPORT,
        "生产电力消耗": ELEC_KWH * ef_elec,
        "热洗蒸汽能耗": STEAM_GJ * f * EF_STEAM,
        "氢氧化钠药剂": NAOH_KG * f * EF_NAOH,
        "新鲜水消耗": WATER_M3 * f * EF_WATER,
        "污水处理负荷": WW_M3 * f * EF_WW,
        "副产 HDPE 替代信用": -HDPE_CREDIT_KG * f * EF_HDPE_VIRGIN,
    }
    items["净生命周期碳足迹"] = sum(items.values())
    return items


# ============================================================
# 四、TEA：平准化成本与年毛利
# ============================================================
def tea(y, price_elec, q_out):
    """返回单吨成本分项与 LCOP（元/t rPET）；q_out 为年产量 t/a"""
    # 固定成本（人工、维保、管理/保险/折旧）按实际年产量摊薄
    f = (1 / y) / FEED_BASE
    # 焚烧固废：基准三条物流 65 kg/批；收率由 80% 下降所增加的损失按杂质全部计入焚烧
    waste_kg_per_t = (WASTE_INCIN_BATCH + (Y_BASE - y) * BATCH_IN) / (BATCH_IN * y / 1000)
    items = {
        "原料废瓶砖费用": (1 / y) * PRICE_FEED,
        "电力动力费用": ELEC_KWH * price_elec,
        "天然气蒸汽热力": STEAM_GJ * f * PRICE_STEAM,
        "新鲜水与烧碱药剂": CHEM_WATER * f,
        "焚烧杂质固废处置费": waste_kg_per_t / 1000 * PRICE_WASTE,
        "人工编制成本": 350.0 * 1e4 / q_out,
        "设备维护保修费": 84.0 * 1e4 / q_out,
        "管理、保险及折旧化成本": (FIXED_ANNUAL - 350.0 - 84.0) * 1e4 / q_out,
        "副产物外售收入抵扣": -HDPE_CREDIT_KG * f / 1000 * PRICE_HDPE,
    }
    items["平准化生产成本"] = sum(items.values())
    return items


# ============================================================
# 五、情景设置与自检
# ============================================================
scenarios = [
    # 名称, 收率, 电力因子, 电价, 年产量
    ("S0 基准（电网电）", Y_BASE, EF_ELEC_GRID, PRICE_ELEC_GRID, Q_BASE),
    ("S1 绿电（任务1）", Y_BASE, EF_ELEC_GREEN, PRICE_ELEC_GREEN, Q_BASE),
    ("S2 绿电+收率70%", 0.70, EF_ELEC_GREEN, PRICE_ELEC_GREEN, FEED_SUPPLY * 0.70),
    ("S3 电网+收率70%", 0.70, EF_ELEC_GRID, PRICE_ELEC_GRID, FEED_SUPPLY * 0.70),
]

print(f"{'情景':<18}{'GWP(kgCO2e/t)':>16}{'LCOP(元/t)':>13}{'年毛利(万元)':>14}")
rows = []
for name, y, ef, pe, q in scenarios:
    lca_r = lca(y, ef)
    tea_r = tea(y, pe, q)
    gwp = lca_r["净生命周期碳足迹"]
    lcop = tea_r["平准化生产成本"]
    profit = (PRICE_RPET - lcop) * q / 1e4
    rows.append((name, y, gwp, lcop, q, profit))
    print(f"{name:<18}{gwp:>16.1f}{lcop:>13.1f}{profit:>14.1f}")

# --- 自检：与讲义基准值比对，偏差超过 1% 即报警 ---
gwp0 = rows[0][2]
assert abs(gwp0 - 636.0) / 636.0 < 0.01, f"基准 GWP 复核失败：{gwp0:.1f}"
assert abs(rows[0][3] - 6153.4) / 6153.4 < 0.001, f"基准 LCOP 复核失败：{rows[0][3]:.1f}"

# --- 自检：70% 收率情景下质量守恒（1000 kg 进料 = rPET + HDPE + 废弃物）---
mb70 = mfa(0.70)
assert abs(mb70["pet_kg"] + mb70["hdpe_kg"] + mb70["waste_kg"] - BATCH_IN) < 1e-6

# --- 输出明细表 ---
lca1, tea1 = lca(Y_BASE, EF_ELEC_GREEN), tea(Y_BASE, PRICE_ELEC_GREEN, Q_BASE)
with open(OUT_DIR / "results_summary.csv", "w", encoding="utf-8-sig") as fh:
    fh.write("情景,收率,净碳足迹_kgCO2e_per_t,LCOP_元_per_t,年产量_t,年毛利_万元\n")
    for name, y, gwp, lcop, q, profit in rows:
        fh.write(f"{name},{y:.0%},{gwp:.1f},{lcop:.1f},{q:.0f},{profit:.1f}\n")

print("\n【S1 绿电情景 LCA 清单】(kg CO2e/t)")
for k, v in lca1.items():
    print(f"  {k:<22}{v:>9.2f}")

print("\n【S1 绿电情景 TEA 清单】(元/t)")
for k, v in tea1.items():
    if not k.startswith("_"):
        print(f"  {k:<22}{v:>9.2f}")

# ============================================================
# 六、情景对比图
# ============================================================
names = ["S0\n电网基准\n(Y=80%)", "S1\n绿电\n(Y=80%)",
         "S2\n绿电\n(Y=70%)", "S3\n电网\n(Y=70%)"]
gwps = [r[2] for r in rows]
lcops = [r[3] for r in rows]
colors = ["#8c8c8c", "#2e9e5b", "#e08b2e", "#c0504d"]

fig, axes = plt.subplots(1, 2, figsize=(12, 5.4))
for ax, vals, title, unit, ref in zip(
    axes,
    [gwps, lcops],
    ["净生命周期碳足迹 GWP", "平准化生产成本 LCOP"],
    ["kg CO2e/t rPET", "元/t rPET"],
    [GWP_VIRGIN_PET, None],
):
    bars = ax.bar(names, vals, color=colors, edgecolor="black",
                  linewidth=0.6, width=0.6)
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_ylabel(unit)
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    top = max(vals + ([ref] if ref else []))
    ax.set_ylim(0, top * 1.18)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + top * 0.02,
                f"{v:,.1f}", ha="center", va="bottom", fontsize=9.5)
    if ref:  # 原生 PET 基准参考线
        ax.axhline(ref, color="red", linestyle="--", linewidth=1)
        ax.text(-0.35, ref * 0.97, f"原生 PET 基准 {ref:,.0f}",
                color="red", ha="left", va="top", fontsize=9)

fig.suptitle("PET 机械再生系统多情景 MFA-LCA-TEA 联动结果",
             fontsize=15, fontweight="bold")
fig.tight_layout(rect=(0, 0, 1, 0.93))
fig.savefig(OUT_DIR / "scenario_comparison.png", dpi=300, bbox_inches="tight")
print("\n已生成：results_summary.csv、scenario_comparison.png")
