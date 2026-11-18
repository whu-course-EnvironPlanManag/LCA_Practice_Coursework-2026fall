"""五系统教学原型；全部流量 Mt P/yr。见 README 的适用范围。"""
from pathlib import Path
from dataclasses import dataclass
import argparse,csv,json,math
import openpyxl
from product_conversion import convert_baseline

@dataclass
class Subsystem:
    name: str
    stock: float = 0.0
    def balance(self, flows):
        incoming=sum(f['value'] for f in flows if f['target']==self.name)
        outgoing=sum(f['value'] for f in flows if f['source']==self.name)
        err=abs(incoming-outgoing-self.stock)/(incoming+1e-6)
        assert err<1e-4,(self.name,err)
        return dict(system=self.name,input=incoming,output=outgoing,stock_change=self.stock,relative_error=err)

class Model:
    def __init__(self):
        self.systems={n:Subsystem(n) for n in ['PMS','CIS','ACS','LBS','RCS']}
        self.flows=[]
    def add(self,a,b,value,basis):
        assert math.isfinite(value) and value>=0,(a,b,value)
        self.flows.append(dict(source=a,target=b,value=value,basis=basis))
    def verify(self):
        checks=[s.balance(self.flows) for s in self.systems.values()]
        names=set(self.systems)
        i=sum(f['value'] for f in self.flows if f['source'] not in names and f['target'] in names)
        o=sum(f['value'] for f in self.flows if f['source'] in names and f['target'] not in names)
        stock=sum(s.stock for s in self.systems.values())
        err=abs(i-o-stock)/(i+1e-6)
        assert err<1e-4
        checks.append(dict(system='TOTAL',input=i,output=o,stock_change=stock,relative_error=err))
        return checks

