# -*- coding: utf-8 -*-
"""
课程名称：《环境规划与管理》
案例主题：工业园区二氧化碳捕集耦合绿氢合成绿色甲醇系统
任务编号：任务 3（学生实训脚本）
脚本名称：task3_pareto_frontier_decision.py
实训目标：
  1. 耦合任务 1 已核验的 MFA 反应-循环物料平衡模型、LCA 净碳足迹模型、TEA 成本模型
     与任务 2 已核验的政策量化算子，全部参数只保留一份来源；
  2. 建立绿电消纳比例 f_green 与循环气驰放分流比 r_purge 二维调控下的双目标优化模型
     （min LCOM_adjusted，min GWP_net）；
  3. 执行 60 x 50 = 3,000 组网格遍历，剔除法规一票否决方案后做非支配排序，提取帕累托前沿；
  4. 以目标空间归一化欧氏距离最小化自动标定帕累托拐点（锚点 B），并提取成本极小锚点 A
     与净碳足迹最小锚点 C（锚点数值全部由数据计算得出，脚本内不预设任何锚点数值）；
  5. 保存全部工况结果、帕累托前沿与三大锚点指标，并输出 300 DPI 决策图
     至 figures_output/fig2_pareto_decision_frontier.png。

================================================================================
【参数口径统一说明】
  物料与电耗：一律调用 task1_mfa_recycle_solver.solve_mfa_balance(X_sp=0.25, r_purge)，
              取模型自身算出的新鲜 CO2、新鲜 H2、副产 O2、循环气量、生成水量与分项电耗，
              不再使用任何"按 eta 反推 1423/198 kg"的替代公式；
  政策参数  ：一律引用 task2_policy_vibe_engine 的常量（含 R_REF、GWP_BENCH_CTM、
              GWP_RED_III、F_GREEN_MIN、FOSSIL_METHANOL_PRICE）与 evaluate_policy_compliance()，
              补贴、碳费用、水费用、环保税、合规状态、调整后 LCOM 与 MAC 全部由该引擎给出；
  LCA 系数  ：取自 data_cohort/lca_grid_scenarios_lci.csv 的清单口径
              （绿电 0.035、区域电网 0.550 kg CO2e/kWh；逸散 15 + 基建 80 = 95 kg CO2e/t；
               CO2 原料固定信用 1.00 kg CO2e/kg；副产 O2 信用 0.06 kg CO2e/kg O2）；
  CO2 固定信用口径（本脚本的修正）：信用只计入"留存于甲醇产品中的净固碳"
              n_meoh x MW_CO2 = 1,373.48 kg CO2/t，即"新鲜 CO2 − 随驰放气重返大气 CO2"；
              不得按新鲜进料全额计信用——否则被驰放的 CO2 既算作已固定、又实际排入大气，
              会使 GWP 随 r_purge 增大而虚假变负（"多驰放更环保"），锚点 C 被推到最大驰放比。
              修正后 GWP_net 仍为负值，这是课程 cradle-to-gate CCU 生产边界下的负 GWP
              （不是 CDR，也不等同于永久负排放）：
              捕集的烟气 CO2 计入避免排放，产品端临时固碳不计使用期再释放（若按
              cradle-to-grave 计入甲醇燃烧释放 n_meoh x MW_CO2，GWP 将回到正值区间）；
              该负号与 data_cohort/lca_grid_scenarios_lci.csv 情景 A（−1,044.12 kg CO2e/t）
              及课程卡片"净负碳示范级 1.2 倍 CCER"（政策分级名称）一致，运行输出"口径对账"段落给出逐项核对。
              注：CCER 激励基数为相对煤制基准的减排量 ΔGHG = (2600 − GWP_net)/1000，
              不是负 GWP 的绝对值（B 方案 ΔGHG ≈ 3.60275 t CO2e/t）；该收益属课程政策模型估算，
              不代表已获得实际核证收入。
  TEA 系数  ：电力结算价序列取自 data_cohort/tea_lcom_sensitivity_data.csv（0.05–0.40 元/kWh 及对应
              electricity_cost / lcom 列）；非电分项分解（基础 CAPEX 年金 835.2、CO2 捕集 260 元/t、
              固定运维 285、水与药剂运维 65、副产 O2 外售 200 元/t O2，按 1,584 kg O2/t 折 316.8 元/t 甲醇）
              为课程脚手架给定的分解口径，CSV 未单列，属模型输入假设，不应标注为数据底座实测值。
  口径差异  ：MFA 模型在 r=1%、X=25% 处的新鲜 CO2 为 1,414.68 kg/t（数据集 1,423）、
              新鲜 H2 为 194.41 kg/t（数据集 198）、电耗 10,637.8 kWh/t（数据集 10,826）。
              本脚本按 MFA 模型绝对值计算，并在运行输出的"口径对账"段落中记录与数据集
              LCA 情景 A/B、TEA 非电成本的偏差，不做任何配平。
================================================================================
"""

import sys
import io
import os

# 针对 Windows 控制台编码环境进行 UTF-8 容错封装
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# 导入任务 1 已核验的物料平衡模型（唯一物料/电耗来源）
try:
    from task1_mfa_recycle_solver import solve_mfa_balance, MW_CO2
except ImportError:                                            # 兼容包内导入方式
    from code_implementation.task1_mfa_recycle_solver import solve_mfa_balance, MW_CO2

