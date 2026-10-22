from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import schemdraw
from schemdraw import flow
ROOT=Path(__file__).resolve().parent
plt.rcParams['font.sans-serif']=['Microsoft YaHei','SimHei','DejaVu Sans']
plt.rcParams['axes.unicode_minus']=False

def draw():
    with schemdraw.Drawing(show=False,inches_per_unit=.65) as d:
        d.config(fontsize=11,font='Microsoft YaHei')
        labels=['废 PET 瓶砖：1,000 kg','1  拆包、筛选与干式脱标','2  湿式粉碎与热碱洗','3  密度浮选分离','4  光学色选、脱水与干燥','5  真空挤出造粒与固相增粘','瓶级 rPET 颗粒：800 kg\n产品收率 80%']
        nodes=[]
        for i,label in enumerate(labels):
            box=flow.Box(w=7.4,h=1.6).at((0,-i*2.6)).anchor('N').label(label)
            d.add(box); nodes.append(box)
        for i,mass in enumerate(['1,000','955','920','840','800','800']):
            d += flow.Arrow().at(nodes[i].S).to(nodes[i+1].N)
        branches=[(1,'45 kg','标签 20 kg\n泥沙 25 kg'),(2,'35 kg','胶水及溶解性杂质\n排入污水处理站'),(3,'80 kg','HDPE 副产品 75 kg\nHDPE 沉渣损失 5 kg'),(4,'40 kg','杂色瓶片与超细粉\n降级利用或处置')]
        for i,mass,label in branches:
            d += flow.Arrow().at(nodes[i].E).right().length(1.7)
            d += flow.Box(w=6,h=1.6).anchor('W').label(label)
        fig=d.draw(show=False)
        for i,mass in enumerate(['1,000','955','920','840','800','800']):
            fig.ax.text(.35,-i*2.6-2.1,mass+' kg',ha='left',va='center',fontsize=11,fontfamily='Microsoft YaHei')
        for i,mass,label in branches:
            fig.ax.text(4.55,-i*2.6-.55,mass,ha='center',va='bottom',fontsize=10,fontfamily='Microsoft YaHei')
        fig.fig.suptitle('废 PET 瓶机械物理再生：工艺与物质流',fontsize=17,y=1.01,fontfamily='Microsoft YaHei')
        fig.fig.text(.5,-.025,'基准：1,000 kg 瓶砖；800 + 75 + 20 + 25 + 35 + 5 + 40 = 1,000 kg\n干物料平衡；辅助投入另见 LCI 清单；箭头宽度不表示质量比例。',ha='center',fontsize=10,fontfamily='Microsoft YaHei')
        for ext in ['png','svg']:
            fig.fig.savefig(ROOT/('process_flow_diagram.'+ext),dpi=300,bbox_inches='tight',facecolor='white')
        plt.close(fig.fig)
    print('Saved PNG (300 dpi) and SVG')
if __name__=='__main__':
    draw()


