"""Reproducible coursework analysis. Observations, SI coefficients and assumptions stay distinct.
Run: python run_analysis.py [--source-data PATH] [--population-projection CSV]
Projection CSV columns: Year,Population (persons), including 2022 and 2050.
"""
from __future__ import annotations
import argparse
import hashlib
import itertools
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
if (HERE / '.deps').exists():
    sys.path.insert(0, str(HERE / '.deps'))
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import statsmodels.api as sm
from pypdf import PdfReader


def find(src, pattern, within=None):
    matches = [p for p in src.rglob(pattern) if within is None or within in str(p)]
    if len(matches) != 1:
        raise ValueError(f'Expected unique {pattern}: {matches}')
    return matches[0]


def read_csv(p, **kwargs):
    try:
        return pd.read_csv(p, encoding='utf-8-sig', **kwargs)
    except UnicodeDecodeError:
        return pd.read_csv(p, encoding='gb18030', **kwargs)


def save(df, name):
    df.to_csv(OUT / name, index=False, encoding='utf-8-sig')


def norm(s):
    return re.sub(r'[^a-z0-9]', '', str(s).lower())


def extract_si_coefficients(pdf, allowed_items):
    """Only unambiguous single-line two-column rows; wrapped names are NOT guessed."""
    reader = PdfReader(pdf)
    rows, active = [], False
    for page_no, page in enumerate(reader.pages, 1):
        plain = page.extract_text()
        if re.search(r'Table\s+S2\.\s+P\s+content', plain) and page_no > 100:
            active = True
        if active and re.search(r'Table\s+S3\.\s+Values', plain):
            break
        if not active:
            continue
        layout = page.extract_text(extraction_mode='layout')
        for line in layout.splitlines():
            match = re.match(r'^\s*(.*?)\s{2,}(\d+(?:\.\d+)?)\s{2,}(.*?)\s{2,}(\d+(?:\.\d+)?)\s*$', line)
            if not match:
                continue
            for item, percent in [(match[1], match[2]), (match[3], match[4])]:
                item = re.sub(r'\s+', ' ', item).strip()
                # Reject summary totals and fragments of wrapped product names.
                if norm(item) in allowed_items and 0 <= float(percent) <= 10:
                    rows.append(dict(Item=item, P_percent=float(percent),
                                     g_P_per_kg=float(percent)*10, PDF_page=page_no,
                                     source='SI Table S2; automatic unwrapped-row extraction'))
    df = pd.DataFrame(rows).drop_duplicates('Item')
    # Reject conflicting normalized names instead of silently choosing a coefficient.
    df['key'] = df.Item.map(norm)
    assert df.groupby('key').P_percent.nunique().max() == 1
    return df.drop_duplicates('key')


# SI Table S3, PDF pp.121-122. Units kg P/t product; NOT S2 composition %.
# These 17 named crops define the modeled ACS boundary; excluded crops are disclosed.
CROPS = [
    ('Rice',4.1,2.9),('Wheat',5.1,3.7),('Maize (corn)',4.0,2.7),
    ('Barley',5.1,3.6),('Sorghum',4.8,3.4),('Millet',4.5,3.5),
    ('Rye',5.2,3.6),('Oats',6.0,3.8),('Potatoes',0.8,0.7),
    ('Sweet potatoes',1.,1.),('Cassava, fresh',0.2,0.1),
    ('Soya beans',0.2,0.2),('Rape or colza seed',7.,7.),
    ('Olives',0.7,0.2),('Sugar beet',0.7,0.5),('Sugar cane',0.3,0.3),
    ('Seed cotton, unginned',16.,12.2)]


