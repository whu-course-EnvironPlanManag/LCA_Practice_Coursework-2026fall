"""AI-assisted tests for financial unit mapping, omissions and double counting."""
import csv
import tempfile
import unittest
from pathlib import Path
from prepare_economic_case import SPECS, build_case, load_quantities
from handoff_analysis import completion_check

class IntakeTests(unittest.TestCase):
    def setUp(self):
        self.p=[{'param_id':k,'normalized_value':v} for k,v in {
          **{f'CAP-{i:02}':100 for i in range(1,9)},'PRC-01':2026,'FIN-01':20,'FIN-02':.07,
          'FS-03':6640,'TR-01':500,**{s[2]:10 for s in SPECS if s[2]}}.items()]
        self.cfg={'load_factor':.85,'included_capex_ids':[f'CAP-{i:02}' for i in range(1,9)],'transport_additional_confirmed':None}
        self.q={s[0]:{'quantity_per_year':None,'quantity_source':''} for s in SPECS}

    def test_no_unknown_transport_addition(self):
        c=build_case(self.p,self.cfg,self.q)
        self.assertIsNone(c['cost_items'][1]['unit_price'])
        self.assertIn('cost_items.inbound_transport.unit_price',completion_check(c))

    def test_delivered_price_does_not_add_freight(self):
        self.cfg['transport_additional_confirmed']=False
        c=build_case(self.p,self.cfg,self.q)
        self.assertEqual(c['cost_items'][1]['unit_price'],0)

    def test_ex_vat_conversion_uses_explicit_model_column(self):
        for r in self.p:r['ex_vat_planning_value']=r['normalized_value']/1.13
        self.cfg['valuation_basis']='ex_vat_planning_assumption'
        c=build_case(self.p,self.cfg,self.q)
        self.assertAlmostEqual(c['capex'],800/1.13)
        self.assertAlmostEqual(c['cost_items'][0]['unit_price'],6640/1.13)

    def test_capex_control_total_not_double_counted(self):
        c=build_case(self.p+[{'param_id':'CAP-09','normalized_value':800}],self.cfg,self.q)
        self.assertEqual(c['capex'],800)
        self.cfg['included_capex_ids'].append('CAP-09')
        with self.assertRaises(ValueError):build_case(self.p,self.cfg,self.q)

    def test_actual_load_and_no_invented_lce_yield(self):
        c=build_case(self.p,self.cfg,self.q)
        self.assertEqual(c['feed_t_per_year'],68000)
        self.assertIsNone(c['fu_per_year'])
        self.assertTrue(completion_check(c))

    def test_each_product_has_own_unit(self):
        c=build_case(self.p,self.cfg,self.q)
        products={r['name']:r for r in c['revenue_items']}
        self.assertEqual(products['reuse_modules']['unit'],'kWh_sale_capacity')
        self.assertEqual(products['repair_product']['unit'],'annual_revenue_CNY')
        self.assertNotEqual(products['repair_product']['name'],products['LCE_product']['name'])

    def test_zero_quantity_needs_evidence_and_no_implicit_unit_change(self):
        rows=[dict(name=s[0],quantity_per_year='',unit=s[3],quantity_source='') for s in SPECS]
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'q.csv'
            def save():
                with path.open('w',encoding='utf-8-sig',newline='') as f:
                    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
            rows[0]['quantity_per_year']='0';save()
            with self.assertRaises(ValueError):load_quantities(path)
            rows[0]['quantity_source']='confirmed no grid purchase';save()
            self.assertEqual(load_quantities(path)[rows[0]['name']]['quantity_per_year'],0)
            rows[0]['unit']='MWh';save()
            with self.assertRaises(ValueError):load_quantities(path)

if __name__=='__main__':unittest.main()
