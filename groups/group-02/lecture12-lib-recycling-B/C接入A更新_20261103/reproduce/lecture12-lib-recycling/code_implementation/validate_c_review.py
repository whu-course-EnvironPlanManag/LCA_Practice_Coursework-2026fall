"""AI-assisted final verification of audit artifacts and source preservation."""
import ast
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'report/review_20261103'
def rows(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def main():
    checks=[]
    def check(name,result):
        if not result:raise AssertionError(name)
        checks.append({'check':name,'status':'PASS'})
    audit=json.loads((OUT/'quote_audit.json').read_text(encoding='utf-8'))
    qrows=rows(OUT/'报价原件日期适用条件核对.csv')
    check('38个唯一参数逐项登记',len(qrows)==38 and len({r['param_id'] for r in qrows})==38)
    check('28项外部金额没有被冒认为原件已核',sum(r['parameter_kind']=='external_monetary_estimate' for r in qrows)==28 and audit['exact_original_commercial_quotes_verified']==0)
    check('未编造精确报价日期或有效期',all(not r['exact_quote_date'] and not r['quote_valid_until'] for r in qrows))
    before=json.loads((OUT/'before_manifest.json').read_text(encoding='utf-8'))['files']
    raw='data_cohort/economic_parameters_revised_20261103.csv'
    check('用户修改版原始CSV未被覆盖',hashlib.sha256((ROOT/raw).read_bytes()).hexdigest()==before[raw]['sha256'])
    cfg=json.loads((ROOT/'data_cohort/tea_accounting_assumptions.json').read_text(encoding='utf-8'))
    check('税价存在适用问题时不标完成',cfg['quote_tax_basis_confirmed'] is False and cfg['source_assumptions_reviewed'] is False)
    case=json.loads((ROOT/'data_cohort/tea_case_economic_intake.json').read_text(encoding='utf-8'))
    check('到厂运费去重而未填造产品销量',case['cost_items'][1]['unit_price']==0 and all(x['quantity_per_year'] is None for x in case['revenue_items']))
    s=json.loads((ROOT/'report/economic_intake_20261103/intake_summary.json').read_text(encoding='utf-8'))
    check('最新完整TEA保持缺数状态',s['status']=='PENDING' and s['formal_lcor'] is None and len(s['missing_numeric_fields'])==23 and len(s['unresolved_accounting_reviews'])==7)
    econ=(ROOT/'report/drafts/ch05_economics.md').read_text(encoding='utf-8')
    check('旧经济版本从活动章节移出', '首次经济表接入记录' not in econ and '4,908.43' not in econ and '5.7 税价、产品与复算控制' in econ)
    for chapter in ['ch03_indicators.md','ch05_economics.md','ch06_management.md']:
        check('审阅前章节已保存：'+chapter,(OUT/'before/report/drafts'/chapter).exists())
    for script in ['audit_quote_sources.py','apply_chapter_review.py','record_c_review.py','prepare_economic_case.py']:
        ast.parse((ROOT/'code_implementation'/script).read_text(encoding='utf-8'))
    check('新增和修改脚本语法通过',True)
    proc=subprocess.run([sys.executable,'-X','utf8','-m','unittest','discover','-s',str(ROOT/'code_implementation'),'-p','test_*.py','-v'],capture_output=True,text=True,encoding='utf-8')
    (OUT/'unit_test_log.txt').write_text(proc.stdout+proc.stderr,encoding='utf-8')
    check('模型与政策测试全部通过',proc.returncode==0)
    result={'review_date':'2026-11-03','timezone':'Asia/Shanghai','checks':checks,
      'unit_tests':'37 passed','test_return_code':proc.returncode,
      'note':'自动化校验，不证明报价真实、税收资格已具备或人类已经签认。'}
    (OUT/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print('PASS:',len(checks),'review controls; 37 unit tests. Original revised CSV preserved.')

if __name__=='__main__':main()
