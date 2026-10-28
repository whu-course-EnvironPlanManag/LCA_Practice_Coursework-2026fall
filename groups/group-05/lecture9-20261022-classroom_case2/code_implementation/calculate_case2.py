"""Case 2: audit source data, solve a consistent ideal recycle model, and assess scenarios.
Run: python calculate_case2.py. Only Python standard library is required.
Original CSVs are read-only. All reconciled streams are explicitly identified.
"""
from pathlib import Path
import csv
import json

ROOT = Path(__file__).resolve().parent
DATA = ROOT.parent / 'case_files' / 'data_cohort'
# Consistent atomic masses; kg/kmol. Avoid rounded molecular masses that break balances.
ATOMS = {'C': 12.011, 'H': 1.008, 'O': 15.999}
FORMULAS = {'CO2': {'C':1,'O':2}, 'H2': {'H':2}, 'CH3OH': {'C':1,'H':4,'O':1},
            'H2O': {'H':2,'O':1}, 'O2': {'O':2}, 'CO': {'C':1,'O':1}}
MW = {s:sum(ATOMS[e]*n for e,n in f.items()) for s,f in FORMULAS.items()}
FIELDS = {'CO2':'co2_wt_pct','H2':'h2_wt_pct','CH3OH':'meoh_wt_pct','H2O':'h2o_wt_pct','O2':'o2_wt_pct'}

def read_csv(name):
    with (DATA/name).open(encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))

