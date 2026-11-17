"""Lecture 15: transparent reduced five-system P budget, Mt elemental P/year.

Run: python model.py . All paths are relative to this file. No network access.
Observed data, literature parameters and closure assumptions are kept distinct.
"""
from pathlib import Path
from dataclasses import dataclass
import json
import itertools
import numpy as np
import pandas as pd
import statsmodels.api as sm
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import plotly.graph_objects as go

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'
OUT=ROOT/'results'
FIG=ROOT/'figures'
for p in [OUT,FIG]: p.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'Microsoft YaHei','axes.unicode_minus':False,'figure.dpi':150})

def save(df,name):
    df.to_csv(OUT/name,index=False,encoding='utf-8-sig',float_format='%.12g')

def read_history(name):
    d=pd.read_csv(DATA/f'{name}_1961_2022.csv')
    assert not d.duplicated(['Country','Product']).any()
    ys=[str(y) for y in range(1961,2023)]
    missing=d.melt(id_vars=['Country','Product'],value_vars=ys,var_name='year',value_name='P_t')
    missing=missing[missing.P_t.isna()]
    if len(missing):
        save(missing,f'missing_{name}.csv')
        assert name!='production', 'Missing production requires investigation'
        print(f'NOTICE: {name} has {len(missing)} missing cells; retained as NA, never zero.')
    assert ((d[ys]>=0)|d[ys].isna()).all().all()
    return d

@dataclass
class Subsystem:
    name: str
    inputs: dict
    outputs: dict
    stock: float=0.0
    def verify(self):
        ti=sum(self.inputs.values()); to=sum(self.outputs.values())
        e=abs(ti-to-self.stock)/(ti+1e-6)
        assert all(v>=-1e-10 for v in [*self.inputs.values(),*self.outputs.values()])
        assert e<1e-4, f'{self.name} balance error {e}'
        return dict(system=self.name,input_Mt=ti,output_Mt=to,stock_Mt=self.stock,relative_error=e)

class ACSPModel(Subsystem):
    """Harvest and losses are separate from the residual soil stock budget."""
    def __init__(self,inputs,harvest,residue,water,feed,res_feed,straw_return):
        self.harvest=harvest
        self.uptake=harvest+residue
        outputs={'LBS_crop':feed,'LBS_straw':res_feed,'RCS':harvest-feed,
                 'straw_return':straw_return,'Water':water,
                 'Other_soil':residue-res_feed-straw_return}
        super().__init__('ACS',inputs,outputs,sum(inputs.values())-sum(outputs.values()))

class PMSModel(Subsystem): pass
class CISModel(Subsystem): pass
class LBSModel(Subsystem): pass
class RCSModel(Subsystem): pass

