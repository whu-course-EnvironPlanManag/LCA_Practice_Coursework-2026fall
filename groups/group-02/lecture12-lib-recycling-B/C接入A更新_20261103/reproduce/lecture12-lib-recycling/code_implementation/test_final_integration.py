"""AI-assisted scientific/accounting checks for conditional final integration."""
import copy
import unittest
from finalize_member_c import default_assumptions,prices_received,read_csv,B,build_case,environmental,policy_case,b_energy
from tea_model import evaluate_tea
from policy_engine import evaluate_policy

class FinalIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=default_assumptions();cls.p=prices_received()
        raw=read_csv(B/'data_cohort/scenario_results.csv')
        cls.brows=[r for r in raw if float(r['process_mix'])==0 and float(r['green_ratio'])==0 and float(r['grid_ef'])==.314 and float(r['lithium_price_usd'])==10000]
        cls.factors={r['factor_name']:r for r in read_csv(B/'data_cohort/environmental_factors.csv')}
    def case(self,green=.5,price=133000,beta=0):return build_case(self.cfg,self.p,self.brows,3000,green,price,1.,beta)
    def test_b_synthetic_lcor_never_used(self):
        original=evaluate_tea(self.case())['base_net_cost_per_year']
        changed=copy.deepcopy(self.brows)
        for r in changed:r['lcor_rmb_per_t']='9999999999999';r['c_policy_status']='PASS'
        new=evaluate_tea(build_case(self.cfg,self.p,changed,3000,.5,133000,1.))['base_net_cost_per_year']
        self.assertEqual(original,new)
    def test_reference_lce_not_derived_from_a_inventory(self):
        c=self.case();self.assertEqual(c['fu_per_year'],3000)
        self.assertIn('conditional',c['data_status'])
        self.assertEqual(c['capex'],456000000)
    def test_chemical_commercial_concentration(self):
        c={r['name']:r for r in self.case()['cost_items']}
        self.assertAlmostEqual(c['peroxide27_5']['quantity_per_year'],400/.275/1000*3000)
        self.assertAlmostEqual(c['acid98']['quantity_per_year'],2500/.98/1000*3000)
    def test_inbound_freight_and_wages(self):
        c={r['name']:r for r in self.case()['cost_items']}
        self.assertEqual(c['separate_inbound_freight']['unit_price'],0)
        self.assertEqual(c['staff']['unit_price'],85000)
    def test_green_improves_cost_under_received_quotes(self):
        a=evaluate_tea(self.case(0));b=evaluate_tea(self.case(1))
        e,_=b_energy(self.brows,1.)
        self.assertAlmostEqual(a['base_net_cost_per_year']-b['base_net_cost_per_year'],e*3000*(.62-.41),delta=1e-5)
    def test_no_threshold_fill_and_no_policy_feasible_claim(self):
        e,h=b_energy(self.brows,1.);c=policy_case(self.cfg,1.,e,h)
        self.assertNotIn('li_smelting_recovery',c['metrics'])
        self.assertEqual(evaluate_policy(c)['status'],'UNKNOWN')
    def test_price_transmission_derivative(self):
        beta=.05
        a=evaluate_tea(self.case(price=133000,beta=beta));b=evaluate_tea(self.case(price=134000,beta=beta))
        self.assertAlmostEqual(b['base_net_cost_per_year']-a['base_net_cost_per_year'],1000*(68000*beta-3000))
    def test_regional_water_factor_is_not_fixed(self):
        e,h=b_energy(self.brows,1.)
        lo=environmental(self.cfg,self.factors,e,h,3000,0,.314)
        hi=environmental(self.cfg,self.factors,e,h,3000,0,.749)
        self.assertAlmostEqual(hi[1]-lo[1],e*(2.5-1.5))
    def test_invalid_quantity_rejected(self):
        with self.assertRaises(ValueError):build_case(self.cfg,self.p,self.brows,0,.5,133000,1.)

if __name__=='__main__':unittest.main()
