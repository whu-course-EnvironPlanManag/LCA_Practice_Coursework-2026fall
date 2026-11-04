"""AI辅助。Prompt：固定推荐方案，对照自建/委托，核算空间能力、贮存、事故池和建设触发条件。人工核验待课程组员确认。"""
from planning import *
from test_models import rows

def main():
    detail=rows('chemistry_dmfa.csv');net=json.loads((O/'network_summary.json').read_text());rec=json.loads((O/'recommended.json').read_text());dy=json.loads((O/'design_year.json').read_text());u=json.loads((O/'design_inventory.json').read_text())
    alternatives=[]
    for label,toll,stages in [('分期配置',P['outsourcing_toll_CNY_t'],P['phases']),('全期委托_低报价',900,[]),('全期委托_基准报价',1800,[]),('全期委托_高报价',2700,[])]:
        p=dict(P,phases=stages,outsourcing_toll_CNY_t=toll);r,_,_=simulate(detail,net,rec['collection'],rec['green'],rec['recovery'],rec['price_CNY_tLCE'],p)
        alternatives.append(dict(option=label,toll_CNY_t=toll,NPV_cost_CNY=r['NPV_cost_CNY'],total_CAPEX_CNY=r['total_CAPEX_CNY'],peak_funding_CNY=r['peak_funding_CNY'],Li_t=r['cumulative_Li_t']))
    write('implementation_comparison.csv',alternatives)
    flows=rows('network_assignments.csv');centers=defaultdict(float)
    for r in flows:centers[r['centre']]+=r['fraction_total']
    capacity=dy['capacity_tpa'];design=[]
    for name,share in centers.items():
        cap=capacity*share;storage=cap/P['operating_days']*P['storage_days'];design.append(dict(centre=name,flow_share=share,capacity_tpa=cap,actual_2030_tpa=dy['feed_t']*share,storage_t=storage,storage_area_m2=storage*P['inventory_footprint_m2_t'],land_screen_m2=cap*P['land_m2_per_tpa'],max_first_leg_km=max(r['distance_km'] for r in flows if r['centre']==name)))
    write('centre_capacity.csv',design)
    # 事故池采用明确设计工况，分设施核算，不把全市流量装入一个池。
    pools=[]
    for r in design:
        # 最大液体泄漏按单个罐100m3，消防25L/s×2h，汇水面积为集散地块20%，30mm事件降雨。
        rain=.03*r['land_screen_m2']*.2*.9;volume=25*2*3.6+100+rain-30
        pools.append(dict(centre=r['centre'],firewater_m3=180,leak_m3=100,rain_m3=rain,available_containment_m3=30,computed_m3=volume,reserved_pool_m3=math.ceil(volume/50)*50))
    write('accident_pools.csv',pools)
    # 估算未来固定资产强度，实际用地取决于厂房层数、公辅共享及消防间距。
    facilities=load('facilities_local_evidence.json')['observations'];local=next(r for r in facilities if r['evidence_id']=='LF01')
    local_ratio=local['total_investment_CNY']/(local['phase1_feed_tpa']+local['phase2_battery_scrap_tpa']+local['phase2_black_mass_tpa'])
    local_energy=next(r for r in facilities if r['evidence_id']=='LF02')['unit_energy_tce_tfeed']*1000
    dump('feasibility_summary.json',dict(local_mixed_feed_CAPEX_CNY_tpa=local_ratio,design_CAPEX_CNY_tpa=P['capex_CNY_per_tpa'],local_design_energy_kgce_tfeed=local_energy,model_site_energy_kgce_tpack=(u['electricity_kWh']*3.6+u['heat_MJ'])/29.3076,land_screen_m2=capacity*P['land_m2_per_tpa'],storage_t=capacity/P['operating_days']*P['storage_days'],treatment_design_m3_day=u['water_discharge_L']/1000*capacity/P['operating_days'],max_first_leg_km=max(r['distance_km'] for r in flows),design_electric_MW=u['electricity_kWh']*capacity/P['operation_hours']/1000,design_heat_MW=u['heat_MJ']*capacity/P['operation_hours']/3600,independent_land_and_permit_gate=True))
    # 组分分流及税费设计预算由同一计量记录生成。
    summary=[]
    for e in ['Li','Ni','Co','Mn']:
        summary.append(dict(element=e,input_kg_tpack=u[e+'_feed_kg'],product_kg_tpack=u[e+'_product_inherited_kg'],residue_kg_tpack=u[e+'_residue_kg']))
    write('unit_element_inventory.csv',summary)
    print('FEASIBILITY',alternatives)
if __name__=='__main__':main()
