"""Extend C's policy scenarios with full-horizon checks and conditional incentives."""

# AI prompt: Use the A/C module outputs and the assignment's China/EU policy thresholds
# to complete B's compliance and financial-policy checks. Preserve missing evidence as
# unresolved, distinguish 2031 from 2036 targets, and add tests. Manually reviewed against
# the assignment, C's parameters/results, and the generated reports; tests executed.

from __future__ import annotations

import csv
import json
import math
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data_cohort"
KGCE_PER_GJ = 34.12
PARAMETERS_FILE = DATA / "ABC_parameters.json"
POLICY_FILE = DATA / "B_policy_results.json"
LCA_FILE = DATA / "C_lca_tea_results.json"
REVIEW_JSON = DATA / "B_policy_review.json"
REVIEW_CSV = DATA / "B_policy_review.csv"
FINANCIAL_CSV = DATA / "B_policy_financial_adjustments.csv"
ALLOCATION_CSV = DATA / "B_policy_route_allocation.csv"


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def compare(value: float | None, operator: str, threshold: float | None) -> str:
    if value is None or threshold is None:
        return "待核验"
    if operator == ">=":
        return "通过" if value >= threshold - 1e-9 else "不通过"
    if operator == ">":
        return "通过" if value > threshold else "不通过"
    if operator == "<":
        return "通过" if value < threshold else "不通过"
    raise ValueError(f"Unsupported operator: {operator}")


def make_check(
    code: str,
    name: str,
    value: float | None,
    operator: str,
    threshold: float | None,
    unit: str,
    evidence: str,
    jurisdiction: str,
) -> dict[str, Any]:
    return {
        "code": code,
        "name": name,
        "value": value,
        "operator": operator,
        "threshold": threshold,
        "unit": unit,
        "status": compare(value, operator, threshold),
        "evidence": evidence,
        "jurisdiction": jurisdiction,
    }


def summarize_status(checks: list[dict[str, Any]]) -> str:
    statuses = [item["status"] for item in checks if item["status"] != "不适用"]
    if "不通过" in statuses:
        return "不通过"
    if "待核验" in statuses:
        return "待核验"
    return "通过"