class PNetwork:
    """Global food-chain reduced budget; not the full published eight-sector model.

    Closure estimates (grass input, resident residual, legacy P) are exposed.
    All scenario coefficients are computed from this base, not paper effect sizes.
    """
    def __init__(self,base,scale=1.0,reduce=0.0,manure=0.67,recycle=0.0):
        b=base; self.scale=scale
        assert 0<=reduce<=1 and b['manure_return']<=manure<=1 and 0<=recycle<=1
        H=b['harvest']*scale; A=b['animal']*scale
        residue=b['residue']*scale; feed=b['feed']*scale
        sr=residue*b['straw_return']; sf=residue*b['straw_feed']
        totalfeed=A/b['livestock_pue']
        excretion=totalfeed-A
        manure_P=manure*excretion
        human_excr=b['population']*scale*b['human_excretion']/1e9
        human_direct=human_excr*b['human_return']
        eligible=human_excr-human_direct
        sewage_recovered=eligible*recycle
        extra_manure=(manure-b['manure_return'])*excretion
        # Replacement is credited once, before a proportional efficiency measure.
        fertilizer=max(0,(b['fertilizer']*scale-extra_manure-sewage_recovered)*(1-reduce))
        # Baseline industrial feed/nonfertilizer demand held fixed across 3R runs.
        additive=b['feed_additive']*scale
        other_chemical=b['other_chemical']*scale
        gypsum=fertilizer/b['p_in_p2o5']*b['gypsum_per_p2o5']*b['p_in_gypsum']
        concentrate=fertilizer+additive+other_chemical+gypsum
        ore=concentrate/b['mining_yield']; mine_waste=ore-concentrate
        grass=totalfeed-feed-sf-additive
        assert grass>=0
        deposition=b['deposition'] # fixed cropland area
        water_acs=b['acs_water']  # fixed area emission coefficients
        acs=ACSPModel({'CIS':fertilizer,'LBS':manure_P,'RCS_direct':human_direct,
                      'RCS_recovered':sewage_recovered,'Deposition':deposition,'straw_return':sr},
                     H,residue,water_acs,feed,sf,sr)
        lbs=LBSModel('LBS',{'ACS_crop':feed,'ACS_straw':sf,'CIS':additive,'Grass':grass},
                     {'RCS':A,'ACS':manure_P,'Water':excretion-manure_P})
        rcs_in=H-feed+A
        rcs_residual=rcs_in-human_excr
        assert rcs_residual>=0
        rcs=RCSModel('RCS',{'ACS':H-feed,'LBS':A},
                     {'ACS_direct':human_direct,'ACS_recovered':sewage_recovered,
                      'Water':eligible-sewage_recovered,'Other_soil':rcs_residual})
        cis=CISModel('CIS',{'PMS':concentrate},{'ACS':fertilizer,'LBS':additive,
                     'Other_products':other_chemical,'Gypsum':gypsum})
        pms=PMSModel('PMS',{'Ore':ore},{'CIS':concentrate,'Mine_waste':mine_waste})
        self.systems=[pms,cis,acs,lbs,rcs]
        self.balance=[s.verify() for s in self.systems]
        # Shared internal edges must agree, independent of local residual closure.
        pairs=[(pms.outputs['CIS'],cis.inputs['PMS']), (cis.outputs['ACS'],acs.inputs['CIS']),
               (cis.outputs['LBS'],lbs.inputs['CIS']), (acs.outputs['LBS_crop'],lbs.inputs['ACS_crop']),
               (acs.outputs['LBS_straw'],lbs.inputs['ACS_straw']), (acs.outputs['RCS'],rcs.inputs['ACS']),
               (lbs.outputs['ACS'],acs.inputs['LBS']), (lbs.outputs['RCS'],rcs.inputs['LBS']),
               (rcs.outputs['ACS_direct'],acs.inputs['RCS_direct']),
               (rcs.outputs['ACS_recovered'],acs.inputs['RCS_recovered'])]
        assert all(abs(x-y)<1e-10 for x,y in pairs)
        water=water_acs+lbs.outputs['Water']+rcs.outputs['Water']
        other_soil=acs.outputs['Other_soil']+rcs_residual+mine_waste+gypsum
        external_in=ore+grass+deposition
        external_out=water+other_soil+other_chemical
        err=abs(external_in-external_out-acs.stock)/(external_in+1e-6)
        assert err<1e-4
        self.balance.append(dict(system='External_boundary',input_Mt=external_in,
            output_Mt=external_out,stock_Mt=acs.stock,relative_error=err))
        self.metrics=dict(fertilizer_Mt=fertilizer,new_mineral_P_Mt=ore,
            manure_recycled_Mt=manure_P,sewage_recovered_Mt=sewage_recovered,
            water_loss_Mt=water,other_soil_Mt=other_soil,legacy_P_Mt=acs.stock,
            environmental_load_Mt=water+other_soil+acs.stock,
            crop_harvest_Mt=H,crop_uptake_Mt=acs.uptake,
            crop_PUE=H/sum(acs.inputs.values()),livestock_PUE=A/totalfeed,
            fertilizer_share=fertilizer/sum(acs.inputs.values()),grass_closure_Mt=grass)
        self.edges=[('矿石边界输入','PMS',ore),('PMS','CIS',concentrate),('PMS','矿业残余',mine_waste),
            ('CIS','ACS',fertilizer),('CIS','LBS',additive),('CIS','其他化工产品',other_chemical),
            ('CIS','磷石膏残余',gypsum),('其他饲草边界输入','LBS',grass),('大气沉降','ACS',deposition),
            ('ACS','LBS',feed+sf),('ACS','RCS',H-feed),('LBS','RCS',A),
            ('LBS','回收粪肥',manure_P),('回收粪肥','ACS',manure_P),
            ('RCS','回收人源磷',human_direct+sewage_recovered),('回收人源磷','ACS',human_direct+sewage_recovered),
            ('ACS','还田秸秆',sr),('还田秸秆','ACS',sr),
            ('ACS','水体损失',water_acs),('LBS','水体损失',lbs.outputs['Water']),
            ('RCS','水体损失',rcs.outputs['Water']),('ACS','非耕地残余',acs.outputs['Other_soil']),
            ('RCS','消费及加工残余',rcs_residual)]
        if acs.stock>=0: self.edges.append(('ACS','土壤净积累',acs.stock))
        else: self.edges.append(('土壤库存释放','ACS',-acs.stock))

