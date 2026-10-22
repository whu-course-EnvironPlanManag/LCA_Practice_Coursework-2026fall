"""Render case-2 figures from calculate_case2.py output (PNG 300 dpi + SVG)."""
from pathlib import Path
import csv
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import StrMethodFormatter
import schemdraw
from schemdraw import flow

ROOT=Path(__file__).resolve().parent
plt.rcParams.update({'font.sans-serif':['Microsoft YaHei','SimHei','DejaVu Sans'],
    'axes.unicode_minus':False,'font.size':11,'axes.spines.top':False,'axes.spines.right':False,
    'svg.fonttype':'none'})
BLUE='#21618c'; GREEN='#148f77'; ORANGE='#ca6f1e'; RED='#b03a2e'

def save(fig,name):
    for ext in ['png','svg']:
        fig.savefig(ROOT/(name+'.'+ext),dpi=300,bbox_inches='tight',facecolor='white')
    plt.close(fig)

def sensitivity(s):
    with (ROOT/'sensitivity_results.csv').open(encoding='utf-8-sig') as f:
        rows=list(csv.DictReader(f))
    p=[float(r['electricity_price']) for r in rows]
    fig,axes=plt.subplots(3,1,figsize=(10,11),sharex=True,layout='constrained')
    specs=[('LCOM_RMB_per_t','平准化甲醇成本 / 元/t',BLUE,s['fossil_price']),
           ('green_premium_RMB_per_t','绿色溢价 / 元/t',ORANGE,0),
           ('MAC_RMB_per_tCO2e','减排成本 / 元/t CO2e',GREEN,100)]
    for ax,(key,label,color,reference) in zip(axes,specs):
        ax.plot(p,[float(r[key]) for r in rows],color=color,lw=2.4)
        ax.axhline(reference,color='#666666',ls='--',lw=1.2,label=f'参考值：{reference:,.0f}')
        ax.axvline(s['critical_price_carbon100'],color=GREEN,ls=':',lw=1.8,label='100 元碳收益下临界电价 0.1502')
        ax.axvline(s['critical_price_no_carbon'],color=BLUE,ls='--',lw=1,label='无碳收益平价电价 0.1165')
        ax.set_ylabel(label); ax.grid(alpha=.18); ax.legend(fontsize=9,loc='upper left')
        ax.yaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))
    axes[-1].set_xlabel('电价 p / 元/kWh'); axes[-1].set_xlim(.05,.60)
    fig.suptitle('绿色甲醇：电价—成本—绿色溢价—减排成本联动',fontsize=17)
    fig.supxlabel('固定绿电碳因子 0.035；碳收益按全部核算减排量可变现的课程假设，非实际补贴承诺。',fontsize=10)
    save(fig,'cost_mac_sensitivity')

def environmental(s):
    fig,axes=plt.subplots(1,2,figsize=(13,5.5),layout='constrained')
    ax=axes[0]; values=[s['green_gwp'],2600,s['grid_gwp']]
    bars=ax.bar(['绿电 0.035','煤制甲醇基准','区域电网 0.550'],values,color=[GREEN,'#7f8c8d',RED],width=.6)
    ax.axhline(0,color='#555',lw=1); ax.set_ylabel('出厂边界净 GWP / kg CO2e/t')
    ax.set_title('电力碳因子决定环境表现')
    for bar,v in zip(bars,values):
        ax.annotate(f'{v:,.2f}',(bar.get_x()+bar.get_width()/2,v),xytext=(0,6 if v>0 else -16),textcoords='offset points',ha='center',fontsize=11)
    ax.set_ylim(-1600,5300); ax.grid(axis='y',alpha=.15)
    ax=axes[1]; x=[i/100 for i in range(101)]
    y=[10826*(.75-.71*t)+s['nonpower_offset_kgCO2e'] for t in x]
    ax.plot([v*100 for v in x],y,color=BLUE,lw=2.5)
    ax.axhline(2600,color='#666',ls='--',label='煤制甲醇 2,600 kg CO2e/t')
    ax.axvline(s['pv_min_share']*100,color=GREEN,ls=':',label=f"临界光伏占比 {s['pv_min_share']*100:.2f}%")
    ax.scatter([s['pv_min_share']*100],[2600],color=GREEN,zorder=5)
    ax.set_xlabel('光伏占总供电量比例 / %'); ax.set_ylabel('净 GWP / kg CO2e/t')
    ax.set_title('光伏 0.04 与自备煤电 0.75 混供'); ax.legend(fontsize=9); ax.grid(alpha=.15)
    fig.suptitle('绿电悖论与混供临界比例',fontsize=17)
    fig.supxlabel('沿用课程捕集与氧气替代信用；负值不等于产品使用后永久移除 CO2。',fontsize=10)
    save(fig,'lca_and_pv_threshold')

