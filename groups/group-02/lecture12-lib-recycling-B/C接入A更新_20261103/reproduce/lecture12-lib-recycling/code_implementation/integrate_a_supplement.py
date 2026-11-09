"""Integrate A's new supplement into profile-separated ANNUAL physical ledgers.
No raw A/B files altered. No hidden activation, cross-source plant combination,
intermediate-as-battery-grade sales, steam-energy inversion, or LCE multipliers.
"""
import copy,csv,hashlib,json,math,os,shutil
from pathlib import Path
from tea_model import capital_recovery_factor
from annual_tea_interface import evaluate_annual_case
from policy_engine import evaluate_policy
from reuse_policy_2026 import evaluate_reuse_application

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT.parent/'A_BC核查与数据补充_20261103/A_BC核查与数据补充_20261103'
DATA=ROOT/'data_cohort/a_update_20261103'
REPORT=ROOT/'report/a_update_20261103'
DELIVERY=ROOT.parent/'outputs/C接入A更新_20261103'
SOURCE=Path(os.environ.get('A_SUPPLEMENT_PATH',str(DATA/'A_给BC的补充数据.json')))

def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def csvout(p,rows):
    if not rows:return
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def source_hashes():
    return {str(p.relative_to(RAW)):hashlib.sha256(p.read_bytes()).hexdigest() for p in RAW.rglob('*') if p.is_file()} if RAW.exists() else {}
def load_supplement():return read(SOURCE)
def prices():
    with (ROOT/'data_cohort/economic_parameters_received.csv').open(encoding='utf-8-sig') as f:
        return {r['param_id']:float(r['normalized_value']) for r in csv.DictReader(f)}

def mechanical_rows(s):
    rows=[];rate=s['mechanical_capture_screening']['reference_capture_fraction']
    for r in s['annual_common_inventory']:
        inv=r['blackmass_component_inventory_t_a'];capture=inv*rate
        rows.append(dict(**r,case_id='PARK_ANNUAL_MASS_20261103',capture_profile='EV_I_M02_TRANSFER_SCREENING',
          capture_fraction=rate,captured_blackmass_reference_t_a=capture,uncaptured_reference_t_a=inv-capture,
          actual_measured_blackmass_t_a=None,physical_plant_product_t_a=None,source_note='JR组成+EV I实验迁移；未证实分母/体系等效，不是元素收率'))
    return rows

def ls_annual(s,powder,acid_version='total',case_id='LS_REFERENCE_EV_I_TOTAL'):
    """Scale only native LS WET powder-stage rows, not JR/LS full-plant flows."""
    if not math.isfinite(powder) or powder<=0:raise ValueError('powder must be positive finite')
    if acid_version not in ['total','alternate']:raise ValueError('acid version')
    ls=s['reference_routes'][0];rows=[]
    for r in ls['records']:
        unit=r['unit']
        if unit not in ['t_report_product/t_declared_powder','m3/t_powder','t_steam/t_powder','t/t_powder','t_Li/t_declared_powder']:continue
        amount=r['value']*powder
        annual_unit={'t_report_product/t_declared_powder':'t_report_product/a','m3/t_powder':'m3/a','t_steam/t_powder':'t_steam/a','t/t_powder':'t/a','t_Li/t_declared_powder':'t_Li/a'}[unit]
        row=dict(case_id=case_id,profile_id=ls['profile_id'],item_id=r['id'],label=r['label'],
          quantity_per_year=amount,unit=annual_unit,input_powder_t_a=powder,
          source_id=r['source_id'],locator=r['locator'],source_intensity=r['value'],source_unit=unit,
          moisture_fraction=r.get('moisture_fraction'),commercial_concentration=None,active_equivalent_t_a=None,
          dry_pure_substance_t_a=None,role=r.get('product_role','wet_stage_activity_or_intermediate'),
          plant_saleable_quantity=None,status='INDEPENDENT_LS_NATIVE_REFERENCE_NOT_PLANT',
          scope_note='仅匹配LFP粉料的LS湿法独立参照；投料规模借EV I数量，不证明JR产粉已兼容；不含电芯预处理')
        if r.get('moisture_fraction') is not None and r.get('dry_purity_fraction') is not None:
            row['dry_pure_substance_t_a']=amount*(1-r['moisture_fraction'])*r['dry_purity_fraction']
        if r.get('reported_product_grade_fraction') is not None:
            row['reported_element_content_t_a']=amount*r['reported_product_grade_fraction']
        rows.append(row)
    for r in ls['commercial_reagent_intensities']:
        value=.4902 if acid_version=='alternate' and r['parameter_id']=='LS_ACID' else r['value']
        amount=value*powder
        rows.append(dict(case_id=case_id,profile_id=ls['profile_id'],item_id=r['parameter_id'],label=r['name'],
          quantity_per_year=amount,unit='t_commercial_product/a',input_powder_t_a=powder,
          source_id='SRC040',locator=r['locator'],source_intensity=value,source_unit='t_commercial_product/t_powder',
          commercial_concentration=r['specification_fraction'],active_equivalent_t_a=amount*r['specification_fraction'],
          dry_pure_substance_t_a=None,role='reagent_input',plant_saleable_quantity=None,
          status='INDEPENDENT_LS_NATIVE_REFERENCE_NOT_PLANT',acid_version=acid_version,
          scope_note='商品吨和有效吨不重复相加；两种硫酸版本分情景而不叠加'))
    return rows

