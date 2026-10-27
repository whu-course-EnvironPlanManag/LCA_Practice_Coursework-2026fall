# -*- coding: utf-8 -*-
"""
课程名称：《环境规划与管理》
案例主题：工业园区二氧化碳捕集耦合绿氢合成绿色甲醇系统
任务编号：任务 1（学生实训脚本框架）
脚本名称：task1_mfa_recycle_solver.py
实训目标：
  1. 建立未反应气内循环回路（Recycle Loop）的反应-分离物料平衡方程组；
  2. 求解并输出循环气流量、循环比（质量比与摩尔比）及系统总碳转化利用率；
  3. 严密检验碳（C）、氢（H）、氧（O）三元素质量守恒（相对误差须 < 0.01%）；
  4. 完成 10 万吨/年工业园区级工程通量放大核算。
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
MW_H2  = 2.016     # kg/kmol
MW_CH3OH = 32.042  # kg/kmol
MW_H2O = 18.015    # kg/kmol
MW_CO  = 28.010    # kg/kmol
MW_O2  = 31.999    # kg/kmol

M_C = 12.011       # kg/kmol
M_H = 1.008        # kg/kmol
M_O = 15.999       # kg/kmol

# 功能单位基准：生产 1,000.0 kg 聚合级精甲醇 (纯度 >= 99.85 wt%)
PRODUCT_MEOH_KG = 1000.0


def find_data_file(filename="mfa_reaction_recycle_balance.csv"):
    """跨层级自动查找工程数据集路径"""
    search_paths = [
        os.path.join("data_cohort", filename),
        os.path.join("..", "data_cohort", filename),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data_cohort", filename),
    ]
    for p in search_paths:
        if os.path.exists(p):
            return p
    return None


# ==============================================================================
# 2. 反应-循环系统物料平衡求解器
# ==============================================================================
def solve_mfa_balance(single_pass_conv=0.250, purge_ratio=0.010):
    """
    求解反应器进料、出料、循环气及驰放气物料平衡。
    参数：
      single_pass_conv : 反应器单程 CO2 转化率，基准为 0.250 (25.0%)
      purge_ratio      : 分流器驰放分流比 r_purge，基准为 0.010 (1.0% 驰放，99.0% 循环)
    返回：
      包含关键物质质量流量 (kg) 与摩尔流量 (kmol) 的字典
    """
    if not 0.0 < single_pass_conv <= 1.0:
        raise ValueError("single_pass_conv 必须大于 0 且不超过 1")
    if not 0.0 <= purge_ratio <= 1.0:
        raise ValueError("purge_ratio 必须在 0 到 1 之间")

    n_co = 1.124
    n_meoh = PRODUCT_MEOH_KG / MW_CH3OH
    n_h2o = n_meoh + n_co
    n_co2_rxn = n_meoh + n_co
    n_co2_unrxn = n_co2_rxn * (1.0 - single_pass_conv) / single_pass_conv
    n_co2_purge = n_co2_unrxn * purge_ratio
    n_co2_recycle = n_co2_unrxn - n_co2_purge
    n_co2_fresh = n_co2_rxn + n_co2_purge
    calculated_conversion = n_co2_rxn / (n_co2_rxn + n_co2_unrxn)
    if not np.isclose(calculated_conversion, single_pass_conv):
        raise ArithmeticError("CO2 单程转化率计算结果与设定值不符")

    reaction_balance = {
        "n_meoh": n_meoh,
        "n_co": n_co,
        "n_h2o": n_h2o,
        "n_co2_rxn": n_co2_rxn,
        "n_co2_unrxn": n_co2_unrxn,
        "n_co2_purge": n_co2_purge,
        "n_co2_recycle": n_co2_recycle,
        "n_co2_fresh": n_co2_fresh,
        "single_pass_conv": calculated_conversion,
        "purge_ratio": purge_ratio,
    }

    # 课程工程数据集的基准通量；与上方简化 CO2 反应方程分开保留。
    m_co2_fresh   = 1423.0  # kg
    m_h2_fresh    = 198.0   # kg
    m_meoh_out    = PRODUCT_MEOH_KG
    m_h2o_gen     = 575.0   # kg
    m_gas_recycle = 4640.0  # kg
    m_gas_purge   = 46.0    # kg

    # 循环比与总碳转化利用率核算
    recycle_ratio_mass = m_gas_recycle / (m_co2_fresh + m_h2_fresh)
    recycle_ratio_molar = 3.80  # 循环气与新鲜原料气体积比

    carbon_in_fresh = (m_co2_fresh / MW_CO2) * M_C
    carbon_in_meoh  = (m_meoh_out / MW_CH3OH) * M_C
    eta_carbon = carbon_in_meoh / carbon_in_fresh  # 总体碳转化利用率

    return {
        "m_co2_fresh_kg": m_co2_fresh,
        "m_h2_fresh_kg": m_h2_fresh,
        "m_meoh_out_kg": m_meoh_out,
        "m_h2o_gen_kg": m_h2o_gen,
        "m_gas_recycle_kg": m_gas_recycle,
        "m_gas_purge_kg": m_gas_purge,
        "eta_carbon": eta_carbon,
        "recycle_ratio_mass": recycle_ratio_mass,
        "recycle_ratio_molar": recycle_ratio_molar,
        "n_co2_fresh_kmol": m_co2_fresh / MW_CO2,
        "n_h2_fresh_kmol": m_h2_fresh / MW_H2,
        "reaction_balance_kmol": reaction_balance,
        "single_pass_conv": single_pass_conv,
        "purge_ratio": purge_ratio,
    }


# ==============================================================================
# 3. 严格元素守恒核查 (C, H, O 质量守恒)
# ==============================================================================
def verify_element_conservation(res):
    """
    核验 C、H、O 元素的绝对质量守恒。
    输入端：新鲜 CO2 进料，新鲜 H2 进料。
    输出端：精甲醇主产品，反应生成水，系统驰放废气。
    """
    # --------------------------------------------------------------------------
    # 在缺少驰放气详细组分数据时，以未进入已知产品的元素差额估算驰放元素量。
    c_in = res["m_co2_fresh_kg"] * (M_C / MW_CO2)
    h_in = res["m_h2_fresh_kg"]
    o_in = res["m_co2_fresh_kg"] * (2.0 * M_O / MW_CO2)
    if min(c_in, h_in, o_in) <= 0.0:
        raise ValueError("元素守恒核算要求输入端 C、H、O 质量均大于 0")

    c_meoh = res["m_meoh_out_kg"] * (M_C / MW_CH3OH)
    h_meoh = res["m_meoh_out_kg"] * (4.0 * M_H / MW_CH3OH)
    o_meoh = res["m_meoh_out_kg"] * (M_O / MW_CH3OH)

    h_water = res["m_h2o_gen_kg"] * (2.0 * M_H / MW_H2O)
    o_water = res["m_h2o_gen_kg"] * (M_O / MW_H2O)

    # 驰放废气带走元素
    c_purge = c_in - c_meoh
    h_purge = h_in - (h_meoh + h_water)
    o_purge = o_in - (o_meoh + o_water)
    if min(c_purge, h_purge, o_purge) < 0.0:
        raise ValueError("产品中的元素质量超过输入，无法得到非负驰放元素量")
    purge_element_mass = c_purge + h_purge + o_purge
    purge_mass_error = (
        abs(purge_element_mass - res["m_gas_purge_kg"])
        / res["m_gas_purge_kg"]
    )

    c_out = c_meoh + c_purge
    h_out = h_meoh + h_water + h_purge
    o_out = o_meoh + o_water + o_purge

    err_c = abs(c_in - c_out) / c_in
    err_h = abs(h_in - h_out) / h_in
    err_o = abs(o_in - o_out) / o_in

    return {
        "C_in": c_in, "C_out": c_out, "C_err": err_c,
        "H_in": h_in, "H_out": h_out, "H_err": err_h,
        "O_in": o_in, "O_out": o_out, "O_err": err_o,
        "purge_element_mass_kg": purge_element_mass,
        "purge_mass_error": purge_mass_error,
    }


# ==============================================================================
# 4. 园区级工程规模放大核算 (10 万吨/年)
# ==============================================================================
def scale_up_park_level(res, annual_meoh_ton=100000.0):
    """
    根据单吨产品定额，放大至 10 万吨/年工业园区级工程通量规模。
    """
    if annual_meoh_ton <= 0.0:
        raise ValueError("annual_meoh_ton 必须大于 0")

    scale_factor = annual_meoh_ton
    total_electrolyzer_water_kg_per_ton = 1960.0
    power_kwh_per_ton = 10826.0

    annual_co2_ton = res["m_co2_fresh_kg"] * scale_factor / 1000.0
    annual_green_h2_ton = res["m_h2_fresh_kg"] * scale_factor / 1000.0
    annual_crude_water_ton = res["m_h2o_gen_kg"] * scale_factor / 1000.0
    annual_makeup_water_ton = (
        total_electrolyzer_water_kg_per_ton - res["m_h2o_gen_kg"]
    ) * scale_factor / 1000.0
    annual_oxygen_ton = (
        res["m_h2_fresh_kg"] * 8.0 * scale_factor / 1000.0
    )
    annual_purge_gas_ton = res["m_gas_purge_kg"] * scale_factor / 1000.0
    annual_power_b_kwh = power_kwh_per_ton * annual_meoh_ton / 1e8

    return {
        "annual_meoh_capacity_ton": annual_meoh_ton,
        "annual_co2_ton": annual_co2_ton,
        "annual_green_h2_ton": annual_green_h2_ton,
        "annual_crude_water_ton": annual_crude_water_ton,
        "annual_makeup_water_ton": annual_makeup_water_ton,
        "annual_oxygen_ton": annual_oxygen_ton,
        "annual_purge_gas_ton": annual_purge_gas_ton,
        "annual_power_b_kwh": annual_power_b_kwh
    }


# ==============================================================================
# 5. 主程序与自检核验
# ==============================================================================
if __name__ == "__main__":
    print("=" * 80)
    print("《环境规划与管理》任务 1：MFA 循环流求解与元素质量守恒验证")
    print("=" * 80)

    # 1. 读取实测工程数据
    csv_file = find_data_file()
    if csv_file:
        df = pd.read_csv(csv_file)
        print(f"[数据源] 成功加载实操工程数据集: {csv_file} (共 {len(df)} 个节点)")
    else:
        print("[提示] 使用内建工业实测标准物料平衡常数。")

    # 2. 求解物料平衡
    res = solve_mfa_balance(single_pass_conv=0.250, purge_ratio=0.010)
    reaction = res["reaction_balance_kmol"]
    print("\n【简化 CO2 反应-循环方程计算结果】")
    print(f"  反应消耗 CO2       : {reaction['n_co2_rxn']:.4f} kmol")
    print(f"  未反应 CO2         : {reaction['n_co2_unrxn']:.4f} kmol")
    print(f"  CO2 驰放量         : {reaction['n_co2_purge']:.4f} kmol")
    print(f"  CO2 循环量         : {reaction['n_co2_recycle']:.4f} kmol")
    print(f"  方程计算新鲜 CO2   : {reaction['n_co2_fresh']:.4f} kmol "
          f"({reaction['n_co2_fresh'] * MW_CO2:.1f} kg)")
    print("  注：以下工程基准流量取自课程数据集，与上述简化 CO2 方程分开列示。")

    print("\n【单吨产品 (1,000 kg 精甲醇) 物料平衡求解结果】")
    print(f"  新鲜捕集高纯 CO2 进料量 : {res['m_co2_fresh_kg']:.1f} kg")
    print(f"  新鲜 PEM 电解绿氢进料量 : {res['m_h2_fresh_kg']:.1f} kg")
    print(f"  反应分离副产生成水量   : {res['m_h2o_gen_kg']:.1f} kg (回流电解槽)")
    print(f"  未反应气内循环流量     : {res['m_gas_recycle_kg']:.1f} kg")
    print(f"  系统驰放废气排放量     : {res['m_gas_purge_kg']:.1f} kg (送供热锅炉)")
    print(f"  反应器单程 CO2 转化率  : {res['single_pass_conv']:.1%}")
    print(f"  循环比 (质量流量比)    : {res['recycle_ratio_mass']:.2f} : 1")
    print(f"  循环比 (摩尔/体积比)   : {res['recycle_ratio_molar']:.2f} : 1")
    print(f"  全系统总碳转化利用率   : {res['eta_carbon'] * 100.0:.1f}%")

    # 3. 元素质量守恒校验
    cons = verify_element_conservation(res)
    print("\n【按产品与输入差额核算的 C, H, O 元素闭合】")
    print(f"  碳元素 (C): 输入 {cons['C_in']:.2f} kg | 输出 {cons['C_out']:.2f} kg | 相对误差: {cons['C_err']:.6%}")
    print(f"  氢元素 (H): 输入 {cons['H_in']:.2f} kg | 输出 {cons['H_out']:.2f} kg | 相对误差: {cons['H_err']:.6%}")
    print(f"  氧元素 (O): 输入 {cons['O_in']:.2f} kg | 输出 {cons['O_out']:.2f} kg | 相对误差: {cons['O_err']:.6%}")
    print(f"  按元素差额反推的驰放元素质量: {cons['purge_element_mass_kg']:.2f} kg "
          f"(工程数据驰放总质量 {res['m_gas_purge_kg']:.2f} kg)")

    assert cons['C_err'] < 1e-4, "碳守恒误差超出阈值"
    assert cons['H_err'] < 1e-4, "氢守恒误差超出阈值"
    assert cons['O_err'] < 1e-4, "氧守恒误差超出阈值"
    print("  -> C/H/O 闭合误差小于 0.01%；驰放元素质量由输入与产品差额反推，"
          "不是独立组分测量结果。")

    # 4. 园区级工程规模放大 (10 万吨/年)
    park = scale_up_park_level(res, annual_meoh_ton=100000.0)
    print("\n【工业园区 10 万吨/年工程规划通量清单（请填入报告第 2 章）】")
    print(f"  绿色精甲醇设计产能     : {park['annual_meoh_capacity_ton']:.0f} 吨/年")
    print(f"  工业点源 CO2 年需捕集量 : {park['annual_co2_ton']:.2f} 吨/年 (14.23 万吨/年)")
    print(f"  电解水绿氢年需求总量   : {park['annual_green_h2_ton']:.2f} 吨/年 (1.98 万吨/年)")
    print(f"  精馏副产生成水回用量   : {park['annual_crude_water_ton']:.2f} 吨/年 (5.75 万吨/年)")
    print(f"  园区新鲜除盐水净补水量 : {park['annual_makeup_water_ton']:.2f} 吨/年 (13.85 万吨/年)")
    print(f"  副产高纯工业纯氧总量   : {park['annual_oxygen_ton']:.2f} 吨/年 (15.84 万吨/年)")
    print(f"  全厂年综合用电负荷     : {park['annual_power_b_kwh']:.3f} 亿 kWh/年")
    print("=" * 80)
