"""Meaningful regression checks for A v2 annual/profile and C interface contracts."""
import copy,json,unittest
from pathlib import Path
from annual_tea_interface import evaluate_annual_case
from integrate_a_supplement import RAW,ROOT,mechanical_rows,ls_annual,anl_annual,park_case,profile_case,prices,policy_results

def load():
    path=ROOT/'data_cohort/a_update_20261103/A_给BC的补充数据.json'
    if not path.exists():path=RAW/'A_给BC的补充数据.json'
    return json.loads(path.read_text(encoding='utf-8'))

class AnnualSupplementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s=load();cls.p=prices();cls.mass=mechanical_rows(cls.s)
        cls.lfp=next(r for r in cls.mass if r['chemistry']=='LFP')
        cls.nmc=next(r for r in cls.mass if r['chemistry']!='LFP')
        cls.ls=ls_annual(cls.s,cls.lfp['captured_blackmass_reference_t_a'])
    def test_load_and_reuse_applied_once(self):
        self.assertAlmostEqual(sum(r['received_pack_t_a'] for r in self.mass),68000)
        self.assertAlmostEqual(sum(r['recycling_inlet_pack_t_a'] for r in self.mass),59500)
        self.assertAlmostEqual(sum(r['cell_t_a'] for r in self.mass),38763.298)
    def test_capture_not_assay_or_li_recovery(self):
        self.assertAlmostEqual(sum(r['captured_blackmass_reference_t_a'] for r in self.mass),15587.39542700032)
        for r in self.mass:
            self.assertAlmostEqual(r['captured_blackmass_reference_t_a']+r['uncaptured_reference_t_a'],r['blackmass_component_inventory_t_a'])
            self.assertIsNone(r['actual_measured_blackmass_t_a'])
    def test_wet_vs_dry_intermediate_not_final_product(self):
        d={r['item_id']:r for r in self.ls};r=d['LS23_PRODUCT_CRUDE_LIC']
        self.assertAlmostEqual(r['quantity_per_year'],1338.0510913947232)
        self.assertAlmostEqual(r['dry_pure_substance_t_a'],1059.7364643846208)
        self.assertIsNone(r['plant_saleable_quantity'])
        self.assertAlmostEqual(d['LS23_PRODUCT_FEP_SLAG']['dry_pure_substance_t_a'],4193.784444026418)
    def test_liquid_caustic_is_commercial_not_pure(self):
        r=next(r for r in self.ls if r['item_id']=='LS_NAOH')
        self.assertAlmostEqual(r['quantity_per_year'],13788.61202757568)
        self.assertAlmostEqual(r['active_equivalent_t_a'],4412.355848824218)
        c=profile_case(self.ls,self.p)
        self.assertIsNone(next(r for r in c['cost_items'] if r['name']=='LS_NAOH')['unit_price'])
    def test_only_one_acid_version_and_one_steam(self):
        a=ls_annual(self.s,9418.8555147456,'alternate');d={r['item_id']:r for r in a}
        self.assertEqual(sum(r['item_id']=='LS_ACID' for r in a),1)
        self.assertAlmostEqual(d['LS_ACID']['quantity_per_year'],4617.1229733282935)
        self.assertEqual(sum(r['item_id']=='LS23_STEAM' for r in a),1)
    def test_combined_facility_electricity_and_cell_preprocessing_not_added(self):
        ids={r['item_id'] for r in self.ls}
        self.assertNotIn('LS23_COMBINED_ELECTRICITY',ids)
        self.assertNotIn('LS23_PRE_NG',ids)
        e=evaluate_annual_case(profile_case(self.ls,self.p))
        self.assertIn('cost_items.single_wet_stage_electricity.quantity_per_year',e['missing_fields'])
    def test_anl_cell_units_and_no_extra_capture_loss(self):
        d={r['item_id']:r for r in anl_annual(self.s,self.nmc['cell_t_a'])}
        self.assertAlmostEqual(d['electricity']['quantity_per_year'],524475.9722222222)
        self.assertAlmostEqual(d['natural_gas_energy']['quantity_per_year'],37762270)
        self.assertAlmostEqual(d['water']['quantity_per_year'],57178.29673943587)
        self.assertAlmostEqual(d['H2SO4']['quantity_per_year'],16313.30064)
        self.assertIsNone(d['H2SO4']['commercial_concentration'])
    def test_missing_not_zero_no_synthetic_lcor(self):
        cfg=json.loads((ROOT/'data_cohort/final_integration_20261103/C_final_assumptions.json').read_text(encoding='utf-8'))
        c=park_case(self.s,self.p,cfg);e=evaluate_annual_case(c)
        self.assertEqual(e['status'],'NOT_READY');self.assertIsNone(e['lcor_CNY_per_t_LCE'])
        self.assertIsNone(e['total_opex_CNY_a']);self.assertIsNone(e['annual_net_profit_CNY'])
        self.assertEqual(e['priced_cost_items']['feed_delivered'],451520000)
        self.assertEqual(e['priced_cost_items']['inbound_transport_additional'],0)
        self.assertFalse(e['formal_result_eligible'])
    def test_policy_does_not_use_proxy_capture_or_thresholds_as_measurement(self):
        out=policy_results(self.s)
        self.assertEqual(len(out),6)
        for r in out:
            self.assertEqual(r['result']['status'],'UNKNOWN')
            self.assertEqual(r['input']['metrics'],{'recycling_capacity_t_per_year':70000})
    def complete_case(self):
        # Synthetic, hand-checkable annual cash case; no plant provenance claim.
        c=profile_case(anl_annual(self.s,self.nmc['cell_t_a']),self.p)
        c.update(case_id='SYNTHETIC_A',data_status='synthetic_test',capex=100,discount_rate=0,operating_years=10,
          feed_t_per_year=10,fu_per_year=2,whole_boundary_activities_complete=True,
          saleable_product_quantities_complete=True,profile_compatibility_confirmed=True)
        c['cost_items']=c['cost_items'][:6]
        cats=['feedstock','transport','utilities','reagents','labor','maintenance','pollution_control','taxes_fees']
        from integrate_a_supplement import row
        c['cost_items']=[row('cost_'+cat,cat,1.,5.,'unit','synthetic_price','synthetic_quantity') for cat in cats]
        c['revenue_items']=[row('sale',None,2.,20.,'t_LCE','synthetic_price','synthetic_quantity',sale=True)]
        c['revenue_items'][0]['sale_status']='saleable_confirmed_for_case'
        return c
    def test_two_annual_cases_reach_engine_and_link_quantities_prices(self):
        a=self.complete_case();ra=evaluate_annual_case(a)
        self.assertEqual(ra['status'],'CALCULATED');self.assertEqual(ra['lcor_CNY_per_t_LCE'],5)
        b=copy.deepcopy(a);b['case_id']='SYNTHETIC_B';b['cost_items'][0]['quantity_per_year']=3
        rb=evaluate_annual_case(b);self.assertEqual(rb['lcor_CNY_per_t_LCE'],10)
        b['revenue_items'][0]['unit_price']=25;rc=evaluate_annual_case(b)
        self.assertEqual(rc['lcor_CNY_per_t_LCE'],5)
        self.assertFalse(ra['formal_result_eligible']);self.assertFalse(rb['formal_result_eligible'])
    def test_intermediate_sale_is_rejected_even_with_number(self):
        c=self.complete_case();c['revenue_items'][0]['sale_status']='internal_intermediate'
        r=evaluate_annual_case(c);self.assertIsNone(r['lcor_CNY_per_t_LCE'])
        self.assertIn('revenue_items.sale.saleability_unconfirmed',r['missing_fields'])
    def test_currency_unit_and_missing_amount_do_not_silently_pass(self):
        c=self.complete_case();c['cost_items'][0]['price_unit']='MJ';c['cost_items'][1]['currency']='USD';c['cost_items'][2]['quantity_per_year']=None
        r=evaluate_annual_case(c);self.assertEqual(r['status'],'NOT_READY')
        self.assertNotIn('cost_feedstock',r['priced_cost_items']);self.assertNotIn('cost_transport',r['priced_cost_items'])
        self.assertIsNone(r['total_opex_CNY_a'])
    def test_duplicate_price_rows_rejected(self):
        c=self.complete_case();c['cost_items'].append(c['cost_items'][0])
        with self.assertRaises(ValueError):evaluate_annual_case(c)
    def test_invalid_activity_feed_rejected(self):
        with self.assertRaises(ValueError):ls_annual(self.s,-1)
        with self.assertRaises(ValueError):anl_annual(self.s,float('nan'))

if __name__=='__main__':unittest.main()
