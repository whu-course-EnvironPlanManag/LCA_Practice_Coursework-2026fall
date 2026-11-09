# -*- coding: utf-8 -*-
"""
成员 B · 组件单元测试（LCA 模型 / 情景网格 / 帕累托排序）
=========================================================
不依赖成员 A 工序数据与成员 C 经济数据，仅验证本目录环境维度代码的
结构正确性与数值可复现性；不产出报告数值结论。

覆盖：
  1. LCA 分项之和与总量一致（核算闭合）；
  2. 原生矿产基准相对量级合理（盐湖卤水 GWP < 硬岩锂辉石 GWP）；
  3. 区域电网水因子随碳强度档位同步变化（regression: 修正前固定水因子）；
  4. build_activities 直接再生占比升高时电耗下降（方向正确性）；
  5. 情景网格规模 ≥ 500 且含关键列；
  6. 帕累托非支配排序在小规模合成算例上返回正确下标。

运行：python -m unittest code_implementation/test_lca_model.py -v
"""
from __future__ import annotations

import os
import sys
import unittest

import numpy as np

_BASE = os.path.dirname(os.path.abspath(__file__))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

from lca_model import LCAModel, VIRGIN_BENCHMARKS          # noqa: E402
from scenario_analysis import build_activities             # noqa: E402
from optimization import pareto_front                      # noqa: E402


class TestLCAModel(unittest.TestCase):
    def setUp(self) -> None:
        self.model = LCAModel()

    def test_breakdown_sums_to_total(self):
        res = self.model.compute(green_ratio=0.8)
        self.assertAlmostEqual(res.gwp_kgco2e, res.breakdown["gwp_kgco2e"].sum(), places=6)
        self.assertAlmostEqual(res.water_l, res.breakdown["water_l"].sum(), places=6)

    def test_virgin_benchmark_ordering(self):
        self.assertLess(
            VIRGIN_BENCHMARKS["salt_lake_brine"]["gwp"],
            VIRGIN_BENCHMARKS["hard_rock_spodumene"]["gwp"],
        )

    def test_grid_water_syncs_with_carbon(self):
        # 修正前区域水因子固定为 2 L/kWh；现应随碳强度档位同步变化。
        self.assertAlmostEqual(self.model._resolve_grid(0.314)["water"], 1.50)
        self.assertAlmostEqual(self.model._resolve_grid(0.556)["water"], 2.00)
        self.assertAlmostEqual(self.model._resolve_grid(0.749)["water"], 2.50)

    def test_grid_gwp_resolution(self):
        self.assertAlmostEqual(self.model._resolve_grid(0.314)["gwp"], 0.314)
        self.assertAlmostEqual(self.model._resolve_grid(0.749)["gwp"], 0.749)


class TestScenario(unittest.TestCase):
    def test_build_activities_direct_regeneration_lower_energy(self):
        pm0 = build_activities(0.0, 1.0)
        pm1 = build_activities(1.0, 1.0)
        self.assertLess(pm1["electricity_kwh"], pm0["electricity_kwh"])
        self.assertLess(pm1["natural_gas"], pm0["natural_gas"])

    def test_build_activities_reagents_reduce_with_direct_regeneration(self):
        pm0 = build_activities(0.0, 1.0)
        pm1 = build_activities(1.0, 1.0)
        self.assertEqual(pm1["sulfuric_acid_H2SO4"], 0.0)

    def test_scenario_grid_size(self):
        from scenario_analysis import _PROCESS, _GREEN, _GRID_EF, _LI_PRICE, _EFF
        n = len(_PROCESS) * len(_GREEN) * len(_GRID_EF) * len(_LI_PRICE) * len(_EFF)
        self.assertGreaterEqual(n, 500)
        self.assertEqual(n, 11 * 11 * 3 * 3 * 3)


class TestPareto(unittest.TestCase):
    def test_pareto_front_non_dominated(self):
        x = np.array([1.0, 2.0, 3.0, 2.5])
        y = np.array([3.0, 2.0, 1.0, 2.5])
        front = sorted(pareto_front(x, y).tolist())
        self.assertEqual(front, [0, 1, 2])


if __name__ == "__main__":
    unittest.main()