"""AI辅助。Prompt：广州2026—2040，净成本/锂总量双目标及成本/净减排辅助分析，分期投资、来源假设分层、独立守恒和政策测试。
人工校验状态：尚待课程组员确认；自动检查见 verification.json。所有输出由输入数据计算。
"""
from model import *
from functools import lru_cache
P=load('plan_parameters.json')
YEARS=list(range(2026,2041))

def pareto2(rows, benefit="cumulative_Li_t"):
    valid=[dict(r) for r in rows if r['status']=='PASS']
    x=np.array([[r['NPV_cost_CNY'],-r[benefit]] for r in valid])
    # 对目标单位先缩放，支配判定不受元/t的数量级影响。
    spans=np.ptp(x,axis=0);z=(x-x.min(axis=0))/np.where(spans>0,spans,1)
    keep=np.array([not np.any(np.all(z<=v+1e-12,axis=1)&np.any(z<v-1e-12,axis=1)) for v in z])
    front=[r for r,k in zip(valid,keep) if k];f=x[keep]
    lo=f.min(axis=0);span=np.ptp(f,axis=0);norm=(f-lo)/np.where(span>0,span,1)
    for r,v in zip(front,norm):r['ideal_distance']=float(np.linalg.norm(v));r['normalized_cost'],r['normalized_Li_loss' if benefit=='cumulative_Li_t' else 'normalized_carbon_loss']=map(float,v)
    aa=min(front,key=lambda r:(r['NPV_cost_CNY'],-r[benefit]))
    bb=min(front,key=lambda r:(r['ideal_distance'],r['NPV_cost_CNY']))
    cc=min(front,key=lambda r:(-r[benefit],r['ideal_distance'],r['NPV_cost_CNY']))
    return front,dict(A=aa,B=bb,C=cc)

def inventory(detail,eta,green,price,col,net,overrides=None):
    a=dict(A);a['hydro_li_recovery']=eta
    # 更高提锂率需要更多精制；取凸增量用于明确的设计假设，不作实测拟合。
    intensity=((eta-.90)/.08)**2
    a['process_electricity_multiplier']*=1+P['recovery_extra_process_fraction']*intensity
    a['process_heat_MJ_kgcell']*=1+P['recovery_extra_process_fraction']*intensity
    a['product_sales_realization']=P['product_sales_realization']
    if overrides:a.update(overrides)
    u=unit_inventory(detail,0,green,price,a,net['weighted_first_leg_km'],col)
    u['cost_precision_CNY']=P['recovery_extra_service_CNY_t']*intensity
    # 有限排放情景：50元/吨入厂包环境税费预算，独立于治理OPEX；不将排放未知记作零。
    u['cost_environment_tax_CNY']=50
    # 水量核算：循环水补水中20%蒸发/产品带出，80%达标外排，作为用水消耗情景。
    u['water_consumptive_L']=u['water_gross_L']-.8*u['freshwater_L']
    u['water_discharge_L']=.8*u['freshwater_L']
    u['energy_lifecycle_MJ']=(u['electricity_kWh']*3.6*((1-green)*EB['GREET IO!AQ56']+green*EB['GREET IO!AI56'])/1e6+u['heat_MJ']*(1+EB['GREET IO!B22']/1e6)+(u['acid_kg']*EB['GREET IO!AE79']+u['peroxide_kg']*EB['GREET IO!G79']+u['soda_kg']*EB['GREET IO!E79'])*1055.05585/907.2+(net['weighted_first_leg_km']+a['refining_leg_km'])*2)
    u['water_consumptive_net_L']=u['water_consumptive_L']-u['water_credit_proxy_L']
    return u,a

