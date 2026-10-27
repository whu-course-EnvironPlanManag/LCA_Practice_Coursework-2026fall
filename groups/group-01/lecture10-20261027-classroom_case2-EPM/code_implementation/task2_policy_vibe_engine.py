# -*- coding: utf-8 -*-
"""任务2：按同组 policy_clauses_pack.md 四张课程卡片计算政策修正。

术语：物质流分析 MFA (Material Flow Analysis)、全生命周期评价 LCA
(Life Cycle Assessment)、技术经济分析 TEA (Techno-Economic Analysis)；
全球变暖潜势 GWP (Global Warming Potential)、平准化甲醇成本
LCOM (Levelized Cost of Methanol)、边际减排成本 MAC (Marginal Abatement Cost)；
欧盟《可再生能源指令》第三版 RED III (Renewable Energy Directive III)、
非生物源可再生燃料 RFNBO (Renewable Fuels of Non-Biological Origin)、
碳排放权交易体系 ETS (Emissions Trading System)、国家核证自愿减排量
CCER (China Certified Emission Reduction)。

【完整使用的 Prompt】
【角色】你是一名精通mfa,lca,tea的环境规划管理专家以及精通python编程的专家
【任务】请你阅读groups\\group-01\\lecture10-20261027-classroom_case2-EPM文件夹中的groups\\group-01\\lecture10-20261027-classroom_case2-EPM\\task_docs\\background_engineering_docs.md文件中的内容，阅读完成后研读 data_cohort/policy_clauses_pack.md 中的四张政策卡片（欧盟 RED III 准入与溢价、中国碳市场阶梯奖惩与两高一票否决、工业取水定额累进水资源税、次生大气污染物环保税与清洁生产底线），并按照文档中的要求完成groups\\group-01\\lecture10-20261027-classroom_case2-EPM\\task_docs\\lecture10_task_manual.md中的任务2，完成后无需进行git的push操作，只需进行add与commit操作，且需要在我当前分支进行git的相关操作。
【输入】来自groups\\group-01\\lecture10-20261027-classroom_case2-EPM\\task_docs\\background_engineering_docs.md以及groups\\group-01\\lecture10-20261027-classroom_case2-EPM\\data_cohort中的相关文件，还有data_cohort/policy_clauses_pack.md
【输出】完成groups\\group-01\\lecture10-20261027-classroom_case2-EPM\\task_docs\\lecture10_task_manual.md文件中的任务2，编写groups\\group-01\\lecture10-20261027-classroom_case2-EPM\\code_implementation\\task2_policy_vibe_engine.py文件。若触发任何一票否决项，状态标记为 'Redline_Vetoed'；否则若满足欧盟认证，标记为 'RED_III_RFNBO_Certified'；否则标记为 'Domestic_Compliant'。计算政策修正后平准化成本 lcom_policy_adjusted 与边际减排成本 mac_policy_adjusted（以煤制甲醇价格 2500.0 元/t 与碳排 2600.0 kg/t 为参考）。在代码文件末尾编写单元测试，对标准自检表中的三个典型工况进行验证。
【限制】严格按照四张政策卡片中的内容进行分析。

【实现口径与资料差异】
1. 按卡片1第3款及参考Prompt的明确条件，认证阈值取561.2 kg/t；
   卡片同页推导的561.18为未取整值，程序不再对输入GWP预先舍入。
2. 卡片3的超水量红线要求强制技改，技改后按1.390 t/t计税，非一票否决。
3. 状态优先级为否决 > 欧盟认证 > 国内达标。各成本分项仍按各自公式
   计算；卡片未规定否决时撤回补贴，不另设撤回规则。否决方案不得因成本
   低而参与合规方案比选。MAC仅在正向减排时定义；无减排/反向增排返回NaN。
4. 原表三个工况的LCOM列与卡片公式不一致；完整精度计算分别得到
   1262.473、4066.701666666667、8699.325元/t。保留原表值供审计，
   不调整公式去匹配原表，不使用中间费用的两位小数显示值继续计算。

运行：python task2_policy_vibe_engine.py（标准工况报告及全部单元测试）
      python task2_policy_vibe_engine.py --self-test（仅运行测试）
本函数直接接收MFA/LCA/TEA上游结果，不重新标定其GWP、电耗或基础成本。
"""

import argparse
import math
import sys
import unittest

