"""基准对照与离线汇总页；不把外生参考值当作复现成功。"""
from pathlib import Path
import argparse,csv,json,html
from run import write_csv

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--data',type=Path);ap.add_argument('--output',type=Path,default=Path(__file__).resolve().parent/'outputs');a=ap.parse_args();o=a.output
    b=json.loads((o/'results.json').read_text());r=json.loads((o/'scenario_results.json').read_text())
    with (o/'flows_2022.csv').open(encoding='utf-8-sig') as f:flows=list(csv.DictReader(f))
    total=sum(float(f['value']) for f in flows if f['target']=='ACS' and f['source']!='ACS')
    mineral=sum(float(f['value']) for f in flows if f['source']=='CIS' and f['target']=='ACS')
    share=mineral/total*100
    rows=[
     dict(indicator='1961—2022累计开采P',reference='约1153 Mt',result='',status='未复现',explanation='未构建完整历史采矿序列，不能将2022反推量外推作为历史观测'),
     dict(indicator='1961化肥施用',reference='约4.9 Mt',result='',status='未复现',explanation='历史类别序列未覆盖化肥核算'),
     dict(indicator='2022化肥施用',reference='约20.5 Mt',result=mineral,status='外生输入',explanation='直接引用任务书；不计算伪零偏差'),
     dict(indicator='2022 ACS化肥输入占比',reference='超过64%',result=round(share,4),status='未达参考范围且口径未完全一致',explanation='本版不含田内循环的外部ACS输入；依赖粪便反推与用途假设，不能以简化为由自动豁免'),
     dict(indicator='LBS历史平均PUE',reference='约23%',result=23,status='外生假设',explanation='借用历史均值反推2022粪便量；未独立复现年度PUE'),
     dict(indicator='S4.3原生磷需求削减',reference='22.15%',result='',status='待核对原始基准归属',explanation='任务书与补充材料膳食变化段落归属冲突；课堂75%与论文100%参数不同'),
     dict(indicator='S4.3化肥需求削减',reference='76.9%',result='',status='不直接比较',explanation='同上；不以课堂Replace情景充当论文S4.3'),
     dict(indicator='S2.3饲料效率提升效果',reference='IFD约-26%；FGD约-35%；NPR约-17%',result='',status='未模拟',explanation='不属于课堂三项措施；仅保留文献参考'),
     dict(indicator='S5原生磷需求削减',reference='约97%',result='',status='不直接比较',explanation='课堂3R与全链条S5措施范围不同'),
     dict(indicator='国家农田PUE70%达标',reference='单措施8国；综合17国',result='',status='未模拟',explanation='当前全球模型未提供35国分析'),
     dict(indicator='回归R2',reference='>0.85',result=r['regression'][-1]['R2'],status='教学效率指标响应面达到',explanation='样本和响应变量不同，不能视为论文回归独立复现')]
    write_csv(o/'benchmark_comparison.csv',rows)
    assessment=[('数据工程与守恒','守恒通过；已接入2022年产出与贸易的分产品含磷率换算'),('复现精度','尚无完整独立基准验收，不能声明3%达标'),('算法与回归','3R和中心化回归已运行；比值交互解释须保留'),('图件','桑基图仍依赖外部Plotly；离线情景页可用，交互图未验收'),('报告','讨论稿已形成，结论受占位假设限制'),('一键复现','主计算与本页生成已整合；数据源需另行提供，离线Plotly仍缺失')]
    text=['# 评分项核查','',f'2022 ACS矿物磷肥占外部输入 {share:.2f}%，未达到任务书超过64%的参考。不能通过调参强行修正。','']+['- '+k+'：'+v for k,v in assessment]
    (o/'验收清单.md').write_text('\n'.join(text))
    esc=lambda x:html.escape(str(x))
    table='<table><tr><th>情景</th><th>化肥 Mt P/年</th><th>开采 Mt P/年</th><th>水体流失 Mt P/年</th><th>供给效率</th></tr>'
    for s in r['scenarios']:table+=f'<tr><td>{esc(s["scenario"])}</td><td>{s["fertilizer_Mt"]:.3f}</td><td>{s["mining_Mt"]:.3f}</td><td>{s["water_Mt"]:.3f}</td><td>{100*s["system_supply_efficiency"]:.2f}%</td></tr>'
    table+='</table>'
    bar=[]
    for field,title in [('water_Mt','水体磷流失'),('mining_Mt','原生磷开采需求')]:
        bar.append(f'<h2>{title}（Mt P/年）</h2><svg viewBox="0 0 760 290" role="img" aria-label="{title}">')
        for i,scenario in enumerate(r['scenarios']):
            value=scenario[field]
            y=20+i*50
            width=value/max(item[field] for item in r['scenarios'])*520
            bar.append(f'<text x="5" y="{y+22}">{esc(scenario["scenario"])}</text><rect x="95" y="{y}" width="{width}" height="30" fill="#167d8d"/><text x="{width+105}" y="{y+22}">{value:.3f}</text>')
        bar.append('</svg>')
    page='<!doctype html><html lang="zh"><meta charset="utf-8"><title>磷循环课堂作业核查</title><style>body{max-width:1100px;margin:40px auto;padding:20px;font:17px/1.65 sans-serif;color:#173042}table{border-collapse:collapse;width:100%}td,th{padding:10px;border-bottom:1px solid #ddd;text-align:left}svg{width:100%}.note{background:#fff4da;padding:18px}</style><h1>磷循环课堂模型：计算与验收</h1><p class="note">部分参数为教学假设，尚未完成独立文献精度验收。</p>'+table+''.join(bar)+'<h2>评分项检查</h2><ul>'+''.join('<li><b>'+esc(k)+'</b>：'+esc(v)+'</li>' for k,v in assessment)+'</ul><h2>文献基准</h2><table><tr><th>指标</th><th>参考</th><th>当前值</th><th>状态</th></tr>'+''.join('<tr>'+''.join('<td>'+esc(x[k])+'</td>' for k in ['indicator','reference','result','status'])+'</tr>' for x in rows)+'</table><h2>回归解释</h2><p>绝对削减量在当前范围内为加和关系。效率比值可呈现显著的形式交互，不能推广为过程协同或政策因果关系。所有数值均为模型条件下的结果。</p></html>'
    (o/'scenario_offline.html').write_text(page,encoding='utf-8')
    print('Benchmark check: ACS mineral share',share,'percent; independent accuracy acceptance incomplete')
if __name__=='__main__':main()
