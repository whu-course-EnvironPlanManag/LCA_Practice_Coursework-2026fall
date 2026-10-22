import unittest
from pathlib import Path

import case2_analysis as case2
from PIL import Image


class Case2AnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mfa, cls.lca_data, cls.tea_data = case2.read_case_data()
        cls.lca = case2.analyze_lca(cls.lca_data)
        cls.tea = case2.analyze_tea(cls.tea_data, cls.lca)

    def test_recycle_model_and_source_mismatch_are_explicit(self):
        results = case2.solve_recycle_model(self.mfa)
        self.assertAlmostEqual(results["solver_residual_kg"], 0.0, places=8)
        self.assertAlmostEqual(results["solved_recycle_ratio"], 2.8856, places=3)
        self.assertAlmostEqual(results["overall_carbon_utilization_pct"], 97.1393, places=3)

        audit = case2.audit_reported_boundary(self.mfa)
        self.assertAlmostEqual(audit["mass_delta_kg"], -376.0, places=6)
        self.assertGreater(
            max(abs(value["delta_pct_of_input"]) for value in audit["elements"].values()),
            0.01,
        )

    def test_reaction_level_elements_balance(self):
        for reaction in case2.reaction_balance_checks().values():
            for element in reaction.values():
                self.assertLess(abs(element["delta_pct"]), 0.01)

    def test_lca_tea_and_planning_checkpoints(self):
        self.assertAlmostEqual(self.lca["green_gwp"], -1044.12, places=2)
        self.assertAlmostEqual(self.lca["grid_gwp"], 4531.26, places=2)
        self.assertAlmostEqual(self.lca["electricity_kwh"], 10826.0, places=6)
        self.assertAlmostEqual(
            self.tea["break_even_electricity_price_rmb_per_kwh"], 0.15020, places=4
        )
        planning = case2.analyze_planning_case(self.lca)
        self.assertAlmostEqual(planning["solar_share_threshold"], 0.533, places=3)
        self.assertAlmostEqual(
            planning["capital_cost_multiplier_at_rooftop_solar_utilization"], 6.6667, places=3
        )

    def test_generated_pngs_are_high_resolution(self):
        output_dir = Path(case2.__file__).resolve().parent
        for filename in ("methanol_recycle_process.png", "tea_lcom_mac_sensitivity.png"):
            with Image.open(output_dir / filename) as image:
                self.assertGreaterEqual(min(image.info["dpi"]), 299)
                self.assertGreater(image.width, 1000)


if __name__ == "__main__":
    unittest.main()