# 导入任务 2 已核验的政策量化引擎及其政策常量（唯一政策参数来源）
try:
    from task2_policy_vibe_engine import (
        evaluate_policy_compliance, R_REF, GWP_BENCH_CTM, GWP_RED_III,
        F_GREEN_MIN, STATUS_VETO, R_PURGE_CLEAN_LIMIT,
    )
except ImportError:
    from code_implementation.task2_policy_vibe_engine import (
        evaluate_policy_compliance, R_REF, GWP_BENCH_CTM, GWP_RED_III,
        F_GREEN_MIN, STATUS_VETO, R_PURGE_CLEAN_LIMIT,
    )

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'PingFang SC', 'DejaVu Sans', 'Arial']
plt.rcParams['axes.unicode_minus'] = False
pd.set_option('display.unicode.east_asian_width', True)


# ==============================================================================
# 模块零：统一参数表（仅此处定义一次，下游全部引用）
# ==============================================================================
# 决策变量域与网格分辨率
F_GREEN_MIN_GRID, F_GREEN_MAX_GRID, F_GREEN_STEPS = 0.0, 1.0, 60
R_PURGE_MIN_GRID, R_PURGE_MAX_GRID, R_PURGE_STEPS = 0.004, 0.045, 50

SINGLE_PASS_CONV = 0.250     # 与任务 1 基准口径一致的反应器单程 CO2 转化率

# LCA 清单系数（lca_grid_scenarios_lci.csv）
EF_GREEN = 0.035             # kg CO2e/kWh，绿电
EF_GRID = 0.550              # kg CO2e/kWh，区域电网
GWP_FUGITIVE = 15.0          # kg CO2e/t，吹扫气残余燃烧与微量逸散
GWP_INFRA = 80.0             # kg CO2e/t，电解槽膜电极与催化剂折算
CO2_FIX_CREDIT = 1.00        # kg CO2e/kg，原料 CO2 净固定信用（仅对留存于产品的净固碳计）
O2_CREDIT = 0.06             # kg CO2e/kg O2，副产氧替代深冷空分信用

# TEA 成本系数：电力结算价序列取自 tea_lcom_sensitivity_data.csv（0.05–0.40 元/kWh 及其
# electricity_cost / lcom 列）；以下非电分项 CSV 未单列，为课程脚手架给定口径/模型输入假设，
# 不应标注为数据底座实测值。
P_ELEC_GREEN = 0.18          # 元/kWh，绿电直供
P_ELEC_GRID = 0.42           # 元/kWh，区域电网
CAPEX_BASE = 835.2           # 元/t，基础 CAPEX 年金摊销（不含储能与循环压缩机增量）
STORAGE_CAPEX_COEF = 680.0   # 元/t，绿电波动储能缓冲年金摊销系数
STORAGE_CAPEX_EXP = 2.80
RECYCLE_CAPEX_COEF = 45.0    # 元/t，低驰放比下循环压缩机尺寸增量系数
RECYCLE_CAPEX_EXP = 0.80
CO2_CAPTURE_COST = 260.0     # 元/t CO2，MEA 捕集提纯成本
WATER_OANDM = 65.0           # 元/t 甲醇，水系统与药剂运维（课程脚手架口径，不含水资源税；未拆分冷却补水与工艺水）
FIXED_OM = 285.0             # 元/t 甲醇，固定运维与人工（课程脚手架口径，CSV 未单列）
O2_SALE_PRICE = 200.0        # 元/t O2（模型假设：按 1,584 kg O2/t 折 316.8 元/t 甲醇；tea CSV 未单列该系数）

ANCHOR_DEF = {
    "A": "成本极小方案（财务保守型，近期过渡）",
    "B": "归一化理想点距离最小（帕累托拐点，规划主推基准）",
    "C": "净碳足迹最低方案（课程生产边界最大负 GWP，国际航运绿色外销）",
}


def get_figures_output_dir():
    """跨层级定位 figures_output 目录"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(current_dir, "..", "figures_output"),
        os.path.join("figures_output"),
        os.path.join("..", "figures_output")
    ]
    for d in candidates:
        try:
            os.makedirs(d, exist_ok=True)
            return d
        except Exception:
            continue
    return "."


def get_results_output_dir():
    """跨层级定位 results_output 目录（任务 3 数值结果落盘处）"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(current_dir, "..", "results_output"),
        os.path.join("results_output"),
        os.path.join("..", "results_output")
    ]
    for d in candidates:
        try:
            os.makedirs(d, exist_ok=True)
            return d
        except Exception:
            continue
    return "."


