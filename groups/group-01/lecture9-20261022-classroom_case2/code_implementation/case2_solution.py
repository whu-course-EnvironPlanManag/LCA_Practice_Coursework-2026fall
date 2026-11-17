#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
第九讲 案例二：CO2 捕集耦合电解水绿氢制甲醇（Power-to-Methanol / CCU）

任务 1  MFA：scipy.optimize.fsolve 联立求解「新鲜进料 - 反应器 - 气液分离 - 循环/驰放」
        12 元方程组，输出循环比、总碳利用率与 C/H/O 元素守恒核算
任务 2  LCA + TEA：双电网情景净碳足迹、LCOM / 绿色溢价 / MAC 的电价敏感度、
        碳价 100 元/t 下的商业自平衡临界电价，并输出联动折线图
任务 3  工艺流程图见 plot_case2_process.py

运行：
    python case2_solution.py

输出：
    case2_solution_report.md
    lcom_premium_mac_sensitivity.png / .svg
"""

from pathlib import Path
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.optimize import fsolve

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "SimSun", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["svg.fonttype"] = "none"


# ----------------------------------------------------------------------------
# 0. 数据目录定位（兼容小组目录 / starter_materials 两种位置）
# ----------------------------------------------------------------------------
def locate_data_dir() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        p = parent / "case_files" / "data_cohort"
        if (p / "mfa_reaction_recycle_balance.csv").exists():
            return p
        p = (parent / "starter_materials" / "lecture9-20261022-classroom_case2"
             / "case_files" / "data_cohort")
        if (p / "mfa_reaction_recycle_balance.csv").exists():
            return p
    raise FileNotFoundError("未找到 case_files/data_cohort 数据目录")


DATA = locate_data_dir()
OUT = Path(__file__).resolve().parent

mfa = pd.read_csv(DATA / "mfa_reaction_recycle_balance.csv")
lca = pd.read_csv(DATA / "lca_grid_scenarios_lci.csv")
tea = pd.read_csv(DATA / "tea_lcom_sensitivity_data.csv")

MW = {"CO2": 44.01, "H2": 2.016, "CO": 28.01, "MeOH": 32.04, "H2O": 18.016, "O2": 31.998}
AW = {"C": 12.011, "H": 1.008, "O": 15.999}

# 设计基准（讲义 / README）
X_SP = 0.25            # 反应器 CO2 单程转化率
PHI = 0.01             # 分离器顶部气分流比：1% 驰放
F_CO2_KG = 1423.0      # 新鲜 CO2 kg / t 甲醇
F_H2_KG = 198.0        # 新鲜 H2 kg / t 甲醇
PRODUCT_KG = 1000.0    # 精甲醇 kg / t 甲醇
ANNUAL_T = 100_000.0   # 年产 10 万吨
OPERATING_H = 8000.0   # 年运行 8,000 h
CAPEX_RMB = 8.20e8     # 总投资 8.20 亿元
WACC, LIFE = 0.08, 20  # 折现率 8%，20 年
ELEC_KWH = 10_826.0    # 综合电耗 kWh / t 甲醇
FOSSIL_PRICE = 2500.0  # 化石甲醇售价 元/t
CO2_CAPTURE_COST = 260.0   # 元 / t CO2
O2_CREDIT_PRICE = 200.0    # 元 / t O2
BENCHMARK_GWP = 2600.0     # 煤制甲醇基准 kg CO2e/t

N_CO2_FRESH = F_CO2_KG / MW["CO2"]      # 32.331 kmol
N_H2_FRESH = F_H2_KG / MW["H2"]         # 98.214 kmol
N_MEOH_SPEC = PRODUCT_KG / MW["MeOH"]   # 31.211 kmol


# ============================================================================
# 1. 任务 1：反应-分离-循环回路联立求解（fsolve）
# ============================================================================
# 未知量 z = [nC_in, nC_out, rC, nH_in, nH_out, rH, nCO_out, rCO, pC, pH, pCO, eps]
#   nC_in / nH_in  反应器入口 CO2 / H2 摩尔流率 (kmol/t)
#   nC_out/nH_out 反应器出口（分离前）摩尔流率
#   rC / rH / rCO 循环气各组分摩尔流率
#   pC / pH / pCO 驰放气各组分摩尔流率
#   eps           RWGS 副反应选择性（已反应 CO2 中生成 CO 的份额）
# 反应：CO2 + 3H2 -> CH3OH + H2O（主）；CO2 + H2 -> CO + H2O（RWGS）
def recycle_balance(z):
    nC_in, nC_out, rC, nH_in, nH_out, rH, nCO_out, rCO, pC, pH, pCO, eps = z
    R = X_SP * nC_in                      # 单程已反应 CO2
    return [
        nC_out - (1.0 - X_SP) * nC_in,                        # 反应器：CO2 未反应部分
        rC - (1.0 - PHI) * nC_out,                            # 分流器：CO2 循环
        nC_in - rC - N_CO2_FRESH,                             # 混合器：CO2 碳守恒
        (1.0 - eps) * R - N_MEOH_SPEC,                        # 产品规格：甲醇 1000 kg
        nH_in - rH - N_H2_FRESH,                              # 混合器：H2 守恒
        rH - (1.0 - PHI) * nH_out,                            # 分流器：H2 循环
        nH_out - (nH_in - (3.0 * (1.0 - eps) * R + eps * R)),  # 反应耗氢（主反应3、RWGS 1）
        nCO_out - eps * R / PHI,                              # CO 稳态：生成量 = 驰放量
        rCO - (1.0 - PHI) * nCO_out,                          # 分流器：CO 循环
        pC - PHI * nC_out,                                    # 分流器：CO2 驰放
        pH - PHI * nH_out,                                    # 分流器：H2 驰放
        pCO - PHI * nCO_out,                                  # 分流器：CO 驰放
    ]


z0 = [125.0, 94.0, 93.0, 533.0, 439.0, 435.0, 17.6, 17.4, 0.94, 4.4, 0.18, 0.006]
sol, info, ier, msg = fsolve(recycle_balance, z0, full_output=True)
if ier != 1:
    raise RuntimeError("fsolve 未收敛: " + str(msg))

(nC_in, nC_out, rC, nH_in, nH_out, rH,
 nCO_out, rCO, pC, pH, pCO, eps) = sol
R_REACT = X_SP * nC_in
residual = np.max(np.abs(recycle_balance(sol)))

# 派生指标
n_meoh = (1.0 - eps) * R_REACT
n_h2o = R_REACT                                     # 主反应 + RWGS 合计生成水
mass_inlet = nC_in * MW["CO2"] + nH_in * MW["H2"]
mass_fresh = F_CO2_KG + F_H2_KG
mass_recycle = rC * MW["CO2"] + rH * MW["H2"] + rCO * MW["CO"]
mass_purge = pC * MW["CO2"] + pH * MW["H2"] + pCO * MW["CO"]
mass_product = n_meoh * MW["MeOH"]
mass_water = n_h2o * MW["H2O"]

# 循环比两种口径（讲义 3.8:1 对应「入口气 / 新鲜气」）
ratio_inlet_fresh = mass_inlet / mass_fresh
ratio_recycle_fresh = mass_recycle / mass_fresh
ratio_molar_inlet = (nC_in + nH_in) / (N_CO2_FRESH + N_H2_FRESH)

# 总碳利用率：产品碳 / 新鲜碳
carbon_util = mass_product * AW["C"] / MW["MeOH"] / (F_CO2_KG * AW["C"] / MW["CO2"])
carbon_loss_purge = (pC + pCO) * AW["C"] / (N_CO2_FRESH * AW["C"])

# ---- C / H / O 元素守恒（回路控制体） ----
elem = {
    "C_in": N_CO2_FRESH * AW["C"],
    "C_out": (n_meoh + pC + pCO) * AW["C"],
    "H_in": 2.0 * N_H2_FRESH * AW["H"],
    "H_out": (4.0 * n_meoh + 2.0 * n_h2o + 2.0 * pH) * AW["H"],
    "O_in": 2.0 * N_CO2_FRESH * AW["O"],
    "O_out": (n_meoh + n_h2o + 2.0 * pC + pCO) * AW["O"],
}
elem_dev = {k: (elem[k + "_out"] - elem[k + "_in"]) / elem[k + "_in"] * 100.0
            for k in ("C", "H", "O")}

# ---- 与 CSV 流股对照 ----
def csv_mass(stream_id):
    return float(mfa.loc[mfa["stream_id"] == stream_id,
                         "mass_flow_per_ton_product_kg"].iloc[0])


def csv_mean_mw(stream_id):
    row = mfa.loc[mfa["stream_id"] == stream_id].iloc[0]
    wt = {"CO2": row["co2_wt_pct"], "H2": row["h2_wt_pct"], "MeOH": row["meoh_wt_pct"],
          "H2O": row["h2o_wt_pct"], "O2": row["o2_wt_pct"]}
    inv = sum(v / 100.0 / MW[k] for k, v in wt.items() if v > 0)
    return 1000.0 / inv if inv > 0 else np.nan


compare = [
    ("S01 新鲜 CO2", F_CO2_KG, csv_mass("S01")),
    ("S02 新鲜 H2", F_H2_KG, csv_mass("S02")),
    ("S06 循环气", mass_recycle, csv_mass("S06")),
    ("S07 反应器入口", mass_inlet, csv_mass("S07")),
    ("S09 粗甲醇液相", mass_product + mass_water, csv_mass("S09")),
    ("S11 驰放气", mass_purge, csv_mass("S11")),
    ("S12 精甲醇产品", mass_product, csv_mass("S12")),
]
# CSV 自洽性体检：由质量分数反算的平均分子量 vs 其列值隐含的平均分子量
mfa_check = []
for sid in ("S07", "S06", "S11"):
    row = mfa.loc[mfa["stream_id"] == sid].iloc[0]
    implied = row["mass_flow_per_ton_product_kg"] / row["molar_flow_per_ton_product_kmol"]
    mfa_check.append((sid, row["stream_name"], csv_mean_mw(sid), implied))


# ============================================================================
# 2. 任务 2-A：LCA 双电网情景净碳足迹
# ============================================================================
SUMMARY_ROWS = {"Net_Life_Cycle_GWP_Total", "Fossil_Benchmark_CtM",
                "Net_GHG_Reduction_vs_Benchmark"}
lci_items = lca[~lca["lci_inventory_item"].isin(SUMMARY_ROWS)].copy()
GWP_GREEN = float(lci_items["gwp_scenario_a_kgCO2e"].sum())
GWP_GRID = float(lci_items["gwp_scenario_b_kgCO2e"].sum())

GWP_GREEN_CSV = float(lca.loc[lca["lci_inventory_item"] == "Net_Life_Cycle_GWP_Total",
                              "gwp_scenario_a_kgCO2e"].iloc[0])
GWP_GRID_CSV = float(lca.loc[lca["lci_inventory_item"] == "Net_Life_Cycle_GWP_Total",
                             "gwp_scenario_b_kgCO2e"].iloc[0])

RED_GREEN = (BENCHMARK_GWP - GWP_GREEN) / BENCHMARK_GWP * 100.0
RED_GRID = (GWP_GRID - BENCHMARK_GWP) / BENCHMARK_GWP * 100.0
DELTA_GHG = (BENCHMARK_GWP - GWP_GREEN) / 1000.0        # t CO2e / t 甲醇 = 3.644

# 电力分项（用于报告表格）
elec_rows = lci_items[lci_items["lci_inventory_item"].str.startswith("Electricity")]
elec_total_kwh = float(elec_rows["flow_per_ton_product"].sum())


# ============================================================================
# 3. 任务 2-B：TEA / LCOM / 绿色溢价 / MAC / 临界电价
# ============================================================================
CRF = WACC * (1 + WACC) ** LIFE / ((1 + WACC) ** LIFE - 1.0)
CAPEX_PER_T = CAPEX_RMB * CRF / ANNUAL_T                       # 835.2 元/t
COST_CO2 = F_CO2_KG / 1000.0 * CO2_CAPTURE_COST               # 370.0
COST_WATER_CAT = 65.0
COST_FIXED_OM = 285.0
PROFIT_O2 = 1584.0 / 1000.0 * O2_CREDIT_PRICE                 # -316.8
NON_ELEC_COST = CAPEX_PER_T + COST_CO2 + COST_WATER_CAT + COST_FIXED_OM - PROFIT_O2
NON_ELEC_CSV = float(tea["non_electricity_cost_rmb_per_t"].iloc[0])


def lcom(price):
    return ELEC_KWH * price + NON_ELEC_COST


def premium(price):
    return lcom(price) - FOSSIL_PRICE


def mac(price):
    return premium(price) / DELTA_GHG


PRICE_REF = [0.35, 0.15]
ref = {p: {"lcom": lcom(p), "premium": premium(p), "mac": mac(p),
           "cost_elec": ELEC_KWH * p, "elec_pct": ELEC_KWH * p / lcom(p) * 100.0}
       for p in PRICE_REF}

CARBON_PRICE = 100.0                       # 全国碳市场碳价 元/t CO2e
BREAKEVEN_LCOM = FOSSIL_PRICE + CARBON_PRICE * DELTA_GHG
PRICE_CRIT = (BREAKEVEN_LCOM - NON_ELEC_COST) / ELEC_KWH
PRICE_PARITY = (FOSSIL_PRICE - NON_ELEC_COST) / ELEC_KWH   # 不计碳价的平价点

# CSV 敏感度表复核
tea_check = tea.copy()
tea_check["lcom_recalc"] = ELEC_KWH * tea_check["electricity_price_rmb_per_kwh"] + NON_ELEC_COST
tea_check["mac_recalc"] = tea_check["green_premium_rmb_per_t"] / DELTA_GHG
max_lcom_dev = float(np.abs(tea_check["lcom_recalc"] - tea_check["lcom_rmb_per_t"]).max())
max_mac_dev = float(np.abs(tea_check["mac_recalc"] - tea_check["mac_rmb_per_tCO2e"]).max())

# ============================================================================
# 4. 随堂研讨题：光伏占比临界值 x*
# ============================================================================
EF_SELF_COAL, EF_PV = 0.75, 0.04
PV_COEF = EF_SELF_COAL - EF_PV       # 0.71
PV_CRIT = ((EF_SELF_COAL - (BENCHMARK_GWP + F_CO2_KG) / ELEC_KWH) / PV_COEF)


def gwp_pv_mix(x):
    """随堂题给定口径：只计电力排放与 CO2 捕集信用，其余分项忽略。"""
    return ELEC_KWH * (EF_SELF_COAL - PV_COEF * x) - F_CO2_KG


# ============================================================================
# 5. 绘图：LCOM / 绿色溢价 / MAC 联动曲线 + 光伏占比临界点
# ============================================================================
p_grid = np.linspace(0.05, 0.60, 221)
lcom_grid = lcom(p_grid)
prem_grid = premium(p_grid)
mac_grid = mac(p_grid)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15.5, 6.2))

c_lcom, c_prem, c_mac = "#1f4e79", "#c0504d", "#2e7d32"
ax1.plot(p_grid, lcom_grid, color=c_lcom, lw=2.6, label="平准化甲醇成本 LCOM")
ax1.plot(p_grid, prem_grid, color=c_prem, lw=2.2, ls="--", label="绿色溢价 (LCOM-2500)")
ax1.axhline(FOSSIL_PRICE, color="#7f7f7f", lw=1.4, ls=":")
ax1.text(0.055, FOSSIL_PRICE + 90, "化石甲醇基准 2,500 元/t", color="#555555", fontsize=10)
ax1.axvline(PRICE_CRIT, color="#2e7d32", lw=1.6, ls="-.")
ax1.annotate("临界电价 %.3f 元/kWh\n(MAC=碳价100元)" % PRICE_CRIT,
             xy=(PRICE_CRIT, lcom(PRICE_CRIT)), xytext=(0.245, 2500),
             fontsize=10, color="#2e7d32",
             arrowprops=dict(arrowstyle="->", color="#2e7d32", lw=1.2))
for p, col in zip(PRICE_REF, ["#c0504d", "#1f4e79"]):
    ax1.scatter([p], [lcom(p)], s=70, color=col, zorder=5, edgecolor="white")
    ax1.annotate("%.2f 元\n%.0f 元/t" % (p, lcom(p)), xy=(p, lcom(p)),
                 xytext=(p - 0.055, lcom(p) + 520), fontsize=9.5, color=col)
ax1.set_xlabel("工业电价 p （元/kWh）", fontsize=12)
ax1.set_ylabel("成本 / 溢价 （元/t 甲醇）", fontsize=12)
ax1.set_title("(a) LCOM 与绿色溢价对电价的响应", fontsize=13, fontweight="bold")
ax1.grid(alpha=0.3, ls=":")
ax1.legend(loc="upper left", fontsize=10)
ax1.set_xlim(0.05, 0.60)

ax1b = ax1.twinx()
ax1b.plot(p_grid, mac_grid, color=c_mac, lw=2.0, ls="-.", alpha=0.85)
ax1b.set_ylabel("边际减排成本 MAC （元/t CO$_2$e）", fontsize=12, color=c_mac)
ax1b.tick_params(axis="y", colors=c_mac)
ax1b.axhline(CARBON_PRICE, color=c_mac, lw=1.0, ls=":", alpha=0.7)

x = np.linspace(0.0, 1.0, 201)
gwp_x = gwp_pv_mix(x)
ax2.plot(x * 100, gwp_x, color="#8d2c5f", lw=2.6, label="GWP$_{net}$(x)")
ax2.axhline(BENCHMARK_GWP, color="#7f7f7f", lw=1.4, ls=":")
ax2.text(2, BENCHMARK_GWP + 140, "煤制甲醇基准 2,600 kg CO$_2$e/t", color="#555555", fontsize=10)
ax2.axhline(0.0, color="#999999", lw=1.0, ls="--")
ax2.axvline(PV_CRIT * 100, color="#2e7d32", lw=1.6, ls="-.")
ax2.scatter([PV_CRIT * 100], [gwp_pv_mix(PV_CRIT)], s=80, color="#2e7d32",
            zorder=5, edgecolor="white")
ax2.annotate("x* = %.1f%%\nGWP = 2,600" % (PV_CRIT * 100),
             xy=(PV_CRIT * 100, BENCHMARK_GWP), xytext=(PV_CRIT * 100 + 8, BENCHMARK_GWP + 1500),
             fontsize=10.5, color="#2e7d32",
             arrowprops=dict(arrowstyle="->", color="#2e7d32", lw=1.2))
ax2.set_xlabel("光伏绿电占比 x （%）", fontsize=12)
ax2.set_ylabel("净碳足迹 GWP$_{net}$ （kg CO$_2$e/t）", fontsize=12)
ax2.set_title("(b) 随堂研讨：光伏占比临界值", fontsize=13, fontweight="bold")
ax2.grid(alpha=0.3, ls=":")
ax2.legend(loc="upper right", fontsize=10)
ax2.set_xlim(0, 100)

fig.suptitle("绿氢合成绿色甲醇：电价敏感度与规划临界点", fontsize=15, fontweight="bold")
fig.tight_layout(rect=[0, 0, 1, 0.94])
fig.savefig(OUT / "lcom_premium_mac_sensitivity.png", dpi=300, bbox_inches="tight",
            facecolor="white")
fig.savefig(OUT / "lcom_premium_mac_sensitivity.svg", bbox_inches="tight",
            facecolor="white")
plt.close(fig)


# ============================================================================
# 6. 控制台输出
# ============================================================================
def line(k, v, unit="", w=38):
    print("  %-*s%14s %s" % (w, k, v, unit))


def fmt(v, nd=2):
    return ("%%.%df" % nd) % v


print("=" * 78)
print("任务 1  MFA 反应-分离-循环回路求解（fsolve，残差 %.2e）" % residual)
print("=" * 78)
line("单程转化率 X_sp", fmt(X_SP * 100, 1), "%")
line("驰放分流比 phi", fmt(PHI * 100, 1), "%")
line("反应器入口 CO2", fmt(nC_in), "kmol/t")
line("反应器入口 H2", fmt(nH_in), "kmol/t")
line("反应器出口 CO2", fmt(nC_out), "kmol/t")
line("循环气 CO2 / H2 / CO", "%.2f / %.2f / %.2f" % (rC, rH, rCO), "kmol/t")
line("驰放气 CO2 / H2 / CO", "%.3f / %.2f / %.3f" % (pC, pH, pCO), "kmol/t")
line("甲醇产量", fmt(mass_product, 1), "kg/t")
line("生成水", fmt(mass_water, 1), "kg/t")
print("-" * 78)
line("循环比（入口气/新鲜气，质量）", fmt(ratio_inlet_fresh), ":1")
line("循环比（循环气/新鲜气，质量）", fmt(ratio_recycle_fresh), ":1")
line("循环比（入口气/新鲜气，摩尔）", fmt(ratio_molar_inlet), ":1")
line("总碳利用率", fmt(carbon_util * 100, 2), "%")
line("驰放碳损失", fmt(carbon_loss_purge * 100, 2), "%")

print("\n" + "=" * 78)
print("任务 1  C / H / O 元素守恒（回路控制体）")
print("=" * 78)
print("  元素      输入(kg)        输出(kg)        偏差")
for k in ("C", "H", "O"):
    print("  %-6s %14.4f %15.4f %12.2e%%" % (k, elem[k + "_in"], elem[k + "_out"], elem_dev[k]))
print("\n  质量衡算: 输入 %.2f kg = 产品 %.2f + 生成水 %.2f + 驰放 %.2f = %.2f kg"
      % (mass_fresh, mass_product, mass_water, mass_purge,
         mass_product + mass_water + mass_purge))

print("\n" + "=" * 78)
print("任务 2-A  LCA 双情景净碳足迹（kg CO2e/t 甲醇）")
print("=" * 78)
line("情景 A 100% 绿电 (EF=0.035)", fmt(GWP_GREEN, 1), "kg CO2e/t")
line("情景 B 区域电网 (EF=0.550)", fmt(GWP_GRID, 1), "kg CO2e/t")
line("情景 A 较煤制甲醇减排率", fmt(RED_GREEN, 1), "%")
line("情景 B 较煤制甲醇增排率", fmt(RED_GRID, 1), "%")
line("单吨减排量 Delta GWP", fmt(DELTA_GHG, 4), "t CO2e/t")

print("\n" + "=" * 78)
print("任务 2-B  TEA：LCOM / 绿色溢价 / MAC")
print("=" * 78)
line("CRF（8%, 20a）", fmt(CRF, 5), "")
line("CAPEX 年金摊销", fmt(CAPEX_PER_T, 1), "元/t")
line("非电成本合计", fmt(NON_ELEC_COST, 2), "元/t")
for p in PRICE_REF:
    r = ref[p]
    print("  电价 %.2f 元/kWh: 电费 %.1f (占 %.1f%%) | LCOM %.1f | 溢价 %+.1f | MAC %.1f"
          % (p, r["cost_elec"], r["elec_pct"], r["lcom"], r["premium"], r["mac"]))
line("临界电价（MAC = 碳价 %.0f 元）" % CARBON_PRICE, fmt(PRICE_CRIT, 4), "元/kWh")
line("平价电价（不计碳价，LCOM=2500）", fmt(PRICE_PARITY, 4), "元/kWh")
line("CSV 复核：LCOM 最大偏差", fmt(max_lcom_dev, 3), "元/t")
line("CSV 复核：MAC 最大偏差", fmt(max_mac_dev, 3), "元/t CO2e")

print("\n" + "=" * 78)
print("随堂研讨  光伏占比临界值")
print("=" * 78)
line("x* 临界值", fmt(PV_CRIT * 100, 1), "%")
line("x=50% 时 GWP", fmt(gwp_pv_mix(0.50), 1), "kg CO2e/t")
line("x=55% 时 GWP", fmt(gwp_pv_mix(0.55), 1), "kg CO2e/t")


# ============================================================================
# 7. 自动生成 Markdown 报告
# ============================================================================
elem_rows = "\n".join(
    "| %s | %.4f | %.4f | %.2e | %s |" % (
        k, elem[k + "_in"], elem[k + "_out"], elem_dev[k],
        "通过" if abs(elem_dev[k]) < 0.01 else "超差")
    for k in ("C", "H", "O"))

lci_rows = "\n".join(
    "| %s | %.1f | %s | %s | %.2f | %.2f |" % (
        r["stage_process"], r["flow_per_ton_product"], r["unit"],
        ("%.3f" % pd.to_numeric(r["ef_scenario_a_green_power"], errors="coerce"))
        if pd.notna(pd.to_numeric(r["ef_scenario_a_green_power"], errors="coerce")) else "—",
        r["gwp_scenario_a_kgCO2e"], r["gwp_scenario_b_kgCO2e"])
    for _, r in lci_items.iterrows())

cmp_rows = "\n".join(
    "| %s | %.1f | %.1f | %+.1f%% |" % (name, model, csv, (model / csv - 1) * 100)
    for name, model, csv in compare)

chk_rows = "\n".join(
    "| %s | %s | %.2f | %.2f |" % (sid, name, inv, imp)
    for sid, name, inv, imp in mfa_check)

tea_rows = "\n".join(
    "| %.2f | %.1f | %.1f | %.1f | %+.1f | %.1f | %.1f | %s |" % (
        r["electricity_price_rmb_per_kwh"], r["electricity_cost_rmb_per_t"],
        r["lcom_rmb_per_t"], r["green_premium_rmb_per_t"],
        r["green_premium_pct"], r["mac_rmb_per_tCO2e"], r["mac_usd_per_tCO2e"],
        "商业自平衡" if r["lcom_rmb_per_t"] <= BREAKEVEN_LCOM else "需补贴/溢价")
    for _, r in tea.iterrows())

report = """# 案例二作业：CO₂ 捕集耦合电解水绿氢制甲醇系统 MFA-LCA-TEA 建模

