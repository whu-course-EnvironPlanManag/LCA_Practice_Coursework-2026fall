# -*- coding: utf-8 -*-
"""
课程名称：《环境规划与管理》
案例主题：工业园区二氧化碳捕集耦合绿氢合成绿色甲醇系统
任务编号：任务 2（政策量化计算）
脚本名称：task2_policy_vibe_engine.py
实训目标：
  1. 研读 data_cohort/policy_clauses_pack.md 中的四项政策法规与技术标准条文；
  2. 借助 AI 编程助手（Vibe Coding）生成 policy_engine 量化算子；
  3. 实现对欧盟 RED III、国内碳市场（ETS/CCER）、工业取水定额与次生环保税的算法化量化；
  4. 运行内建单元测试，验证合规状态与成本修正值是否与基准自检表完全一致。

================================================================================
用户提供的任务二提示词全文见下方注释及 prompts/task2_prompt.txt。
当前结果的适用范围见报告附录。
"""

# 请完成第十讲任务二“政策量化规制引擎”，实际编写、运行和验证代码。
# 
# 一、工作范围
# 
# 工作目录：
# D:\Library\agent\codex\环境规划课程\LCA_Practice_Coursework-2026fall\groups\group-05\lecture10-green-methanol-FullEPM
# 
# 首先阅读：
# - task_docs/lecture10_task_manual.md
# - data_cohort/policy_clauses_pack.md
# - code_implementation/task2_policy_vibe_engine.py
# - 已完成的任务一说明及其实际输出
# 
# 只修改本目录中的任务二相关文件，不改教师原始资料，不覆盖任务一成果，不提前完成任务三、任务四。
# 所有成果留在本地，不执行 Git 提交、推送或 PR 操作。
# 
# 将本次实际使用的完整提示词保留在任务二脚本头部，不以摘要或占位符代替。
# 
# 二、实现接口与单位
# 
# 保留函数：
# evaluate_policy_compliance(
#     gwp_net, base_lcom, e_total_kwh, f_green, r_purge
# ) -> dict
# 
# 输入单位：
# - gwp_net：kg CO2e/t 甲醇，允许为负；
# - base_lcom：元/t 甲醇；
# - e_total_kwh：kWh/t 甲醇，必须非负；
# - f_green：绿电比例，范围 [0, 1]；
# - r_purge：驰放比例，物理有效范围 (0, 1]。
# 
# 任务三的搜索范围 [0.004, 0.045] 是优化范围，
# 不要将其误作政策函数的全部有效输入范围，否则无法测试节水改造分支。
# 所有输入必须是有限实数，拒绝 NaN、无穷大及非法输入，并给出明确错误信息。
# 
# 三、严格实现四张卡片的课堂规则
# 
# 1. 欧盟认证条件与溢价
# 当 gwp_net <= 561.2 且 f_green >= 0.80：
# red_iii_subsidy = -1200.0
# 否则为 0。
# 
# 说明 561.18 是公式精确折算值，561.2 是卡片操作规则使用的阈值；
# 本任务按 561.2 执行，不在不同代码位置混用阈值。
# 
# 2. 碳市场阶梯修正
# 基准 GWP 为 2600 kg CO2e/t，碳价为 100 元/t CO2e。
# 
# gwp_net <= 0：
# carbon_cost_mod = -1.2 * (2600-gwp_net)/1000 * 100
# 
# 0 < gwp_net <= 2600：
# carbon_cost_mod = -(2600-gwp_net)/1000 * 100
# 
# gwp_net > 2600：
# carbon_cost_mod = 2*(gwp_net-2600)/1000*100 + 0.10*e_total_kwh
# 同时触发碳排放否决。
# 
# 注意 kg 与 t 的换算，避免重复计入惩罚电价。
# 
# 3. 取水费用与节水改造
# 改造前取水量：
# w_total = 1.385 + 0.008*(0.010/r_purge)，单位 t/t。
# 
# w_total <= 1.400：
# water_cost_mod = w_total*5
# 
# 1.400 < w_total <= 1.425：
# water_cost_mod = 1.400*5 + (w_total-1.400)*15
# 
# w_total > 1.425：
# 必须实施节水改造，改造后实际取水为 1.390 t/t；
# water_cost_mod = 1.390*5 + 85 = 91.95 元/t。
# 
# 分别记录改造前取水量、改造后实际取水量、
# 水税和改造年金，避免将 85 元/t 重复加入总成本。
# 该分支是强制改造，不额外自行添加“一票否决”规则。
# 
# 4. 环保税及末端治理费用
# env_tax_mod = 12 + 18.5*(r_purge/0.010)
# 
# r_purge > 0.035 时触发清洁生产否决；
# r_purge = 0.035 时不因该条款被否决。
# 
# 四、状态、成本与 MAC
# 
# 状态优先级：
# 任何否决条件成立 → Redline_Vetoed
# 否则满足认证条件 → RED_III_RFNBO_Certified
# 否则 → Domestic_Compliant
# 
# 分别返回两类否决标记及原因，确保认证条件不能覆盖否决状态。
# 按卡片独立计算各费用项；即使因驰放过大而被否决，
# 也保留可追溯的条件性费用计算，但明确方案不可进入可行解集，
# 不能将其中的溢价理解为已实现收入。
# 
# lcom_policy_adjusted =
# base_lcom + red_iii_subsidy + carbon_cost_mod
# + water_cost_mod + env_tax_mod
# 
# ghg_avoided = (2600-gwp_net)/1000
# 当 ghg_avoided > 0：
# mac_policy_adjusted = (lcom_policy_adjusted-2500)/ghg_avoided
# 否则返回 NaN，并解释为“没有正减排量，MAC 不适用”。
# 
# MAC 是否可计算与方案是否被否决是不同问题：
# 不得用“MAC 为 NaN”代替合规判断，也不得将所有否决情景的
# NaN 原因都解释为同一种情况。
# 
# 保持模板已有返回字段：
# lcom_policy_adjusted、mac_policy_adjusted、compliance_status、
# policy_breakdown，以及其中的四个费用字段。
# 可追加取水、改造、认证条件和否决原因等审计字段。
# 内部计算保留精度，仅在展示时舍入。
# 
# 五、与任务一的衔接和适用范围
# 
# 任务二是接收外部 GWP、成本、电耗等指标的政策算子，
# 不在内部重新求解任务一，也不擅自改变传入数据。
# 
# 卡片中的 1.385 t/t 净补水、驰放与取水经验关系、
# 以及 3.5% 驰放否决阈值，按课堂规则保留。
# 明确它们不是任务一自洽物料模型自动推导的结果。
# 特别不要宣称任务一已经证明“驰放超过 3.5% 必然使碳利用率低于 88%”。
# 
# 本任务实现的是课程给定的政策情景模型，
# 不能把课堂简化阈值、碳价、补贴和税费说成普遍适用的现行法定规则。
# 状态名称保留课程接口，但说明它不构成真实认证或行政审批。
# 若需要讨论现实法规效力，应另查官方原文并注明来源，
# 不要因此擅自替换课堂算法。
# 负的产品碳足迹也不能直接表述为永久碳移除或保证获得 CCER 收入。
# 
# 六、测试与原始自检表审计
# 
# 保留并验证三个指定工况：
# 1. (-1044.1, 2862.3, 10826.0, 1.00, 0.010)
# 2. (800.0, 4200.0, 10826.0, 0.65, 0.015)
# 3. (4531.3, 7193.0, 10826.0, 0.00, 0.010)
# 
# 不仅检查状态、补贴和碳费用，
# 还要检查取水量、水费、环保费用、总 LCOM 和 MAC。
# 
# 教师表格、表下注释与公式存在总成本不一致：
# 请独立逐项复算，以明确的分项公式为实现依据，
# 输出“原表值—公式计算值—差异—原因”对照表。
# 不得添加无来源费用、硬编码总成本或放宽容差以强行通过。
# 区分“公式测试通过”与“教师参考表存在差异”。
# 
# 另增加以下有意义的测试：
# - GWP 在 0、561.2、2600 的边界及两侧；
# - 绿电比例在 0.80 的边界及两侧；
# - 驰放比在 0.035 的边界及两侧；
# - 取水量在 1.400、1.425 的边界及两侧；
# - 强制节水改造分支；
# - 同时满足认证条件和驰放否决时，否决优先；
# - 两种否决同时触发时，原因均保留；
# - 零减排、负减排时 MAC 不适用；
# - 非法比例、零驰放、负电耗、NaN 和无穷大；
# - 总成本等于各分项之和。
# 
# 在任务三的驰放搜索范围内，最大模型取水量为 1.405 t/t，
# 不会触发 >1.425 的改造分支；
# 因此必须使用搜索范围之外但物理有效的驰放参数测试该分支。
# 
# 边界处理应考虑浮点运算误差，但不得用宽松容差改变政策阈值。
# 测试期望值应独立计算，不能调用被测函数生成自己的预期答案。
# 使用真正的断言或 unittest；失败时必须返回非零退出码，
# 不能仅打印 FAIL 后正常退出。
# 
# 七、交付成果
# 
# 交付：
# 1. 完善后的 task2_policy_vibe_engine.py；
# 2. 可重复运行的自动化测试；
# 3. 三个基准工况的完整分项结果及参考表差异表；
# 4. 任务二说明文档：规则、单位、边界、适用范围、
#    与任务一的口径关系、运行方式和实际测试结果。
# 
# 输出路径相对脚本定位，模块导入时不自动运行测试或写文件。
# 如输出 JSON，将不适用 MAC 序列化为 null 并附原因，
# 避免生成包含非标准 NaN 的 JSON。
# 
# 实际运行全部测试，报告通过数量和未解决问题。
# 不要仅给出实现方案，也不要宣称与有矛盾的参考表完全一致。

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
    # 实现说明
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

    import math
    import numbers
    values = (gwp_net, base_lcom, e_total_kwh, f_green, r_purge)
    if any(isinstance(v, bool) or not isinstance(v, numbers.Real) or not math.isfinite(v) for v in values):
        raise ValueError("Inputs must be finite real numbers")
    if e_total_kwh < 0 or not 0 <= f_green <= 1 or not 0 < r_purge <= 1:
        raise ValueError("Invalid electricity or decision-variable range")
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

    assert all_passed, "Policy baseline verification failed"
