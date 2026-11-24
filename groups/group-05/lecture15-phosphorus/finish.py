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
colors = {'地质资源':'#53677D','PMS':'#A05A2C','CIS':'#2866AC','ACS':'#248350','LBS':'#8F4C9A','RCS':'#B8424E','大气沉降':'#509CB1','边界外草料':'#AB851D'}
neutral = '#596670'
# Left/right duplicates unroll internal cycles. Band widths use one common scale.
sources=list(dict.fromkeys(x['source'] for x in f));targets=list(dict.fromkeys(x['target'] for x in f))
pos={};cursor={};svg=[]
for field,labels,x in [('source',sources,190),('target',targets,760)]:
    y=34
    for n in labels:
        h=sum(float(row['value']) for row in f if row[field]==n)*4
        pos[field,n]=cursor[field,n]=y
        svg.append(f'<rect x="{x}" y="{y}" width="8" height="{max(h,1)}" fill="{colors.get(n, neutral)}"/><text x="{x-5 if field=="source" else x+13}" text-anchor="{"end" if field=="source" else "start"}" y="{y+max(12,h/2)}">{n}</text>')
        y+=max(h,14)+12
bands=[]
for row in f:
    l,r,v=row['source'],row['target'],float(row['value']);h=v*4;y=cursor['source',l]+h/2;z=cursor['target',r]+h/2
    bands.append(f'<path d="M198 {y} C470 {y} 490 {z} 760 {z}" stroke="{colors[l]}" stroke-opacity=".62" stroke-width="{h}" tabindex="0"><title>{l} → {r}：{v:.3f} Mt P/年</title></path>');cursor['source',l]+=h;cursor['target',r]+=h
fig='<svg xmlns="http://www.w3.org/2000/svg" class="offline-flow" viewBox="0 0 950 900" font-family="sans-serif"><title>2022年全球磷流，颜色对应左侧来源，宽度表示年流量</title><g fill="none" stroke="#559eaa">'+''.join(bands)+'</g>'+''.join(svg)+'</svg>'
(o/'sankey_2022.svg').write_text(fig)
source_colors = [colors[row['source']] for row in f]
link_colors = ['rgba(%d,%d,%d,0.62)' % tuple(bytes.fromhex(color[1:])) for color in source_colors]
node_colors = [colors.get(name, neutral) for name in names]
trace = dict(type='sankey', node=dict(label=names,color=node_colors,pad=18),
             link=dict(source=[names.index(row['source']) for row in f],
                       target=[names.index(row['target']) for row in f],
                       value=[float(row['value']) for row in f],color=link_colors))
try:
    import plotly.graph_objects as go
except ImportError:
    chart = '<div id="chart" style="height:800px"></div><script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script><script>if(window.Plotly) Plotly.newPlot("chart",'+json.dumps([trace],ensure_ascii=False)+',{margin:{l:80,r:150,t:30,b:30}},{responsive:true})</script>'
else:
    chart = go.Figure(trace).update_layout(height=800).to_html(full_html=False,include_plotlyjs=True)
flow_rows = ''.join('<tr>'+''.join('<td>'+html.escape(str(row[key]))+'</td>' for key in ('source','target','value','basis'))+'</tr>' for row in flows)
style = '<style>body{max-width:960px;margin:2rem auto;padding:0 1rem;font:17px/1.65 sans-serif;color:#183342}img,.offline-flow{max-width:100%;height:auto}table{border-collapse:collapse}td,th{padding:.4rem .7rem;border-bottom:1px solid #ccc}.offline-flow path:hover,.offline-flow path:focus{stroke-opacity:1}</style>'
(o/'sankey_2022.html').write_text('<!doctype html><meta charset="utf-8"><title>2022年全球磷流</title>'+style+'<h1>2022年全球磷流</h1><p>流带颜色对应左侧来源，宽度表示年流量（Mt P/年）。悬停可读数。田内种子循环仅列入明细。</p>'+fig+'<h2>交互视图</h2>'+chart+'<h2>流量明细</h2><table><tr><th>来源</th><th>去向</th><th>Mt P/年</th><th>依据</th></tr>'+flow_rows+'</table>')
import re
labels={'BAU':'常规基准','Reduce':'化肥减施','Replace':'粪便利用','Recycle':'污水回收','3R':'三项组合'}
scenario_rows=rows('scenarios_2050.csv')
comparison=['情景 | 化肥需求 | 原生磷开采 | 水体流失','---|---:|---:|---:']
for row in scenario_rows:
    comparison.append(labels[row['scenario']]+' | '+' | '.join(format(float(row[key]),'.3f') for key in ('fertilizer_Mt','mining_Mt','water_Mt')))
figures=['![图1 2022年全球磷流](sankey_2022.svg)','图1　2022年全球磷流。左列为来源，右列为去向；流带同色表示同一来源，宽度按 Mt P/年绘制。土壤存量增加单列，田内种子循环省略。','表1　2050年五种情景的磷需求与流失（Mt P/年）','\n'.join(comparison)]
for number,svg in enumerate(re.findall(r'<svg .*?</svg>',(o/'scenario_offline.html').read_text(),re.S),2):
    caption=re.search('aria-label="([^"]+)"',svg).group(1)
    for key,label in labels.items():
        svg=svg.replace('>'+key+'<','>'+label+'<')
    name=f'scenario_{number}.svg'
    (o/name).write_text(svg.replace('<svg ', '<svg xmlns="http://www.w3.org/2000/svg" font-family="sans-serif" ',1))
    figures.extend([f'![{caption}]({name})',f'图{number}　2050年{caption}（Mt P/年）。各图按各自基准绘制，条末标注绝对量。'])
