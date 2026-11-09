"""AI Prompt: 独立复算B占位模型，按固定外部情景比较决策，并检查数据完整性。
人工核验：待成员C审阅。复算不是参数实证核验，不把占位成本当完整TEA。
"""
from __future__ import annotations

import math


def activities_from_b(pm, efficiency):
    if not 0 <= pm <= 1 or efficiency <= 0:
        raise ValueError('工艺份额或能效参数非法')
    return {
        'electricity_kwh': (12000 * (1-pm) + 6000 * pm) / efficiency,
        'natural_gas': (15000 * (1-pm) + 8000 * pm) / efficiency,
        'sulfuric_acid_H2SO4': 2500 * (1-pm),
        'hydrogen_peroxide_H2O2': 400 * (1-pm),
        'sodium_hydroxide_NaOH': 1500 * (1-.7*pm),
        'sodium_carbonate_Na2CO3': 1600 * (1-.5*pm),
        'lime_CaO': 800 * (1-.3*pm), 'diesel_truck': 2000,
        'wastewater_treatment': 30 * (1-.5*pm),
        'fluoride_wastewater_advanced': 10 * (1-.7*pm),
        'hazardous_residue_disposal': 1.5 * (1-.5*pm),
    }


def reconstruct_b(row, factors):
    """按B原代码重现；固定2 L/kWh网电水因子也保留以暴露其行为。"""
    a = activities_from_b(row['process_mix'], row['energy_efficiency'])
    gr, pm = row['green_ratio'], row['process_mix']
    gwp = a['electricity_kwh'] * (gr*.035 + (1-gr)*row['grid_ef'])
    water = a['electricity_kwh'] * (gr*.2 + (1-gr)*2)
    for key, amount in a.items():
        if key == 'electricity_kwh':
            continue
        gwp += amount * factors[key]['gwp_kgco2e_per_unit']
        water += amount * factors[key]['water_l_per_unit']
    costs = {'electricity': a['electricity_kwh']*(gr*.5+(1-gr)*.4),
             'heat': a['natural_gas']*.25, 'reagents_lump_sum': 8000.,
             'labor_maintenance_lump_sum': 5000., 'direct_route_premium': 20000.*pm}
    sales = {'lce_sale_assumed': row['lithium_price_usd']*7.2, 'coproduct_sale_assumed': 2000.}
    energy = a['electricity_kwh']*.1229 + a['natural_gas']/29.3076
    net = sum(costs.values())-sum(sales.values())
    return dict(activities=a, costs=costs, sales=sales, gwp=gwp, water=water,
                energy_kgce_per_b_fu=energy, lcor=net,
                two_rule_eligible=energy < 2200 and .90+.09*pm >= .90)


def pareto_indices(rows, x='gwp_kgco2e', y='lcor_rmb_per_t'):
    """min/min，保留同坐标并列，按x组处理，避免相同x的劣解保留。"""
    if not rows:
        return []
    if any(not math.isfinite(r[x]) or not math.isfinite(r[y]) for r in rows):
        raise ValueError('帕累托输入必须是有限数')
    order = sorted(range(len(rows)), key=lambda i: (rows[i][x], rows[i][y], rows[i]['case_id']))
    best_y, result, pos = math.inf, [], 0
    while pos < len(order):
        end = pos+1
        while end < len(order) and rows[order[end]][x] == rows[order[pos]][x]:
            end += 1
        same_x = order[pos:end]
        min_y = min(rows[i][y] for i in same_x)
        if min_y < best_y:
            result.extend(i for i in same_x if rows[i][y] == min_y)
        best_y = min(best_y, min_y)
        pos = end
    return result


def choose_anchors(rows):
    front = [rows[i] for i in pareto_indices(rows)]
    if not front:
        raise ValueError('无可比较的两规则通过工况')
    gx = [r['gwp_kgco2e'] for r in front]; cy = [r['lcor_rmb_per_t'] for r in front]
    dx, dy = max(gx)-min(gx), max(cy)-min(cy)
    score = lambda r: ((r['gwp_kgco2e']-min(gx))/(dx or 1))**2 + ((r['lcor_rmb_per_t']-min(cy))/(dy or 1))**2
    return {'cost': min(front,key=lambda r:(r['lcor_rmb_per_t'],r['gwp_kgco2e'],r['case_id'])),
            'environment': min(front,key=lambda r:(r['gwp_kgco2e'],r['lcor_rmb_per_t'],r['case_id'])),
            'compromise': min(front,key=lambda r:(score(r),r['case_id'])), 'front':front}


def completion_check(case):
    """列出完整TEA所需缺项；不把0当缺失，也不自动采用B的报价占位值。"""
    missing = []
    for key in ['price_year','feed_t_per_year','fu_per_year','capex','discount_rate','operating_years']:
        if case.get(key) is None:
            missing.append(key)
    for collection in ['cost_items','revenue_items']:
        for row in case.get(collection,[]):
            for key in ['quantity_per_year','unit_price']:
                if row.get(key) is None:
                    missing.append(f"{collection}.{row['name']}.{key}")
    return missing