def simulate(detail,net,col,green,eta,price,p=None,overrides=None,cache=None,keep=False):
    p=P if p is None else p
    yearly={y:[r for r in detail if r['year']==y] for y in YEARS}
    q={y:sum(r['scrap_pack_t'] for r in yearly[y])*col for y in YEARS}
    module=p['module_tpa'];caprate=p['capex_CNY_per_tpa']*p['capex_multiplier']*(1+p['recovery_extra_capex_fraction']*((eta-.90)/.08)**2)
    stages={};prev=0
    for start,end in p['phases']:
        cap=math.ceil(max(q[y] for y in range(start,end+1))/p['utilization_ceiling']/module)*module
        stages[start+p['commissioning_delay_years']]=(cap,max(0,cap-prev)*caprate);prev=cap
    capacity=0.;assets=0.;vintages=[];oldwc=0.;annual=[];unitrows=[];failed=[]
    for y in YEARS:
        key=(y,col,green,eta,price)
        if cache is not None and key in cache:u,a=cache[key]
        else:
            u,a=inventory(yearly[y],eta,green,price,col,net,overrides)
            if cache is not None:cache[key]=(u,a)
        invest=0
        if y in stages:
            capacity,invest=stages[y];assets+=invest;vintages.append((y,invest))
        outsource=q[y] if capacity==0 else max(0,q[y]-capacity*p['utilization_ceiling'])
        own=q[y]-outsource
        var=sum(v for k,v in u.items() if k.startswith('cost_') and k not in ['cost_revenue_CNY','cost_equipment_annual_equivalent_CNY'])
        opex=(var*q[y]+assets*p['fixed_om_fraction']+outsource*p['outsourcing_toll_CNY_t'])*p['opex_multiplier']
        revenue=u['cost_revenue_CNY']*q[y]
        wc=opex*p['working_capital_days']/365;delta_wc=wc-oldwc;oldwc=wc
        terminal=p.get('terminal_asset_realization',1.0)*sum(iv*max(0,1-(2041-v)/p['asset_life']) for v,iv in vintages) if y==2040 else 0
        cash=invest+delta_wc+opex-revenue-terminal-(wc if y==2040 else 0)
        discount=(1+p['discount_rate'])**(y-2025)
        li=u['Li_secondary_kg']*q[y]/1000
        case=dict(has_smelting=True,has_repair=False,Li=eta,Ni=a['other_metal_recovery'],Co=a['other_metal_recovery'],Mn=a['other_metal_recovery'],Cu=a['other_metal_recovery'],Al=a['other_metal_recovery'],F=a['fluorine_fixation'],powder=a['preprocess_capture'],Al_impurity=a['powder_Al_impurity'],Cu_impurity=a['powder_Cu_impurity'],energy_kgce_tLCE=u['energy_kgce_tLCE'],water_recycle=a['water_recirculation'],capacity_tpa=max(capacity,5000),rd_fraction=a['rd_fraction'])
        policy=assess(case,when=f'{y}-12-31')
        if policy['status']!='PASS':failed.append(str(y)+':'+','.join(k for k,v in policy['checks'].items() if v!='PASS'))
        annual.append(dict(year=y,collection=col,green=green,recovery=eta,feed_t=q[y],capacity_tpa=capacity,own_processed_t=own,outsourced_t=outsource,utilization=own/capacity if capacity else 0,investment_CNY=invest,cumulative_CAPEX_CNY=assets,OPEX_CNY=opex,revenue_CNY=revenue,working_capital_CNY=wc,net_operating_cost_CNY=opex-revenue,terminal_asset_CNY=terminal,net_cash_cost_CNY=cash,discount_factor=discount,PV_cost_CNY=cash/discount,Li_recovered_t=li,LCE_product_t=li*LCE,gross_carbon_t=u['gwp_gross_kgCO2e']*q[y]/1000,avoided_carbon_t=-u['gwp_net_brine_kgCO2e']*q[y]/1000,avoided_hard_t=-u['gwp_net_hard_kgCO2e']*q[y]/1000,freshwater_m3=u['freshwater_L']*q[y]/1000,water_consumptive_m3=u['water_consumptive_L']*q[y]/1000,water_discharge_m3=u['water_discharge_L']*q[y]/1000,electricity_kWh=u['electricity_kWh']*q[y],heat_MJ=u['heat_MJ']*q[y],energy_kgce_tLCE=u['energy_kgce_tLCE'],status=policy['status']))
        if keep:unitrows.append(dict(year=y,**u))
    npvc=sum(r['PV_cost_CNY'] for r in annual);lithium=sum(r['Li_recovered_t'] for r in annual);avoided=sum(r['avoided_carbon_t'] for r in annual);pvli=sum(r['Li_recovered_t']/r['discount_factor'] for r in annual);pvfeed=sum(r['feed_t']/r['discount_factor'] for r in annual)
    balance=0;peak=0
    for r in annual:
        balance+=r['investment_CNY']+r['OPEX_CNY']-r['revenue_CNY']
        peak=max(peak,balance+r['working_capital_CNY'])
    result=dict(collection=col,green=green,recovery=eta,price_CNY_tLCE=price,NPV_cost_CNY=npvc,cumulative_Li_t=lithium,cumulative_avoided_tCO2=avoided,total_CAPEX_CNY=assets,initial_2028_investment_CNY=annual[2]['investment_CNY'],peak_funding_CNY=peak,PV_feed_t=pvfeed,LCOR_CNY_kgLi=npvc/(pvli*1000),MAC_CNY_tCO2=npvc/sum(r['avoided_carbon_t']/r['discount_factor'] for r in annual),EPR_break_even_CNY_tpack=max(0,npvc/pvfeed),cumulative_gross_tCO2=sum(r['gross_carbon_t'] for r in annual),cumulative_water_m3=sum(r['water_consumptive_m3'] for r in annual),max_energy_kgce_tLCE=max(r['energy_kgce_tLCE'] for r in annual),status='FAIL' if failed else 'PASS',failure_reasons=';'.join(failed))
    return result,annual,unitrows