def main():
    prod=read_history('production'); imp=read_history('imports'); exp=read_history('exports')
    plant=list('ABCDEFIK') # exclude G animal, H cakes, J processed drinks, M live animals
    history=[]
    for country in prod.Country.unique():
        p=prod[prod.Country.eq(country)].set_index('Product')
        im=imp[imp.Country.eq(country)].set_index('Product')
        ex=exp[exp.Country.eq(country)].set_index('Product')
        for year in range(1961,2023):
            y=str(year)
            history.append(dict(country=country,year=year,crop_primary_P_Mt=p.loc[plant,y].sum()/1e6,
                cereals_P_Mt=p.loc['E',y]/1e6,animal_products_P_Mt=p.loc['G',y]/1e6,
                import_P_Mt=im.loc[list('ABCDEFGHIJKM'),y].sum(min_count=12)/1e6,
                export_P_Mt=ex.loc[list('ABCDEFGHIJKM'),y].sum(min_count=12)/1e6))
    hist=pd.DataFrame(history);hist['net_import_Mt']=hist.import_P_Mt-hist.export_P_Mt
    save(hist,'historical_series.csv')
    crops=pd.read_csv(DATA/'typical_crops_2022.csv')
    assumptions=json.loads((DATA/'assumptions.json').read_text(encoding='utf8'))
    uptake=assumptions['uptake_kg_per_t']
    feedshare=assumptions['crop_feed_share']
    crops['uptake_P_t']=crops.Value*crops.Item.map(uptake)/1000
    crops['residue_P_t']=crops.uptake_P_t-crops.P_t
    crops['feed_P_t']=crops.P_t*crops.Item.map(feedshare)
    assert (crops.residue_P_t>=0).all()
    assert np.allclose(crops.P_t,crops.Value*crops.Coefficient)
    save(crops,'typical_crops_calculated.csv')
    pop=pd.read_csv(DATA/'population.csv');gpop=pop[pop.region.eq('World')].set_index('year').population
    scale=float(gpop[2050]/gpop[2022])
    land=pd.read_csv(DATA/'world_cropland.csv').set_index('Year')
    hectares=float(land.loc[2022,'Value'])*1000
    p=hist[(hist.country=='World')&(hist.year==2022)].iloc[0]
    w=crops[crops.Area.eq('World')]
    b=dict(harvest=float(p.crop_primary_P_Mt),animal=float(p.animal_products_P_Mt),
           residue=float(w.residue_P_t.sum()/1e6),feed=float(w.feed_P_t.sum()/1e6),
           population=float(gpop[2022]))
    for key in ['fertilizer','livestock_pue','manure_return','straw_return','straw_feed',
                'human_excretion','p_in_p2o5','gypsum_per_p2o5','p_in_gypsum','mining_yield']:
        b[key]=assumptions[key]
    b['human_return']=assumptions['urban_share']*assumptions['urban_human_return']+(1-assumptions['urban_share'])*assumptions['rural_human_return']
    b['deposition']=hectares*assumptions['deposition_kg_ha']/1e9
    b['acs_water']=hectares*(assumptions['runoff_kg_ha']+assumptions['leaching_kg_ha'])/1e9
    nonfert=b['fertilizer']*(1-assumptions['fertilizer_share_of_chemical'])/assumptions['fertilizer_share_of_chemical']
    b['feed_additive']=nonfert*assumptions['food_feed_additive_share']*assumptions['feed_share_of_additives']
    b['other_chemical']=nonfert-b['feed_additive']
    (OUT/'base_inputs.json').write_text(json.dumps(b,ensure_ascii=False,indent=2),encoding='utf8')
    baseline=PNetwork(b)
    save(pd.DataFrame(baseline.balance),'mass_balance_2022.csv')
    save(pd.DataFrame(baseline.edges,columns=['source','target','P_Mt']),'flows_2022.csv')
    print('2022 flows and budgets (Mt P/year)')
    for s in baseline.systems:
        print(s.name,s.inputs,s.outputs,'stock=',s.stock)
    print('PASS: all nodes, shared flows, external boundary < 1e-4')
    names=['BAU','Reduce','Replace','Recycle','3R']
    pars=[(0,.67,0),(.2,.67,0),(0,.75,0),(0,.67,.60),(.2,.75,.60)]
    runs=[PNetwork(b,scale,*v) for v in pars]
    rows=[]
    for n,m in zip(names,runs):
        row={'scenario':n,**m.metrics}
        for k in ['fertilizer_Mt','new_mineral_P_Mt','water_loss_Mt','environmental_load_Mt']:
            row[k+'_change_pct']=100*(m.metrics[k]/runs[0].metrics[k]-1)
        rows.append(row)
    scen=pd.DataFrame(rows);save(scen,'scenarios_2050.csv')
    save(pd.DataFrame([dict(scenario=n,**r) for n,m in zip(names,runs) for r in m.balance]),'scenario_mass_balance.csv')
    print(scen[['scenario','fertilizer_Mt','new_mineral_P_Mt','water_loss_Mt','legacy_P_Mt','crop_PUE']].to_string(index=False))
    # 5 x 5 x 5 factorial runs: 3 actual policy variables, no artificial noise.
    grid=[]
    for r,m,c in itertools.product(np.linspace(0,.2,5),np.linspace(.67,.75,5),np.linspace(0,.6,5)):
        model=PNetwork(b,scale,float(r),float(m),float(c))
        grid.append(dict(Reduce=r,Replace=m,Recycle=c,
                    crop_PUE=model.metrics['crop_PUE']))
    design=pd.DataFrame(grid);save(design,'policy_design_125.csv')
    x=design[['Reduce','Replace','Recycle']].copy();x=x-x.mean()
    for a,c in itertools.combinations(['Reduce','Replace','Recycle'],2):x[a+'*'+c]=x[a]*x[c]
    x=(x-x.mean())/x.std(ddof=0)
    y=(design.crop_PUE-design.crop_PUE.mean())/design.crop_PUE.std(ddof=0)
    model=sm.OLS(y,sm.add_constant(x)).fit()
    reg=pd.DataFrame({'term':model.params.index,'standardized_beta':model.params.values,'p_value':model.pvalues.values})
    reg['interpretation']=[('主效应' if '*' not in t else '无实质交互（数值零）' if abs(beta)<1e-10 else
                          '无显著交互' if pv>=.05 else '协同增强' if beta>0 else '拮抗削弱')
                          for t,beta,pv in zip(reg.term,reg.standardized_beta,reg.p_value)]
    save(reg,'policy_regression.csv')
    (OUT/'policy_regression_summary.txt').write_text(model.summary().as_text(),encoding='utf8')
    print(reg.to_string(index=False));print('Policy emulator R2',model.rsquared)
    checks=[]
    for label,key,value in [('低开采产率','mining_yield',.8),('高开采产率','mining_yield',.95),
                            ('低养殖PUE','livestock_pue',.16),('高养殖PUE','livestock_pue',.30)]:
        bb={**b,key:value}
        ba=PNetwork(bb,scale);rr=PNetwork(bb,scale,.2,.75,.60)
        checks.append(dict(case=label,parameter=key,value=value,
            new_P_change_pct=(rr.metrics['new_mineral_P_Mt']/ba.metrics['new_mineral_P_Mt']-1)*100,
            water_change_pct=(rr.metrics['water_loss_Mt']/ba.metrics['water_loss_Mt']-1)*100))
    save(pd.DataFrame(checks),'assumption_sensitivity.csv')
    # Independent historical E+G regression, same random split and scaling as source.
    pp=prod[prod.Country.eq('World')].set_index('Product')[[str(y) for y in range(1961,2023)]].T
    pp=pp[list('ABCDEFGHIJK')].astype(float)
    xx=pp[['E','G']].copy();xx['E*G']=(xx.E-xx.E.mean())*(xx.G-xx.G.mean())
    yy=pp.sum(axis=1)
    xx=(xx-xx.mean())/xx.std(ddof=0);yy=(yy-yy.mean())/yy.std(ddof=0)
    order=np.random.RandomState(42).permutation(len(xx));test=order[:19];train=order[19:]
    hm=sm.OLS(yy.iloc[train],sm.add_constant(xx).iloc[train]).fit()
    predicted=hm.predict(sm.add_constant(xx).iloc[test])
    r2=1-((yy.iloc[test]-predicted)**2).sum()/((yy.iloc[test]-yy.iloc[test].mean())**2).sum()
    hr=pd.DataFrame({'term':hm.params.index,'beta':hm.params.values,'p_value':hm.pvalues.values})
    save(hr,'historical_EG_regression.csv')
    (OUT/'historical_EG_summary.txt').write_text(hm.summary().as_text(),encoding='utf8')
    # Broken-flow test proves balance checks do not automatically reclose perturbations.
    testnode=Subsystem('intentional_fault',{'in':10},{'out':9},0)
    try: testnode.verify()
    except AssertionError: print('PASS: injected 10% imbalance rejected')
    else: raise AssertionError('Balance validator failed to catch fault')
    assert len(design)==125 and model.rsquared>.85
    assert runs[-1].metrics['crop_harvest_Mt']==runs[0].metrics['crop_harvest_Mt']
    summary={'population_ratio':scale,'baseline_2022':baseline.metrics,'policy_r2':model.rsquared,
             'historical_EG_test_r2':r2,'historical_EG_beta_interaction':float(hm.params['E*G']),
             'historical_EG_p_interaction':float(hm.pvalues['E*G'])}
    (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
    # Standalone offline Plotly HTML. Feedback loops are deliberately retained.
    nodes=list(dict.fromkeys(n for a,c,v in baseline.edges for n in [a,c]))
    ids={n:i for i,n in enumerate(nodes)}
    fig=go.Figure(go.Sankey(arrangement='snap',node=dict(label=nodes,pad=22,thickness=18),
        link=dict(source=[ids[a] for a,c,v in baseline.edges],target=[ids[c] for a,c,v in baseline.edges],
                  value=[v for a,c,v in baseline.edges],hovertemplate='%{source.label} → %{target.label}<br>%{value:.4f} Mt P/年<extra></extra>')))
    fig.update_layout(title='2022 年全球五子系统简化磷预算（含文献参数与残差估计）',font=dict(family='Microsoft YaHei',size=13),height=850)
    fig.write_html(FIG/'sankey_2022.html',include_plotlyjs=True)
    labels={'World':'全球','China, mainland':'中国大陆','India':'印度','United States of America':'美国'}
    fig,ax=plt.subplots(figsize=(9,4.4))
    for c in labels:
        h=hist[hist.country.eq(c)];ax.plot(h.year,h.cereals_P_Mt,label=labels[c],lw=2)
    ax.set(xlabel='年份',ylabel='谷物产品磷 / Mt P',title='图 1  全球与三个典型国家的谷物磷产出');ax.legend();ax.grid(alpha=.18)
    fig.tight_layout();fig.savefig(FIG/'history.png',dpi=300);plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(10,4.1))
    cn=['BAU','减施20%','粪肥75%','污水60%','3R组合']
    for ax,col,title in zip(axs,['new_mineral_P_Mt','water_loss_Mt'],['原生矿物磷需求','模型水体压力']):
        ax.bar(cn,scen[col],color=['#7894a8','#387ca3','#35937c','#9b85ad','#d38645']);ax.set(title=title,ylabel='Mt P/年');ax.tick_params(axis='x',rotation=20)
    fig.suptitle('图 2  2050 年典型情景（简化模型估计）');fig.tight_layout();fig.savefig(FIG/'scenarios.png',dpi=300);plt.close(fig)
    z=np.array([[PNetwork(b,scale,r,m,0).metrics['new_mineral_P_Mt'] for r in np.linspace(0,.2,21)] for m in np.linspace(.67,.75,21)])
    fig,ax=plt.subplots(figsize=(7,4.3));im=ax.imshow(z,origin='lower',aspect='auto',extent=[0,20,67,75],cmap='viridis_r')
    ax.set(xlabel='化肥减施率 / %',ylabel='粪便还田率 / %',title='图 3  减施与粪肥替代的联合响应');fig.colorbar(im,ax=ax,label='原生矿物磷需求 / Mt P/年')
    fig.tight_layout();fig.savefig(FIG/'interaction.png',dpi=300);plt.close(fig)
    print('Finished; offline HTML and 300 DPI figures saved.')

if __name__=='__main__': main()
