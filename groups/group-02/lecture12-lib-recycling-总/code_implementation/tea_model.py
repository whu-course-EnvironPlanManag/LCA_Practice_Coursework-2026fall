"""成员 C 技术经济模型，恒定实际价格、税前、无杠杆年度现金流。
AI Prompt: 根据作业12方向B成员C分工，实现资本年金、分项运行费用、
产品收入、价格与SOH采购联动、情景激励和同边界MAC，严格检查缺失值与单位。
人工核验修正：尚待成员C逐项核验；自动化测试不能替代人工审阅。
"""
from __future__ import annotations

import math


def number(value, name, *, positive=False, upper=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name}: 必须填写数值，不得用空值或字符串")
    if not math.isfinite(value) or value < 0 or (positive and value == 0):
        raise ValueError(f"{name}: 必须为有限{'正' if positive else '非负'}数")
    if upper is not None and value > upper:
        raise ValueError(f"{name}: 不得大于{upper}")
    return float(value)


def capital_recovery_factor(rate, years):
    r = number(rate, 'discount_rate', upper=1)
    n = number(years, 'operating_years', positive=True)
    if not n.is_integer():
        raise ValueError('operating_years: 使用整数运营年限')
    if r == 0:
        return 1 / n
    return r / (1 - (1 + r) ** (-n))


def evaluate_tea(case):
    """所有现金额同币种同价格年；流量均为年总量。无隐式汇率换算。

    返回base不含情景激励；with_scenario含显式假设收入/费用。
    LCOR为净年成本/功能单位年产量。每吨进料净收益单独输出。
    不计算所得税、贷款利息、建设期、残值和营运资金；若需这些应扩展现金流。
    """
    for key in ('case_id', 'currency', 'price_year', 'functional_unit', 'data_status'):
        if not case.get(key):
            raise ValueError(f'{key}: 必填')
    feed = number(case.get('feed_t_per_year'), 'feed_t_per_year', positive=True)
    output = number(case.get('fu_per_year'), 'fu_per_year', positive=True)
    crf = capital_recovery_factor(case.get('discount_rate'), case.get('operating_years'))
    capex = number(case.get('capex'), 'capex')
    cost_rows = case.get('cost_items')
    revenue_rows = case.get('revenue_items')
    if not isinstance(cost_rows, list) or not isinstance(revenue_rows, list):
        raise ValueError('cost_items/revenue_items 必须提供列表')
    categories = {r.get('category') for r in cost_rows}
    required = {'feedstock', 'transport', 'utilities', 'reagents', 'labor',
                'maintenance', 'pollution_control', 'taxes_fees'}
    if required - categories:
        raise ValueError(f'缺少费用类别（确认为零也须明示）: {sorted(required - categories)}')
    costs, revenues = {}, {}
    seen = set()
    for rows, target in ((cost_rows, costs), (revenue_rows, revenues)):
        for row in rows:
            name = row.get('name')
            if not name or name in seen:
                raise ValueError('费用和收入项目须有唯一name')
            seen.add(name)
            if not row.get('unit') or not row.get('source_id'):
                raise ValueError(f'{name}: 必须记录计量单位和source_id')
            q = number(row.get('quantity_per_year'), f'{name}.quantity_per_year')
            p = number(row.get('unit_price'), f'{name}.unit_price')
            # 采购报价的局部线性情景式；系数必须由报价或情景假设明确提供。
            link = row.get('price_link')
            if link:
                if row.get('category') != 'feedstock':
                    raise ValueError('price_link 仅适用于采购项目')
                current = number(link.get('lce_price'), 'lce_price')
                ref = number(link.get('reference_lce_price'), 'reference_lce_price')
                beta = number(link.get('lce_pass_through'), 'lce_pass_through')
                soh = number(link.get('soh'), 'soh', upper=1)
                soh0 = number(link.get('reference_soh'), 'reference_soh', upper=1)
                gamma = number(link.get('soh_coefficient'), 'soh_coefficient')
                p += beta * (current - ref) + gamma * (soh - soh0)
                number(p, f'{name}.linked_price')
            target[name] = q * p
    opex = sum(costs.values())
    revenue = sum(revenues.values())
    annual_capital = capex * crf
    base_net = annual_capital + opex - revenue
    scenario_income = scenario_cost = 0.0
    for item in case.get('scenario_adjustments', []):
        if item.get('status') != 'assumption' or not item.get('basis'):
            raise ValueError('情景修正必须标记assumption并写明basis；不得冒充已确认收入')
        amount = number(item.get('amount_per_year'), 'scenario.amount_per_year')
        if item.get('kind') == 'income':
            scenario_income += amount
        elif item.get('kind') == 'cost':
            scenario_cost += amount
        else:
            raise ValueError('scenario.kind必须为income/cost')
    adjusted_net = base_net + scenario_cost - scenario_income
    result = {
        'case_id': case['case_id'], 'data_status': case['data_status'],
        'currency': case['currency'], 'price_year': case['price_year'],
        'functional_unit': case['functional_unit'], 'crf': crf,
        'annualized_capex': annual_capital, 'opex_per_year': opex,
        'revenue_per_year': revenue, 'cost_breakdown': costs,
        'revenue_breakdown': revenues, 'base_net_cost_per_year': base_net,
        'base_lcor_per_fu': base_net / output,
        'base_net_profit_per_t_feed': -base_net / feed,
        'scenario_income_per_year': scenario_income,
        'scenario_cost_per_year': scenario_cost,
        'with_scenario_net_cost_per_year': adjusted_net,
        'with_scenario_lcor_per_fu': adjusted_net / output,
        'mac_per_tco2e': None, 'mac_status': '缺少同边界基准或排放数据',
    }
    baseline = case.get('baseline')
    if baseline is not None:
        for key in ('functional_unit', 'currency', 'price_year'):
            if baseline.get(key) != case[key]:
                raise ValueError(f'基准与回收路径的{key}不一致')
        # 净成本允许负值；禁止用number的非负约束限制基准净成本。
        bcost = baseline.get('net_cost_per_fu')
        if isinstance(bcost, bool) or not isinstance(bcost, (float, int)) or not math.isfinite(bcost):
            raise ValueError('baseline.net_cost_per_fu 必须为有限数')
        if baseline.get('boundary_id') != case.get('boundary_id') or not case.get('boundary_id'):
            raise ValueError('必须明确且一致的boundary_id，包括多产品分配与替代规则')
        bghg = number(baseline.get('gwp_kgco2e_per_fu'), 'baseline.gwp')
        ghg = number(case.get('gwp_kgco2e_per_fu'), 'case.gwp')
        avoided = (bghg - ghg) / 1000
        if avoided > 0:
            result['mac_per_tco2e'] = (base_net / output - bcost) / avoided
            result['mac_status'] = '已按不含情景激励的成本计算'
        else:
            result['mac_status'] = '未产生正减排量，MAC不定义'
    return result