# ==============================================================================
# 模块一：MFA-LCA-TEA-Policy 全链路联动仿真模型
# ==============================================================================
def simulate_park_methanol_system(f_green: float, r_purge: float) -> dict:
    """
    输入决策调控参数，返回该工况的全套物料、碳足迹、成本与政策合规指标。

    参数：
      f_green : 园区风光绿电直供混供消纳比例 [0.0, 1.0]
      r_purge : 循环回路未反应气驰放分流比 [0.004, 0.045]
    返回：
      单条工况记录（dict），键名与结果 CSV 列名一致。
    """
    if not 0.0 <= f_green <= 1.0:
        raise ValueError("绿电消纳比例 f_green 必须位于 [0, 1] 区间")

    # ---------- 1. MFA：任务 1 已核验的反应-循环稳态物料平衡 ----------
    mfa = solve_mfa_balance(single_pass_conv=SINGLE_PASS_CONV, purge_ratio=r_purge)
    fresh_co2_kg = mfa["m_co2_fresh_kg"]
    fresh_h2_kg = mfa["m_h2_fresh_kg"]
    o2_kg = mfa["m_o2_kg"]
    recycle_gas_kg = mfa["m_gas_recycle_kg"]
    purge_gas_kg = mfa["m_gas_purge_kg"]
    gen_water_kg = mfa["m_h2o_gen_kg"]
    e_total_kwh = mfa["e_total_kwh"]
    eta_carbon = mfa["eta_carbon"]

    # ---------- 2. LCA：净碳足迹（电耗间接排放 + 逸散基建 - 净固碳 - O2 替代信用） ----------
    # 净固碳只计留存于产品中的 CO2（= 反应消耗量 = 新鲜 CO2 − 驰放 CO2）；
    # 驰放气带回大气的 CO2 不得再计为已固定，否则 GWP 会随 r_purge 增大而虚假变负。
    purge_co2_kg = mfa["n_co2_purge_kmol"] * MW_CO2        # 随驰放气重返大气（已扣除，不获信用）
    co2_fixed_kg = mfa["n_meoh_kmol"] * MW_CO2             # 化学固定于甲醇产品的净固碳
    ef_blended = f_green * EF_GREEN + (1.0 - f_green) * EF_GRID
    ghg_power = e_total_kwh * ef_blended
    credit_co2 = co2_fixed_kg * CO2_FIX_CREDIT
    credit_o2 = o2_kg * O2_CREDIT
    gwp_net = ghg_power + GWP_FUGITIVE + GWP_INFRA - credit_co2 - credit_o2

    # ---------- 3. TEA：基础平准化成本（不含政策修正项） ----------
    p_elec_blended = f_green * P_ELEC_GREEN + (1.0 - f_green) * P_ELEC_GRID
    cost_elec = e_total_kwh * p_elec_blended
    storage_capex = STORAGE_CAPEX_COEF * (f_green ** STORAGE_CAPEX_EXP)
    recycle_capex = RECYCLE_CAPEX_COEF * max(0.0, (R_REF / r_purge) ** RECYCLE_CAPEX_EXP - 1.0)
    cost_capex = CAPEX_BASE + storage_capex + recycle_capex
    cost_co2 = fresh_co2_kg / 1000.0 * CO2_CAPTURE_COST
    credit_o2_sale = -o2_kg / 1000.0 * O2_SALE_PRICE
    base_lcom = cost_elec + cost_capex + cost_co2 + WATER_OANDM + FIXED_OM + credit_o2_sale

    # ---------- 4. Policy：任务 2 政策量化引擎 ----------
    policy_res = evaluate_policy_compliance(
        gwp_net=gwp_net,
        base_lcom=base_lcom,
        e_total_kwh=e_total_kwh,
        f_green=f_green,
        r_purge=r_purge,
    )
    bd = policy_res["policy_breakdown"]

    return {
        "f_green": f_green,
        "r_purge": r_purge,
        "eta_carbon_pct": eta_carbon * 100.0,
        "fresh_co2_kg_t": fresh_co2_kg,
        "fresh_h2_kg_t": fresh_h2_kg,
        "o2_byproduct_kg_t": o2_kg,
        "recycle_gas_kg_t": recycle_gas_kg,
        "purge_gas_kg_t": purge_gas_kg,
        "gen_water_kg_t": gen_water_kg,
        "e_h2_kwh": mfa["e_h2_kwh"],
        "e_co2_kwh": mfa["e_co2_kwh"],
        "e_recycle_kwh": mfa["e_recycle_kwh"],
        "e_distill_kwh": mfa["e_distill_kwh"],
        "e_total_kwh": e_total_kwh,
        "ef_blended": ef_blended,
        "ghg_power": ghg_power,
        "co2_fixed_kg_t": co2_fixed_kg,
        "purge_co2_kg_t": purge_co2_kg,
        "credit_co2": credit_co2,
        "credit_o2": credit_o2,
        "gwp_net": gwp_net,
        "cost_elec": cost_elec,
        "cost_capex": cost_capex,
        "cost_co2_capture": cost_co2,
        "credit_o2_sale": credit_o2_sale,
        "base_lcom": base_lcom,
        "red_iii_subsidy": bd["red_iii_subsidy"],
        "carbon_cost_mod": bd["carbon_cost_mod"],
        "water_cost_mod": bd["water_cost_mod"],
        "env_tax_mod": bd["env_tax_mod"],
        "water_total_tpt": bd["water_total_tpt"],
        "delta_ghg_t": bd["delta_ghg_t"],
        "lcom_policy_adjusted": policy_res["lcom_policy_adjusted"],
        "mac_policy_adjusted": policy_res["mac_policy_adjusted"],
        "compliance_status": policy_res["compliance_status"],
        "veto_carbon": bd["veto_carbon"],
        "veto_clean_prod": bd["veto_clean_prod"],
    }


