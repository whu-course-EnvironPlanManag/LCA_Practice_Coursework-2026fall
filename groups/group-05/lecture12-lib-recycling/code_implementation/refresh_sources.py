"""AI辅助：核验原始政策与论文元数据并留存下载状态。人工校验待组员确认。"""
from pathlib import Path
import urllib.request,json,hashlib,concurrent.futures
D=Path(__file__).resolve().parents[1]/'data_cohort';R=D/'raw_current';R.mkdir(exist_ok=True)
S={
'MIIT2024': 'https://jxt.hubei.gov.cn/bmdt/rdjj/202412/P020241228550305312661.pdf',
'MIIT2026_20':'https://wap.miit.gov.cn/jgsj/jns/zhlyh/art/2026/art_68252019ef6648f886b2c070ef8ced02.html',
'MIIT2026_73':'https://www.miit.gov.cn/gyhxxhb/jgsj/cyzcyfgs/bmgz/jdcjxl/art/2026/art_392462fdc40c415ea4a4129cac3028c2.html',
'EU2026':'https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:02023R1542-20260813',
'GRID2024':'https://www.mee.gov.cn/xxgk2018/xxgk/xxgk01/202510/W020251024569470952545.pdf',
'KELLY2021':'https://www.osti.gov/servlets/purl/1868964',
'YOUMEI_EIA':'https://sthjj.gz.gov.cn/gkmlpt/content/9/9802/post_9802113.html',
'YOUMEI_ENERGY':'https://fgw.gz.gov.cn/tzgg/xmgg/content/post_9843213.html',
'HUADU':'https://www.huadu.gov.cn/xxgk/zdxm/content/post_10213799.html',
}
DOIS=['10.1038/s41467-024-54634-y','10.1038/s41560-024-01701-9','10.1038/s43247-024-01667-2','10.1038/s41467-025-56063-x','10.1038/s41467-025-61481-y','10.1038/s41467-024-52030-0','10.1016/j.resconrec.2021.105762','10.1038/s43247-026-03643-4']
for i,doi in enumerate(DOIS):S['CROSSREF'+str(i+1)]='https://api.crossref.org/works/'+doi
S['OPENALEX']='https://api.openalex.org/works?search=lithium%20battery%20recycling&per-page=5'
def get(kv):
 k,url=kv
 existing=list(R.glob(k+'.*'))
 if existing and existing[0].stat().st_size>0:
  p=existing[0];b=p.read_bytes();return dict(id=k,url=url,checked='2026-11-04',status='downloaded',path=str(p.relative_to(D)),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
 r={'id':k,'url':url,'checked':'2026-11-04'}
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'Academic coursework source verification/1.0'})
  with urllib.request.urlopen(req,timeout=40) as f:b=f.read();ct=f.headers.get('Content-Type','')
  if not b or ('pdf' in url.lower() and not b.startswith(b'%PDF')):raise ValueError('empty or non-PDF response')
  ext='.pdf' if b.startswith(b'%PDF') else '.json' if k.startswith(('CROSSREF','OPENALEX')) else '.html'
  p=R/(k+ext);p.write_bytes(b);r.update(status='downloaded',path=str(p.relative_to(D)),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
 except Exception as e:r.update(status='unavailable',error=str(e))
 return r
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:rows=list(ex.map(get,S.items()))
(D/'current_source_manifest.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
for r in rows:print(r['id'],r['status'])
# Bibliography from Crossref, retaining exact metadata.
bib=[];audit=[]
for i,doi in enumerate(DOIS):
 p=R/f'CROSSREF{i+1}.json'
 if not p.exists():continue
 m=json.loads(p.read_text())['message'];authors=' and '.join(x.get('family','')+', '+x.get('given','') for x in m.get('author',[]));year=m.get('published',m.get('issued',{}))['date-parts'][0][0]
 fields={'author':authors,'title':m['title'][0],'journal':m.get('container-title',[''])[0],'year':str(year),'volume':m.get('volume',''),'pages':m.get('page',m.get('article-number','')).replace('-', '--'),'doi':doi,'url':'https://doi.org/'+doi}
 bib.append('@article{Ref'+str(i+1)+',\n'+',\n'.join('  '+k+' = {'+str(v)+'}' for k,v in fields.items() if v)+'\n}')
 audit.append({'doi':doi,'missing':[k for k,v in fields.items() if not v]})
(D/'references.bib').write_text('\n\n'.join(bib));(D/'bibliography_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2))