def anl_annual(s,cell_t,case_id='ANL_CELL_REFERENCE'):
    if not math.isfinite(cell_t) or cell_t<=0:raise ValueError('cell feed must be positive finite')
    route=s['reference_routes'][1];rows=[]
    for r in route['activity_intensities']:
        if r['unit']=='kg_declared_chemical/kg_cell':qty=r['value']*cell_t;unit='t_declared_chemical/a'
        elif r['unit']=='MJ/kg_cell' and r['id']=='electricity':qty=r['value']*1000/3.6*cell_t;unit='kWh/a'
        elif r['unit']=='MJ/kg_cell':qty=r['value']*1000*cell_t;unit='MJ/a'
        elif r['unit']=='USgal/kg_cell':qty=r['value']*3.785411784*cell_t;unit='m3/a'
        else:raise ValueError('unmapped ANL unit')
        rows.append(dict(case_id=case_id,profile_id=route['profile_id'],item_id=r['id'],label=r['id'],
          quantity_per_year=qty,unit=unit,input_cell_t_a=cell_t,source_id=route['source_id'],locator=route['locator'],
          source_intensity=r['value'],source_unit=r['unit'],commercial_concentration=None,
          active_equivalent_t_a=None,status='INDEPENDENT_ANL_CELL_REFERENCE_NOT_PLANT',
          scope_note='通用电芯整套机械+湿法参考；不再乘EV捕集率或叠LS前处理；water按原作者消费量估计，非已闭合园区取水'))
    return rows

def row(name,cat,q,p,unit,price_source,quantity_source,*,sale=False,**extra):
    r=dict(name=name,quantity_per_year=q,unit_price=p,unit=unit,price_unit=unit,
      currency='CNY',price_year=2026,source_id=price_source,quantity_source_id=quantity_source,**extra)
    if cat:r['category']=cat
    if sale:r['sale_status']='unknown'
    return r

def basecase(case_id,profile,feed):
    return dict(case_id=case_id,profile_id=profile,currency='CNY',price_year=2026,
      data_status='conditional_reference',functional_unit='t_battery_grade_LCE_product',
      feed_t_per_year=feed,fu_per_year=None,capex=None,discount_rate=.07,operating_years=20,
      boundary_id=profile,cost_items=[],revenue_items=[],scenario_adjustments=[],
      whole_boundary_activities_complete=False,saleable_product_quantities_complete=False,
      profile_compatibility_confirmed=False)

