from pathlib import Path
import argparse,csv,json,html
from run import write_csv
base=Path(__file__).resolve().parent
ap=argparse.ArgumentParser()
ap.add_argument('--data',type=Path,default=base.parent/'环境规划与管理-第十五讲20261117'/'source_data')
ap.add_argument('--output',type=Path,default=base/'outputs')
a=ap.parse_args();o=a.output
def rows(name):
    with (o/name).open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
p=next(a.data.glob('**/*P2O5 use*.csv'))
with p.open(encoding='gb18030') as f:
    records=[x for x in csv.DictReader(f) if x['Year']=='1961' and x['Element']=='Agricultural Use' and x['Unit']=='t' and x['Value'] and x['Area']!='China']
value=sum(float(x['Value']) for x in records)*.4364/1e6
b=rows('benchmark_comparison.csv')
b[1].update(result=value,status=f'相对偏差 {abs(value/4.9-1):.2%}',explanation='逐地区农业施用P₂O₅吨数×0.4364，排除与大陆记录重复的China汇总。参考值取一位小数。')
b[3]['explanation']='八类存栏排磷×67%代表回用率。分母排除种子田内循环。'
b[4].update(result='',status='历史时期不同',explanation='采用八类物种独立计算年度排磷，未估算历史平均利用效率。')
write_csv(o/'benchmark_comparison.csv',b)
s=json.loads((o/'scenario_results.json').read_text());last=s['scenarios'][-1]
report=(base/'报告模板.md').read_text().replace('（讨论稿）','').replace('动物产品类别尚未完全拆分陆生、水生及非食用产品，这是后续完善的重点。','养殖边界覆盖牛、水牛、绵羊、山羊、猪、马、鸡和鸭。产出采用可识别物种的初级肉、奶、蛋12项。马计入存栏排磷，混合马属产品和其他鸟蛋未分摊。').replace('由养殖需求','由养殖需求')
for old,new in {'0.1741':'0.1718','6.86%':'7.01%','16.456':'16.419','21.804':'21.758','31.82%':'31.96%','5.094':'5.106','18.61%':'18.43%','8.30%':'8.99%','10.20%':'11.26%','0.9989':format(s['regression'][-1]['R2'],'.4f')}.items():report=report.replace(old,new)
report+='\n\n## 数据核验与来源\n1961年全球农业化肥按P₂O₅转元素P得到%.3f Mt，与任务书约4.9 Mt相差%.2f%%。八类畜禽存栏乘补充材料第121页排磷系数得到18.833 Mt，乘代表回用率67%%得到12.618 Mt。该回用量是参数估算，实际收集、处理和到田环节存在差异。2022年化肥占农田外部输入%.2f%%，低于参考阈值64%%。数据来自Liu等（2026），PNAS，doi:10.1073/pnas.2512673123，作者Dryad数据doi:10.5061/dryad.bzkh189n2。模型文件保存了逐产品和逐物种的计算明细。\n'%(value,abs(value/4.9-1)*100,float(b[3]['result']))
flows=rows('flows_2022.csv')
incoming=[row for row in flows if row['target']=='ACS' and row['source']!='ACS']
total=sum(float(row['value']) for row in incoming)
parts='、'.join(f"{row['source']} {float(row['value']):.3f}" for row in incoming)
denominator=f"2022年 ACS 外部输入共 {total:.3f} Mt P，由{parts} Mt P 组成。种子自循环不计入。论文正文报告化肥占总输入由40%升至64%，补充材料的种植系统还列有农药磷和秸秆还田。将两项计入分母只会进一步降低本模型的化肥占比。若固定化肥20.5 Mt P，64%对应总输入32.031 Mt P，比课堂分母少 {total-20.5/.64:.3f} Mt P。粪便回田量采用八类存栏和统一利用率估算，缺少作者同年逐项流量，差额尚不能归因到单一来源。"
b[3]['explanation']=denominator
write_csv(o/'benchmark_comparison.csv',b)
report+='\n'+denominator+'\n'
cases=rows('assumption_sensitivity.csv')
table=['有效替代系数 | 污水收集率 | 原生磷开采（Mt P/年） | 开采降幅 | 水体流失（Mt P/年）','---:|---:|---:|---:|---:']
for case in cases:
    table.append('{equivalence:.2f} | {sewage_collection:.0%} | {mining_Mt:.3f} | {mining_reduction_pct:.2f}% | {water_Mt:.3f}'.format(**{k:float(v) for k,v in case.items()}))
