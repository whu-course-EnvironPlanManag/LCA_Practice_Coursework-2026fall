"""AI辅助。Prompt：检查图文引用、DPI、章节、源数据一致性、禁用修辞与个人标识。人工验收待小组完成。"""
from pathlib import Path
import json,re,csv,hashlib
from PIL import Image
B=Path(__file__).resolve().parents[1];R=B/'report';D=B/'data_cohort';O=D/'model_results'

def main():
    text=(R/'Environmental_Planning_Report.md').read_text();checks=[]
    def check(name,ok):checks.append({'check':name,'status':'PASS' if ok else 'FAIL'});assert ok,name
    figures=json.loads((B/'figures_output/figure_manifest.json').read_text())
    for r in figures:
        p=B/'figures_output'/(r['file']+'.png');im=Image.open(p)
        check(r['file']+'_dpi',min(im.info.get('dpi',(0,0)))>=300)
        check(r['file']+'_reference',r['file']+'.png' in text)
        check(r['file']+'_vector',(p.with_suffix('.pdf')).exists())
    for title in ['模块0','第1章','第2章','第3章','第4章','第5章','第6章','第7章']:check('chapter_'+title,title in text)
    for target in re.findall(r'\]\(([^)]+)\)',text):
        if not target.startswith(('http:','https:','#')):check('link_'+target,(R/target).exists())
    banned=['城市矿山','退役潮洪峰','井喷式增长','双刃剑','甜点','领头羊','排头兵','压舱石','两张皮','卡脖子','香饽饽','硬骨头','小作坊游击队','吃干榨净','变废为宝','绿色名片','护城河','组合拳','定海神针']
    check('科学语气禁词',not any(x in text for x in banned))
    check('无学号字段值',not re.search(r'学号\s*[:：|]\s*\d+',text))
    check('成员分工表已列明',all(x in text for x in ['团队成员分工与贡献度声明','张晓璐','明子骅']))
    v=json.loads((O/'verification.json').read_text());t=json.loads((O/'tests_summary.json').read_text())
    check('守恒误差',v['stock_error_pct']<.05 and v['process_error_pct']<.05)
    check('工况数量',v['scenarios']>=500)
    check('工程账目',abs(v['project_CAPEX_difference'])<.01 and abs(v['project_OPEX_difference'])<.01)
    check('测试通过',t['failed']==0 and t['total']>=3)
    if (R/'广州A方案_离线阅读版.html').exists():check('自包含HTML图表',(R/'广州A方案_离线阅读版.html').read_text().count('data:image/png;base64,')==len(figures))
    summary=json.loads((R/'report_generation.json').read_text());check('摘要汉字数',400<=summary['summary_hanzi']<=600)
    hashes=[]
    for folder in ['code_implementation','figures_output','report']:
        for p in sorted((B/folder).rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts and p.name not in ['delivery_checks.json','delivery_manifest.csv','validation_run.log']:
                hashes.append({'path':str(p.relative_to(B)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    with (R/'delivery_manifest.csv').open('w',encoding='utf-8-sig',newline='') as out:
        w=csv.DictWriter(out,fieldnames=list(hashes[0]));w.writeheader();w.writerows(hashes)
    (R/'delivery_checks.json').write_text(json.dumps({'passed':len(checks),'failed':0,'checks':checks},ensure_ascii=False,indent=2));print('DELIVERY PASS',len(checks))
if __name__=='__main__':main()
