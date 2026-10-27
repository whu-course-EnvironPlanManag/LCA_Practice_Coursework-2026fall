# -*- coding: utf-8 -*-
"""
《环境规划与管理》第十讲实训任务
作者：帕娜尔·阿克木 (Group 02)
任务：政策量化规制引擎 (Vibe Coding)

功能说明：
  根据 data_cohort/policy_clauses_pack.md 中的四项政策法规，
  编写量化评估函数，实现对绿色甲醇项目的合规性判定与成本修正。

四项政策卡片：
  卡片1: 欧盟 RED III 准入与溢价补贴
  卡片2: 中国碳市场 ETS/CCER 阶梯奖惩
  卡片3: 工业取水定额与累进水资源税
  卡片4: 次生大气污染物环保税与清洁生产底线

================================================================================
Vibe Coding Prompt (向 AI 助手发送的提示词):
================================================================================
请根据以下四项政策卡片，编写 evaluate_policy_compliance() 函数：

卡片1 - 欧盟 RED III：
  - 基准线: 1870.6 kg CO2e/t
  - 减排阈值: >= 70% (即 GWP <= 561.2 kg CO2e/t)
  - 绿电要求: f_green >= 80%
  - 达标补贴: -1200 元/t (国际航运溢价)

卡片2 - 中国碳市场 ETS/CCER：
  - 基准线: 2600 kg CO2e/t (传统煤制甲醇)
  - 碳价: 100 元/t CO2e
  - GWP <= 0: 享受 1.2 倍 CCER 激励
  - 0 < GWP <= 2600: 享受 1.0 倍常规减排
  - GWP > 2600: 一票否决，2.0 倍惩罚碳价 + 0.10 元/kWh 电价惩罚

卡片3 - 工业取水定额：
  - 定额: 1.400 t 水/t 甲醇
  - 税率: 5.0 元/t
  - 超定额累进: 1.400-1.425 区间 3 倍 (15 元/t)
  - 严重超定额 (>1.425): 强制闭式空冷 (+85 元/t)，取水压降至 1.390

卡片4 - 环保税与清洁生产：
  - 基础环保税: 12 + 18.5 * (r_purge / 0.010)
  - r_purge > 3.5%: 碳利用率跌破 88%，一票否决
================================================================================
"""

import sys
import io
import numpy as np

# Windows 环境 UTF-8 编码处理
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass


# =============================================================================
# 政策量化评估核心函数
# =============================================================================
def evaluate_policy_compliance(gwp_net, base_lcom, e_total_kwh, f_green, r_purge):
    """
    综合评估绿色甲醇项目的政策合规性与成本修正

    参数:
        gwp_net:     全生命周期净碳足迹 (kg CO2e/t 甲醇)
        base_lcom:   基础平准化甲醇成本 (元/t)
        e_total_kwh: 吨甲醇综合电耗 (kWh/t)
        f_green:     绿电消纳比例 (0.0 ~ 1.0)
        r_purge:     驰放分流比 (0.004 ~ 0.045)

    返回:
        dict: 包含调整后成本、合规标签及各政策分项的字典
    """
    # ---- 卡片1: 欧盟 RED III 认证判定 ----
    # 减排 70% 阈值 = 1870.6 * (1 - 0.70) = 561.18 kg/t
    REDIII_GWP_THRESHOLD = 561.2
    REDIII_GREEN_THRESHOLD = 0.80
    REDIII_SUBSIDY = -1200.0  # 元/t (负值表示补贴收入)

    qualifies_rediii = (gwp_net <= REDIII_GWP_THRESHOLD) and (f_green >= REDIII_GREEN_THRESHOLD)
    subsidy_rediii = REDIII_SUBSIDY if qualifies_rediii else 0.0

    # ---- 卡片2: 国内碳市场阶梯奖惩 ----
    FOSSIL_BASELINE = 2600.0  # kg CO2e/t (煤制甲醇基准)
    CARBON_PRICE = 100.0      # 元/t CO2e

    veto_carbon = False

    if gwp_net <= 0:
        # 负碳: 享受 1.2 倍 CCER 激励
        credit = (FOSSIL_BASELINE - gwp_net) / 1000.0
        cost_carbon = -1.2 * credit * CARBON_PRICE
    elif gwp_net <= FOSSIL_BASELINE:
        # 低碳: 享受 1.0 倍常规减排收益
        credit = (FOSSIL_BASELINE - gwp_net) / 1000.0
        cost_carbon = -1.0 * credit * CARBON_PRICE
    else:
        # 超排: 一票否决 + 2.0 倍惩罚 + 电价惩罚
        veto_carbon = True
        penalty = (gwp_net - FOSSIL_BASELINE) / 1000.0
        cost_carbon = 2.0 * penalty * CARBON_PRICE + 0.10 * e_total_kwh

    # ---- 卡片3: 工业取水定额与累进水资源税 ----
    WATER_QUOTA = 1.400  # t 水/t 甲醇
    WATER_TAX_BASE = 5.0  # 元/t

    # 取水量计算: 基础 + 驰放气蒸发导致的额外补水
    water_total = 1.385 + 0.008 * (0.010 / r_purge)

    if water_total <= WATER_QUOTA:
        cost_water = water_total * WATER_TAX_BASE
    elif water_total <= 1.425:
        # 累进税率: 定额内 1 倍 + 超额部分 3 倍
        cost_water = WATER_QUOTA * WATER_TAX_BASE + (water_total - WATER_QUOTA) * (3.0 * WATER_TAX_BASE)
    else:
        # 严重超标: 强制闭式空冷 + 取水压降
        cost_water = 1.390 * WATER_TAX_BASE + 85.0

    # ---- 卡片4: 环保税与清洁生产底线 ----
    # 基础环保税 + 驰放气比例调节
    cost_env_tax = 12.0 + 18.5 * (r_purge / 0.010)

    # 清洁生产一票否决: 驰放比 > 3.5% 导致碳利用率 < 88%
    veto_clean_production = (r_purge > 0.035)

    # ---- 综合合规标签 ----
    if veto_carbon or veto_clean_production:
        compliance_label = "Redline_Vetoed"
    elif qualifies_rediii:
        compliance_label = "RED_III_RFNBO_Certified"
    else:
        compliance_label = "Domestic_Compliant"

    # ---- 调整后成本计算 ----
    lcom_adjusted = base_lcom + subsidy_rediii + cost_carbon + cost_water + cost_env_tax

    # 边际减排成本 MAC
    ghg_avoided = (FOSSIL_BASELINE - gwp_net) / 1000.0
    FOSSIL_COST = 2500.0  # 元/t (煤制甲醇参考成本)

    if ghg_avoided > 0:
        mac_adjusted = (lcom_adjusted - FOSSIL_COST) / ghg_avoided
    else:
        mac_adjusted = np.nan

    return {
        "lcom_adjusted": lcom_adjusted,
        "mac_adjusted": mac_adjusted,
        "compliance": compliance_label,
        "breakdown": {
            "red_iii_subsidy": subsidy_rediii,
            "carbon_cost": cost_carbon,
            "water_cost": cost_water,
            "env_tax": cost_env_tax
        }
    }


