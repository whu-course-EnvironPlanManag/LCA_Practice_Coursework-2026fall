"""独立化学计量校核：纯组分、净RWGS=1.124 kmol/t、氢气单程消耗率=25%。"""
import json
from pathlib import Path
def solve_mfa_balance(single_pass_conv=.25,purge_ratio=.01):
    x,r=single_pass_conv,purge_ratio
    if not 0<x<=1 or not 0<r<=1: raise ValueError('invalid conversion/purge')
    mw={'CO2':44.009,'H2':2.016,'CO':28.010,'MeOH':32.042,'water':18.015}
    a=1000/mw['MeOH']; b=1.124
    consumed={'CO2':a+b,'H2':3*a+b}
    un={k:v*(1-x)/x for k,v in consumed.items()}
    fresh={k:v+r*un[k] for k,v in consumed.items()}
    purge={k:r*v for k,v in un.items()}; purge['CO']=b
    recycle={k:(1-r)*v for k,v in un.items()}; recycle['CO']=b*(1-r)/r
    out={'MeOH':a,'water':a+b,**purge}
    atoms={'CO2':(1,0,2),'H2':(0,2,0),'CO':(1,0,1),'MeOH':(1,4,1),'water':(0,2,1)}
    err={e:abs(sum(v*atoms[k][i] for k,v in fresh.items())-sum(v*atoms[k][i] for k,v in out.items()))/sum(v*atoms[k][i] for k,v in fresh.items()) for i,e in enumerate('CHO')}
    assert max(err.values())<1e-4
    return dict(fresh_kg={k:v*mw[k] for k,v in fresh.items()},water_kg=(a+b)*mw['water'],purge_kg=sum(v*mw[k] for k,v in purge.items()),recycle_kg=sum(v*mw[k] for k,v in recycle.items()),eta_carbon=a/fresh['CO2'],errors=err,recycle_ratio_molar=sum(recycle.values())/sum(fresh.values()),recycle_ratio_mass=sum(v*mw[k] for k,v in recycle.items())/sum(v*mw[k] for k,v in fresh.items()))
if __name__=='__main__':
    d=solve_mfa_balance(); print(json.dumps(d,indent=2)); p=Path(__file__).resolve().parents[1]/'figures_output';p.mkdir(exist_ok=True);(p/'mfa_check.json').write_text(json.dumps(d,indent=2))
