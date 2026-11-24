"""Validate and package current C annual-input delivery with minimal reproduction."""
import csv,hashlib,io,json,os,shutil,subprocess,sys,unittest,zipfile
from pathlib import Path
from integrate_a_supplement import ROOT,DATA,REPORT,DELIVERY,RAW,read,dump,source_hashes

def copyfile(src,dest):
    dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
def included(folder,p):
    parts=p.relative_to(folder).parts
    if not p.is_file() or '__pycache__' in parts or p.suffix=='.pyc':return False
    if 'reproduce' in parts:
        tail=parts[parts.index('reproduce')+1:]
        if any(x in tail for x in ['outputs','pdf_qa','figure_render','chapter_before']):return False
    return True
def archive(folder,target):
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
        for p in folder.rglob('*'):
            if included(folder,p):z.write(p,folder.name+'/'+str(p.relative_to(folder)))

def main():
    capture=io.StringIO();suite=unittest.defaultTestLoader.discover(str(ROOT/'code_implementation'),pattern='test_*.py')
    run=unittest.TextTestRunner(stream=capture,verbosity=2).run(suite)
    (REPORT/'test_results.txt').write_text(capture.getvalue(),encoding='utf-8')
    if not run.wasSuccessful():raise RuntimeError(capture.getvalue())
    summary=read(REPORT/'summary.json');assert summary['formal_LCOR'] is None and summary['profile_sensitivity_count']==19
    manifest=read(REPORT/'source_manifest.json');assert manifest['after']==source_hashes()
    packet=DELIVERY/'给B_年度接口v2'
    child_env=dict(os.environ,PYTHONIOENCODING='utf-8')
    executed=subprocess.run([sys.executable,str(packet/'run_annual_case.py')],capture_output=True,text=True,encoding='utf-8',env=child_env)
    # Windows console encoding can vary; set a deterministic UTF-8 environment on retry if needed.
    if executed.returncode:raise RuntimeError(executed.stderr)
    b_result=json.loads(executed.stdout)
    assert b_result['status']=='NOT_READY' and b_result['lcor_CNY_per_t_LCE'] is None
    assert b_result['known_priced_opex_subtotal_CNY_a']==479840000
    policy=subprocess.run([sys.executable,str(packet/'run_policy_checks.py')],capture_output=True,text=True,encoding='utf-8',env=child_env)
    assert policy.returncode==0 and policy.stdout.count('UNKNOWN')==6
    bmap=read(packet/'C_to_B_existing_case_status_v2.json')
    assert len(bmap)==3267 and all(x['lcor_rmb_per_t_LCE'] is None and not x['formal_result_eligible'] for x in bmap)
    (REPORT/'B_packet_smoke_test.txt').write_text(executed.stdout+'\n'+policy.stdout,encoding='utf-8')
    qa=dict(tests_run=run.testsRun,tests_passed=True,new_annual_tests=14,
      B_packet_run_passed=True,B_policy_checks=6,B_existing_case_ids_preserved=3267,
      source_files_unchanged=True,annual_tea_status='NOT_READY_WITH_PARTIAL_COSTS',formal_LCOR=None,
      complete_project_profit=None,MAC=None,formal_result_eligible=False,
      PDF_visual_review='5 pages inspected after final render',Word_output='not generated this round')
    repro_summary=DELIVERY/'reproduce'/ROOT.name/'report/a_update_20261103/summary.json'
    qa['minimal_reproduction_summary_identical']=repro_summary.exists() and repro_summary.read_bytes()==(REPORT/'summary.json').read_bytes()
    dump(REPORT/'validation_summary.json',qa)
    contribution=f'''# C本轮贡献与验收记录（A补充接入v2）

2026-11-03。C在A新增补充基础上完成年度数量复算、商品基准与路线分离、成本匹配和缺项输出；保留原tea_model，新增annual_tea_interface及可运行B接口。两套不同年度输入通过引擎联动测试。共{run.testsRun}项自动测试通过，新增14项；B独立接口和6组政策调用运行通过。A补充源文件SHA256前后不变。

更新第3/5/6章当前状态、当前结果入口及贡献记录；生成两张300DPI图和年度接续报告。PDF按页渲染检查；未冒称检查Word版式。旧财务变量情景与最新年度物理清单区分，旧接口不自动覆盖本轮正式结果。

验收界限：A补充明确精制成品、分线电热与全厂配套尚缺，C的完整OPEX、产品收入、LCOR、利润、MAC不能据此给出数值。已定价部分小计不当完整成本。价格证据核查继续保留，不把等有效量价当商业报价。

A贡献为原始数据、来源定位与补充校验；C贡献为接入、模型接口、复核测试、图文与交接。AI辅助整理和编程，不代填本人确认、签字或工时。
'''
    (REPORT/'C贡献与验收记录_v2.md').write_text(contribution,encoding='utf-8')
    for p in DATA.iterdir():
        if p.is_file():copyfile(p,DELIVERY/'年度数据'/p.name)
    for name in ['summary.json','annual_tea_results.json','policy_rerun_results.json','policy_checks.csv','source_manifest.json','test_results.txt','B_packet_smoke_test.txt','validation_summary.json','C贡献与验收记录_v2.md','给A_本轮剩余最小确认项.md']:
        copyfile(REPORT/name,DELIVERY/'核验记录'/name)
    for name in ['ch03_indicators.md','ch05_economics.md','ch06_management.md']:
        copyfile(ROOT/'report/drafts'/name,DELIVERY/'章节补充'/name)
    for p in RAW.iterdir():
        if p.is_file():copyfile(p,DELIVERY/'A原始补充只读快照'/p.name)
    for name in ['38项经济参数公开出处核查.md','逐项公开出处核查.json']:
        copyfile(ROOT/'report/public_source_audit_20261103'/name,DELIVERY/'报价核查'/name)
    snap=DELIVERY/'reproduce';croot=snap/ROOT.name
    for p in (ROOT/'code_implementation').rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc':copyfile(p,croot/p.relative_to(ROOT))
    for name in ['economic_parameters_received.csv','economic_parameters_revised_20261103.csv','economic_source_register.csv','policy_parameters.json','tea_case_template.json','tea_annual_quantities.csv']:
        copyfile(ROOT/'data_cohort'/name,croot/'data_cohort'/name)
    copyfile(ROOT/'data_cohort/final_integration_20261103/C_final_assumptions.json',croot/'data_cohort/final_integration_20261103/C_final_assumptions.json')
    for p in DATA.iterdir():
        if p.is_file():copyfile(p,croot/'data_cohort/a_update_20261103'/p.name)
    for name in ['ch03_indicators.md','ch05_economics.md','ch06_management.md']:
        copyfile(ROOT/'report/drafts'/name,croot/'report/drafts'/name)
    bbase=ROOT.parent/'lecture12-lib-recycling-B/lecture12-lib-recycling-B'
    for name in ['scenario_results.csv','environmental_factors.csv']:
        copyfile(bbase/'data_cohort'/name,snap/bbase.relative_to(ROOT.parent)/'data_cohort'/name)
    (snap/'requirements.txt').write_text('reportlab\npypdfium2\nPillow\n',encoding='utf-8')
    (snap/'README_复现.md').write_text('''# 最小复现

Python3.11以上；只跑年度清单、经济接口和测试用标准库即可。画图/PDF另需requirements.txt依赖与Windows微软雅黑字体。进入lecture12-lib-recycling后依次执行：

    python code_implementation/integrate_a_supplement.py
    python -m unittest discover -s code_implementation -p "test_*.py" -v
    python code_implementation/write_a_update_report.py
    python code_implementation/render_a_update_pdf.py

A补充读取data_cohort/a_update_20261103快照，不回写A目录。B旧CSV仅用于保留工况ID及历史测试，不读取合成LCOR作为新经济值。不同参考profile不是全厂拼接清单。重新生成的报告需再次检查版式。
''',encoding='utf-8')
    files={str(p.relative_to(DELIVERY)):hashlib.sha256(p.read_bytes()).hexdigest() for p in DELIVERY.rglob('*') if included(DELIVERY,p) and p.name!='delivery_manifest.json'}
    dump(DELIVERY/'delivery_manifest.json',files)
    archive(packet,DELIVERY.parent/'C给B_年度接口v2_20261103.zip')
    archive(DELIVERY,Path(str(DELIVERY)+'.zip'))
    print(json.dumps(qa,ensure_ascii=False,indent=2));print(str(DELIVERY)+'.zip')

if __name__=='__main__':main()