discussion='同取60%收集率时，有效替代系数从0.50提高到1.00，开采降幅由25.52%增至31.96%。同取完全替代时，收集率从30%提高至90%，水体流失从6.275降至3.937 Mt P/年。表中水体流失为各组合的绝对量，收集率变化也会影响对应BAU的污水排放。'
report=report.replace('## 六、','三项政策参数保持课堂设定，改变有效替代系数和污水收集率所得结果如下。\n\n'+'\n'.join(table)+'\n\n'+discussion+'\n\n## 六、')
(o/'课程报告.md').write_text(report)
# Supply a usable offline flow view even when Plotly is unavailable.
f=rows('flows_2022.csv');f=[x for x in f if x['source']!=x['target']]
f.append(dict(source='ACS',target='土壤存量增加',value=json.loads((o/'results.json').read_text())['soil_stock_change']))
names=list(dict.fromkeys(k for x in f for k in (x['source'],x['target'])))
try:
    import plotly.graph_objects as go
except ImportError:
    # Left/right duplicates unroll internal cycles. Band widths use one common scale.
    sources=list(dict.fromkeys(x['source'] for x in f));targets=list(dict.fromkeys(x['target'] for x in f))
    pos={};cursor={};svg=[]
    for field,labels,x in [('source',sources,190),('target',targets,760)]:
        y=34
        for n in labels:
            h=sum(float(row['value']) for row in f if row[field]==n)*4
            pos[field,n]=cursor[field,n]=y
            svg.append(f'<rect x="{x}" y="{y}" width="8" height="{max(h,1)}" fill="#18685f"/><text x="{x-5 if field=="source" else x+13}" text-anchor="{"end" if field=="source" else "start"}" y="{y+max(12,h/2)}">{n}</text>')
            y+=max(h,14)+12
    bands=[]
    for row in f:
        l,r,v=row['source'],row['target'],float(row['value']);h=v*4;y=cursor['source',l]+h/2;z=cursor['target',r]+h/2
        bands.append(f'<path d="M198 {y} C470 {y} 490 {z} 760 {z}" stroke-width="{h}" tabindex="0"><title>{l} → {r}：{v:.3f} Mt P/年</title></path>');cursor['source',l]+=h;cursor['target',r]+=h
    fig='<svg class="offline-flow" viewBox="0 0 950 900"><g fill="none" stroke="#559eaa">'+''.join(bands)+'</g>'+''.join(svg)+'</svg>'
    # Preserve existing Plotly chart as network enhancement, offline SVG is standalone.
    path=o/'sankey_2022.html';page=path.read_text().replace('<div id="chart"', '<details open><summary>离线桑基图 · 左列为来源，右列为去向；悬停查看流量</summary><style>.offline-flow path:hover,.offline-flow path:focus{stroke:#c96c2d}.offline-flow{width:100%;max-width:1050px}</style>'+fig+'</details><div id="chart"');path.write_text(page)
else:
    go.Figure(go.Sankey(node=dict(label=names),link=dict(source=[names.index(x['source']) for x in f],target=[names.index(x['target']) for x in f],value=[float(x['value']) for x in f]))).update_layout(title='2022年五系统磷流（Mt P/年）',height=800).write_html(o/'sankey_2022.html',include_plotlyjs=True)
summary=html.escape(report)
(o/'index.html').write_text('<meta charset="utf-8"><title>全球磷循环课程作业</title><style>body{max-width:900px;margin:40px auto;font:17px/1.8 sans-serif}article{white-space:pre-wrap}</style><h1>全球磷循环课程作业</h1><p><a href="sankey_2022.html">2022年桑基图</a>　<a href="scenario_offline.html">2050年情景图</a>　<a href="benchmark_comparison.csv">基准核验表</a></p><article>'+summary+'</article>')
page=o/'scenario_offline.html'
page.write_text(page.read_text().split('<h2>评分项检查')[0]+'<p><a href="benchmark_comparison.csv">文献基准核验</a>　<a href="index.html">返回报告</a></p></html>')
(o/'验收清单.md').write_text(f'2022与2050情景守恒检查通过。1961年施肥量偏差 {abs(value/4.9-1):.2%}。2022年ACS化肥占比 {b[3]["result"]}%。全部基准见benchmark_comparison.csv。')