report=report.replace('2050年BAU化肥需求', '\n\n'.join(figures)+'\n\n2050年BAU化肥需求',1)
report=report.replace('三项政策参数保持课堂设定，改变有效替代系数和污水收集率所得结果如下。','表2　三项措施组合在不同有效替代系数和污水收集率下的结果')
policy_url='https://nyncw.cq.gov.cn/xxgk_161/zfxxgkzl/fdzdgknr/ghjh/202201/t20220106_10280790.html'
policy='重庆市农业农村委员会《重庆市农业生态环境保护与农业废弃物资源化利用“十四五”规划（2021—2025年）》列出两项2025年地方目标：主要农作物化肥利用率达到43%（2020年为40.3%），畜禽粪污综合利用率稳定在80%以上。前者考核养分利用效率，后者涵盖多种粪污利用途径。全球课堂模型分别控制矿物磷投入量和粪便磷还田比例，两地理尺度、指标分母和目标年份均有差异。[政策原文]('+policy_url+')'
policy=policy.replace('两地理尺度','两者的地理尺度')
law_url = 'https://legalinfo.moj.gov.cn/pub/sfbzhfx/zt/2026zt0106/xxxcsthjfd20260817/sthjfd20260817/202608/t20260818_538611.html'
values = {row['scenario']: row for row in scenario_rows}
def flow_value(scenario, source, target):
    records = rows(f'flows_2050_{scenario}.csv')
    return sum(float(row['value']) for row in records if row['source'] == source and row['target'] == target)

def difference(scenario, metric):
    return float(values['BAU'][metric]) - float(values[scenario][metric])

legal_section = [
    '《中华人民共和国生态环境法典》对农业面源污染防治和污泥管理规定了具体职责。下列数值取自2050年全球模型，各单项情景均与同年常规基准比较。20%、75%和60%为课堂情景参数。当地实施效果需用田块、养殖场和污水厂数据核算。[法典原文]('+law_url+')',
    f"农田施肥。第三百零八条要求地方农业农村等部门推广测土配方施肥技术，控制化肥过量使用。模型将化肥磷投入削减20%，年用量减少{difference('Reduce','fertilizer_Mt'):.3f} Mt P，入水磷减少{difference('Reduce','water_Mt'):.3f} Mt P。田块减施幅度应结合土壤有效磷和作物需磷量确定，并逐季核对单位面积施磷量和产量。",
    f"养殖场粪污。第三百零九条规定国家支持建设粪污利用或无害化处理设施，养殖场须保障设施运行和粪污达标排放。利用率由67%升至75%时，粪便还田磷由{flow_value('BAU','LBS','ACS'):.3f}增至{flow_value('Replace','LBS','ACS'):.3f} Mt P/年。在等磷替代假设下，原生磷开采每年减少{difference('Replace','mining_Mt'):.3f} Mt P。落实到养殖场，可用转运量、含磷率和农田签收记录核实还田磷量，再以排放监测核验达标情况。",
    f"城镇污水与污泥。第三百零四条要求相关单位无害化处理处置污泥，跟踪、记录并报告污泥流向、用途和用量。模型取污水收集率60%、设施磷回收率60%，进入污泥处置环节的磷由{flow_value('BAU','RCS','污泥处置'):.3f}降至{flow_value('Recycle','RCS','污泥处置'):.3f} Mt P/年，居民系统入水磷减少{difference('Recycle','water_Mt'):.3f} Mt P/年。设施台账可在法定去向记录基础上补记污泥干重和含磷率，据此区分剩余污泥携磷量与回收产品携磷量。"
]
report = report.replace('当前结果支持', '\n\n'.join([*legal_section, policy, '当前结果支持']), 1)
(o/'课程报告.md').write_text(report)
blocks=[]
for para in report.strip().split('\n\n'):
    if ' | ' in para and '\n---' in para:
        lines=para.splitlines()
        cells=[]
        for i,line in enumerate(lines):
            if i==1: continue
            tag='td' if i else 'th'
            cells.append('<tr>'+''.join(f'<{tag}>{html.escape(cell.strip())}</{tag}>' for cell in line.split('|'))+'</tr>')
        blocks.append('<table>'+''.join(cells)+'</table>')
        continue
    for line in para.splitlines():
        image=re.fullmatch(r'!\[(.*?)\]\((.*?)\)',line)
        if image:
            blocks.append(f'<img src="{image[2]}" alt="{image[1]}">')
        else:
            tag='h2' if line.startswith('## ') else 'h1' if line.startswith('# ') else 'p'
            content=html.escape(line.lstrip('# '))
            content=content.replace('[政策原文]('+policy_url+')', '<a href="'+policy_url+'">政策原文</a>')
            content=content.replace('[法典原文]('+law_url+')', '<a href="'+law_url+'">法典原文</a>')
            blocks.append(f'<{tag}>{content}</{tag}>')
(o/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>全球磷循环课程报告</title>'+style+'<nav><a href="sankey_2022.html">交互桑基图</a> · <a href="scenario_offline.html">情景对照</a> · <a href="benchmark_comparison.csv">基准核验表</a></nav>'+''.join(blocks))
page=o/'scenario_offline.html'
page.write_text(page.read_text().split('<h2>评分项检查')[0]+'<p><a href="benchmark_comparison.csv">文献基准核验</a>　<a href="index.html">返回报告</a></p></html>')
(o/'验收清单.md').write_text(f'2022与2050情景守恒检查通过。1961年施肥量偏差 {abs(value/4.9-1):.2%}。2022年ACS化肥占比 {b[3]["result"]}%。全部基准见benchmark_comparison.csv。')