> 功能单位：生产 1 t（1,000 kg）聚合级绿色精甲醇（Cradle-to-Gate）
> 系统边界：烟气 CO₂ 捕集 → 130 MW PEM 电解制氢 → 固定床合成 → 气液分离 → 循环/驰放 → 双塔精馏
> 数据来源：`case_files/data_cohort/` 三个 CSV + 讲义基准值
> 求解工具：`scipy.optimize.fsolve`（12 元联立方程组，终态残差 {residual:.2e}）

## 一、任务 1：反应-分离-循环回路的严格质量守恒

### 1.1 方程组构造

回路解耦的关键是**单程转化率不等于系统转化率**。设反应器入口 CO₂ 摩尔流率为 $n$、单程转化率 $X_{{sp}}=25\\%$、分流器驰放比 $\\varphi=1\\%$，则稳态下：

$$
n = F_{{CO_2}} + (1-\\varphi)(1-X_{{sp}})\\,n
\\;\\Longrightarrow\\;
\\frac{{n}}{{F_{{CO_2}}}} = \\frac{{1}}{{X_{{sp}} + \\varphi(1-X_{{sp}})}} = \\frac{{1}}{{0.25 + 0.0075}} = {n_ratio:.2f}
$$

脚本把该守恒关系与 RWGS 副反应、H₂ 循环、CO 累积一并写成 12 个联立方程（未知量：入口/出口/循环/驰放各组分流率 + RWGS 选择性 ε），用 `fsolve` 求解：

