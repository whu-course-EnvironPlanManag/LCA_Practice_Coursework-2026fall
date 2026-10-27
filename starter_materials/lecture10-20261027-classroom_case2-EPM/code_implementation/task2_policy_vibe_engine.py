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

    # =========================================================================
    # 卡片 1：欧盟 RED III RFNBO 认证判定
    # 条文推导（policy_clauses_pack.md L47-59）：
    #   化石燃料基准线 E_F = 94.0 g CO2e/MJ
    #   精甲醇低位发热量 = 19,900 MJ/t
    #   → GWP_fossil_ref = 94.0e-3 × 19,900 = 1,870.6 kg CO2e/t
    #   减排阈值 GWP_net <= 1,870.6 × (1 - 70%) = +561.2 kg CO2e/t
    #   绿电准入 f_green >= 80.0%
    #   达标补贴 -1,200.0 元/t
    # =========================================================================
    EF_fossil_benchmark = 94.0e-3           # kg CO2e/MJ（条文 L47）
    LHV_methanol_MJ_per_t = 19900.0         # MJ/t（条文 L47）
    REDUCTION_RATE = 0.70                   # 70% 强制减排（条文 L51）
    MIN_F_GREEN = 0.80                      # 绿电比例下限（条文 L51）
    SUBSIDY_RFNB0 = -1200.0                 # 国际航运溢价补贴（条文 L58）

    gwp_fossil_ref = EF_fossil_benchmark * LHV_methanol_MJ_per_t   # = 1,870.6
    gwp_red_iii_threshold = gwp_fossil_ref * (1 - REDUCTION_RATE)   # = +561.2

    is_red_iii = (gwp_net <= gwp_red_iii_threshold) and (f_green >= MIN_F_GREEN)
    red_iii_subsidy = SUBSIDY_RFNB0 if is_red_iii else 0.0

    # =========================================================================
    # 卡片 2：国内碳市场 ETS/CCER 阶梯奖惩
    # 条文推导（policy_clauses_pack.md L67-80）：
    #   国内煤制甲醇行业 GWP_bench = +2,600.0 kg CO2e/t（条文 L67）
    #   全国碳市场结算碳价 P_carbon = 100.0 元/t CO2e（条文 L67）
    #   三级阶梯：负碳示范(1.2x) / 常规减排(1.0x) / 反向增排否决(2.0x + 惩罚电价)
    # =========================================================================
    gwp_bench = 2600.0       # kg CO2e/t 煤制甲醇基准（条文 L67）
    p_carbon  = 100.0        # 元/t CO2e 碳价（条文 L67）
    EXCESS_PENALTY_RATE = 2.0            # 超额排放惩罚系数（条文 L77）
    PENALTY_ELECTRICITY = 0.10           # 惩罚阶梯电价 元/kWh（条文 L77）
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

    # =========================================================================
    # 卡片 3：工业取水定额 + 超定额累进税率
    # 条文推导（policy_clauses_pack.md L87-100）：
    #   PEM 电解槽除盐纯水理论净消耗 = 1.385 t/t（扣除精馏副产回水 0.575 t/t）
    #   循环冷却蒸发散失量随驰放比降低而上升 → W_total 模型（条文 L89）
    #   阶梯税率：5.0 元/t（定额内）→ 15.0 元/t（超定额累进）→ +85 元/t（强制空冷技改）
    # =========================================================================
    W_BASIS = 1.385                                 # t 水/t 甲醇（条文 L87）
    W_QUOTA = 1.400                                 # 取水定额红线（条文 L92）
    W_RETROFIT_THRESHOLD = 1.425                    # 强制技改阈值（条文 L97）
    W_AFTER_RETROFIT = 1.390                        # 技改后实际取水（条文 L97）
    BASE_WATER_TAX = 5.0                            # 基准税率 元/t（条文 L92）
    SURCHARGE_WATER_TAX = 15.0                      # 超定额累进税率（条文 L93）
    RETROFIT_COST = 85.0                            # 闭式空冷技改年金摊销 元/t（条文 L97）

    w_total = W_BASIS + 0.008 * (0.010 / r_purge)  # 条文 L89 给定的吨水消耗模型
    if w_total <= W_QUOTA:
        water_cost_mod = w_total * BASE_WATER_TAX
    elif w_total <= W_RETROFIT_THRESHOLD:
        water_cost_mod = (W_QUOTA * BASE_WATER_TAX) + ((w_total - W_QUOTA) * SURCHARGE_WATER_TAX)
    else:
        water_cost_mod = (W_AFTER_RETROFIT * BASE_WATER_TAX) + RETROFIT_COST

    # =========================================================================
    # 卡片 4：次生环保税 + 清洁生产物料转化利用率红线
    # 条文推导（policy_clauses_pack.md L109-118）：
    #   污染源：MEA 吸收剂 VOCs 逸散 + 驰放气掺烧 NOx
    #   环保税核算模型（条文 L114）
    #   清洁生产红线：r_purge > 0.035 → 总碳利用率 < 88.0% → 一票否决
    # =========================================================================
    BASE_ENV_TAX = 12.0                             # 基准环保税 元/t（条文 L114）
    VARIABLE_ENV_TAX_COEFF = 18.5                   # 随驰放比变化系数（条文 L114）
    CLEAN_PRODUCTION_PURGE_LIMIT = 0.035            # 清洁生产驰放比红线（条文 L118）

    env_tax_mod = BASE_ENV_TAX + VARIABLE_ENV_TAX_COEFF * (r_purge / 0.010)
    veto_clean_prod = (r_purge > CLEAN_PRODUCTION_PURGE_LIMIT)

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

    # MAC = (LCOM_adj - P_fossil) / GHG_avoided
    # P_fossil = 2,500 元/t 煤制甲醇市场参考价（条文提示）
    fossil_price = 2500.0
    ghg_avoided = (gwp_bench - gwp_net) / 1000.0  # 减排量 t CO2e/t 甲醇
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
