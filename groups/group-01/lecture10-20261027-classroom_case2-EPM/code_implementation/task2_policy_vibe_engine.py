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
【Vibe Coding 提示词记录 (Prompt Log)】

Prompt 1（首轮生成）
  请阅读 data_cohort/policy_clauses_pack.md 中的四项政策条文卡片，用 Python 编写
  函数 evaluate_policy_compliance(gwp_net, base_lcom, e_total_kwh, f_green, r_purge)，
  返回字典（lcom_policy_adjusted、mac_policy_adjusted、compliance_status、
  policy_breakdown）。严格执行：
  (1) 欧盟 RED III：gwp_net <= 561.2 且 f_green >= 0.80 时补贴 -1200.0 元/t，否则 0；
  (2) 国内碳市场：基准 2600.0 kg CO2e/t、碳价 100.0 元/t；gwp_net <= 0 用 1.2 倍
      CCER 激励，0 < gwp_net <= 2600.0 用 1.0 倍配额收益，gwp_net > 2600.0 触发
      Redline_Vetoed 并按 2.0 倍惩罚碳价对超额部分计费、另加 0.10 元/kWh 阶梯电价；
  (3) 取水定额：w_total = 1.385 + 0.008*(0.010/r_purge)，定额 1.400 t/t 内按
      5.0 元/t；1.400 < w_total <= 1.425 时超出部分按 15.0 元/t 累进；w_total >
      1.425 时追加 85.0 元/t 空冷技改摊销，取水压降至 1.390 t/t 计税；
  (4) 次生环保税：12.0 + 18.5*(r_purge/0.010)；r_purge > 0.035 触发清洁生产一票否决；
  (5) 状态优先级：任一否决 -> Redline_Vetoed；否则满足欧盟认证 -> RED_III_RFNBO_Certified；
      否则 Domestic_Compliant；
  (6) MAC = (lcom_policy_adjusted - 2500.0) / ((2600.0 - gwp_net)/1000.0)，分母非正时返回 NaN。

Prompt 2（复核修正）
  请逐项复核（1）—（6）的阈值边界是否与条文精确一致，特别检查：碳市场三级判定应使用
  <= 0 与 <= 2600.0 的闭区间；取水定额累进应以 1.400 为计税分界而非 1.425；一票否决
  判定优先于欧盟认证标签。随后在脚本末尾加入三组临界工况单元测试，只校验状态标签、
  欧盟补贴与碳市场调节费三项（总平准化成本因基准自检表存在算术偏差，仅作参照输出）。

【复核说明】
  基准自检表（policy_clauses_pack.md 第四节）所列总平准化成本与其自身注释中的分项
  算术结果不一致：工况 1 表列 1262.51 而分项合计为 1262.48（偏差 0.03 元/t）；
  工况 2 表列 4089.47 而分项合计为 4066.70（偏差 22.77 元/t）；工况 3 表列 8706.36
  而分项合计为 8699.33（偏差 7.03 元/t）。本脚本以条文公式为唯一权威口径，并在
  单元测试中以“公式复算值”作为判定基准，同时打印与表列的偏差供核对。
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
    # 
    # 步骤 1：卡片 1 - 欧盟 RED III 判定 (基准 1870.6 kg/t，减排 >= 70% 阈值为 +561.2 kg/t，f_green >= 80%)
    #         达标获得国际航运溢价补贴 red_iii_subsidy = -1200.0 元/t，否则为 0.0
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
    if w_total <= w_quota:
        water_cost_mod = w_total * 5.0
    elif w_total <= 1.425:
        water_cost_mod = (w_quota * 5.0) + ((w_total - w_quota) * 15.0)
    else:
        water_cost_mod = (1.390 * 5.0) + 85.0

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
            "expected_carbon_mod": -437.29,
            "table_lcom": 1262.51,
            "formula_lcom": 1262.48
        },
        {
            "name": "工况 2：多能互补过渡情景 (65% 绿电, 驰放比 1.5%)",
            "args": (800.0, 4200.0, 10826.0, 0.65, 0.015),
            "expected_status": "Domestic_Compliant",
            "expected_red_iii": 0.0,
            "expected_carbon_mod": -180.0,
            "table_lcom": 4089.47,
            "formula_lcom": 4066.70
        },
        {
            "name": "工况 3：高碳电网反向增排情景 (0% 绿电, 驰放比 1.0%)",
            "args": (4531.3, 7193.0, 10826.0, 0.00, 0.010),
            "expected_status": "Redline_Vetoed",
            "expected_red_iii": 0.0,
            "expected_carbon_mod": 1468.86,
            "table_lcom": 8706.36,
            "formula_lcom": 8699.33
        }
    ]

    all_passed = True
    for tc in test_cases:
        res = evaluate_policy_compliance(*tc["args"])
        status = res["compliance_status"]
        red_iii = res["policy_breakdown"]["red_iii_subsidy"]
        carbon_mod = res["policy_breakdown"]["carbon_cost_mod"]
        water_mod = res["policy_breakdown"]["water_cost_mod"]
        env_tax = res["policy_breakdown"]["env_tax_mod"]
        lcom = res["lcom_policy_adjusted"]

        status_ok = (status == tc["expected_status"])
        red_iii_ok = abs(red_iii - tc["expected_red_iii"]) < 1e-2
        carbon_ok = abs(carbon_mod - tc["expected_carbon_mod"]) < 0.1
        lcom_ok = abs(lcom - tc["formula_lcom"]) < 0.05

        print(f"\n[{tc['name']}]")
        print(f"  合规状态判定 : {status} (预期: {tc['expected_status']}) -> {'PASS' if status_ok else 'FAIL'}")
        print(f"  欧盟认证补贴 : {red_iii:.2f} 元/t (预期: {tc['expected_red_iii']:.2f}) -> {'PASS' if red_iii_ok else 'FAIL'}")
        print(f"  碳市场调节费 : {carbon_mod:.2f} 元/t (预期: {tc['expected_carbon_mod']:.2f}) -> {'PASS' if carbon_ok else 'FAIL'}")
        print(f"  取水/环保税费: {water_mod:.3f} + {env_tax:.3f} 元/t")
        print(f"  调整后 LCOM  : {lcom:.2f} 元/t (分项公式复算 {tc['formula_lcom']:.2f}) -> {'PASS' if lcom_ok else 'FAIL'}")
        print(f"  自检表列值   : {tc['table_lcom']:.2f} 元/t，与本模型偏差 {lcom - tc['table_lcom']:+.2f} 元/t")
        print(f"  调整后 MAC   : {res['mac_policy_adjusted']:.2f} 元/t CO2e" if not np.isnan(res['mac_policy_adjusted']) else "  调整后 MAC   : NaN (一票否决)")

        if not (status_ok and red_iii_ok and carbon_ok and lcom_ok):
            all_passed = False

    print("\n" + "=" * 80)
    if all_passed:
        print("[测试结论] 政策量化引擎四项关键判据全部 PASS（状态 / 欧盟补贴 / 碳市场调节费 / 公式总账）。")
        print("           基准自检表所列总平准化成本存在算术偏差，已在上述逐项偏差行标注，")
        print("           本引擎以 policy_clauses_pack.md 条文公式为唯一权威口径。")
    else:
        print("[测试结论] 存在未通过项，请排查阈值判定与修正项逻辑。")
    print("=" * 80)
