"""AI Prompt: 接入A台账与B工况，保留证据、复算占位结果、分情景寻优并输出C交接表。
人工核验：待成员C审阅；不修改A/B文件，不把诊断值写成实证TEA。
"""
from __future__ import annotations
import csv
import hashlib
import json
import math
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from openpyxl import load_workbook
from handoff_analysis import reconstruct_b, choose_anchors, completion_check
from policy_engine import evaluate_policy
from reuse_policy_2026 import evaluate_reuse_application

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT.parent
A=WORK/'A前期数据资料包_20261103/A前期数据资料包_20261103'
B=WORK/'lecture12-lib-recycling-B/lecture12-lib-recycling-B'
OUT=ROOT/'data_cohort/integration_20261103'
REPORT=ROOT/'report/integration_20261103'


def csv_read(path):
    with path.open(encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))


def csv_write(path, rows):
    if not rows:
        return
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def json_write(path,obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')


def main():
    OUT.mkdir(parents=True,exist_ok=True); REPORT.mkdir(parents=True,exist_ok=True)
    sources=[A/'A前期数据台账_20261103.xlsx',WORK/'C_从B情景与因子提取_20261103.xlsx',
             B/'data_cohort/scenario_results.csv',B/'data_cohort/environmental_factors.csv',
             B/'code_implementation/scenario_analysis.py',B/'code_implementation/lca_model.py',
             B/'code_implementation/optimization.py',B/'data_cohort/README_data_sources.md',
             *[A/'data_cohort'/n for n in ['literature_parameters.csv','source_registry.csv',
                 'policy_register.csv','process_parameters.csv','uploaded_document_audit.csv','project_data.csv']]]
    manifest=[dict(path=str(p.relative_to(WORK)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size) for p in sources]
    json_write(OUT/'source_manifest.json',manifest)
    # 提取两本工作簿用于复查，保留原始单元格位置。
    extracts=[]
    for p in sources[:2]:
        wb=load_workbook(p,data_only=True,read_only=True)
        for ws in wb:
            for row in ws:
                for cell in row:
                    if cell.value is not None:
                        extracts.append(dict(file=p.name,sheet=ws.title,cell=cell.coordinate,value=str(cell.value)))
        wb.close()
    csv_write(OUT/'workbook_cells.csv',extracts)

    raw=csv_read(B/'data_cohort/scenario_results.csv')
    factors={r['factor_name']:{**r,'gwp_kgco2e_per_unit':float(r['gwp_kgco2e_per_unit']),
                              'water_l_per_unit':float(r['water_l_per_unit'])} for r in csv_read(B/'data_cohort/environmental_factors.csv')}
    rows=[]; seen=set(); policy_details=[]; costs=[]; maxerr=defaultdict(float)
    for original in raw:
        r={k:(v if k in ['feasible','violations'] else float(v)) for k,v in original.items()}
        r['case_id']=int(r['case_id']); r['feasible']=r['feasible'].lower()=='true'
        if r['case_id'] in seen: raise ValueError('重复工况ID')
        seen.add(r['case_id'])
        computed=reconstruct_b(r,factors)
        for orig,new in [('gwp_kgco2e','gwp'),('water_l','water'),('lcor_rmb_per_t','lcor')]:
            maxerr[orig]=max(maxerr[orig],abs(r[orig]-computed[new]))
            if not math.isclose(r[orig],computed[new],rel_tol=1e-10,abs_tol=1e-7):
                raise ValueError(f"复算不一致: {r['case_id']} {orig}")
        if r['feasible'] != computed['two_rule_eligible']: raise ValueError('两规则筛选复算不一致')
        pm=r['process_mix']
        # 纯湿法的声明功能单位可诊断折标值。混合/修复缺产品分流，不能套用整线LCE分母。
        case=dict(case_id=r['case_id'],evaluation_date='2030-12-31',route='smelting' if pm==0 else 'repair' if pm==1 else 'mixed',
                  metals_present=['Li','Ni','Co','Mn','Cu','Al'],eu_material_recovery_scope=False,
                  eu_new_battery_scope=False,produces_lithium_carbonate=pm<1,
                  metrics={'recycling_capacity_t_per_year':70000,
                           'lce_energy_kgce_per_t':computed['energy_kgce_per_b_fu'] if pm==0 else None})
        pc=evaluate_policy(case)
        for check in pc['checks']:
            policy_details.append(dict(case_id=r['case_id'],**check))
        r.update(b_energy_kgce_per_assumed_fu=computed['energy_kgce_per_b_fu'],
                 c_diagnostic_policy_status=pc['status'],c_unknown_rule_count=sum(x['status']=='UNKNOWN' for x in pc['checks']),
                 c_formal_tea_status='INCOMPLETE',c_formal_lcor_rmb_per_t=None,c_mac_rmb_per_tco2e=None,
                 evidence_status='B_placeholder_reproduced_not_project_estimate')
        rows.append(r)
        costs.append(dict(case_id=r['case_id'],**computed['costs'],**computed['sales'],
                          accounted_cost_total=sum(computed['costs'].values()),
                          accounted_revenue_total=sum(computed['sales'].values()),
                          b_partial_net_cost=computed['lcor'],
                          omitted_cost_headroom=-computed['lcor'],
                          unit='CNY_per_B_assumed_t_LCE',status='placeholder_bridge_not_full_TEA'))
    csv_write(OUT/'scenario_c_review.csv',rows)
    csv_write(OUT/'policy_checks_diagnostic.csv',policy_details)
    csv_write(OUT/'b_cost_bridge.csv',costs)
    feasible=[r for r in rows if r['feasible']]
    global_anchors=choose_anchors(feasible)
    original_env=min(feasible,key=lambda r:r['gwp_kgco2e'])
    groups=defaultdict(list)
    for r in feasible:
        groups[(r['grid_ef'],r['lithium_price_usd'],r['energy_efficiency'])].append(r)
    conditional=[]; fronts=[]
    for key, group in sorted(groups.items()):
        anchors=choose_anchors(group)
        for label in ['cost','compromise','environment']:
            r=anchors[label]
            conditional.append({k:r[k] for k in ['case_id','grid_ef','lithium_price_usd','energy_efficiency','green_ratio','process_mix','gwp_kgco2e','water_l','lcor_rmb_per_t']}|
                               dict(anchor=label,two_rule_pass_count=len(group),front_count=len(anchors['front']),
                                    decision_status='method_demo_only_not_validated_recommendation'))
        for r in anchors['front']:
            fronts.append({k:r[k] for k in ['case_id','grid_ef','lithium_price_usd','energy_efficiency','green_ratio','process_mix','gwp_kgco2e','lcor_rmb_per_t']})
    csv_write(OUT/'conditional_anchors.csv',conditional); csv_write(OUT/'conditional_fronts.csv',fronts)
    representatives=[dict(role='B原全局成本锚点',case_id=global_anchors['cost']['case_id']),
                     dict(role='B原全局折衷锚点',case_id=global_anchors['compromise']['case_id']),
                     dict(role='B原环境锚点首个同值工况',case_id=original_env['case_id'])]
    for x in conditional:
        if (x['grid_ef'],x['lithium_price_usd'],x['energy_efficiency'])==(.556,22000.,1.):
            representatives.append(dict(role='固定外部情景_'+x['anchor'],case_id=x['case_id']))
    lookup={r['case_id']:r for r in rows}; costmap={r['case_id']:r for r in costs}
    for rep in representatives:
        rep.update({k:lookup[rep['case_id']][k] for k in ['green_ratio','process_mix','grid_ef','lithium_price_usd','energy_efficiency','gwp_kgco2e','water_l','lcor_rmb_per_t','c_diagnostic_policy_status']})
    csv_write(OUT/'representatives.csv',representatives)

    price_summary=[]
    for price in sorted({r['lithium_price_usd'] for r in rows}):
        vals=sorted(r['lcor_rmb_per_t'] for r in feasible if r['lithium_price_usd']==price)
        price_summary.append(dict(price_usd_per_t=price,count=len(vals),minimum=min(vals),
                                  median=(vals[(len(vals)-1)//2]+vals[len(vals)//2])/2,maximum=max(vals),
                                  interpretation='B局部净成本，非完整项目利润'))
    csv_write(OUT/'price_summary.csv',price_summary)
    # 抽取表格使用整数显示；允许半单位四舍五入误差，绝不以它替代完整CSV。
    wb=load_workbook(sources[1],data_only=True,read_only=True)
    extract_checks=[]
    for row in list(wb['B推荐工况'].values)[1:]:
        rr=lookup[int(row[1])]
        for j,col in [(8,'lcor_rmb_per_t'),(9,'gwp_kgco2e'),(10,'water_l')]:
            delta=float(row[j])-rr[col]
            extract_checks.append(dict(case_id=rr['case_id'],metric=col,workbook_value=row[j],csv_value=rr[col],difference=delta,
                                       matches_display_rounding=abs(delta)<=.5000001))
    wb.close(); csv_write(OUT/'extracted_workbook_checks.csv',extract_checks)
    historical=[r for r in csv_read(A/'data_cohort/literature_parameters.csv') if r['record_id'].startswith('W-') or r['record_id'].startswith('J-T7')]
    csv_write(OUT/'a_literature_reference_only.csv',historical)
    source_register=csv_read(A/'data_cohort/source_registry.csv')
    csv_write(OUT/'a_source_registry_received.csv',source_register)
    # 经济模板只承接已经确认的规模，不把20,000t历史线数据外推到8万吨园区。
    case=json.loads((ROOT/'data_cohort/tea_case_template.json').read_text(encoding='utf-8'))
    case['integration_status']='A_process_inputs_missing_B_costs_placeholder'
    case['reuse_application_review']=evaluate_reuse_application(dict(evaluation_date='2026-11-03',has_reuse_branch=True))
    json_write(OUT/'tea_case_ready_for_data.json',case)
    missing=completion_check(case)
    gaps=[dict(priority='P0',owner='A',item='包/模组/电芯/黑粉/LCE物质流及分支产品',impact='决定年产量、单耗和每吨LCE分母',status='未提供完整MFA'),
          dict(priority='P0',owner='C+A',item='CAPEX分项、运营年限、实际折现率、年负荷',impact='计算资本年金；不能按原型总投资比例缩放',status='缺失'),
          dict(priority='P0',owner='C',item='采购及运输、公辅试剂、人工治理税费与产品报价',impact='完整OPEX及收入；B固定值仅为占位',status='缺失'),
          dict(priority='P0',owner='A+B',item='混合/直接修复的功能等效、补锂和产品分配',impact='不能把修复材料全部当成可售Li2CO3',status='缺失'),
          dict(priority='P0',owner='C+A',item='1万吨再使用用途、适用标准及质量证据',impact='现行政策用途核对；分流预算仍保留',status='UNKNOWN'),
          dict(priority='P1',owner='B',item='因子来源、华中基准、区域水因子和配电边界',impact='目前0.556不能称为华中已核LCA因子',status='待校准'),
          dict(priority='P1',owner='B+C',item='原生对照同功能成本及排放',impact='完整MAC不可计算',status='缺失'),
          dict(priority='P1',owner='C',item='2026不变价人民币与汇率/指数证据',impact='B的7.2无现价证据',status='待确认')]
    csv_write(OUT/'missing_inputs.csv',gaps)
    summary=dict(scenarios=len(rows),b_two_rule_pass=len(feasible),b_two_rule_fail=len(rows)-len(feasible),
                 max_reproduction_absolute_error=dict(maxerr),external_groups=len(groups),
                 c_diagnostic_policy_counts=dict(Counter(r['c_diagnostic_policy_status'] for r in rows)),
                 formal_tea_ready=0,formal_tea_missing_field_count=len(missing),missing_tea_fields=missing,
                 original_environment_anchor_id=original_env['case_id'],
                 original_environment_anchor_dominated=any(r['gwp_kgco2e']<=original_env['gwp_kgco2e'] and r['lcor_rmb_per_t']<=original_env['lcor_rmb_per_t'] and
                      (r['gwp_kgco2e']<original_env['gwp_kgco2e'] or r['lcor_rmb_per_t']<original_env['lcor_rmb_per_t']) for r in feasible),
                 b_global_compromise_id=global_anchors['compromise']['case_id'],
                 reuse_policy_status=case['reuse_application_review'],source_files_unchanged=True)
    for entry in manifest:
        if hashlib.sha256((WORK/entry['path']).read_bytes()).hexdigest()!=entry['sha256']:
            raise RuntimeError('源文件发生变化')
    json_write(REPORT/'summary.json',summary)
    json_write(REPORT/'workbook_payload.json',dict(summary=summary,representatives=representatives,price_summary=price_summary,
                 conditional=conditional,costs=[costmap[r['case_id']]|{'role':r['role']} for r in representatives],gaps=gaps,
                 missing_fields=missing,extract_checks=extract_checks,
                 sources=[dict(source_id=r['source_id'],title=r['title'],url=r['url']) for r in source_register if r['source_id'] in ['LIT-WANG2024','LIT-JIANG2024','S_UPDATE2026','S_RULE_73']]))
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