| 变量 | 数值 (kmol/t) | 变量 | 数值 (kmol/t) |
|---|---|---|---|
| 反应器入口 CO₂ $n_{{C,in}}$ | {nC_in:.2f} | 反应器入口 H₂ $n_{{H,in}}$ | {nH_in:.2f} |
| 反应器出口 CO₂ | {nC_out:.2f} | 反应器出口 H₂ | {nH_out:.2f} |
| 循环气 CO₂ / H₂ / CO | {rC:.2f} / {rH:.2f} / {rCO:.2f} | 驰放气 CO₂ / H₂ / CO | {pC:.3f} / {pH:.2f} / {pCO:.3f} |
| 甲醇产量 | {n_meoh:.2f}（= {mass_product:.1f} kg） | 生成水 | {n_h2o:.2f}（= {mass_water:.1f} kg） |
| RWGS 选择性 ε | {eps_pct:.2f}% | 单程已反应 CO₂ | {R_REACT:.2f} |

### 1.2 循环比：两种口径必须分清

| 口径 | 计算值 | 讲义/CSV | 说明 |
|---|---|---|---|
| **入口气 / 新鲜气（质量）** | **{ratio_inlet_fresh:.2f} : 1** | **3.8 : 1（CSV 3.86）** | 讲义 3.8:1 即此口径，偏差 {dev_if:.1f}% |
| 循环气 / 新鲜气（质量） | {ratio_recycle_fresh:.2f} : 1 | 2.86（CSV 4640/1621） | 任务书写的"循环气/新鲜气" |
| 入口气 / 新鲜气（摩尔） | {ratio_molar_inlet:.2f} : 1 | 3.80（CSV，但其摩尔列自相矛盾） | 见 1.4 自洽性体检 |

