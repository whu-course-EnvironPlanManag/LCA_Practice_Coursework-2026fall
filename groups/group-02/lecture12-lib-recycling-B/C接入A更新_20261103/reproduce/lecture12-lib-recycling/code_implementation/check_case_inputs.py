"""AI Prompt: 核对用户宜昌案例的规模、SOH分流和黑粉口径，生成可复现交接审查。
人工核验修正：待成员C与A确认；只诊断规划假设，不生成真实经济结论。
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    case = json.loads((ROOT / 'data_cohort/case_assumptions.json').read_text(encoding='utf-8'))
    feed = case['feed']['mass_t_per_year']
    chemistry = case['feed']['chemistry_fractions']
    bins = case['soh_bins']
    for fractions in [list(chemistry.values()), [b['fraction'] for b in bins]]:
        if not all(0 <= x <= 1 for x in fractions) or not math.isclose(sum(fractions), 1, abs_tol=1e-12):
            raise ValueError('规划占比必须在0至1且加总为1')
    masses = {b['id']: feed * b['fraction'] for b in bins}
    candidates = masses['above_85'] + masses['70_to_85']
    capacity = case['reuse_capacity_t_per_year']
    black_mass = case['claimed_black_mass_t_per_year']
    chosen = next(x for x in case['allocation_options'] if x['id'] == case['allocation_decision'])
    reuse = chosen['reuse_priority_t_per_year'] + chosen['reuse_candidate_t_per_year']
    recycle = chosen['recycling_pack_equivalent_t_per_year']
    if not math.isclose(reuse + recycle, feed) or reuse > capacity:
        raise ValueError('已选方案的包当量分流不守恒或超出确认的梯次上限')
    results = {
        'basis': '假设年度满负荷及SOH为电池包质量占比；模组能力尚未换算',
        'chemistry_mass_t_per_year': {k: v * feed for k, v in chemistry.items()},
        'soh_mass_t_per_year': masses,
        'priority_and_candidate_pack_mass_t_per_year': candidates,
        'nominal_candidate_minus_capacity_t_per_year': candidates - capacity,
        'black_mass_divided_by_total_pack_input': black_mass / feed,
        'selected_reuse_pack_equivalent_t_per_year': reuse,
        'selected_recycling_pack_equivalent_t_per_year': recycle,
        'selected_pack_allocation_residual_t_per_year': feed - reuse - recycle,
        'unselected_candidate_to_recycling_t_per_year': masses['70_to_85'] - chosen['reuse_candidate_t_per_year'],
        'black_mass_divided_by_selected_recycling_pack_input': black_mass / recycle,
        'mass_balance_validated': False,
        'allocation_decision': case['allocation_decision'],
        'blocking_inputs': ['包/模组/电芯质量换算', '黑粉分选边界',
                            '实际运行负荷', 'LCE产量及产品品级', 'NMC622/811内部比例',
                            '工艺路线及活动量', '投资与单价', '价格年币种确认',
                            '同边界原生基准', '现行政策核验及欧盟适用范围']
    }
    target = ROOT / 'report' / 'case_input_review.json'
    target.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Planning input review; NOT a validated mass balance')
    for k, v in results.items():
        if k not in ['blocking_inputs', 'basis']:
            print(k, '=', v)


if __name__ == '__main__':
    main()