def data_engineering(src, si):
    prod_path = find(src, 'Agricultural products_P_result*.xlsx')
    raw = pd.read_excel(prod_path, sheet_name='product_P_result (tons)')
    raw.columns = [int(c) if str(c).isdigit() else c for c in raw.columns]
    years = list(range(1961,2023))
    assert set(years) <= set(raw.columns)
    assert not raw.duplicated(['Country','Product']).any()
    assert (raw[years].min().min() >= 0)
    world = raw.loc[raw.Country.eq('World')].copy()
    assert len(world) > 0
    long = world.melt(id_vars=['Country','Product'], value_vars=years,
                      var_name='Year', value_name='P_tons')
    assert long.P_tons.notna().all()
    long['P_Mt'] = long.P_tons/1e6
    save(long, 'historical_product_P_1961_2022.csv')
    # These totals mix primary products, processed products and live animals.
    # They describe throughput by product group, NOT net crop harvest or external input.
    totals = long.groupby('Year',as_index=False).P_Mt.sum()
    save(totals,'historical_product_throughput.csv')
    production_path = find(src,'2022.csv','Raw data on agricultural production')
    activities = read_csv(production_path)
    allowed_items = set(activities.Item.map(norm))
    for p in src.rglob('2022.csv'):
        if 'exports' in str(p).lower() or 'imports' in str(p).lower():
            allowed_items.update(read_csv(p).Item.map(norm))
    coeff = extract_si_coefficients(si, allowed_items)
    save(coeff.drop(columns='key'),'si_product_coefficients.csv')
    production = activities.loc[activities.Area.eq('World') & activities.Element.eq('Production') & activities.Unit.eq('t')].copy()
    production['key'] = production.Item.map(norm)
    joined = production.merge(coeff, on='key', how='left', suffixes=('','_SI'), validate='many_to_one')
    joined['P_tons'] = joined.Value*joined.g_P_per_kg/1000
    save(joined, 'production_2022_coefficient_join.csv')
    trade_stats = []
    for label in ['exports','imports']:
        paths = [p for p in src.rglob('2022.csv') if label in str(p).lower()]
        if len(paths) != 1:
            raise ValueError(f'Missing trade data {label}')
        t = read_csv(paths[0])
        t = t.loc[t.Area.eq('World') & t.Unit.eq('t')].copy()
        t['key'] = t.Item.map(norm)
        t = t.merge(coeff,on='key',how='left',validate='many_to_one',suffixes=('','_SI'))
        t['P_tons'] = t.Value*t.g_P_per_kg/1000
        save(t, f'{label}_2022_coefficient_join.csv')
        trade_stats.append(dict(kind=label,matched=t.g_P_per_kg.notna().sum(),
                                valid_activity=t.Value.notna().sum(),covered_P_Mt=t.P_tons.sum()/1e6))
    save(pd.DataFrame(trade_stats),'trade_coverage.csv')
    # Fertilizer CSV P(t) column is not reliably populated; recompute from Value.
    f = read_csv(find(src,'Nutrient phosphate*.csv'))
    f = f.loc[f.Element.eq('Agricultural Use') & f.Unit.eq('t')].copy()
    # Dataset has no World/regional rows; avoid China aggregate/territory overlap.
    f = exclude_aggregates(f)
    fert = f.groupby('Year').Value.sum(min_count=1)*0.4364/1e6
    save(fert.rename('fertilizer_Mt_P').reset_index(),'fertilizer_history.csv')
    population = read_csv(find(src,'Global country-level population data.csv'))
    pop = population.loc[population.Area.eq('World') & population.Element.eq('Total Population - Both sexes')].set_index('Year').Value*1000
    assert pop.index.is_unique
    land = read_csv(find(src,'Global level cropland area.csv'))
    land = land.loc[land.Area.eq('World') & land.Element.eq('Area') & land.Item.eq('Cropland')].set_index('Year').Value*1000
    assert land.index.is_unique
    # Bottom-up ACS uptake and harvest from S3. Every mapped item must be observed.
    s3 = pd.DataFrame(CROPS, columns=['Item','uptake_kg_per_t','harvest_kg_per_t'])
    s3 = s3.merge(production[['Item','Value']],on='Item',how='left',validate='one_to_one')
    assert s3.Value.notna().all(), s3.loc[s3.Value.isna(),'Item'].tolist()
    s3['harvest_Mt_P'] = s3.Value*s3.harvest_kg_per_t/1e9
    s3['uptake_Mt_P'] = s3.Value*s3.uptake_kg_per_t/1e9
    save(s3,'core_crop_uptake_2022.csv')
    # Animal products: primary meat, eggs (mass unit only), and raw milk only.
    def animal_k(item):
        if item.startswith('Raw milk of '): return 1.10
        if 'eggs' in item.lower(): return 2.04
        if item.startswith('Meat of cattle') or item.startswith('Meat of buffalo'): return 1.65
        if item.startswith('Meat of sheep') or item.startswith('Meat of goat'): return 3.37
        if item.startswith('Meat of pig '): return 2.02
        if item.startswith(('Meat of chickens','Meat of ducks','Meat of geese','Meat of turkeys')): return 2.03
        if item.startswith(('Meat of ','Horse meat','Game meat','Other meat')): return 2.14
        return np.nan
    animal = production.copy();animal['P_kg_per_t']=animal.Item.map(animal_k)
    animal=animal.loc[animal.P_kg_per_t.notna() & animal.Value.notna()].copy()
    animal['P_Mt']=animal.Value*animal.P_kg_per_t/1e9
    save(animal,'animal_products_2022.csv')
    stocks=activities.loc[activities.Area.eq('World') & activities.Element.eq('Stocks') & activities.Value.notna()].copy()
    # SI S3 excretion kg/head/year; bird stocks reported in thousand head.
    stock_k={'Buffalo':15.2,'Cattle':5.6,'Goats':0.1,'Sheep':0.1,'Horses':6.8,'Swine / pigs':2.4,'Chickens':0.135,'Ducks':0.384}
    stocks=stocks.loc[stocks.Item.isin(stock_k)].copy()
    assert set(stocks.Item)==set(stock_k), stocks.Item.tolist()
    stocks['heads']=stocks.Value*np.where(stocks.Unit.str.contains('1000'),1000,1)
    stocks['waste_Mt_P']=stocks.heads*stocks.Item.map(stock_k)/1e9
    save(stocks,'manure_2022.csv')
    audit={'world_rows':len(world),'all_rows':len(raw),'coefficient_count_extracted':len(coeff),
           'production_valid_t_items':int(production.Value.notna().sum()),
           'production_matched_valid_items':int((joined.Value.notna()&joined.g_P_per_kg.notna()).sum()),
           'fertilizer_last_year':int(fert.index.max()),'population_last_year':int(pop.index.max()),
           'land_last_year':int(land.index.max()),'core_crop_count':len(s3),
           'missing_revision_directory_files':sum(p.is_file() for p in (src/'Supplementary_dataset_PNAS_First_Revision').rglob('*'))}
    return dict(fert=fert,pop=pop,land=land,harvest=s3.harvest_Mt_P.sum(),
                nonfood=float(s3.loc[s3.Item.eq('Seed cotton, unginned'),'harvest_Mt_P'].sum()),
                uptake=s3.uptake_Mt_P.sum(),animal=animal.P_Mt.sum(),manure=stocks.waste_Mt_P.sum(),
                history=long,audit=audit)


