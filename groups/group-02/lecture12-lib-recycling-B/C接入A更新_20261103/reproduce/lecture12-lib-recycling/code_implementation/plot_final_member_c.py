"""AI-assisted research charts with ReportLab chart primitives and PDFium rasterization."""
import csv
import json
from pathlib import Path
from reportlab.graphics.shapes import Drawing,String,Line
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics import renderPDF
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import pypdfium2 as pdfium

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data_cohort/final_integration_20261103'
OUT=ROOT/'figures_output'
TMP=ROOT/'report/final_integration_20261103/chart_render'
FONT='MSYH'
pdfmetrics.registerFont(TTFont(FONT,'C:/Windows/Fonts/msyh.ttc',subfontIndex=0))
COLORS=['#247A9A','#E68A26','#21885B','#8754A5','#B44B54','#60758C','#946C42']
def read(name):
    with (DATA/name).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def label(d,x,y,t,size=10,color='#23364A',anchor='start'):
    d.add(String(x,y,t,fontName=FONT,fontSize=size,fillColor=colors.HexColor(color),textAnchor=anchor))
def canvas(title,subtitle):
    d=Drawing(900,540);label(d,45,500,title,21);label(d,45,470,subtitle,10.5);return d
def finish(d,name,foot):
    label(d,45,49,foot,9)
    label(d,45,28,'C条件情景  非实证园区结论  年产量与预算假设见C_final_assumptions.json',9,'#68788A')
    TMP.mkdir(parents=True,exist_ok=True);pdf=TMP/(name+'.pdf');renderPDF.drawToFile(d,str(pdf))
    doc=pdfium.PdfDocument(str(pdf));page=doc[0];bitmap=page.render(scale=300/72)
    image=bitmap.to_pil();image.save(OUT/(name+'.png'),dpi=(300,300));page.close();doc.close()
    print(OUT/(name+'.png'))
def lineplot(d,data,xrange,yrange,xticks,yticks,xlabel,ylabel,names):
    c=LinePlot();c.x=115;c.y=125;c.width=720;c.height=295;c.data=data
    c.xValueAxis.valueMin,c.xValueAxis.valueMax=xrange
    c.yValueAxis.valueMin,c.yValueAxis.valueMax=yrange
    c.xValueAxis.valueSteps=xticks;c.yValueAxis.valueSteps=yticks
    for a in [c.xValueAxis,c.yValueAxis]:
        a.labels.fontName=FONT;a.labels.fontSize=9;a.strokeColor=colors.HexColor('#A8B8C5')
    c.yValueAxis.visibleGrid=True;c.yValueAxis.gridStrokeColor=colors.HexColor('#E4EAF0')
    c.lines.strokeWidth=2
    for i in range(len(data)):c.lines[i].strokeColor=colors.HexColor(COLORS[i])
    d.add(c);label(d,120,440,ylabel,10.5);label(d,475,93,xlabel,10.5,anchor='middle')
    legend=Legend();legend.x=150;legend.y=76;legend.fontName=FONT;legend.fontSize=9;legend.alignment='right';legend.columnMaximum=1
    legend.colorNamePairs=[(colors.HexColor(COLORS[i]),n) for i,n in enumerate(names)]
    legend.dx=12;legend.dy=6;legend.deltax=170;d.add(legend);return c

