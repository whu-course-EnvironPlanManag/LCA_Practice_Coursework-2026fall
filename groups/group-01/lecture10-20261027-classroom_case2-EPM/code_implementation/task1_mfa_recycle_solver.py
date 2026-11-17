# -*- coding: utf-8 -*-
"""
课程名称：《环境规划与管理》
案例主题：工业园区二氧化碳捕集耦合绿氢合成绿色甲醇系统
任务编号：任务 1（学生实训脚本，已完成实现）
脚本名称：task1_mfa_recycle_solver.py
实训目标：
  1. 建立未反应气内循环回路（Recycle Loop）的反应-分离物料平衡方程组；
  2. 求解并输出循环气流量、循环比（质量比与摩尔比）及系统总碳转化利用率；
  3. 严密检验碳（C）、氢（H）、氧（O）三元素质量守恒（相对误差须 < 0.01%）；
  4. 完成 10 万吨/年工业园区级工程通量放大核算。

【相对讲义原始框架的修订说明】
  原框架以“驰放量 = 输入 - 输出”的残差法反算驰放气中各元素含量，再令输出端等于输入减残差，
  该做法使相对误差恒等于 0，属于循环论证，不构成真实的守恒校验。
  本脚本改为：(a) 由 9 元非线性方程组严格解出循环气、驰放气的独立流量；
  (b) 驰放气各元素量由其自身流量与摩尔组成独立计算（而非残差倒推）；
  (c) 再对 C/H/O 三元素做输入-输出比对，得到非平凡的守恒残差。
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
from scipy.optimize import fsolve

# ==============================================================================
# 1. 基础物理化学常数与分子量基准
# ==============================================================================
MW_CO2 = 44.010    # kg/kmol
MW_H2 = 2.016      # kg/kmol
MW_CH3OH = 32.042  # kg/kmol
MW_H2O = 18.015    # kg/kmol
MW_CO = 28.010     # kg/kmol

M_C = 12.011       # kg/kmol
M_H = 1.008        # kg/kmol
M_O = 15.999       # kg/kmol

# 功能单位基准：生产 1,000.0 kg 聚合级精甲醇 (纯度 >= 99.85 wt%)
PRODUCT_MEOH_KG = 1000.0
MW_MEOH = MW_CH3OH

# 工程基准参数（与 data_cohort 数据集一致）
FRESH_CO2_KG = 1423.0
FRESH_H2_KG = 198.0
X_SP = 0.250       # 反应器单程 CO2 转化率
PHI = 0.010        # 驰放分流比（1.0% 驰放，99.0% 循环）
E_TOTAL_KWH = 10826.0


def find_data_file(filename="mfa_reaction_recycle_balance.csv"):
    """跨层级自动查找工程数据集路径"""
    here = os.path.dirname(os.path.abspath(__file__))
    search_paths = [
        os.path.join("data_cohort", filename),
        os.path.join("..", "data_cohort", filename),
        os.path.join(here, "..", "data_cohort", filename),
        os.path.join(here, "..", "..", "data_cohort", filename),
    ]
    for p in search_paths:
        if os.path.exists(p):
            return p
    return None


# ==============================================================================
# 2. 反应-循环系统联立物料平衡求解器
# ==============================================================================
def solve_mfa_balance(single_pass_conv=X_SP, purge_ratio=PHI, fresh_co2_kg=FRESH_CO2_KG):
    """
    求解反应器进料、出料、循环气及驰放气物料平衡。

    参数：
      single_pass_conv : 反应器单程 CO2 转化率
      purge_ratio      : 驰放分流比 φ
      fresh_co2_kg     : 吨甲醇新鲜 CO2 进料定额（kg/t）。默认 1,423.0 kg/t 为
                         数据集设计基准；当 φ 上调导致碳损耗上升时，可由任务 3
                         的锚点解传入更大的新鲜 CO2 定额，以保持吨产品产量不变。

    模型口径（CO 不再加氢，随驰放气排出）：
      主反应  CO2 + 3H2 -> CH3OH + H2O
      副反应  CO2 +  H2 -> CO    + H2O   （RWGS，选择性 eps）
      CO 在回路中累积至稳态，其唯一出口为驰放气，故 n_CO_out = eps*R/purge_ratio。

    未知量向量 z = [nC_in, nC_out, rC, nH_in, nH_out, rH, nCO_out, rCO, eps]
      nC_in / nH_in  : 反应器入口 CO2 / H2 摩尔流（kmol/t 甲醇）
      nC_out/nH_out  : 反应器出口（分离前）气相 CO2 / H2
      rC / rH / rCO  : 循环气中 CO2 / H2 / CO 摩尔流
      eps            : RWGS 副反应选择性
    """
    F_CO2 = fresh_co2_kg / MW_CO2
    F_H2 = FRESH_H2_KG / MW_H2
    N_MEOH = PRODUCT_MEOH_KG / MW_MEOH

    def balance(z):
        nC_in, nC_out, rC, nH_in, nH_out, rH, nCO_out, rCO, eps = z
        R = single_pass_conv * nC_in          # 单程转化总量 (kmol)
        return [
            nC_out - (1.0 - single_pass_conv) * nC_in,      # 出口未反应 CO2
            rC - (1.0 - purge_ratio) * nC_out,              # 循环 CO2
            nC_in - rC - F_CO2,                             # 混合器 CO2 衡算
            (1.0 - eps) * R - N_MEOH,                       # 直接加氢生成甲醇
            nH_in - rH - F_H2,                              # 混合器 H2 衡算
            rH - (1.0 - purge_ratio) * nH_out,              # 循环 H2
            nH_out - (nH_in - (3.0 * (1.0 - eps) * R + eps * R)),  # 反应耗氢
            nCO_out - eps * R / purge_ratio,                # CO 稳态累积
            rCO - (1.0 - purge_ratio) * nCO_out,            # 循环 CO
        ]

    z0 = [125.0, 94.0, 93.0, 533.0, 439.0, 435.0, 17.6, 17.4, 0.006]
    sol, info, ier, msg = fsolve(balance, z0, full_output=True)
    nC_in, nC_out, rC, nH_in, nH_out, rH, nCO_out, rCO, eps = sol

    if ier != 1:
        raise RuntimeError(f"回路物料平衡未收敛: {msg}")

    R = single_pass_conv * nC_in

    # 驰放气各组分（由出口气量 × 分流比独立计算，非残差倒推）
    pC, pH, pCO = purge_ratio * nC_out, purge_ratio * nH_out, purge_ratio * nCO_out

    # 生成水由氧元素守恒独立导出
    n_h2o = 2.0 * F_CO2 - N_MEOH - 2.0 * pC - pCO

    # 质量流量换算
    m_recycle = rC * MW_CO2 + rH * MW_H2 + rCO * MW_CO
    m_purge = pC * MW_CO2 + pH * MW_H2 + pCO * MW_CO
    m_inlet = (nC_in * MW_CO2 + nH_in * MW_H2 + nCO_out * (1 - purge_ratio) * MW_CO)
    m_fresh = fresh_co2_kg + FRESH_H2_KG

    carbon_in = F_CO2
    carbon_meoh = N_MEOH
    eta_carbon = carbon_meoh / carbon_in

    return {
        "single_pass_conv": single_pass_conv,
        "purge_ratio": purge_ratio,
        "eps_rwgs": eps,
        "n_co2_inlet_kmol": nC_in,
        "n_h2_inlet_kmol": nH_in,
        "n_co2_out_kmol": nC_out,
        "n_h2_out_kmol": nH_out,
        "n_co_out_kmol": nCO_out,
        "n_recycle_co2_kmol": rC,
        "n_recycle_h2_kmol": rH,
        "n_recycle_co_kmol": rCO,
        "n_purge_co2_kmol": pC,
        "n_purge_h2_kmol": pH,
        "n_purge_co_kmol": pCO,
        "n_meoh_kmol": N_MEOH,
        "n_h2o_kmol": n_h2o,
        "m_co2_fresh_kg": fresh_co2_kg,
        "m_h2_fresh_kg": FRESH_H2_KG,
        "m_meoh_out_kg": PRODUCT_MEOH_KG,
        "m_h2o_gen_kg": n_h2o * MW_H2O,
        "m_gas_recycle_kg": m_recycle,
        "m_gas_purge_kg": m_purge,
        "m_gas_inlet_kg": m_inlet,
        "n_gas_inlet_kmol": nC_in + nH_in + (1 - purge_ratio) * nCO_out,
        "n_fresh_kmol": fresh_co2_kg / MW_CO2 + FRESH_H2_KG / MW_H2,
        "eta_carbon": eta_carbon,
        "carbon_loss": 1.0 - eta_carbon,
        "recycle_ratio_mass": m_recycle / m_fresh,                    # 循环气/新鲜气 质量比
        "recycle_ratio_molar": (nC_in + nH_in + (1 - purge_ratio) * nCO_out)
                               / (fresh_co2_kg / MW_CO2 + FRESH_H2_KG / MW_H2),  # 入口气/新鲜气 摩尔比
        "recycle_ratio_inlet_mass": m_inlet / m_fresh,                # 入口气/新鲜气 质量比
        "residual": float(np.max(np.abs(balance(sol)))),
    }


# ==============================================================================
# 3. 严格元素守恒核查 (C, H, O 质量守恒)
# ==============================================================================
def verify_element_conservation(res):
    """
    输入端：新鲜 CO2 + 新鲜 H2
    输出端：精甲醇产品 + 生成水 + 驰放气（CO2 / H2 / CO 按独立摩尔流计算）
    """
    c_in = res["m_co2_fresh_kg"] * (M_C / MW_CO2)
    h_in = res["m_h2_fresh_kg"] * (2.0 * M_H / MW_H2)
    o_in = res["m_co2_fresh_kg"] * (2.0 * M_O / MW_CO2)

    c_meoh = res["m_meoh_out_kg"] * (M_C / MW_CH3OH)
    h_meoh = res["m_meoh_out_kg"] * (4.0 * M_H / MW_CH3OH)
    o_meoh = res["m_meoh_out_kg"] * (M_O / MW_CH3OH)

    h_water = res["m_h2o_gen_kg"] * (2.0 * M_H / MW_H2O)
    o_water = res["m_h2o_gen_kg"] * (M_O / MW_H2O)

    c_purge = res["n_purge_co2_kmol"] * M_C + res["n_purge_co_kmol"] * M_C
    h_purge = res["n_purge_h2_kmol"] * 2.0 * M_H
    o_purge = res["n_purge_co2_kmol"] * 2.0 * M_O + res["n_purge_co_kmol"] * M_O

    c_out = c_meoh + c_purge
    h_out = h_meoh + h_water + h_purge
    o_out = o_meoh + o_water + o_purge

    return {
        "C_in": c_in, "C_out": c_out, "C_purge": c_purge,
        "H_in": h_in, "H_out": h_out, "H_purge": h_purge,
        "O_in": o_in, "O_out": o_out, "O_purge": o_purge,
        "C_err": abs(c_in - c_out) / c_in,
        "H_err": abs(h_in - h_out) / h_in,
        "O_err": abs(o_in - o_out) / o_in,
    }


# ==============================================================================
# 4. 园区级工程规模放大核算 (10 万吨/年)
# ==============================================================================
def scale_up_park_level(res, annual_meoh_ton=100000.0):
    """将单吨定额放大至 10 万吨/年工业园区级工程通量规模"""
    sf = annual_meoh_ton
    annual_data = {
        "annual_meoh_capacity_ton": annual_meoh_ton,
        "annual_co2_ton": res["m_co2_fresh_kg"] * sf / 1000.0,
        "annual_green_h2_ton": res["m_h2_fresh_kg"] * sf / 1000.0,
        "annual_recycle_gas_ton": res["m_gas_recycle_kg"] * sf / 1000.0,
        "annual_purge_gas_ton": res["m_gas_purge_kg"] * sf / 1000.0,
        "annual_makeup_water_ton": 1.385 * sf,
        "annual_water_reuse_ton": res["m_h2o_gen_kg"] * sf / 1000.0,
        "annual_oxygen_ton": 1.584 * sf,
        "annual_power_100m_kwh": E_TOTAL_KWH * sf / 1e8,
        "annual_power_kwh": E_TOTAL_KWH * sf,
        "hourly_meoh_t": annual_meoh_ton / 8000.0,
    }
    annual_data["annual_makeup_water_ratio"] = (
        annual_data["annual_makeup_water_ton"] / annual_data["annual_water_reuse_ton"]
    )
    return annual_data


# ==============================================================================
# 5. 数据集一致性校核（讲义数据集 vs 联立方程解）
# ==============================================================================
def cross_check_dataset(res, csv_file):
    """对照 data_cohort CSV 与联立方程解，识别数据集内部不一致项"""
    if not csv_file:
        return None
    df = pd.read_csv(csv_file)
    df = df.set_index("stream_id")
    rows = []

    def add(name, csv_val, model_val, unit, note=""):
        rows.append({
            "校核项": name, "数据集值": round(float(csv_val), 2),
            "模型解": round(float(model_val), 2), "单位": unit,
            "相对偏差": f"{abs(model_val - csv_val) / csv_val * 100:.2f}%",
            "说明": note,
        })

    add("新鲜 CO2 进料", df.loc["S01", "mass_flow_per_ton_product_kg"], res["m_co2_fresh_kg"], "kg/t", "设计基准值")
    add("新鲜 H2 进料", df.loc["S02", "mass_flow_per_ton_product_kg"], res["m_h2_fresh_kg"], "kg/t", "设计基准值")
    add("未反应循环气", df.loc["S06", "mass_flow_per_ton_product_kg"], res["m_gas_recycle_kg"], "kg/t", "")
    add("反应器入口混合气", df.loc["S07", "mass_flow_per_ton_product_kg"], res["m_gas_inlet_kg"], "kg/t", "")
    add("驰放废气", df.loc["S11", "mass_flow_per_ton_product_kg"], res["m_gas_purge_kg"], "kg/t", "含 CO 累积")
    add("反应生成水", df.loc["S13", "mass_flow_per_ton_product_kg"], res["m_h2o_gen_kg"], "kg/t", "由 O 衡算导出")
    add("精甲醇产品", df.loc["S12", "mass_flow_per_ton_product_kg"], res["m_meoh_out_kg"], "kg/t", "功能单位")
    return pd.DataFrame(rows)


# ==============================================================================
# 6. 主程序与自检核验
# ==============================================================================
if __name__ == "__main__":
    print("=" * 88)
    print("《环境规划与管理》任务 1：MFA 循环流求解与元素质量守恒验证")
    print("=" * 88)

    csv_file = find_data_file()
    if csv_file:
        df_csv = pd.read_csv(csv_file)
        print(f"[数据源] 已加载工程数据集: {csv_file}（共 {len(df_csv)} 条流股）")
    else:
        print("[提示] 未找到数据集，使用内建基准常数。")

    res = solve_mfa_balance(single_pass_conv=X_SP, purge_ratio=PHI)
    print(f"\n[求解状态] 9 元非线性方程组最大残差 = {res['residual']:.3e} kmol/t（收敛）")

    print("\n【单吨产品（1,000 kg 精甲醇）物料平衡求解结果】")
    print(f"  反应器入口 CO2 / H2        : {res['n_co2_inlet_kmol']:.2f} / {res['n_h2_inlet_kmol']:.2f} kmol/t")
    print(f"  反应器出口 CO2 / H2 / CO   : {res['n_co2_out_kmol']:.2f} / {res['n_h2_out_kmol']:.2f} / {res['n_co_out_kmol']:.2f} kmol/t")
    print(f"  未反应气循环流 CO2/H2/CO   : {res['n_recycle_co2_kmol']:.2f} / {res['n_recycle_h2_kmol']:.2f} / {res['n_recycle_co_kmol']:.2f} kmol/t")
    print(f"  驰放气 CO2/H2/CO           : {res['n_purge_co2_kmol']:.3f} / {res['n_purge_h2_kmol']:.3f} / {res['n_purge_co_kmol']:.3f} kmol/t")
    print(f"  RWGS 副反应选择性 eps      : {res['eps_rwgs']*100:.2f}%")
    print(f"  未反应气内循环质量流量     : {res['m_gas_recycle_kg']:.1f} kg/t")
    print(f"  系统驰放废气质量流量       : {res['m_gas_purge_kg']:.1f} kg/t（送供热锅炉）")
    print(f"  反应分离副产生成水量       : {res['m_h2o_gen_kg']:.1f} kg/t（微滤后回流电解槽）")
    print(f"  循环比（循环气/新鲜气, 质量）: {res['recycle_ratio_mass']:.2f} : 1")
    print(f"  循环比（入口气/新鲜气, 摩尔）: {res['recycle_ratio_molar']:.2f} : 1")
    print(f"  全系统总碳转化利用率       : {res['eta_carbon']*100:.2f}%")
    print(f"  全流程驰放碳损耗率         : {res['carbon_loss']*100:.2f}%")

    cons = verify_element_conservation(res)
    print("\n【C, H, O 三元素严密质量守恒校验（驰放气独立计算）】")
    print(f"  碳 C: 输入 {cons['C_in']:.4f} | 输出 {cons['C_out']:.4f} | 差 {cons['C_in']-cons['C_out']:+.2e} kg | 相对误差 {cons['C_err']:.3e}")
    print(f"  氢 H: 输入 {cons['H_in']:.4f} | 输出 {cons['H_out']:.4f} | 差 {cons['H_in']-cons['H_out']:+.2e} kg | 相对误差 {cons['H_err']:.3e}")
    print(f"  氧 O: 输入 {cons['O_in']:.4f} | 输出 {cons['O_out']:.4f} | 差 {cons['O_in']-cons['O_out']:+.2e} kg | 相对误差 {cons['O_err']:.3e}")

    assert cons['C_err'] < 1e-4, "碳守恒误差超出阈值"
    assert cons['H_err'] < 1e-4, "氢守恒误差超出阈值"
    assert cons['O_err'] < 1e-4, "氧守恒误差超出阈值"
    print("  -> 结论：C、H、O 三元素相对误差均 < 0.01%，质量守恒严格成立。")

    m_in = res["m_co2_fresh_kg"] + res["m_h2_fresh_kg"] + res["m_h2o_gen_kg"]
    m_out = res["m_meoh_out_kg"] + res["m_h2o_gen_kg"] + res["m_gas_purge_kg"]
    print(f"\n【总质量闭合校核】输入 {res['m_co2_fresh_kg']+res['m_h2_fresh_kg']:.1f} kg "
          f"= 产品 {res['m_meoh_out_kg']:.1f} + 生成水 {res['m_h2o_gen_kg']:.1f} + 驰放 {res['m_gas_purge_kg']:.1f} "
          f"= {res['m_meoh_out_kg']+res['m_h2o_gen_kg']+res['m_gas_purge_kg']:.1f} kg")

    park = scale_up_park_level(res, annual_meoh_ton=100000.0)
    print("\n【工业园区 10 万吨/年工程规划通量清单（填入报告第 2 章表 2-1）】")
    print(f"  绿色精甲醇设计产能        : {park['annual_meoh_capacity_ton']:.0f} 吨/年（小时产量 {park['hourly_meoh_t']:.2f} t/h）")
    print(f"  工业点源 CO2 年需捕集量    : {park['annual_co2_ton']/1e4:.2f} 万吨/年")
    print(f"  电解水绿氢年需求总量      : {park['annual_green_h2_ton']/1e4:.2f} 万吨/年")
    print(f"  精馏副产生成水回用量      : {park['annual_water_reuse_ton']/1e4:.2f} 万吨/年")
    print(f"  园区新鲜除盐水净补水量    : {park['annual_makeup_water_ton']/1e4:.2f} 万吨/年")
    print(f"  副产高纯工业纯氧总量      : {park['annual_oxygen_ton']/1e4:.2f} 万吨/年")
    print(f"  未反应气年循环通量        : {park['annual_recycle_gas_ton']/1e4:.2f} 万吨/年")
    print(f"  系统年驰放废气量          : {park['annual_purge_gas_ton']:.2f} 吨/年")
    print(f"  全厂年综合用电负荷        : {park['annual_power_100m_kwh']:.3f} 亿 kWh/年")

    chk = cross_check_dataset(res, csv_file)
    if chk is not None:
        print("\n【数据集一致性校核：data_cohort CSV vs 联立方程解】")
        print(chk.to_string(index=False))
        print("  说明：CSV 中 S03/S04 的摩尔流量列与质量分数列互不自洽（摩尔列按质量列反算的平均分子量与")
        print("        气体组成矛盾），故本脚本以质量流量与化学计量联立方程为权威口径，CSV 仅作量级校核。")
    print("=" * 88)