# 参数均来自四张政策卡片；煤制成本基准同时见工程背景第4.3节。
RED_III_GWP_LIMIT = 561.2
RED_III_GREEN_SHARE_MIN = 0.80
RED_III_SUBSIDY = -1200.0
GWP_BENCHMARK = 2600.0
FOSSIL_METHANOL_PRICE = 2500.0
CARBON_PRICE = 100.0
WATER_QUOTA = 1.400
WATER_RETROFIT_LIMIT = 1.425
CLEAN_PRODUCTION_PURGE_LIMIT = 0.035


def _finite_scalar(name, value):
    """无效输入抛错，避免NaN因比较结果为False而被误判成达标。"""
    if isinstance(value, (bool, str, bytes)):
        raise ValueError(f"{name}必须为有限实数")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{name}必须为有限实数") from error
    if not math.isfinite(number):
        raise ValueError(f"{name}必须为有限实数")
    return number


def evaluate_policy_compliance(
    gwp_net: float,
    base_lcom: float,
    e_total_kwh: float,
    f_green: float,
    r_purge: float,
) -> dict:
    """执行四张卡片，保持任务3所用的参数及原有返回键。

    gwp_net: kg CO2e/t甲醇；base_lcom: 元/t甲醇；e_total_kwh: kWh/t甲醇；
    f_green: 绿电占比[0,1]；r_purge: 物理驰放分流比(0,1]。
    任务3搜索范围[0.004,0.045]是该任务的工况约束，并非本政策函数的
    适用边界；允许更低的合法驰放比以执行卡片3的强制空冷技改规则。
    所有费用正数加成本、负数抵扣成本；不对中间结果取整。
    """
    gwp_net = _finite_scalar("gwp_net", gwp_net)
    base_lcom = _finite_scalar("base_lcom", base_lcom)
    e_total_kwh = _finite_scalar("e_total_kwh", e_total_kwh)
    f_green = _finite_scalar("f_green", f_green)
    r_purge = _finite_scalar("r_purge", r_purge)
    if e_total_kwh < 0:
        raise ValueError("e_total_kwh不能为负")
    if not 0 <= f_green <= 1:
        raise ValueError("f_green必须在[0,1]内")
    if not 0 < r_purge <= 1:
        raise ValueError("r_purge必须在(0,1]内")

    # 卡片1：两个条件同时满足才获得认证溢价。
    is_red_iii = gwp_net <= RED_III_GWP_LIMIT and f_green >= RED_III_GREEN_SHARE_MIN
    red_iii_subsidy = RED_III_SUBSIDY if is_red_iii else 0.0

    # 卡片2：kg换算t后使用100元/t CO2e碳价；惩罚电价仅在碳超标时加收。
    ghg_avoided_ton = (GWP_BENCHMARK - gwp_net) / 1000.0
    veto_carbon = gwp_net > GWP_BENCHMARK
    if gwp_net <= 0:
        carbon_cost_mod = -1.2 * ghg_avoided_ton * CARBON_PRICE
    elif not veto_carbon:
        carbon_cost_mod = -ghg_avoided_ton * CARBON_PRICE
    else:
        carbon_cost_mod = -2.0 * ghg_avoided_ton * CARBON_PRICE + 0.10 * e_total_kwh

    # 卡片3：取水总量含净补水和冷却蒸发，超定额部分累进计税。
    w_total = 1.385 + 0.008 * (0.010 / r_purge)
    retrofit_required = w_total > WATER_RETROFIT_LIMIT
    if w_total <= WATER_QUOTA:
        w_actual, water_tax, retrofit_cost = w_total, w_total * 5.0, 0.0
    elif not retrofit_required:
        w_actual = w_total
        water_tax = WATER_QUOTA * 5.0 + (w_total - WATER_QUOTA) * 15.0
        retrofit_cost = 0.0
    else:
        w_actual, water_tax, retrofit_cost = 1.390, 1.390 * 5.0, 85.0
    water_cost_mod = water_tax + retrofit_cost

    # 卡片4：环保税包含末端治理运维；3.5%本身未超过否决线。
    env_tax_mod = 12.0 + 18.5 * (r_purge / 0.010)
    veto_clean_prod = r_purge > CLEAN_PRODUCTION_PURGE_LIMIT
    if veto_carbon or veto_clean_prod:
        status = "Redline_Vetoed"
    elif is_red_iii:
        status = "RED_III_RFNBO_Certified"
    else:
        status = "Domestic_Compliant"

    breakdown = {"red_iii_subsidy": red_iii_subsidy, "carbon_cost_mod": carbon_cost_mod,
                 "water_cost_mod": water_cost_mod, "env_tax_mod": env_tax_mod}
    lcom_adjusted = base_lcom + sum(breakdown.values())
    mac_adjusted = ((lcom_adjusted - FOSSIL_METHANOL_PRICE) / ghg_avoided_ton
                    if ghg_avoided_ton > 0 else math.nan)
    reasons = []
    if veto_carbon:
        reasons.append("carbon_emissions_above_benchmark")
    if veto_clean_prod:
        reasons.append("purge_ratio_above_clean_production_limit")
    return {
        "lcom_policy_adjusted": lcom_adjusted,
        "mac_policy_adjusted": mac_adjusted,
        "compliance_status": status,
        "policy_breakdown": breakdown,
        "red_iii_eligible": is_red_iii,
        "veto_carbon": veto_carbon,
        "veto_clean_prod": veto_clean_prod,
        "veto_reasons": reasons,
        "ghg_avoided_ton": ghg_avoided_ton,
        "water_use_before_retrofit_t_per_t": w_total,
        "water_use_actual_t_per_t": w_actual,
        "water_retrofit_required": retrofit_required,
        "water_tax_cost": water_tax,
        "water_retrofit_cost": retrofit_cost,
    }