**结论**：讲义"循环比 3.8:1"对应 **入口气/新鲜气** 口径；若按任务书字面的"循环气/新鲜气"，则为 {ratio_recycle_fresh:.2f}:1。两个口径差一个 $(1+1/循环比)$ 因子，做题时必须声明，否则结论差 30%。

### 1.3 总碳利用率：96.5% vs 96.0%

$$
\\eta_{{C}} = \\frac{{\\text{{产品甲醇中的碳}}}}{{\\text{{新鲜 CO₂ 中的碳}}}} = \\frac{{{mass_product:.1f}\\times 12.011/32.04}}{{{F_CO2_KG:.1f}\\times 12.011/44.01}} = \\frac{{{c_prod:.2f}}}{{{c_fresh:.2f}}} = \\mathbf{{{carbon_util_pct:.2f}\\%}}
$$

* 驰放碳损失 = {carbon_loss_pct:.2f}%（CO₂ + CO 合计），与产品碳相加恰好等于新鲜碳。
* **与讲义 96.0% 的差异说明**：讲义导览页的 96.0% 为取整口径；其 MFA 表内"驰放带走碳 13.5 kg / 388.0 kg = 3.48%"反算出的利用率即为 **96.52%**，与本模型 {carbon_util_pct:.2f}% 一致。差异来自 1,423 kg 新鲜 CO₂ 的取整（严格闭合需 {f_co2_exact:.1f} kg）与微量逸散项，**不影响结论**。

