"""C v2 annual-inventory interface: no q_LCE * placeholder generation.
Missing quantities/prices are not zero; intermediate streams are not sales.
AI-assisted; complete planning inputs and independent review remain distinct.
"""
import math
from tea_model import evaluate_tea,capital_recovery_factor

def valid(value,positive=False):
    return not isinstance(value,bool) and isinstance(value,(int,float)) and math.isfinite(value) and (value>0 if positive else value>=0)

def evaluate_annual_case(case):
    """Return partial cost coverage and explicit readiness; call TEA only when complete.

    Every row's unit is the quantity unit AND the price denominator unit. No
    implicit concentration, mass/volume, heat/steam or currency conversions.
    Complete synthetic tests can exercise the same engine but are never formal.
    """
    missing=[];costs={};revenues={};seen=set()
    if not case.get('case_id'):raise ValueError('case_id required')
    for field in ['functional_unit','boundary_id','currency','price_year','data_status']:
        if not case.get(field):missing.append(field)
    if not valid(case.get('feed_t_per_year'),True):missing.append('feed_t_per_year')
    if not valid(case.get('fu_per_year'),True):missing.append('fu_per_year')
    if not valid(case.get('capex')):missing.append('capex')
    try:crf=capital_recovery_factor(case.get('discount_rate'),case.get('operating_years'))
    except (ValueError,TypeError):crf=None;missing.append('discount_rate_or_years')
    required={'feedstock','transport','utilities','reagents','labor','maintenance','pollution_control','taxes_fees'}
    required-=set(r.get('category') for r in case.get('cost_items',[]))
    missing.extend('cost_category:'+x for x in sorted(required))
    for section,target in [('cost_items',costs),('revenue_items',revenues)]:
        rows=case.get(section)
        if not isinstance(rows,list):raise ValueError(section+' must be a list')
        for row in rows:
            name=row.get('name')
            if not name or name in seen:raise ValueError('duplicate or absent row name')
            seen.add(name);key=section+'.'+name
            for field in ['quantity_per_year','unit_price']:
                if not valid(row.get(field)):missing.append(key+'.'+field)
            for field in ['unit','source_id','quantity_source_id']:
                if not row.get(field):missing.append(key+'.'+field)
            if row.get('price_unit')!=row.get('unit'):missing.append(key+'.price_unit_mismatch')
            if row.get('currency')!=case.get('currency') or row.get('price_year')!=case.get('price_year'):
                missing.append(key+'.price_basis_mismatch')
            if section=='revenue_items' and row.get('sale_status')!='saleable_confirmed_for_case':
                missing.append(key+'.saleability_unconfirmed')
            if not any(x.startswith(key+'.') for x in missing):target[name]=row['quantity_per_year']*row['unit_price']
    gates=['whole_boundary_activities_complete','saleable_product_quantities_complete','profile_compatibility_confirmed']
    for gate in gates:
        if case.get(gate) is not True:missing.append(gate)
    if not case.get('revenue_items'):missing.append('revenue_items.empty_not_confirmed_no_sales')
    annual_cap=case['capex']*crf if valid(case.get('capex')) and crf is not None else None
    result=dict(case_id=case['case_id'],profile_id=case.get('profile_id'),boundary_id=case.get('boundary_id'),
      status='NOT_READY' if missing else 'CALCULATED',missing_fields=sorted(set(missing)),
      known_priced_opex_subtotal_CNY_a=sum(costs.values()),priced_cost_items=costs,
      known_confirmed_revenue_subtotal_CNY_a=sum(revenues.values()),priced_revenue_items=revenues,
      annualized_capex_CNY_a=annual_cap,total_opex_CNY_a=None,annual_revenue_CNY_a=None,
      annual_net_cost_CNY_a=None,lcor_CNY_per_t_LCE=None,annual_net_profit_CNY=None,
      formal_result_eligible=False,MAC_CNY_tCO2=None,
      warning='已定价部分小计不是完整OPEX/利润；未定价项不为零。不同profile结果不得相加。')
    if not missing:
        tea=evaluate_tea(case)
        result.update(total_opex_CNY_a=tea['opex_per_year'],annual_revenue_CNY_a=tea['revenue_per_year'],
          annual_net_cost_CNY_a=tea['base_net_cost_per_year'],lcor_CNY_per_t_LCE=tea['base_lcor_per_fu'],
          annual_net_profit_CNY=-tea['base_net_cost_per_year'],tea=tea)
        result['formal_result_eligible']=case.get('data_status')=='confirmed_planning_case'
    return result
