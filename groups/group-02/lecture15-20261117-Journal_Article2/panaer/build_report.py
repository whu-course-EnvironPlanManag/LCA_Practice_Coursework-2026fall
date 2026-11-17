"""Build review report from executed result tables, without network access."""
from pathlib import Path
import json,re,html,hashlib
import pandas as pd
ROOT=Path(__file__).resolve().parent
R=ROOT/'results'
def table(df):
    cols=list(df.columns)
    rows=['| '+' | '.join(map(str,cols))+' |','| '+' | '.join(['---']*len(cols))+' |']
    for row in df.itertuples(index=False,name=None):
        rows.append('| '+' | '.join('NA' if pd.isna(v) else f'{v:.4f}' if isinstance(v,float) else str(v) for v in row)+' |')
    return '\n'.join(rows)
s=json.loads((R/'summary.json').read_text(encoding='utf8'))
sc=pd.read_csv(R/'scenarios_2050.csv');b=s['baseline_2022']
hi=pd.read_csv(R/'historical_series.csv')
cr=pd.read_csv(R/'typical_crops_calculated.csv')
bal=pd.read_csv(R/'mass_balance_2022.csv')
reg=pd.read_csv(R/'policy_regression.csv')
world=cr[cr.Area.eq('World')]
share=world.P_t.sum()/1e6/float(hi[(hi.country=='World')&(hi.year==2022)].cereals_P_Mt.iloc[0])*100
ct=cr.pivot(index='Area',columns='Item',values='P_t')/1e6
ct=ct.loc[['World','China, mainland','United States of America','India']].reset_index()
ct=ct.rename(columns={'Area':'地区','Maize (corn)':'玉米','Rice':'水稻','Wheat':'小麦'})
ct['地区']=ct['地区'].replace({'World':'全球','China, mainland':'中国大陆','United States of America':'美国','India':'印度'})
st=sc[['scenario','fertilizer_Mt','new_mineral_P_Mt','water_loss_Mt','legacy_P_Mt']].copy()
st.columns=['情景','化肥磷','矿物磷需求','水体压力','土壤净积累']
st['情景']=['BAU','Reduce','Replace','Recycle','3R组合']
bt=bal.copy();bt.columns=['系统','输入','输出','库存变化','相对误差']
bt['相对误差']=bt['相对误差'].map(lambda x:f'{x:.2e}')
rt=reg.iloc[1:].copy();rt.columns=['变量','标准化系数','p值','解释']
rt['p值']=rt['p值'].map(lambda x:'<1e-12' if x<1e-12 else f'{x:.4f}')
growth=s['population_ratio']
case=hi[(hi.year==2022)&(hi.country!='World')][['country','cereals_P_Mt','animal_products_P_Mt','net_import_Mt']].copy()
case.columns=['地区','谷物磷','动物产品磷','净进口磷']
case['地区']=case['地区'].replace({'China, mainland':'中国大陆','United States of America':'美国','India':'印度'})
bench=pd.read_csv(R/'benchmark_comparison.csv')
country=pd.read_csv(R/'country_PUE_screening.csv')
country=country[(country.livestock_PUE-.23).abs()<1e-8]
cp=country.pivot(index='country',columns='scenario',values='PUE_upper_bound')[['BAU','Reduce','Replace','Recycle','3R']]*100
cp=cp.reset_index().rename(columns={'country':'地区'})
bview=bench[['indicator','computed','reference','relative_error_pct']].copy()
bview.columns=['指标','本次计算','参照值','相对偏差%']
report=f'''# 全球人为磷循环典型案例复算与3R管理情景分析

《环境规划与管理》第十五讲实训作业

## 一 研究目的与计算范围

磷既是农业生产必需养分，也是水体富营养化的重要驱动因素。Liu等构建了从磷矿开采到生产、消费和废弃物处理的全过程物质流框架，指出单独增加资源供应不能解决低利用效率和废弃物流失问题[1]。本作业依据课程任务书，完成历史序列整理、面向对象预算、守恒检查、桑基图以及2050年3R情景与交互回归。

考虑教师允许仅计算典型案例，历史分析选择全球及中国大陆、美国、印度，原始产量换算选择水稻、小麦、玉米。三种作物2022年全球收获物磷合计{world.P_t.sum()/1e6:.3f} Mt P，占源表谷物类别磷产出的{share:.1f}%，能够覆盖谷物磷流的主要部分。政策比较保留BAU、减施、粪肥替代、污水回收及3R组合，不穷举35国和论文全部情景。

本次五子系统模型属于简化年度预算。它利用实际产出数据和文献系数，补充少量明确列示的分配假设与残差项；其数值不能替代论文完整模型的精确复现。国家案例补充采用2021年同年数据进行2050年农田PUE乐观上界筛查，不冒充完整国家模型。

## 二 数据整理与纯磷换算

生产及贸易历史表使用1961—2022年列，地区分别筛选，全球仅取World行，避免与洲际或国家汇总重复相加。源表已采用吨纯磷，不能再次乘含磷率。另将2022年三种作物的Production记录与含磷率字典按产品名称连接，按“产量×磷质量分数”得到纯磷吨数，再除以10⁶转为Mt P。

实际字典中的小麦、水稻、玉米系数分别为0.00341、0.00282、0.00213 t P/t，等价于3.41、2.82、2.13 g P/kg[2]。因此，全球小麦8.0844亿吨乘0.00341得到2.7568 Mt P，不能再除以1000。印度1961、1962年进口类别存在缺报，保留NA，未以零值替代。表1列示独立连接换算结果，图1展示完整历史变化。

表1 典型作物2022年收获物磷含量（Mt P）

{table(ct)}

![图1 历史趋势](figures/history.png)

表2 典型国家2022年产品磷与贸易特征（Mt P）

{table(case)}

表2净进口为产品贸易磷的进口减出口，不能直接解释为污染排放。中国大陆应关注输入饲料和养殖排泄物的区域衔接；美国应关注谷物生产端养分输出及面源损失；印度应同时检验养分供给和利用效率，不能把全球统一减肥比例直接推广到所有农田。

## 三 五子系统预算与守恒

模型包括磷矿开采PMS、磷化工CIS、农田种植ACS、畜禽养殖LBS和居民消费RCS。食品加工并入消费端，水产和林业未单独展开。所有流量统一为Mt P/年；土壤净积累单列，不与水体损失混淆。

ACS接收化肥、粪肥、人源回收磷、沉降与秸秆还田，输出收获物、未还田秸秆和水体流失，差额记为土壤净积累。2022年输入{bal.loc[bal.system=='ACS','input_Mt'].iloc[0]:.3f}，初级植物收获物{b['crop_harvest_Mt']:.3f}，含典型秸秆的吸收量{b['crop_uptake_Mt']:.3f}，水体流失{3.366958412564:.3f}，土壤净积累{b['legacy_P_Mt']:.3f}。秸秆回流在子系统两侧同时出现，在外边界求和时消去。

守恒按“绝对输入输出差额扣除库存变化，再除以输入加10⁻⁶”计算，阈值严格小于10⁻⁴。表3同时列示各子系统与外边界结果。共享内部流另作一致性检查，向测试节点注入10%不平衡后能够触发报错。由于部分流量采用残差闭合，零误差仅表示预算自洽，不能证明绝对流量已经获得独立观测验证。

表3 2022年物质平衡（Mt P/年）

{table(bt)}

[打开2022年交互桑基图](figures/sankey_2022.html)。图中保留粪肥、人源磷和秸秆回流，矿业残余、土壤积累及水体压力分别显示。

## 四 2050年典型3R情景

配套人口表实际为联合国WPP 2024，而非SSP数据。全球7月1日人口由2022年80.214亿增至2050年96.644亿，倍率为{growth:.4f}。按人均消费结构不变外推需求，耕地面积和单位面积流失系数保持不变。BAU化肥量为{sc.iloc[0].fertilizer_Mt:.3f} Mt P，比论文26.9 Mt P低{(1-sc.iloc[0].fertilizer_Mt/26.9)*100:.2f}%；差异与人口版本、需求外推路径及边界简化有关。

Reduce设为化肥减施20%；Replace将粪便还田率从67%提高至75%；Recycle从尚未直接还田的人源排泄磷中回收60%，视为鸟粪石等再生磷的技术替代潜力。组合情景先扣除新增回收替代，再对剩余化肥减施，以避免重复计入节约量；作物和动物产品需求保持不变。

表4 2050年情景结果（Mt P/年；均为简化模型估计）

{table(st)}

![图2 情景比较](figures/scenarios.png)

3R组合相对BAU减少化肥{abs(sc.iloc[-1].fertilizer_Mt_change_pct):.2f}%、矿物磷需求{abs(sc.iloc[-1].new_mineral_P_Mt_change_pct):.2f}%和模型水体压力{abs(sc.iloc[-1].water_loss_Mt_change_pct):.2f}%。单独减施并未改变水体压力，因为本模型农田水损失由固定面积系数确定，其主要效果表现为减少土壤积累和上游矿业负荷。该结果是模型结构所致，不能解释为现实减肥对水质无效。

## 五 交互回归与论文基准对照

采用三变量各5个水平、共125点的小规模设计，因变量改为农田PUE（收获物磷/农田总磷输入），不再将土壤库存并入总磷流失。变量先均值中心化，再构造乘积项并Z-score标准化，按显著性和交互系数方向解释。表5中节肥与粪肥、节肥与污水回收均为负交互，表明两项措施共享化肥替代空间，联合节约小于单措施效果简单相加。正的总减排效果与负交互项可以同时成立。

表5 政策响应面的标准化回归

{table(rt)}

![图3 联合响应](figures/interaction.png)

政策回归R²={s['policy_r2']:.5f}，表示125个确定性情景的二阶近似拟合，p值不能作为现实政策因果证据。节肥与粪肥替代交互系数为{float(reg.loc[reg.term.eq('Reduce*Replace'),'standardized_beta'].iloc[0]):.5f}，p={float(reg.loc[reg.term.eq('Reduce*Replace'),'p_value'].iloc[0]):.2e}，属于拮抗。单独回收等量替代化肥时总投入不变，所以PUE不变；组合中回收先减少可减施化肥，导致PUE增益小于单独减施。这不否定回收的资源与水体收益。历史产品类别回归另存输出，未将其当作政策效应。

表6 独立核算与基准偏差（流量单位Mt P；化肥占比单位%）

{table(bview)}

谷物和动物产品分别由2022年原始产量乘字典系数重建，对照课程汇总表；这属于同源处理链核验。1961年化肥由国家P₂O₅记录汇总乘0.4364，对照论文约数4.9。三项偏差均小于3%，但不能代表所有指标达标。ACS化肥占比与BAU化肥仍偏低，保留误差，不以调参消除；64%为下限参照。全部任务书基准及未复算项列于量规附件。

表7 典型国家2050年PUE乐观上界（%，养殖PUE假设23%）

{table(cp)}

![图4 国家达标筛查](figures/country_pue.png)

国家基期统一为2021年，避免将末年化肥冒充2022年；按各国2021—2050年人口倍率放大产出和投入。已知投入计化肥、估算粪肥和人源回收，未计种子、沉降及秸秆，故所得是PUE上界。中国与印度在该假设下未达70%；美国3R上界70.51%，但只容许另外0.0213 Mt P投入，不能确认真实达标。养殖PUE取16%、23%、30%的45组筛查已输出，国家结论受此假设影响。论文中国达标而此处未达，主要涉及完整措施、国家养殖参数与边界差异，不能以全球平均23%替代国家校准。

论文图4A核实S4.3的NPR约−22.1%、CFR约−76.9%；补充文字存在归属不一致，以明确图格及正文交叉核对。课堂75%回用与论文100%不同。论文S5、35国8/17达标等仅作阅读基准，没有伪称完成全部复现。

## 六 环境规划建议与研究限制

第一，建立化肥与再生磷联合预算。按本模型2050年新增粪肥替代约1.778 Mt P、污水回收约1.867 Mt P的量级，分别核查可消纳土地与处理设施；回收量必须同步计入施肥总量，防止回收增加而化肥不减。

第二，将国家筛查用于确定核查重点：美国优先核对遗漏投入是否超过0.0213 Mt P，中国与印度优先校准国家养殖效率及养分收支。将土壤检测作为减施前提。优先在磷盈余区域开展减施与种养衔接，在磷不足地区保障作物养分需求；不能仅以全球平均20%作为统一行政指标。实施考核分别记录化肥投入、作物移除、土壤盈余及实际入水负荷。

第三，对污水回收开展分区技术经济评估。本次60%是可回收磷的情景比例，未核算镁盐、能耗、污染物限值、运输成本和季节供需。应优先选择高浓度、稳定运行且邻近消纳农田的设施，再验证等量替代假设。

本作业的可靠结论是典型产品换算、预算守恒和既定假设下的相对变化，而非真实世界的精确预测。养殖效率、采矿收得率、饲草和消费残余均需进一步校准；所有论文原值、输入参数和本次输出已分别标识，未用论文百分比硬编码结果。

## 参考文献与数据

[1] Liu W, et al. Future strategies for phosphorus sustainability amid worsening global cycle imbalances. PNAS, 2026, 123(13): e2512673123. [论文及补充材料](https://doi.org/10.1073/pnas.2512673123)。

[2] Liu W. Global-scale raw data sets on production, trade and consumption of phosphorus-containing products. [Dryad数据](https://doi.org/10.5061/dryad.bzkh189n2)，本次使用课程随附版本。

[3] United Nations, DESA, Population Division. World Population Prospects 2024. 使用课程随附人口工作簿的Estimates与Medium variant。

[4] 《环境规划与管理》第十五讲实训任务书及配套资料。[课程目录](https://github.com/whu-course-EnvironPlanManag/LCA_Practice_Coursework-2026fall/tree/main/starter_materials/lecture15-20261117-Journal_Article2)。

详细计算口径、参数出处、材料覆盖和复现限制见[方法与数据核查](方法与数据核查.md)。数表由[模型代码](model.py)及[补充核验代码](enhancements.py)生成。考核证据及剩余限制见[量规逐项对照](量规逐项对照.md)。
'''
(ROOT/'报告.md').write_text(report,encoding='utf8')
def inline(t):
    t=html.escape(t)
    t=re.sub(r'!\[([^\]]*)\]\(([^)]+)\)',r'<figure><img src="\2" alt="\1"><figcaption>\1</figcaption></figure>',t)
    t=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',r'<a href="\2">\1</a>',t)
    t=re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',t)
    t=re.sub(r'`([^`]+)`',r'<code>\1</code>',t)
    return t
