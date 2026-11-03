"""纯合成测试夹具，不是湖北观测、预测或文献参数，不写入正式data_cohort。"""
from copy import deepcopy
from pathlib import Path
import contextlib
import io
import json
import math
import tempfile
import unittest
from unittest.mock import patch

import common
import input_data
import run_analysis
from common import InputError, write_csv
from dmfa_model import survival, retirement_probability, run_dmfa, stock_driven_installations
from policy_engine import evaluate_policy, financial_adjustments
from lca_tea import capital_recovery_factor, compare_pathway, evaluate_inventory, find_procurement_quote
from network_model import solve_network
from decision import pareto_frontier

PROVENANCE = {"source": "SYNTHETIC_TEST_ONLY", "source_locator": "unit test; not a provincial estimate"}
RULES = json.loads((common.DATA / "policy_rules.json").read_text("utf-8"))


def fixture_mfa(start=2025, end=2031):
    materials = [{"chemistry": "LFP", "vintage_year": 2025, "eta_years": 2, "beta": 2,
                  "pack_specific_energy_kwh_per_kg": 0.1, "Li_kg_per_kwh": 0.1,
                  "Ni_kg_per_kwh": 0, "Co_kg_per_kwh": 0, "Mn_kg_per_kwh": 0, **PROVENANCE}]
    cohorts = [{"year": 2025, "city": "测试市", "chemistry": "LFP", "installed_kwh": 100000,
                "record_type": "documented_scenario", **PROVENANCE}]
    collection = {(year, "测试市"): 0.8 for year in range(start, end+1)}
    diversion = {(year, "LFP"): {"echelon_share": 0, "delay_years": 0, **PROVENANCE} for year in range(start, end+1)}
    recovery = {"LFP": {"Li": 0.9, "Ni": 1, "Co": 1, "Mn": 1}}
    return cohorts, materials, start, end, collection, diversion, recovery


def policy_case():
    return {"as_of_date": "2030-12-31", "pathway": "hydro", "powder_recovery_fraction": 0.98,
            "al_impurity_fraction": 0.01, "cu_impurity_fraction": 0.01,
            "cu_recovery_fraction": 0.98, "al_recovery_fraction": 0.98,
            "wastewater_reuse_fraction": 0.9, "fluorine_fixation_fraction": 0.995,
            "rd_revenue_fraction": 0.03, "design_capacity_t_y": 5000,
            "produces_lce": True, "li_smelting_recovery_fraction": 0.9,
            "lce_energy_kgce_per_t": 2199, "present_elements": ["Li"], "export_eu": False}


def fixture_network():
    nodes = []
    for key, role, capacity, lon in (("O", "origin", 0, 110), ("C", "collection", 10000, 111), ("R", "refining", 10000, 112)):
        nodes.append({"node_id": key, "city": "测试市", "role": role, "capacity_t_y": capacity,
                      "capex_cny": 100 if role != "origin" else 0, "wacc": 0, "life_years": 10,
                      "fixed_opex_cny_y": 0, "variable_handling_cny_t": 0,
                      "eligible": "true", "longitude": lon, "latitude": 30, **PROVENANCE})
    edges = [{"from_node": a, "to_node": b, "commodity": "recycling", "road_distance_km": 10,
              "transport_cny_tkm": 1, "transport_gwp_kg_tkm": 0.1, "transport_water_l_tkm": 0.01,
              **PROVENANCE} for a, b in (("O", "C"), ("C", "R"))]
    supplies = [{"node_id": "O", "commodity": "recycling", "supply_t": 100}]
    return nodes, edges, supplies


class InputValidationTests(unittest.TestCase):
    def test_null_or_blank_provenance_is_rejected(self):
        for field in ("source", "source_locator"):
            for value in (None, "", "   "):
                with self.subTest(field=field, value=value), self.assertRaises(InputError):
                    common.source({**PROVENANCE, field: value}, "test input")

    def test_decision_year_must_be_inside_planning_period(self):
        config = common.load_config()
        config["decision_year"] = config["planning_end_year"]+1
        with patch.object(input_data, "load_config", return_value=config):
            self.assertTrue(any("时间边界配置错误" in issue for issue in input_data.check_readiness()))


