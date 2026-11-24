"""AI Prompt: 用手算可核对的合成数据验证资本年金、费用、激励、采购联动和MAC。
人工核验修正：尚待成员C核验。测试值不得用于园区经济结论。
"""
import copy
import json
import unittest
from pathlib import Path
from tea_model import capital_recovery_factor, evaluate_tea

FIXTURE = json.loads((Path(__file__).parent / 'fixtures/tea_synthetic.json').read_text())


class TeaTests(unittest.TestCase):
    def setUp(self):
        self.case = copy.deepcopy(FIXTURE)

    def test_zero_interest_and_hand_calculated_result(self):
        result = evaluate_tea(self.case)
        self.assertEqual(result['annualized_capex'], 1000)
        self.assertEqual(result['opex_per_year'], 16000)
        self.assertEqual(result['revenue_per_year'], 20000)
        self.assertEqual(result['base_lcor_per_fu'], -30)
        self.assertEqual(result['base_net_profit_per_t_feed'], 30)

    def test_positive_interest(self):
        self.assertAlmostEqual(capital_recovery_factor(.1, 2), 121 / 210)

    def test_required_inputs(self):
        for key, val in [('feed_t_per_year', 0), ('fu_per_year', 0), ('capex', None),
                         ('discount_rate', -.1), ('operating_years', 0),
                         ('operating_years', 2.5), ('capex', float('nan'))]:
            case = copy.deepcopy(self.case); case[key] = val
            with self.subTest(key=key, value=val), self.assertRaises(ValueError):
                evaluate_tea(case)

    def test_required_cost_categories(self):
        self.case['cost_items'].pop()
        with self.assertRaises(ValueError):
            evaluate_tea(self.case)

    def test_duplicate_items_rejected(self):
        self.case['cost_items'].append(self.case['cost_items'][0].copy())
        with self.assertRaises(ValueError):
            evaluate_tea(self.case)

    def test_scenario_incentive_separate(self):
        self.case['scenario_adjustments'] = [dict(kind='income', amount_per_year=500,
                                                status='assumption', basis='合成测试')]
        result = evaluate_tea(self.case)
        self.assertEqual(result['base_lcor_per_fu'], -30)
        self.assertEqual(result['with_scenario_lcor_per_fu'], -35)

    def test_linked_procurement(self):
        self.case['cost_items'][0]['price_link'] = dict(
            lce_price=200, reference_lce_price=100, lce_pass_through=.1,
            soh=.8, reference_soh=.7, soh_coefficient=100)
        result = evaluate_tea(self.case)
        self.assertAlmostEqual(result['cost_breakdown']['feed_purchase'], 12000)

    def test_mac_and_kg_to_t(self):
        self.case.update(boundary_id='same_product_system', gwp_kgco2e_per_fu=500)
        self.case['baseline'] = dict(functional_unit='t_feed', currency='CNY', price_year=2026,
                                     boundary_id='same_product_system',
                                     net_cost_per_fu=-40, gwp_kgco2e_per_fu=1000)
        self.assertEqual(evaluate_tea(self.case)['mac_per_tco2e'], 20)
        self.case['baseline']['gwp_kgco2e_per_fu'] = 500
        self.assertIsNone(evaluate_tea(self.case)['mac_per_tco2e'])
        self.case['baseline']['functional_unit'] = 't_LCE'
        with self.assertRaises(ValueError):
            evaluate_tea(self.case)

    def test_real_template_does_not_produce_fake_result(self):
        path = Path(__file__).resolve().parents[1] / 'data_cohort/tea_case_template.json'
        with self.assertRaises(ValueError):
            evaluate_tea(json.loads(path.read_text(encoding='utf-8')))


if __name__ == '__main__':
    unittest.main(verbosity=2)
