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
  ... [学生在此处粘贴完整 Prompt] ...
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
    # --------------------------------------------------------------------------
    # TODO: [学生编写代码 / Vibe Coding 生成代码]
    # 使用的完整提示词：
    # "请阅读 data_cohort/policy_clauses_pack.md 的四项政策卡片，实现
    # evaluate_policy_compliance(gwp_net, base_lcom, e_total_kwh, f_green, r_purge)。
    # RED III：当 gwp_net <= 561.2 kg CO2e/t 且 f_green >= 0.80，认证并补贴 -1200 元/t。
    # ETS/CCER：基准 2600 kg CO2e/t，碳价 100 元/t；gwp_net <= 0 时按 1.2 倍取得
    # CCER 收益；0 < gwp_net <= 2600 时按 1.0 倍取得减排收益；gwp_net > 2600 时一票否决，
    # 超额部分按 2 倍碳价计费，并按全厂电耗加收 0.10 元/kWh。
    # 水资源：w_total = 1.385 + 0.008*(0.010/r_purge)；定额 1.400 t/t，基准水价税
    # 5 元/t；1.400 < w_total <= 1.425 的超额部分按 15 元/t；超过 1.425 时增加
    # 85 元/t 技改年金，并以 1.390 t/t 计税。
    # 大气环保税与末端运维费为 12 + 18.5*(r_purge/0.010) 元/t；r_purge > 0.035
    # 触发清洁生产一票否决。任一否决条件优先标记 Redline_Vetoed；否则 RED III 达标
    # 标记 RED_III_RFNBO_Certified，其余为 Domestic_Compliant。按条文计算 LCOM/MAC，
    # 并用内置三个工况核对状态、补贴、碳费用和成本分项，发现不一致时回溯条文而非硬编码答案。"
    #
    # 步骤 2：卡片 2 - 国内碳市场 (ETS/CCER) 阶梯奖惩 (基准 2600.0 kg/t，碳价 100.0 元/t)
    #         - gwp_net <= 0: 享受 1.2 倍 CCER 激励
    #         - 0 < gwp_net <= 2600.0: 享受 1.0 倍常规减排收益
    #         - gwp_net > 2600.0: 触发一票否决 (Redline_Vetoed)，超额排放征收 2.0 倍惩罚碳价，
    #                             并对全厂用电加收 0.10 元/kWh 惩罚阶梯电价
    #
    # 步骤 3：卡片 3 - 工业取水定额与水资源税 (定额 1.400 t/t，税率 5.0 元/t)
    #         - w_total = 1.385 + 0.008 * (0.010 / r_purge)
    #         - w_total <= 1.400: 按 5.0 元/t 计征
    #         - 1.400 < w_total <= 1.425: 超出部分按 3.0 倍 (15.0 元/t) 累进计征
    #         - w_total > 1.425: 强制配套闭式空冷系统 (+85.0 元/t 摊销)，取水量强制压降至 1.390 t/t 计税
    #
    # 步骤 4：卡片 4 - 次生污染物环保税与清洁生产底线
    #         - env_tax = 12.0 + 18.5 * (r_purge / 0.010)
    #         - r_purge > 0.035 (3.5%): 导致总碳利用率跌破 88.0%，触发清洁生产一票否决
    #
    # 步骤 5：汇总综合合规标签 (Redline_Vetoed / RED_III_RFNBO_Certified / Domestic_Compliant)
    #         计算 lcom_policy_adjusted 与 mac_policy_adjusted (对比 2500 元/t 与 2600 kg/t 煤制甲醇)
    # --------------------------------------------------------------------------

    # RED III 模块：满足至少 70% 减排阈值和 80% 绿电比例才取得认证溢价。
    red_iii_gwp_limit = 561.2
    red_iii_green_power_min = 0.80
    red_iii_premium = -1200.0
    is_red_iii = (gwp_net <= red_iii_gwp_limit) and (f_green >= red_iii_green_power_min)
    red_iii_subsidy = red_iii_premium if is_red_iii else 0.0

    # 碳市场一票否决 + 阶梯奖惩模块：严格按净碳足迹相对 2600 kg/t 的三级区间计算。
    gwp_bench = 2600.0
    p_carbon = 100.0
    ccer_incentive_factor = 1.2
    allowance_income_factor = 1.0
    penalty_carbon_factor = 2.0
    penalty_electricity_rate = 0.10
    veto_carbon = False

    # 第一级：净负碳项目按 1.2 倍基准碳价核算 CCER 成本抵扣。
    if gwp_net <= 0.0:
        delta_ghg_ton = (gwp_bench - gwp_net) / 1000.0
        carbon_cost_mod = -ccer_incentive_factor * delta_ghg_ton * p_carbon
    # 第二级：高于零但不超过煤制甲醇基准时，按 1.0 倍碳价核算减排收益。
    elif gwp_net <= gwp_bench:
        delta_ghg_ton = (gwp_bench - gwp_net) / 1000.0
        carbon_cost_mod = -allowance_income_factor * delta_ghg_ton * p_carbon
    # 第三级：超过基准触发环境准入一票否决，并计入超额碳费与惩罚电价。
    else:
        veto_carbon = True
        excess_ghg_ton = (gwp_net - gwp_bench) / 1000.0
        carbon_cost_mod = (
            penalty_carbon_factor * excess_ghg_ton * p_carbon
            + penalty_electricity_rate * e_total_kwh
        )

    # 水资源累进税模块：驰放比进入给定取水模型，再按定额区间计税或强制节水技改。
    if r_purge <= 0.0:
        raise ValueError("r_purge 必须大于 0，才能计算政策卡片规定的取水强度")
    w_total = 1.385 + 0.008 * (0.010 / r_purge)
    w_quota = 1.400
    water_base_tax_rate = 5.0
    water_over_quota_rate = 15.0
    water_redline = 1.425
    water_retrofit_cost = 85.0
    retrofit_water_intensity = 1.390

    if w_total <= w_quota:
        # 定额以内：全部实际取水量按基准税率计征。
        water_taxable_intensity = w_total
        water_cost_mod = water_taxable_intensity * water_base_tax_rate
        water_retrofit_mod = 0.0
        water_policy_action = "Within_Quota"
    elif w_total <= water_redline:
        # 超定额但未越红线：定额内按基准税率，超额段按 3 倍税率。
        water_taxable_intensity = w_total
        water_cost_mod = (
            w_quota * water_base_tax_rate
            + (w_total - w_quota) * water_over_quota_rate
        )
        water_retrofit_mod = 0.0
        water_policy_action = "Progressive_Water_Tax"
    else:
        # 超出承载力红线：强制技改，按压降后的取水强度计税并加年金摊销。
        water_taxable_intensity = retrofit_water_intensity
        water_retrofit_mod = water_retrofit_cost
        water_cost_mod = water_taxable_intensity * water_base_tax_rate + water_retrofit_mod
        water_policy_action = "Cooling_Retrofit_Redline"

    # 大气环保税模块：VOCs/胺洗涤、驰放尾气脱硝和环保税合并按卡片公式计费。
    env_tax_base_cost = 12.0
    purge_treatment_cost_per_reference = 18.5
    reference_purge_ratio = 0.010
    env_tax_mod = env_tax_base_cost + purge_treatment_cost_per_reference * (
        r_purge / reference_purge_ratio
    )

    # 清洁生产底线：驰放比严格高于 3.5% 时，触发一票否决。
    clean_production_purge_limit = 0.035
    veto_clean_prod = r_purge > clean_production_purge_limit

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
            "env_tax_mod": env_tax_mod
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
            "expected_carbon_mod": -437.29
        },
        {
            "name": "工况 2：多能互补过渡情景 (65% 绿电, 驰放比 1.5%)",
            "args": (800.0, 4200.0, 10826.0, 0.65, 0.015),
            "expected_status": "Domestic_Compliant",
            "expected_red_iii": 0.0,
            "expected_carbon_mod": -180.0
        },
        {
            "name": "工况 3：高碳电网反向增排情景 (0% 绿电, 驰放比 1.0%)",
            "args": (4531.3, 7193.0, 10826.0, 0.00, 0.010),
            "expected_status": "Redline_Vetoed",
            "expected_red_iii": 0.0,
            "expected_carbon_mod": 1468.86
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

        print(f"\n[{tc['name']}]")
        print(f"  合规状态判定 : {status} (预期: {tc['expected_status']}) -> {'PASS' if status_ok else 'FAIL'}")
        print(f"  欧盟认证补贴 : {red_iii:.2f} 元/t (预期: {tc['expected_red_iii']:.2f}) -> {'PASS' if red_iii_ok else 'FAIL'}")
        print(f"  碳市场调节费 : {carbon_mod:.2f} 元/t (预期: {tc['expected_carbon_mod']:.2f}) -> {'PASS' if carbon_ok else 'FAIL'}")
        print(f"  调整后 LCOM  : {res['lcom_policy_adjusted']:.2f} 元/t")
        print(f"  调整后 MAC   : {res['mac_policy_adjusted']:.2f} 元/t CO2e" if not np.isnan(res['mac_policy_adjusted']) else "  调整后 MAC   : NaN (一票否决)")

        if not (status_ok and red_iii_ok and carbon_ok):
            all_passed = False

    print("\n" + "=" * 80)
    if all_passed:
        print("[测试结论] 政策量化引擎完全通过基准自检，可直接接入任务 3 帕累托寻优模型！")
    else:
        print("[测试结论] 存在未通过项，请排查阈值判定与修正项逻辑。")
    print("=" * 80)