class DynamicMFATests(unittest.TestCase):
    def test_annual_cdf_difference_and_retained_tail(self):
        p = sum(retirement_probability(age, 8, 3) for age in range(1, 10))
        self.assertAlmostEqual(p+survival(9, 8, 3), 1)
        self.assertGreater(survival(9, 8, 3), 0)

    def test_no_same_year_retirement(self):
        rows, balance = run_dmfa(*fixture_mfa())
        first = rows[0]
        self.assertEqual(first["retired_kwh"], 0)
        self.assertEqual(first["stock_kwh"], 100000)
        self.assertLess(max(r["relative_error"] for r in balance), 1e-12)

    def test_echelon_is_delayed_and_inventory_is_conserved(self):
        args = list(fixture_mfa())
        args[5] = {key: {"echelon_share": 1, "delay_years": 1} for key in args[5]}
        rows, balances = run_dmfa(*args)
        one, two = rows[1], rows[2]
        self.assertEqual(one["Li_secondary_kg"], 0)
        self.assertGreater(one["echelon_stock_t"], 0)
        self.assertAlmostEqual(two["Li_secondary_kg"], one["Li_collected_kg"]*0.9)
        self.assertLess(max(r["relative_error"] for r in balances), 1e-12)

    def test_conditional_opening_stock(self):
        args = list(fixture_mfa())
        args[0] = []
        args[1][0]["vintage_year"] = 2021
        opening = [{"base_year": 2024, "city": "测试市", "chemistry": "LFP", "vintage_year": 2021,
                    "age_years": 3, "surviving_kwh": 1000, **PROVENANCE}]
        rows, _ = run_dmfa(*args, opening=opening)
        expected = 1000*math.exp(-((4/2)**2-(3/2)**2))
        self.assertAlmostEqual(rows[0]["stock_kwh"], expected)
        self.assertNotAlmostEqual(rows[0]["stock_kwh"], 1000*survival(4, 2, 2))

    def test_missing_rate_and_inconsistent_pack_units_fail(self):
        args = list(fixture_mfa())
        args[4] = {}
        with self.assertRaises(InputError):
            run_dmfa(*args)
        args = list(fixture_mfa())
        args[1][0]["Li_kg_per_kwh"] = 20
        with self.assertRaises(InputError):
            run_dmfa(*args)

    def test_stock_driven_rejects_unmodelled_forced_scrappage(self):
        installed = stock_driven_installations({2025: 100, 2026: 100}, 5, 2)
        self.assertAlmostEqual(installed[2026], 100*(1-survival(1, 5, 2)))
        with self.assertRaises(InputError):
            stock_driven_installations({2025: 100, 2026: 0}, 5, 2)

    def test_vintage_specific_material_intensity_is_not_retroactively_changed(self):
        args = list(fixture_mfa())
        second = {**args[0][0], "year": 2026, "installed_kwh": 0}
        args[0].append(second)
        args[1].append({**args[1][0], "vintage_year": 2026, "Li_kg_per_kwh": 0.2})
        rows, _ = run_dmfa(*args)
        self.assertAlmostEqual(rows[1]["Li_stock_kg"], 10000*survival(1, 2, 2))


class PolicyTests(unittest.TestCase):
    def test_noncompliant_rough_recovery_veto(self):
        case = {**policy_case(), "li_smelting_recovery_fraction": 0.85}
        self.assertEqual(evaluate_policy(case, RULES)["status"], "Redline_Vetoed")

    def test_conventional_hydro_passes_numerical_screen(self):
        self.assertEqual(evaluate_policy(policy_case(), RULES)["status"], "Domestic_Numerical_Screen_Passed")

    def test_advanced_direct_material_restoration(self):
        case = {**policy_case(), "pathway": "direct", "material_restoration_fraction": 0.99}
        case.pop("li_smelting_recovery_fraction")
        self.assertEqual(evaluate_policy(case, RULES)["status"], "Domestic_Numerical_Screen_Passed")

    def test_strict_energy_and_impurity_boundaries(self):
        for key, value in (("lce_energy_kgce_per_t", 2200), ("al_impurity_fraction", 0.015), ("cu_impurity_fraction", 0.015)):
            self.assertEqual(evaluate_policy({**policy_case(), key: value}, RULES)["status"], "Redline_Vetoed")

    def test_missing_is_not_accepted_and_absent_metals_are_not_required(self):
        case = policy_case()
        self.assertFalse(evaluate_policy(case, RULES)["missing"])
        case["present_elements"] = ["Li", "Ni"]
        self.assertEqual(evaluate_policy(case, RULES)["status"], "Data_Incomplete")

    def test_eu_exact_effective_dates(self):
        case = {**policy_case(), "export_eu": True, "li_material_recovery_fraction": 0.9,
                "eu_present_elements": ["Li"],
                "li_recycled_content_fraction": 0, "passport_ready": True,
                "export_carbon_limit_applicable": False, "as_of_date": "2031-08-17"}
        self.assertEqual(evaluate_policy(case, RULES)["status"], "EU_Numerical_Screen_Passed")
        case["as_of_date"] = "2031-08-18"
        self.assertEqual(evaluate_policy(case, RULES)["status"], "Redline_Vetoed")
        case["li_recycled_content_fraction"] = 0.06
        self.assertEqual(evaluate_policy(case, RULES)["status"], "EU_Numerical_Screen_Passed")
        case["as_of_date"] = "2036-08-18"
        self.assertEqual(evaluate_policy(case, RULES)["status"], "Redline_Vetoed")

    def test_no_automatic_carbon_credit_or_export_subsidy(self):
        finance = {"carbon_mode": "none", "water_tax_cny_m3": 0, "pollutant_tax_cny_per_unit": {}, "export_premium_mode": "none"}
        self.assertEqual(financial_adjustments(1000, 0, {}, finance, True)["total_cny"], 0)


