"""AI辅助。Prompt：广州A方向，保留队列原始化学结构，分开车辆退出与电池更换，
政策筛选后按固定外生价格分别寻优，工程表只能引用同一推荐方案。
人工校验：待课程组员复核；自动验证与局限见report/验收核对表.md。
"""
from pathlib import Path
from collections import defaultdict
from itertools import combinations,product
import csv, json, math
import numpy as np
from scipy.optimize import linprog
from scipy.io import loadmat
from zipfile import ZipFile
import io
from policy_engine import assess, fiscal_adjustment

BASE=Path(__file__).resolve().parents[1];D=BASE/'data_cohort';O=D/'model_results'
def load(name):return json.loads((D/name).read_text())
def read(name):return list(csv.DictReader((D/name).open(encoding='utf-8-sig')))
def write(name,rows):
    path=O/name;path.parent.mkdir(exist_ok=True,parents=True)
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def dump(name,obj):
    O.mkdir(exist_ok=True,parents=True)
    (O/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False))
A=load('planning_assumptions.json')
CHEMS=[r['chemistry'] for r in read('chemistry_parameters.csv')]
CH=read('chemistry_parameters.csv');CP=read('cell_coproduct_parameters.csv')
I=np.array([[float(r[k+'_kg_kWh']) for k in ['Li','Ni','Co','Mn']] for r in CH])
SH=np.array([float(r['share_2021']) for r in CH]);LIFE=load('lifetime_parameters.json')
PMA=load('ma_selected_scalars.json');EB=load('everbatt_selected_cells.json');PRI=load('primary_lithium_baselines.json')
ELEMENTS=['Li','Ni','Co','Mn'];LCE=73.88/(2*6.94)

def crf(r,n):return 1/n if r==0 else r*(1+r)**n/((1+r)**n-1)

def survival(age,eta,beta):return math.exp(-(max(age,0)/eta)**beta)
def hazard(age,eta,beta):
    return -math.expm1(-((age/eta)**beta-((age-1)/eta)**beta))

def chemistry_shares(year,a):
    s=SH.copy();f=min(1,max(0,(year-2021)/19))
    s[0]=SH[0]+f*(a['lfp_share_2040']-SH[0]);s[1:]*=(1-s[0])/(1-SH[0]);return s

def vehicle_stock_target(year,a,obs):
    if year in obs:return obs[year]
    if year<2019:
        return a['initial_2010_vehicles']*(obs[2019]/a['initial_2010_vehicles'])**((year-2010)/9)
    k=a['future_saturation_vehicles'];return k/(1+(k/obs[2025]-1)*math.exp(-a['future_logistic_growth']*(year-2025)))