def checks_for_values(
    name: str,
    values: dict[str, float | None],
    params: dict[str, Any],
    *,
    evidence_prefix: str,
) -> list[dict[str, Any]]:
    cn = params["policy"]["cn"]
    eu = params["policy"]["eu"]
    checks = [
        make_check("CN-LI", "冶炼锂回收率", values.get("li"), ">=", cn["li_recovery"], "%", evidence_prefix, "中国"),
        make_check("CN-NICOMN", "镍钴锰综合回收率", values.get("nico"), ">=", cn["nico_mn_recovery"], "%", evidence_prefix + "；C模型为合并指标", "中国"),
        make_check("CN-POWDER", "电极粉料回收率", values.get("powder"), ">=", cn["powder_recovery"], "%", evidence_prefix, "中国"),
        make_check("CN-CUAL", "铜铝回收率", values.get("cual"), ">=", cn["cu_al_recovery"], "%", evidence_prefix + "；C模型为合并指标", "中国"),
        make_check("CN-F", "氟固化率", values.get("f"), ">=", cn["f_fixation"], "%", evidence_prefix, "中国"),
        make_check("CN-LCE-ENERGY", "碳酸锂单位综合能耗", values.get("energy"), "<", cn["lce_energy_kgce_per_t"], "kgce/t Li2CO3", evidence_prefix + "；按严格小于判定", "中国"),
        make_check("CN-WATER", "工艺废水循环利用率", values.get("ww"), ">=", cn["wastewater_recycle"], "%", evidence_prefix, "中国"),
        make_check("CN-CAPACITY", "再生利用设计能力", values.get("capacity"), ">=", cn["capacity_recycle_t_per_year"], "t/a", evidence_prefix, "中国"),
        make_check("CN-REPAIR", "直接再生材料修复回收比重", values.get("repair"), ">=", cn["material_repair"], "%", "C参数有Direct产品产率97%，但未提供与法规定义同口径的材料修复回收比重，需核实", "中国"),
        make_check("CN-CU-IMPURITY", "电极粉料杂质铜含量", values.get("cu_impurity"), "<", 1.5, "%", "未提供黑粉杂质化验结果", "中国"),
        make_check("CN-AL-IMPURITY", "电极粉料杂质铝含量", values.get("al_impurity"), "<", 1.5, "%", "未提供黑粉杂质化验结果", "中国"),
        make_check("CN-RD", "研发及工艺改进费用占业务收入比例", values.get("rd_ratio"), ">=", 3.0, "%", "未提供年度研发费用和综合利用业务收入", "中国"),
        make_check("CN-CASCADE-CAPACITY", "梯次利用年综合利用能力", values.get("cascade_capacity"), ">=", cn["capacity_echelon_t_per_year"], "t/a", "C数据包未提供梯次利用设计能力", "中国"),
    ]

    nico = values.get("nico")
    cual = values.get("cual")
    checks.extend(
        [
            make_check("EU-LI-2027", "欧盟2027锂回收率", values.get("li"), ">=", eu["li_recovery_2027"], "%", evidence_prefix, "欧盟"),
            make_check("EU-LI-2031", "欧盟2031锂回收率", values.get("li"), ">=", eu["li_recovery_2031"], "%", evidence_prefix, "欧盟"),
            make_check("EU-NICO-CU-2027", "欧盟2027镍钴铜回收率", min(nico, cual) if nico is not None and cual is not None else None, ">=", eu["nico_cu_pb_recovery_2027"], "%", evidence_prefix + "；Ni/Co与Cu采用C合并指标代理，未覆盖Pb", "欧盟"),
            make_check("EU-NICO-CU-2031", "欧盟2031镍钴铜回收率", min(nico, cual) if nico is not None and cual is not None else None, ">=", eu["nico_cu_pb_recovery_2031"], "%", evidence_prefix + "；Ni/Co与Cu采用C合并指标代理，未覆盖Pb", "欧盟"),
            make_check("EU-LI-CONTENT-2031", "欧盟2031再生锂含量", values.get("recycled"), ">=", eu["recycled_li_2031"], "%", evidence_prefix, "欧盟"),
            make_check("EU-LI-CONTENT-2036", "欧盟2036再生锂含量", values.get("recycled"), ">=", eu["recycled_li_2036"], "%", evidence_prefix, "欧盟"),
            make_check("EU-NI-CONTENT", "欧盟再生镍含量", values.get("recycled_ni"), ">=", eu["recycled_ni_2031"], "%", "未提供新电池再生镍含量数据", "欧盟"),
            make_check("EU-CO-CONTENT", "欧盟再生钴含量", values.get("recycled_co"), ">=", eu["recycled_co_2031"], "%", "未提供新电池再生钴含量数据", "欧盟"),
            make_check("EU-DPP", "电池数字护照及碳足迹声明", values.get("dpp"), ">=", 1.0, "已实施/未实施", "具备LCA核算结果，但未提供护照与正式声明记录", "欧盟"),
        ]
    )
    return checks


def build_scenario_values(params: dict[str, Any], policy_results: dict[str, Any], lca_results: dict[str, Any]) -> dict[str, dict[str, float | None]]:
    output: dict[str, dict[str, float | None]] = {}
    for name, result in policy_results["conditions"].items():
        vals = result["values"]
        output[name] = {
            "li": vals["li"],
            "nico": vals["nico"],
            "powder": vals["powder"],
            "cual": vals["cual"],
            "f": vals["f"],
            "ww": vals["ww"],
            "energy": vals["energy"],
            "recycled": vals["recycled"],
            "capacity": vals["capacity"],
            "repair": None,
            "cu_impurity": None,
            "al_impurity": None,
            "rd_ratio": None,
            "cascade_capacity": None,
            "recycled_ni": None,
            "recycled_co": None,
            "dpp": None,
        }

    knee = lca_results["pareto"]["knee"]
    process = params["process"]
    knee_scenario = lca_results["scenarios"]["knee"]
    knee_energy = (
        knee_scenario["electric_kwh_per_t"] * process["kwh_to_kgce"]
        + knee_scenario["heat_gj_per_t"] * KGCE_PER_GJ
    ) / max(knee_scenario["lce_t"], 1e-12)
    output["推荐拐点（C-Knee）"] = {
        "li": knee["li_recovery"],
        "nico": knee["nico_recovery"],
        "powder": process["pretreatment"]["black_mass_recovery"],
        "cual": process["pretreatment"]["copper_al_recovery"],
        "f": process["pretreatment"]["fluorine_fixation"],
        "ww": process["wastewater_recycle"],
        "energy": knee_energy,
        "recycled": params["tea"]["recycled_content_li"],
        "capacity": params["_meta"]["design_capacity_t_cells_per_year"],
        "repair": None,
        "cu_impurity": None,
        "al_impurity": None,
        "rd_ratio": None,
        "cascade_capacity": None,
        "recycled_ni": None,
        "recycled_co": None,
        "dpp": None,
    }
    return output