# 以下输入/状态/补贴/表列总成本原样摘自政策包标准表。
# formula_lcom由卡片公式逐项计算，保留全精度，独立于原表错误的总成本列。
STANDARD_CASES = (
    {"name": "工况1：高比例绿电基地", "args": (-1044.1, 2862.3, 10826.0, 1.0, 0.010),
     "status": "RED_III_RFNBO_Certified", "subsidy": -1200.0, "carbon_display": -437.29,
     "water": 6.965, "env": 30.5, "formula_lcom": 1262.473, "table_lcom": 1262.51},
    {"name": "工况2：多能互补过渡", "args": (800.0, 4200.0, 10826.0, 0.65, 0.015),
     "status": "Domestic_Compliant", "subsidy": 0.0, "carbon_display": -180.0,
     "water": 6.951666666666667, "env": 39.75,
     "formula_lcom": 4066.701666666667, "table_lcom": 4089.47},
    {"name": "工况3：高碳电网反向增排", "args": (4531.3, 7193.0, 10826.0, 0.0, 0.010),
     "status": "Redline_Vetoed", "subsidy": 0.0, "carbon_display": 1468.86,
     "water": 6.965, "env": 30.5, "formula_lcom": 8699.325, "table_lcom": 8706.36},
)


# 单元测试放在文件末尾；直接运行时失败将返回非零退出码。
class PolicyEngineTests(unittest.TestCase):
    def test_three_standard_cases(self):
        names = ("gwp_net", "base_lcom", "e_total_kwh", "f_green", "r_purge")
        for case in STANDARD_CASES:
            with self.subTest(case=case["name"]):
                res = evaluate_policy_compliance(**dict(zip(names, case["args"])))
                costs = res["policy_breakdown"]
                self.assertEqual(res["compliance_status"], case["status"])
                self.assertEqual(costs["red_iii_subsidy"], case["subsidy"])
                self.assertEqual(round(costs["carbon_cost_mod"], 2), case["carbon_display"])
                self.assertAlmostEqual(costs["water_cost_mod"], case["water"], places=10)
                self.assertAlmostEqual(costs["env_tax_mod"], case["env"], places=10)
                self.assertAlmostEqual(res["lcom_policy_adjusted"], case["formula_lcom"], places=9)
                if case["args"][0] < GWP_BENCHMARK:
                    expected_mac = (case["formula_lcom"] - 2500.0) / ((2600.0 - case["args"][0]) / 1000)
                    self.assertAlmostEqual(res["mac_policy_adjusted"], expected_mac, places=9)
                else:
                    self.assertTrue(math.isnan(res["mac_policy_adjusted"]))

    def test_red_iii_thresholds(self):
        for gwp, green, certified in ((561.2, 0.8, True), (561.18, 0.8, True),
                                      (math.nextafter(561.2, math.inf), 0.8, False),
                                      (561.2, math.nextafter(0.8, 0), False)):
            with self.subTest(gwp=gwp, green=green):
                res = evaluate_policy_compliance(gwp, 4200, 10826, green, 0.01)
                self.assertEqual(res["red_iii_eligible"], certified)
                self.assertEqual(res["policy_breakdown"]["red_iii_subsidy"], -1200 if certified else 0)
                self.assertEqual(res["compliance_status"],
                                 "RED_III_RFNBO_Certified" if certified else "Domestic_Compliant")

    def test_carbon_tiers_and_zero_abatement(self):
        for gwp, expected in ((0, -312.0), (0.001, -259.9999), (2600, 0.0), (2601, 1082.8)):
            with self.subTest(gwp=gwp):
                res = evaluate_policy_compliance(gwp, 4200, 10826, 0.65, 0.01)
                self.assertAlmostEqual(res["policy_breakdown"]["carbon_cost_mod"], expected)
                self.assertEqual(res["veto_carbon"], gwp > 2600)
                self.assertEqual(math.isnan(res["mac_policy_adjusted"]), gwp >= 2600)
                self.assertEqual(res["compliance_status"], "Redline_Vetoed" if gwp > 2600 else "Domestic_Compliant")

    def test_water_quota_progressive_tax_and_retrofit(self):
        for p, w, expected, retrofit in ((0.010, 1.393, 6.965, False),
                                         (0.008 * 0.010 / 0.015, 1.400, 7.0, False),
                                         (0.004, 1.405, 7.075, False),
                                         (0.002, 1.425, 7.375, False),
                                         (0.001, 1.465, 91.95, True)):
            with self.subTest(purge=p):
                res = evaluate_policy_compliance(800, 4200, 10826, 0.65, p)
                self.assertAlmostEqual(res["water_use_before_retrofit_t_per_t"], w)
                self.assertEqual(res["water_retrofit_required"], retrofit)
                self.assertAlmostEqual(res["policy_breakdown"]["water_cost_mod"], expected)
                self.assertEqual(res["compliance_status"], "Domestic_Compliant")
                self.assertAlmostEqual(res["water_use_actual_t_per_t"], 1.390 if retrofit else w)
                self.assertAlmostEqual(res["water_retrofit_cost"], 85.0 if retrofit else 0.0)

    def test_clean_production_boundary_and_veto_priority(self):
        for p, veto in ((0.035, False), (math.nextafter(0.035, math.inf), True)):
            res = evaluate_policy_compliance(-1044.1, 2862.3, 10826, 1, p)
            self.assertEqual(res["veto_clean_prod"], veto)
            self.assertEqual(res["compliance_status"], "Redline_Vetoed" if veto else "RED_III_RFNBO_Certified")
            self.assertEqual(res["policy_breakdown"]["red_iii_subsidy"], -1200)
            self.assertTrue(math.isfinite(res["mac_policy_adjusted"]))
        both = evaluate_policy_compliance(4531.3, 7193, 10826, 0, 0.04)
        self.assertEqual(both["compliance_status"], "Redline_Vetoed")
        self.assertEqual(len(both["veto_reasons"]), 2)

    def test_invalid_inputs(self):
        valid = [-1044.1, 2862.3, 10826.0, 1.0, 0.01]
        for i in range(len(valid)):
            for invalid in (math.nan, math.inf, -math.inf, None, "not a number", True):
                with self.subTest(index=i, value=invalid):
                    args = valid.copy()
                    args[i] = invalid
                    with self.assertRaises(ValueError):
                        evaluate_policy_compliance(*args)
        for i, invalid in ((2, -1), (3, -0.01), (3, 1.01), (4, 0), (4, -0.01), (4, 1.01)):
            args = valid.copy()
            args[i] = invalid
            with self.assertRaises(ValueError):
                evaluate_policy_compliance(*args)


def main():
    parser = argparse.ArgumentParser(description="任务2：四张政策卡片量化引擎与自检")
    parser.add_argument("--self-test", action="store_true", help="仅执行单元测试")
    args = parser.parse_args()
    if not args.self_test:
        print("任务2：政策修正规则标准工况报告（元/t甲醇）")
        for case in STANDARD_CASES:
            res = evaluate_policy_compliance(*case["args"])
            costs = res["policy_breakdown"]
            print(f"\n{case['name']}：{res['compliance_status']}")
            print("  费用分项：" + ", ".join(f"{k}={v:.6f}" for k, v in costs.items()))
            print(f"  公式LCOM={res['lcom_policy_adjusted']:.6f}；原表LCOM={case['table_lcom']:.2f}；"
                  f"差额={res['lcom_policy_adjusted']-case['table_lcom']:+.6f}")
            mac = res["mac_policy_adjusted"]
            print(f"  MAC={mac:.6f} 元/t CO2e" if math.isfinite(mac)
                  else "  MAC=NaN（没有正向减排量，边际减排成本无定义）")
        print("\n[资料差异] 原表三项LCOM与四张卡片公式不一致；以上采用公式计算值。", flush=True)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(PolicyEngineTests)
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    sys.exit(main())
