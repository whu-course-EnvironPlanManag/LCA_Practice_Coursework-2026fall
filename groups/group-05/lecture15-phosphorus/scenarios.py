"""2050课堂3R及中心化交互回归。沿用2022模型边界，禁止解释为完整论文复现。"""
from pathlib import Path
import argparse,json,csv,itertools,math
import numpy as np
from scipy.stats import t
import openpyxl
from run import Model,write_csv

def project(base_flows,scale,p,reduce=0,manure_rate=None,recovery=0,equivalence=1):
    manure_rate=p['manure_return_rate'] if manure_rate is None else manure_rate
    assert 0<=reduce<=1 and 0<=manure_rate<=1 and 0<=recovery<=1 and 0<=equivalence<=1
    m=Model();m.flows=[dict(f,value=f['value']*scale) for f in base_flows]
    def get(a,b):return next(f for f in m.flows if f['source']==a and f['target']==b)
    def val(a,b):return get(a,b)['value']
    def put(a,b,v):
        assert v>=-1e-10,(a,b,v)
        get(a,b)['value']=max(0,v)
    manure=val('LBS','ACS')+val('LBS','未利用粪便处置')
    extra_manure=manure*(manure_rate-p['manure_return_rate'])
    put('LBS','ACS',manure*manure_rate);put('LBS','未利用粪便处置',manure*(1-manure_rate))
    # Reconstruct sewage from excretion, directly returned P and household chemicals.
    direct=val('RCS','ACS')
    excretion=direct/p['direct_human_return']
    sewage=excretion-direct+val('CIS','RCS')
    treated=sewage*p['sewage_collection'];extra_recovery=treated*recovery
    put('RCS','ACS',direct+extra_recovery)
    put('RCS','水体',sewage-treated+treated*(1-recovery)*p['treated_residual_water_share'])
    put('RCS','污泥处置',treated*(1-recovery)*(1-p['treated_residual_water_share']))
    # Paper Text S7.3: water loss = positive fertilizer/manure surplus * beta.
    # Transfer the footprint relation to this teaching SFA explicitly; calibrate beta
    # to the existing area-based BAU loss, without claiming spatial reproduction.
    original=lambda a,b: next(f['value']*scale for f in base_flows if f['source']==a and f['target']==b)
    harvested=sum(f['value'] for f in m.flows if f['source']=='ACS' and f['target'] in ['LBS','RCS','其他产品边界','加工废物处置'])
    surplus0=original('CIS','ACS')+original('LBS','ACS')+original('RCS','ACS')-harvested
    assert surplus0>0, 'BAU surplus cannot calibrate a positive loss fraction'
    beta=original('ACS','水体')/surplus0
    assert 0<=beta<=1, 'Calibrated loss fraction is outside physical range'
    f0=val('CIS','ACS')
    fertilizer=max(0,f0*(1-reduce)-equivalence*(extra_manure+extra_recovery))
    put('CIS','ACS',fertilizer)
    surplus=fertilizer+val('LBS','ACS')+val('RCS','ACS')-harvested
    put('ACS','水体',beta*max(0,surplus))
    products=fertilizer+val('CIS','LBS')+val('CIS','RCS')
    concentrate=products/p['chemical_yield'];geologic=concentrate/p['mining_yield']
    put('PMS','CIS',concentrate);put('地质资源','PMS',geologic)
    put('PMS','采矿废物处置',geologic-concentrate);put('CIS','化工废物处置',concentrate-products)
    # All boundary throughput scaled with population: explicit constant per-capita BAU.
    m.systems['ACS'].stock=sum(f['value'] for f in m.flows if f['target']=='ACS')-sum(f['value'] for f in m.flows if f['source']=='ACS')
    checks=m.verify()
    water=sum(f['value'] for f in m.flows if f['target']=='水体')
    disposal=sum(f['value'] for f in m.flows if '处置' in f['target'])
    useful=excretion
    external=geologic+val('边界外草料','LBS')+val('大气沉降','ACS')
    metrics=dict(system_supply_efficiency=useful/external,cropland_surplus_Mt=surplus,loss_fraction_beta=beta,reduce=reduce,manure_rate=manure_rate,recovery=recovery,equivalence=equivalence,mining_Mt=geologic,fertilizer_Mt=fertilizer,water_Mt=water,waste_disposal_Mt=disposal,soil_stock_change_Mt=m.systems['ACS'].stock,max_balance_error=max(x['relative_error'] for x in checks))
    return m,metrics

