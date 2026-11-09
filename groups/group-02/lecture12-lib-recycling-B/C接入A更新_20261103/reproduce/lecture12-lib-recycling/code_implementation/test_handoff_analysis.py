"""AI Prompt: 测试交接复算、固定情景帕累托并列和2026再使用规则。
人工核验：待C审阅。
"""
import unittest
from handoff_analysis import pareto_indices, choose_anchors, completion_check
from reuse_policy_2026 import evaluate_reuse_application


class HandoffTests(unittest.TestCase):
    def test_same_x_dominated_and_duplicate(self):
        rows=[dict(case_id=i,gwp_kgco2e=x,lcor_rmb_per_t=y) for i,(x,y) in enumerate([(1,5),(1,2),(1,2),(2,2),(3,1)])]
        self.assertEqual(pareto_indices(rows),[1,2,4])
        self.assertEqual(choose_anchors(rows)['environment']['case_id'],1)

    def test_negative_cost_minimized(self):
        rows=[dict(case_id=0,gwp_kgco2e=1,lcor_rmb_per_t=-1),dict(case_id=1,gwp_kgco2e=1,lcor_rmb_per_t=-10)]
        self.assertEqual(pareto_indices(rows),[1])

    def test_no_fabricated_missing_data(self):
        c={k:0 for k in ['price_year','feed_t_per_year','fu_per_year','capex','discount_rate','operating_years']}
        self.assertEqual(completion_check(c),[])
        c['capex']=None
        self.assertEqual(completion_check(c),['capex'])

    def test_reuse_evidence_missing(self):
        self.assertEqual(evaluate_reuse_application(dict(evaluation_date='2026-11-03',has_reuse_branch=True))['status'],'UNKNOWN')

    def test_reuse_bicycle_prohibited(self):
        self.assertEqual(evaluate_reuse_application(dict(evaluation_date='2026-11-03',has_reuse_branch=True,application='electric_bicycle'))['status'],'FAIL')

    def test_reuse_scoped_pass_not_blanket_permission(self):
        r=evaluate_reuse_application(dict(evaluation_date='2030-01-01',has_reuse_branch=True,application='stationary_storage',prohibited_by_law_or_mandatory_standard=False,quality_standard_evidence_verified=True))
        self.assertEqual(r['status'],'PASS_SCOPED')

    def test_reuse_before_update(self):
        self.assertEqual(evaluate_reuse_application(dict(evaluation_date='2026-07-29',has_reuse_branch=True))['status'],'NOT_APPLICABLE')


if __name__ == '__main__':
    unittest.main()
