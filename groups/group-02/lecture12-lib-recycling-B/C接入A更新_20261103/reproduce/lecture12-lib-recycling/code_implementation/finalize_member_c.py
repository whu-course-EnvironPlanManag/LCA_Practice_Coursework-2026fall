"""AI-assisted member C final integration, strictly labelled conditional analysis.
No blocked A material-flow output is invented, no B synthetic LCOR enters the TEA.
Annual LCE and unquoted budgets are explicit financial scenario variables, not MFA results.
Human review/signature and actual project validation remain separate.
"""
from __future__ import annotations
import csv
import hashlib
import json
import math
from collections import Counter
from itertools import product
from pathlib import Path
from tea_model import evaluate_tea
from policy_engine import evaluate_policy
from reuse_policy_2026 import evaluate_reuse_application
from handoff_analysis import pareto_indices

ROOT=Path(__file__).resolve().parents[1]
A=ROOT.parent/'lecture12-20261103-classroom-case3/lecture12-20261103-classroom-case3'
B=ROOT.parent/'lecture12-lib-recycling-B/lecture12-lib-recycling-B'
DATA=ROOT/'data_cohort/final_integration_20261103'
REPORT=ROOT/'report/final_integration_20261103'
DELIVERY=ROOT.parent/'outputs/C最终交付_20261103'