# ==============================================================================
# 模块二：非支配排序与三大规划决策锚点提取
# ==============================================================================
def extract_pareto_frontier_and_anchors(df: pd.DataFrame):
    """
    在合规方案中提取帕累托前沿，并标定锚点 A、B、C。

    步骤：
      1. 过滤 compliance_status == 'Redline_Vetoed' 的一票否决方案；
      2. 双目标非支配排序（gwp_net 与 lcom_policy_adjusted 均为最小化方向）；
      3. 在帕累托解集内部做归一化：(x-min)/(max-min)，计算到理想点 (0,0) 的欧氏距离；
      4. A = 成本最小点；B = 归一化距离最小点；C = 净碳足迹最小点。
    返回：
      (pareto_df, anchors_dict)
    """
    valid_df = df[df["compliance_status"] != STATUS_VETO].copy().reset_index(drop=True)
    if valid_df.empty:
        raise ValueError("网格内不存在合规方案，无法提取帕累托前沿")

    points = valid_df[["gwp_net", "lcom_policy_adjusted"]].to_numpy(dtype=float)
    n_pts = points.shape[0]
    is_pareto = np.ones(n_pts, dtype=bool)

    for i in range(n_pts):
        if not is_pareto[i]:
            continue
        # 被支配判据：存在 j 使两个目标均不劣，且至少一个严格更优
        dominated = np.all(points <= points[i], axis=1) & np.any(points < points[i], axis=1)
        if np.any(dominated):
            is_pareto[i] = False

    pareto_df = valid_df[is_pareto].copy().sort_values(by="gwp_net").reset_index(drop=True)

    gwp_min, gwp_max = pareto_df["gwp_net"].min(), pareto_df["gwp_net"].max()
    lcom_min, lcom_max = (pareto_df["lcom_policy_adjusted"].min(),
                          pareto_df["lcom_policy_adjusted"].max())
    span_gwp = max(gwp_max - gwp_min, 1e-12)
    span_lcom = max(lcom_max - lcom_min, 1e-12)

    pareto_df["norm_gwp"] = (pareto_df["gwp_net"] - gwp_min) / span_gwp
    pareto_df["norm_lcom"] = (pareto_df["lcom_policy_adjusted"] - lcom_min) / span_lcom
    pareto_df["utopia_distance"] = np.sqrt(pareto_df["norm_gwp"] ** 2 + pareto_df["norm_lcom"] ** 2)
    pareto_df["anchor_tag"] = "-"

    i_a = pareto_df["lcom_policy_adjusted"].idxmin()    # 成本极小
    i_b = pareto_df["utopia_distance"].idxmin()         # 理想点距离最小（拐点）
    i_c = pareto_df["gwp_net"].idxmin()                 # 净碳足迹最小

    pareto_df.loc[i_a, "anchor_tag"] = "A"
    pareto_df.loc[i_b, "anchor_tag"] = "B"
    pareto_df.loc[i_c, "anchor_tag"] = "C"

    anchors = {
        "A": pareto_df.loc[i_a],
        "B": pareto_df.loc[i_b],
        "C": pareto_df.loc[i_c],
    }
    return pareto_df, anchors


def build_anchor_table(anchors: dict) -> pd.DataFrame:
    """把三大锚点整理为便于写入报告的指标表"""
    rows = []
    for key in ("A", "B", "C"):
        row = anchors[key]
        rows.append({
            "锚点": key,
            "方案定位": ANCHOR_DEF[key],
            "绿电比例 f_green (%)": round(row["f_green"] * 100.0, 2),
            "驰放分流比 r_purge (%)": round(row["r_purge"] * 100.0, 4),
            "总碳利用率 (%)": round(row["eta_carbon_pct"], 2),
            "新鲜 CO2 (kg/t)": round(row["fresh_co2_kg_t"], 2),
            "新鲜绿氢 (kg/t)": round(row["fresh_h2_kg_t"], 2),
            "副产 O2 (kg/t)": round(row["o2_byproduct_kg_t"], 2),
            "综合电耗 (kWh/t)": round(row["e_total_kwh"], 1),
            "取水总量 (t/t)": round(row["water_total_tpt"], 4),
            "净固定 CO2 (kg/t)": round(row["co2_fixed_kg_t"], 2),
            "驰放 CO2 再排放 (kg/t)": round(row["purge_co2_kg_t"], 2),
            "GWP_net (kg CO2e/t)": round(row["gwp_net"], 2),
            "ΔGHG (t CO2e/t)": round(row["delta_ghg_t"], 4),
            "基础 LCOM (元/t)": round(row["base_lcom"], 2),
            "RED III 补贴 (元/t)": round(row["red_iii_subsidy"], 2),
            "碳市场调节 (元/t)": round(row["carbon_cost_mod"], 2),
            "水费用 (元/t)": round(row["water_cost_mod"], 2),
            "环保税 (元/t)": round(row["env_tax_mod"], 2),
            "调整后 LCOM (元/t)": round(row["lcom_policy_adjusted"], 2),
            "MAC (元/t CO2e)": round(row["mac_policy_adjusted"], 2),
            "合规状态": row["compliance_status"],
            "乌托邦归一化距离": round(row["utopia_distance"], 4),
        })
    return pd.DataFrame(rows)


