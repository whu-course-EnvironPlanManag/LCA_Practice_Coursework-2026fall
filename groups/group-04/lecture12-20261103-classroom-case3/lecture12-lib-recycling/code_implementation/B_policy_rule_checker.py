"""Rule-based policy compliance checks for the Group 4 battery-recycling case."""

# AI prompt: Use the group's A-side battery-recycling data and assignment policy thresholds
# to build a Python compliance checker; treat missing inputs as unresolved and add CSV output
# plus unit tests. Human reviewed against the assignment and A-side handbook; tests executed.

from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data_cohort"
PARAMETERS_PATH = DATA_DIR / "B_policy_parameters.json"
RESULTS_PATH = DATA_DIR / "B_policy_scenario_results.csv"
GRID_RESULTS_PATH = DATA_DIR / "B_policy_decision_grid.csv"


def load_parameters() -> dict[str, Any]:
    with PARAMETERS_PATH.open(encoding="utf-8") as file:
        return json.load(file)


def check_requirement(value: float | None, operator: str, threshold: float) -> str:
    if value is None:
        return "待核验"
    if operator == ">=":
        return "通过" if value >= threshold else "不通过"
    if operator == "<":
        return "通过" if value < threshold else "不通过"
    raise ValueError(f"Unsupported operator: {operator}")


def evaluate_scenario(
    scenario: dict[str, Any], parameters: dict[str, Any]
) -> dict[str, Any]:
    metric_values = scenario["metrics"]
    china_checks = []
    for requirement in parameters["china_requirements"]:
        value = metric_values.get(requirement["metric"])
        china_checks.append(
            {
                "id": requirement["id"],
                "name": requirement["name"],
                "value": value,
                "operator": requirement["operator"],
                "threshold": requirement["threshold"],
                "unit": requirement["unit"],
                "status": check_requirement(
                    value, requirement["operator"], requirement["threshold"]
                ),
            }
        )

    eu_checks = []
    for requirement in parameters["eu_requirements"]:
        value = metric_values.get(requirement["metric"])
        eu_checks.append(
            {
                "id": requirement["id"],
                "name": requirement["name"],
                "value": value,
                "operator": requirement["operator"],
                "threshold": requirement["threshold"],
                "unit": requirement["unit"],
                "status": check_requirement(
                    value, requirement["operator"], requirement["threshold"]
                ),
            }
        )

    statuses = [check["status"] for check in china_checks]
    overall_status = (
        "不通过" if "不通过" in statuses else
        "待核验" if "待核验" in statuses else
        "通过"
    )
    return {
        "scenario_id": scenario["scenario_id"],
        "scenario_name": scenario["scenario_name"],
        "data_class": scenario["data_class"],
        "china_overall_status": overall_status,
        "china_checks": china_checks,
        "eu_checks": eu_checks,
    }


def scenarios() -> list[dict[str, Any]]:
    common = {
        "recycling_capacity_t_per_year": 20000.0,
        "cascade_capacity_t_per_year": 4000.0,
        "rd_expense_ratio_percent": None,
        "black_mass_recovery_percent": 98.0,
        "copper_recovery_percent": 98.0,
        "aluminum_recovery_percent": 98.0,
        "material_repair_percent": 99.0,
        "lithium_carbonate_energy_kgce_per_t": None,
        "fluorine_solidification_percent": None,
        "recycled_lithium_content_percent": None,
    }
    return [
        {
            "scenario_id": "A_BASE",
            "scenario_name": "A侧基准参数",
            "data_class": "A侧数据；缺失项保留为空",
            "metrics": {
                **common,
                "li_recovery_percent": 92.0,
                "ni_recovery_percent": 95.0,
                "co_recovery_percent": 95.0,
                "mn_recovery_percent": 90.0,
                "wastewater_reuse_percent": None,
            },
        },
        {
            "scenario_id": "LEGAL_MIN",
            "scenario_name": "法规阈值示范工况",
            "data_class": "示范值，仅验证判定逻辑，不代表A侧实测",
            "metrics": {
                **common,
                "rd_expense_ratio_percent": 3.0,
                "li_recovery_percent": 92.0,
                "ni_recovery_percent": 98.0,
                "co_recovery_percent": 98.0,
                "mn_recovery_percent": 98.0,
                "wastewater_reuse_percent": 90.0,
                "lithium_carbonate_energy_kgce_per_t": 2199.0,
                "fluorine_solidification_percent": 99.5,
                "recycled_lithium_content_percent": 6.0,
            },
        },
        {
            "scenario_id": "ADVANCED",
            "scenario_name": "强化控制示范工况",
            "data_class": "示范值，仅验证判定逻辑，不代表A侧实测",
            "metrics": {
                **common,
                "rd_expense_ratio_percent": 3.0,
                "li_recovery_percent": 95.0,
                "ni_recovery_percent": 99.0,
                "co_recovery_percent": 99.0,
                "mn_recovery_percent": 99.0,
                "wastewater_reuse_percent": 95.0,
                "lithium_carbonate_energy_kgce_per_t": 2100.0,
                "fluorine_solidification_percent": 99.8,
                "recycled_lithium_content_percent": 12.0,
            },
        },
        {
            "scenario_id": "BELOW_LIMIT",
            "scenario_name": "低于法规阈值示范工况",
            "data_class": "示范值，仅验证判定逻辑，不代表A侧实测",
            "metrics": {
                **common,
                "rd_expense_ratio_percent": 3.0,
                "li_recovery_percent": 89.0,
                "ni_recovery_percent": 98.0,
                "co_recovery_percent": 98.0,
                "mn_recovery_percent": 98.0,
                "wastewater_reuse_percent": 89.0,
                "lithium_carbonate_energy_kgce_per_t": 2200.0,
                "fluorine_solidification_percent": 99.5,
                "recycled_lithium_content_percent": 5.0,
            },
        },
    ]