def park_case(s,p,cfg):
    op=s['operating_case'];case=basecase('PARK_ANNUAL_20261103','PARK_ANNUAL_NOT_COMPOSITE_REFERENCE',op['actual_received_pack_t_a'])
    case['capex']=sum(p[k] for k in cfg['capex_ids']);case['discount_rate']=cfg['real_discount_rate'];case['operating_years']=cfg['operating_years']
    case['cost_items']=[
      row('feed_delivered','feedstock',op['actual_received_pack_t_a'],p['FS-03'],'t_pack','C:FS03_received_quote','A:operating_case'),
      row('inbound_transport_additional','transport',op['actual_received_pack_t_a'],0.,'t_pack','C:delivered_includes_inbound','A:operating_case'),
      row('whole_plant_grid_electricity','utilities',None,p['UT-01'],'kWh','C:UT01','A:M08_ELECTRIC'),
      row('whole_plant_green_electricity','utilities',None,p['UT-02'],'kWh','C:UT02','A:M08_ELECTRIC'),
      row('whole_plant_steam','utilities',None,p['UT-03'],'MJ','C:UT03','A:M08_STEAM'),
      row('whole_plant_freshwater','utilities',None,p['UT-04'],'m3','C:UT04','A:M08_WATER'),
      row('whole_plant_reagents','reagents',None,None,'annual_CNY','C:spec_price_pending','A:profile_compatibility_pending'),
      row('staff_budget','labor',cfg['workforce_person_year'],p['LB-01'],'person_year','C:LB01','C:explicit_staff_budget_not_A_design'),
      row('maintenance_budget','maintenance',case['capex'],cfg['maintenance_fraction_of_selected_capex'],'CNY_capex','C:explicit_rate','C:chosen_capex'),
      row('whole_plant_waste_treatment','pollution_control',None,None,'annual_CNY','C:waste_class_price_pending','A:whole_plant_waste_pending'),
      row('rd_budget','other',1.,cfg['rd_budget_CNY_a'],'annual_budget','C:explicit_budget','C:budget_not_actual'),
      row('other_services_budget','other',1.,cfg['other_services_CNY_a'],'annual_budget','C:explicit_budget','C:budget_not_actual'),
      row('other_fees_budget','taxes_fees',1.,cfg['other_fees_CNY_a'],'annual_budget','C:explicit_budget','C:budget_not_actual')]
    for name,pid,unit in [('LCE_product','PR-01','t_battery_grade_LCE'),('iron_phosphate','PR-02','t_sale_FePO4'),('nmc_salts','PR-03','t_sale_mixed_salt'),('copper','PR-04','t_sale_Cu'),('aluminium','PR-05','t_sale_Al'),('reuse_modules','PR-06','kWh_sale_capacity')]:
        case['revenue_items'].append(row(name,None,None,p[pid],unit,'C:'+pid,'A:M05_PRODUCTS_or_M01_REUSE_SALE',sale=True))
    return case

