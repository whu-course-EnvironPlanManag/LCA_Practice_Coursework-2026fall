"""AI-assisted economic intake, source trace and annual-quantity handoff.
Received prices remain planning assumptions until evidence and accounting bases are checked.
No missing quantity is replaced by zero. Original workbook is read only.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from pathlib import Path

from tea_model import capital_recovery_factor, evaluate_tea
from handoff_analysis import completion_check

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data_cohort'
OUT = ROOT / 'report/economic_intake_20261103'
AUDIT = ROOT / 'report/review_20261103/quote_audit.json'
ORIGINAL = ROOT.parent / 'economic_parameters.xlsx'
REVISED = DATA / 'economic_parameters_revised_20261103.csv'
SOURCE = REVISED if REVISED.exists() else ORIGINAL
QPATH = DATA / 'tea_annual_quantities.csv'
CONFIG = DATA / 'tea_accounting_assumptions.json'

# Annual quantities must match the exact purchased/sold basis of each price.
SPECS = [
 ('grid_electricity','utilities','UT-01','kWh','A','网电年购入量；与绿电分开'),
 ('green_electricity','utilities','UT-02','kWh','A+B','绿电年购入量；交付电量与自发电边界分开'),
 ('steam','utilities','UT-03','MJ','A','购买蒸汽热量；不直接套天然气MJ'),
 ('freshwater','utilities','UT-04','m3','A','外购新水；不将回用水重复计费'),
 ('sulfuric_acid_98pct','reagents','RG-01','t_solution','A','98%硫酸商品质量；纯酸量除以0.98'),
 ('hydrogen_peroxide_27_5pct','reagents','RG-02','t_solution','A','27.5%双氧水商品质量；纯H2O2量除以0.275'),
 ('sodium_hydroxide','reagents','RG-03','t_commercial_product','A','片碱商品质量；确认报价纯度'),
 ('sodium_carbonate','reagents','RG-04','t_commercial_product','A','纯碱商品质量'),
 ('lime','reagents','RG-05','t_commercial_product','A','石灰商品质量；与治理包价核对'),
 ('labor','labor','LB-01','person_year','A+C','全年等效人数；8.5万元/人年'),
 ('hazardous_residue','pollution_control','WS-01','t_waste','A','实际废物类别与接收报价匹配；不能仅凭表格认定HW49'),
 ('LCE_product','revenue','PR-01','t_battery_grade_LCE','A','实际可售电池级碳酸锂量，不是理论锂当量总量'),
 ('iron_phosphate','revenue','PR-02','t_sale_product','A','品级合格的磷酸铁销量'),
 ('nmc_mixed_sulfate','revenue','PR-03','t_sale_product','A','核对干基/溶液浓度及金属含量，不能按金属吨直接套价'),
 ('copper','revenue','PR-04','t_sale_product','A','商品铜品级与售价匹配'),
 ('aluminum','revenue','PR-05','t_sale_product','A','商品铝品级与售价匹配'),
 ('reuse_modules','revenue','PR-06','kWh_sale_capacity','A','可售模块容量kWh；不将吨数乘元/kWh'),
 ('maintenance','maintenance',None,'annual_budget_CNY','A+C','年维修总预算，不含折旧及资本年金'),
 ('other_pollution_control','pollution_control',None,'annual_budget_CNY','A+C','除已计电热药剂危废外的治理费用，防止重复'),
 ('other_taxes_fees','taxes_fees',None,'annual_budget_CNY','C','本税前模型的其他适用费用；不含所得税，不叠加增值税税率'),
 ('other_costs','other',None,'annual_budget_CNY','A+C','保险、质检、包装、补锂等未列费用；确认为零须写依据'),
 ('repair_product','revenue',None,'annual_revenue_CNY','A+B+C','直接修复产品单列年度销售额；不用碳酸锂价格替代'),
]


def write_csv(path, rows, fields=None):
    rows = list(rows)
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields or list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def read_prices(source=SOURCE):
    expected = ('param_id','category','name','unit','value','source','note')
    if source.suffix.lower()=='.csv':
        with source.open(encoding='utf-8-sig',newline='') as f:
            reader=csv.DictReader(f)
            if not set(expected)<=set(reader.fieldnames or []):raise ValueError('经济CSV缺少必要列')
            records=[dict(r) for r in reader if r.get('param_id')]
        for r in records:r['value']=float(r['value'])
    else:
        import openpyxl
        wb = openpyxl.load_workbook(source, data_only=True, read_only=True)
        rows = list(wb['economic_parameters'].values)
        if tuple(rows[0]) != expected:raise ValueError('经济参数表列名变化，请核对映射')
        records = [dict(zip(expected,r)) for r in rows[1:] if r[0]]
        wb.close()
    ids = [r['param_id'] for r in records]
    if len(set(ids)) != len(ids): raise ValueError('重复param_id')
    for r in records:
        v = r['value']
        if isinstance(v,bool) or not isinstance(v,(float,int)) or not math.isfinite(v) or v < 0:
            raise ValueError(f"非法经济数值: {r['param_id']}")
        r['status'] = 'received_unverified_planning_assumption'
        r.setdefault('tax_basis','未明确')
        r['source_file'] = source.name
        r['source_locator'] = (f"CSV数据行{ids.index(r['param_id'])+2}" if source.suffix.lower()=='.csv'
                               else f"economic_parameters!E{ids.index(r['param_id'])+2}")
        factor = 10000 if r['unit'] == '万元' else .01 if r['unit'] == '%' else 1
        r['normalized_value'] = v * factor
        r['normalized_unit'] = 'CNY' if r['unit'] == '万元' else 'fraction' if r['unit'] == '%' else r['unit']
        tax=re.fullmatch(r'含税(\d+(?:\.\d+)?)%',r['tax_basis'])
        r['received_vat_rate']=float(tax.group(1))/100 if tax else None
        r['model_treatment']='收到报价；税率适用和进项可抵扣资格仍待证据'
        r['ex_vat_planning_value']=r['normalized_value']/(1+r['received_vat_rate']) if tax else r['normalized_value']
        if r['param_id']=='LB-01':
            r['ex_vat_planning_value']=r['normalized_value']
            r['model_treatment']='自有员工薪酬预算保持原额，不征增值税；原表含税6%不适用于该工资口径，若外包则另建服务项目'
    if AUDIT.exists():
        audit=json.loads(AUDIT.read_text(encoding='utf-8'))['per_parameter']
        for r in records:
            item=audit.get(r['param_id'],{})
            r['source_review_status']=item.get('review_status','尚未复核')
            r['claimed_quote_period']=item.get('claimed_period','')
            r['exact_quote_date']=item.get('exact_quote_date','')
            r['applicability_review']=item.get('application_conditions','')
            r['original_quote_received']=item.get('original_quote_received',False)
    return records


def load_quantities(path=QPATH):
    with path.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
    result={}
    for row in rows:
        name=row['name']
        if name in result: raise ValueError(f'重复年度数量: {name}')
        value=row['quantity_per_year'].strip()
        if value:
            value=float(value)
            if not math.isfinite(value) or value < 0: raise ValueError(f'非法年度数量: {name}')
            if not row['quantity_source'].strip(): raise ValueError(f'{name}: 已填数量须注明来源，零值也需要依据')
        else: value=None
        result[name]={**row,'quantity_per_year':value}
    expected={s[0]:s[3] for s in SPECS}
    if set(result)!=set(expected): raise ValueError('年度数量项目缺失或新增，请先更新SPECS映射')
    for name,unit in expected.items():
        if result[name]['unit']!=unit: raise ValueError(f'{name}: 单位必须为{unit}；不得隐式换算')
    return result


def build_case(prices, config, quantities):
    basis=config.get('valuation_basis','quoted_cash_amounts')
    if basis not in ['quoted_cash_amounts','ex_vat_planning_assumption']:raise ValueError('未知计价口径')
    p={r['param_id']:(r['ex_vat_planning_value'] if basis=='ex_vat_planning_assumption' else r['normalized_value']) for r in prices}
    load=config['load_factor']
    if not isinstance(load,(int,float)) or isinstance(load,bool) or not math.isfinite(load) or not 0<load<=1:
        raise ValueError('load_factor须为0至1内正数')
    included=config['included_capex_ids']
    if len(set(included))!=len(included) or any(x not in {f'CAP-{i:02}' for i in range(1,9)} for x in included):
        raise ValueError('投资只能选择CAP-01至CAP-08且不能重复，CAP-09为控制合计')
    capex=sum(p[x] for x in included)
    feed=80000*load
    case=dict(case_id='YCH_2026_PROVISIONAL_ECONOMIC_INTAKE',data_status='pending_quantities_and_basis',
      currency='CNY',price_year=int(p['PRC-01']),functional_unit='t_battery_grade_LCE_product',
      feed_t_per_year=feed,fu_per_year=quantities['LCE_product']['quantity_per_year'],
      capex=capex,discount_rate=p['FIN-02'],operating_years=int(p['FIN-01']),
      cost_items=[],revenue_items=[],scenario_adjustments=[],
      accounting_note=f'Valuation basis: {basis}. Ex-VAT uses received rates and assumes recoverable input VAT, pending applicability evidence. Own-employee wages are not deflated. Provisional 85% load does not alter design capacities.',
      boundary_id=None)
    # Procurement is a weighted receipt-book assumption, not a verified delivered-price contract.
    case['cost_items'].append(dict(name='feed_purchase',category='feedstock',quantity_per_year=feed,
      unit_price=p['FS-03'],unit='t_feed_pack',source_id='ECON_BOOK:FS-03'))
    case['cost_items'].append(dict(name='inbound_transport',category='transport',quantity_per_year=feed,
      unit_price=(p['TR-01'] if config['transport_additional_confirmed'] is True else 0.
                  if config['transport_additional_confirmed'] is False else None),
      unit='t_feed_pack',source_id='ECON_BOOK:TR-01; delivered-price overlap checked via config'))
    for name,category,pid,unit,owner,note in SPECS:
        q=quantities[name]
        row=dict(name=name,quantity_per_year=q['quantity_per_year'],unit_price=p[pid] if pid else 1.,
          unit=unit,source_id=f"ECON_BOOK:{pid}; {q['quantity_source']}" if pid else q['quantity_source'] or 'PENDING_ANNUAL_BUDGET',
          quantity_note=note)
        if category=='revenue': case['revenue_items'].append(row)
        else: row['category']=category;case['cost_items'].append(row)
    return case


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,default=SOURCE)
    args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    prices=read_prices(args.source)
    write_csv(DATA/'economic_parameters_received.csv',prices)
    p={r['param_id']:r['normalized_value'] for r in prices}
    # Update the old generic interface without erasing historical literature rows.
    legacy_path=DATA/'economic_parameters.csv'
    mapping={'capex':'CAP-09','discount_rate':'FIN-02','operating_years':'FIN-01',
      'feedstock_price':'FS-03','transport_price':'TR-01','electricity_price':'UT-01',
      'steam_price':'UT-03','water_price':'UT-04','waste_treatment_price':'WS-01',
      'product_price':'PR-01','fx_usd_cny':'EXCH-01'}
    with legacy_path.open(encoding='utf-8-sig',newline='') as f: legacy=list(csv.DictReader(f))
    units={'capex':'CNY','discount_rate':'fraction','operating_years':'year',
      'feedstock_price':'CNY/t_pack','transport_price':'CNY/t_pack_per_trip',
      'electricity_price':'CNY/kWh','steam_price':'CNY/MJ','water_price':'CNY/m3',
      'waste_treatment_price':'CNY/t_matching_residue','product_price':'CNY/t_battery_grade_LCE','fx_usd_cny':'CNY/USD'}
    for row in legacy:
        key=row['parameter_id']
        if key in mapping:
            pid=mapping[key];row.update(value=p[pid],unit=units[key],status='received_unverified_planning_assumption',
              source_or_next_action=f'ECON_BOOK:{pid}; 此为收到报价，税价模型值见economic_parameters_received.csv；完整来源见economic_source_register.csv')
        elif key=='reagents_price':row['source_or_next_action']='不得使用统一试剂价；分别采用economic_parameters_received.csv的RG-01至05'
    write_csv(legacy_path,legacy)
    if abs(sum(p[f'CAP-{i:02}'] for i in range(1,9))-p['CAP-09'])>.01: raise ValueError('投资合计与CAP-09不符')
    if abs(.6*p['FS-01']+.4*p['FS-02']-p['FS-03'])>.01: raise ValueError('加权采购价不符')
    if not QPATH.exists():
        write_csv(QPATH,[dict(name=s[0],quantity_per_year='',unit=s[3],quantity_source='',owner=s[4],note=s[5]) for s in SPECS])
    if not CONFIG.exists():
        CONFIG.write_text(json.dumps(dict(load_factor=p['FIN-03'],
          load_note='收到表的85%规划假设；设计能力8万吨、梯次能力1万吨保留，实际分流待A确认',
          included_capex_ids=[f'CAP-{i:02}' for i in range(1,9)],
          capex_route_confirmed=False,transport_additional_confirmed=None,
          quote_tax_basis_confirmed=False,discount_rate_real_confirmed=False,
          product_boundary_confirmed=False,chemical_basis_confirmed=False,
          load_and_split_confirmed=False,source_assumptions_reviewed=False),ensure_ascii=False,indent=2),encoding='utf-8')
    config=json.loads(CONFIG.read_text(encoding='utf-8-sig'))
    if args.source.suffix.lower()=='.csv':
        config.setdefault('valuation_basis','ex_vat_planning_assumption')
        config.setdefault('vat_recoverability_confirmed',False)
        config['discount_rate_real_confirmed']=True
        config['discount_rate_basis_note']='修改版FIN-02明确实际折现率；来源真实性仍单列待核'
        if '不再另计' in next(r for r in prices if r['param_id']=='FS-01')['note']:
            config['transport_additional_confirmed']=False
        config['quote_tax_basis_confirmed']=False
        config['tax_basis_note']='报价含税标记已收，仍存在工资、供水/供热、混合工程及服务的税目适用性疑点，不能视为税价核验完成。表列税率除税仅为压力假设；员工薪酬不除税。'
        CONFIG.write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
    case=build_case(prices,config,load_quantities())
    (DATA/'tea_case_economic_intake.json').write_text(json.dumps(case,ensure_ascii=False,indent=2),encoding='utf-8')
    missing=completion_check(case)
    review_fields=['capex_route_confirmed','transport_additional_confirmed','quote_tax_basis_confirmed',
      'discount_rate_real_confirmed','product_boundary_confirmed','chemical_basis_confirmed',
      'load_and_split_confirmed','source_assumptions_reviewed']
    if config.get('valuation_basis')=='ex_vat_planning_assumption':review_fields.append('vat_recoverability_confirmed')
    unresolved=[k for k in review_fields if not isinstance(config.get(k),bool) or
                (config.get(k) is False and k!='transport_additional_confirmed')]
    # False transport means no separate bill: record an explicit zero price and basis.
    if config.get('transport_additional_confirmed') is False:
        for r in case['cost_items']:
            if r['name']=='inbound_transport': r['unit_price']=0.;r['source_id']='ACCOUNTING:included_in_delivered_feed_price'
        (DATA/'tea_case_economic_intake.json').write_text(json.dumps(case,ensure_ascii=False,indent=2),encoding='utf-8')
        missing=completion_check(case)
    crf=capital_recovery_factor(p['FIN-02'],p['FIN-01'])
    summary=dict(status='PENDING' if missing or unresolved else 'ASSUMPTION_SCENARIO_READY',
      parameter_count=len(prices),source_sha256=hashlib.sha256(args.source.read_bytes()).hexdigest(),
      capex_sum_CNY=p['CAP-09'],capex_control_difference_CNY=0,
      weighted_feed_price_CNY_per_t=p['FS-03'],design_feed_t_per_year=80000,
      provisional_actual_feed_t_per_year=case['feed_t_per_year'],provisional_crf=crf,
      provisional_annual_capital_CNY=case['capex']*crf,
      model_capex_CNY=case['capex'],valuation_basis=config.get('valuation_basis','quoted_cash_amounts'),
      provisional_feed_purchase_CNY=case['cost_items'][0]['quantity_per_year']*case['cost_items'][0]['unit_price'],
      transport_CNY_if_additional=case['feed_t_per_year']*p['TR-01'],
      separate_inbound_transport_CNY=0 if config.get('transport_additional_confirmed') is False else None,
      missing_numeric_fields=missing,unresolved_accounting_reviews=unresolved,
      formal_lcor=None,formal_profit=None,
      original_quotations_verified=0 if AUDIT.exists() else None,
      source_review_report='report/review_20261103/报价原件日期适用条件核对.csv' if AUDIT.exists() else None,
      note='已收参数的算术控制与部分年度金额，非完整经济结果；修改版7%已明确实际折现率。计价口径及VAT抵扣假设单独标识，报价证据仍待核。')
    if not missing and not unresolved:
        case['data_status']='reviewed_planning_assumptions'
        summary['assumption_scenario_tea']=evaluate_tea(case)
    (OUT/'intake_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    write_csv(OUT/'remaining_inputs.csv',[
      dict(type='numeric',field=x,owner='A/C',status='missing') for x in missing]+[
      dict(type='accounting_basis',field=x,owner='A/B/C',status='pending_review') for x in unresolved])
    # Complete received-book provenance, without claiming online verification of quoted sources.
    write_csv(DATA/'economic_source_register.csv',[dict(source_id='ECON_BOOK:'+r['param_id'],
      locator=r['source_locator'],claimed_source=r['source'] or '',received_note=r['note'] or '',
      received_tax_basis=r['tax_basis'],model_treatment=r['model_treatment'],
      source_review_status=r.get('source_review_status','未复核'),
      claimed_quote_period=r.get('claimed_quote_period',''),exact_quote_date=r.get('exact_quote_date',''),
      applicability_review=r.get('applicability_review',''),
      verification='未取得原始报价/页码/链接；按收到的规划假设登记',
      action='补报价日期、含税口径、有效期、商品规格及可核读原件') for r in prices])
    caprows=[dict(param_id=f'CAP-{i:02}',name=next(r['name'] for r in prices if r['param_id']==f'CAP-{i:02}'),
      capex_quoted_CNY=p[f'CAP-{i:02}'],
      capex_ex_vat_assumption_CNY=next(r['ex_vat_planning_value'] for r in prices if r['param_id']==f'CAP-{i:02}'),
      included=f'CAP-{i:02}' in config['included_capex_ids']) for i in range(1,9)]
    write_csv(OUT/'chapter4_capex_handoff.csv',caprows)
    # Prepare explicit external price anchors; do not invent prices for coproducts or procurement transmission.
    write_csv(DATA/'tea_price_scenarios.csv',[dict(scenario=name,lce_price_CNY_per_t=usd*p['EXCH-01'],
      fx_CNY_per_USD=p['EXCH-01'],historical_literature_anchor_USD=usd,
      tax_basis='文献税价口径待核；只存外部压力锚点，不自动接入除税模型',
      status='literature_stress_assumption_not_observed_2026_price',
      procurement_pass_through='待补；不得将锂价上升默认为采购价不变')
      for name,usd in [('low',10000),('middle',22000),('high',50000)]])
    report=f'''# C经济参数接入结果（2026-11-03）

已接收并规范化{len(prices)}项参数，原Excel未修改。投资8项合计为{p['CAP-09']/1e8:.2f}亿元，与表内合计一致；采购加权价为{p['FS-03']:,.0f}元/吨，与60%/40%组成一致。

按收到表的85%负荷，暂定实际总进料{case['feed_t_per_year']:,.0f}吨/年；不改变8万吨设计及1万吨梯次能力，实际分流待A确认。当前模型口径为`{summary['valuation_basis']}`，模型资本额{case['capex']/1e4:,.2f}万元；按7%、20年，资本回收系数{crf:.6f}、年金{case['capex']*crf/1e4:,.2f}万元/年。采购金额暂算{summary['provisional_feed_purchase_CNY']/1e4:,.2f}万元/年。单独进厂运输记账为{summary['separate_inbound_transport_CNY']}元；若采购已含运输，不再加原3,400万元/年的整程报价。

## 已落实的核算规则

- CAP-09仅为控制合计，不与CAP-01至08重复相加。直接修复线、湿法线和绿电配套按路线复核后确定是否纳入。
- 资本年金之外不重复计折旧、融资利息。本模型为税前无杠杆稳态年金，不等同含建设期、残值和营运资金的NPV。
- 修改版FIN-02明确7%为实际折现率，与不变价匹配；收到表原注中的名义/实际利率关系写法应改为(1+名义)=(1+实际)×(1+通胀)。
- 修改版已补税价标记，规划情景按原列税率换算不含可抵扣VAT金额，实际税率与抵扣资格仍待核，不把该假设视为税务认证。员工工资8.5万元/人年原额保留，不按6%除税；外包服务另列。
- TX的13%、25%、30%只登记，不作为OPEX加成或已确认退税/所得税减免收入，原备注的优惠适用性未核。
- 运输500元/吨不再乘180公里；修改版明确采购到厂价已含运费，独立进厂运费为零，不再重复计入。货物分类按实际认定，报价名称不证明电池一律是危废。
- 双氧水按27.5%商品吨、硫酸按98%商品吨；蒸汽按MJ，不能直接使用天然气活动量；混合硫酸盐需浓度/干基，梯次产品按kWh计价。
- 电费使用网电0.62、绿电0.41的收到表假设，分列购电量；自有光储投资与直购电费须核对边界。无绿电可用量证据时不自动承诺100%。
- 产品不重复计算：修复材料、碳酸锂、混合盐及后续分离盐按实际外售环节入账；补锂药剂和修复收入均需单列。
- 年度预算/年度销售额项目填与模型一致的不含可抵扣VAT金额；原始票据口径及税额另保留，不把含税总额直接混入模型。
- 3档文献价格及7.2汇率是压力情景，不称为核实后的2026现货价。补贴、碳信用、溢价及退税不计入当前基准。

## 数据到达后的最短操作

1. 在`data_cohort/tea_annual_quantities.csv`填年数量与来源，确认为零也写依据，单位不得变更。
2. 在`tea_accounting_assumptions.json`记录路线投资、税价、实际折现率、分配、化学品及分流核对状态；运输是否另收费填true/false。
3. 运行`python code_implementation/prepare_economic_case.py`，程序列出所有剩余缺项；齐备后输出明确标识的规划假设TEA。
4. 将最终方案编号与B对应，完成完整成本收益图、价格影响图及政策判断。当前LCOR、利润和MAC继续留空。

当前缺少{len(missing)}个数值字段、{len(unresolved)}项核算口径；详见同目录JSON/CSV。不再沿用旧summary.json的22项缺失作为最新清单。当前报价外部证据仍未完整取得，所有税率转换仅为明确标识的规划假设。
'''
    (OUT/'C经济参数接入与费用口径说明.md').write_text(report,encoding='utf-8')
    if args.source.suffix.lower()=='.csv':
        old={r['param_id']:r for r in read_prices(ORIGINAL)}
        differences=[]
        for row in prices:
            for field in ['name','unit','value','tax_basis','source','note']:
                a=old.get(row['param_id'],{}).get(field,'')
                b=row.get(field,'')
                if str(a)!=str(b) and not(field=='value' and a==b):
                    differences.append(dict(param_id=row['param_id'],field=field,old_value=a,new_value=b))
        write_csv(OUT/'revised_vs_original.csv',differences)
    print(json.dumps({k:summary[k] for k in ['status','parameter_count','capex_sum_CNY','provisional_actual_feed_t_per_year','provisional_annual_capital_CNY']},ensure_ascii=False))
    print('Missing numeric fields:',len(missing),'Accounting reviews:',len(unresolved))


if __name__=='__main__':main()
