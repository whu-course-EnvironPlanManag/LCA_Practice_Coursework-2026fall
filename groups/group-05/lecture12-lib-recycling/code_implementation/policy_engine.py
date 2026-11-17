"""AI辅助。Prompt：按实际适用工艺/日期判断课程硬约束，边界等号和未知值必须测试。
人工校验状态：待组员人工确认；自动测试见 test_models.py。
"""
from pathlib import Path
import json, math
from datetime import date
P=json.loads((Path(__file__).resolve().parents[1]/'data_cohort/policy_parameters.json').read_text())

def threshold_for(schedule, when, default=0):
    when=str(when)
    vals=[(k,v) for k,v in schedule.items() if k<=when]
    return sorted(vals)[-1][1] if vals else default

def assess(case, when='2030-12-31', export=False):
    """只判断量化规划筛选。未知数据=UNKNOWN，不能据此声称取得企业/地块许可。"""
    g=P['cn_guidance']; c=P['course_additional_targets'];checks={}
    def check(key,op,val):
        x=case.get(key)
        if x is None or not isinstance(x,(int,float)) or not math.isfinite(x):checks[key]='UNKNOWN'
        elif x<0 or (key not in ['energy_kgce_tLCE','capacity_tpa'] and x>1):checks[key]='FAIL'
        else:checks[key]='PASS' if op(x,val) else 'FAIL'
    ge=lambda x,y:x>=y;lt=lambda x,y:x<y
    for k,v in [('powder',g['powder_min']),('water_recycle',g['water_recycle_min']),('capacity_tpa',g['recycling_capacity_principle_min_tpa']),('rd_fraction',g['rd_min_fraction']),('F',c['F_fixation_min']),('Cu',c['Cu_min']),('Al',c['Al_min'])]: check(k,ge,v)
    for k in ['Al_impurity','Cu_impurity']:check(k,lt,g[k.split('_')[0]+'_impurity_strict_max'])
    if case.get('has_smelting',True):
        for k in ['Li','Ni','Co','Mn']:check(k,ge,g['li_smelting_min'] if k=='Li' else g[k+'_min'])
        check('energy_kgce_tLCE',lt,g['energy_kgce_tLCE_strict_max'])
    if case.get('has_repair',False):check('repair_material',ge,g['repair_material_min'])
    if case.get('reuse_application')=='electric_bicycle':checks['prohibited_application']='FAIL'
    if export:
        check('EU_Li_recovery',ge,threshold_for(P['eu']['lithium_recovery'],when))
        for k in ['Co','Cu','Ni']:
            check('EU_'+k+'_recovery',ge,threshold_for(P['eu']['other_material_recovery'],when))
        content=threshold_for(P['eu']['recycled_content'],when,{})
        for k,v in content.items():
            if k in case.get('active_elements',['Li','Ni','Co']):check('content_'+k,ge,v)
        # 任何未知最大碳阈值/电池护照资料都不能判定为出口合规。
        checks['export_gwp_threshold']='UNKNOWN' if P['eu']['gwp_threshold_kgCO2e_kWh'] is None else 'PASS'
        if str(when)>=P['eu']['passport_date']:checks['passport']='PASS' if case.get('passport_verified') is True else 'UNKNOWN'
    status='FAIL' if 'FAIL' in checks.values() else 'UNKNOWN' if 'UNKNOWN' in checks.values() else 'PASS'
    return dict(status=status,checks=checks,scope='numeric_planning_screen_only')

def pollutant_tax(records,air_rate=1.8,water_rate=2.8):
    """按排口/类别将kg转污染当量。标准税额、不含未提供证据的减免或VOCs试点规则。
    records需给medium、outlet、category(first/other)、mass_kg、equivalent_kg。
    无实际排放记录时不调用此函数推断实际税额为零。
    """
    from collections import defaultdict
    grouped=defaultdict(list)
    for r in records:
        medium=r['medium'];assert medium in ['air','water']
        mass=float(r['mass_kg']);equivalent=float(r['equivalent_kg'])
        if not math.isfinite(mass) or not math.isfinite(equivalent) or mass<0 or equivalent<=0:raise ValueError('invalid pollutant mass/equivalent')
        category=r.get('category','other') if medium=='water' else 'air'
        if medium=='water' and category not in ['first','other']:raise ValueError('unknown water pollutant category')
        grouped[medium,r['outlet'],category].append(mass/equivalent)
    tax=0.;charged={}
    for (medium,outlet,category),vals in grouped.items():
        count=3 if medium=='air' or category=='other' else 5
        equivalents=sum(sorted(vals,reverse=True)[:count]);tax+=equivalents*(air_rate if medium=='air' else water_rate)
        charged[f'{medium}:{outlet}:{category}']=equivalents
    return dict(tax_CNY=tax,charged_equivalents=charged,scope='standard_tax_no_unverified_exemptions')

def fiscal_adjustment(*,avoided_tCO2,price,ccer_eligible=False,ets_covered=False,air_equivalents=0,water_equivalents=0,air_rate=1.8,water_rate=2.8,surface_m3=0,surface_rate=.2,water_source='municipal',subsidy=0,export_premium=0,export_verified=False):
    carbon=max(avoided_tCO2,0)*price if ccer_eligible else 0
    penalty=max(-avoided_tCO2,0)*price if ets_covered else 0
    taxes=air_equivalents*air_rate+water_equivalents*water_rate+(surface_m3*surface_rate if water_source=='direct_surface' else 0)
    premium=export_premium if export_verified else 0
    return dict(carbon_credit=carbon,carbon_penalty=penalty,environment_water_tax=taxes,export_premium=premium,subsidy=subsidy,net_support=carbon+premium+subsidy-penalty-taxes)
