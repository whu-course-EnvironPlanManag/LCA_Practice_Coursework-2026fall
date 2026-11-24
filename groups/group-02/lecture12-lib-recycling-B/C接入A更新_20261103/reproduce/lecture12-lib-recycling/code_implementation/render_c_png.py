"""AI-assisted: render reviewed C diagnostic charts, without changing source data."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'figures_output'
OUT.mkdir(exist_ok=True)
data = json.loads((ROOT / 'data_cohort/integration_20261103/c_chart_data.json').read_text(encoding='utf-8-sig'))
FONT = 'C:/Windows/Fonts/msyh.ttc'
def text(x,y,t,size=28,fill='#25364A'):
    d.text((x,y),str(t),font=ImageFont.truetype(FONT,size),fill=fill)
def canvas(title,sub):
    global im,d
    im=Image.new('RGB',(2000,1250),'white'); d=ImageDraw.Draw(im)
    text(90,50,title,48); text(90,125,sub,26)
def save(name,foot):
    text(90,1100,foot,25)
    text(90,1150,'来源：B 情景结果，经 C 复算；2026-11-03。占位模型诊断，不代表实际园区绩效。',24,'#68788A')
    im.save(OUT/name,dpi=(300,300))

canvas('图 C1  已计成本构成（固定情景 case 580）','单位：元 / B 声明的吨 LCE；仅包含 B 模型已计入项目')
left,right=390,1770
for tick in range(0,9000,2000):
    x=left+tick/9000*(right-left)
    d.line((x,240,x,900),fill='#E3E9EF',width=2);text(x-25,925,f'{tick:,}',25)
for i,(label,val) in enumerate(data['cost']):
    y=260+i*125
    text(90,y+16,label,32)
    x=left+val/9000*(right-left)
    d.rounded_rectangle((left,y,x,y+76),radius=6,fill='#247A9A')
    text(x+16,y+17,f'{val:,.0f}',30)
text(390,1000,f"已计成本合计：{data['cost_total']:,.0f} 元 / t LCE",36)
save('fig_c1_cost_breakdown.png','未计入完整 CAPEX、进料采购等成本；该小计不能用于判断项目盈利。')

canvas('图 C2  固定外部条件下的成本—碳排放比较','电网因子 0.556 kg CO₂e/kWh；锂价 22,000 USD/t；能效系数 1.0（均为 B 情景设定）')
x0,x1,y0,y1=220,1850,230,930
def xy(x,y): return (x0+(x-2000)/11000*(x1-x0),y1-(y+14.2)/2.4*(y1-y0))
for v in range(2000,14000,2000):
    x,_=xy(v,-14.2);d.line((x,y0,x,y1),fill='#E3E9EF',width=2);text(x-35,y1+15,str(v),24)
for v in [-14,-13.5,-13,-12.5,-12]:
    _,y=xy(2000,v);d.line((x0,y,x1,y),fill='#E3E9EF',width=2);text(115,y-15,str(v),24)
text(220,185,'B 局部净成本（万元 / t LCE，越低越优）',26)
text(660,995,'GWP100（kg CO₂e / t LCE，越低越优）',28)
for row in data['scatter']:
    x,y=xy(row[0],row[1]);d.ellipse((x-6,y-6,x+6,y+6),fill='#B6C4D5')
front=sorted([r for r in data['scatter'] if r[2] is not None])
d.line([xy(r[0],r[2]) for r in front],fill='#168256',width=5)
for col,color,label,offset in [(3,'#247A9A','成本端 case 13',(-260,-65)),(4,'#EA8A26','折衷点 case 580',(20,-65)),(5,'#8855AA','环境端 case 3253',(25,15))]:
    r=next(r for r in data['scatter'] if r[col] is not None);x,y=xy(r[0],r[col]);d.ellipse((x-15,y-15,x+15,y+15),fill=color,outline='white',width=3);text(x+offset[0],y+offset[1],label,27,color)
save('fig_c2_conditional_pareto.png','121 个组内工况；绿色线为 23 个非支配点。净成本含假定收入，不等于完整 TEA 或实际利润。')

canvas('图 C3  筛选结果与证据完整性复核','同一批 3,267 个占位工况；两套检查范围不同，不应解释为实际园区合规结论')
text(240,210,'B：两项筛选',28,'#247A9A');text(650,210,'C：保守证据诊断',28,'#EA8A26')
left,right=400,1800
for tick in [0,1000,2000,3000]:
    x=left+tick/3400*(right-left);d.line((x,285,x,960),fill='#E3E9EF',width=2);text(x-20,980,str(tick),25)
for i,(label,b,c) in enumerate(data['policy']):
    y=310+i*220;text(115,y+45,label,35)
    for j,(val,color) in enumerate([(b,'#247A9A'),(c,'#EA8A26')]):
        yy=y+j*80;x=left+val/3400*(right-left)
        if val: d.rectangle((left,yy,x,yy+55),fill=color)
        text(x+16,yy+8,f'{val:,}',29,color)
save('fig_c3_policy_evidence.png','C 的“信息不足”表示证据缺失；“不通过”仅针对占位数据诊断，不是对真实企业作出的认定。')
print('\n'.join(str(p) for p in OUT.glob('fig_c*.png')))