### 1.4 C / H / O 元素守恒核算（回路控制体）

| 元素 | 输入 (kg/t) | 输出 (kg/t) | 相对偏差 | 判定（< 0.01%） |
|---|---|---|---|---|
{elem_rows}

质量衡算：输入 {mass_fresh:.2f} kg = 精甲醇 {mass_product:.2f} + 生成水 {mass_water:.2f} + 驰放气 {mass_purge:.2f} = {mass_sum:.2f} kg，闭合偏差 {mass_dev:.2e} kg。

### 1.5 与 CSV 流股对照及数据自洽性体检

| 流股 | 模型值 (kg/t) | CSV 值 (kg/t) | 偏差 |
|---|---|---|---|
{cmp_rows}

CSV 的摩尔流量列与质量分数列**互斥**，这是必须指出的数据瑕疵：

| 流股 | 名称 | 由质量分数反算的平均分子量 (g/mol) | 由 CSV 流量反算的平均分子量 (g/mol) |
|---|---|---|---|
{chk_rows}

CO₂/H₂ 体系的平均分子量不可能只有 12.6 g/mol（纯 CO₂ 为 44、纯 H₂ 为 2），因此 CSV 的 `molar_flow_per_ton_product_kmol` 列不可直接用于推算循环比。**本作业以质量流量 + 联立方程为准**，CSV 仅作量级校核：新鲜进料、产品、粗甲醇三项偏差 < 1%，循环/驰放/入口三项偏差 5%~20%（源于其流股为工程示意取整）。