def main():
    annual,detail,balance=run_dmfa();write('annual_dmfa.csv',annual);write('chemistry_dmfa.csv',detail);write('stock_flow_balance.csv',balance)
    print('年度元素守恒表：year element opening_t input_t scrap_t closing_t relative_error_pct')
    for r in balance:print(r['year'],r['element'],*[round(r[k],8) for k in ['opening_t','inflow_t','scrap_t','closing_t']],r['relative_error_pct'])
    net,flows,options=solve_network();dump('network_summary.json',net);write('network_assignments.csv',flows);write('network_options.csv',options)
    rows=[];fronts=[];environment_fronts=[];anchors={};cache={}
    for price in A['price_CNY_tLCE']:
        subset=[]
        for col,green,eta in product(P['collection_rates'],P['green_shares'],P['recoveries']):
            r,_,_=simulate(detail,net,col,green,eta,price,cache=cache);r['scenario_id']=f'S{len(rows)+1:04d}';rows.append(r);subset.append(r)
        ff,aa=pareto2(subset);fronts+=ff;anchors[str(price)]=aa
        ef,_=pareto2(subset,"cumulative_avoided_tCO2");environment_fronts+=ef
    write('environment_pareto_front.csv',environment_fronts)
    write('all_scenarios.csv',rows);write('pareto_front.csv',fronts);dump('anchors_by_price.json',anchors)
    anchors_base=anchors[str(A['price_CNY_tLCE'][1])];dump('anchors.json',anchors_base);rec=anchors_base['B'];dump('recommended.json',rec)
    allannual=[];balances=[]
    for label,r in anchors_base.items():
        _,ar,ur=simulate(detail,net,r['collection'],r['green'],r['recovery'],r['price_CNY_tLCE'],keep=True)
        allannual += [dict(anchor=label,**x) for x in ar]
        if label=='B':write('recommended_annual.csv',ar);write('recommended_inventory.csv',ur)
        for yr,u in zip(ar,ur):
            q=yr['feed_t'];col=r['collection']
            for e in ELEMENTS:
                regional=u[e+'_feed_kg']*q/col/1000;uncollected=regional*(1-col);prod_mass=u[e+'_product_inherited_kg']*q/1000;loss=u[e+'_residue_kg']*q/1000
                error=abs(regional-uncollected-prod_mass-loss)/max(regional,1e-30)*100
                balances.append(dict(anchor=label,year=yr['year'],element=e,regional_input_t=regional,uncollected_t=uncollected,product_t=prod_mass,process_residue_t=loss,relative_error_pct=error))
    write('anchor_annual.csv',allannual);write('process_balance.csv',balances)
    ar=[r for r in allannual if r['anchor']=='B'];dy=next(r for r in ar if r['year']==2030);u=next(r for r in ur if r['year']==2030) # below re-evaluate B, never reuse C inventory
    _,_,bunits=simulate(detail,net,rec['collection'],rec['green'],rec['recovery'],rec['price_CNY_tLCE'],keep=True);u=next(r for r in bunits if r['year']==2030)
    dump('design_year.json',dy);dump('design_inventory.json',u)
    projects=[];shares=[.15,.45,.20,.15,.05];names=['收集与放电预处理网络','分质湿法提锂及产品精制','废水回用与残渣治理','供电及热能系统','溯源检测与研发平台']
    keys=[['collection','transport','disassembly'],['procurement','reagents','makeup_lithium','labor','precision'],['water','pollution_control','environment_tax'],['electricity','heat'],['rd']]
    for i in range(5):
        projects.append(dict(project_id=f'P{i+1:02}',name=names[i],location=[net['selected']+'区级集散单元','白云钟落潭产业基础协作/依法选定的新增基地','与P02配套','与P02配套','市级平台及处理企业'][i],CAPEX_CNY_2030=dy['cumulative_CAPEX_CNY']*shares[i],CAPEX_CNY_2040=rec['total_CAPEX_CNY']*shares[i],OPEX_CNY_2030=sum(u['cost_'+k+'_CNY'] for k in keys[i])*dy['feed_t']+dy['cumulative_CAPEX_CNY']*P['fixed_om_fraction']*shares[i],design_scale=[dy['capacity_tpa'],dy['capacity_tpa'],u['water_discharge_L']/1000*dy['capacity_tpa']/P['operating_days'],u['electricity_kWh']*dy['capacity_tpa'],dy['capacity_tpa']][i],scale_unit=['tpack/a','tpack/a','m3/d','kWh/a','tpack/a'][i],Li_tpa=dy['Li_recovered_t'] if i==1 else 0,avoided_tCO2pa=dy['avoided_carbon_t'] if i==1 else 0,water_reused_m3pa=u['circulating_water_L']*.95*dy['feed_t']/1000 if i==2 else 0,period='2026—2027签约；2028/2032/2036分期配置',responsible=['车企及回收运营商','再生项目公司','项目公司及环保运维单位','项目公司及能源供应商','车企与项目公司，工信部门监管'][i]))
    write('projects.csv',projects)
    # 资金补足价格与年度现金需求：统一服务费使折现净成本为零，另保留建设周转需求。
    fee=rec['EPR_break_even_CNY_tpack'];balance_cash=0;peak=0;finance=[]
    for r in ar:
        support=fee*r['feed_t'];balance_cash+=r['investment_CNY']+r['OPEX_CNY']-r['revenue_CNY']-support
        peak=max(peak,balance_cash+r['working_capital_CNY'])
        finance.append(dict(year=r['year'],EPR_service_CNY=support,net_operating_after_EPR_CNY=r['revenue_CNY']+support-r['OPEX_CNY'],cumulative_cash_need_CNY=balance_cash+r['working_capital_CNY']))
    write('financing.csv',finance);dump('financing_summary.json',dict(service_CNY_tpack=fee,peak_capital_after_service_CNY=peak,equity_40pct=peak*.4,credit_60pct=peak*.6,service_is_proposed_contract=True))
    # 固定B，不把压力测试重新优化成另一个更好方案。
    sens=[]
    tests=[('price',x) for x in A['price_CNY_tLCE']]+[(k,v) for k,vs in [('capex_multiplier',[.7,1,1.5]),('opex_multiplier',[.8,1,1.2]),('commissioning_delay_years',[0,2]),('terminal_asset_realization',[0,.5,1]),('product_sales_realization',[.6,.85,1]),('process_heat_MJ_kgcell',[0,2,8]),('grid_gwp_kgCO2e_kWh',[.45,.5823,.75]),('process_water_multiplier',[10/375,20/375,40/375,1]),('product_substitution_quality',[.5,.8,1])] for v in vs]
    for k,v in tests:
        p=dict(P);over={};price=rec['price_CNY_tLCE']
        if k=='price':price=v
        elif k in p:p[k]=v
        else:over[k]=v
        if k=='product_sales_realization':over[k]=v
        rr,_,_=simulate(detail,net,rec['collection'],rec['green'],rec['recovery'],price,p,over)
        sens.append(dict(parameter=k,value=v,NPV_cost_CNY=rr['NPV_cost_CNY'],cumulative_Li_t=rr['cumulative_Li_t'],cumulative_avoided_tCO2=rr['cumulative_avoided_tCO2'],EPR_break_even_CNY_tpack=rr['EPR_break_even_CNY_tpack'],status=rr['status']))
    write('sensitivity.csv',sens)
    unc=[]
    for k,vals in [('initial_2010_vehicles',[100,1000,5000]),('future_saturation_vehicles',[4000000,6000000,8000000]),('battery_life_multiplier',[.8,1,1.2])]:
        for v in vals:
            a=dict(A);a[k]=v;ars,_,_=run_dmfa(a)
            for r in ars:
                if r['year']>=2026:unc.append(dict(parameter=k,value=v,year=r['year'],scrap_pack_t=r['battery_scrap_t'],Li_scrap_t=r['Li_scrap_t']))
    write('uncertainty.csv',unc)
    # 梯次利用造成的资源延迟：20%收集量延后5年、继承Li不损失，无再次收集损失的上界。
    delay=[];byyear={r['year']:r for r in ar};closing=0
    for y,r in byyear.items():
        entered=.2*r['Li_recovered_t'];returned=.2*byyear[y-5]['Li_recovered_t'] if y-5 in byyear else 0;opening=closing;closing+=entered-returned
        delay.append(dict(year=y,baseline_Li_t=r['Li_recovered_t'],reuse_delayed_Li_t=.8*r['Li_recovered_t']+returned,opening_reuse_stock_Li_t=opening,enter_reuse_Li_t=entered,return_Li_t=returned,closing_reuse_stock_Li_t=closing))
    write('reuse_delay.csv',delay)
    # 技术路径定点比较，仅材料修复作为备选，原生补锂严格从二次Li扣除。
    routes=[];design_detail=[r for r in detail if r['year']==2030]
    for price in A['price_CNY_tLCE']:
        for direct in [0,.25,.5]:
            aa=dict(A);aa['hydro_li_recovery']=rec['recovery'];uu=unit_inventory(design_detail,direct,rec['green'],price,aa,net['weighted_first_leg_km'],rec['collection'])
            variable=sum(v for k,v in uu.items() if k.startswith('cost_') and k not in ['cost_revenue_CNY','cost_equipment_annual_equivalent_CNY'])
            routes.append(dict(price_CNY_tLCE=price,direct_LFP_share=direct,inherited_Li_kg_tpack=uu['Li_secondary_kg'],external_Li_kg_tpack=uu['Li_external_input_kg'],variable_net_cost_CNY_tpack=variable-uu['cost_revenue_CNY'],net_gwp_kg_tpack=uu['gwp_net_brine_kgCO2e']))
    write('route_comparison.csv',routes)
    # 主基准能耗和水对照，Kelly Table6独立原生数据；不把GREET平均水量混成两条路线。
    dump('primary_water_energy.json',dict(source='Kelly2021 Table6 PDF p11',brine_water_L_kgLCE=[15.5,32.8],ore_water_L_kgLCE=[77,77],brine_energy_MJ_kgLCE=[30,36],ore_energy_MJ_kgLCE=[218,218],note='数值须与Table6逐项核验；回收水采用新水消耗情景，原生为蓝水；矿区卤水蒸发另列'))
    verification=dict(scenarios=len(rows),scenarios_per_price=len(rows)//3,feasible=sum(r['status']=='PASS' for r in rows),fronts=len(fronts),stock_error_pct=max(r['relative_error_pct'] for r in balance),process_error_pct=max(r['relative_error_pct'] for r in balances),project_CAPEX_difference=sum(r['CAPEX_CNY_2030'] for r in projects)-dy['cumulative_CAPEX_CNY'],project_OPEX_difference=sum(r['OPEX_CNY_2030'] for r in projects)-dy['OPEX_CNY'])
    dump('verification.json',verification);print('SUMMARY',verification);print('ABC',anchors_base)
if __name__=='__main__':main()