def main():
    OUT.mkdir(exist_ok=True)
    summary=json.loads((ROOT/'report/final_integration_20261103/summary.json').read_text(encoding='utf-8'))
    base=summary['baseline'];cost={r['name']:float(r['annual_CNY']) for r in read('annual_cost_breakdown.csv')}
    groups=[('进厂采购',cost['feed_delivered']),('公辅',sum(cost[k] for k in ['grid_power','green_power','process_steam','makeup_water'])),
      ('试剂',sum(cost[k] for k in ['acid98','peroxide27_5','naoh99','soda','lime90'])),
      ('人工维修',cost['staff']+cost['maintenance']),('治理及其他',sum(cost[k] for k in ['residue_disposal','basic_wastewater','advanced_increment','rd_budget','other_services','other_fees'])),
      ('资本年金',base['annualized_capex_quote_CNY']),('锂盐回款',base['LCE_receipts_quote_CNY']),('需额外净贡献',base['other_net_credit_needed_CNY'])]
    d=canvas('图 C6  年度成本构成与锂盐回款覆盖','参考情景  年LCE 3000吨  绿电50%  锂盐报价13.3万元每吨  单位为万元每年')
    bc=VerticalBarChart();bc.x=90;bc.y=135;bc.width=750;bc.height=280
    bc.data=[[v/1e4 for _,v in groups]];bc.categoryAxis.categoryNames=[n for n,_ in groups]
    bc.categoryAxis.labels.fontName=FONT;bc.categoryAxis.labels.fontSize=9;bc.valueAxis.labels.fontName=FONT;bc.valueAxis.labels.fontSize=9
    bc.valueAxis.valueMin=0;bc.valueAxis.valueMax=50000;bc.valueAxis.valueStep=10000
    bc.valueAxis.visibleGrid=True;bc.valueAxis.gridStrokeColor=colors.HexColor('#E4EAF0')
    bc.barLabelFormat='%.0f';bc.barLabels.fontName=FONT;bc.barLabels.fontSize=8
    bc.bars[0].fillColor=colors.HexColor(COLORS[0]);bc.bars[0,6].fillColor=colors.HexColor(COLORS[2]);bc.bars[0,7].fillColor=colors.HexColor(COLORS[1])
    d.add(bc);label(d,95,100,f"总年化报价支出 {((base['annualized_capex_quote_CNY']+base['opex_quote_CNY'])/1e4):,.0f} 万元；锂盐回款 {base['LCE_receipts_quote_CNY']/1e4:,.0f} 万元",11)
    finish(d,'fig_c6_final_cost_coverage','额外净贡献须来自其他产品或服务且扣除未计支出；缺口不等于项目亏损，未进行VAT清算。')
    linked=read('procurement_link_sensitivity.csv')
    d=canvas('图 C7  锂盐价格与采购传导的条件影响','固定年LCE 3000吨  进料68000吨  绿电50%  正差额需其他产品净贡献覆盖')
    data=[];names=[]
    for beta in [0,.02,.05,.1]:
        rs=sorted([r for r in linked if float(r['beta'])==beta],key=lambda r:float(r['LCE_price_quote_CNY_t']))
        data.append([(float(r['LCE_price_quote_CNY_t'])/1e4,float(r['gross_quote_gap_CNY_a'])/1e4) for r in rs]);names.append(f'采购传导 β={beta:g}')
    lineplot(d,data,(7,37),(-60000,110000),[10,15,20,25,30,35],[-50000,0,50000,100000],
      '锂盐报价  万元每吨LCE','锂盐回款口径差额  万元每年',names)
    finish(d,'fig_c7_final_price_link','β为人为扰动系数，不是合同估计；其他产品、SOH和报价税价不确定性未被消除。')
    scenarios=read('conditional_scenarios.csv')
    fixed=[r for r in scenarios if float(r['annual_LCE_scenario_t'])==3000 and float(r['LCE_price_quote_CNY_t'])==133000 and float(r['energy_efficiency'])==1 and float(r['grid_ef'])==.556]
    fixed.sort(key=lambda r:float(r['gwp_kgco2e_t_LCE']))
    data=[[(float(r['gwp_kgco2e_t_LCE'])/1000,float(r['gross_quote_gap_CNY_a'])/1e4) for r in fixed]]
    x=[v[0] for v in data[0]];y=[v[1] for v in data[0]]
    d=canvas('图 C8  固定外部情景的成本与碳比较','仅改变购入绿电比例  年LCE 3000吨  锂盐报价13.3万元每吨  能效1.0')
    xmin=min(x)-.2;xmax=max(x)+.2;ymin=18700;ymax=19800
    lineplot(d,data,(xmin,xmax),(ymin,ymax),[9,10,11,12,13,14],[18800,19000,19200,19400,19600],
      '条件工序碳指标  吨CO2e每吨LCE','锂盐回款口径差额  万元每年',['绿电0%至100%条件比较'])
    label(d,145,390,'低碳低差额端对应100%绿电供给上界',10,COLORS[2])
    label(d,145,370,'本输入下没有内部成本环境拐点',10,COLORS[2])
    finish(d,'fig_c8_final_conditional_front','不是已确认合规前沿；100%绿电受合同、可交付电量和计费边界约束，不是保证可行方案。')
    a=ROOT.parent/'lecture12-20261103-classroom-case3/lecture12-20261103-classroom-case3/data_cohort/dmfa_yichang_annual_total.csv'
    with a.open(encoding='utf-8-sig',newline='') as f:arows=list(csv.DictReader(f))
    data=[]
    for scenario in ['C065','C085','C100']:
        rs=[r for r in arows if r['collection_scenario']==scenario and 2026<=int(r['year'])<=2035]
        data.append([(int(r['year']),float(r['collected_total_t'])/68000*100) for r in rs])
    d=canvas('图 C9  已知首装队列贡献与园区需求尺度','宜昌2010至2025首装队列在2026至2035的释放贡献  园区实际进料参照68000吨每年')
    lineplot(d,data,(2026,2035),(0,8),[2026,2028,2030,2032,2035],[0,2,4,6,8],
      '年份','已知队列收集量除园区需求  %',['正规收集率65%','正规收集率85%','正规收集率100%'])
    finish(d,'fig_c9_final_cohort_scale','仅为已知队列贡献上界；不包括未来新装、替换和真实跨域流，不能据此推算全市缺口。')

if __name__=='__main__':main()