def save_csv(name, rows):
    with (ROOT/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

def species_from_raw(row):
    return {s:float(row['mass_flow_per_ton_product_kg'])*float(row[col])/100/MW[s] for s,col in FIELDS.items()}

def elements(stream):
    return {e:sum(n*FORMULAS[s].get(e,0)*ATOMS[e] for s,n in stream.items()) for e in ATOMS}

def add(*streams):
    return {s:sum(st.get(s,0) for st in streams) for s in MW}

def mass(stream):
    return sum(n*MW[s] for s,n in stream.items())

def conservation(name, inputs, outputs):
    ei,eo=elements(add(*inputs)),elements(add(*outputs))
    return [{'boundary':name,'element':e,'input_kg':ei[e],'output_kg':eo[e],
             'difference_kg':ei[e]-eo[e],
             'relative_error_pct':100*abs(ei[e]-eo[e])/max(abs(ei[e]),1e-12)} for e in ATOMS]

def solve_linear(matrix, vector):
    """Gaussian elimination with partial pivoting, for the explicit recycle equations."""
    a=[list(map(float,r))+[float(b)] for r,b in zip(matrix,vector)]
    n=len(a)
    for c in range(n):
        pivot=max(range(c,n),key=lambda r:abs(a[r][c])); a[c],a[pivot]=a[pivot],a[c]
        if abs(a[c][c])<1e-12: raise ValueError('Singular balance equations')
        z=a[c][c]; a[c]=[v/z for v in a[c]]
        for r in range(n):
            if r!=c:
                z=a[r][c]; a[r]=[v-z*w for v,w in zip(a[r],a[c])]
    return [a[r][-1] for r in range(n)]

def audit(raw):
    r={row['stream_id']:row for row in raw}
    m={k:float(v['mass_flow_per_ton_product_kg']) for k,v in r.items()}
    checks=[]
    def record(name,a,b,unit='kg'):
        checks.append({'check':name,'value':a,'reference':b,'difference':a-b,'unit':unit})
    record('Mixer: fresh + recycle vs inlet',m['S01']+m['S02']+m['S06'],m['S07'])
    record('Separator: inlet vs liquid + gas',m['S08'],m['S09']+m['S10'])
    record('Splitter: offgas vs recycle + purge',m['S10'],m['S06']+m['S11'])
    record('Synthesis overall: fresh vs MeOH + water + purge',m['S01']+m['S02'],m['S12']+m['S13']+m['S11'])
    record('Electrolyzer: total water vs H2 + O2',m['S04'],m['S02']+m['S05'])
    record('Whole plant external: CO2 + net water vs MeOH + O2 + purge',m['S01']+m['S03'],m['S12']+m['S05']+m['S11'])
    record('Recycle / fresh mass ratio',m['S06']/(m['S01']+m['S02']),3.8,'kg/kg')
    record('Actual recycle fraction',m['S06']/m['S10']*100,99,'%')
    record('Ideal 25% conversion + 99% recycle overall conversion',.25/(1-.99*.75)*100,96,'%')
    raw_carbon=(elements(species_from_raw(r['S12']))['C']/elements(species_from_raw(r['S01']))['C'])*100
    record('CSV known-species product carbon / fresh CO2 carbon',raw_carbon,96,'%')
    for k,row in r.items():
        pct=sum(float(row[col]) for col in list(FIELDS.values())+['other_inerts_wt_pct'])
        record(k+' composition sum',pct,100,'%')
    save_csv('raw_data_audit.csv',checks)
    raw_el=conservation('raw synthesis / listed species only',
                        [species_from_raw(r[k]) for k in ['S01','S02']],
                        [species_from_raw(r[k]) for k in ['S12','S13','S11']])
    save_csv('raw_known_species_elements.csv',raw_el)
    return checks,raw_el

def balanced_model(x=.25,recycle_fraction=.99):
    # Unknowns [reactor CO2 inlet A, fresh CO2 F, recycle CO2 R, purge CO2 P, reaction extent xi]
    # A-F-R=0; R-r(1-x)A=0; P-(1-r)(1-x)A=0; xi-xA=0; xi=1000/MW(MeOH).
    r=recycle_fraction
    matrix=[[1,-1,-1,0,0],[-r*(1-x),0,1,0,0],[-(1-r)*(1-x),0,0,1,0],[-x,0,0,0,1],[0,0,0,0,1]]
    vector=[0,0,0,0,1000/MW['CH3OH']]
    a,f,rc,p,xi=solve_linear(matrix,vector)
    residuals=[sum(v*z for v,z in zip(row,[a,f,rc,p,xi]))-b for row,b in zip(matrix,vector)]
    streams={
        'fresh_gas':{'CO2':f,'H2':3*f},
        'reactor_inlet':{'CO2':a,'H2':3*a},
        'reactor_outlet':{'CO2':a-xi,'H2':3*(a-xi),'CH3OH':xi,'H2O':xi},
        'separator_gas':{'CO2':a-xi,'H2':3*(a-xi)},
        'recycle':{'CO2':rc,'H2':3*rc},
        'purge':{'CO2':p,'H2':3*p},
        'crude_liquid':{'CH3OH':xi,'H2O':xi},
        'methanol':{'CH3OH':xi},'recovered_water':{'H2O':xi},
        'electrolyzer_water':{'H2O':3*f},'hydrogen':{'H2':3*f},'oxygen':{'O2':1.5*f},
        'net_water':{'H2O':3*f-xi},'fresh_co2':{'CO2':f}}
    checks=[]
    checks+=conservation('mixer',[streams['fresh_gas'],streams['recycle']],[streams['reactor_inlet']])
    checks+=conservation('reactor',[streams['reactor_inlet']],[streams['reactor_outlet']])
    checks+=conservation('separator',[streams['reactor_outlet']],[streams['separator_gas'],streams['crude_liquid']])
    checks+=conservation('splitter',[streams['separator_gas']],[streams['recycle'],streams['purge']])
    checks+=conservation('distillation',[streams['crude_liquid']],[streams['methanol'],streams['recovered_water']])
    checks+=conservation('synthesis overall',[streams['fresh_gas']],[streams['methanol'],streams['recovered_water'],streams['purge']])
    checks+=conservation('electrolyzer',[streams['electrolyzer_water']],[streams['hydrogen'],streams['oxygen']])
    checks+=conservation('whole plant external',[streams['fresh_co2'],streams['net_water']],[streams['methanol'],streams['oxygen'],streams['purge']])
    assert max(q['relative_error_pct'] for q in checks)<.01
    assert max(map(abs,residuals))<1e-9
    save_csv('balanced_element_checks.csv',checks)
    save_csv('balanced_streams.csv',[{'stream':k,'mass_kg_per_t_methanol':mass(st),**{s+'_kmol':st.get(s,0) for s in MW}} for k,st in streams.items()])
    return {'single_pass':x,'recycle_fraction':r,'overall_carbon_utilization':xi/f,
            'recycle_mass_ratio':mass(streams['recycle'])/mass(streams['fresh_gas']),
            'max_element_error_pct':max(q['relative_error_pct'] for q in checks),
            'max_equation_residual_kmol':max(map(abs,residuals)),
            'streams_kg':{k:mass(st) for k,st in streams.items()}}

def scenarios(lci,tea):
    e_rows=[r for r in lci if r['unit']=='kWh']
    energy=sum(float(r['flow_per_ton_product']) for r in e_rows)
    lookup={r['lci_inventory_item']:r for r in lci}
    nonpower={}
    for key in ['Direct_Fugitive_Emissions','Infrastructure_and_Catalyst']:
        row=lookup[key]; nonpower[key]=float(row['flow_per_ton_product'])*float(row['ef_scenario_a_green_power'])
    # Credits carry two negative signs in source CSV; normalize to a negative contribution once.
    for key in ['CO2_Capture_Credit','Byproduct_Oxygen_Credit']:
        row=lookup[key]; nonpower[key]=-abs(float(row['flow_per_ton_product'])*float(row['ef_scenario_a_green_power']))
    offset=sum(nonpower.values())
    green=energy*.035+offset; grid=energy*.55+offset
    fossil=float(lookup['Fossil_Benchmark_CtM']['gwp_scenario_a_kgCO2e'])
    abatement=(fossil-green)/1000
    fixed=float(tea[0]['non_electricity_cost_rmb_per_t'])
    price=float(tea[0]['fossil_methanol_price_rmb_per_t'])
    def pcrit(carbon): return (price+carbon*abatement-fixed)/energy
    # Fine grid (0.005 RMB/kWh) and raw 12-point reproduction.
    rows=[]
    for j in range(111):
        p=.05+j*.005; cost=energy*p+fixed; premium=cost-price
        rows.append({'electricity_price':p,'LCOM_RMB_per_t':cost,'green_premium_RMB_per_t':premium,'MAC_RMB_per_tCO2e':premium/abatement})
    save_csv('sensitivity_results.csv',rows)
    reproduction=[]
    for row in tea:
        p=float(row['electricity_price_rmb_per_kwh']); c=energy*p+fixed
        assert abs(c-float(row['lcom_rmb_per_t']))<.011
        reproduction.append({'electricity_price':p,'computed_LCOM':c,'source_LCOM':float(row['lcom_rmb_per_t']),
            'difference':c-float(row['lcom_rmb_per_t']),'computed_MAC':(c-price)/abatement,
            'source_MAC':float(row['mac_rmb_per_tCO2e'])})
    save_csv('tea_source_reproduction.csv',reproduction)
    contributions=[]
    for r in e_rows:
        amount=float(r['flow_per_ton_product'])
        contributions.append({'item':r['lci_inventory_item'],'green_kgCO2e':amount*.035,'grid_kgCO2e':amount*.55})
    contributions += [{'item':k,'green_kgCO2e':v,'grid_kgCO2e':v} for k,v in nonpower.items()]
    save_csv('lca_contributions.csv',contributions)
    pv=(.75-(fossil-offset)/energy)/(.75-.04)
    assert 0.50<pv<.55
    assert .15<pcrit(100)<.151
    return {'energy_kWh_per_t':energy,'PEM_share_pct':10296/energy*100,'nonpower_offset_kgCO2e':offset,
            'green_gwp':green,'grid_gwp':grid,'green_reduction_pct':(fossil-green)/fossil*100,
            'grid_increase_pct':(grid-fossil)/fossil*100,'abatement_tCO2e_per_t':abatement,
            'non_electric_cost':fixed,'fossil_price':price,'critical_price_no_carbon':pcrit(0),
            'critical_price_carbon100':pcrit(100),'carbon_price_assumption':100,
            'pv_min_share':pv,'pv_min_share_lecture_rounded':(.75-(2600+1423)/energy)/.71,
            'critical_EF_for_fossil_parity':(fossil-offset)/energy,
            'critical_EF_for_zero_GWP':-offset/energy,
            'low_price_LCOM':energy*.15+fixed,'high_price_LCOM':energy*.35+fixed,
            'low_price_MAC':(energy*.15+fixed-price)/abatement,
            'high_price_MAC':(energy*.35+fixed-price)/abatement}

def main():
    raw=read_csv('mfa_reaction_recycle_balance.csv')
    audits,raw_elements=audit(raw)
    m=balanced_model()
    s=scenarios(read_csv('lca_grid_scenarios_lci.csv'),read_csv('tea_lcom_sensitivity_data.csv'))
    # An alternative ideal split giving exactly 96%, holding single-pass conversion fixed.
    target=.96
    alternative_recycle=(1-.25/target)/.75
    result={'reaction_enthalpy_CO_hydrogenation_kJ_per_mol':-49.5-41.2,
        'model_assumptions':'Ideal pure CO2/H2, H2:CO2=3:1; sole net methanol reaction; complete liquid separation; no inert gas, reaction selectivity or kinetics supplied. Illustrative reconciliation, not a fit to original streams.',
        'balanced_model':m,'alternative_recycle_fraction_for_96pct':alternative_recycle,
        'course_LCA_TEA':s,'raw_audit':audits,'raw_known_species_elements':raw_elements}
    (ROOT/'calculation_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print('CO hydrogenation enthalpy:',result['reaction_enthalpy_CO_hydrogenation_kJ_per_mol'],'kJ/mol')
    for c in read_output_checks():
        print(f"{c['boundary']:22s} {c['element']} in={float(c['input_kg']):.9f} out={float(c['output_kg']):.9f} error={float(c['relative_error_pct']):.3e}%")
    print(json.dumps({'balanced_model':m,'course_LCA_TEA':s},ensure_ascii=False,indent=2))
    return result

def read_output_checks():
    with (ROOT/'balanced_element_checks.csv').open(encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))

if __name__=='__main__':
    main()