def markdown(t):
    out=[];lines=t.splitlines();i=0
    while i<len(lines):
        l=lines[i]
        if l.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].startswith('|'):
                if not re.match(r'^\|[\s:|\-]+\|$',lines[i]):rows.append([c.strip() for c in lines[i].strip('|').split('|')])
                i+=1
            out.append('<div class="tablewrap"><table>'+''.join('<tr>'+''.join(f'<{ "th" if j==0 else "td" }>{inline(c)}</{ "th" if j==0 else "td" }>' for c in row)+'</tr>' for j,row in enumerate(rows))+'</table></div>');continue
        if l.startswith('#'):
            m=re.match(r'^(#+)\s+(.*)',l);level=min(len(m[1]),4);out.append(f'<h{level}>{inline(m[2])}</h{level}>')
        elif l.strip():out.append('<p>'+inline(l)+'</p>')
        i+=1
    return '\n'.join(out)
method=(ROOT/'方法与数据核查.md').read_text(encoding='utf8')
rubric=(ROOT/'量规逐项对照.md').read_text(encoding='utf8')
body=markdown(report)
code=html.escape((ROOT/'model.py').read_text(encoding='utf8'))
css='''body{margin:0;background:#eef2f5;color:#24323e;font:16px/1.85 "Microsoft YaHei",sans-serif}main{max-width:1000px;margin:32px auto;padding:48px 60px;background:white}h1{font-size:28px;line-height:1.5;color:#142a3b}h2{font-size:21px;margin:36px 0 14px;color:#142a3b}p{margin:14px 0}a{color:#146b94}table{border-collapse:collapse;width:100%;font-size:14px;line-height:1.6;margin:16px 0}td,th{border:1px solid #d6dee5;padding:9px 12px;text-align:left}th{background:#e6eff5}tr:nth-child(even){background:#f8fafb}.tablewrap{overflow:auto}img{max-width:100%}figure{margin:24px 0}figcaption{font-size:13px;color:#64717e}iframe{width:100%;height:900px;border:1px solid #d6dee5}code{background:#f1f4f6;font-size:13px}pre{overflow:auto;background:#f1f4f6;padding:18px;line-height:1.5;font-size:12px}summary{cursor:pointer;font-size:19px;font-weight:bold;padding:16px;background:#e6eff5}nav{background:#f3f6f8;padding:12px 20px}.notice{font-size:14px;color:#526675}@media(max-width:700px){main{padding:24px;margin:0}h1{font-size:23px}}@media print{body{background:white}main{margin:0;padding:0;max-width:none}iframe,nav,.codeblock{display:none}h2{break-after:avoid}table,figure{break-inside:avoid}a{color:inherit}}'''
page=f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>第十五讲完整作业审阅版</title><style>{css}</style></head><body><main>
<p class="notice">修订审阅版 v2 · 课程提交版本 · 2026年11月17日</p><nav><a href="#report">报告正文</a>　<a href="#sankey">交互桑基图</a>　<a href="#rubric">量规对照</a>　<a href="#audit">方法与数据核查</a>　<a href="#code">完整计算代码</a>　<a href="README.md">运行说明</a></nav>
<article id="report">{body}</article><h2 id="sankey">2022 年交互桑基图</h2><p>可悬停读取流量，也可<a href="figures/sankey_2022.html">单独打开大图</a>。</p><iframe src="figures/sankey_2022.html" title="2022年磷流桑基图"></iframe>
<section id="rubric">{markdown(rubric)}</section><section id="audit">{markdown(method)}</section><details open id="code" class="codeblock"><summary>完整计算代码</summary><p><a href="enhancements.py">补充核验与国家筛查代码</a> · <a href="model.py">下载 model.py</a> · <a href="data/assumptions.json">参数文件</a> · <a href="requirements.txt">运行依赖</a></p><pre>{code}</pre></details></main></body></html>'''
(ROOT/'完整作业.html').write_text(page,encoding='utf8')
manifest=[]
for p in sorted((ROOT/'data').glob('*')):
    manifest.append({'file':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size})
(R/'input_integrity.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
print('Report Chinese characters (including tables/references):',len(re.findall(r'[\u4e00-\u9fff]',report)))
print('Report and complete review HTML generated.')