# =============================================================================
# 单元测试
# =============================================================================
if __name__ == "__main__":
    print("=" * 80)
    print("《环境规划与管理》任务 2: 政策量化规制引擎 - 单元测试")
    print("学生: 帕娜尔·阿克木 | Group 02")
    print("=" * 80)

    # 定义三个典型测试工况
    test_scenarios = [
        {
            "name": "工况1: 高比例绿电基地 (100% 绿电, 驰放比 1.0%)",
            "input": (-1044.1, 2862.3, 10826.0, 1.00, 0.010),
            "expected": {
                "compliance": "RED_III_RFNBO_Certified",
                "red_iii_subsidy": -1200.0,
                "carbon_cost": -437.29
            }
        },
        {
            "name": "工况2: 多能互补过渡 (65% 绿电, 驰放比 1.5%)",
            "input": (800.0, 4200.0, 10826.0, 0.65, 0.015),
            "expected": {
                "compliance": "Domestic_Compliant",
                "red_iii_subsidy": 0.0,
                "carbon_cost": -180.0
            }
        },
        {
            "name": "工况3: 高碳电网反向增排 (0% 绿电, 驰放比 1.0%)",
            "input": (4531.3, 7193.0, 10826.0, 0.00, 0.010),
            "expected": {
                "compliance": "Redline_Vetoed",
                "red_iii_subsidy": 0.0,
                "carbon_cost": 1468.86
            }
        }
    ]

    all_pass = True

    for scenario in test_scenarios:
        result = evaluate_policy_compliance(*scenario["input"])
        expected = scenario["expected"]

        # 检查合规标签
        check_label = result["compliance"] == expected["compliance"]
        # 检查 RED III 补贴
        check_subsidy = abs(result["breakdown"]["red_iii_subsidy"] - expected["red_iii_subsidy"]) < 0.01
        # 检查碳市场调节
        check_carbon = abs(result["breakdown"]["carbon_cost"] - expected["carbon_cost"]) < 0.1

        passed = check_label and check_subsidy and check_carbon

        print(f"\n[{scenario['name']}]")
        print(f"  合规标签: {result['compliance']} (预期: {expected['compliance']}) -> {'PASS' if check_label else 'FAIL'}")
        print(f"  RED III 补贴: {result['breakdown']['red_iii_subsidy']:.2f} 元/t (预期: {expected['red_iii_subsidy']:.2f}) -> {'PASS' if check_subsidy else 'FAIL'}")
        print(f"  碳市场调节: {result['breakdown']['carbon_cost']:.2f} 元/t (预期: {expected['carbon_cost']:.2f}) -> {'PASS' if check_carbon else 'FAIL'}")
        print(f"  调整后 LCOM: {result['lcom_adjusted']:.2f} 元/t")
        if not np.isnan(result['mac_adjusted']):
            print(f"  调整后 MAC: {result['mac_adjusted']:.2f} 元/t CO2e")
        else:
            print(f"  调整后 MAC: NaN (一票否决)")

        if not passed:
            all_pass = False

    print("\n" + "=" * 80)
    if all_pass:
        print("[结论] 全部测试工况通过! 政策引擎可接入任务3帕累托寻优模型")
    else:
        print("[结论] 存在未通过的测试项，请检查阈值判定逻辑")
    print("=" * 80)