def route_allocation(params: dict[str, Any], lca_results: dict[str, Any]) -> dict[str, float]:
    feed = params["feedstock"]["share"]
    direct_lfp = lca_results["scenarios"]["knee"]["direct_share_lfp"]
    rc_share_non_lfp = 0.30
    non_lfp = feed["NMC811"] + feed["NCA"]
    direct = feed["LFP"] * direct_lfp
    rc_hy = non_lfp * rc_share_non_lfp
    hy = feed["LFP"] * (1 - direct_lfp) + non_lfp * (1 - rc_share_non_lfp)
    capacity = params["_meta"]["design_capacity_t_cells_per_year"]
    return {
        "direct_share_total_feed": direct,
        "hy_share_total_feed": hy,
        "rc_hy_share_total_feed": rc_hy,
        "direct_t_per_year": direct * capacity,
        "hy_t_per_year": hy * capacity,
        "rc_hy_t_per_year": rc_hy * capacity,
        "total_share": direct + hy + rc_hy,
    }


def financial_adjustments(params: dict[str, Any], lca_results: dict[str, Any]) -> list[dict[str, Any]]:
    primary = lca_results["primary"]
    cap = params["_meta"]["design_capacity_t_cells_per_year"]
    carbon_price = params["tea"]["carbon_price_yuan_per_t"]
    eu_premium = params["tea"]["eu_premium_yuan_per_t_lce"]
    eu_target_2031 = params["policy"]["eu"]["recycled_li_2031"]
    eu_target_2036 = params["policy"]["eu"]["recycled_li_2036"]
    recycled_content = params["tea"]["recycled_content_li"]
    rows = []
    for name, scenario in lca_results["scenarios"].items():
        avoided_t = (primary["co2_kg_per_t"] - scenario["gwp_kg_per_t"]) / 1000
        theoretical_carbon_value = avoided_t * carbon_price
        lce_t = scenario["lce_t"]
        qualifies_2031 = recycled_content >= eu_target_2031
        qualifies_2036 = recycled_content >= eu_target_2036
        premium_2031 = lce_t * eu_premium if qualifies_2031 else 0.0
        premium_2036 = lce_t * eu_premium if qualifies_2036 else 0.0
        cost = scenario["cost_detail"]
        rows.append(
            {
                "scenario": name,
                "green_share_percent": scenario["green_share"] * 100,
                "direct_share_of_lfp_percent": scenario["direct_share_lfp"] * 100,
                "gwp_kg_co2e_per_t_cells": scenario["gwp_kg_per_t"],
                "avoided_co2_t_per_t_cells": avoided_t,
                "carbon_price_yuan_per_t_co2e": carbon_price,
                "theoretical_carbon_value_yuan_per_t_cells": theoretical_carbon_value,
                "theoretical_carbon_value_yuan_per_year": theoretical_carbon_value * cap,
                "ccer_eligibility": "待方法学适用性、项目登记与核证；不得作为已实现收入",
                "recycled_lithium_content_percent": recycled_content * 100,
                "eu_2031_content_status": "通过" if qualifies_2031 else "不通过",
                "eu_2036_content_status": "通过" if qualifies_2036 else "不通过",
                "lce_t_per_t_cells": lce_t,
                "eu_premium_assumption_yuan_per_t_lce": eu_premium,
                "conditional_eu_premium_2031_yuan_per_t_cells": premium_2031,
                "conditional_eu_premium_2031_yuan_per_year": premium_2031 * cap,
                "conditional_eu_premium_2036_yuan_per_t_cells": premium_2036,
                "conditional_eu_premium_2036_yuan_per_year": premium_2036 * cap,
                "c_lcor_yuan_per_t_cells_before_policy_uplift": scenario["lcor_yuan_per_t"],
                "existing_environmental_cost_yuan_per_t_cells": params["tea"]["env_cost_yuan_per_t"],
                "existing_water_cost_yuan_per_t_cells": cost["water_cost"],
                "accounting_note": "碳价值与欧盟溢价为条件性增量情景，未计入C基准LCOR；环境管理费与水费已在C的OPEX中，禁止重复加计。",
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def run_review() -> dict[str, Any]:
    params = load_json(PARAMETERS_FILE)
    c_policy = load_json(POLICY_FILE)
    mfa_results = load_json(DATA / "A_mfa_results.json")
    lca_results = load_json(LCA_FILE)
    values_by_scenario = build_scenario_values(params, c_policy, lca_results)
    reviews = {}
    flat_checks = []
    for name, values in values_by_scenario.items():
        checks = checks_for_values(name, values, params, evidence_prefix="C模块模型输出")
        cn_checks = [item for item in checks if item["jurisdiction"] == "中国"]
        eu_checks = [item for item in checks if item["jurisdiction"] == "欧盟"]
        eu_2031 = [item for item in eu_checks if "2036" not in item["code"]]
        eu_2036 = [item for item in eu_checks if "2036" in item["code"]]
        c_model_checks = c_policy["conditions"].get(name, {}).get("assertions", [])
        reviews[name] = {
            "values": values,
            "china_status_full_scope": summarize_status(cn_checks),
            "eu_status_2031": summarize_status(eu_2031),
            "eu_status_2036": summarize_status(eu_2036),
            "c_original_11_rule_verdict": c_policy["conditions"].get(name, {}).get("verdict"),
            "checks": checks,
        }
        for item in checks:
            flat_checks.append({"scenario": name, **item})

    routes = route_allocation(params, lca_results)
    financial = financial_adjustments(params, lca_results)
    knee_summary = dict(lca_results["pareto"]["knee"])
    knee_summary["kgce"] = values_by_scenario["推荐拐点（C-Knee）"]["energy"]
    result = {
        "source_files": ["ABC_parameters.json", "B_policy_results.json", "A_mfa_results.json", "C_lca_tea_results.json"],
        "data_version": params["_meta"]["base_year"],
        "mfa_max_element_closure_error_percent": mfa_results["closure_error_max_pct"],
        "recommended_knee": knee_summary,
        "route_allocation": routes,
        "scenarios": reviews,
        "financial_adjustments": financial,
        "limitations": [
            "拐点单位能耗按C附件公式（电力和热能分别折标后除以LCE产量）重算；与组内C结果文件原kgce字段不一致，须以统一边界和企业能源计量复核。",
            "C原始11条断言的PASS只代表该断言集通过，不覆盖工信部材料修复率、粉料杂质、研发费用和梯次产能等所有要求。",
            "C模型给出的Direct产品产率97%不能在缺少口径说明时直接等同于法规材料修复回收率；需补工艺核算或检测证据。",
            "欧盟2036年再生锂含量目标为12%；C参数中的再生锂含量6%满足2031目标但不满足2036目标。",
            "欧盟碳足迹最高阈值数值、正式电池护照记录、再生Ni/Co含量及铅回收适用性未提供，当前按待核验或不适用处理。",
            "碳价与欧盟溢价是C的TEA情景参数；CCER收益需满足方法学、登记与核证条件，EU溢价也不是法规自动产生的收入。",
        ],
    }
    REVIEW_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(REVIEW_CSV, flat_checks)
    write_csv(FINANCIAL_CSV, financial)
    route_rows = [
        {"route": name, "share_total_feed_percent": routes[key] * 100, "feed_t_per_year": routes[tkey]}
        for name, key, tkey in (
            ("Direct（适用LFP）", "direct_share_total_feed", "direct_t_per_year"),
            ("Hy（LFP余量+70% NMC/NCA）", "hy_share_total_feed", "hy_t_per_year"),
            ("RC_Hy（30% NMC/NCA）", "rc_hy_share_total_feed", "rc_hy_t_per_year"),
        )
    ]
    write_csv(ALLOCATION_CSV, route_rows)
    return result


class PolicyCompletionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.params = load_json(PARAMETERS_FILE)
        cls.policy = load_json(POLICY_FILE)
        cls.lca = load_json(LCA_FILE)
        cls.review = run_review()

    def test_energy_ceiling_is_strict(self) -> None:
        limit = self.params["policy"]["cn"]["lce_energy_kgce_per_t"]
        self.assertEqual(compare(limit, "<", limit), "不通过")
        self.assertEqual(compare(limit - 0.01, "<", limit), "通过")

    def test_c_wet_and_green_cases_pass_c_defined_2031_rules(self) -> None:
        for name in ("W2 达标湿法", "W3 绿电直接再生"):
            checks = self.review["scenarios"][name]["checks"]
            modeled_codes = {
                "CN-LI", "CN-NICOMN", "CN-POWDER", "CN-CUAL", "CN-F",
                "CN-LCE-ENERGY", "CN-WATER", "CN-CAPACITY",
            }
            c_checks = [item for item in checks if item["code"] in modeled_codes]
            self.assertTrue(all(item["status"] == "通过" for item in c_checks))
            eu = {item["code"]: item["status"] for item in checks if item["jurisdiction"] == "欧盟"}
            for code in ("EU-LI-2027", "EU-LI-2031", "EU-NICO-CU-2027", "EU-NICO-CU-2031", "EU-LI-CONTENT-2031"):
                self.assertEqual(eu[code], "通过")
            self.assertEqual(self.review["scenarios"][name]["eu_status_2031"], "待核验")

    def test_knee_energy_from_attached_c_method_exceeds_ceiling(self) -> None:
        result = self.review["scenarios"]["推荐拐点（C-Knee）"]
        checks = {item["code"]: item["status"] for item in result["checks"]}
        self.assertGreater(result["values"]["energy"], self.params["policy"]["cn"]["lce_energy_kgce_per_t"])
        self.assertEqual(self.review["recommended_knee"]["kgce"], result["values"]["energy"])
        self.assertEqual(checks["CN-LCE-ENERGY"], "不通过")
        for code in ("CN-LI", "CN-NICOMN", "CN-POWDER", "CN-CUAL", "CN-F", "CN-WATER", "CN-CAPACITY"):
            self.assertEqual(checks[code], "通过")
        self.assertEqual(result["china_status_full_scope"], "不通过")

    def test_c_recycled_lithium_does_not_meet_2036_target(self) -> None:
        for name in ("W1 粗放回收", "W2 达标湿法", "W3 绿电直接再生", "推荐拐点（C-Knee）"):
            result = self.review["scenarios"][name]
            self.assertEqual(result["eu_status_2036"], "不通过")

    def test_knee_route_shares_match_c_feed_mix(self) -> None:
        routes = self.review["route_allocation"]
        self.assertTrue(math.isclose(routes["total_share"], 1.0, abs_tol=1e-12))
        self.assertTrue(math.isclose(routes["direct_share_total_feed"], 0.36, abs_tol=1e-12))
        self.assertTrue(math.isclose(routes["hy_share_total_feed"], 0.52, abs_tol=1e-12))
        self.assertTrue(math.isclose(routes["rc_hy_share_total_feed"], 0.12, abs_tol=1e-12))

    def test_knee_policy_value_is_conditional_and_not_in_base_lcor(self) -> None:
        knee = next(item for item in self.review["financial_adjustments"] if item["scenario"] == "knee")
        self.assertGreater(knee["theoretical_carbon_value_yuan_per_year"], 6_000_000)
        self.assertGreater(knee["conditional_eu_premium_2031_yuan_per_year"], 1_000_000)
        self.assertEqual(knee["conditional_eu_premium_2036_yuan_per_year"], 0)
        self.assertIn("未计入C基准LCOR", knee["accounting_note"])


if __name__ == "__main__":
    review = run_review()
    print("B扩展政策核查：")
    for name, result in review["scenarios"].items():
        print(
            f"  {name}: 中国全口径={result['china_status_full_scope']}; "
            f"欧盟2031={result['eu_status_2031']}; 欧盟2036={result['eu_status_2036']}"
        )
    routes = review["route_allocation"]
    print(
        "拐点路线配比（全部来料）: "
        f"Direct {routes['direct_share_total_feed']:.0%}, "
        f"Hy {routes['hy_share_total_feed']:.0%}, "
        f"RC_Hy {routes['rc_hy_share_total_feed']:.0%}"
    )
    print(f"核查结果: {REVIEW_JSON}")
    print(f"财务调整: {FINANCIAL_CSV}")
    unittest.main(argv=["B_policy_completion.py"], exit=False)