def exclude_aggregates(d):
    aggregates=['World','Africa','Americas','Asia','Europe','Oceania','Northern America',
                'Central America','Caribbean','South America']
    d=d.loc[~d.Area.isin(aggregates)].copy()
    # If China aggregate exists use it, otherwise retain its constituent reporting areas.
    if d.Area.eq('China').any():
        d=d.loc[~d.Area.isin(['China, mainland','China, Hong Kong SAR','China, Macao SAR','China, Taiwan Province of'])]
    return d


@dataclass
class Subsystem:
    name: str

    def verify_mass_balance(self, edges, tolerance=1e-4):
        incoming=sum(v for s,t,v in edges if t==self.name)
        outgoing=sum(v for s,t,v in edges if s==self.name)
        # Stocks are explicit terminal nodes; they are not counted as external outputs below.
        delta=sum(v for s,t,v in edges if s==self.name and t.startswith('Stock:'))
        output=outgoing-delta
        error=abs(incoming-output-delta)/(incoming+1e-6)
        assert error<tolerance, f'{self.name}: {error}'
        return dict(system=self.name,input=incoming,output=output,stock_change=delta,relative_error=error)


class PMSModel(Subsystem):
    def __init__(self): super().__init__('PMS')


class CISModel(Subsystem):
    def __init__(self): super().__init__('CIS')


class ACSModel(Subsystem):
    def __init__(self): super().__init__('ACS')

    def calculate(self, fertilizer, organic, deposition, loss_fraction, harvest, residues):
        total=fertilizer+organic+deposition
        loss=total*loss_fraction
        stock=total-harvest-residues-loss
        # A negative stock means legacy P drawdown; never conceal it with abs() or clipping.
        return dict(Total_Input=total,Crop_Uptake=harvest+residues,Harvest=harvest,
                    Residues=residues,Water_Loss=loss,Soil_Legacy_P=stock)


class LBSModel(Subsystem):
    def __init__(self): super().__init__('LBS')


class RCSModel(Subsystem):
    def __init__(self): super().__init__('RCS')