class EconomicAndDecisionTests(unittest.TestCase):
    def test_capital_recovery(self):
        self.assertAlmostEqual(capital_recovery_factor(0, 10), 0.1)
        self.assertAlmostEqual(capital_recovery_factor(0.08, 20), 0.1018522088231506)

    def test_procurement_does_not_invent_soh_relation(self):
        with self.assertRaises(InputError):
            find_procurement_quote([], "LFP", 1000, 0.8)

    def test_lcor_excludes_main_product_revenue_and_mac_zero_is_undefined(self):
        inventory = {"gwp": 100, "water": 10, "variable_cost": 100}
        finance = {"design_capacity_t_y": 100, "capex_cny": 1000, "wacc": 0, "life_years": 10, "fixed_opex_cny_y": 0}
        products = {"lce_t_per_t_battery": 0.1, "lce_price_cny_t": 2000,
                    "lce_environment_allocation_fraction": 1, "allocation_source": "TEST_ONLY", "coproducts": []}
        baseline = {"functional_unit": "t_LCE", "system_boundary": "cradle_to_gate", "gwp_kg_per_t_lce": 1000,
                    "water_l_per_t_lce": 1000, "cost_cny_per_t_lce": 2000, **PROVENANCE}
        result = compare_pathway(inventory, finance, 100, 0, products, baseline)
        self.assertAlmostEqual(result["lcor_cny_per_t_lce"], 1010)
        self.assertAlmostEqual(result["net_cost_cny_per_t_battery"], -99)
        self.assertIsNone(result["mac_cny_per_t_co2e"])
        baseline["functional_unit"] = "kg_NCA_equivalent"
        with self.assertRaises(InputError):
            compare_pathway(inventory, finance, 100, 0, products, baseline)

    def test_pareto_is_strict_and_degenerate_frontier_is_retained(self):
        rows = [{"gwp_kg_per_t_lce": a, "lcor_cny_per_t_lce": b} for a,b in ((1, 1), (2, 2), (1, 1))]
        frontier, anchors = pareto_frontier(rows)
        self.assertEqual(len(frontier), 2)
        self.assertEqual(anchors["B_Utopia_Distance_Min"]["utopia_distance"], 0)
        with self.assertRaises(InputError):
            pareto_frontier([{"gwp_kg_per_t_lce": math.nan, "lcor_cny_per_t_lce": 1}])


class NetworkTests(unittest.TestCase):
    def test_capacity_and_supply_conservation(self):
        result = solve_network(*fixture_network())
        self.assertEqual(result["status"], "Optimal")
        self.assertAlmostEqual(result["terminal_received_t"], 100)
        self.assertAlmostEqual(result["annual_cost_cny"], 2020)
        self.assertEqual(set(result["opened_nodes"]), {"C", "R"})

    def test_insufficient_capacity_and_radius_are_infeasible(self):
        nodes, edges, supply = fixture_network()
        nodes[-1]["capacity_t_y"] = 99
        self.assertEqual(solve_network(nodes, edges, supply)["status"], "Network_Infeasible")
        self.assertEqual(solve_network(*fixture_network(), radius_km=9)["status"], "Network_Infeasible")

    def test_unknown_candidate_eligibility_does_not_pass(self):
        nodes, edges, supply = fixture_network()
        nodes[-1]["eligible"] = "unknown"
        with self.assertRaises(InputError):
            solve_network(nodes, edges, supply)


