"""AI Prompt: 验证三组典型工况及工艺、适用对象、日期、严格边界和缺失值。
人工核验修正：尚待成员C审阅；夹具全部为合成测试数据。
"""
import copy
import json
import unittest
from pathlib import Path
from policy_engine import evaluate_policy

FIXTURES = json.loads((Path(__file__).parent / 'fixtures/policy_synthetic.json').read_text())


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.case = copy.deepcopy(FIXTURES[1])

    def test_three_typical_cases(self):
        for case, expected in zip(FIXTURES, ['FAIL', 'PASS', 'PASS']):
            with self.subTest(case=case['case_id']):
                self.assertEqual(evaluate_policy(case)['status'], expected)

    def test_inclusive_recovery_threshold(self):
        self.assertEqual(evaluate_policy(self.case)['status'], 'PASS')
        self.case['metrics']['li_smelting_recovery'] = .899999
        self.assertEqual(evaluate_policy(self.case)['status'], 'FAIL')

    def test_strict_energy_threshold(self):
        self.case['metrics']['lce_energy_kgce_per_t'] = 2200
        self.assertEqual(evaluate_policy(self.case)['status'], 'FAIL')

    def test_strict_impurity_threshold(self):
        self.case['metrics']['powder_al_impurity'] = .015
        self.assertEqual(evaluate_policy(self.case)['status'], 'FAIL')

    def test_missing_invalid_ratio(self):
        for value in [None, True, '0.9', 90, -1, float('nan'), float('inf')]:
            with self.subTest(value=value):
                self.case['metrics']['li_smelting_recovery'] = value
                result = evaluate_policy(self.case)
                self.assertEqual(result['status'], 'UNKNOWN')
                self.assertFalse(result['feasible'])

    def test_missing_metric_not_pass(self):
        del self.case['metrics']['process_wastewater_reuse']
        self.assertEqual(evaluate_policy(self.case)['status'], 'UNKNOWN')

    def test_repair_has_distinct_denominator(self):
        self.case['route'] = 'repair'
        self.case['produces_lithium_carbonate'] = False
        self.case['metrics']['repair_material_recovery'] = .99
        del self.case['metrics']['li_smelting_recovery']
        self.assertEqual(evaluate_policy(self.case)['status'], 'PASS')
        self.case['metrics']['repair_material_recovery'] = .98999
        self.assertEqual(evaluate_policy(self.case)['status'], 'FAIL')

    def test_mixed_requires_both_routes(self):
        self.case['route'] = 'mixed'
        self.assertEqual(evaluate_policy(self.case)['status'], 'UNKNOWN')
        self.case['metrics']['repair_material_recovery'] = .99
        self.assertEqual(evaluate_policy(self.case)['status'], 'PASS')

    def test_lfp_does_not_require_absent_nickel(self):
        self.case['metals_present'] = ['Li', 'Cu', 'Al']
        for key in ['ni_smelting_recovery', 'co_smelting_recovery', 'mn_smelting_recovery']:
            del self.case['metrics'][key]
        self.assertEqual(evaluate_policy(self.case)['status'], 'PASS')

    def test_eu_recycled_content_dates(self):
        self.case['eu_new_battery_scope'] = True
        self.case['metals_present'] = ['Li', 'Cu', 'Al']
        for date, content, expected in [
            ('2031-08-17', None, 'PASS'), ('2031-08-18', .05999, 'FAIL'),
            ('2031-08-18', .06, 'PASS'), ('2036-08-17', .06, 'PASS'),
            ('2036-08-18', .06, 'FAIL'), ('2036-08-18', .12, 'PASS')]:
            with self.subTest(date=date, content=content):
                self.case['evaluation_date'] = date
                self.case['metrics']['li_recycled_content'] = content
                self.assertEqual(evaluate_policy(self.case)['status'], expected)

    def test_eu_recovery_dates_and_separate_metric(self):
        self.case['eu_material_recovery_scope'] = True
        self.case['metals_present'] = ['Li']
        for date, value, expected in [
            ('2027-12-30', None, 'PASS'), ('2027-12-31', None, 'UNKNOWN'),
            ('2027-12-31', .5, 'PASS'), ('2031-12-30', .5, 'PASS'),
            ('2031-12-31', .5, 'FAIL'), ('2031-12-31', .8, 'PASS')]:
            with self.subTest(date=date, value=value):
                self.case['evaluation_date'] = date
                self.case['metrics']['li_eu_material_recovery'] = value
                self.assertEqual(evaluate_policy(self.case)['status'], expected)

    def test_domestic_does_not_require_eu_new_battery_content(self):
        self.case['evaluation_date'] = '2036-08-18'
        self.assertEqual(evaluate_policy(self.case)['status'], 'PASS')

    def test_unverified_law_cannot_pass_current_profile(self):
        self.assertEqual(evaluate_policy(self.case, profile='verified_current')['status'], 'UNKNOWN')

    def test_missing_scope_cannot_silently_skip(self):
        for key in ['route', 'eu_new_battery_scope', 'metals_present']:
            case = copy.deepcopy(self.case)
            del case[key]
            with self.subTest(key=key), self.assertRaises(ValueError):
                evaluate_policy(case)


if __name__ == '__main__':
    unittest.main(verbosity=2)
