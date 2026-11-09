"""AI-assisted contribution evidence; no invented signatures, hours or Git commits."""
import argparse
import difflib
import hashlib
import json
import shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'report/review_20261103'
TARGETS=['report/drafts/ch03_indicators.md','report/drafts/ch05_economics.md',
         'report/drafts/ch06_management.md','code_implementation/prepare_economic_case.py',
         'data_cohort/tea_accounting_assumptions.json']

def manifest():
    items={}
    for base in ['code_implementation','data_cohort','report/drafts','figures_output','report/review_20261103']:
        for p in (ROOT/base).rglob('*'):
            if p.is_file() and not any(x in p.parts for x in ['__pycache__','node_modules']):
                if 'review_20261103' in p.parts and ('before' in p.parts or p.name in ['before_manifest.json','after_manifest.json','file_changes.json','review_changes.diff']):
                    continue
                items[p.relative_to(ROOT).as_posix()]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
    return items

def main():
    a=argparse.ArgumentParser();a.add_argument('phase',choices=['before','after']);args=a.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    dest=OUT/f'{args.phase}_manifest.json'
    if args.phase=='before' and dest.exists():raise ValueError('审阅前基线已存在，不覆盖历史证据')
    current=manifest()
    dest.write_text(json.dumps({'date':'2026-11-03','timezone':'Asia/Shanghai','files':current},ensure_ascii=False,indent=2),encoding='utf-8')
    if args.phase=='before':
        for name in TARGETS:
            dst=OUT/'before'/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,dst)
    else:
        old=json.loads((OUT/'before_manifest.json').read_text(encoding='utf-8'))['files']
        changes=[]
        for name in sorted(set(old)|set(current)):
            if old.get(name)!=current.get(name):
                changes.append({'path':name,'change':'added' if name not in old else 'removed' if name not in current else 'modified',
                                'before':old.get(name),'after':current.get(name)})
        (OUT/'file_changes.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2),encoding='utf-8')
        patches=[]
        for name in TARGETS:
            before=(OUT/'before'/name).read_text(encoding='utf-8-sig').splitlines(keepends=True)
            after=(ROOT/name).read_text(encoding='utf-8-sig').splitlines(keepends=True)
            patches.extend(difflib.unified_diff(before,after,fromfile='before/'+name,tofile='after/'+name))
        (OUT/'review_changes.diff').write_text(''.join(patches),encoding='utf-8')
        print('Changed/added project evidence files:',len(changes))
    print(dest)

if __name__=='__main__':main()