def write_csv(path,rows):
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--data',type=Path,default=Path(__file__).resolve().parent.parent/'环境规划与管理-第十五讲20261117'/'source_data');ap.add_argument('--output',type=Path,default=Path(__file__).resolve().parent/'outputs');args=ap.parse_args()
    out=args.output;out.mkdir(parents=True,exist_ok=True)
    params=json.loads(Path(__file__).with_name('parameters.json').read_text())
    p=params['values'];rev=args.data/'Supplementary_dataset_PNAS_First_Revision'
    convert_baseline(rev,out,write_csv)
    file=next(rev.glob('**/Agricultural products_P*'));w=openpyxl.load_workbook(file,read_only=True,data_only=True)
    it=iter(w.active.values);headers=next(it);cat={};history=[]
    for row in it:
        if row[0]=='World':
            cat[row[1]]=float(row[headers.index(2022)] or 0)/1e6
            for j,y in enumerate(headers):
                if isinstance(y,int):history.append(dict(year=y,category=row[1],P_Mt=float(row[j] or 0)/1e6))
    w.close();write_csv(out/'historical_world.csv',history)
    landfile=next(args.data.glob('**/Global level cropland area.csv'))
    with landfile.open(encoding='utf-8-sig') as f:
        land=[x for x in csv.DictReader(f) if x['Area']=='World' and x['Year']=='2022' and x['Element']=='Area']
    assert len(land)==1 and land[0]['Unit']=='1000 ha'
    ha=float(land[0]['Value'])*1000
    popfile=next(rev.glob('7.Global population*'));w=openpyxl.load_workbook(popfile,read_only=True,data_only=True)
    pop=None
    for row in w['Estimates'].values:
        if len(row)>12 and row[2]=='World' and row[10]==2022:pop=float(row[12])*1000;break
    w.close();assert pop
    # G is supplied total animal-product P, not automatically edible food.
    crop=sum(cat[k] for k in ['A','B','C','D','E','F','I','J'])
    feed=sum(cat.get(k,0)*v for k,v in p['feed_shares'].items())+cat['H']+cat['K']
    nonfood=cat['A']+cat['I'];seed=crop*p['seed_share']
    crop_food=crop-(feed-cat['H']-cat['K'])-nonfood-seed
    assert crop_food>0
    from livestock import inputs
    animal, manure=inputs(rev,args.data,out,write_csv)
    animal_food=animal*p['animal_edible_share']
    animal_other=animal-animal_food

    mineral_feed=p['feed_additive_Mt'];grass=animal+manure-feed-mineral_feed
    assert grass>=0
    manure_return=manure*p['manure_return_rate']
    # Aggregate processing loss allocated only to plant food; animal G split explicitly.
    processing=crop_food*p['plant_processing_loss'];plant_delivered=crop_food-processing
    excretion=pop*p['excretion_kg_per_person']/1e9
    food_waste=plant_delivered+animal_food-excretion
    assert food_waste>=0
    direct=excretion*p['direct_human_return']
    wastewater=excretion-direct+p['household_chemical_Mt']
    treated=wastewater*p['sewage_collection'];recovered=treated*p['recovery_rate']
    tailwater=treated*(1-p['recovery_rate'])*p['treated_residual_water_share']
    sludge=treated*(1-p['recovery_rate'])-tailwater
    fertilizer=p['fertilizer_Mt'];chemical_products=fertilizer+mineral_feed+p['household_chemical_Mt']
    concentrate=chemical_products/p['chemical_yield'];geologic=concentrate/p['mining_yield']
    m=Model();m.add('地质资源','PMS',geologic,'需求反推：产品需求/化工收率/采矿收率')
    m.add('PMS','CIS',concentrate,'模型反推');m.add('PMS','采矿废物处置',geologic-concentrate,'假设收率')
    m.add('CIS','ACS',fertilizer,'任务书2022参考值，外生输入，非独立复现')
    m.add('CIS','LBS',mineral_feed,'教学假设');m.add('CIS','RCS',p['household_chemical_Mt'],'教学假设')
    m.add('CIS','化工废物处置',concentrate-chemical_products,'假设收率')
    m.add('大气沉降','ACS',ha*p['deposition_kg_ha']/1e9,'耕地面积×论文代表系数')
    m.add('ACS','LBS',feed,'类别分配假设；H/K并入农田产品链，不再次计入crop')
    m.add('ACS','RCS',plant_delivered,'作者产品P×用途分配，扣假设加工损失')
    m.add('ACS','其他产品边界',nonfood,'A/I类别合并；需后续细分')
    m.add('ACS','加工废物处置',processing,'教学加工损失假设')
    m.add('ACS','ACS',seed,'年度种子内部循环；收支抵消')
    m.add('ACS','水体',ha*p['runoff_kg_ha']/1e9,'耕地面积×论文代表流失系数')
    m.add('边界外草料','LBS',grass,'平衡反推，非独立测量')
    m.add('LBS','RCS',animal_food,'入选初级动物产品×可食用比例')
    m.add('LBS','其他动物产品边界',animal_other,'选定动物产品剩余部分，非全部污染排放')
    m.add('LBS','ACS',manure_return,'八类存栏×分种排磷系数×67%代表利用率')
    m.add('LBS','未利用粪便处置',manure-manure_return,'未利用量不等于全部进入水体')
    m.add('RCS','ACS',direct+recovered,'直接还田与污水回收互斥分流')
    m.add('RCS','生活固废处置',food_waste,'食品输入减排泄，人体净存量假设为零')
    m.add('RCS','水体',wastewater-treated+tailwater,'未收集污水+处理尾水')
    m.add('RCS','污泥处置',sludge,'处理后未回收且未入尾水的磷')
    # Soil storage is an explicitly balanced quantity, not an independent accuracy test.
    m.systems['ACS'].stock=sum(f['value'] for f in m.flows if f['target']=='ACS')-sum(f['value'] for f in m.flows if f['source']=='ACS')
    checks=m.verify();write_csv(out/'flows_2022.csv',m.flows);write_csv(out/'balance_2022.csv',checks)
    print("2022年各流向（Mt P/年）")
    for flow in m.flows:
        print(f"{flow['source']} → {flow['target']}  {flow['value']:.6f}")
    for check in checks:
        print(f"守恒断言通过  {check['system']}  相对误差 {check['relative_error']:.3e}")
    summary=dict(status='教学原型，未完成文献精度验收',unit='Mt P/year',population_2022=pop,cropland_ha=ha,categories=cat,soil_stock_change=m.systems['ACS'].stock,balance=checks,assumptions=params)
    (out/'results.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
    # Plotly supplied online; data table remains usable offline.
    names=list(dict.fromkeys([f['source'] for f in m.flows]+[f['target'] for f in m.flows]+['土壤存量增加']))
    links=[f for f in m.flows if f['source']!=f['target']]
    if m.systems['ACS'].stock>0:links=links+[dict(source='ACS',target='土壤存量增加',value=m.systems['ACS'].stock)]
    trace=dict(type='sankey',node=dict(label=names,pad=20,thickness=20),link=dict(source=[names.index(f['source']) for f in links],target=[names.index(f['target']) for f in links],value=[f['value'] for f in links]))
    import html
    table=''.join('<tr>'+''.join('<td>'+html.escape(str(f[k]))+'</td>' for k in ['source','target','value','basis'])+'</tr>' for f in m.flows)
    page='<!doctype html><meta charset="utf-8"><title>2022年磷循环教学原型</title><style>body{font-family:sans-serif;margin:30px}td,th{padding:8px;border:1px solid #ddd}table{border-collapse:collapse}</style><h1>2022年五系统磷流教学原型</h1><p>单位：Mt P/年。含明确的教学假设；守恒通过不代表已复现论文精度。</p><p id="status">图形需联网加载Plotly；下方流量表可离线查看。</p><div id="chart" style="height:760px"></div><table><tr><th>起点</th><th>终点</th><th>磷流量</th><th>依据</th></tr>'+table+'</table><script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script><script>if(window.Plotly){Plotly.newPlot("chart",'+json.dumps([trace],ensure_ascii=False)+',{font:{size:13},margin:{t:30,b:30}},{responsive:true});document.getElementById("status").textContent="Plotly已加载；悬停可查看流量。"}</script>'
    (out/'sankey_2022.html').write_text(page,encoding='utf-8')
    print(json.dumps(dict(soil_stock_Mt=m.systems['ACS'].stock,max_balance_error=max(c['relative_error'] for c in checks),flows=len(m.flows),output=str(out)),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