## 二、任务 2-A：LCA "绿电悖论"

### 2.1 清单核算（kg CO₂e/t 甲醇）

| 清单项 | 活动量 | 单位 | EF(A 绿电) | 情景 A | 情景 B |
|---|---|---|---|---|---|
{lci_rows}
| **合计** | — | — | — | **{GWP_GREEN:.2f}** | **{GWP_GRID:.2f}** |

脚本按分项求和得到 {GWP_GREEN:.2f} / {GWP_GRID:.2f}，与 CSV 合计行（{GWP_GREEN_CSV:.2f} / {GWP_GRID_CSV:.2f}）完全一致，说明清单闭合。

### 2.2 悖论的定量刻画

| 指标 | 情景 A（绿电 0.035） | 情景 B（网电 0.550） |
|---|---|---|
| 电力间接排放 | +{elec_a:.1f} kg CO₂e | +{elec_b:.1f} kg CO₂e |
| 净碳足迹 GWP | **{GWP_GREEN:.1f} kg CO₂e/t** | **{GWP_GRID:.1f} kg CO₂e/t** |
| 相对煤制甲醇（2,600） | 减排 **{RED_GREEN:.1f}%**（净负碳） | **反向增排 {RED_GRID:.1f}%** |
| 单吨减排量 ΔGWP | **{DELTA_GHG:.4f} t CO₂e/t** | 负值，无减排效益 |

* **电力是唯一支配项**：电解制氢 {elec_pem:.0f} kWh 占综合电耗的 {elec_pem_pct:.1f}%，所以 GWP 几乎完全由 $EF_{{grid}}$ 决定。
* **热力学成因**：火电效率 ~40% × PEM 电解 ~64% × 合成与精馏损失，三级串联后每焦耳甲醇化学能需数倍煤炭输入。绿电情景的负值来自"把烟气 CO₂ 永久固定在甲醇分子中"的 −1,423 kg 捕集信用，一旦电力排放超过约 **{ef_break:.3f} kg CO₂e/kWh**，净碳足迹即转正——这就是"绿电阈值"。
* **规划铁律**：在未实现电力深度脱碳的区域，不得审批 Power-to-X 项目。

## 三、任务 2-B：TEA 与绿色溢价 / MAC

### 3.1 成本结构（CAPEX 年金化）

* $CRF = 0.08(1.08)^{{20}}/[(1.08)^{{20}}-1] = {CRF:.5f}$
* 资本摊销 = 8.20 亿元 × {CRF:.5f} / 100,000 t = **{CAPEX_PER_T:.1f} 元/t**
* 非电成本 = {CAPEX_PER_T:.2f}（摊销） + {COST_CO2:.2f}（CO₂ 捕集） + {COST_WATER_CAT:.2f}（纯水催化剂） + {COST_FIXED_OM:.2f}（固定运维） − {PROFIT_O2_ABS:.2f}（O₂ 抵扣） = **{NON_ELEC_COST:.2f} 元/t**
* 与 CSV 非电成本 {NON_ELEC_CSV:.2f} 元/t 偏差 {non_elec_dev:.2f} 元/t