class IntegrationTests(unittest.TestCase):
    def test_500_parameter_pairs_with_two_baselines_and_outputs(self):
        # 所有夹具仅在临时目录存在；禁止把本测试输出作湖北结果提交。
        with tempfile.TemporaryDirectory(prefix="lecture12_SYNTHETIC_TEST_") as folder:
            folder = Path(folder)
            data, output = folder / "data", folder / "output"
            data.mkdir(); output.mkdir()
            config = json.loads((common.DATA / "model_config.json").read_text("utf-8"))
            config.update({"model_start_year": 2025, "planning_end_year": 2031,
                           "historical_installations_complete": True, "use_opening_stock": False,
                           "opening_echelon_stock_status": "documented_zero", "battery_migration_boundary": "closed_region_scenario",
                           "baseline_pathway_id": "test_hydro"})
            p = {"id": "test_hydro", "pathway": "hydro", "lithium_output_kind": "battery_grade_LCE", "refining_node_ids": ["R"],
                 "soh_fraction": 0.8, "lce_prices_cny_t": [1000, 2000], "policy_case": policy_case(),
                 "lce_environment_allocation_fraction": 1, "allocation_source": "TEST_ONLY single product",
                 "coproducts_per_t_battery": [], "fresh_withdrawal_m3_per_t_battery": 0,
                 "taxable_pollutants_per_t_battery": {}, "financial_policy": {"carbon_mode": "none", "water_tax_cny_m3": 0,
                 "pollutant_tax_cny_per_unit": {}, "export_premium_mode": "none"}, **PROVENANCE}
            config["pathways"] = [p]
            common.write_json(data / "model_config.json", config)
            common.write_json(data / "policy_rules.json", RULES)
            args = fixture_mfa()
            all_rows = {name: [] for name in input_data.TABLES}
            all_rows["installation_cohorts.csv"] = args[0]
            all_rows["material_parameters.csv"] = args[1]
            all_rows["collection_rates.csv"] = [{"year": y, "city": c, "collection_fraction": v, **PROVENANCE} for (y,c),v in args[4].items()]
            all_rows["echelon_parameters.csv"] = [{"year": y, "chemistry": c, **v} for (y,c),v in args[5].items()]
            all_rows["recovery_parameters.csv"] = [{"pathway": "test_hydro", "chemistry": "LFP", **{e+"_effective_recovery": v for e,v in args[6]["LFP"].items()}, **PROVENANCE}]
            all_rows["energy_factors.csv"] = [{"year": 2030, "grid_gwp_kg_per_kwh": 1, "green_gwp_kg_per_kwh": 0.1,
                "grid_water_l_per_kwh": 1, "green_water_l_per_kwh": 2, "grid_price_cny_per_kwh": 1, "green_price_cny_per_kwh": 2, **PROVENANCE}]
            all_rows["lci.csv"] = [{"pathway": "test_hydro", "chemistry": "LFP", "component": component,
                "quantity_per_t_battery": 100 if component == "electricity_mix" else 0,
                "unit": "kWh" if component == "electricity_mix" else "test_unit", "gwp_kg_per_unit": 0,
                "water_l_per_unit": 0, "cost_cny_per_unit": 0, **PROVENANCE}
                for component in ("electricity_mix", "pretreatment", "process_heat", "reagents", "pollution_control")]
            all_rows["procurement_quotes.csv"] = [{"chemistry": "LFP", "lce_price_cny_t": price, "soh_fraction": 0.8, "purchase_cny_per_t_battery": purchase, **PROVENANCE} for price, purchase in ((1000, 100), (2000, 200))]
            all_rows["primary_lce_baselines.csv"] = [{"route": route, "functional_unit": "t_LCE", "system_boundary": "cradle_to_gate",
                "gwp_kg_per_t_lce": 20000, "water_l_per_t_lce": 30000, "cost_cny_per_t_lce": 5000, **PROVENANCE} for route in ("brine", "spodumene")]
            nodes, edges, _ = fixture_network()
            all_rows["network_nodes.csv"], all_rows["road_distances.csv"] = nodes, edges
            for name, fields in input_data.TABLES.items():
                write_csv(data / name, all_rows[name], fields)
            # 绘图单独检查；此处验证整个计算链而不让测试生成貌似真实的省域图片。
            with patch.object(common, "DATA", data), patch.object(input_data, "DATA", data), patch.object(run_analysis, "OUTPUT", output), patch("plot_results.render_results") as plotter, contextlib.redirect_stdout(io.StringIO()):
                run_analysis.run_full()
            results = run_analysis.common.read_csv("scenario_results.csv", directory=output)
            self.assertEqual(len(results), 2000)
            self.assertTrue(all(row["status"] == "Feasible" for row in results))
            self.assertTrue((output / "recommended_network_brine.json").is_file())
            self.assertTrue((output / "recommended_balance_brine.csv").is_file())
            self.assertFalse(any(p.suffix == ".png" for p in output.iterdir()))
            if getattr(self, "render_fixture", False):
                # 仅供人工QA调用，显式写到临时QA位置，不运行于普通--self-test。
                import plot_results
                import shutil
                with patch.object(plot_results, "DATA", data):
                    plot_results.render_results(output)
                shutil.copytree(output, self.qa_destination)


if __name__ == "__main__":
    unittest.main(verbosity=2)
