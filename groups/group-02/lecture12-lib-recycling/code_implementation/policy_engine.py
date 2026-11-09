"""课程政策量化模型；结果不构成法律合规认证。
AI Prompt: 建立数据驱动政策引擎，区分工艺、市场、日期及口径，
缺失数据返回UNKNOWN，支持严格小于和大于等于边界并输出失败原因。
人工核验修正：尚待成员C核对官方文件、适用范围和计算分母。
"""
from __future__ import annotations

import json
import math
import operator
from datetime import date
from pathlib import Path

DEFAULT_POLICY = Path(__file__).resolve().parents[1] / 'data_cohort' / 'policy_parameters.json'
OPS = {'>=': operator.ge, '<': operator.lt, '<=': operator.le, '>': operator.gt}


def evaluate_policy(case, policy_path=DEFAULT_POLICY, *, profile='coursework'):
    """coursework：任务书阈值；verified_current：仅接受核实过的现行规则。

    必填日期、工艺分支、欧盟材料回收/新电池对象标识及所含金属列表。
    pass仅表示已编码定量项满足阈值；缺失信息不作为达标。
    """
    if profile not in {'coursework', 'verified_current'}:
        raise ValueError('未知profile')
    evaluation_date = date.fromisoformat(case['evaluation_date'])
    if case.get('route') not in {'smelting', 'repair', 'mixed'}:
        raise ValueError('route 必须为 smelting/repair/mixed；mixed须提供各分支指标')
    for key in ('eu_material_recovery_scope', 'eu_new_battery_scope', 'produces_lithium_carbonate'):
        if not isinstance(case.get(key), bool):
            raise ValueError(f'{key}必须显式填写true或false；无法确认适用性时先补充资料')
    metals = case.get('metals_present')
    if not isinstance(metals, list) or not metals or not all(isinstance(m, str) for m in metals):
        raise ValueError('metals_present须由A的物料清单提供非空金属列表')
    if len(set(metals)) != len(metals) or set(metals) - {'Li', 'Ni', 'Co', 'Mn', 'Cu', 'Al', 'Pb'}:
        raise ValueError('metals_present含重复或未支持元素')
    policy = json.loads(Path(policy_path).read_text(encoding='utf-8'))
    rows = []
    for rule in policy['rules']:
        reason = None
        if rule.get('routes') and case['route'] not in rule['routes']:
            reason = '工艺不适用'
        if rule.get('requires_flag') and not case[rule['requires_flag']]:
            reason = '不在本规则对象范围'
        if rule.get('metal') and rule['metal'] not in metals:
            reason = '物料清单不含该金属'
        if evaluation_date < date.fromisoformat(rule['start']):
            reason = '未到本阶段日期'
        if rule.get('end_exclusive') and evaluation_date >= date.fromisoformat(rule['end_exclusive']):
            reason = '本阶段已结束'
        row = {'rule_id': rule['id'], 'metric': rule['metric'], 'threshold': rule['threshold'],
               'operator': rule['operator'], 'unit': rule['unit'], 'source_id': rule['source_id']}
        if reason:
            row.update(status='NOT_APPLICABLE', reason=reason, actual=None)
        elif profile == 'verified_current' and rule['verification'] != 'verified_current':
            row.update(status='UNKNOWN', reason='官方现行版本及适用性尚未核实', actual=None)
        else:
            value = case.get('metrics', {}).get(rule['metric'])
            valid = (not isinstance(value, bool) and isinstance(value, (float, int))
                     and math.isfinite(value) and value >= 0)
            if valid and rule['unit'] == 'fraction':
                valid = value <= 1
            if not valid:
                row.update(status='UNKNOWN', reason='缺失或非法数值；比例须为0至1', actual=None)
            else:
                passed = OPS[rule['operator']](value, rule['threshold'])
                row.update(status='PASS' if passed else 'FAIL', actual=value,
                           reason='满足编码阈值' if passed else f"{value} 不满足 {rule['operator']} {rule['threshold']}")
        rows.append(row)
    active = [r for r in rows if r['status'] != 'NOT_APPLICABLE']
    overall = ('FAIL' if any(r['status'] == 'FAIL' for r in active) else
               'UNKNOWN' if not active or any(r['status'] == 'UNKNOWN' for r in active) else 'PASS')
    return {'case_id': case.get('case_id'), 'profile': profile, 'status': overall,
            'feasible': overall == 'PASS', 'checks': rows,
            'issues': [r for r in active if r['status'] in {'FAIL', 'UNKNOWN'}],
            'scope_note': policy['scope_note']}