def process(model):
    m=model['streams_kg']
    d=schemdraw.Drawing(show=False,inches_per_unit=.48)
    d.config(fontsize=9,font='Microsoft YaHei')
    boxes={}
    def box(key,xy,label,w=5.8,h=1.7):
        b=flow.Box(w=w,h=h).at(xy).anchor('N').label(label)
        d.add(b); boxes[key]=b
    box('co2',(0,0),f"新鲜 CO2\n{m['fresh_co2']:.2f} kg")
    box('mix',(0,-3.5),'气体混合与预热')
    box('reactor',(0,-7),f"甲醇合成反应器\n单程转化率 25%")
    box('sep',(0,-10.5),'冷却冷凝与\n高压气液分离')
    box('distill',(0,-14),'精馏提纯')
    box('product',(0,-17.5),'精甲醇主产品\n1,000.00 kg')
    box('pem',(-9,-3.5),f"PEM 电解水制氢\nH2 {m['hydrogen']:.2f} kg")
    box('oxygen',(-9,0),f"副产氧气外售\n{m['oxygen']:.2f} kg")
    box('water',(-9,-10.5),f"电解槽总进水\n{m['electrolyzer_water']:.2f} kg")
    box('netwater',(-9,-17.5),f"外购净补水\n{m['net_water']:.2f} kg")
    box('split',(9,-10.5),'未反应气分流器\n99% 循环 / 1% 驰放')
    box('comp',(9,-3.5),f"循环压缩机\n{m['recycle']:.2f} kg")
    box('purge',(9,-17.5),f"驰放气 → 厂内处理\n{m['purge']:.2f} kg")
    def arrow(a,pa,b,pb):
        d.add(flow.Arrow().at(getattr(boxes[a],pa)).to(getattr(boxes[b],pb)))
    for a,b in [('co2','mix'),('mix','reactor'),('reactor','sep'),('sep','distill'),('distill','product')]: arrow(a,'S',b,'N')
    arrow('pem','E','mix','W'); arrow('pem','N','oxygen','S')
    arrow('water','N','pem','S'); arrow('netwater','N','water','S')
    arrow('sep','E','split','W'); arrow('split','N','comp','S'); arrow('comp','W','mix','E'); arrow('split','S','purge','N')
    # Condensate return: distillation side outlet -> rising line -> total water inlet.
    start=boxes['distill'].W
    corner=(-5.7,start.y)
    d.add(flow.Line().at(start).to(corner))
    d.add(flow.Line().at(corner).to((-5.7,boxes['water'].E.y)))
    d.add(flow.Arrow().at((-5.7,boxes['water'].E.y)).to(boxes['water'].E))
    fig=d.draw(show=False)
    ax=fig.ax
    def text(x,y,label,ha='left'): ax.text(x,y,label,fontsize=9,ha=ha,va='center',fontfamily='Microsoft YaHei',bbox=dict(facecolor='white',edgecolor='none',pad=1))
    text(.3,-6.1,f"混合气 {m['reactor_inlet']:,.2f} kg")
    text(.3,-9.6,f"反应出口 {m['reactor_outlet']:,.2f} kg")
    text(.3,-13.1,f"粗液 {m['crude_liquid']:,.2f} kg")
    text(4.5,-10.5,f"气相\n{m['separator_gas']:,.2f} kg",ha='center')
    text(-4.2,-13.55,f"回收水\n{m['recovered_water']:.2f} kg",ha='center')
    text(-8.7,-7.5,'供水')
    fig.fig.suptitle('CO2 加氢制甲醇：反应—分离—循环工艺物质流',fontsize=17,y=1.015)
    fig.fig.text(.5,-.025,'理想守恒模型；基准 1 t 纯甲醇；流量单位 kg/t 产品；单程 25%，气相循环 99%。\n纯 CO2/H2，完全气液分离；循环比 2.8835，总碳利用率 97.0874%；与原始 CSV 审计分开。',ha='center',fontsize=10,fontfamily='Microsoft YaHei')
    save(fig.fig,'process_flow_diagram')

def main():
    result=json.loads((ROOT/'calculation_results.json').read_text(encoding='utf-8'))
    sensitivity(result['course_LCA_TEA'])
    environmental(result['course_LCA_TEA'])
    process(result['balanced_model'])
    print('Generated 3 figures, each as 300 dpi PNG and SVG.')

if __name__=='__main__': main()
