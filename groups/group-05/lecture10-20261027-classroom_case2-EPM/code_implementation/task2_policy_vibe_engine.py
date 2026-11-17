# -*- coding: utf-8 -*-
"""
课程名称：《环境规划与管理》
案例主题：工业园区二氧化碳捕集耦合绿氢合成绿色甲醇系统
任务编号：任务 2（学生实训脚本框架）
脚本名称：task2_policy_vibe_engine.py
实训目标：
  1. 研读 data_cohort/policy_clauses_pack.md 中的四项政策法规与技术标准条文；
  2. 借助 AI 编程助手（Vibe Coding）生成 policy_engine 量化算子；
  3. 实现对欧盟 RED III、国内碳市场（ETS/CCER）、工业取水定额与次生环保税的算法化量化；
  4. 运行内建单元测试，验证合规状态与成本修正值是否与基准自检表完全一致。

================================================================================
【请在此处粘贴你向 AI 助手发送的 Vibe Coding 提示词 (Prompt)】
Prompt:
  请根据 data_cohort/policy_clauses_pack.md 实现 evaluate_policy_compliance
  (gwp_net, base_lcom, e_total_kwh, f_green, r_purge)。严格实现 RED III
  准入阈值（GWP <= 561.2 kg CO2e/t 且绿电比例 >= 0.80）及 -1200 元/t
  补贴；国内碳市场以 2600 kg CO2e/t 和 100 元/t CO2e 为基准，分别
  实现 GWP <= 0 的 1.2 倍 CCER 激励、0 < GWP <= 2600 的常规碳收益、
  超基准时的 2 倍惩罚碳价和 0.10 元/kWh 惩罚电价，并将其标记为一票否决；
  按政策卡片中的总取水函数、累进税和超限空冷改造规则计算水成本；按驰放比
  计算次生污染物环保税，并在驰放比 > 0.035 时触发清洁生产否决。输出政策
  分项、合规标签、调整后 LCOM 和以 2500 元/t 煤制甲醇价格计算的 MAC。
  检查有限数值和输入范围，为三组标准工况验证标签、补贴、碳费用与成本。
================================================================================
"""

import sys
import io
import numpy as np

# 针对 Windows 控制台编码环境进行 UTF-8 容错封装
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def evaluate_policy_compliance(
    gwp_net: float,
    base_lcom: float,
    e_total_kwh: float,
    f_green: float,
    r_purge: float
) -> dict:
    """
    基于 policy_clauses_pack.md 的四项政策条文，量化评估项目合规状态与净平准化成本。

    参数：
      gwp_net     : 全生命周期净碳足迹 (kg CO2e/t 甲醇)
      base_lcom   : 基础平准化甲醇成本 (元/t 甲醇)
      e_total_kwh : 吨甲醇总综合电耗 (kWh/t 甲醇)
      f_green     : 清洁可再生绿电消纳比例 [0.0, 1.0]
      r_purge     : 循环回路驰放分流比 [0.004, 0.045]

    返回：
      包含调整后 LCOM、调整后 MAC、合规状态标签及各项政策成本分项的字典。
    """
    inputs = (gwp_net, base_lcom, e_total_kwh, f_green, r_purge)
    if not all(np.isfinite(value) for value in inputs):
        raise ValueError("Policy inputs must all be finite numbers.")
    if e_total_kwh < 0 or not 0.0 <= f_green <= 1.0 or r_purge <= 0.0:
        raise ValueError("Energy must be non-negative, f_green in [0, 1], and r_purge positive.")

    # 1. 卡片 1 判定
    is_red_iii = (gwp_net <= 561.2) and (f_green >= 0.80)
    red_iii_subsidy = -1200.0 if is_red_iii else 0.0

    # 2. 卡片 2 判定
    gwp_bench = 2600.0
    p_carbon  = 100.0
    veto_carbon = False

    if gwp_net <= 0.0:
        delta_ghg_ton = (gwp_bench - gwp_net) / 1000.0
        carbon_cost_mod = -1.2 * delta_ghg_ton * p_carbon
    elif gwp_net <= gwp_bench:
        delta_ghg_ton = (gwp_bench - gwp_net) / 1000.0
        carbon_cost_mod = -1.0 * delta_ghg_ton * p_carbon
    else:
        veto_carbon = True
        excess_ghg_ton = (gwp_net - gwp_bench) / 1000.0
        carbon_cost_mod = (+2.0 * excess_ghg_ton * p_carbon) + (0.10 * e_total_kwh)

    # 3. 卡片 3 判定
    w_total = 1.385 + 0.008 * (0.010 / r_purge)
    w_quota = 1.400
    water_retrofit_cost = 0.0
    if w_total <= w_quota:
        water_cost_mod = w_total * 5.0
    elif w_total <= 1.425:
        water_cost_mod = (w_quota * 5.0) + ((w_total - w_quota) * 15.0)
    else:
        water_retrofit_cost = 85.0
        water_cost_mod = (1.390 * 5.0) + water_retrofit_cost

    # 4. 卡片 4 判定
    env_tax_mod = 12.0 + 18.5 * (r_purge / 0.010)
    veto_clean_prod = (r_purge > 0.035)

    # 5. 综合判定
    if veto_carbon or veto_clean_prod:
        status = "Redline_Vetoed"
    elif is_red_iii:
        status = "RED_III_RFNBO_Certified"
    else:
        status = "Domestic_Compliant"

    lcom_adjusted = (
        base_lcom
        + red_iii_subsidy
        + carbon_cost_mod
        + water_cost_mod
        + env_tax_mod
    )

    fossil_price = 2500.0
    ghg_avoided = (gwp_bench - gwp_net) / 1000.0
    if ghg_avoided > 0:
        mac_adjusted = (lcom_adjusted - fossil_price) / ghg_avoided
    else:
        mac_adjusted = np.nan

    return {
        "lcom_policy_adjusted": lcom_adjusted,
        "mac_policy_adjusted": mac_adjusted,
        "compliance_status": status,
        "policy_breakdown": {
            "red_iii_subsidy": red_iii_subsidy,
            "carbon_cost_mod": carbon_cost_mod,
            "water_cost_mod": water_cost_mod,
            "env_tax_mod": env_tax_mod,
            "water_retrofit_cost": water_retrofit_cost,
            "water_total_t_per_t": w_total
        }
    }


