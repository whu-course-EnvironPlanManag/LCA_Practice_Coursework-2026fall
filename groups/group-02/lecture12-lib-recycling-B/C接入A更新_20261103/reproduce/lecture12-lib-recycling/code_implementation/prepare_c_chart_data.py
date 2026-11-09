"""AI Prompt: 从已复核CSV生成C成员图表数据；明确B占位参数及固定外部情景。
人工核验：待成员C复核。图表用于课程联调阶段，不代表实测经济结论。
"""
import csv
import json
from pathlib import Path

root=Path(__file__).resolve().parents[1]
def read(name):
    with (root/'data_cohort/integration_20261103'/name).open(encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))
rows=read('scenario_c_review.csv')
group=[r for r in rows if float(r['grid_ef'])==.556 and float(r['lithium_price_usd'])==22000 and float(r['energy_efficiency'])==1 and r['feasible']=='True']
front={int(r['case_id']) for r in read('conditional_fronts.csv') if float(r['grid_ef'])==.556 and float(r['lithium_price_usd'])==22000 and float(r['energy_efficiency'])==1}
cost=next(r for r in read('b_cost_bridge.csv') if int(r['case_id'])==580)
scatter=[]
for r in sorted(group,key=lambda r:float(r['gwp_kgco2e'])):
    i=int(r['case_id']); x=float(r['gwp_kgco2e']); y=float(r['lcor_rmb_per_t'])/10000
    scatter.append([x,y,y if i in front else None,y if i==13 else None,y if i==580 else None,y if i==3253 else None])
summary=json.loads((root/'report/integration_20261103/summary.json').read_text(encoding='utf-8'))
data={'cost':[['电力',float(cost['electricity'])],['热能',float(cost['heat'])],['试剂打包费',float(cost['reagents_lump_sum'])],['人工运维',float(cost['labor_maintenance_lump_sum'])],['工艺附加费',float(cost['direct_route_premium'])]],
      'cost_total':float(cost['accounted_cost_total']),'scatter':scatter,'group_count':len(group),'front_count':len(front),
      'policy':[['通过',summary['b_two_rule_pass'],0],['不通过',summary['b_two_rule_fail'],summary['c_diagnostic_policy_counts']['FAIL']],['信息不足',0,summary['c_diagnostic_policy_counts']['UNKNOWN']]]}
path=root/'data_cohort/integration_20261103/c_chart_data.json'
path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print(path); print('group',len(group),'front',len(front),'cost',data['cost_total'])