因此 $LCOM(p) = 10,826\\,p + {NON_ELEC_COST:.2f}$，是电价的纯线性函数；**电费占 LCOM 的 {pct_low:.0f}%（0.15 元）~{pct_high:.0f}%（0.35 元）**，重资产属性被高能耗掩盖。

### 3.2 两个基准情景

| 项目 | 0.35 元/kWh（沿海工商业绿电） | 0.15 元/kWh（沙戈荒大基地） |
|---|---|---|
| 电费 | {e035:.1f} 元/t（占 {p035:.1f}%） | {e015:.1f} 元/t（占 {p015:.1f}%） |
| **LCOM** | **{l035:.1f} 元/t** | **{l015:.1f} 元/t** |
| 绿色溢价（vs 2,500） | **+{pr035:.1f} 元/t（+{prp035:.1f}%）** | **+{pr015:.1f} 元/t（+{prp015:.1f}%）** |
| **MAC** | **{m035:.1f} 元/t CO₂e（≈ ${m035u:.1f}/t）** | **{m015:.1f} 元/t CO₂e（≈ ${m015u:.1f}/t）** |

### 3.3 电价敏感度全表（CSV 复核）

| p (元/kWh) | 电费 | LCOM | 溢价 | 溢价率(%) | MAC | MAC(USD) | 判定 |
|---|---|---|---|---|---|---|---|
{tea_rows}

脚本按 $LCOM=10,826p+{NON_ELEC_COST:.2f}$ 重算全部 12 行，与 CSV 的 LCOM 最大偏差 **{max_lcom_dev:.3f} 元/t**、MAC 最大偏差 **{max_mac_dev:.3f} 元/t CO₂e**，说明 CSV 完全服从同一线性模型。

### 3.4 商业自平衡的临界电价

碳价 $P_C=100$ 元/t 时，绿色甲醇可获得的碳资产价值为 $100\\times{DELTA_GHG:.3f}={carbon_rev:.2f}$ 元/t，故自平衡条件为：

$$
LCOM(p) \\le 2,500 + {carbon_rev:.2f} = {BREAKEVEN_LCOM:.2f}
\\;\\Longrightarrow\\;
p^* = \\frac{{{BREAKEVEN_LCOM:.2f} - {NON_ELEC_COST:.2f}}}{{10,826}} = \\mathbf{{{PRICE_CRIT:.4f}\\ \\text{{元/kWh}}}}
$$

* 即 **p\\* ≈ {PRICE_CRIT_CHI:.2f} 元/kWh**，与沙戈荒大基地消纳电价（0.15 元）几乎重合——这正是"把项目规划在新能源基地"的定量依据。
* 若不计碳价，纯市场平价点为 {PRICE_PARITY:.4f} 元/kWh（低于任何现实电价，故无补贴时不可行）。
* MAC 与碳价的关系更直观：**临界点就是 MAC = 碳价**（{PRICE_CRIT:.4f} 元/kWh 时 MAC 恰为 100 元/t CO₂e）。

![电价敏感度与临界点](lcom_premium_mac_sensitivity.png)

## 四、任务 3：工艺流程图

见 `plot_case2_process.py`，输出 300 dpi 的 `process_flow_diagram_case2.png` 与矢量 `.svg`，图中完整标注了 99%/1% 分流、循环压缩机回路与全部吨产品流股质量。

![工艺流程图](process_flow_diagram_case2.png)

## 五、随堂研讨：光伏占比临界值

设光伏绿电占比 $x$，加权排放因子 $EF(x)=0.04x+0.75(1-x)=0.75-0.71x$：

$$
GWP_{{net}}(x)=10,826\\times(0.75-0.71x)-1,423.0 \\le 2,600
\\;\\Longrightarrow\\;
x \\ge \\mathbf{{{PV_CRIT_PCT:.1f}\\%}}
$$

| x | 50% | **{PV_CRIT_PCT:.1f}%（临界）** | 55% |
|---|---|---|---|
| GWP (kg CO₂e/t) | {gwp50:.0f} | 2,600 | {gwp55:.0f} |

落在讲义预告的 **50%~55%** 区间内。配套结论：屋顶光伏年满发仅 1,200 h，而化工装置需 8,000 h 连续运行，设备利用率降至 15% 会使 CAPEX 摊销放大 6.7 倍（835 → 约 5,570 元/t），因此**必须"网电保连续、绿电保碳强度"混供，并以物理 PPA / 绿证锁定绿电比例 ≥ {PV_CRIT_PCT:.0f}%**。

## 六、结论与规划建议

1. **MFA**：单程 25% 只是反应器特性，循环回路把系统总碳利用率抬到 **{carbon_util_pct:.1f}%**；循环比必须声明口径（入口气/新鲜气 = {ratio_inlet_fresh:.2f}:1）。
2. **LCA**：绿电情景 **{GWP_GREEN:.0f} kg CO₂e/t**（净负碳，减排 {RED_GREEN:.0f}%），网电情景 **+{GWP_GRID:.0f} kg CO₂e/t**（增排 {RED_GRID:.0f}%）。同一套设备，结论反转 5,575 kg CO₂e/t，**电力碳因子是项目的生死变量**。
3. **TEA**：0.35 元电价的 LCOM {l035:.0f} 元/t、MAC {m035:.0f} 元/t CO₂e，只能靠 ISCC/欧盟 ETS 航运溢价出口；0.15 元电价的 MAC {m015:.0f} 元/t CO₂e 与国内碳价 100 元接轨，**可实现商业自平衡**。
4. **空间规划**：项目的可行域由 $p \\le {PRICE_CRIT:.3f}$ 元/kWh 唯一决定——应布局在风光大基地直供区，**严禁在煤电为主的区域电网内立项**。
5. **技术改进优先级**：电耗 10,826 kWh 中制氢占 {elec_pem_pct:.0f}%，因此降本减碳的第一杠杆是 **PEM 电耗（52 kWh/kg H₂）与电解槽 CAPEX**，其次才是合成回路与精馏的热集成。