class GlobalModel:
    """Five-sector teaching model; no claim to represent all 11 original sectors."""
    sectors=[PMSModel(),CISModel(),ACSModel(),LBSModel(),RCSModel()]

    def __init__(self, data, fertilizer, scale=1.):
        self.d=data; self.F=fertilizer*scale; self.scale=scale

    def run(self, reduce=0., replace=0.67, recycle=0.):
        assert 0<=reduce<=1 and 0<=replace<=1 and 0<=recycle<=1
        d=self.d;s=self.scale
        h=d['harvest']*s;a=d['animal']*s;w=d['manure']*s
        residues=(d['uptake']-d['harvest'])*s
        straw_return=residues*0.4       # SI S3 beta1
        straw_feed=residues*0.25        # SI S3 beta2
        nonfood=d['nonfood']*s          # cotton is not counted as edible food
        crop_feed=(h-nonfood)*0.25     # teaching assumption; not estimated from data
        food=h-nonfood-crop_feed+a
        food_waste=food*0.20            # teaching assumption; demand not fitted
        wastewater=food-food_waste
        recovery=wastewater*recycle
        baseline_manure=w*0.67         # SI S3 beta3
        manure=w*replace
        # New fertilizer displaces extra recovered P 1:1, then Reduce acts on the remainder.
        # This order permits real resource overlap and possible antagonistic interactions.
        fertilizer=max(0.,self.F-(manure-baseline_manure)-recovery)*(1-reduce)
        feed_total=a+w
        additive=feed_total*0.05        # teaching assumption, feed P partition
        natural_feed=feed_total-additive-crop_feed-straw_feed
        assert natural_feed>=0, 'Inconsistent feed partition'
        dep=d['land2022']*0.4/1e9*s     # SI S3 lambda1 kg/ha
        base_inputs=self.F+baseline_manure+straw_return+dep
        loss_fraction=(d['land2022']*(1.8+0.34)/1e9*s)/base_inputs
        acs=ACSModel().calculate(fertilizer,manure+straw_return+recovery,dep,loss_fraction,h,residues)
        # Chemical industry: phosphogypsum loss relative to product P, SI alpha11/12/1.
        chemical_products=fertilizer+additive
        chemical_loss=chemical_products*4.8*0.004/0.4364
        concentrate=chemical_products+chemical_loss
        mining_loss=concentrate*0.05     # teaching assumption (not full SI mining model)
        edges=[]
        def e(source,target,value):
            assert np.isfinite(value) and value>=0, (source,target,value)
            if value>0: edges.append((source,target,float(value)))
        e('Geological resource','PMS',concentrate+mining_loss)
        e('PMS','CIS',concentrate);e('PMS','Mining waste',mining_loss)
        e('CIS','ACS',fertilizer);e('CIS','LBS',additive);e('CIS','Chemical waste',chemical_loss)
        e('Atmospheric deposition','ACS',dep);e('Natural pasture/feed','LBS',natural_feed)
        e('ACS','LBS',crop_feed+straw_feed);e('ACS','RCS',h-crop_feed)
        e('ACS','ACS',straw_return)
        e('ACS','Crop residue waste',residues-straw_return-straw_feed)
        e('ACS','Surface water',acs['Water_Loss'])
        if acs['Soil_Legacy_P']>=0:e('ACS','Stock: soil legacy P',acs['Soil_Legacy_P'])
        else:e('Legacy P mobilization','ACS',-acs['Soil_Legacy_P'])
        e('LBS','ACS',manure);e('LBS','RCS',a);e('LBS','Manure loss',w-manure)
        e('RCS','ACS',recovery);e('RCS','Food waste',food_waste)
        e('RCS','Nonfood waste',nonfood)
        e('RCS','Wastewater discharge',wastewater-recovery)
        balance=pd.DataFrame([sector.verify_mass_balance(edges) for sector in self.sectors])
        names={x.name for x in self.sectors}
        external_in=sum(v for source,target,v in edges if source not in names and target in names)
        external_out=sum(v for source,target,v in edges if source in names and target not in names and not target.startswith('Stock:'))
        stock=sum(v for source,target,v in edges if target.startswith('Stock:'))
        err=abs(external_in-external_out-stock)/(external_in+1e-6)
        assert err<1e-4,err
        balance.loc[len(balance)]=['GLOBAL',external_in,external_out,stock,err]
        result=dict(fertilizer_Mt= fertilizer,new_P_Mt=concentrate+mining_loss,
                    environmental_loss_Mt=external_out,water_loss_Mt=acs['Water_Loss'],
                    soil_stock_delta_Mt=acs['Soil_Legacy_P'],harvest_Mt=h,
                    ACS_PUE=h/acs['Total_Input'],LBS_PUE=a/feed_total,
                    recovered_manure_Mt=manure,recovered_sewage_Mt=recovery,
                    food_P_Mt=food,reduce=reduce,replace=replace,recycle=recycle)
        return result,edges,balance,acs


def extrapolate(series, target):
    sample=series.dropna().tail(10)
    assert (sample>0).all() and len(sample)>=5
    slope,intercept=np.polyfit(sample.index.to_numpy(dtype=float),np.log(sample.to_numpy(dtype=float)),1)
    return float(np.exp(intercept+slope*target)),float(slope)


def sensitivity(model, baseline):
    rows=[]
    # Full deterministic factorial grid: no synthetic noise, no seed dependence, no selection by p-value.
    for r,m,c in itertools.product(np.linspace(0,.2,7),np.linspace(.67,.75,7),np.linspace(0,.6,7)):
        result,*_=model.run(r,m,c)
        rows.append(dict(Reduce=r,Replace=m,Recycle=c,
                         avoided_loss=baseline['environmental_loss_Mt']-result['environmental_loss_Mt']))
    df=pd.DataFrame(rows);save(df,'policy_factorial_grid.csv')
    main=['Reduce','Replace','Recycle']
    centered=df[main]-df[main].mean()
    x=centered.copy()
    for a,b in itertools.combinations(main,2): x[a+'*'+b]=centered[a]*centered[b]
    x=(x-x.mean())/x.std(ddof=0)
    y=(df.avoided_loss-df.avoided_loss.mean())/df.avoided_loss.std(ddof=0)
    fit=sm.OLS(y,sm.add_constant(x)).fit()
    # Robust p-values to reduce heteroscedasticity effects; still conditional on this model grid.
    fit=fit.get_robustcov_results(cov_type='HC3')
    records=[]
    for name,beta,p,se in zip(['const']+list(x),fit.params,fit.pvalues,fit.bse):
        interaction='not an interaction'
        if '*' in name:
            interaction='无显著交互作用' if p>=.05 else ('协同增强' if beta>0 else '拮抗削弱')
        records.append(dict(term=name,standardized_beta=beta,HC3_se=se,p_value=p,interaction=interaction))
    stats=pd.DataFrame(records);save(stats,'policy_regression.csv')
    (OUT/'policy_regression_summary.txt').write_text(fit.summary().as_text(),encoding='utf8')
    # Controls for numerical cancellation in deterministic factorial fits.
    assert np.linalg.matrix_rank(sm.add_constant(x).to_numpy())==len(x.columns)+1
    return stats,dict(R_squared=float(fit.rsquared),n=int(fit.nobs),
                      response='avoided environmental loss (positive = benefit)',
                      inference='deterministic model grid, HC3; not observational or causal evidence')


