"""AI辅助。Prompt：验证政策边界、守恒独立方程、双目标支配关系及工程现金流一致性。人工复核待小组确认。"""
from planning import *
from policy_engine import threshold_for
import copy
checks=[]
def check(name,condition):
    checks.append(dict(test=name,status='PASS' if condition else 'FAIL'))
    assert condition,name

def rows(name):
    out=list(csv.DictReader((O/name).open(encoding='utf-8-sig')))
    for r in out:
        for k,v in r.items():
            try:r[k]=float(v)
            except (ValueError,TypeError):pass
    return out

def main():
    case=dict(has_smelting=True,has_repair=False,Li=.92,Ni=.98,Co=.98,Mn=.98,Cu=.98,Al=.98,F=.995,powder=.98,Al_impurity=.01,Cu_impurity=.01,energy_kgce_tLCE=1500,water_recycle=.95,capacity_tpa=10000,rd_fraction=.03)
    check('常规湿法达标',assess(case)['status']=='PASS')
    check('粗放回收否决',assess(dict(case,Li=.85,F=.9))['status']=='FAIL')
    check('先进修复达标',assess(dict(case,has_repair=True,repair_material=.99))['status']=='PASS')
    for k,bound in [('Li',.9),('Ni',.98),('Co',.98),('Mn',.98),('powder',.98),('F',.995),('water_recycle',.9),('rd_fraction',.03)]:
        check(k+'_等号',assess(dict(case,**{k:bound}))['status']=='PASS')
        check(k+'_下界外',assess(dict(case,**{k:bound-1e-5}))['status']=='FAIL')
    check('能耗严格小于',assess(dict(case,energy_kgce_tLCE=2200))['status']=='FAIL')
    check('杂质严格小于',assess(dict(case,Al_impurity=.015))['status']=='FAIL')
    check('未知能耗不通过',assess(dict(case,energy_kgce_tLCE=None))['status']=='UNKNOWN')
    check('禁止电动自行车',assess(dict(case,reuse_application='electric_bicycle'))['status']=='FAIL')
    check('EU2027前',threshold_for(POL['eu']['lithium_recovery'],'2027-12-30')==0)
    check('EU2027日期',threshold_for(POL['eu']['lithium_recovery'],'2027-12-31')==.5)
    check('EU2031日期',threshold_for(POL['eu']['lithium_recovery'],'2031-12-31')==.8)
    check('EU含量2031',threshold_for(POL['eu']['recycled_content'],'2031-08-18')['Li']==.06)
    check('EU含量2036',threshold_for(POL['eu']['recycled_content'],'2036-08-18')['Li']==.12)
    check('国内通过不等于出口认证',assess(case,export=True)['status']=='UNKNOWN')
    f=fiscal_adjustment(avoided_tCO2=100,price=100)
    check('不确认未获资格碳收入',f['carbon_credit']==0)
    check('授权情景碳收入',fiscal_adjustment(avoided_tCO2=100,price=100,ccer_eligible=True)['carbon_credit']==10000)
    for age in range(1,20):
        s=survival(age-1,7.5,4.1);check('寿命离散差分_'+str(age),math.isclose(s*hazard(age,7.5,4.1),s-survival(age,7.5,4.1),abs_tol=1e-12))
    b=rows('stock_flow_balance.csv');check('逐年元素守恒',max(r['relative_error_pct'] for r in b)<.05)
    proc=rows('process_balance.csv');check('过程独立残余流守恒',max(r['relative_error_pct'] for r in proc)<.05)
    allrows=rows('all_scenarios.csv');front=rows('pareto_front.csv');aa=json.loads((O/'anchors.json').read_text())
    check('主方案统一电网供电',all(r['green']==0 for r in allrows))
    check('每价格至少500工况',all(sum(r['price_CNY_tLCE']==p for r in allrows)>=500 for p in A['price_CNY_tLCE']))
    for price in A['price_CNY_tLCE']:
        valid=[r for r in allrows if r['status']=='PASS' and r['price_CNY_tLCE']==price]
        x=np.array([[r['NPV_cost_CNY'],-r['cumulative_Li_t']] for r in valid]);scale=np.maximum(np.ptp(x,axis=0),1)
        for r in [r for r in front if r['price_CNY_tLCE']==price]:
            v=np.array([r['NPV_cost_CNY'],-r['cumulative_Li_t']]);delta=(x-v)/scale
            check('非支配_'+r['scenario_id'],not np.any(np.all(delta<=1e-12,axis=1)&np.any(delta<-1e-12,axis=1)))
    synthetic=[dict(status='PASS',NPV_cost_CNY=cost,cumulative_Li_t=li,cumulative_avoided_tCO2=carbon) for cost,li,carbon in [(1,1,100),(2,2,-100),(3,1,999)]]
    sf,sa=pareto2(synthetic);check('碳排放不参与主目标支配',len(sf)==2 and sa['C']['cumulative_Li_t']==2)
    for price in A['price_CNY_tLCE']:
        valid=[r for r in allrows if r['status']=='PASS' and r['price_CNY_tLCE']==price]
        for r in [r for r in rows('environment_pareto_front.csv') if r['price_CNY_tLCE']==price]:
            check('环境辅助非支配_'+r['scenario_id'],not any(q['NPV_cost_CNY']<=r['NPV_cost_CNY'] and q['cumulative_avoided_tCO2']>=r['cumulative_avoided_tCO2'] and (q['NPV_cost_CNY']<r['NPV_cost_CNY'] or q['cumulative_avoided_tCO2']>r['cumulative_avoided_tCO2']) for q in valid))
    baseline=[r for r in front if r['price_CNY_tLCE']==A['price_CNY_tLCE'][1]]
    check('A成本端点',aa['A']['NPV_cost_CNY']==min(r['NPV_cost_CNY'] for r in baseline))
    check('B理想点',aa['B']['ideal_distance']==min(r['ideal_distance'] for r in baseline))
    check('C锂量端点',aa['C']['cumulative_Li_t']==max(r['cumulative_Li_t'] for r in baseline))
    ar=rows('recommended_annual.csv');pr=rows('projects.csv');dy=next(r for r in ar if r['year']==2030)
    check('NPV逐年求和',math.isclose(sum(r['PV_cost_CNY'] for r in ar),aa['B']['NPV_cost_CNY'],rel_tol=1e-12))
    check('累计锂逐年求和',math.isclose(sum(r['Li_recovered_t'] for r in ar),aa['B']['cumulative_Li_t'],rel_tol=1e-12))
    check('工程投资同源',math.isclose(sum(r['CAPEX_CNY_2030'] for r in pr),dy['cumulative_CAPEX_CNY'],rel_tol=1e-12))
    check('工程运行成本同源',math.isclose(sum(r['OPEX_CNY_2030'] for r in pr),dy['OPEX_CNY'],rel_tol=1e-12))
    check('工程效益不重复',math.isclose(sum(r['Li_tpa'] for r in pr),dy['Li_recovered_t'],rel_tol=1e-12))
    check('产能不超负荷',all(r['own_processed_t']<=r['capacity_tpa']*P['utilization_ceiling']+1e-8 for r in ar))
    check('委托自营数量闭合',all(abs(r['own_processed_t']+r['outsourced_t']-r['feed_t'])<1e-8 for r in ar))
    reuse=rows('reuse_delay.csv');check('梯次延迟存量守恒',all(abs(r['opening_reuse_stock_Li_t']+r['enter_reuse_Li_t']-r['return_Li_t']-r['closing_reuse_stock_Li_t'])<1e-8 for r in reuse))
    check('期末延迟不计回收',abs(sum(r['baseline_Li_t']-r['reuse_delayed_Li_t'] for r in reuse)-reuse[-1]['closing_reuse_stock_Li_t'])<1e-8)
    write('tests.csv',checks);dump('tests_summary.json',dict(total=len(checks),passed=len(checks),failed=0));print('TEST PASS',len(checks))
POL=load('policy_parameters.json')
if __name__=='__main__':main()