def run_dmfa(a=None):
    a=dict(A if a is None else a)
    obs={int(r['year']):float(r['nev_stock_vehicles']) for r in read('vehicle_annual_2015_2025.csv') if r['nev_stock_vehicles']}
    with ZipFile(D/'literature_raw/Battery Recycling Code.zip') as z:
        cap=loadmat(io.BytesIO(z.read('Battery Recycling Code/Code/7-Parameter input/general/battery_capacity/battery_capacity_low/battery_capacity.mat')))['battery_capacity'].ravel()[a['archetype_capacity_rows']]
    weights=np.array(a['archetype_weights']);assert abs(weights.sum()-1)<1e-12
    density=np.array([a['cell_density_lfp_kWh_kg']]+[a['cell_density_other_kWh_kg']]*5)
    pack_kg_per_kWh=1/(density*a['cell_to_pack_mass_fraction'])
    # state[vintage_vehicle, vintage_battery, vehicle_class, chemistry] = number
    states={};annual=[];details=[];balance=[];last=np.zeros(4)
    for year in range(a['start_year'],a['end_year']+1):
        nextstates={};replacements=defaultdict(float);scrap=np.zeros((3,6));vdead=0
        for (v,b,t,c),n in states.items():
            hv=hazard(year-v,a['vehicle_weibull_eta'],a['vehicle_weibull_beta'])
            life=LIFE['LFP' if c==0 else 'ternary']
            hb=hazard(year-b,life['eta']*a['battery_life_multiplier'],life['beta'])
            dead=n*(hv+(1-hv)*hb);alive=n*(1-hv)*(1-hb)
            scrap[t,c]+=dead;vdead+=n*hv
            if alive>1e-10:nextstates[v,b,t,c]=alive
            replacements[v,t]+=n*(1-hv)*hb
        survivors=sum(nextstates.values())+sum(replacements.values())
        target=vehicle_stock_target(year,a,obs);newcars=target-survivors
        assert newcars>=-1e-5,'negative new vehicle inflow: model scope not applicable'
        shares=chemistry_shares(year,a);installed=np.zeros((3,6))
        for t in range(3):
            for c in range(6):
                n=max(newcars,0)*weights[t]*shares[c]
                nextstates[year,year,t,c]=n;installed[t,c]+=n
        for (v,t),n in replacements.items():
            for c in range(6):
                val=n*shares[c];nextstates[v,year,t,c]=val;installed[t,c]+=val
        states=nextstates
        ikwh=(installed*cap[:,None]).sum(axis=0);rkwh=(scrap*cap[:,None]).sum(axis=0)
        skwh=np.zeros(6)
        for (v,b,t,c),n in states.items():skwh[c]+=n*cap[t]
        inputs=ikwh@I;outputs=rkwh@I;stock=skwh@I
        for i,e in enumerate(ELEMENTS):
            error=abs(last[i]+inputs[i]-outputs[i]-stock[i])/max(last[i]+inputs[i],1e-30)
            balance.append(dict(year=year,element=e,opening_t=last[i]/1000,inflow_t=inputs[i]/1000,scrap_t=outputs[i]/1000,closing_t=stock[i]/1000,relative_error_pct=error*100))
            assert error<.0005
        rpack=float((rkwh*pack_kg_per_kWh).sum()/1000)
        row=dict(year=year,vehicle_stock=target,vehicle_inflow_reconstructed=newcars,vehicle_outflow=vdead,battery_replacements=sum(replacements.values()),battery_scrap_number=float(scrap.sum()),battery_scrap_t=rpack,Li_stock_t=stock[0]/1000,Li_scrap_t=outputs[0]/1000,Li_input_t=inputs[0]/1000,Li_potential_secondary_t=outputs[0]*.85*a['preprocess_capture']*a['hydro_li_recovery']/1000)
        annual.append(row)
        for c in range(6):
            row=dict(year=year,chemistry=CHEMS[c],scrap_kWh=float(rkwh[c]),scrap_pack_t=float(rkwh[c]*pack_kg_per_kWh[c]/1000),stock_kWh=float(skwh[c]))
            for i,e in enumerate(ELEMENTS):row[e+'_scrap_kg']=float(rkwh[c]*I[c,i])
            details.append(row)
        last=stock
    return annual,details,balance