def read_csv(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def write_csv(path,rows):
    rows=list(rows)
    if not rows:return
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def dump(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
def source_hashes():
    files=[]
    for role,base in [('A',A),('B',B)]:
        for p in base.rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts:
                files.append(dict(role=role,path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size))
    return files

def default_assumptions():
    return dict(
      case_id='C_HYD_CONDITIONAL_20261103',status='explicit_financial_scenarios_not_validated_plant',
      scope='纯湿法再生+保留再次使用能力的报价现金覆盖测算；不宣称已闭合物质流、完整利润或法定合规',
      designed_pack_t_a=80000,load_factor=.85,reuse_design_capacity_t_a=10000,
      reuse_share_of_actual=.125,composition_LFP=.6,composition_NMC=.4,
      operating_years=20,real_discount_rate=.07,
      capex_ids=['CAP-01','CAP-02','CAP-03','CAP-05','CAP-06','CAP-08'],
      excluded_capex={'CAP-04':'本轮不选直接修复路线，避免其产品功能等效缺口',
                     'CAP-07':'购入绿电情景，不再同时计自有光储系统；有自发电方案时另算'},
      lce_reference_t_a=3000,lce_scenario_t_a=list(range(1000,4001,250)),
      lce_quantity_note='人为设置的财务产量变量，不是A产量；区间不代表已证明的技术可行产量',
      green_reference=.5,grid_reference=.556,efficiency_reference=1.,
      quoted_LCE_price_CNY_per_t=133000,lce_price_scenarios_CNY_per_t=[72000,133000,158400,360000],
      price_note='133000为收到报价假设，其余为文献锂价×假设汇率7.2的压力锚点；非同年实测分布',
      workforce_person_year=120,workforce_sensitivity=[80,120,160],
      maintenance_fraction_of_selected_capex=.02,
      rd_budget_CNY_a=5000000,other_services_CNY_a=3000000,other_fees_CNY_a=1000000,
      financial_budget_note='120人、2%维修率、研发500万及其他300万/100万为C显式预算假设，非A定员或核实报价；不用于证明研发比例合规',
      freshwater_m3_per_t_LCE=30,wastewater_basic_CNY_m3=8,wastewater_advanced_increment_CNY_m3=25,
      water_note='30m3/t为新水预算变量；不从B上游水足迹反推。废水30m3基础+其中10m3深度处理增量，价格8/25均为C假设',
      transport_inbound_km=180,
      material_price_basis='B试剂活动量暂按有效物质kg，分别换算98%酸/27.5%双氧水/99%片碱/重质纯碱/90%石灰商品吨；因子基准仍待核',
      financial_tax_basis='统一采用收到的含税报价现金金额，不作VAT清算；工资原额不除税；不是已确定的税前利润',
      other_product_credit_reference_CNY_a=0,
      other_credit_note='零表示暂不计入其他产品回款的参照口径，不表示物理上没有铜铝、盐或再次使用产品；用所需额外净贡献表达缺口',
      feed_price_link_beta_reference=0.,
      beta_note='仅零传导部分敏感性参照，非采购合同估计；另给beta=.02/.05/.1的联动敏感性，系人为扰动',
      policy_note='只输入设计能力及B能耗代理；未测回收率、杂质、固氟和回用率保持缺失，不把阈值当实测',
      mac_note='缺原生同产品篮子成本与完整分配，MAC不计算',
      evidence_status='quoted_planning_assumptions_plus_B_provisional_activities')

def prices_received():
    return {r['param_id']:float(r['normalized_value']) for r in read_csv(ROOT/'data_cohort/economic_parameters_received.csv')}

def b_energy(brows,eff):
    matches=[r for r in brows if float(r['process_mix'])==0 and float(r['energy_efficiency'])==eff]
    if not matches:raise ValueError('B缺少纯湿法对应能效工况')
    r=matches[0]
    # Only environmental activity fields are consumed. Ignore lcor/policy flags.
    return float(r['electricity_kwh']),float(r['heat_mj'])

def build_case(cfg,p,brows,q,green,price,eff,beta=0.):
    if not (q>0 and math.isfinite(q) and 0<=green<=1 and eff>0):raise ValueError('非法条件工况')
    feed=cfg['designed_pack_t_a']*cfg['load_factor']
    capex=sum(p[k] for k in cfg['capex_ids'])
    e,h=b_energy(brows,eff)
    effective_feed_price=p['FS-03']+beta*(price-cfg['quoted_LCE_price_CNY_per_t'])
    if effective_feed_price<0:raise ValueError('联动后采购价负值，超出局部线性情景适用范围')
    costs=[];rev=[]
    def cost(name,category,qty,unit_price,unit,source):
        costs.append(dict(name=name,category=category,quantity_per_year=qty,unit_price=unit_price,unit=unit,source_id=source))
    cost('feed_delivered','feedstock',feed,effective_feed_price,'t_pack','USER_QUOTE_FS03; beta_explicit_scenario')
    cost('separate_inbound_freight','transport',feed,0.,'t_pack','USER_REVISED_FS:delivered_included')
    cost('grid_power','utilities',e*q*(1-green),p['UT-01'],'kWh','B_pure_hydro_activity;USER_UT01')
    cost('green_power','utilities',e*q*green,p['UT-02'],'kWh','B_pure_hydro_activity;USER_UT02')
    cost('process_steam','utilities',h*q,p['UT-03'],'MJ','B_steam_proxy;USER_UT03')
    cost('makeup_water','utilities',cfg['freshwater_m3_per_t_LCE']*q,p['UT-04'],'m3','C_water_budget_assumption;USER_UT04')
    reagents=[('acid98',2500,.98,'RG-01'),('peroxide27_5',400,.275,'RG-02'),
              ('naoh99',1500,.99,'RG-03'),('soda',1600,1.,'RG-04'),('lime90',800,.9,'RG-05')]
    for name,kg,purity,pid in reagents:
        cost(name,'reagents',kg/purity/1000*q,p[pid],'t_commercial_product','B_reagent_proxy;C_active_basis_assumption;USER_'+pid)
    cost('staff','labor',cfg['workforce_person_year'],p['LB-01'],'person_year','C_staff_budget;USER_LB01:no_VAT_deflation')
    cost('maintenance','maintenance',capex,cfg['maintenance_fraction_of_selected_capex'],'CNY_selected_capex','C_2pct_budget_not_measured')
    cost('residue_disposal','pollution_control',1.5*q,p['WS-01'],'t_residue','B_residue_proxy;USER_WS01:waste_code_pending')
    cost('basic_wastewater','pollution_control',30*q,cfg['wastewater_basic_CNY_m3'],'m3','B_volume_proxy;C_budget_unit_price')
    cost('advanced_increment','pollution_control',10*q,cfg['wastewater_advanced_increment_CNY_m3'],'m3_incremental','C_increment_not_double_volume_assumption')
    cost('rd_budget','other',1,cfg['rd_budget_CNY_a'],'annual_budget','C_explicit_budget')
    cost('other_services','other',1,cfg['other_services_CNY_a'],'annual_budget','C_explicit_budget:insurance_quality_warranty_and_unlisted_services')
    cost('other_fees','taxes_fees',1,cfg['other_fees_CNY_a'],'annual_budget','C_budget_excluding_VAT_income_tax_and_incentives')
    rev.append(dict(name='LCE_sales_only',quantity_per_year=q,unit_price=price,unit='t_battery_grade_LCE',source_id='C_LCE_volume_scenario;USER_or_literature_price_assumption'))
    return dict(case_id=cfg['case_id'],currency='CNY',price_year=2026,
      data_status='explicit_conditional_scenario_not_validated_plant',functional_unit='t_battery_grade_LCE_product',
      feed_t_per_year=feed,fu_per_year=q,capex=capex,discount_rate=cfg['real_discount_rate'],operating_years=cfg['operating_years'],
      cost_items=costs,revenue_items=rev,scenario_adjustments=[],
      boundary_id='C_gross_quote_budget_LCE_revenue_only_other_products_net_credit_unresolved',
      source_note=cfg['financial_tax_basis'])

def environmental(cfg,factors,e,h,q,green,grid):
    grid_name={.314:'grid_low_carbon',.556:'grid_china_base',.749:'grid_high_carbon'}[grid]
    rows=[]
    def add(name,amount,fac):
        f=factors[fac];rows.append(dict(item=name,quantity_per_t_LCE=amount,factor=fac,
          gwp_kgco2e=amount*float(f['gwp_kgco2e_per_unit']),water_l=amount*float(f['water_l_per_unit'])))
    add('网电',e*(1-green),grid_name);add('直购绿电',e*green,'green_power_mix');add('蒸汽',h,'process_steam')
    for name,value in [('sulfuric_acid_H2SO4',2500),('hydrogen_peroxide_H2O2',400),('sodium_hydroxide_NaOH',1500),('sodium_carbonate_Na2CO3',1600),('lime_CaO',800)]:add(name,value,name)
    add('入厂运输',cfg['designed_pack_t_a']*cfg['load_factor']*cfg['transport_inbound_km']/q,'diesel_truck')
    add('基础废水处理',30,'wastewater_treatment');add('深度处理增量',10,'fluoride_wastewater_advanced');add('残渣处理',1.5,'hazardous_residue_disposal')
    return sum(r['gwp_kgco2e'] for r in rows),sum(r['water_l'] for r in rows),rows

def policy_case(cfg,eff,e,h,year=2030):
    return dict(case_id=f'C_HYD_{year}_EE{eff}',evaluation_date=f'{year}-12-31',route='smelting',
      metals_present=['Li','Ni','Co','Mn','Cu','Al'],eu_material_recovery_scope=False,eu_new_battery_scope=False,
      produces_lithium_carbonate=True,metrics={'recycling_capacity_t_per_year':70000,
      'lce_energy_kgce_per_t':e*.1229+h/29.3076})

def analyze(cfg,p,brows,factors):
    output=[];policies={}
    for eff in [.8,1.,1.2]:
        e,h=b_energy(brows,eff)
        policies[eff]=evaluate_policy(policy_case(cfg,eff,e,h))
    for i,(q,g,price,eff,grid) in enumerate(product(cfg['lce_scenario_t_a'],[i/10 for i in range(11)],cfg['lce_price_scenarios_CNY_per_t'],[.8,1.,1.2],[.314,.556,.749])):
        case=build_case(cfg,p,brows,q,g,price,eff)
        tea=evaluate_tea(case);e,h=b_energy(brows,eff);gwp,water,_=environmental(cfg,factors,e,h,q,g,grid)
        gap=tea['base_net_cost_per_year']
        totalcost=tea['annualized_capex']+tea['opex_per_year']
        output.append(dict(case_id=i,annual_LCE_scenario_t=q,green_ratio=g,LCE_price_quote_CNY_t=price,
          energy_efficiency=eff,grid_ef=grid,annualized_capex_CNY=tea['annualized_capex'],opex_CNY_a=tea['opex_per_year'],
          LCE_receipts_CNY_a=tea['revenue_per_year'],gross_quote_gap_CNY_a=gap,
          gap_CNY_per_t_LCE=gap/q,other_net_credit_needed_CNY_a=max(0,gap),
          breakeven_LCE_quote_CNY_t=totalcost/q,gwp_kgco2e_t_LCE=gwp,water_l_t_LCE=water,
          policy_status=policies[eff]['status'],confirmed_policy_feasible=False,
          actual_plant_profit_CNY_a=None,MAC_CNY_tCO2=None,
          data_status='CONDITIONAL_BUDGET_NOT_VALIDATED_PLANT'))
    return output,policies

def main():
    for path in [DATA,REPORT,DELIVERY]:path.mkdir(parents=True,exist_ok=True)
    originals=source_hashes();dump(DATA/'source_manifest_before.json',originals)
    config_path=DATA/'C_final_assumptions.json'
    if not config_path.exists():dump(config_path,default_assumptions())
    cfg=json.loads(config_path.read_text(encoding='utf-8'));p=prices_received()
    brows=read_csv(B/'data_cohort/scenario_results.csv')
    factors={r['factor_name']:r for r in read_csv(B/'data_cohort/environmental_factors.csv')}
    scenarios,policies=analyze(cfg,p,brows,factors)
    write_csv(DATA/'conditional_scenarios.csv',scenarios)
    q0=cfg['lce_reference_t_a'];price0=cfg['quoted_LCE_price_CNY_per_t'];eff0=1.
    anchors=[next(r for r in scenarios if r['annual_LCE_scenario_t']==q0 and r['LCE_price_quote_CNY_t']==price0 and r['energy_efficiency']==eff0 and r['grid_ef']==.556 and r['green_ratio']==g) for g in [0,.5,1.]]
    write_csv(DATA/'conditional_representatives.csv',anchors)
    baseline_case=build_case(cfg,p,brows,q0,.5,price0,eff0)
    baseline=evaluate_tea(baseline_case)
    dump(DATA/'conditional_baseline_case.json',baseline_case)
    dump(REPORT/'conditional_baseline_results.json',{'scope':cfg['scope'],'tea_mathematical_output':baseline,
      'full_project_profit':None,'other_product_quantities':None,'MAC':None,'not_validated_plant':True})
    write_csv(DATA/'annual_cost_breakdown.csv',[dict(name=k,annual_CNY=v) for k,v in baseline['cost_breakdown'].items()])
    e,h=b_energy(brows,1.);_,_,contrib=environmental(cfg,factors,e,h,q0,.5,.556)
    write_csv(DATA/'environmental_contributions.csv',contrib)
    # Comparison only within fixed external conditions; never optimize over market prices or LCE yields.
    fixed=[dict(r,gwp_kgco2e=r['gwp_kgco2e_t_LCE'],lcor_rmb_per_t=r['gap_CNY_per_t_LCE']) for r in scenarios
           if r['annual_LCE_scenario_t']==q0 and r['LCE_price_quote_CNY_t']==price0 and r['energy_efficiency']==1 and r['grid_ef']==.556]
    front=[fixed[i]['case_id'] for i in pareto_indices(fixed)]
    dump(REPORT/'conditional_front.json',dict(fixed_external_conditions={'annual_LCE_scenario_t':q0,'price':price0,'efficiency':1,'grid':.556},
      case_ids=front,policy_feasible_front=[],note='条件预算前沿不是已确认合规前沿；本价格下绿电同时改善成本碳水，不构造拐点'))
    # Local procurement pass-through sensitivity uses explicit beta, no hidden fixed procurement assumption.
    linked=[]
    for beta,price in product([0,.02,.05,.1],[72000,100000,133000,158400,200000,260000,360000]):
        case=build_case(cfg,p,brows,q0,.5,price,1.,beta);t=evaluate_tea(case)
        linked.append(dict(beta=beta,LCE_price_quote_CNY_t=price,annual_LCE_scenario_t=q0,
          delivered_pack_price_CNY_t=case['cost_items'][0]['unit_price'],gross_quote_gap_CNY_a=t['base_net_cost_per_year'],
          scope='人为采购传导系数扰动，非合同回归估计；其他产品净贡献未计'))
    write_csv(DATA/'procurement_link_sensitivity.csv',linked)
    drows=read_csv(A/'data_cohort/dmfa_yichang_annual_total.csv')
    coverage=[]
    for r in drows:
        if int(r['year']) in [2026,2029,2030,2035]:
            collected=float(r['collected_total_t']);feed=68000.
            coverage.append(dict(collection_scenario=r['collection_scenario'],year=int(r['year']),
              known_cohort_retired_t=float(r['retired_total_t']),known_cohort_collected_t=collected,
              illustrative_plant_feed_t=feed,known_cohort_to_plant_ratio_upper_bound=collected/feed,
              scope='2010—2025首装队列贡献，非全市未来总量；上界假设全部进入本园区，不表示实际捕获'))
    write_csv(DATA/'dmfa_plant_boundary_check.csv',coverage)
    # Reapply only already-confirmed split to received composition inventory, without inventing sorting yields.
    inventory=read_csv(A/'data_cohort/received_component_inventory.csv')
    inventory_schema=list(inventory[0])
    partial=[]
    for r in inventory:
        numeric_key=next((k for k in ['annual_mass_t_a','annual_mass_t','mass_t_a'] if k in r),None)
        if numeric_key:
            partial.append(dict(component_id=r.get('component_id',r.get('component',r.get('name',''))),chemistry=r.get('chemistry',''),
              level=r.get('level',''),A_design_received_inventory_t=float(r[numeric_key]),
              C_actual_recycling_inlet_inventory_t=float(r[numeric_key])*.85*.875,
              scope='C假设两体系均按85%负荷及12.5%再次使用分流；仅入口组分存量，不是分选产物或LCE产量'))
    write_csv(DATA/'conditional_recycling_inlet_inventory.csv',partial)
    policyrows=[]
    for year,eff in product([2026,2030,2035],[.8,1.,1.2]):
        ee,hh=b_energy(brows,eff);pol=evaluate_policy(policy_case(cfg,eff,ee,hh,year))
        for r in pol['checks']:policyrows.append(dict(evaluation_year=year,efficiency=eff,**r))
    write_csv(DATA/'project_policy_checks.csv',policyrows)
    reuse=evaluate_reuse_application(dict(evaluation_date='2030-12-31',has_reuse_branch=True,application='stationary_storage',
          prohibited_by_law_or_mandatory_standard=None,quality_standard_evidence_verified=None))
    fixtures=json.loads((ROOT/'code_implementation/fixtures/policy_synthetic.json').read_text())
    typical=[dict(case_id=f['case_id'],status=evaluate_policy(f)['status'],scope='合成测试，不是项目方案') for f in fixtures]
    typical.append(dict(case_id='PROJECT_EVIDENCE_PENDING',status=policies[1.]['status'],scope='项目证据判定'))
    write_csv(DATA/'policy_typical_cases.csv',typical)
    after=source_hashes();unchanged=originals==after
    if not unchanged:raise AssertionError('A/B源文件发生变化')
    dump(DATA/'source_manifest_after.json',after)
    summary=dict(status='C_CONDITIONAL_DELIVERY_COMPLETE_NOT_EMPIRICAL_PLANT',A_source=str(A),B_source=str(B),
      source_files_unchanged=unchanged,B_received_rows=len(brows),
      B_received_tea_status=dict(Counter(r.get('c_tea_status','') for r in brows)),
      B_received_policy_status=dict(Counter(r.get('c_policy_status','') for r in brows)),
      B_received_synthetic_LCOR_used=False,B_threshold_fill_as_measurement_used=False,
      C_conditional_scenarios=len(scenarios),C_confirmed_policy_feasible=0,
      baseline=dict(annual_LCE_scenario_t=q0,actual_feed_scenario_t=68000,reuse_actual_scenario_t=8500,
        recycling_actual_scenario_t=59500,selected_capex_quote_CNY=baseline_case['capex'],
        annualized_capex_quote_CNY=baseline['annualized_capex'],opex_quote_CNY=baseline['opex_per_year'],
        LCE_receipts_quote_CNY=baseline['revenue_per_year'],gross_quote_gap_CNY=baseline['base_net_cost_per_year'],
        other_net_credit_needed_CNY=max(0,baseline['base_net_cost_per_year']),
        breakeven_LCE_quote_CNY_t=(baseline['annualized_capex']+baseline['opex_per_year'])/q0),
      conditional_front_ids=front,reuse_status=reuse,actual_LCE_output_t_a=None,actual_project_profit=None,MAC=None,
      inventory_input_schema=inventory_schema,
      provenance_note='C提供TEA/政策引擎和规则；B当前合成LCOR及阈值填充是方法校验开关结果，责任按函数调用区分。')
    dump(REPORT/'summary.json',summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
