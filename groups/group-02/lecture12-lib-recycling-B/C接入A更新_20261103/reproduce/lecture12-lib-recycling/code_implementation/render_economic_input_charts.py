"""AI-assisted static input charts; no invented annual production or profit."""
import csv
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'figures_output'
with (ROOT/'data_cohort/economic_parameters_received.csv').open(encoding='utf-8-sig',newline='') as f:
    rows={r['param_id']:r for r in csv.DictReader(f)}
FONT='C:/Windows/Fonts/msyh.ttc'
def text(x,y,t,size=28,color='#25364A'):
    draw.text((x,y),str(t),font=ImageFont.truetype(FONT,size),fill=color)
def canvas(title,sub):
    global im,draw
    im=Image.new('RGB',(2200,1450),'white');draw=ImageDraw.Draw(im)
    text(95,55,title,50);text(95,135,sub,28)
def save(name):
    text(95,1365,'来源：用户修改版经济参数表，2026-11-03；报价及项目适用性仍待原始证据核验。',25,'#68788A')
    im.save(OUT/name,dpi=(300,300))

canvas('图 C4  规划投资分项（收到报价口径）','单位：万元；设计能力8万吨电池包/年；各工艺线是否同时建设需与A的工程方案核对')
labels=['预处理产线','再次使用重组线','湿法冶金主线','直接修复示范线','三废治理工程','园区公用工程','绿电微网配套','数字化平台']
left,right=480,1970
for tick in [0,5000,10000,15000,20000,25000]:
    x=left+tick/25000*(right-left);draw.line((x,245,x,1090),fill='#E3E9EF',width=2);text(x-30,1110,f'{tick:,}',25)
for i,label in enumerate(labels):
    value=float(rows[f'CAP-{i+1:02}']['value']);y=265+i*100
    text(95,y+10,label,31);end=left+value/25000*(right-left)
    draw.rectangle((left,y,end,y+60),fill='#247A9A');text(end+15,y+10,f'{value:,.0f}',29)
text(480,1180,'含税报价合计：52,000万元（5.20亿元）',36)
text(95,1265,'CAP-09仅作合计控制；不重复加总。上图采用收到表的含税金额，不代表经审定工程概算。',26)
save('fig_c4_capex_received.png')

canvas('图 C5  绿电比例对单位购电价格的影响','仅比较收到报价：网电0.62、直购绿电0.41元/kWh；不代表园区年度成本或最终收益')
x0,x1,y0,y1=230,2000,270,1100
def xy(g,p):return x0+g*(x1-x0),y1-(p-.30)/.40*(y1-y0)
for g in [0,.25,.5,.75,1]:
    x,_=xy(g,.3);draw.line((x,y0,x,y1),fill='#E3E9EF',width=2);text(x-24,1125,f'{g:.0%}',28)
for p in [.3,.4,.5,.6,.7]:
    _,y=xy(0,p);draw.line((x0,y,x1,y),fill='#E3E9EF',width=2);text(130,y-17,f'{p:.2f}',28)
text(230,215,'购电价格（元/kWh）',29)
for rate,color,label in [(1,'#247A9A','收到含税报价'),(1.13,'#EA8A26','按13%换算的不含税规划值')]:
    draw.line([xy(g,(.62*(1-g)+.41*g)/rate) for g in [i/100 for i in range(101)]],fill=color,width=6)
    for g in [0,1]:
        p=(.62*(1-g)+.41*g)/rate;x,y=xy(g,p)
        draw.ellipse((x-9,y-9,x+9,y+9),fill=color)
        text(x+(18 if g==0 else -110),y-45,f'{p:.3f}',27,color)
draw.line((580,1205,650,1205),fill='#247A9A',width=6);text(670,1180,'收到含税报价',28)
draw.line((1040,1205,1110,1205),fill='#EA8A26',width=6);text(1130,1180,'不含税规划值',28)
text(95,1265,'绿电为直购交付电量假设；自有光储、输配费用和进项抵扣资格需另核，未计缺失的年度用电量。',26)
save('fig_c5_electricity_price_assumption.png')
print('Saved C4/C5 input charts.')