def km(p,q):
    lon1,lat1,lon2,lat2=map(math.radians,[p[0],p[1],q[0],q[1]])
    h=math.sin((lat2-lat1)/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 6371*2*math.asin(min(1,math.sqrt(h)))

def solve_network(a=A):
    features=load('raw/DATAV_440100.json')['features'];names=[x['properties']['name'] for x in features]
    points=[x['properties']['centroid'] for x in features]
    pops={r['district']:float(r['value_person']) for r in read('district_population_2015_2024.csv') if r['year']=='2024' and r['population_type']=='permanent' and r['district']!='全市'}
    w=np.array([pops[n] for n in names]);w/=w.sum()
    dist=np.array([[max(a['within_district_km'],km(p,q)*a['road_detour']) for q in points] for p in points])
    candidates=[names.index(n) for n in a['centre_candidate_districts']]
    outcomes=[];assignments={}
    for p in [1,2,3,4]:
        best=None
        for cs in combinations(candidates,p):
            dd=dist[:,cs];c=dd.ravel();eq=np.zeros((11,11*p))
            for i in range(11):eq[i,i*p:(i+1)*p]=1
            ub=np.zeros((p,11*p))
            for j in range(p):ub[j,j::p]=1
            # 单中心只作集中处理基线；多中心按总流量50%抗中断约束。
            r=linprog(c,A_eq=eq,b_eq=w,A_ub=ub,b_ub=np.ones(p)*(1 if p==1 else a['max_centre_flow_share']),bounds=(0,None),method='highs')
            if r.success and (best is None or r.fun<best[0]):best=(float(r.fun),cs,r.x.reshape(11,p))
        assert best is not None
        val,cs,flow=best;outcomes.append(dict(centres=p,selected='、'.join(names[j] for j in cs),weighted_first_leg_km=val,relative_distance_vs_one=val/outcomes[0]['weighted_first_leg_km'] if outcomes else 1))
        assignments[p]=[dict(district=names[i],centre=names[cs[j]],fraction_total=float(flow[i,j]),district_fraction=float(flow[i,j]/w[i]),distance_km=float(dist[i,cs[j]]),population=pops[names[i]],lon=points[i][0],lat=points[i][1],centre_lon=points[cs[j]][0],centre_lat=points[cs[j]][1]) for i in range(11) for j in range(p) if flow[i,j]>1e-10]
    result=outcomes[a['network_centres']-1]
    return result,assignments[a['network_centres']],outcomes

def unit_inventory(detail,direct,green,price,a=A,first_km=20,collection=.85):
    """每处理1t电池包的筛选清单。直接修复仅分配给可分选LFP，NMC/NCA保持湿法。
    Ma工艺数字按原代码计量，电/水/热假设另有明确标记；无实测设施合规结论。
    """
    total=sum(float(r['scrap_pack_t']) for r in detail)
    comp={r['chemistry']:r for r in CP}
    scalar=lambda k:PMA[k]
    out=defaultdict(float);gwp=defaultdict(float);cost=defaultdict(float)
    # 1 mmBtu =1055.05585MJ, 1 US gal=3.7854L; GREET的ton按short ton=907.2kg。
    gridwater=EB['Geographic Par.!G75']*3.7854/(1055.05585/3.6)
    greenwater=EB['GREET IO!AI61']*3.7854/(1055.05585/3.6)
    wf=(1-green)*gridwater+green*greenwater
    ef=(1-green)*a['grid_gwp_kgCO2e_kWh']+green*a['green_gwp_kgCO2e_kWh']
    # Ma的实际元价，固定历史汇率不转为当前价。
    px_e=.72+green*a['green_electricity_CNY_kWh_premium']
    li_secondary=0.;hydro_lce=0.;hydro_MJ=0.;direct_added_li=0.;feed_elements=np.zeros(4);products=np.zeros(4);residue=np.zeros(4)
    qlce_brine=PRI['brine'];qlce_hard=PRI['spodumene']
    coproduct_credit=0.;water_upstream=0.;water_credit=0.;added_li_water=0.
    for c,r in enumerate(detail):
        pack=float(r['scrap_pack_t'])/total*1000;cell=pack*a['cell_to_pack_mass_fraction'];energy=float(r['scrap_kWh'])/total
        feed=np.array([float(r[e+'_scrap_kg'])/total for e in ELEMENTS]);feed_elements+=feed
        direct_share=direct if c==0 else 0
        capture=a['preprocess_capture'];recovery=a['hydro_li_recovery'];retention=a['repair_li_retention']
        hfeed=feed*capture*(1-direct_share);dfeed=feed*capture*direct_share
        rates=np.array([recovery]+[a['other_metal_recovery']]*3)
        prod=hfeed*rates+dfeed*retention
        # Ma以SOH代理可参与补锂的晶格锂占位；剩余原锂进入残余流而不是凭空消失。
        # 该代理缺少当地化学分析，必须在报告中说明不能把SOH视作实测元素损失率。
        prod[0]=hfeed[0]*recovery+dfeed[0]*a['direct_SOH']*retention
        products+=prod;residue+=feed*(1-capture)+hfeed*(1-rates)+dfeed*(1-retention)
        residue[0]+=dfeed[0]*(1-a['direct_SOH'])*retention
        li_secondary+=prod[0];hlce=hfeed[0]*recovery*LCE;hydro_lce+=hlce
        extLi=dfeed[0]*(1-a['direct_SOH']);direct_added_li+=extLi
        # 直接修复材料中的原电池锂与外加锂分别核算。
        direct_total_li=(dfeed[0]*a['direct_SOH']+extLi)*retention
        lce_secondary=prod[0]*LCE
        out['secondary_LCE_kg']+=lce_secondary;out['hydro_LCE_product_kg']+=hlce
        out['direct_inherited_Li_kg']+=dfeed[0]*a['direct_SOH']*retention
        out['direct_external_Li_product_kg']+=extLi*retention
        out['direct_external_Li_loss_kg']+=extLi*(1-retention)
        # 单位电芯清单：Ma LFP/NMCRecycle电耗500/300kWh每吨、电厂水500/200kg每kg电芯。
        hcell=cell*(1-direct_share);dcell=cell*direct_share
        elec_h=hcell*.5*a['process_electricity_multiplier'];elec_d=dcell*.3*a['process_electricity_multiplier']
        pre_e=pack*.01;elec=elec_h+elec_d+pre_e
        heat=cell*a['process_heat_MJ_kgcell'];hydro_MJ+=(elec_h+pre_e*(1-direct_share))*3.6+heat*(1-direct_share)
        circulation=(hcell*500+dcell*200)*a['process_water_multiplier']
        fresh=circulation*(1-a['water_recirculation'])
        acid=hfeed[0]/6.94/2*98
        peroxide=hfeed[0]/6.94/2*34
        soda=hfeed[0]/6.94/2*106
        makeup_lce=extLi*LCE
        out['electricity_kWh']+=elec;out['heat_MJ']+=heat;out['circulating_water_L']+=circulation;out['freshwater_L']+=fresh
        out['acid_kg']+=acid;out['peroxide_kg']+=peroxide;out['soda_kg']+=soda;out['makeup_LCE_kg']+=makeup_lce
        gwp['electricity']+=elec*ef
        # 天然气燃烧+上游，GREET天然气总GHGs约见B39，提取由extract补存。
        gwp['heat']+=heat*(EB['GREET IO!B39']+EB['GREET IO!B14'])/1000/1055.05585
        gwp['reagents']+=acid*scalar('CO2_H2SO4_mar')+peroxide*scalar('CO2_H2O2_mar')+soda*scalar('CO2_Na2CO3_mar')
        gwp['makeup_lithium']+=makeup_lce*scalar('CO2_Li2CO3_mar')
        gwp['water_supply']+=fresh*scalar('CO2_water_mar')
        # 化学品上游耗水按EverBatt一组一致清单；新增锂输入同口径计入。
        water_upstream+=(acid*EB['GREET IO!AE84']+peroxide*EB['GREET IO!G84']+soda*EB['GREET IO!E84']+makeup_lce*EB['GREET IO!F84'])*3.7854/907.2
        water_upstream+=elec*wf+heat*EB['GREET IO!B27']*3.7854/1055.05585
        # 铜铝按电芯组成表，分离率不再重复乘粉料捕集率；其他包壳不计额外收益。
        cu=cell*float(comp[CHEMS[c]]['Cu_kg_kg_cell'])*a['other_metal_recovery'];al=cell*float(comp[CHEMS[c]]['Al_kg_kg_cell'])*a['other_metal_recovery']
        out['Cu_product_kg']+=cu;out['Al_product_kg']+=al
        out['F_input_kg']+=cell*float(comp[CHEMS[c]]['F_kg_kg_cell'])
        coproduct_credit+=cu*scalar('CO2_Cu_pro')+al*scalar('CO2_Al_pro')
        water_credit+=(cu*EB['GREET IO!M84']+al*EB['GREET IO!N84'])*3.7854/907.2
        # 湿法金属盐按无水硫酸盐当量；销售用EverBatt的金属含量计价，避免盐/金属混淆。
        saltkg=np.array([prod[1]*154.75/58.693,prod[2]*154.99/58.933,prod[3]*151.0/54.938])
        coproduct_credit+=float(saltkg@np.array([scalar('CO2_NiSO4_pro'),scalar('CO2_CoSO4_pro'),scalar('CO2_MnSO4_pro')]))
        water_credit+=(saltkg[0]*EB['GREET IO!AJ84']+saltkg[1]*EB['GREET IO!AI84'])*3.7854/907.2
        # 湿法LFP的FePO4和直接修复LFP不重复计盐；直接修复只计继承材料替代信用。
        fepo4=hfeed[0]/6.94*150.82*a['other_metal_recovery'] if c==0 else 0
        repaired_lfp=dfeed[0]/6.94*157.76*a['repair_material_yield']
        out['FePO4_product_kg']+=fepo4;out['repaired_LFP_kg']+=repaired_lfp
        # LFP修复信用含锂：拆出继承锂对应LCE，以免与二次锂替代信用重复。
        coproduct_credit+=fepo4*scalar('CO2_FePO4_pro')+repaired_lfp*scalar('CO2_LiFePO4_pro')-dfeed[0]*a['direct_SOH']*retention*LCE*qlce_brine
        cost['electricity']+=elec*px_e;cost['heat']+=heat*(12*scalar('ExchangeRate')/1055.05585)
        cost['water']+=fresh/1000*3.2
        cost['reagents']+=acid*.55+peroxide*4.2+soda*3
        cost['makeup_lithium']+=makeup_lce*price/1000
        # 原料采购与碳酸锂价格、SOH联动：Ma降级正极材料价格，按Li价相对变化调整。
        active=feed[0]/6.94*(157.76 if c==0 else 97.3)
        pricebase=38750 if c==0 else 118250
        cost['procurement']+=active*pricebase/1000*(a['direct_SOH']/.8)*(.5+.5*price/154880)
        cost['labor']+=hcell*2.15+dcell*1.564
        cost['disassembly']+=hcell*.85+dcell*1
        cost['pollution_control']+=hcell*.99+dcell*.7
        cost['equipment_annual_equivalent']+=hcell*.365+dcell*.4
        # 所有产品收益一次计入；直接修复材料只销售正极材料，不再销售其锂盐。
        metalprice=np.array([EB['Materials!C5'],EB['Materials!C4'],EB['Materials!C6']])*scalar('ExchangeRate')
        revenues=(hlce*price/1000+float(prod[1:]@metalprice)+cu*5.43*scalar('ExchangeRate')+al*1.45*scalar('ExchangeRate')+fepo4*35.8+repaired_lfp*81.5)
        cost['revenue']+=revenues
    # 分项结果的功能单位均为每吨入厂电池包。
    distance=first_km+a['refining_leg_km']
    gwp['transport']=distance*a['transport_gwp_kgCO2e_tkm']
    cost['transport']=distance*a['transport_CNY_tkm'];cost['collection']=1000*(a['collection_CNY_kgpack']+a['collection_marginal_cost_scale_CNY_kgpack']*((collection-.5)/.45)**2)
    cost['rd']=cost['revenue']*a['rd_fraction']
    out['Li_secondary_kg']=li_secondary;out['Li_external_input_kg']=direct_added_li
    out['gwp_gross_kgCO2e']=sum(gwp.values())
    # 全LFP直接修复时不重复计其LCE信用；修复信用已经拆成其余材料与继承锂两部分。
    coproduct_credit*=a['product_substitution_quality']
    out['gwp_credit_coproduct_kgCO2e']=coproduct_credit
    out['gwp_credit_lithium_brine_kgCO2e']=out['secondary_LCE_kg']*qlce_brine*a['product_substitution_quality']
    # 直接修复LFP产品替代基准固定，其隐含锂不随外部盐湖/硬岩反事实改变。
    salt_equiv=(out['secondary_LCE_kg']-out['direct_inherited_Li_kg']*LCE)
    out['gwp_credit_lithium_hard_kgCO2e']=out['gwp_credit_lithium_brine_kgCO2e']+salt_equiv*(qlce_hard-qlce_brine)*a['product_substitution_quality']
    out['gwp_net_brine_kgCO2e']=out['gwp_gross_kgCO2e']-coproduct_credit-out['gwp_credit_lithium_brine_kgCO2e']
    out['gwp_net_hard_kgCO2e']=out['gwp_gross_kgCO2e']-coproduct_credit-out['gwp_credit_lithium_hard_kgCO2e']
    out['water_gross_L']=out['freshwater_L']+water_upstream
    out['water_credit_proxy_L']=(water_credit+out['secondary_LCE_kg']*EB['GREET IO!F84']*3.7854/907.2)*a['product_substitution_quality']
    out['water_net_proxy_L']=out['water_gross_L']-out['water_credit_proxy_L']
    # 能耗红线使用厂内最终能量，非生命周期累计能耗；整条湿法保守归到LCE。
    out['energy_kgce_tLCE']=hydro_MJ/hydro_lce/29.3076*1000 if hydro_lce>1e-10 else 0
    for i,e in enumerate(ELEMENTS):
        out[e+'_feed_kg']=float(feed_elements[i]);out[e+'_product_inherited_kg']=float(products[i]);out[e+'_residue_kg']=float(residue[i])
    for k,v in gwp.items():out['gwp_'+k+'_kgCO2e']=v
    cost['revenue']*=a['product_sales_realization']
    cost['rd']=cost['revenue']*a['rd_fraction']
    for k,v in cost.items():out['cost_'+k+'_CNY']=v
    out['grid_water_L_kWh']=gridwater;out['green_water_L_kWh']=greenwater
    return dict(out)
