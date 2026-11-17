"""Independent checks and conservative country PUE screening; run after model.py."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent; D=R/'data'; O=R/'results'

def main():
    h=pd.read_csv(O/'historical_series.csv')
    prod=pd.read_csv(D/'production_1961_2022.csv').set_index(['Country','Product'])
    raw=pd.read_csv(D/'world_products_2022_joined.csv')
    checks=[]
    for cat,label in [('E','2022全球谷物磷'),('G','2022全球动物产品磷')]:
        value=raw.loc[raw.Category.eq(cat),'P_t'].sum()/1e6
        reference=float(prod.loc[('World',cat),'2022'])/1e6
        checks.append(dict(indicator=label,computed=value,reference=reference,
                           relative_error_pct=100*(value/reference-1),unit='Mt P',
                           evidence='原始Production×含磷质量分数，对照课程纯磷汇总表；两者共享底层统计，不是外部观测验证'))
    f=pd.read_csv(D/'fertilizer_use.csv'); fv=f[f.Year.eq(1961)]
    assert not fv.duplicated(['Area','Year']).any()
    v=fv.Value.sum()*.4364/1e6
    checks.append(dict(indicator='1961全球矿物磷肥',computed=v,reference=4.9,
                       relative_error_pct=100*(v/4.9-1),unit='Mt P',
                       evidence='课程FAO国家记录汇总：P2O5×0.4364；对照任务书约数4.9'))
    b=json.loads((O/'summary.json').read_text(encoding='utf8'))
    for name,value,ref,unit in [('2022 ACS化肥占比',b['baseline_2022']['fertilizer_share']*100,64,'%'),
                               ('2050 BAU化肥',pd.read_csv(O/'scenarios_2050.csv').iloc[0].fertilizer_Mt,26.9,'Mt P')]:
        checks.append(dict(indicator=name,computed=value,reference=ref,relative_error_pct=100*(value/ref-1),unit=unit,
                           evidence='简化模型偏差保留；64是下限参照，不能当作精确点值'))
    pd.DataFrame(checks).to_csv(O/'benchmark_comparison.csv',index=False,encoding='utf-8-sig')
    # Exact same-year 2021 crop/animal production and fertiliser. Unknown deposition,
    # seeds, straw and human recycling are nonnegative, so ignoring them gives an
    # UPPER BOUND on PUE, not a point estimate of a complete national model.
    ff=pd.read_csv(D/'country_fertilizer_2021.csv').set_index('Area')
    pop=pd.read_csv(D/'country_population_2021_2050.csv').set_index(['region','year'])
    labels={'China, mainland':'中国大陆','United States of America':'美国','India':'印度'}
    regions={'China, mainland':'China','United States of America':'United States of America','India':'India'}
    rows=[]
    for country,label in labels.items():
        H=h[(h.country==country)&(h.year==2021)].iloc[0].crop_primary_P_Mt
        A=h[(h.country==country)&(h.year==2021)].iloc[0].animal_products_P_Mt
        F=float(ff.loc[country,'Value'])*.4364/1e6
        k=float(pop.loc[(regions[country],2050),'population']/pop.loc[(regions[country],2021),'population'])
        N=float(pop.loc[(regions[country],2050),'population'])
        for pue in [.16,.23,.30]:
            M=A*k*(1/pue-1)
            for name,r,m,c in [('BAU',0,.67,0),('Reduce',.2,.67,0),('Replace',0,.75,0),('Recycle',0,.67,.6),('3R',.2,.75,.6)]:
                # Recovered sewage must be added to ACS input when replacing fertilizer.
                # Effective excretion return uses the global assumed ratio as a scenario parameter.
                direct=N*.47/1e9*.31504
                rec=N*.47/1e9*(1-.31504)*c
                fert=max(0,(F*k-(m-.67)*M-rec)*(1-r))
                known=fert+m*M+direct+rec
                output=H*k
                upper=output/known
                headroom=output/.70-known
                rows.append(dict(country=label,base_year=2021,scenario=name,livestock_PUE=pue,
                                 harvest_Mt=output,chemical_Mt=fert,known_input_Mt=known,
                                 PUE_upper_bound=upper,unmodelled_input_allowance_Mt=headroom,
                                 status='尚不能排除达标；须核对遗漏输入' if upper>=.70 else '在此假设下即使忽略遗漏输入也未达标'))
    c=pd.DataFrame(rows);c.to_csv(O/'country_PUE_screening.csv',index=False,encoding='utf-8-sig')
    plt.rcParams.update({'font.family':'Microsoft YaHei','axes.unicode_minus':False})
    fig,ax=plt.subplots(figsize=(8,4.5))
    for country in labels.values():
        q=c[(c.country==country)&np.isclose(c.livestock_PUE,.23)]
        ax.plot(q.scenario,q.PUE_upper_bound*100,marker='o',label=country)
    ax.axhline(70,color='#a84739',ls='--',label='70%目标')
    ax.set(ylabel='PUE乐观上界 / %',title='图4 典型国家2050年达标筛查（2021年基期）')
    ax.legend();ax.grid(alpha=.2);fig.tight_layout()
    fig.savefig(R/'figures/country_pue.png',dpi=300);plt.close(fig)
    # Mathematical invariants: bound >= any result with additional nonnegative inputs.
    assert (c.PUE_upper_bound>=c.harvest_Mt/(c.known_input_Mt+.01)).all()
    assert len(c)==45 and np.isfinite(c.PUE_upper_bound).all()
    print('Independent benchmark checks:');print(pd.DataFrame(checks).to_string(index=False))
    print('Country upper-bound screening, not original-paper reproduction:')
    print(c[np.isclose(c.livestock_PUE,.23)][['country','scenario','PUE_upper_bound','unmodelled_input_allowance_Mt']].to_string(index=False))

if __name__=='__main__':main()