# ==============================================================================
# 单元测试自检程序
# ==============================================================================
if __name__ == "__main__":
    print("=" * 80)
    print("《环境规划与管理》任务 2：政策量化引擎 (task2_policy_vibe_engine.py) 单元测试")
    print("=" * 80)

    test_cases = [
        {
            "name": "工况 1：高比例绿电基地情景 (100% 绿电, 驰放比 1.0%)",
            "args": (-1044.1, 2862.3, 10826.0, 1.00, 0.010),
            "expected_status": "RED_III_RFNBO_Certified",
            "expected_red_iii": -1200.0,
            "expected_carbon_mod": -437.29,
            "expected_lcom": 1262.47
        },
        {
            "name": "工况 2：多能互补过渡情景 (65% 绿电, 驰放比 1.5%)",
            "args": (800.0, 4200.0, 10826.0, 0.65, 0.015),
            "expected_status": "Domestic_Compliant",
            "expected_red_iii": 0.0,
            "expected_carbon_mod": -180.0,
            "expected_lcom": 4066.70
        },
        {
            "name": "工况 3：高碳电网反向增排情景 (0% 绿电, 驰放比 1.0%)",
            "args": (4531.3, 7193.0, 10826.0, 0.00, 0.010),
            "expected_status": "Redline_Vetoed",
            "expected_red_iii": 0.0,
            "expected_carbon_mod": 1468.86,
            "expected_lcom": 8699.33
        }
    ]

    all_passed = True
    for tc in test_cases:
        res = evaluate_policy_compliance(*tc["args"])
        status = res["compliance_status"]
        red_iii = res["policy_breakdown"]["red_iii_subsidy"]
        carbon_mod = res["policy_breakdown"]["carbon_cost_mod"]

        status_ok = (status == tc["expected_status"])
        red_iii_ok = abs(red_iii - tc["expected_red_iii"]) < 1e-2
        carbon_ok = abs(carbon_mod - tc["expected_carbon_mod"]) < 0.1
        lcom_ok = abs(res["lcom_policy_adjusted"] - tc["expected_lcom"]) < 0.02

        print(f"\n[{tc['name']}]")
        print(f"  合规状态判定 : {status} (预期: {tc['expected_status']}) -> {'PASS' if status_ok else 'FAIL'}")
        print(f"  欧盟认证补贴 : {red_iii:.2f} 元/t (预期: {tc['expected_red_iii']:.2f}) -> {'PASS' if red_iii_ok else 'FAIL'}")
        print(f"  碳市场调节费 : {carbon_mod:.2f} 元/t (预期: {tc['expected_carbon_mod']:.2f}) -> {'PASS' if carbon_ok else 'FAIL'}")
        print(f"  调整后 LCOM  : {res['lcom_policy_adjusted']:.2f} 元/t")
        print(f"  LCOM 公式核验: {'PASS' if lcom_ok else 'FAIL'} (预期: {tc['expected_lcom']:.2f})")
        print(f"  调整后 MAC   : {res['mac_policy_adjusted']:.2f} 元/t CO2e" if not np.isnan(res['mac_policy_adjusted']) else "  调整后 MAC   : NaN (一票否决)")

        if not (status_ok and red_iii_ok and carbon_ok and lcom_ok):
            all_passed = False

    threshold_at_limit = evaluate_policy_compliance(-1000.0, 3000.0, 10826.0, 1.0, 0.035)
    threshold_above_limit = evaluate_policy_compliance(-1000.0, 3000.0, 10826.0, 1.0, 0.03501)
    threshold_ok = (
        threshold_at_limit["compliance_status"] != "Redline_Vetoed"
        and threshold_above_limit["compliance_status"] == "Redline_Vetoed"
    )
    print(f"\n[清洁生产边界校验] r_purge=3.5%阈值及其上方 -> {'PASS' if threshold_ok else 'FAIL'}")
    all_passed = all_passed and threshold_ok

    print("\n" + "=" * 80)
    if all_passed:
        print("[测试结论] 政策量化引擎完全通过基准自检，可直接接入任务 3 帕累托寻优模型！")
    else:
        print("[测试结论] 存在未通过项，请排查阈值判定与修正项逻辑。")
    print("=" * 80)
