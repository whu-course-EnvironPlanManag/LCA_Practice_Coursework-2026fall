# -*- coding: utf-8 -*-
"""C侧 LCOR 交接计算：从A的JR23组成到园区净成本，输出基准值与B情景网格值。

用途
----
成员B的 ``c_interface.lcor_estimate`` 只读 ``tea_case_economic_intake.json``，
该文件所有 annual quantity 为空时返回 NaN，B因此无法生成帕累托前沿（fig_b4）。
本模块用A已交付的 JR23 包装/电芯/黑粉组成 + C已接入的38项经济参数，构造
一个有据可查的基准工况，并给出B的3267组工况对应的LCOR。

口径（必须与报告一致）
----------------------
* 边界：仅拆解再生线（不含量1万吨梯次线CAP-02及其收入），因为梯次是另一条
  产品线，其收入不能除以LCE产量。
* 负荷：设计8万吨/年 × 85% = 6.8万吨进厂；其中梯次1万吨×85%=0.85万吨，
  拆解再生5.95万吨。
* 功能单位：1 t 电池级LCE产品；LCOR = 净年成本 / 年LCE产量。
* 计价：2026年不变价人民币，不含可抵扣增值税（与
  ``tea_accounting_assumptions.json`` 的 ex_vat_planning_assumption 一致）。
* 多产品：磷酸铁、镍钴锰混合硫酸盐、铜、铝按实际可售量计入收入；不把修复
  材料重复计为碳酸锂。园区净额除以LCE产量是“按LCE归一化的园区净成本”，
  不等于单一碳酸锂产品分摊成本（见第5章5.1）。

来源
----
A的JR23组成：湖南金瑞2023环评表3.4-3/3.4-6/3.4-7（SRC039），经A交接包
``yichang_dmfa_dataset.json`` → ``legacy_park_handoff.payload.composition_profiles``。
C的价格：``data_cohort/economic_parameters_revised_20261103.csv``。
AI辅助生成；人工核验待成员C完成。所有假设单列于 ``ASSUMPTIONS``，不得把
本结果当作A实测物质流或已核报价的最终结论。
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data_cohort'
OUT = ROOT / 'report/lcor_handoff_20261103'
sys.path.insert(0, str(Path(__file__).resolve().parent))

from prepare_economic_case import read_prices  # noqa: E402
from tea_model import capital_recovery_factor, evaluate_tea  # noqa: E402

# ---------------------------------------------------------------------------
# A. 固定设计与组成（A/JR23；不是本园区实测）
# ---------------------------------------------------------------------------
DESIGN_FEED_T = 80_000.0
LOAD = 0.85
REUSE_CAPACITY_T = 10_000.0
CHEM = {'LFP': 0.60, 'NMC': 0.40}

# 包→电芯、电芯→黑粉（含胶黏剂）、黑粉元素品位
PACK = {
    'LFP': {
        'cell': 0.6627, 'powder_in_cell': 0.4268,
        'li': 0.03425, 'fe': 0.25344, 'al_foil_cell': 0.0572, 'cu_foil_cell': 0.16398,
        'current_collector': 0.08158, 'cu_wire': 0.01442,
    },
    'NMC': {
        'cell': 0.63466, 'powder_in_cell': 0.4378,
        'li': 0.04340, 'ni': 0.14857, 'co': 0.06770, 'mn': 0.10808,
        'al_foil_cell': 0.11440, 'cu_foil_cell': 0.13460,
        'current_collector': 0.07812, 'cu_wire': 0.01624,
    },
}
LI2CO3_LI_FRACTION = 0.18787          # 2*6.941 / (2*6.941+12.011+3*15.999)
FEPO4_FE_FRACTION = 0.3690            # 55.845 / 150.816
SULFATE_METAL_FRACTION = 0.22         # 混合硫酸盐中Ni+Co+Mn质量分数（假设）

# 金属/锂收率：任务书阈值，非实测
YIELD = {
    'li_to_lce': 0.90,                # 课程 CN_LI 阈值；文献92%作敏感性
    'fe_to_fepo4': 0.85,              # 任务书 Fe/P回收率>85%
    'metals_to_sulfate': 0.98,        # 课程 Ni/Co/Mn 阈值
    'cu': 0.98,
    'al': 0.98,
}

# 单耗（每 t LCE），来自B的活动量口径，供本模块算OPEX；与B的
# DEFAULT_ACTIVITIES 一致，便于B直接对齐。
PER_T_LCE = {
    'electricity_kwh': 12_000.0,
    'steam_mj': 15_000.0,
    'freshwater_m3': 25.0,            # 假设：B只给废水，未给新水
    'h2so4_t': 2.5,                   # B: 2500 kg
    'h2o2_t': 0.4,
    'naoh_t': 1.5,
    'na2co3_t': 1.6,
    'lime_t': 0.8,
    'hazardous_t': 1.5,               # B: 1.5 t/t LCE
}

# 年度固定费用（假设；需A/C核）
FIXED_ANNUAL = {
    'labor_persons': 300.0,           # 8.5万元/人年
    'maintenance_rate_of_capex': 0.025,
    'other_pollution_control': 8_000_000.0,
    'other_costs': 12_000_000.0,
    'taxes_fees': 0.0,                # 税前模型；不含所得税/增值税
}

# 锂价→采购价传导：β = 每元/t LCE变动带来的元/t进料变动。
# 依据：1 t包约含10.64 kg Li → 56.6 kg LCE当量；按含锂价值的60%传导。
FEED_PASS_THROUGH = 0.034

ASSUMPTIONS = [
    ('A01', '拆解再生进料', 59_500, 't/a',
     '8万×85% − 1万×85%；A/C确认的选项A分流', '设计/负荷假设'),
    ('A02', '黑粉产量', None, 't/a', 'A JR23 包→电芯→黑粉组成，无捕集损失', 'A组成；M02未定'),
    ('A03', 'LCE产量', None, 't/a', '黑粉Li × 90% ÷ 18.787%', 'CN_LI阈值，非实测'),
    ('A04', '磷酸铁产量', None, 't/a', 'LFP黑粉Fe × FePO4化学计量 × 85%', '任务书Fe/P>85%'),
    ('A05', '混合硫酸盐产量', None, 't/a', 'NMC黑粉Ni+Co+Mn ÷ 22% × 98%', '22%金属含量为假设'),
    ('A06', '铜/铝产量', None, 't/a', '包级集流体+铜线，按电芯箔材比例拆分 × 98%', 'A组成；未精炼折价'),
    ('A07', '新水单耗', 25, 'm3/t LCE', 'B未给新水，按40 m3废水反推的数量级', '假设'),
    ('A08', '定员', 300, '人', '按6.8万吨园区规模估算', '假设，需A/C核'),
    ('A09', '维修费', 2.5, '% capex/a', '设备维护常见比例', '假设'),
    ('A10', '其他治理/其他费用', None, 'CNY/a', '800万+1200万，避免与已计项重复', '假设'),
    ('A11', '采购价锂价传导β', FEED_PASS_THROUGH, 't LCE/t feed',
     '1t包含56.6kg LCE当量，按含锂价值60%传导', '假设，需报价样本'),
    ('A12', 'LCE情景价', 117_699.1, 'CNY/t', '以C的2026年基准价锚定，按锂价比例缩放',
     'C价格；10k/22k/50k USD为文献锚点'),
]

# ---------------------------------------------------------------------------
# B. 价格（C经济参数表；已按收到税率作不含VAT规划换算）
# ---------------------------------------------------------------------------
PRICE_IDS = ['FS-03', 'PR-01', 'PR-02', 'PR-03', 'PR-04', 'PR-05',
             'UT-01', 'UT-02', 'UT-03', 'UT-04', 'RG-01', 'RG-02', 'RG-03',
             'RG-04', 'RG-05', 'LB-01', 'WS-01', 'FIN-02', 'FIN-01']
CAPEX_IDS = ['CAP-01', 'CAP-03', 'CAP-04', 'CAP-05', 'CAP-06', 'CAP-07', 'CAP-08']


def prices():
    rows = read_prices()
    p = {r['param_id']: r['ex_vat_planning_value'] for r in rows}
    return p


def mass_balance(yields=None):
    """返回年度物质流（t/a）与品位，全部可从A组成复算。"""
    y = dict(YIELD)
    y.update(yields or {})
    feed_total = DESIGN_FEED_T * LOAD
    reuse = REUSE_CAPACITY_T * LOAD
    recycle = feed_total - reuse
    out = {'feed_total': feed_total, 'reuse': reuse, 'recycle': recycle}
    powder = {k: 0.0 for k in CHEM}
    li = {k: 0.0 for k in CHEM}
    fe = {k: 0.0 for k in CHEM}
    metals = {'Ni': 0.0, 'Co': 0.0, 'Mn': 0.0}
    cu = al = 0.0
    for chem, share in CHEM.items():
        q = recycle * share
        c = PACK[chem]
        out[f'feed_{chem}'] = q
        pw = q * c['cell'] * c['powder_in_cell']
        powder[chem] = pw
        li[chem] = pw * c['li']
        if chem == 'LFP':
            fe[chem] = pw * c['fe']
        else:
            for m in metals:
                metals[m] += pw * c[m.lower()]
        foam_sum = c['al_foil_cell'] + c['cu_foil_cell']
        cu_share = c['cu_foil_cell'] / foam_sum
        al_share = c['al_foil_cell'] / foam_sum
        cu += q * (c['current_collector'] * cu_share + c['cu_wire'])
        al += q * c['current_collector'] * al_share
    out.update(powder=sum(powder.values()), powder_LFP=powder['LFP'],
               powder_NMC=powder['NMC'], li_in_powder=sum(li.values()))
    out['lce'] = out['li_in_powder'] * y['li_to_lce'] / LI2CO3_LI_FRACTION
    out['fepo4'] = fe['LFP'] / FEPO4_FE_FRACTION * y['fe_to_fepo4']
    out['sulfate'] = sum(metals.values()) / SULFATE_METAL_FRACTION * y['metals_to_sulfate']
    out['cu'] = cu * y['cu']
    out['al'] = al * y['al']
    out['metals'] = metals
    return out


def per_t_lce(mb):
    q = mb['lce']
    return {
        'feed': mb['recycle'] / q,
        'fepo4': mb['fepo4'] / q,
        'sulfate': mb['sulfate'] / q,
        'cu': mb['cu'] / q,
        'al': mb['al'] / q,
    }


def build_case(p, mb, *, green_ratio=0.0, lithium_price_usd=22_000.0,
               energy_efficiency=1.0, feed_pass_through=None,
               case_id='YCH_2026_C_BASE_LCOR'):
    """构造一个完整 tea_model 工况；LCOR = base_lcor_per_fu。"""
    if not 0.0 <= green_ratio <= 1.0:
        raise ValueError('green_ratio须在0-1')
    if energy_efficiency <= 0:
        raise ValueError('energy_efficiency须为正')
    ee = float(energy_efficiency)
    q = mb['lce']
    u = per_t_lce(mb)

    # 情景锂价：以C的2026基准价为锚，按美元锚点比例缩放（不是汇率换算）
    lce_price = p['PR-01'] * (float(lithium_price_usd) / 22_000.0)
    beta = FEED_PASS_THROUGH if feed_pass_through is None else float(feed_pass_through)
    feed_price = max(0.0, p['FS-03'] + beta * (lce_price - p['PR-01']))

    crf = capital_recovery_factor(p['FIN-02'], int(p['FIN-01']))
    capex = sum(p[k] for k in CAPEX_IDS)

    total_kwh = PER_T_LCE['electricity_kwh'] * q / ee
    costs = [
        dict(name='feed_purchase', category='feedstock', quantity_per_year=mb['recycle'],
             unit_price=feed_price, unit='t_feed_pack',
             source_id='ECON_BOOK:FS-03 + A11锂价传导'),
        dict(name='inbound_transport', category='transport', quantity_per_year=mb['recycle'],
             unit_price=0.0, unit='t_feed_pack',
             source_id='ACCOUNTING:included_in_delivered_feed_price'),
        dict(name='grid_electricity', category='utilities',
             quantity_per_year=total_kwh * (1 - green_ratio),
             unit_price=p['UT-01'], unit='kWh', source_id='ECON_BOOK:UT-01'),
        dict(name='green_electricity', category='utilities',
             quantity_per_year=total_kwh * green_ratio,
             unit_price=p['UT-02'], unit='kWh', source_id='ECON_BOOK:UT-02'),
        dict(name='steam', category='utilities', quantity_per_year=PER_T_LCE['steam_mj'] * q / ee,
             unit_price=p['UT-03'], unit='MJ', source_id='ECON_BOOK:UT-03'),
        dict(name='freshwater', category='utilities',
             quantity_per_year=PER_T_LCE['freshwater_m3'] * q / ee,
             unit_price=p['UT-04'], unit='m3', source_id='ECON_BOOK:UT-04; A07'),
        dict(name='sulfuric_acid_98pct', category='reagents',
             quantity_per_year=PER_T_LCE['h2so4_t'] * q / ee,
             unit_price=p['RG-01'], unit='t_solution', source_id='ECON_BOOK:RG-01'),
        dict(name='hydrogen_peroxide_27_5pct', category='reagents',
             quantity_per_year=PER_T_LCE['h2o2_t'] * q / ee,
             unit_price=p['RG-02'], unit='t_solution', source_id='ECON_BOOK:RG-02'),
        dict(name='sodium_hydroxide', category='reagents',
             quantity_per_year=PER_T_LCE['naoh_t'] * q / ee,
             unit_price=p['RG-03'], unit='t_commercial_product', source_id='ECON_BOOK:RG-03'),
        dict(name='sodium_carbonate', category='reagents',
             quantity_per_year=PER_T_LCE['na2co3_t'] * q / ee,
             unit_price=p['RG-04'], unit='t_commercial_product', source_id='ECON_BOOK:RG-04'),
        dict(name='lime', category='reagents',
             quantity_per_year=PER_T_LCE['lime_t'] * q / ee,
             unit_price=p['RG-05'], unit='t_commercial_product', source_id='ECON_BOOK:RG-05'),
        dict(name='labor', category='labor', quantity_per_year=FIXED_ANNUAL['labor_persons'],
             unit_price=p['LB-01'], unit='person_year', source_id='ECON_BOOK:LB-01; A08'),
        dict(name='hazardous_residue', category='pollution_control',
             quantity_per_year=PER_T_LCE['hazardous_t'] * q / ee,
             unit_price=p['WS-01'], unit='t_waste', source_id='ECON_BOOK:WS-01'),
        dict(name='maintenance', category='maintenance', quantity_per_year=1.0,
             unit_price=FIXED_ANNUAL['maintenance_rate_of_capex'] * capex,
             unit='annual_budget_CNY', source_id='A09: 2.5% capex'),
        dict(name='other_pollution_control', category='pollution_control',
             quantity_per_year=1.0, unit_price=FIXED_ANNUAL['other_pollution_control'],
             unit='annual_budget_CNY', source_id='A10'),
        dict(name='other_taxes_fees', category='taxes_fees', quantity_per_year=1.0,
             unit_price=FIXED_ANNUAL['taxes_fees'], unit='annual_budget_CNY',
             source_id='税前模型，不含所得税及增值税'),
        dict(name='other_costs', category='other', quantity_per_year=1.0,
             unit_price=FIXED_ANNUAL['other_costs'], unit='annual_budget_CNY',
             source_id='A10: 保险/质检/包装/补锂'),
    ]
    revenues = [
        dict(name='LCE_product', quantity_per_year=q, unit_price=lce_price,
             unit='t_battery_grade_LCE', source_id='ECON_BOOK:PR-01; A03'),
        dict(name='iron_phosphate', quantity_per_year=u['fepo4'] * q, unit_price=p['PR-02'],
             unit='t_sale_product', source_id='ECON_BOOK:PR-02; A04'),
        dict(name='nmc_mixed_sulfate', quantity_per_year=u['sulfate'] * q,
             unit_price=p['PR-03'], unit='t_sale_product', source_id='ECON_BOOK:PR-03; A05'),
        dict(name='copper', quantity_per_year=u['cu'] * q, unit_price=p['PR-04'],
             unit='t_sale_product', source_id='ECON_BOOK:PR-04; A06'),
        dict(name='aluminum', quantity_per_year=u['al'] * q, unit_price=p['PR-05'],
             unit='t_sale_product', source_id='ECON_BOOK:PR-05; A06'),
    ]
    case = dict(
        case_id=case_id, data_status='c_provisional_from_A_composition',
        currency='CNY', price_year=2026,
        functional_unit='t_battery_grade_LCE_product', feed_t_per_year=mb['recycle'],
        fu_per_year=q, capex=capex, discount_rate=p['FIN-02'],
        operating_years=int(p['FIN-01']), cost_items=costs, revenue_items=revenues,
        scenario_adjustments=[], boundary_id='RECYCLING_ONLY_EXCLUDES_REUSE_LINE',
        accounting_note='Valuation basis: ex-VAT 2026 constant CNY planning assumption. '
                        'Boundary: recycling line only (reuse line and its revenue excluded). '
                        'Indicator: park net cost normalised by LCE output; not an allocated '
                        'cost of a single LCE product.',
    )
    return case


def evaluate(p, mb, **kw):
    return evaluate_tea(build_case(p, mb, **kw))


def scenario_lcor(p, mb, lithium_price_usd, green_ratio, energy_efficiency):
    """返回 (园区口径LCOR, 仅LCE收入LCOR)。"""
    case = build_case(p, mb, green_ratio=green_ratio,
                      lithium_price_usd=lithium_price_usd,
                      energy_efficiency=energy_efficiency, case_id='scenario')
    park = evaluate_tea(case)['base_lcor_per_fu']
    case = json.loads(json.dumps(case))
    for row in case['revenue_items']:
        if row['name'] != 'LCE_product':
            row['quantity_per_year'] = 0.0
    only = evaluate_tea(case)['base_lcor_per_fu']
    return park, only


# ---------------------------------------------------------------------------
# C. 输出
# ---------------------------------------------------------------------------
def _write_csv(path, rows, fields=None):
    rows = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields or list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def b_grid():
    """与B scenario_analysis 完全相同的遍历顺序；case_id 必须一一对应。"""
    import itertools
    green = [round(x, 4) for x in [i / 10 for i in range(11)]]
    process = [round(x, 4) for x in [i / 10 for i in range(11)]]
    out = []
    cid = 0
    for pm in process:
        for gr in green:
            for ef in (0.314, 0.556, 0.749):
                for lp in (10_000.0, 22_000.0, 50_000.0):
                    for ee in (0.80, 1.00, 1.20):
                        out.append(dict(case_id=cid, process_mix=pm, green_ratio=gr,
                                        grid_ef=ef, lithium_price_usd=lp,
                                        energy_efficiency=ee))
                        cid += 1
    return out


def sensitivity(p, mb):
    """单因素与组合敏感性；用于说明单点LCOR的驱动因素，不替代正式情景。"""
    p_fepo4 = dict(p)
    p_fepo4['PR-02'] = 11_000.0 / 1.13          # 市场量级压力值（含税11,000）
    mb_li92 = mass_balance({'li_to_lce': 0.92})

    def lce_only(case):
        """只计LCE收入、副产品全部不计，用于回答“单吨LCE的净成本”。"""
        case = json.loads(json.dumps(case))
        for row in case['revenue_items']:
            if row['name'] != 'LCE_product':
                row['quantity_per_year'] = 0.0
                row['source_id'] += '; 敏感性：副产品不计'
        return case

    variants = [
        ('基准（收到报价，全部副产品计收入）', build_case(p, mb)),
        ('仅LCE收入（副产品不计）', lce_only(build_case(p, mb))),
        ('磷酸铁按含税11,000元/t', build_case(p_fepo4, mb)),
        ('锂回收率92%', build_case(p, mb_li92)),
        ('磷酸铁11,000+锂回收率92%', build_case(p_fepo4, mb_li92)),
        ('锂价50,000且采购价不传导(β=0)',
         build_case(p, mb, lithium_price_usd=50_000.0, feed_pass_through=0.0)),
        ('绿电100%', build_case(p, mb, green_ratio=1.0)),
        ('锂价50,000 USD/t', build_case(p, mb, lithium_price_usd=50_000.0)),
        ('锂价10,000 USD/t', build_case(p, mb, lithium_price_usd=10_000.0)),
    ]
    rows = []
    for label, case in variants:
        r = evaluate_tea(case)
        rows.append(dict(scenario=label, lce_t_per_year=case['fu_per_year'],
                         net_cost_CNY_per_year=r['base_net_cost_per_year'],
                         lcor_CNY_per_t_LCE=r['base_lcor_per_fu'],
                         net_profit_CNY_per_t_feed=r['base_net_profit_per_t_feed']))
    return rows


def main():
    p = prices()
    mb = mass_balance()
    OUT.mkdir(parents=True, exist_ok=True)
    base = evaluate(p, mb)
    base_case = build_case(p, mb)
    (OUT / 'tea_case_c_base.json').write_text(
        json.dumps(base_case, ensure_ascii=False, indent=2), encoding='utf-8')

    # 基准分项
    rows = []
    for k, v in base['cost_breakdown'].items():
        rows.append(dict(item=k, kind='cost', value_CNY_per_year=v,
                         value_CNY_per_t_LCE=v / mb['lce']))
    for k, v in base['revenue_breakdown'].items():
        rows.append(dict(item=k, kind='revenue', value_CNY_per_year=v,
                         value_CNY_per_t_LCE=v / mb['lce']))
    rows.append(dict(item='annualized_capex', kind='cost',
                     value_CNY_per_year=base['annualized_capex'],
                     value_CNY_per_t_LCE=base['annualized_capex'] / mb['lce']))
    _write_csv(OUT / 'base_cost_breakdown.csv', rows)

    # B的3267工况
    grid = b_grid()
    scen = []
    for row in grid:
        row = dict(row)
        park, only = scenario_lcor(
            p, mb, row['lithium_price_usd'], row['green_ratio'], row['energy_efficiency'])
        row['lcor_rmb_per_t_LCE'] = park
        row['lcor_lce_only_rmb_per_t_LCE'] = only
        scen.append(row)
    _write_csv(OUT / 'lcor_for_b_3267.csv', scen)

    sens = sensitivity(p, mb)
    _write_csv(OUT / 'lcor_sensitivity.csv', sens)

    # 假设登记：把可由A组成复算的量填进登记表
    filled = []
    for a, b, c, d, e, f in ASSUMPTIONS:
        if a == 'A02':
            c = round(mb['powder'], 1)
        elif a == 'A03':
            c = round(mb['lce'], 1)
        elif a == 'A04':
            c = round(mb['fepo4'], 1)
        elif a == 'A05':
            c = round(mb['sulfate'], 1)
        elif a == 'A06':
            c = f"Cu {mb['cu']:.1f} / Al {mb['al']:.1f}"
        elif a == 'A10':
            c = FIXED_ANNUAL['other_pollution_control'] + FIXED_ANNUAL['other_costs']
        filled.append(dict(id=a, item=b, value=c, unit=d, basis=e, status=f))
    _write_csv(OUT / 'assumptions_register.csv', filled)

    summary = dict(
        case_id=base['case_id'], data_status=base['data_status'],
        boundary=base_case['boundary_id'], currency='CNY', price_year=base['price_year'],
        mass_balance={k: v for k, v in mb.items() if not isinstance(v, dict)},
        lce_t_per_year=mb['lce'],
        annualized_capex_CNY=base['annualized_capex'],
        opex_CNY=base['opex_per_year'], revenue_CNY=base['revenue_per_year'],
        net_cost_CNY=base['base_net_cost_per_year'],
        lcor_CNY_per_t_LCE=base['base_lcor_per_fu'],
        net_profit_CNY_per_t_feed=base['base_net_profit_per_t_feed'],
        lcor_range_over_b_grid=[min(s['lcor_rmb_per_t_LCE'] for s in scen),
                                max(s['lcor_rmb_per_t_LCE'] for s in scen)],
        lcor_lce_only_range_over_b_grid=[
            min(s['lcor_lce_only_rmb_per_t_LCE'] for s in scen),
            max(s['lcor_lce_only_rmb_per_t_LCE'] for s in scen)],
        sensitivity=sens,
        assumptions=filled,
        note='C侧临时LCOR，用于B跑通帕累托；不是A实测物质流或已核报价的最终结论。',
    )
    (OUT / 'lcor_summary.json').write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=float), encoding='utf-8')
    print(json.dumps({k: summary[k] for k in
                      ('lce_t_per_year', 'annualized_capex_CNY', 'opex_CNY',
                       'revenue_CNY', 'net_cost_CNY', 'lcor_CNY_per_t_LCE',
                       'lcor_range_over_b_grid')}, ensure_ascii=False, indent=2, default=float))


if __name__ == '__main__':
    main()