def plot_sankey(edges):
    names=list(dict.fromkeys([node for s,t,v in edges for node in [s,t]]))
    mapping={n:i for i,n in enumerate(names)}
    # Display straw returned within ACS as an explicit node rather than a self-link.
    if any(s==t for s,t,v in edges):
        names.append('Straw return');mapping['Straw return']=len(names)-1
    shown=[]
    for s,t,v in edges:
        shown.extend([(s,'Straw return',v),('Straw return',t,v)] if s==t else [(s,t,v)])
    fig=go.Figure(go.Sankey(node=dict(label=names,pad=22,thickness=20),
        link=dict(source=[mapping[s] for s,t,v in shown],target=[mapping[t] for s,t,v in shown],
                  value=[v for s,t,v in shown],hovertemplate='%{source.label} → %{target.label}<br>%{value:.4f} Mt P<extra></extra>')))
    fig.update_layout(title='2022 five-sector teaching model (17 core crops; Mt P/year)',height=850,font_size=13)
    fig.write_html(OUT/'sankey_2022.html',include_plotlyjs=True)
    (OUT/'sankey_2022.json').write_text(fig.to_json(),encoding='utf8')


def benchmark_table(d, scenarios, f2022):
    records=[]
    def add(name,ref,value,status,reason):
        err=None if value is None else abs(value-ref)/(abs(ref)+1e-20)*100
        records.append(dict(indicator=name,reference=ref,computed=value,relative_deviation_percent=err,status=status,explanation=reason))
    add('1961 fertilizer Mt P',4.9,float(d['fert'].loc[1961]),'independent calculation','Value P2O5 × 0.4364, national sum with China overlap removed')
    add('2022 fertilizer Mt P',20.5,f2022,'extrapolation','Last ten available years log-linear extrapolation to 2022; not 2022 observation')
    add('2050 BAU fertilizer Mt P',26.9,scenarios.iloc[0].fertilizer_Mt,'teaching projection','Historical population growth extrapolation, fixed per-capita structure')
    add('LBS PUE historical mean',.23,None,'not comparable','Computed 2022 PUE covers selected products and eight stock classes, not a 62-year mean')
    for n,ref in [('1961-2022 mining Mt P',1153),('S4.3 NPR change %',-22.15),('S4.3 CFR change %',-76.9),('S4.3 loss change %',-77),('S2.3 industrial feed change %',-26),('S2.3 feed grain change %',-35),('S2.3 NPR change %',-17),('S2.3 crop PUE gain %',18),('S2.3 livestock PUE gain %',36),('S5 NPR change %',-97),('S5 loss change low %',-33),('S5 loss change high %',-98),('single policy countries at PUE70%',8),('all policies countries at PUE70%',17),('countries still below PUE70%',18)]:
        add(n,ref,None,'not independently reproduced','Required full-sector/country scenario inputs absent; 3R coursework settings differ from SI S15')
    return pd.DataFrame(records)


