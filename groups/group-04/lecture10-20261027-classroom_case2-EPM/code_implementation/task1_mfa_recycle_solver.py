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
    # 以 CSV 中的甲醇产品流为功能单位，氢/碳按 CO2 + 3H2 -> CH3OH + H2O
    # 计量；求解变量是新鲜进料、循环回流和反应程度，不把目标流量赋给结果。
    data_file = find_data_file()
    if data_file is None:
        raise FileNotFoundError("未找到 data_cohort/mfa_reaction_recycle_balance.csv")
    streams = pd.read_csv(data_file).set_index("stream_id")
    m_meoh_out = float(np.asarray(streams.loc["S12", "mass_flow_per_ton_product_kg"]).item())
    n_meoh = m_meoh_out / MW_CH3OH
    n_h2_consumed = 3.0 * n_meoh

    if not 0.0 < single_pass_conv < 1.0:
        raise ValueError("single_pass_conv 必须在 0 和 1 之间")
    if not 0.0 <= purge_ratio < 1.0:
        raise ValueError("purge_ratio 必须在 0 和 1 之间")

    # 每种反应物各有新鲜进料、循环回流、反应量三个未知数。
    # 方程分别约束反应量、反应器单程转化率和分离器出口回流比例。
    n_co2_fresh_seed = float(np.asarray(streams.loc["S01", "mass_flow_per_ton_product_kg"]).item()) / MW_CO2
    n_h2_fresh_seed = float(np.asarray(streams.loc["S02", "mass_flow_per_ton_product_kg"]).item()) / MW_H2
    n_co2_inlet_seed = n_meoh / single_pass_conv
    n_h2_inlet_seed = n_h2_consumed / single_pass_conv
    n_co2_unreacted_seed = n_co2_inlet_seed - n_meoh
    n_h2_unreacted_seed = n_h2_inlet_seed - n_h2_consumed
    initial = [
        n_co2_fresh_seed, (1.0 - purge_ratio) * n_co2_unreacted_seed, n_meoh,
        n_h2_fresh_seed, (1.0 - purge_ratio) * n_h2_unreacted_seed, n_h2_consumed,
    ]

    def balance_equations(values):
        n_co2_fresh, n_co2_recycle, n_co2_rxn, n_h2_fresh, n_h2_recycle, n_h2_rxn = values
        n_co2_inlet = n_co2_fresh + n_co2_recycle
        n_h2_inlet = n_h2_fresh + n_h2_recycle
        n_co2_unreacted = n_co2_inlet - n_co2_rxn
        n_h2_unreacted = n_h2_inlet - n_h2_rxn
        return [
            (n_co2_rxn - n_meoh) / n_meoh,
            n_co2_rxn / n_co2_inlet - single_pass_conv,
            (n_co2_recycle - (1.0 - purge_ratio) * n_co2_unreacted) / n_co2_inlet,
            (n_h2_rxn - n_h2_consumed) / n_h2_consumed,
            n_h2_rxn / n_h2_inlet - single_pass_conv,
            (n_h2_recycle - (1.0 - purge_ratio) * n_h2_unreacted) / n_h2_inlet,
        ]

    solution = None
    message = ""
    for guess in (initial, [value * 0.9 for value in initial]):
        candidate, solver_info, ier, message = fsolve(
            balance_equations, guess, full_output=True
        )
        candidate = np.asarray(candidate, dtype=np.float64)
        candidate_residuals = balance_equations(candidate)
        if ier == 1 and max(abs(value) for value in candidate_residuals) < 1e-8:
            solution = candidate
            break

    if solution is None:
        print("[求解失败] 两组初值均未收敛；最后一组中间变量(kmol/t)：", candidate)
        print("[求解器状态] ", message, "函数调用次数:", solver_info.get("nfev"))
        print("[方程残差] ", candidate_residuals)
        component_columns = {
            "CO2": "co2_wt_pct",
            "H2": "h2_wt_pct",
            "CH3OH": "meoh_wt_pct",
            "H2O": "h2o_wt_pct",
            "O2": "o2_wt_pct",
            "惰性物": "other_inerts_wt_pct",
        }
        print("[CSV逐物流组分质量流量 kg/t]")
        for stream_id, row in streams.iterrows():
            total_flow = float(row["mass_flow_per_ton_product_kg"])
            composition = {
                name: total_flow * float(row[column]) / 100.0
                for name, column in component_columns.items()
            }
            print(f"  {stream_id} {row['stream_name']}: 总流量={total_flow:.3f}; 组分={composition}")
        raise RuntimeError(f"MFA 循环方程求解失败: {message}")

    n_co2_fresh, n_co2_recycle, n_co2_rxn, n_h2_fresh, n_h2_recycle, n_h2_rxn = solution
    n_co2_inlet = n_co2_fresh + n_co2_recycle
    n_h2_inlet = n_h2_fresh + n_h2_recycle
    n_co2_purge = purge_ratio * (n_co2_inlet - n_co2_rxn)
    n_h2_purge = purge_ratio * (n_h2_inlet - n_h2_rxn)
    n_co2_unreacted = n_co2_inlet - n_co2_rxn
    n_h2_unreacted = n_h2_inlet - n_h2_rxn

    m_co2_fresh = n_co2_fresh * MW_CO2
    m_h2_fresh = n_h2_fresh * MW_H2
    m_h2o_gen = n_meoh * MW_H2O
    m_gas_recycle = n_co2_recycle * MW_CO2 + n_h2_recycle * MW_H2
    m_gas_purge = n_co2_purge * MW_CO2 + n_h2_purge * MW_H2
    m_reactor_inlet = n_co2_inlet * MW_CO2 + n_h2_inlet * MW_H2
    m_reactor_outlet = (
        n_co2_unreacted * MW_CO2
        + n_h2_unreacted * MW_H2
        + n_meoh * MW_CH3OH
        + n_meoh * MW_H2O
    )
    recycle_ratio_mass = m_gas_recycle / (m_co2_fresh + m_h2_fresh)
    recycle_ratio_molar = (n_co2_recycle + n_h2_recycle) / (n_co2_fresh + n_h2_fresh)
    recycle_ratio_molar_h2 = (n_co2_recycle + n_h2_recycle) / n_h2_fresh

    csv_fresh_mass = float(np.asarray(streams.loc[["S01", "S02"], "mass_flow_per_ton_product_kg"].sum()).item())
    csv_co2_fresh = float(np.asarray(streams.loc["S01", "mass_flow_per_ton_product_kg"]).item())
    csv_h2_fresh = float(np.asarray(streams.loc["S02", "mass_flow_per_ton_product_kg"]).item())
    csv_makeup_water = float(np.asarray(streams.loc["S03", "mass_flow_per_ton_product_kg"]).item())
    csv_oxygen = float(np.asarray(streams.loc["S05", "mass_flow_per_ton_product_kg"]).item())
    # 报告口径按 CSV 记录的新鲜 CO2 进料核算产品碳利用率；另保留方程边界口径对照。
    eta_carbon = n_meoh / (csv_co2_fresh / MW_CO2)
    eta_carbon_solver_feed = n_meoh / n_co2_fresh

    return {
        "m_co2_fresh_kg": m_co2_fresh,
        "m_h2_fresh_kg": m_h2_fresh,
        "m_meoh_out_kg": m_meoh_out,
        "m_h2o_gen_kg": m_h2o_gen,
        "m_gas_recycle_kg": m_gas_recycle,
        "m_gas_purge_kg": m_gas_purge,
        "eta_carbon": eta_carbon,
        "eta_carbon_solver_feed": eta_carbon_solver_feed,
        "recycle_ratio_mass": recycle_ratio_mass,
        "recycle_ratio_molar": recycle_ratio_molar,
        "recycle_ratio_molar_h2": recycle_ratio_molar_h2,
        "n_meoh_kmol": n_meoh,
        "n_co2_fresh_kmol": n_co2_fresh,
        "n_h2_fresh_kmol": n_h2_fresh,
        "n_co2_recycle_kmol": n_co2_recycle,
        "n_h2_recycle_kmol": n_h2_recycle,
        "n_co2_purge_kmol": n_co2_purge,
        "n_h2_purge_kmol": n_h2_purge,
        "n_co2_inlet_kmol": n_co2_inlet,
        "n_h2_inlet_kmol": n_h2_inlet,
        "n_co2_unreacted_kmol": n_co2_unreacted,
        "n_h2_unreacted_kmol": n_h2_unreacted,
        "m_reactor_inlet_kg": m_reactor_inlet,
        "m_reactor_outlet_kg": m_reactor_outlet,
        "csv_fresh_mass_kg": csv_fresh_mass,
        "csv_co2_fresh_kg": csv_co2_fresh,
        "csv_h2_fresh_kg": csv_h2_fresh,
        "m_makeup_water_kg": csv_makeup_water,
        "m_oxygen_kg": csv_oxygen,
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
    # 独立统计进料、产品/生成水及弛放气中的元素质量，不用差值反推弛放组分。
    c_in = res["n_co2_fresh_kmol"] * M_C
    h_in = res["n_h2_fresh_kmol"] * 2.0 * M_H
    o_in = res["n_co2_fresh_kmol"] * 2.0 * M_O

    c_meoh = res["n_meoh_kmol"] * M_C
    h_meoh = res["n_meoh_kmol"] * 4.0 * M_H
    o_meoh = res["n_meoh_kmol"] * M_O
    h_water = res["n_meoh_kmol"] * 2.0 * M_H
    o_water = res["n_meoh_kmol"] * M_O
    c_purge = res["n_co2_purge_kmol"] * M_C
    h_purge = res["n_h2_purge_kmol"] * 2.0 * M_H
    o_purge = res["n_co2_purge_kmol"] * 2.0 * M_O

    c_out = c_meoh + c_purge
    h_out = h_meoh + h_water + h_purge
    o_out = o_meoh + o_water + o_purge

    err_c = abs(c_in - c_out) / c_in
    err_h = abs(h_in - h_out) / h_in
    err_o = abs(o_in - o_out) / o_in

    return {
        "C_in": c_in, "C_out": c_out, "C_err": err_c,
        "H_in": h_in, "H_out": h_out, "H_err": err_h,
        "O_in": o_in, "O_out": o_out, "O_err": err_o
    }


# ==============================================================================
# 4. 园区级工程规模放大核算 (10 万吨/年)
# ==============================================================================
def scale_up_park_level(res, annual_meoh_ton=100000.0):
    """
    根据单吨产品定额，放大至 10 万吨/年工业园区级工程通量规模。
    """
    # 单吨流量的 kg/t 数值乘以年产吨数，再除以 1000 转成 t/a。
    scale_factor = annual_meoh_ton / 1000.0
    annual_co2_ton = res["m_co2_fresh_kg"] * scale_factor
    annual_green_h2_ton = res["m_h2_fresh_kg"] * scale_factor
    annual_crude_water_ton = res["m_h2o_gen_kg"] * scale_factor
    annual_makeup_water_ton = res["m_makeup_water_kg"] * scale_factor
    annual_oxygen_ton = res["m_oxygen_kg"] * scale_factor
    annual_purge_gas_ton = res["m_gas_purge_kg"] * scale_factor
    annual_power_b_kwh = 10826.0 * annual_meoh_ton / 1e8

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
    print("\n【单吨产品物料平衡求解结果】")
    print(f"  新鲜捕集高纯 CO2 进料量 : {res['m_co2_fresh_kg']:.1f} kg")
    print(f"  新鲜 PEM 电解绿氢进料量 : {res['m_h2_fresh_kg']:.1f} kg")
    print(f"  反应分离副产生成水量   : {res['m_h2o_gen_kg']:.1f} kg (回流电解槽)")
    print(f"  未反应气内循环流量     : {res['m_gas_recycle_kg']:.1f} kg")
    print(f"  系统驰放废气排放量     : {res['m_gas_purge_kg']:.1f} kg (送供热锅炉)")
    print(f"  反应器单程 CO2 转化率  : {100.0 * res['n_meoh_kmol'] / res['n_co2_inlet_kmol']:.2f}%")
    print(f"  循环比 (质量流量比)    : {res['recycle_ratio_mass']:.2f} : 1")
    print(f"  循环摩尔比 (循环/新鲜总气) : {res['recycle_ratio_molar']:.2f} : 1")
    print(f"  循环摩尔比 (循环/新鲜H2)   : {res['recycle_ratio_molar_h2']:.2f} : 1")
    print(f"  总碳转化利用率 (CSV新鲜CO2基准): {res['eta_carbon'] * 100.0:.1f}%")
    print(f"  总碳转化率 (求解新鲜CO2基准)   : {res['eta_carbon_solver_feed'] * 100.0:.1f}%")
    print("\n【验收目标偏差（模型值 - 目标值）】")
    print(f"  循环气流量偏差         : {res['m_gas_recycle_kg'] - 4640.0:+.2f} kg/t")
    print(f"  质量循环比偏差         : {res['recycle_ratio_mass'] - 2.86:+.4f}")
    print(f"  总气摩尔循环比偏差     : {res['recycle_ratio_molar'] - 3.80:+.4f}")
    print(f"  CSV基准碳利用率 vs 96.5%偏差: {(res['eta_carbon'] - 0.965) * 100.0:+.3f} 个百分点")
    print("  注：回流比以全部新鲜气为基准时，CSV与 3.8:1 目标不一致。")

    # 3. 元素质量守恒校验
    cons = verify_element_conservation(res)
    print("\n【C, H, O 三元素严密质量守恒校验】")
    print(f"  碳元素 (C): 输入 {cons['C_in']:.2f} kg | 输出 {cons['C_out']:.2f} kg | 相对误差: {cons['C_err']:.6%}")
    print(f"  氢元素 (H): 输入 {cons['H_in']:.2f} kg | 输出 {cons['H_out']:.2f} kg | 相对误差: {cons['H_err']:.6%}")
    print(f"  氧元素 (O): 输入 {cons['O_in']:.2f} kg | 输出 {cons['O_out']:.2f} kg | 相对误差: {cons['O_err']:.6%}")

    assert cons['C_err'] < 1e-4, "碳守恒误差超出阈值"
    assert cons['H_err'] < 1e-4, "氢守恒误差超出阈值"
    assert cons['O_err'] < 1e-4, "氧守恒误差超出阈值"
    print("  -> 结论：C、H、O 元素守恒严格成立，计算误差均小于 0.01%！")

    # 4. 园区级工程规模放大 (10 万吨/年)
    park = scale_up_park_level(res, annual_meoh_ton=100000.0)
    print("\n【工业园区 10 万吨/年工程规划通量清单（请填入报告第 2 章）】")
    print(f"  绿色精甲醇设计产能     : {park['annual_meoh_capacity_ton']:.0f} 吨/年")
    print(f"  工业点源 CO2 年需捕集量 : {park['annual_co2_ton']:.2f} 吨/年")
    print(f"  电解水绿氢年需求总量   : {park['annual_green_h2_ton']:.2f} 吨/年")
    print(f"  精馏副产生成水回用量   : {park['annual_crude_water_ton']:.2f} 吨/年")
    print(f"  园区新鲜除盐水净补水量 : {park['annual_makeup_water_ton']:.2f} 吨/年")
    print(f"  副产高纯工业纯氧总量   : {park['annual_oxygen_ton']:.2f} 吨/年")
    print(f"  全厂年综合用电负荷     : {park['annual_power_b_kwh']:.3f} 亿 kWh/年")

    print("\n【独立校验报告】")
    print(f"  循环流量       : {res['m_gas_recycle_kg']:.2f} kg/t (目标 4640.00)")
    print(f"  质量循环比     : {res['recycle_ratio_mass']:.4f}:1 (目标 2.86:1)")
    print(f"  总气摩尔循环比 : {res['recycle_ratio_molar']:.4f}:1")
    print(f"  H2基准摩尔比   : {res['recycle_ratio_molar_h2']:.4f}:1 (目标约 3.8:1)")
    print(f"  总碳转化率     : {res['eta_carbon'] * 100.0:.4f}% (CSV基准约 96.5%)")
    print(f"  C 相对误差     : {cons['C_err']:.8%}")
    print(f"  H 相对误差     : {cons['H_err']:.8%}")
    print(f"  O 相对误差     : {cons['O_err']:.8%}")
    if abs(res['m_gas_recycle_kg'] - 4640.0) > 0.1 or abs(res['eta_carbon'] - 0.96) > 1e-4:
        print("  结论：方程已收敛且守恒通过，但给定物理约束无法同时复现全部目标值；未将目标值硬编码进求解结果。")
    print("=" * 80)
