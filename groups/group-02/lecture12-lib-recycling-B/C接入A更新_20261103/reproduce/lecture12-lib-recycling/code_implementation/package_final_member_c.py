"""Package the C conditional delivery and a minimal, explicitly scoped reproduction snapshot."""
from pathlib import Path
import csv,json,shutil,subprocess,sys,hashlib
from finalize_member_c import ROOT,A,B,DATA,REPORT,DELIVERY

def main():
    result=subprocess.run([sys.executable,'-m','unittest','discover','-s','code_implementation','-p','test_*.py','-v'],cwd=ROOT,capture_output=True,text=True)
    (REPORT/'test_results.txt').write_text(result.stdout+result.stderr,encoding='utf-8')
    if result.returncode:raise RuntimeError('Tests failed')
    summary=json.loads((REPORT/'summary.json').read_text(encoding='utf-8'))
    rows=list(csv.DictReader((DATA/'conditional_scenarios.csv').open(encoding='utf-8-sig')))
    assert len(rows)==5148 and summary['source_files_unchanged']
    assert summary['actual_LCE_output_t_a'] is None and summary['MAC'] is None
    note='''# 给A和B的接口与结果说明

2026-11-03；成员C交付归属说明。

LCOR/TEA模型、经济参数、政策参数、规则引擎和典型/边界测试由C负责。A提供规模、物质流、产品与活动量；B提供LCA因子、环境核算与情景比较。B调用C接口并不改变C对自身模型和参数的责任。

当前B交接表3267行的c_tea_status均为PROVISIONAL_SYNTHETIC_LCOR。B代码中的临时合成公式用于接口演示，不能仅因存在C接口就视为C最终核算结果。本轮C未采用该列作为经济结果，而是使用自身TEA与显式财务假设另算。部分政策分支在方法测试中按阈值填值，PASS只反映测试输入；项目缺少实测指标时C保持UNKNOWN。此处区分文件版本和计算来源，不将临时数值归责于任何成员。

正式替换接口需要A提供同一运行负荷下各产品年产量（含LCE）、商业规格、各公用工程和药剂量、分流后的物料守恒；B与C统一功能单位、系统边界、联产品分配，以及逐情景活动量和电网/绿电因子。政策指标须提供分子、分母、年份、适用工艺及证据，不能只提供PASS。

本轮C先完成条件财务分析：LCE产量是显式变量；未核实其他产品不计参照回款，用所需额外净贡献表达差额。无完整同口径原生路线成本与排放，不给出实证MAC。代码tea_model.py与policy_engine.py属于C贡献；A/B原始文件保留不改。
'''
    (REPORT/'给A和B的接口与结果说明.md').write_text(note,encoding='utf-8')
    contribution='''# C最终贡献与验收记录

日期：2026-11-03。成员归属：C。AI辅助整理、编码、计算和文档生成；未代填本人签名或声称已由本人手工审阅确认。

- 经济参数与来源审计保留原记录；含税报价、日期/适用条件未核实项继续显式标记，未自动计补贴、退税或出口溢价。
- 提供参数化TEA、政策引擎、用途核查与典型/阈值测试。本轮46项自动测试全部通过，日志test_results.txt。
- 接续A最新市域历史队列dMFA与组成清单，区分城市队列释放量、园区设计规模和真实物料处理量。
- 接续B活动量代理和环境因子；识别临时合成LCOR与阈值填充，逐情景显式传递C输入，完成5148组条件扫描。
- 交付投资费用表、现金覆盖与价格传导分析、条件绿电比较、队列规模图4张300DPI图片；更新第3/5/6章衔接文字，提供Word/Markdown提交稿和管理安排。
- A/B源文件前后SHA256清单一致；不改写原成果。最小复现快照仅包含本轮必要输入及来源代码，不冒称包含A/B完整资料包。

验收边界：真实全厂LCE产量、联产品收入及分配、完整工程量与质量/许可证据尚未齐备。真实利润、完整项目合规和实证MAC不作已完成结论；本轮完成的是有明确假设的课程条件交付。
'''
    (REPORT/'C最终贡献与验收记录.md').write_text(contribution,encoding='utf-8')
    validation={'tests':46,'tests_passed':True,'conditional_rows':len(rows),'source_files_unchanged':True,'B_synthetic_LCOR_used':False,'confirmed_policy_feasible':0,'actual_project_profit':None,'actual_LCE_output_t_a':None,'MAC':None,'status':'CONDITIONAL_C_DELIVERY','PDF_visual_review':'7 pages inspected; independent ReportLab PDF','DOCX_visual_review':'NOT_COMPLETED: native Word export stalled; editable draft only'}
    (REPORT/'final_validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2),encoding='utf-8')
    for p in DATA.iterdir():
        if p.is_file():shutil.copy2(p,DELIVERY/p.name)
    for name in ['summary.json','conditional_baseline_results.json','final_validation.json','test_results.txt','给A和B的接口与结果说明.md','C最终贡献与验收记录.md']:
        shutil.copy2(REPORT/name,DELIVERY/name)
    for name in ['ch03_indicators.md','ch05_economics.md','ch06_management.md']:
        target=DELIVERY/'章节补充'/name;target.parent.mkdir(exist_ok=True);shutil.copy2(ROOT/'report/drafts'/name,target)
    snap=DELIVERY/'reproduce';croot=snap/ROOT.name
    for p in (ROOT/'code_implementation').rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts:
            target=croot/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
    for name in ['economic_parameters_received.csv','economic_parameters_revised_20261103.csv','policy_parameters.json','tea_case_template.json']:
        p=ROOT/'data_cohort'/name
        if p.exists():
            target=croot/'data_cohort'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
    target=croot/'data_cohort/final_integration_20261103/C_final_assumptions.json';target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(DATA/target.name,target)
    for name in ['ch03_indicators.md','ch05_economics.md','ch06_management.md']:
        target=croot/'report/drafts'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/'report/drafts'/name,target)
    for base,names in [(A,['data_cohort/dmfa_yichang_annual_total.csv','data_cohort/dmfa_yichang_summary.csv','data_cohort/received_component_inventory.csv','data_cohort/engineering_project_catalog.csv','data_cohort/capacity_interfaces.csv']), (B,['data_cohort/scenario_results.csv','data_cohort/environmental_factors.csv','data_cohort/parameter_override.json','code_implementation/scenario_analysis.py','code_implementation/c_interface.py','code_implementation/lca_model.py','code_implementation/a_candidate_override.py'])]:
        for name in names:
            p=base/name
            if p.exists():
                target=snap/base.relative_to(ROOT.parent)/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
    (snap/'requirements_final.txt').write_text('reportlab\npypdfium2\npython-docx\nPillow\n',encoding='utf-8')
    readme='''# C最终交付入口

先打开C成员经济与管理交付稿.pdf，7页已逐页检查；DOCX为同内容可编辑稿，Word导出停滞且电脑操作通道不可用，未完成Word版式核查，不冒称其已验版。PDF独立生成，不是Word版式的验证。Markdown为可编辑文字源。figures目录是本轮C6—C9四张图。conditional_scenarios.csv为5148组条件结果，其余CSV为费用、政策和边界表。

给A和B的接口与结果说明.md说明LCOR及政策指标归属和临时结果状态；C最终贡献与验收记录.md记录C工作和未闭合事项。章节补充中保留完整第3/5/6章方法与管理内容；最新定量口径以主提交稿为准，不混用历史快照。

本包是条件课程仿真成果。年LCE3000吨是财务情景，非A确认产量；不将单独锂盐回款差额称为园区亏损；未确认项目合规、真实利润或实证MAC。

复现：Python 3.11及以上，安装reproduce/requirements_final.txt中的依赖，进入reproduce/lecture12-lib-recycling，依次运行：

    python code_implementation/finalize_member_c.py
    python code_implementation/plot_final_member_c.py
    python code_implementation/write_final_report.py
    python code_implementation/build_final_docx.py
    python code_implementation/build_final_pdf.py
    python -m unittest discover -s code_implementation -p "test_*.py" -v

复现快照保留所需A/B嵌套相对目录；A/B仅为必要输入子集。重新生成文档后应再次检查版式。
'''
    (DELIVERY/'README.md').write_text(readme,encoding='utf-8')
    figures_index=ROOT/'figures_output/README.md'
    text=figures_index.read_text(encoding='utf-8') if figures_index.exists() else ''
    marker='\n## 2026-11-03 最新C条件交付\n'
    text=text.split(marker)[0]+marker+'\n本轮使用fig_c6_final_cost_coverage.png、fig_c7_final_price_link.png、fig_c8_final_conditional_front.png、fig_c9_final_cohort_scale.png。均为300DPI；对应主提交稿见outputs/C最终交付_20261103。旧图保留为历史阶段记录，勿将临时合成LCOR作为最终经济值。\n'
    figures_index.write_text(text,encoding='utf-8')
    manifest=[{'path':str(p.relative_to(DELIVERY)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in DELIVERY.rglob('*') if p.is_file() and p.name!='delivery_manifest.json']
    (DELIVERY/'delivery_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    archive=shutil.make_archive(str(DELIVERY),'zip',root_dir=DELIVERY.parent,base_dir=DELIVERY.name)
    print(archive)

if __name__=='__main__':main()