def regression(rows,response):
    x=np.array([[r[k] for k in ['reduce','manure_rate','recovery']] for r in rows]);c=x-x.mean(axis=0)
    raw=np.column_stack([c,c[:,0]*c[:,1],c[:,0]*c[:,2],c[:,1]*c[:,2]])
    z=(raw-raw.mean(axis=0))/raw.std(axis=0,ddof=0)
    y=np.array([r[response] for r in rows]);ys=y.std();assert ys>0
    yz=(y-y.mean())/ys;X=np.column_stack([np.ones(len(y)),z]);b,_,rank,_=np.linalg.lstsq(X,yz,rcond=None)
    residual=yz-X@b;sse=float(residual@residual);df=len(y)-rank
    exact=sse<1e-20
    se=np.sqrt(np.maximum(0,np.diag(np.linalg.inv(X.T@X))*sse/df))
    terms=['intercept','reduce','manure_rate','recovery','reduce:manure','reduce:recovery','manure:recovery'];result=[]
    for j,name in enumerate(terms):
        pv=None if exact or se[j]==0 else float(2*t.sf(abs(b[j]/se[j]),df))
        interaction='不适用'
        if ':' in name:
            interaction=('结构性加和：交互系数为数值零，p值不可估计' if exact and abs(b[j])<1e-10 else '需解释模型结构') if exact else ('无显著交互' if pv>=.05 else ('协同' if b[j]>0 else '拮抗'))
        if response=='efficiency_gain' and ':' in name:
            interaction='比值响应面的形式判定：'+interaction+'；非过程协同证据'
        result.append(dict(response=response,term=name,standardized_coefficient=float(b[j]),p_value=pv,interpretation=interaction))
    return result,dict(response=response,n=len(y),rank=int(rank),R2=1-sse/float(yz@yz),residual_sum_squares=sse,p_value_status='确定性精确拟合：无法估计残差方差，不报告虚假显著性' if exact else '仅为模型响应面拟合，不代表观测政策因果效应')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--data',type=Path,default=Path(__file__).resolve().parent.parent/'环境规划与管理-第十五讲20261117'/'source_data');ap.add_argument('--output',type=Path,default=Path(__file__).resolve().parent/'outputs');args=ap.parse_args();out=args.output
    base=json.loads((out/'results.json').read_text());p=base['assumptions']['values']
    with (out/'flows_2022.csv').open(encoding='utf-8-sig') as f:flows=[dict(r,value=float(r['value'])) for r in csv.DictReader(f)]
    w=openpyxl.load_workbook(next(args.data.glob('**/7.Global population*')),read_only=True,data_only=True)
    pop=None
    for row in w['Medium variant'].values:
        if len(row)>12 and row[2]=='World' and row[10]==2050:pop=float(row[12])*1000;break
    w.close();assert pop;scale=pop/base['population_2022']
    cases=[('BAU',0,p['manure_return_rate'],0),('Reduce',.2,p['manure_return_rate'],0),('Replace',0,.75,0),('Recycle',0,p['manure_return_rate'],.6),('3R',.2,.75,.6)]
    summary=[];bmetrics=project(flows,scale,p)[1]
    for name,r,m,c in cases:
        model,metrics=project(flows,scale,p,r,m,c);metrics={'scenario':name,**metrics}
        metrics['mining_change_pct']=100*(metrics['mining_Mt']/bmetrics['mining_Mt']-1)
        summary.append(metrics);write_csv(out/f'flows_2050_{name}.csv',model.flows);write_csv(out/f'balance_2050_{name}.csv',model.verify())
    write_csv(out/'scenarios_2050.csv',summary)
    samples=[]
    for r,m,c in itertools.product(np.linspace(0,.2,5),np.linspace(p['manure_return_rate'],.75,5),np.linspace(0,.6,5)):
        _,met=project(flows,scale,p,float(r),float(m),float(c))
        met['efficiency_gain']=met['system_supply_efficiency']-bmetrics['system_supply_efficiency'];met['water_reduction_Mt']=bmetrics['water_Mt']-met['water_Mt'];met['mining_reduction_Mt']=bmetrics['mining_Mt']-met['mining_Mt'];samples.append(met)
    write_csv(out/'sensitivity_samples.csv',samples)
    coeff=[];fit=[]
    for response in ['water_reduction_Mt','mining_reduction_Mt','efficiency_gain']:
        a,b=regression(samples,response);coeff.extend(a);fit.append(b)
    write_csv(out/'regression.csv',coeff)
    print("回归统计表  响应变量 | 项 | 标准化系数 | p值 | 交互解释")
    for row in coeff:
        significance = "不可估计" if row['p_value'] is None else f"{row['p_value']:.5g}"
        print(f"{row['response']} | {row['term']} | {row['standardized_coefficient']:.6g} | {significance} | {row['interpretation']}")
    sens=[]
    for eq,collection in itertools.product([.5,.75,1],[.3,.6,.9]):
        pp={**p,'sewage_collection':collection}
        # A separate consistent BAU is required when collection changes; use original 2022
        # flows for upstream baseline; project reconstructs all RCS sewage destinations.
        _,bm=project(flows,scale,pp,equivalence=eq)
        _,met=project(flows,scale,pp,.2,.75,.6,eq)
        sens.append(dict(sewage_collection=collection,**met,mining_reduction_pct=100*(1-met['mining_Mt']/bm['mining_Mt'])))
    write_csv(out/'assumption_sensitivity.csv',sens)
    report=dict(population_2022=base['population_2022'],population_2050=pop,scale=scale,scenarios=summary,regression=fit,limitations=['人均产品需求与所有基础通量按人口同比放大；未单独模拟耕地扩张或单产变化。','新增回收磷按有效替代系数抵扣化肥，主情景假设系数1；并检验0.5和0.75。','先按BAU化肥减施20%，再扣新增回收替代量；非负下限为0。','农田水体流失=正磷盈余×beta，借用论文Text S7.3足迹方法；beta由2022面积法基线校准，未复现空间土壤/降雨权重。','使用125个主情景组合；绝对削减量为加和关系。系统供给效率是居民实际摄入P（用排泄近似）/系统外部输入P；它的比值非线性可产生交互，不能解释为新增生物物理协同，也不与论文ACS/LBS PUE直接比较。','尚未完成论文3%复现精度核验，土壤余额变化不能单独证明长期产量不受影响。'])
    (out/'scenario_results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    lines=['# 2050年课堂情景：计算结果与适用范围','',f'人口由{base["population_2022"]/1e9:.3f}十亿增至{pop/1e9:.3f}十亿，BAU倍率{scale:.4f}。','', '|情景|原生开采需求 Mt P|化肥 Mt P|水体流失 Mt P|开采变化|','|---|---:|---:|---:|---:|']
    for s in summary:lines.append(f'|{s["scenario"]}|{s["mining_Mt"]:.3f}|{s["fertilizer_Mt"]:.3f}|{s["water_Mt"]:.3f}|{s["mining_change_pct"]:.2f}%|')
    lines+=['','这是教学假设下的模型结果，不能作为现实预测或原论文复现精度证明。','', '## 交互回归','125组全因子参数组合，三个主效应和三个两两交互项；先中心化，再构造乘积并标准化。','农田损失按论文足迹部分的盈余法衔接施肥量，系数由基线校准。绝对量响应为水体磷削减量、原生磷开采需求削减量；另分析系统供给效率增量（实际摄入P/外部输入P）。当前结构在给定范围内严格加和，交互系数接近数值零。残差方差接近零，p值不可估计，不能据此宣称统计显著或强行制造协同。','', '## 限制']+['- '+s for s in report['limitations']]
    (out/'scenario_review.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(dict(population_scale=scale,scenarios=summary,regression=fit),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