def profile_case(annual,p,green=.5):
    profile=annual[0]['profile_id'];cid=annual[0]['case_id']
    feed=annual[0].get('input_powder_t_a',annual[0].get('input_cell_t_a'));case=basecase(cid,profile,feed)
    case['reference_feed_unit']='t_powder' if profile.startswith('LS') else 't_cell'
    # Unknown purchase, capital, products and fixed costs cannot be inferred by allocating park budgets.
    case['cost_items']=[row('profile_feed_purchase','feedstock',feed,None,case['reference_feed_unit'],'C:no_matched_price','A:'+profile)]
    case['cost_items'].extend(row(name,cat,None,None,'annual_CNY','C:unallocated_or_missing','A:'+profile)
      for name,cat in [('profile_transport','transport'),('profile_labor','labor'),('profile_maintenance','maintenance'),('profile_treatment','pollution_control'),('profile_fees','taxes_fees')])
    for r in annual:
        item=r['item_id'];q=r['quantity_per_year'];pid=None;price=None;category='reagents';unit=r['unit'].removesuffix('/a')
        if r.get('role')=='reagent_input':
            if item=='LS_ACID':pid='RG-01';price=p[pid]
            case['cost_items'].append(row(item,category,q,price,unit,'C:'+str(pid) if pid else 'C:missing_matching_commercial_spec_price',r['source_id']+':'+item,commercial_concentration=r.get('commercial_concentration')))
        elif profile.startswith('ANL'):
            if item=='electricity':
                case['cost_items'].append(row('profile_grid_power','utilities',q*(1-green),p['UT-01'],'kWh','C:UT01',r['source_id']+':'+item))
                case['cost_items'].append(row('profile_green_power','utilities',q*green,p['UT-02'],'kWh','C:UT02',r['source_id']+':'+item));continue
            category='utilities' if item in ['natural_gas_energy','diesel_energy','water'] else 'reagents'
            case['cost_items'].append(row(item,category,q,None,unit,'C:missing_matching_unit_or_concentration',r['source_id']+':'+item))
        elif item in ['LS23_PURE_WATER','LS23_SCRUBBER_MAKEUP','LS23_FLOOR_WATER','LS23_STEAM']:
            # Pure water not priced as tap water; steam mass not priced per MJ.
            case['cost_items'].append(row(item,'utilities',q,None,unit,'C:missing_matching_spec_or_heat_state',r['source_id']+':'+item))
    case['revenue_items']=[row('final_battery_grade_LCE',None,None,p['PR-01'],'t_battery_grade_LCE','C:PR01','A:final_quality_yield_missing',sale=True)]
    case['green_ratio']=green
    if profile.startswith('LS'):
        case['cost_items'].append(row('single_wet_stage_electricity','utilities',None,p['UT-01'],'kWh','C:UT01','A:M08_ELECTRIC_NOT_COMBINED_FACILITY'))
    return case

def policy_results(s):
    op=s['operating_case'];outputs=[]
    for year in [2026,2030,2035]:
        for profile in ['coursework','verified_current']:
            case=dict(case_id=f'PARK_ANNUAL_{year}_{profile}',evaluation_date=f'{year}-12-31',route='smelting',
              metals_present=['Li','Ni','Co','Mn','Cu','Al'],eu_material_recovery_scope=False,eu_new_battery_scope=False,
              produces_lithium_carbonate=True,metrics={'recycling_capacity_t_per_year':op['design_recycling_capacity_t_a']})
            result=evaluate_policy(case,profile=profile)
            outputs.append(dict(year=year,result=result,input=case,reuse=evaluate_reuse_application(dict(evaluation_date=f'{year}-12-31',has_reuse_branch=True))))
    return outputs