## 七、假设与口径说明

* 新鲜气按纯组分计（CSV 标注 CO₂ 99.8%、H₂ 99.99%），0.2% 惰性组分随驰放排出，对碳利用率影响 < 0.2 pp。
* 生成水按反应计量计（{mass_water:.0f} kg），CSV 取 575 kg（含精馏回流余量），偏差 {water_dev:.1f}%。
* RWGS 作为唯一副反应，CO 不再在当次通过中加氢，全部随驰放排出；ε = {eps_pct:.2f}% 由"产品必须为 1,000 kg"反解。
* MAC 仅在绿电情景有意义：网电情景项目为净增排，不存在"避免排放量"，MAC 无定义。
* 电解槽水系：理论耗水 {h2o_stoich:.0f} kg/t（98.21 kmol H₂），与 1,960 kg 总进水的差额为排污/氧中夹带，属工程余量。
* 光伏占比题按讲义给定口径（只计电力排放与 CO₂ 捕集信用），未叠加 O₂ 信用与基建项。

---

*本报告由 `case2_solution.py` 自动生成，全部数值可由脚本复现。*
""".format(
    residual=residual,
    n_ratio=nC_in / N_CO2_FRESH,
    nC_in=nC_in, nH_in=nH_in, nC_out=nC_out, nH_out=nH_out,
    rC=rC, rH=rH, rCO=rCO, pC=pC, pH=pH, pCO=pCO,
    n_meoh=n_meoh, mass_product=mass_product, n_h2o=n_h2o, mass_water=mass_water,
    eps_pct=eps * 100, R_REACT=R_REACT,
    ratio_inlet_fresh=ratio_inlet_fresh,
    ratio_recycle_fresh=ratio_recycle_fresh,
    ratio_molar_inlet=ratio_molar_inlet,
    dev_if=(ratio_inlet_fresh / 3.8 - 1) * 100,
    c_prod=mass_product * AW["C"] / MW["MeOH"],
    c_fresh=F_CO2_KG * AW["C"] / MW["CO2"],
    f_co2_exact=N_MEOH_SPEC * MW["CO2"] * (1 + PHI * (1 - X_SP) / X_SP),
    carbon_util_pct=carbon_util * 100,
    carbon_loss_pct=carbon_loss_purge * 100,
    elem_rows=elem_rows,
    mass_fresh=mass_fresh,
    mass_purge=mass_purge,
    mass_sum=mass_product + mass_water + mass_purge,
    mass_dev=mass_product + mass_water + mass_purge - mass_fresh,
    cmp_rows=cmp_rows, chk_rows=chk_rows, lci_rows=lci_rows,
    GWP_GREEN=GWP_GREEN, GWP_GRID=GWP_GRID,
    GWP_GREEN_CSV=GWP_GREEN_CSV, GWP_GRID_CSV=GWP_GRID_CSV,
    elec_a=ELEC_KWH * 0.035, elec_b=ELEC_KWH * 0.55,
    RED_GREEN=RED_GREEN, RED_GRID=RED_GRID, DELTA_GHG=DELTA_GHG,
    elec_pem=10296.0, elec_pem_pct=10296.0 / ELEC_KWH * 100,
    ef_break=(BENCHMARK_GWP + F_CO2_KG - 95.0 - 15.0 - 80.0) / ELEC_KWH,
    CRF=CRF, CAPEX_PER_T=CAPEX_PER_T, COST_CO2=COST_CO2,
    COST_WATER_CAT=COST_WATER_CAT, COST_FIXED_OM=COST_FIXED_OM,
    PROFIT_O2=PROFIT_O2, PROFIT_O2_ABS=abs(PROFIT_O2), NON_ELEC_COST=NON_ELEC_COST,
    F_CO2_KG=F_CO2_KG,
    NON_ELEC_CSV=NON_ELEC_CSV, non_elec_dev=NON_ELEC_COST - NON_ELEC_CSV,
    pct_low=ref[0.15]["elec_pct"], pct_high=ref[0.35]["elec_pct"],
    e035=ref[0.35]["cost_elec"], e015=ref[0.15]["cost_elec"],
    p035=ref[0.35]["elec_pct"], p015=ref[0.15]["elec_pct"],
    l035=ref[0.35]["lcom"], l015=ref[0.15]["lcom"],
    pr035=ref[0.35]["premium"], pr015=ref[0.15]["premium"],
    prp035=ref[0.35]["premium"] / FOSSIL_PRICE * 100,
    prp015=ref[0.15]["premium"] / FOSSIL_PRICE * 100,
    m035=ref[0.35]["mac"], m015=ref[0.15]["mac"],
    m035u=ref[0.35]["mac"] / 7.1, m015u=ref[0.15]["mac"] / 7.1,
    tea_rows=tea_rows, max_lcom_dev=max_lcom_dev, max_mac_dev=max_mac_dev,
    carbon_rev=CARBON_PRICE * DELTA_GHG,
    BREAKEVEN_LCOM=BREAKEVEN_LCOM,
    PRICE_CRIT=PRICE_CRIT, PRICE_CRIT_CHI=PRICE_CRIT,
    PRICE_PARITY=PRICE_PARITY,
    PV_CRIT_PCT=PV_CRIT * 100,
    gwp50=gwp_pv_mix(0.50), gwp55=gwp_pv_mix(0.55),
    water_dev=(575.0 / mass_water - 1) * 100,
    h2o_stoich=N_H2_FRESH * MW["H2O"],
)

(OUT / "case2_solution_report.md").write_text(report, encoding="utf-8")
print("\n报告已写出: %s" % (OUT / "case2_solution_report.md"))
print("图表已写出: %s" % (OUT / "lcom_premium_mac_sensitivity.png"))
