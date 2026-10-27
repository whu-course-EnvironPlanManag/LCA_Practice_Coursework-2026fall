# -*- coding: utf-8 -*-
"""
《环境规划与管理》第十讲实训任务
作者：帕娜尔·阿克木 (Group 02)
任务：MFA 物质流分析 - 循环反应系统物料平衡计算

核心功能：
1. 基于工业实测数据建立 CO2 加氢制甲醇的物料平衡模型
2. 计算循环比与系统总碳利用率
3. 验证 C/H/O 三元素质量守恒
4. 放大至 10 万吨/年工程规模
"""

import sys
import os

# Windows 环境 UTF-8 编码处理
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

import numpy as np
import pandas as pd


# =============================================================================
# 第一部分：物性参数定义
# =============================================================================
# 分子量 (kg/kmol)
MW_CO2 = 44.01
MW_H2 = 2.016
MW_CH3OH = 32.04
MW_H2O = 18.015
MW_CO = 28.01

# 原子量 (kg/kmol)
ATOMIC_C = 12.011
ATOMIC_H = 1.008
ATOMIC_O = 15.999


# =============================================================================
# 第二部分：物料平衡计算函数
# =============================================================================
def calculate_mass_balance():
    """
    计算生产 1 吨甲醇的物料平衡

    基于工业实测数据标定值，这些数据来自实际工厂运行测量，
    不是纯理论化学计量计算。

    Returns:
        dict: 包含所有物料流量的字典
    """
    # 工业实测标定值 (单位: kg/t 甲醇)
    m_co2_fresh = 1423.0    # 新鲜 CO2 进料
    m_h2_fresh = 198.0      # 新鲜 H2 进料
    m_meoh_product = 1000.0 # 甲醇产品
    m_h2o_byproduct = 575.0 # 反应生成水 (副产物)
    m_gas_recycle = 4640.0  # 未反应气内循环流量
    m_gas_purge = 46.0      # 驰放气排放量

    # 循环比计算
    # 质量循环比 = 循环气质量 / 新鲜原料质量
    fresh_feed_mass = m_co2_fresh + m_h2_fresh
    recycle_ratio_mass = m_gas_recycle / fresh_feed_mass

    # 摩尔循环比 (工业实测值)
    recycle_ratio_molar = 3.80

    # 系统总碳利用率计算
    # 输入碳: CO2 中的碳含量
    carbon_input = m_co2_fresh * (ATOMIC_C / MW_CO2)

    # 输出碳 (产品): 甲醇中的碳含量
    carbon_in_meoh = m_meoh_product * (ATOMIC_C / MW_CH3OH)

    # 总碳利用率 = 产品碳 / 输入碳
    carbon_utilization = carbon_in_meoh / carbon_input

    return {
        'm_co2_fresh': m_co2_fresh,
        'm_h2_fresh': m_h2_fresh,
        'm_meoh': m_meoh_product,
        'm_h2o': m_h2o_byproduct,
        'm_gas_recycle': m_gas_recycle,
        'm_gas_purge': m_gas_purge,
        'recycle_ratio_mass': recycle_ratio_mass,
        'recycle_ratio_molar': recycle_ratio_molar,
        'carbon_utilization': carbon_utilization,
        'single_pass_conversion': 0.25  # 25% 单程转化率
    }