def write_results(parameters: dict[str, Any]) -> list[dict[str, Any]]:
    results = [evaluate_scenario(item, parameters) for item in scenarios()]
    with RESULTS_PATH.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "scenario_id", "scenario_name", "data_class", "jurisdiction",
                "requirement_id", "requirement_name", "value", "operator",
                "threshold", "unit", "status", "china_overall_status",
            ]
        )
        for result in results:
            for jurisdiction, checks in (
                ("中国", result["china_checks"]), ("欧盟", result["eu_checks"])
            ):
                for check in checks:
                    writer.writerow(
                        [
                            result["scenario_id"], result["scenario_name"],
                            result["data_class"], jurisdiction, check["id"],
                            check["name"], "" if check["value"] is None else check["value"],
                            check["operator"], check["threshold"], check["unit"],
                            check["status"], result["china_overall_status"],
                        ]
                    )
    return results


def enumerate_decision_grid(parameters: dict[str, Any]) -> tuple[int, int]:
    variables = {item["id"]: item for item in parameters["decision_variables"]}
    lithium = variables["x1"]
    wastewater = variables["x2"]
    lithium_values = _grid_values(lithium)
    wastewater_values = _grid_values(wastewater)
    combinations = 0
    feasible = 0

    with GRID_RESULTS_PATH.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "lithium_recovery_percent",
                "wastewater_reuse_percent",
                "china_li_recovery_status",
                "china_wastewater_status",
                "eu_2031_li_recovery_status",
                "two_variable_feasible",
            ]
        )
        for lithium_rate in lithium_values:
            for wastewater_rate in wastewater_values:
                china_li = check_requirement(lithium_rate, ">=", 90.0)
                china_water = check_requirement(wastewater_rate, ">=", 90.0)
                eu_li = check_requirement(lithium_rate, ">=", 80.0)
                is_feasible = all(
                    status == "通过" for status in (china_li, china_water, eu_li)
                )
                combinations += 1
                feasible += int(is_feasible)
                writer.writerow(
                    [
                        lithium_rate,
                        wastewater_rate,
                        china_li,
                        china_water,
                        eu_li,
                        "是" if is_feasible else "否",
                    ]
                )
    return combinations, feasible


def _grid_values(variable: dict[str, Any]) -> list[float]:
    lower, upper = variable["scenario_range_percent"]
    step = variable["grid_step_percent"]
    count = int(round((upper - lower) / step))
    return [round(lower + index * step, 6) for index in range(count + 1)]


class PolicyEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.parameters = load_parameters()
        cls.results = {
            result["scenario_id"]: result
            for result in (evaluate_scenario(s, cls.parameters) for s in scenarios())
        }

    def test_a_baseline_flags_metal_recovery_gaps_and_missing_data(self) -> None:
        result = self.results["A_BASE"]
        statuses = {check["id"]: check["status"] for check in result["china_checks"]}
        self.assertEqual(result["china_overall_status"], "不通过")
        self.assertEqual(statuses["li_recovery"], "通过")
        self.assertEqual(statuses["ni_recovery"], "不通过")
        self.assertEqual(statuses["co_recovery"], "不通过")
        self.assertEqual(statuses["mn_recovery"], "不通过")
        self.assertEqual(statuses["wastewater_reuse"], "待核验")

    def test_complete_legal_minimum_scenario_passes(self) -> None:
        result = self.results["LEGAL_MIN"]
        self.assertEqual(result["china_overall_status"], "通过")
        eu = {check["id"]: check["status"] for check in result["eu_checks"]}
        self.assertEqual(eu["eu_li_recovery_2031"], "通过")
        self.assertEqual(eu["eu_recycled_content_2031"], "通过")

    def test_below_limit_scenario_fails(self) -> None:
        result = self.results["BELOW_LIMIT"]
        statuses = {check["id"]: check["status"] for check in result["china_checks"]}
        self.assertEqual(result["china_overall_status"], "不通过")
        self.assertEqual(statuses["li_recovery"], "不通过")
        self.assertEqual(statuses["wastewater_reuse"], "不通过")
        self.assertEqual(statuses["lithium_carbonate_energy"], "不通过")

    def test_decision_grid_applies_both_selected_legal_floors(self) -> None:
        combinations, feasible = enumerate_decision_grid(self.parameters)
        self.assertEqual(combinations, 380)
        self.assertEqual(feasible, 90)


if __name__ == "__main__":
    parameters = load_parameters()
    results = write_results(parameters)
    combinations, feasible = enumerate_decision_grid(parameters)
    for result in results:
        unresolved = sum(check["status"] == "待核验" for check in result["china_checks"])
        print(
            f"{result['scenario_id']}: 中国={result['china_overall_status']}; "
            f"未核验项={unresolved}"
        )
    print(f"CSV结果: {RESULTS_PATH}")
    print(
        f"二维法规决策网格: {combinations}组，双变量均达标{feasible}组，"
        f"可行比例={feasible / combinations:.1%}；网格结果: {GRID_RESULTS_PATH}"
    )
    unittest.main(argv=["B_policy_rule_checker.py"], exit=False)