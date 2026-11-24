# -*- coding: utf-8 -*-
"""C成员LCOR/MAC模型测试：物料闭合、LCOR/MAC恒等式、政策与情景。"""
import math
import unittest

import lcor_mac_model as M
from policy_engine import evaluate_policy


def policy_case(m, name, recovery, rd):
    r = M.evaluate(m, linkage=0.80, recovery_case=recovery, rd_compliance=rd)
    pm = r["policy_metrics"]
    return {"case_id": name, "route": "smelting", "evaluation_date": "2026-11-04",
            "metals_present": ["Li", "Ni", "Co", "Mn", "Cu", "Al"],
            "eu_material_recovery_scope": False, "eu_new_battery_scope": False,
            "produces_lithium_carbonate": True,
            "metrics": {k: v for k, v in pm.items() if v is not None}}


class ModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = M.physical()
        cls.k3 = M.evaluate(cls.m, linkage=0.80, recovery_case="improved",
                            rd_compliance=True)

    def test_mass_balance_all_pass(self):
        for c in M.mass_balance_checks(self.m):
            with self.subTest(check=c["check"]):
                self.assertEqual(c["status"], "PASS")
                self.assertLess(c["rel_error"], 1e-9)

    def test_lce_identity(self):
        self.assertAlmostEqual(self.m["lce_t"],
                               self.m["lfp_li2co3_dry_t"] + self.m["nmc_li2co3_t"], places=9)

    def test_li_recovery_below_target_in_base(self):
        self.assertAlmostEqual(self.m["li_smelting_recovery"], 0.8888, places=4)
        self.assertLess(self.m["li_smelting_recovery"], 0.90)

    def test_improved_recovery_meets_target(self):
        im = M.apply_recovery_case(self.m, "improved")
        self.assertGreaterEqual(im["li_smelting_recovery"], 0.90)
        self.assertGreater(im["lce_t"], self.m["lce_t"])

    def test_lcor_identity(self):
        r = self.k3
        denom = r["flows"]["lce_t"]
        self.assertAlmostEqual(r["lcor_CNY_per_t"],
                               (r["annuity_CNY"] + r["opex_CNY"] - r["revenue_CNY"]) / denom,
                               places=6)

    def test_mac_identity(self):
        r = self.k3
        denom = (M.PRIMARY_GWP["lce_spodumene"] - r["gwp_kg_per_t_lce"]) / 1000.0
        self.assertGreater(denom, 0)
        self.assertAlmostEqual(r["mac_CNY_per_tCO2e"],
                               (r["lcor_CNY_per_t"] - 133000.0) / denom, places=4)

    def test_policy_fail_and_pass(self):
        self.assertEqual(evaluate_policy(policy_case(self.m, "base", "base", False))["status"],
                         "FAIL")
        self.assertEqual(evaluate_policy(policy_case(self.m, "imp", "improved", True))["status"],
                         "PASS")

    def test_rd_compliance(self):
        self.assertAlmostEqual(self.k3["rd_revenue_fraction"], 0.03, places=6)

    def test_scenario_grid_size(self):
        self.assertGreaterEqual(len(M.scenario_grid()), 500)

    def test_pareto_front_non_dominated(self):
        pts = [{"gwp": 1.0 + i * 0.1, "lcor": 10.0 - i * 0.5} for i in range(10)]
        front = M.pareto_front(pts)
        for p in front:
            for q in pts:
                self.assertFalse(all(q[k] <= p[k] for k in ("gwp", "lcor"))
                                 and any(q[k] < p[k] for k in ("gwp", "lcor")))
        knee = M.knee_point(front)
        self.assertIn(knee, front)

    def test_no_negative_flows(self):
        for k, v in self.m.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                with self.subTest(key=k):
                    self.assertGreaterEqual(v, 0)

    def test_determinism(self):
        a = M.evaluate(self.m, linkage=0.80, recovery_case="improved", rd_compliance=True)
        b = M.evaluate(self.m, linkage=0.80, recovery_case="improved", rd_compliance=True)
        self.assertEqual(a["lcor_CNY_per_t"], b["lcor_CNY_per_t"])
        self.assertEqual(a["gwp_kg_per_t_lce"], b["gwp_kg_per_t_lce"])

    def test_cost_revenue_flow_refs_exist(self):
        flow_ids = {r["flow_id"] for r in M.material_flow_rows(self.m)}
        known = {"shared", "capex_recycle", "outbound", "electricity", "compliance",
                 "rd", "lce_t", "copper", "al", "lfp_residues", "nmc_ng_mj"}
        for row in self.k3["costs"]["rows"]:
            ref = row["flow_ref"]
            ok = ref in known or ref in flow_ids or ref.startswith(("lfp_", "nmc_", "scrap_"))
            with self.subTest(item=row["item"]):
                self.assertTrue(ok, f"未映射的flow_ref: {ref}")

    def test_water_and_gwp_positive_gross(self):
        self.assertGreater(self.k3["gwp_gross_t"], 0)
        self.assertGreater(self.k3["water_m3_per_t_lce"], 0)
        self.assertLess(self.k3["gwp_net_t"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