def main():
    DATA.mkdir(parents=True,exist_ok=True);REPORT.mkdir(parents=True,exist_ok=True);DELIVERY.mkdir(parents=True,exist_ok=True)
    before=source_hashes()
    if not SOURCE.exists():
        shutil.copy2(RAW/'A_给BC的补充数据.json',SOURCE)
    s=load_supplement();p=prices();cfg=read(ROOT/'data_cohort/final_integration_20261103/C_final_assumptions.json')
    dump(DATA/'A_C_annual_run_config.json',dict(source=SOURCE.name,case_id='PARK_ANNUAL_20261103',
      active_plant_route=None,independent_reference_profiles=['LS23_LFP_NATIVE_POWDER','ANL19_GENERIC_HYD_CELL'],
      full_plant_formal_calculation_enabled=False,budget_assumptions=cfg,
      notes=['财务产量3000不进入新年度清单','不借ND总kgce反推电耗','不同参考工艺不加总成全厂']))
    op=s['operating_case'];mass=mechanical_rows(s)
    assert abs(sum(r['received_pack_t_a'] for r in mass)-op['actual_received_pack_t_a'])<1e-6
    assert abs(op['actual_received_pack_t_a']-op['conditional_reuse_allocated_pack_t_a']-op['actual_recycling_inlet_pack_t_a'])<1e-6
    csvout(DATA/'annual_common_mass_inventory.csv',mass)
    lfp=next(r for r in mass if r['chemistry']=='LFP');nmc=next(r for r in mass if r['chemistry']!='LFP')
    ls=ls_annual(s,lfp['captured_blackmass_reference_t_a']);anl=anl_annual(s,nmc['cell_t_a'])
    csvout(DATA/'LS_independent_wet_annual_inventory.csv',ls);csvout(DATA/'ANL_independent_cell_annual_inventory.csv',anl)
    dump(DATA/'reference_profiles_original.json',s['reference_routes'])
    park=park_case(s,p,cfg);cases=[park,profile_case(ls,p),profile_case(anl,p)];results=[evaluate_annual_case(c) for c in cases]
    dump(DATA/'annual_tea_cases.json',cases);dump(REPORT/'annual_tea_results.json',results)
    costrows=[]
    for case in cases:
        evaluated=evaluate_annual_case(case)
        for row_ in case['cost_items']:
            costrows.append(dict(case_id=case['case_id'],profile_id=case['profile_id'],**row_,
              priced_annual_CNY=evaluated['priced_cost_items'].get(row_['name']),
              status='PRICED_BUDGET_NOT_FULL_COST' if row_['name'] in evaluated['priced_cost_items'] else 'MISSING_QUANTITY_OR_MATCHED_PRICE'))
    csvout(DATA/'annual_cost_mapping_and_gaps.csv',costrows)
    # Equivalent-active-content prices are transparently separated sensitivities, not purchases.
    proxy=[]
    for r in ls:
        if r['item_id'] in ['LS_NAOH','LS_CAO']:
            pid,quote_purity=('RG-03',.99) if r['item_id']=='LS_NAOH' else ('RG-05',.9)
            proxy.append(dict(item_id=r['item_id'],annual_commercial_t=r['quantity_per_year'],
              source_concentration=r['commercial_concentration'],quote_param=pid,assumed_quote_concentration=quote_purity,
              proxy_unit_price_CNY_t=p[pid]*r['commercial_concentration']/quote_purity,
              proxy_annual_CNY=r['active_equivalent_t_a']/quote_purity*p[pid],
              included_in_priced_subtotal=False,status='ACTIVE_EQUIVALENT_PRICE_ASSUMPTION_NOT_COMMERCIAL_QUOTE'))
    csvout(DATA/'concentration_price_proxy_separate.csv',proxy)
    sensitivities=[];mech=s['mechanical_capture_screening']
    captures=[('EV_I',mech['reference_capture_fraction']),('EV_I_minus_SD',max(0,mech['reference_capture_fraction']-mech['reference_sd_fraction'])),
      ('EV_I_plus_SD',min(1,mech['reference_capture_fraction']+mech['reference_sd_fraction'])),('EV_II',mech['alternative_route']['capture_fraction'])]
    for tag,capture in captures:
        for acid in ['total','alternate']:
            annual=ls_annual(s,lfp['blackmass_component_inventory_t_a']*capture,acid,'LS_REF_'+tag+'_'+acid)
            by={r['item_id']:r for r in annual};c=profile_case(annual,p);e=evaluate_annual_case(c)
            sensitivities.append(dict(case_id=c['case_id'],profile_id=c['profile_id'],capture_scenario=tag,blackmass_capture_fraction=capture,
              acid_version=acid,input_powder_scale_t_a=annual[0]['input_powder_t_a'],
              crude_Li2CO3_wet_t_a=by['LS23_PRODUCT_CRUDE_LIC']['quantity_per_year'],
              crude_Li2CO3_dry_pure_t_a=by['LS23_PRODUCT_CRUDE_LIC']['dry_pure_substance_t_a'],
              acid98_commercial_t_a=by['LS_ACID']['quantity_per_year'],priced_acid_budget_CNY_a=e['known_priced_opex_subtotal_CNY_a'],
              full_LCOR=None,formal_result_eligible=False,status='INDEPENDENT_LS_SCALE_SENSITIVITY_NOT_PLANT'))
    for g in [i/10 for i in range(11)]:
        c=profile_case(anl,p,g);c['case_id']='ANL_REF_GR_'+str(g);e=evaluate_annual_case(c)
        sensitivities.append(dict(case_id=c['case_id'],profile_id=c['profile_id'],green_ratio=g,
          electricity_kwh_a=next(r['quantity_per_year'] for r in anl if r['item_id']=='electricity'),
          priced_power_budget_CNY_a=e['known_priced_opex_subtotal_CNY_a'],full_LCOR=None,formal_result_eligible=False,
          status='INDEPENDENT_ANL_POWER_PRICE_SENSITIVITY_NOT_PLANT'))
    csvout(DATA/'profile_separated_sensitivities.csv',sensitivities)
    policies=policy_results(s);dump(REPORT/'policy_rerun_results.json',policies)
    csvout(REPORT/'policy_checks.csv',[dict(case_id=r['result']['case_id'],evaluation_year=r['year'],profile=r['result']['profile'],overall_status=r['result']['status'],**check) for r in policies for check in r['result']['checks']])
    gaps=copy.deepcopy(s['unresolved_inputs'])
    gaps.extend([dict(input_id='C_PRICE_SPEC',value=None,missing='铁粉/磷酸/氧气/CO2/32%液碱等匹配报价；残渣分类及单位；商品浓度；不以近似报价冒充实价',owner='C'),
      dict(input_id='BC_PRODUCT_BASKET',value=None,missing='全路线产品篮子/功能单位、年度量映射与环境因子浓度口径',owner='B+C')])
    dump(DATA/'remaining_input_contract.json',gaps)
    packet=DELIVERY/'给B_年度接口v2';packet.mkdir(exist_ok=True)
    dump(packet/'C_to_B_annual_bundle_v2.json',dict(schema_version='2.0.0',case_id=park['case_id'],
      operating_case=op,annual_common_inventory=mass,annual_tea_cases=cases,annual_tea_results=results,
      physical_profiles={'LS_reference':ls,'ANL_reference':anl},profile_separated_sensitivities=sensitivities,
      policy_results=policies,formal_LCOR=None,formal_result_eligible=False,
      supersedes_for_current_input='旧包q=3000的297条partial LCOR不适用于本轮新年度清单；旧包作为历史财务演示保留',remaining_inputs=gaps))
    # Preserve B's received case IDs and parameters but never invent a per-route LCE denominator.
    bpath=ROOT.parent/'lecture12-lib-recycling-B/lecture12-lib-recycling-B/data_cohort/scenario_results.csv'
    bmap=[]
    if bpath.exists():
        with bpath.open(encoding='utf-8-sig') as f:
            for r in csv.DictReader(f):
                bmap.append(dict(**{k:r[k] for k in ['case_id','process_mix','green_ratio','grid_ef','lithium_price_usd','energy_efficiency']},
                  annual_case_id=park['case_id'],lcor_rmb_per_t_LCE=None,c_tea_status='NOT_READY_ANNUAL_V2',
                  c_policy_status='UNKNOWN',formal_result_eligible=False,reason='缺本工况完整产品分母、全边界活动量和工艺产品篮子'))
    dump(packet/'C_to_B_existing_case_status_v2.json',bmap)
    for name in ['annual_tea_interface.py','tea_model.py','policy_engine.py','reuse_policy_2026.py']:
        shutil.copy2(ROOT/'code_implementation'/name,packet/name)
    shutil.copy2(ROOT/'data_cohort/policy_parameters.json',packet/'policy_parameters.json')
    dump(packet/'annual_case_input.json',park)
    (packet/'run_annual_case.py').write_text("import json\nfrom pathlib import Path\nfrom annual_tea_interface import evaluate_annual_case\np=Path(__file__).resolve().parent\ncase=json.loads((p/'annual_case_input.json').read_text(encoding='utf-8'))\nprint(json.dumps(evaluate_annual_case(case),ensure_ascii=False,indent=2))\n",encoding='utf-8')
    # Keep an inspectable no-zero-fill mapping of legacy C quantity template.
    with (ROOT/'data_cohort/tea_annual_quantities.csv').open(encoding='utf-8-sig') as f:legacy=list(csv.DictReader(f))
    for r in legacy:
        r['quantity_per_year']='';r['quantity_source']='A20261103:whole_plant_quantity_not_complete'
        if r['name']=='labor':r.update(quantity_per_year=cfg['workforce_person_year'],quantity_source='C_explicit_budget_not_A_staffing')
        if r['name']=='maintenance':r.update(quantity_per_year=park['capex']*cfg['maintenance_fraction_of_selected_capex'],quantity_source='C_selected_capex_budget')
        if r['name']=='other_taxes_fees':r.update(quantity_per_year=cfg['other_fees_CNY_a'],quantity_source='C_explicit_budget')
    csvout(DATA/'tea_annual_quantities_whole_plant_v2.csv',legacy)
    after=source_hashes();assert before==after
    dump(REPORT/'source_manifest.json',dict(before=before,after=after,source_files_unchanged=True))
    lsby={r['item_id']:r for r in ls};anlby={r['item_id']:r for r in anl}
    summary=dict(status='ANNUAL_INVENTORY_V2_COMPLETE_FOR_AVAILABLE_INPUTS_NOT_FORMAL_PLANT_LCOR',
      source_dataset=s['metadata']['dataset_id'],operating_case=op,
      captured_blackmass_reference_t_a=sum(r['captured_blackmass_reference_t_a'] for r in mass),
      LS_reference_input_powder_t_a=lfp['captured_blackmass_reference_t_a'],
      LS_crude_Li2CO3_wet_t_a=lsby['LS23_PRODUCT_CRUDE_LIC']['quantity_per_year'],
      LS_crude_Li2CO3_dry_pure_t_a=lsby['LS23_PRODUCT_CRUDE_LIC']['dry_pure_substance_t_a'],
      LS_FePO4_wet_t_a=lsby['LS23_PRODUCT_FEP_SLAG']['quantity_per_year'],
      LS_FePO4_dry_pure_t_a=lsby['LS23_PRODUCT_FEP_SLAG']['dry_pure_substance_t_a'],
      LS_acid98_commercial_t_a=lsby['LS_ACID']['quantity_per_year'],LS_naoh32_commercial_t_a=lsby['LS_NAOH']['quantity_per_year'],
      LS_steam_mass_t_a=lsby['LS23_STEAM']['quantity_per_year'],LS_steam_energy_MJ_a=None,LS_pure_water_m3_a=lsby['LS23_PURE_WATER']['quantity_per_year'],
      ANL_cell_input_t_a=nmc['cell_t_a'],ANL_electricity_kwh_a=anlby['electricity']['quantity_per_year'],
      ANL_natural_gas_MJ_a=anlby['natural_gas_energy']['quantity_per_year'],ANL_water_reference_m3_a=anlby['water']['quantity_per_year'],
      park_priced_opex_subtotal_CNY_a=results[0]['known_priced_opex_subtotal_CNY_a'],park_capital_annuity_CNY_a=results[0]['annualized_capex_CNY_a'],
      profile_sensitivity_count=len(sensitivities),B_existing_case_status_count=len(bmap),
      policy_statuses=[r['result']['status'] for r in policies],final_LCE_sale_t_a=None,
      formal_LCOR=None,formal_profit=None,MAC=None,formal_result_eligible=False,source_files_unchanged=True)
    dump(REPORT/'summary.json',summary);dump(DATA/'summary.json',summary)
    dump(ROOT/'report/latest_member_c.json',dict(latest_report='report/a_update_20261103',latest_data='data_cohort/a_update_20261103',
      latest_delivery=str(DELIVERY),formal_LCOR_ready=False,status=summary['status']))
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