def main():
    global OUT
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-data',type=Path,default=HERE.parent/'source_data')
    parser.add_argument('--population-projection',type=Path)
    args=parser.parse_args();OUT=HERE/'outputs';OUT.mkdir(exist_ok=True)
    si=find(HERE.parent,'*sapp.pdf')
    d=data_engineering(args.source_data,si)
    f2022,f_growth=extrapolate(d['fert'],2022)
    d['land2022']=float(d['land'].loc[2022]) if 2022 in d['land'].index else extrapolate(d['land'],2022)[0]
    if args.population_projection:
        pop=read_csv(args.population_projection).set_index('Year').Population
        pop2022,pop2050=float(pop.loc[2022]),float(pop.loc[2050]);pop_method='user supplied projection'
        assert pop2022>0 and pop2050>0
    else:
        pop2022,growth=extrapolate(d['pop'],2022)
        pop2050,_=extrapolate(d['pop'],2050)
        pop_method='2012-2021 historical log-linear extrapolation; NOT UN2019/SSP projection'
    model=GlobalModel(d,f2022)
    result,edges,balance,acs=model.run()
    save(pd.DataFrame(edges,columns=['source','target','Mt_P']),'flows_2022.csv');save(balance,'balance_2022.csv')
    save(pd.DataFrame([acs]),'acs_2022.csv');plot_sankey(edges)
    future=GlobalModel(d,f2022,pop2050/pop2022)
    scenarios=[]
    for name,params in [('BAU',(0,.67,0)),('Reduce20%',(.2,.67,0)),('Replace75%',(0,.75,0)),('Recycle60%',(0,.67,.6)),('3R',(.2,.75,.6))]:
        r,e,b,a=future.run(*params);r['scenario']=name;scenarios.append(r)
        save(b,f'balance_2050_{name.replace("%","")}.csv')
    comparisons=pd.DataFrame(scenarios)
    for column in ['fertilizer_Mt','new_P_Mt','environmental_loss_Mt']:
        comparisons[column+'_change_percent']=100*(comparisons[column]/comparisons.iloc[0][column]-1)
    save(comparisons,'scenarios_2050.csv')
    fig=go.Figure()
    for col in ['fertilizer_Mt','new_P_Mt','environmental_loss_Mt']:
        fig.add_bar(name=col,x=comparisons.scenario,y=comparisons[col])
    fig.update_layout(title='2050 population-scaled teaching scenarios',yaxis_title='Mt P/year',barmode='group')
    fig.write_html(OUT/'scenarios_2050.html',include_plotlyjs=True)
    history=go.Figure()
    for cat,g in d['history'].groupby('Product'):
        history.add_scatter(x=g.Year,y=g.P_Mt,name=str(cat),mode='lines')
    history.update_layout(title='World product-group P throughput (do not sum as crop harvest)',yaxis_title='Mt P/year')
    history.write_html(OUT/'history_1961_2022.html',include_plotlyjs=True)
    regression,reg_audit=sensitivity(future,scenarios[0])
    benchmarks=benchmark_table(d,comparisons,f2022);save(benchmarks,'benchmark_comparison.csv')
    audit=dict(data=d['audit'],population_method=pop_method,population_2022=pop2022,population_2050=pop2050,
        population_ratio=pop2050/pop2022,fertilizer_2022_Mt=f2022,fertilizer_log_growth=f_growth,
        model_2022=result,regression=reg_audit,
        assumptions={'crop_feed_fraction':.25,'food_waste_fraction':.20,'feed_additive_fraction':.05,
                     'mining_loss_per_concentrate':.05,'baseline_sewage_recovery':0,
                     'extra_recycled_P_substitution_efficiency':1.,'constant_food_output_under_reduce':True},
        max_2022_balance_error=float(balance.relative_error.max()),
        benchmark_independently_reproduced_within_3pct=int(((benchmarks.relative_deviation_percent<3)&benchmarks.status.eq('independent calculation')).sum()))
    (OUT/'audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf8')
    files=[p for p in args.source_data.rglob('*') if p.is_file()]
    # Hash every used dataset and the analysis source for provenance.
    keys=[si,find(args.source_data,'Agricultural products_P_result*.xlsx'),find(args.source_data,'Nutrient phosphate*.csv'),find(args.source_data,'Global country-level population data.csv'),find(args.source_data,'Global level cropland area.csv'),find(args.source_data,'2022.csv','Raw data on agricultural production')]
    keys += [p for p in args.source_data.rglob('2022.csv') if 'exports' in str(p).lower() or 'imports' in str(p).lower()]
    keys += [Path(__file__)]
    if args.population_projection:keys.append(args.population_projection)
    hashes=[dict(file=str(p.relative_to(HERE.parent)) if p.is_relative_to(HERE.parent) else p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in keys]
    save(pd.DataFrame(hashes),'input_sha256.csv')
    write_report(audit,comparisons,regression,benchmarks,acs)
    print('2022 ACS (Mt P/year):\n',pd.Series(acs).to_string())
    print('\nMass balance assertions passed (<1e-4):\n',balance.to_string(index=False))
    print('\n2050 scenarios:\n',comparisons.to_string(index=False))
    print('\nCentered + standardized HC3 regression:\n',regression.to_string(index=False))
    print('\nR2=',reg_audit['R_squared'],'; audit=',OUT/'audit.json')


def write_report(audit,scenarios,regression,benchmarks,acs):
    # The report is generated solely from this run. No numerical result is hand-entered.
    def table(df):
        header='| '+' | '.join(map(str,df.columns))+' |\n'
        header+='| '+' | '.join(['---']*len(df.columns))+' |\n'
        for row in df.itertuples(index=False,name=None):
            header+='| '+' | '.join('未复算' if pd.isna(v) else (f'{v:.5g}' if isinstance(v,(float,np.floating)) else str(v)) for v in row)+' |\n'
        return header
    a=audit;d=a['data'];bau=scenarios.iloc[0];r=scenarios.iloc[-1]
    report=f'''# 全球人为磷循环复现与 2050 年 3R 情景报告

## 1. 研究边界与证据

本报告依据本目录 Liu 等（2026）正文、181 页补充 PDF 与任务书七项下的五个评分维度组织。代码实现三个课堂任务，结果由脚本自动写入本报告及 outputs。研究区分原始统计、作者已有计算、补充材料系数和课堂假设，避免将输入的文献数值当作独立复现成果。所有通量均为 Mt P/年，存量项表示该年变化而非历史累计存量。

任务书列出的第一轮补充数据目录实际上没有文件，缺少 460 类含磷率 Excel、2050 人口预测和 ACSPModel。原始目录仍有生产、贸易、纯磷宽表和土地数据。程序直接从 SI 表 S2 自动提取无换行歧义的双栏系数，共 {d['coefficient_count_extracted']} 项，与实物吨表按产品名称连接，按 g/kg 除以 1000 换算纯磷吨；长名称无法可靠解析的项目保留缺失，不补零、不猜系数。2022 年有值的生产项目 {d['production_valid_t_items']} 项，成功连接 {d['production_matched_valid_items']} 项。逐项覆盖记录和贸易换算见 CSV，覆盖部分不能声称等于全球全部产品净产出。

## 2. 任务一：清洗与 ACS

历史宽表含 {d['all_rows']} 行，其中 World 有 {d['world_rows']} 行。程序只选 World，避免世界值与各国值双计；规整年份，检验国家—类别键唯一性和非负性，输出 1961—2022 年分类时间序列。此表已经是纯磷吨，禁止再次乘含磷率。产品类别包含加工品和活畜，分类吞吐总和不能充当作物收获量或矿石输入。2022 年生产、出口、进口则从实物吨表重新换算，供独立检查，全球进出口统计差异不作为社会系统新增磷。

ACS 使用 SI 表 S3 的 17 种明确命名作物，按产量分别乘吸收系数与收获系数，二者之差作为秸秆磷。这里未覆盖水果蔬菜及其他作物，故是核心作物子边界。表 S3 大豆系数仅为 0.2 kg/t，明显值得核验，代码忠实采用并在系数文件留痕，未擅自改值。化肥源表仅到 {d['fertilizer_last_year']} 年，且 P(t) 列部分为零，因此重算 Value×0.4364，并剔除中国汇总与分地区重叠。以最近十年对数趋势外推 2022 化肥为 {a['fertilizer_2022_Mt']:.4f}，未使用 20.5 倒推校准。

大气沉降按耕地面积乘 0.4 kg/ha，径流和淋溶以 1.8、0.34 kg/ha 确定基年损失率，均来自 S3。土壤年存量变化按输入减去收获、秸秆和水损失求得；秸秆 40% 还田、25% 饲用，内部循环在系统边界中相消。计算吸收量为 {acs['Crop_Uptake']:.4f}，收获量 {acs['Harvest']:.4f}，水损失 {acs['Water_Loss']:.4f}，土壤年净累积 {acs['Soil_Legacy_P']:.4f}。守恒残差推得的土壤存量不是独立观测证据。

## 3. 任务二：五系统闭环与图件

PMS、CIS、ACS、LBS、RCS 分别建立模型类。养殖端用八种牲畜存栏乘 S3 排泄系数，注意鸟类的千只单位；初级肉、蛋、奶单独以吨计，避免把鸡蛋个数与吨相加。总饲料磷由动物产品与排泄反推，天然草地饲料明确列为外部输入，化工饲料添加剂与种植饲料仅为内流。消费端食物磷分为食物废弃物与污水，回收磷返回 ACS，不重复计入新增矿磷。

由于完整活动量缺失，采矿损失占精矿磷 5%、饲料添加剂占饲料磷 5%、作物收获 25% 用于饲料、食物损失 20% 均属课堂假设。CIS 磷石膏按 S3 的 4.8×0.004/0.4364 估计，未涵盖原文所有工业支路。本模型未包含独立水产、林业、食品加工系统，不将五系统图标为原文十一系统全量复现。

程序分别核对五个节点与外部总边界，存量流单列，内部贸易和还田流不算外部输入。2022 年最大相对误差 {a['max_2022_balance_error']:.3e}，小于严格阈值 1e-4；负流量、缺失核心作物、退化设计矩阵会主动报错。零残差证明账目一致，不能证明假设真实。桑基图拓扑含自然饲料、沉降、采矿废物、水体和土壤终端，秸秆自循环拆为独立节点，支持悬浮读取数值，HTML 内嵌 Plotly 可离线打开。

## 4. 任务三：2050 外推与政策交互

人口原始表只到 {d['population_last_year']} 年。缺少任务书所称 SSP 表时，采用 2012—2021 世界人口对数线性趋势外推，2022 年 {a['population_2022']/1e9:.3f} 十亿人，2050 年 {a['population_2050']/1e9:.3f} 十亿人，需求倍数 {a['population_ratio']:.4f}。这是透明的替代情景，不是 UN2019 中位预测，也不是完整人口—饮食需求模型。用户可通过命令行传入正式预测 CSV 替换。BAU 固定人均产品、饲料结构与系数，所有活动按人口倍数放大。

Reduce 减施 20%；Replace 将粪便还田率从 S3 的 67% 提到 75%；Recycle 将污水磷回收从假设的零提高到 60%。回收率作用于模型全部污水磷，假设其均可处理且等效替代肥料，未模拟鸟粪石结晶条件、氮镁供给及能耗，属于技术可达上界。新增回收先一比一替代化肥，再对剩余化肥减施，避免把重叠节约相加。维持食物产出是情景约束，作物减产风险需田间试验检验。

{table(scenarios[['scenario','fertilizer_Mt','new_P_Mt','environmental_loss_Mt','ACS_PUE']])}

3R 相对 BAU 的新增矿磷变化 {r['new_P_Mt_change_percent']:.2f}%，环境外排变化 {r['environmental_loss_Mt_change_percent']:.2f}%，不能直接与原文 S5 的 -97% 比较。环保口径为外部废物和水损失合计，不把仍有潜在农用价值的土壤净累积计作当期外排；水体负荷也不等于所有废物直接入河。

敏感性采用 7×7×7 共 {a['regression']['n']} 个确定性组合，参数范围分别 0—20%、67—75%、0—60%。先均值中心化，再构造三个两两乘积，最后自变量与响应均做 Z-score。因变量采用“相对 BAU 避免的环境损失”，因此正系数表示改善，按任务书显著正交互为协同、负交互为拮抗。拟合 R²={a['regression']['R_squared']:.5f}，使用 HC3 标准误；完整统计见回归文本。

{table(regression[['term','standardized_beta','p_value','interaction']])}

该显著性只描述设定模型的响应面：R²=1 源于公式本身为可被回归完全表达的二次多项式，残差仅为浮点误差；p 值显示为零属于数值下溢，不表示概率严格为零。网格并非真实随机样本，不能将这些显著性作为政策实证。交互必须接受实际符号，不能为满足量规预设节肥与还田必然协同。SI 表 S11/S12 的对象是产品贡献敏感性，与本政策交互不同。

## 5. 基准核验与量化管理

正文第 7—8 页及 SI 表 S15 的减肥为 30%、粪肥为 100% 回用，课堂则为 20%、75%，且增加 60% 污水回收，故二者边界与强度不同。正文和 SI 叙述中还存在 S2 子编号前后不一致，报告用措施名称辨识。完整核心对照表见 [benchmark_comparison.csv](outputs/benchmark_comparison.csv)：仅历史化肥可独立同口径核对，2022 及 2050 仅为外推比较；1153 Mt 历史开采、S4.3、饲料效率、S5、35 国达标数均列为未独立复算，不能把文献标称值填进计算列。

管理上优先建立粪污—耕地空间配对，课堂 3R 可还田粪肥 {r['recovered_manure_Mt']:.3f}、污水回收 {r['recovered_sewage_Mt']:.3f}，应按土壤有效磷与运输半径分配，避免把回收总量全部叠加到原有施肥上。减肥后维持产出的前提需要土壤检测与小区试验，土壤存量下降不能自动等同水质改善。污水回收方案应进一步加入收集率、工艺回收率及农用替代率，当前 60% 全污水可回收假设不宜直接作为工程承诺。国家对策需取得分国耕地、养殖和人口预测后再分组，现阶段不编造“8 国到 17 国”的复算名单。

## 6. 提交前自检与量规对应

数据工程 20%：相对路径、单位检查、键检查和六项守恒断言已实现。复现精度 25%：完整标称指标清单已列，但数据缺口和边界限制使关键指标偏差小于 3% 的优秀要求尚不能证实，不自评满分。情景回归 20%：3R 外推、中心化、标准化、p 值及交互判读均已输出，人口预测与鸟粪石工艺仍有限制。图件 15%：交互桑基图、情景柱图与历史曲线已生成；图形为课堂模型，不声称像素级复刻论文。报告 20%：正文与数据结果联动，建议对应回收量和替代约束，附可复核文件。

未发现将假设伪装成观测或将原文基准填作计算结果的情况；无法获得的数据明确缺失。代码、输入哈希和运行日志支持复核。本次仅完成本地交付，未提交课程 PR。该事实不影响本地结果检查，但 PR 交付仍需后续完成。

依据：本地正文 Fig.1、Fig.4 与方法；SI Text S5、Text S8、Tables S2/S3/S11/S12/S15；任务书第三、四、五、七节；source_data/README.md。原始资料只读，未改写。
'''
    (HERE/'report.md').write_text(report,encoding='utf8')


if __name__=='__main__':
    main()