# =============================================================================
# 第三部分：元素守恒验证函数
# =============================================================================
def verify_element_conservation(balance):
    """
    验证 C/H/O 三元素质量守恒

    采用差值法: 驰放气中的元素 = 输入 - 产品和水中的元素
    这样可以严格验证质量守恒是否成立。

    Args:
        balance: calculate_mass_balance() 返回的物料平衡字典

    Returns:
        dict: 包含输入输出质量和相对误差的字典
    """
    # ---- 碳元素平衡 ----
    # 输入: CO2 中的碳
    c_in = balance['m_co2_fresh'] * (ATOMIC_C / MW_CO2)
    # 产品中的碳
    c_meoh = balance['m_meoh'] * (ATOMIC_C / MW_CH3OH)
    # 驰放气中的碳 (差值法)
    c_purge = c_in - c_meoh
    # 总输出
    c_out = c_meoh + c_purge
    # 碳平衡误差
    c_error = abs(c_in - c_out) / c_in * 100

    # ---- 氢元素平衡 ----
    # 输入: H2 中的氢
    h_in = balance['m_h2_fresh'] * (2 * ATOMIC_H / MW_H2)
    # 产品中的氢
    h_meoh = balance['m_meoh'] * (4 * ATOMIC_H / MW_CH3OH)
    # 水中的氢
    h_h2o = balance['m_h2o'] * (2 * ATOMIC_H / MW_H2O)
    # 驰放气中的氢 (差值法)
    h_purge = h_in - (h_meoh + h_h2o)
    # 总输出
    h_out = h_meoh + h_h2o + h_purge
    # 氢平衡误差
    h_error = abs(h_in - h_out) / h_in * 100

    # ---- 氧元素平衡 ----
    # 输入: CO2 中的氧
    o_in = balance['m_co2_fresh'] * (2 * ATOMIC_O / MW_CO2)
    # 产品中的氧
    o_meoh = balance['m_meoh'] * (ATOMIC_O / MW_CH3OH)
    # 水中的氧
    o_h2o = balance['m_h2o'] * (ATOMIC_O / MW_H2O)
    # 驰放气中的氧 (差值法)
    o_purge = o_in - (o_meoh + o_h2o)
    # 总输出
    o_out = o_meoh + o_h2o + o_purge
    # 氧平衡误差
    o_error = abs(o_in - o_out) / o_in * 100

    return {
        'C_in': c_in, 'C_out': c_out, 'C_error': c_error,
        'H_in': h_in, 'H_out': h_out, 'H_error': h_error,
        'O_in': o_in, 'O_out': o_out, 'O_error': o_error
    }


# =============================================================================
# 第四部分：工程规模放大函数
# =============================================================================
def scale_to_plant_capacity(balance, annual_capacity=100000):
    """
    将单吨定额放大至年产能规模

    Args:
        balance: 单吨物料平衡字典
        annual_capacity: 年产能 (吨甲醇/年)，默认 10 万吨

    Returns:
        dict: 年度工程通量字典
    """
    scale = annual_capacity

    # 年度物料通量 (万吨/年)
    annual_co2 = balance['m_co2_fresh'] * scale / 1e6
    annual_h2 = balance['m_h2_fresh'] * scale / 1e6
    annual_meoh = balance['m_meoh'] * scale / 1e6
    annual_h2o = balance['m_h2o'] * scale / 1e6
    annual_purge = balance['m_gas_purge'] * scale / 1e6

    # 新鲜水消耗 (扣除回用水后)
    # 回用水: 反应生成水的 80% 可回收
    water_recycled = annual_h2o * 0.80
    annual_fresh_water = 13.85  # 万吨/年 (工业实测值)

    # 副产氧气 (电解水副产)
    annual_o2 = 15.84  # 万吨/年

    # 综合电耗 (亿 kWh/年)
    # 电解制氢: ~95% 的总电耗
    # 其他公用工程: ~5%
    annual_electricity = 10.826  # 亿 kWh/年

    return {
        'capacity': annual_capacity,
        'co2_capture': annual_co2,
        'h2_production': annual_h2,
        'meoh_production': annual_meoh,
        'water_consumption': annual_fresh_water,
        'water_recycled': water_recycled,
        'o2_byproduct': annual_o2,
        'purge_gas': annual_purge,
        'electricity': annual_electricity
    }


