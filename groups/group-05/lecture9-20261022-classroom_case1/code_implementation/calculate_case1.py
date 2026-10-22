from pathlib import Path
import csv, json

ROOT = Path(__file__).resolve().parent
DATA = ROOT.parent / 'case_files' / 'data_cohort'

def read(name):
    with (DATA / name).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def calculate():
    mfa = read('mfa_mass_balance.csv')
    incoming = sum(float(r['Mass_kg']) for r in mfa if r['Flow_Type'] == 'Raw_Material')
    outgoing = sum(float(r['Mass_kg']) for r in mfa if r['Flow_Type'] in ('Waste','Co_Product','Main_Product'))
    assert abs(incoming-outgoing) < 1e-8, 'Mass balance failed'
    lci = read('lci_emission_factors.csv')
    items = [r for r in lci if r['Flow_Name'] not in ('Net_Total_GWP','Virgin_PET_Benchmark','Net_GHG_Reduction')]
    baseline = sum(float(r['Amount_per_t_rPET'])*float(r['Emission_Factor']) for r in items)
    params = {r['Parameter_Name']:float(r['Value']) for r in read('tea_cost_parameters.csv')}
    electricity = next(float(r['Amount_per_t_rPET']) for r in items if r['Flow_Name']=='Electricity_Grid')
    green = baseline + electricity*(0.03-0.55)
    cost = params['Unit_LCOP']
    delta = electricity*(0.70-params['Electricity_Industrial'])
    result = {'mass_input_kg':incoming,'mass_output_kg':outgoing,'yield':0.8,'baseline_gwp':baseline,'green_gwp':green,'green_reduction_pct':100*(1-green/2250),'baseline_lcop':cost,'green_lcop':cost+delta,'cost_increase':delta,'cost_increase_pct':delta/cost*100,'green_margin':7600-cost-delta,'annual_green_margin':(7600-cost-delta)*16000}
    # Sensitivity: fixed annual feed, all per-feed loads and co-product yield fixed.
    # Extra 100 kg inert impurity replaces PET and becomes an additional solid residue.
    k=0.8/0.7
    extra_waste_cost=(0.1/0.7)*250
    result['yield70']={'feed_t_per_t':1/0.7,'annual_output_t':20000*0.7,'baseline_gwp':baseline*k,'green_gwp':green*k,'baseline_lcop':cost*k+extra_waste_cost,'green_lcop':(cost+delta)*k+extra_waste_cost,'extra_waste_cost_per_t':extra_waste_cost,'green_margin':7600-(cost+delta)*k-extra_waste_cost,'annual_green_margin':(7600-(cost+delta)*k-extra_waste_cost)*14000}
    assert abs(baseline-636)<1e-8
    assert abs(green-194)<1e-8
    assert abs(delta-42.5)<1e-8
    (ROOT/'calculation_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    with (ROOT/'scenario_comparison.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.writer(f); writer.writerow(['scenario','yield','annual_output_t','GWP_kgCO2e_per_t','LCOP_RMB_per_t','margin_RMB_per_t'])
        for name,y,q,g,c in [('grid_80',.8,16000,baseline,cost),('green_80',.8,16000,green,cost+delta),('grid_70',.7,14000,baseline*k,cost*k+extra_waste_cost),('green_70',.7,14000,green*k,(cost+delta)*k+extra_waste_cost)]:
            writer.writerow([name,y,q,round(g,4),round(c,4),round(7600-c,4)])
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return result

if __name__=='__main__':
    calculate()