# ==============================================================================
# 模块三：口径对账（与 data_cohort 数据集比对，记录差异但不配平）
# ==============================================================================
def reconcile_with_dataset():
    """在 r=1%、f=1/0 处与 lca_grid_scenarios_lci.csv、tea_lcom_sensitivity_data.csv 对账"""
    data_dir = os.path.join(_HERE, "..", "data_cohort")
    lca_path = os.path.join(data_dir, "lca_grid_scenarios_lci.csv")
    tea_path = os.path.join(data_dir, "tea_lcom_sensitivity_data.csv")
    out = {"f_green_1": None, "f_green_0": None, "dataset": {}, "ok": False}
    if not (os.path.exists(lca_path) and os.path.exists(tea_path)):
        return out

    lca = pd.read_csv(lca_path)
    tea = pd.read_csv(tea_path)
    net_row = lca[lca["lci_inventory_item"] == "Net_Life_Cycle_GWP_Total"].iloc[0]
    out["dataset"]["gwp_a"] = float(net_row["gwp_scenario_a_kgCO2e"])
    out["dataset"]["gwp_b"] = float(net_row["gwp_scenario_b_kgCO2e"])
    # 电价 0.25 元/kWh 行的非电成本作为 TEA 非电基准
    tea_row = tea[tea["electricity_price_rmb_per_kwh"] == 0.25].iloc[0]
    out["dataset"]["nonelec"] = float(tea_row["non_electricity_cost_rmb_per_t"])

    out["f_green_1"] = simulate_park_methanol_system(1.0, R_REF)
    out["f_green_0"] = simulate_park_methanol_system(0.0, R_REF)
    out["ok"] = True
    return out


def _print_reconciliation(rec):
    print("\n" + "-" * 95)
    print("【口径对账】r_purge = 1.0000%（与 data_cohort 数据集同一工程基准点）")
    print("-" * 95)
    if not rec["ok"]:
        print("  未找到 data_cohort 数据集文件，跳过对账（不影响寻优结果）。")
        return
    d = rec["dataset"]
    r1, r0 = rec["f_green_1"], rec["f_green_0"]
    print(f"  MFA 口径     : 新鲜 CO2 {r1['fresh_co2_kg_t']:.2f} kg/t（数据集 S01 1,423.00，"
          f"{(r1['fresh_co2_kg_t']/1423.0-1)*100:+.2f}%）；"
          f"新鲜 H2 {r1['fresh_h2_kg_t']:.2f} kg/t（数据集 S02 198.00，"
          f"{(r1['fresh_h2_kg_t']/198.0-1)*100:+.2f}%）")
    print(f"                  副产 O2 {r1['o2_byproduct_kg_t']:.2f} kg/t（数据集 S05 1,584.00，"
          f"{(r1['o2_byproduct_kg_t']/1584.0-1)*100:+.2f}%）；"
          f"综合电耗 {r1['e_total_kwh']:.1f} kWh/t（数据集 10,826.0，"
          f"{(r1['e_total_kwh']/10826.0-1)*100:+.2f}%）")
    print(f"  LCA 情景 A   : 本模型 {r1['gwp_net']:+.2f} kg CO2e/t（f_green=100%）；数据集 "
          f"{d['gwp_a']:+.2f}，差 {r1['gwp_net']-d['gwp_a']:+.2f}  "
          f"({(r1['gwp_net']-d['gwp_a'])/abs(d['gwp_a'])*100:+.2f}%)")
    print(f"  LCA 情景 B   : 本模型 {r0['gwp_net']:+.2f} kg CO2e/t（f_green=0%）；数据集 "
          f"{d['gwp_b']:+.2f}，差 {r0['gwp_net']-d['gwp_b']:+.2f}  "
          f"({(r0['gwp_net']-d['gwp_b'])/abs(d['gwp_b'])*100:+.2f}%)")
    print("-" * 95)
    print("【GWP 符号与 CO2 固定信用逐项核对】")
    print(f"  电耗间接排放 {r1['ghg_power']:+.2f} + 逸散 {GWP_FUGITIVE:+.2f} + 基建 {GWP_INFRA:+.2f}"
          f" − 净固碳信用 {r1['credit_co2']:.2f} − 副产 O2 信用 {r1['credit_o2']:.2f}"
          f" = {r1['gwp_net']:+.2f} kg CO2e/t")
    print(f"  净固碳 = 反应消耗 {r1['co2_fixed_kg_t']:.2f} kg CO2/t"
          f"（= 新鲜进料 {r1['fresh_co2_kg_t']:.2f} − 随驰放气重返大气 {r1['purge_co2_kg_t']:.2f}）；")
    print(f"  驰放部分不再计为已固定碳，本项修正使 GWP 回升 {r1['purge_co2_kg_t']:+.2f} kg CO2e/t，"
          f"且 GWP 不再随 r_purge 增大而虚假变负。")
    print(f"  GWP<0 为课程 cradle-to-gate CCU 生产边界下的负 GWP（不是 CDR，也不等同于永久负排放），")
    print(f"  非符号错误：捕集的烟气 CO2 计入避免排放，")
    print(f"  产品端固碳在使用期暂不释放；数据集情景 A {d['gwp_a']:+.2f} 同为负值即此口径。")
    print(f"  若改按 cradle-to-grave 计入甲醇使用端燃烧释放 {r1['co2_fixed_kg_t']:.2f} kg CO2e/t，"
          f"则 GWP = {r1['gwp_net']+r1['co2_fixed_kg_t']:+.2f} kg CO2e/t（f_green=100%）。")
    print("-" * 95)
    non_elec = r0["base_lcom"] - r0["cost_elec"]
    print(f"  TEA 非电成本 : 本模型 {non_elec:.2f} 元/t（f_green=0%，不含储能年金）；数据集 "
          f"{d['nonelec']:.2f}，差 {non_elec-d['nonelec']:+.2f} "
          f"({(non_elec-d['nonelec'])/d['nonelec']*100:+.2f}%)")
    print(f"                  f_green=100% 时另计绿电波动储能年金 "
          f"+{r1['cost_capex']-r0['cost_capex']:.2f} 元/t（模型项，数据集未含该项）。")
    print("  LCA 差异来源：① MFA 绝对口径（新鲜 CO2 −0.58%、H2 −1.81%、电耗 −1.74%）；")
    print(f"                ② 固定信用口径（本脚本按净固碳 {r1['co2_fixed_kg_t']:.2f} kg/t 计，"
          f"数据集按新鲜进料 1,423.00 kg/t 全额计，")
    print(f"                   二者之差即驰放再排放 {r1['purge_co2_kg_t']:.2f} kg CO2e/t）；")
    print("  按既定原则记录差异、不做配平，网格寻优使用 MFA 模型绝对值与净固碳信用口径。")