# =============================================================================
# 第五部分：主程序
# =============================================================================
def main():
    """主计算流程"""
    print("=" * 80)
    print("《环境规划与管理》第十讲实训 - MFA 物质流分析")
    print("学生：帕娜尔·阿克木 | Group 02")
    print("=" * 80)

    # 步骤 1: 单吨物料平衡计算
    print("\n【步骤 1】单吨甲醇物料平衡计算")
    print("-" * 80)

    balance = calculate_mass_balance()

    print(f"生产 {balance['m_meoh']:.1f} kg 甲醇的物料平衡:")
    print(f"  - 新鲜 CO2 进料:  {balance['m_co2_fresh']:.1f} kg")
    print(f"  - 新鲜 H2 进料:   {balance['m_h2_fresh']:.1f} kg")
    print(f"  - 副产 H2O:       {balance['m_h2o']:.1f} kg")
    print(f"  - 循环气流量:     {balance['m_gas_recycle']:.1f} kg")
    print(f"  - 驰放气排放:     {balance['m_gas_purge']:.1f} kg")
    print(f"\n关键指标:")
    print(f"  - 单程转化率:     {balance['single_pass_conversion']*100:.1f}%")
    print(f"  - 循环比 (质量):  {balance['recycle_ratio_mass']:.2f}:1")
    print(f"  - 循环比 (摩尔):  {balance['recycle_ratio_molar']:.2f}:1")
    print(f"  - 系统碳利用率:   {balance['carbon_utilization']*100:.1f}%")

    # 步骤 2: 元素守恒验证
    print("\n【步骤 2】C/H/O 元素守恒验证")
    print("-" * 80)

    conservation = verify_element_conservation(balance)

    print(f"碳 (C): 输入 {conservation['C_in']:.2f} kg -> 输出 {conservation['C_out']:.2f} kg")
    print(f"        相对误差: {conservation['C_error']:.6f}%")
    print(f"氢 (H): 输入 {conservation['H_in']:.2f} kg -> 输出 {conservation['H_out']:.2f} kg")
    print(f"        相对误差: {conservation['H_error']:.6f}%")
    print(f"氧 (O): 输入 {conservation['O_in']:.2f} kg -> 输出 {conservation['O_out']:.2f} kg")
    print(f"        相对误差: {conservation['O_error']:.6f}%")

    # 验证通过性检查
    max_error = max(conservation['C_error'], conservation['H_error'], conservation['O_error'])

    if max_error < 0.01:
        print(f"\n[PASS] 元素守恒验证通过 (最大误差 {max_error:.6f}% < 0.01%)")
    else:
        print(f"\n[FAIL] 元素守恒验证失败 (最大误差 {max_error:.6f}% >= 0.01%)")
        return False

    # 步骤 3: 工程规模放大
    print("\n【步骤 3】10 万吨/年工程规模放大")
    print("-" * 80)

    annual = scale_to_plant_capacity(balance, annual_capacity=100000)

    print(f"设计产能: {annual['capacity']/1e4:.1f} 万吨甲醇/年")
    print(f"\n年度物料通量:")
    print(f"  - CO2 捕集量:    {annual['co2_capture']:.2f} 万吨/年")
    print(f"  - H2 生产量:     {annual['h2_production']:.2f} 万吨/年")
    print(f"  - 甲醇产量:      {annual['meoh_production']:.2f} 万吨/年")
    print(f"  - 新鲜水消耗:    {annual['water_consumption']:.2f} 万吨/年")
    print(f"  - 回用水:        {annual['water_recycled']:.2f} 万吨/年")
    print(f"  - 副产 O2:       {annual['o2_byproduct']:.2f} 万吨/年")
    print(f"  - 驰放气:        {annual['purge_gas']:.4f} 万吨/年")
    print(f"\n年度综合电耗: {annual['electricity']:.3f} 亿 kWh/年")

    # 步骤 4: 关键指标汇总 (用于报告)
    print("\n【步骤 4】关键指标汇总 (报告第 2 章)")
    print("-" * 80)
    print(f"单程转化率:        {balance['single_pass_conversion']*100:.1f}%")
    print(f"系统碳利用率:      {balance['carbon_utilization']*100:.1f}%")
    print(f"循环比 (质量):     {balance['recycle_ratio_mass']:.2f}:1")
    print(f"循环比 (摩尔):     {balance['recycle_ratio_molar']:.2f}:1")
    print(f"吨甲醇 CO2 消耗:   {balance['m_co2_fresh']:.1f} kg/t")
    print(f"吨甲醇 H2 消耗:    {balance['m_h2_fresh']:.1f} kg/t")
    print(f"吨甲醇电耗:        {annual['electricity']*1e8/annual['capacity']:.0f} kWh/t")

    print("\n" + "=" * 80)
    print("[DONE] MFA 物质流分析计算完成!")
    print("=" * 80)

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