# ==============================================================================
# 模块四：主程序求解、结果落盘与可视化
# ==============================================================================
if __name__ == "__main__":
    print("=" * 95)
    print("《环境规划与管理》任务 3：MFA-LCA-TEA-Policy 多目标寻优与帕累托前沿求解")
    print("=" * 95)
    print(f"[模型接入] 物料与电耗：task1_mfa_recycle_solver.solve_mfa_balance (X_sp = {SINGLE_PASS_CONV:.2f})")
    print(f"[模型接入] 政策与成本修正：task2_policy_vibe_engine.evaluate_policy_compliance")
    print(f"[决策变量] f_green ∈ [{F_GREEN_MIN_GRID:.1f}, {F_GREEN_MAX_GRID:.1f}] × "
          f"r_purge ∈ [{R_PURGE_MIN_GRID:.3f}, {R_PURGE_MAX_GRID:.3f}]，"
          f"网格 {F_GREEN_STEPS} × {R_PURGE_STEPS}")

    # ---------- 1. 网格遍历（60 × 50 = 3,000 组） ----------
    f_green_grid = np.linspace(F_GREEN_MIN_GRID, F_GREEN_MAX_GRID, F_GREEN_STEPS)
    r_purge_grid = np.linspace(R_PURGE_MIN_GRID, R_PURGE_MAX_GRID, R_PURGE_STEPS)
    records = [simulate_park_methanol_system(fg, rp)
               for fg in f_green_grid for rp in r_purge_grid]
    df_all = pd.DataFrame(records)
    print(f"[网格模拟] 共完成 {len(df_all)} 组规划候选工况的全链路仿真。")

    n_veto = int((df_all["compliance_status"] == STATUS_VETO).sum())
    n_red3 = int((df_all["compliance_status"] == "RED_III_RFNBO_Certified").sum())
    n_dom = int((df_all["compliance_status"] == "Domestic_Compliant").sum())
    print(f"[合规筛查] 法规一票否决 {n_veto} 组（碳超基准 "
          f"{int(df_all['veto_carbon'].sum())} 组 + 清洁生产超驰放比 "
          f"{int(df_all['veto_clean_prod'].sum())} 组）；合规 {n_dom + n_red3} 组"
          f"（其中 RED III 认证 {n_red3} 组）。")

    # ---------- 2. 帕累托前沿与三大锚点 ----------
    pareto_df, anchors = extract_pareto_frontier_and_anchors(df_all)
    print(f"[前沿筛选] 剔除否决方案后，提取出 {len(pareto_df)} 个严格非支配帕累托最优解。")
    if pareto_df["f_green"].nunique() == 1:
        print(f"[前沿结构] 前沿全部位于 f_green = {pareto_df['f_green'].iloc[0]*100:.1f}%："
              f"绿电同时降低碳足迹与电费，两目标在该变量上同向占优，")
        print("           前沿退化为 r_purge 单变量一维决策问题（该结论由网格数据自动给出）。")
    print(f"[GWP 校验] 固定信用仅计净固碳 {pareto_df['co2_fixed_kg_t'].iloc[0]:.2f} kg CO2/t"
          f"（驰放气重返大气部分不计信用），前沿上 GWP 随 r_purge 增大而单调变差："
          f"r = {pareto_df['r_purge'].min()*100:.4f}% → {pareto_df['gwp_net'].min():+.2f}；"
          f"r = {pareto_df['r_purge'].max()*100:.4f}% → {pareto_df['gwp_net'].max():+.2f} kg CO2e/t。")
    print(f"           因此深度脱碳锚点 C 落在低驰放侧（r_purge = "
          f"{anchors['C']['r_purge']*100:.4f}%），不再被虚假地推到最大驰放比。")

    # ---------- 3. 三大锚点比选表 ----------
    anchor_table = build_anchor_table(anchors)
    print("\n" + "=" * 95)
    print("【三大规划决策锚点比选数据表（锚点数值由数据计算得出，未预设）】")
    print("=" * 95)
    print(anchor_table.set_index("锚点").T.to_string())
    print("=" * 95)

    # ---------- 4. 结果落盘 ----------
    res_dir = get_results_output_dir()
    all_path = os.path.join(res_dir, "task3_all_scenarios.csv")
    pareto_path = os.path.join(res_dir, "task3_pareto_frontier.csv")
    anchor_path = os.path.join(res_dir, "task3_anchor_metrics.csv")
    df_all.to_csv(all_path, index=False, encoding="utf-8-sig")
    pareto_df.to_csv(pareto_path, index=False, encoding="utf-8-sig")
    anchor_table.to_csv(anchor_path, index=False, encoding="utf-8-sig")
    print(f"\n[结果保存] 全部工况（{len(df_all)} 行 × {df_all.shape[1]} 列） -> {all_path}")
    print(f"[结果保存] 帕累托前沿（{len(pareto_df)} 行）              -> {pareto_path}")
    print(f"[结果保存] 三大锚点指标（3 行）                -> {anchor_path}")

    # ---------- 5. 与数据集口径对账 ----------
    _print_reconciliation(reconcile_with_dataset())

    # ---------- 6. 300 DPI 决策图 ----------
    fig_dir = get_figures_output_dir()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15.4, 6.6))

    df_veto = df_all[df_all["compliance_status"] == STATUS_VETO]
    df_dom = df_all[df_all["compliance_status"] == "Domestic_Compliant"]
    df_red3 = df_all[df_all["compliance_status"] == "RED_III_RFNBO_Certified"]

    styles = {
        "A": ("*", "#1b9e77", 190, "锚点 A：成本极小方案"),
        "B": ("D", "#000000", 150, "锚点 B：归一化理想点拐点（主推）"),
        "C": ("^", "#08519c", 160, "锚点 C：净碳足迹最低方案"),
    }

    # ---------------- 子图 (a)：目标空间 ----------------
    # 红线区：GWP 超过煤制甲醇基准（2,600 kg CO2e/t）即触发一票否决
    ax1.axvspan(GWP_BENCH_CTM, df_all["gwp_net"].max() * 1.02,
                color="#f4a582", alpha=0.10, zorder=0)
    ax1.text(df_all["gwp_net"].max() * 0.98, 0.955,
             "超煤制基准\n一票否决区", transform=ax1.get_xaxis_transform(),
             fontsize=7.4, color="#b2182b", va="top", ha="right", zorder=2)
    ax1.scatter(df_veto["gwp_net"], df_veto["lcom_policy_adjusted"], c="#d95f02", marker="x",
                s=12, alpha=0.30, linewidths=0.8,
                label=f"法规一票否决方案（{len(df_veto)} 组）")
    ax1.scatter(df_dom["gwp_net"], df_dom["lcom_policy_adjusted"], c="#7570b3", marker="o",
                s=12, alpha=0.30, linewidths=0,
                label=f"国内合规被支配方案（{len(df_dom)} 组）")
    ax1.scatter(df_red3["gwp_net"], df_red3["lcom_policy_adjusted"], c="#66a61e", marker="o",
                s=14, alpha=0.40, linewidths=0,
                label=f"RED III 认证方案（{len(df_red3)} 组）")
    ax1.plot(pareto_df["gwp_net"], pareto_df["lcom_policy_adjusted"], color="#e7298a",
             linewidth=2.6, zorder=8,
             label=f"有效帕累托前沿（{len(pareto_df)} 个非支配解）")
    ax1.axvline(GWP_BENCH_CTM, color="#b2182b", linestyle="--", linewidth=1.2,
                label=f"煤制甲醇基准（+{GWP_BENCH_CTM:.0f} kg CO$_2$e/t）")
    ax1.axvline(GWP_RED_III, color="#1b7837", linestyle="-.", linewidth=1.2,
                label=f"RED III 准入限值（+{GWP_RED_III:.2f} kg CO$_2$e/t）")
    ax1.axvline(0.0, color="#525252", linestyle=":", linewidth=1.0,
                label="零碳平衡线（GWP<0：课程生产边界负 GWP，非 CDR）")

    for k, (marker, color, size, lbl) in styles.items():
        pt = anchors[k]
        ax1.scatter(pt["gwp_net"], pt["lcom_policy_adjusted"], marker=marker, c=color, s=size,
                    edgecolors="white", linewidth=1.4, zorder=10, label=lbl)

    ax1.set_title("(a) 政策规制约束下的 LCOM–GWP 目标空间与帕累托前沿",
                  fontsize=11.5, fontweight="bold", pad=12)
    ax1.set_xlabel("全生命周期净碳足迹 GWP$_{net}$ (kg CO$_2$e / t 甲醇)", fontsize=10.5)
    ax1.set_ylabel("政策调整后净平准化成本 LCOM$_{adjusted}$ (元 / t 甲醇)", fontsize=10.5)
    ax1.grid(True, linestyle=":", alpha=0.5)
    ax1.legend(loc="upper left", fontsize=7.0, ncol=2, framealpha=0.95,
               borderpad=0.5, handletextpad=0.5, columnspacing=0.9)

    # 前沿放大窗（避免前沿被否决区压缩后不可辨）
    axin = ax1.inset_axes([0.485, 0.085, 0.475, 0.415])
    axin.set_facecolor("white")
    axin.set_zorder(5)
    axin.scatter(df_red3["gwp_net"], df_red3["lcom_policy_adjusted"], c="#66a61e", s=10,
                 alpha=0.35, linewidths=0, zorder=1)
    axin.scatter(df_dom["gwp_net"], df_dom["lcom_policy_adjusted"], c="#7570b3", s=10,
                 alpha=0.35, linewidths=0, zorder=1)
    axin.plot(pareto_df["gwp_net"], pareto_df["lcom_policy_adjusted"], color="#e7298a",
              linewidth=2.4, zorder=8)
    for k, (marker, color, size, _) in styles.items():
        pt = anchors[k]
        axin.scatter(pt["gwp_net"], pt["lcom_policy_adjusted"], marker=marker, c=color, s=size * 0.42,
                     edgecolors="white", linewidth=1.2, zorder=10)
        axin.annotate(k, xy=(pt["gwp_net"], pt["lcom_policy_adjusted"]),
                      xytext=(6, 6), textcoords="offset points", fontsize=9.0,
                      fontweight="bold", color=color, zorder=11)
    x_lo, x_hi = pareto_df["gwp_net"].min(), pareto_df["gwp_net"].max()
    y_lo, y_hi = pareto_df["lcom_policy_adjusted"].min(), pareto_df["lcom_policy_adjusted"].max()
    axin.set_xlim(x_lo - 0.25 * (x_hi - x_lo) - 5, x_hi + 0.25 * (x_hi - x_lo) + 5)
    axin.set_ylim(y_lo - 0.30 * (y_hi - y_lo), y_hi + 0.30 * (y_hi - y_lo))
    axin.tick_params(labelsize=7.0)
    axin.grid(True, linestyle=":", alpha=0.5)
    axin.set_xlabel("GWP$_{net}$ (kg CO$_2$e/t)", fontsize=7.2, labelpad=1.5)
    axin.set_ylabel("LCOM$_{adj}$ (元/t)", fontsize=7.2, labelpad=1.5)
    axin.set_title("前沿放大（决策锚点区）", fontsize=8.4, pad=4)

    # ---------------- 子图 (b)：决策变量空间 ----------------
    # 红线区：r_purge 超过清洁生产上限即触发一票否决
    ax2.axhspan(R_PURGE_CLEAN_LIMIT * 100.0, R_PURGE_MAX_GRID * 100.0 * 1.22,
                color="#f4a582", alpha=0.12, zorder=0)
    ax2.text(102.0, R_PURGE_CLEAN_LIMIT * 100.0 + 0.10, "清洁生产红线区（一票否决）",
             fontsize=7.2, color="#b2182b", va="bottom", ha="right", zorder=2)
    ax2.scatter(df_all["f_green"] * 100.0, df_all["r_purge"] * 100.0, c="#d9d9d9", s=7,
                alpha=0.55, linewidths=0,
                label=f"全部 {len(df_all)} 组网格工况")
    ax2.scatter(df_dom["f_green"] * 100.0, df_dom["r_purge"] * 100.0, c="#7570b3", s=13,
                alpha=0.55, linewidths=0, label=f"国内合规（被支配，{len(df_dom)} 组）")
    ax2.scatter(df_red3["f_green"] * 100.0, df_red3["r_purge"] * 100.0, c="#66a61e", s=13,
                alpha=0.55, linewidths=0, label=f"RED III 认证（{len(df_red3)} 组）")
    ax2.axvline(F_GREEN_MIN * 100.0, color="#1b7837", linestyle="-.", linewidth=1.2,
                label=f"RED III 绿电门槛（{F_GREEN_MIN*100:.0f}%）")
    ax2.axhline(R_PURGE_CLEAN_LIMIT * 100.0, color="#b2182b", linestyle="--", linewidth=1.2,
                label=f"清洁生产红线（r$_{{purge}}$ > {R_PURGE_CLEAN_LIMIT*100:.1f}%）")
    ax2.scatter(pareto_df["f_green"] * 100.0, pareto_df["r_purge"] * 100.0, marker="o", s=34,
                facecolors="none", edgecolors="#e7298a", linewidths=1.5, zorder=9,
                label=f"帕累托前沿解（{len(pareto_df)} 个）")
    for k, (marker, color, size, lbl) in styles.items():
        pt = anchors[k]
        ax2.scatter(pt["f_green"] * 100.0, pt["r_purge"] * 100.0, marker=marker, c=color, s=size,
                    edgecolors="white", linewidth=1.4, zorder=10, label=lbl)

    if pareto_df["f_green"].nunique() == 1:
        ax2.text(0.02, 0.02,
                 f"网格寻优结果：帕累托前沿解全部位于 f$_{{green}}$ = "
                 f"{pareto_df['f_green'].iloc[0]*100:.1f}%\n"
                 f"（绿电同时降低电费与碳足迹，两目标在该变量上同向占优，\n"
                 f"前沿退化为 r$_{{purge}}$ 单变量一维决策）",
                 transform=ax2.transAxes, fontsize=7.6, va="bottom", ha="left", color="#222222",
                 bbox=dict(boxstyle="round,pad=0.35", facecolor="white", edgecolor="#999999",
                           alpha=0.92), zorder=12)

    ax2.set_xlim(-4.0, 104.0)
    ax2.set_ylim(0.0, R_PURGE_MAX_GRID * 100.0 * 1.22)
    ax2.set_title("(b) 决策变量空间：3,000 组网格工况分布与前沿解位置",
                  fontsize=11.5, fontweight="bold", pad=12)
    ax2.set_xlabel("园区风光绿电直供消纳比例 f$_{green}$ (%)", fontsize=10.5)
    ax2.set_ylabel("未反应气循环回路驰放分流比 r$_{purge}$ (%)", fontsize=10.5)
    ax2.grid(True, linestyle=":", alpha=0.5)
    ax2.legend(loc="upper center", fontsize=6.4, ncol=4, framealpha=0.95, borderpad=0.45,
               handletextpad=0.5, columnspacing=0.8)

    plt.tight_layout()
    output_png = os.path.join(fig_dir, "fig2_pareto_decision_frontier.png")
    plt.savefig(output_png, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"[图表输出] 帕累托决策图（300 DPI）已生成至：{output_png}")
    print("=" * 95)
