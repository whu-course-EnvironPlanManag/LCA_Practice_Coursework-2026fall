"""Checks actual artifacts and deliberately breaks an internal transfer to test conservation."""
import json
import re
from pathlib import Path
import run_analysis as analysis
import numpy as np
import pandas as pd

base=Path(__file__).resolve().parent
out=base/'outputs'
audit=json.loads((out/'audit.json').read_text(encoding='utf8'))
edges=pd.read_csv(out/'flows_2022.csv')
assert (edges.Mt_P>=0).all() and np.isfinite(edges.Mt_P).all()
triples=list(edges.itertuples(index=False,name=None))
for sector in analysis.GlobalModel.sectors:
    sector.verify_mass_balance(triples)
broken=[(s,t,v*1.01 if s=='CIS' and t=='ACS' else v) for s,t,v in triples]
try:
    analysis.ACSModel().verify_mass_balance(broken)
except AssertionError:
    detects_corruption=True
else:
    raise AssertionError('Mass-balance verifier failed to detect changed transfer')
for p in out.glob('balance*.csv'):
    assert pd.read_csv(p).relative_error.max()<1e-4
grid=pd.read_csv(out/'policy_factorial_grid.csv')
assert len(grid)==343 and not grid.duplicated(['Reduce','Replace','Recycle']).any()
reg=pd.read_csv(out/'policy_regression.csv')
for row in reg.itertuples():
    if '*' in row.term:
        expected='无显著交互作用' if row.p_value>=.05 else ('协同增强' if row.standardized_beta>0 else '拮抗削弱')
        assert row.interaction==expected
coeff=pd.read_csv(out/'si_product_coefficients.csv')
assert coeff.P_percent.between(0,10).all()
assert not coeff.Item.str.contains('total number',case=False).any()
assert np.allclose(coeff.g_P_per_kg,coeff.P_percent*10)
fig=json.loads((out/'sankey_2022.json').read_text(encoding='utf8'))
links=fig['data'][0]['link'];n=len(fig['data'][0]['node']['label'])
assert all(isinstance(i,int) and 0<=i<n for i in links['source']+links['target'])
assert len(links['source'])==len(links['target'])==len(links['value'])
for file in ['sankey_2022.html','scenarios_2050.html','history_1961_2022.html']:
    text=(out/file).read_text(encoding='utf8')
    assert 'Plotly.newPlot' in text and len(text)>1_000_000
    assert not re.search(r'<script\s+[^>]*src=["\']https?://',text)
historical=pd.read_csv(out/'historical_product_P_1961_2022.csv')
assert historical.Country.eq('World').all()
assert set(historical.Year)==set(range(1961,2023))
bench=pd.read_csv(out/'benchmark_comparison.csv')
assert bench.loc[bench.status.eq('not independently reproduced'),'computed'].isna().all()
report=(base/'report.md').read_text(encoding='utf8')
chars=len(re.findall('[\u4e00-\u9fff]',report))
assert 2000<=chars<=3000,chars
result=dict(artifact_checks_passed=True,all_balance_errors_below_1e_4=True,
            detects_deliberately_corrupted_transfer=detects_corruption,
            report_Chinese_character_count=chars,policy_grid_size=len(grid),
            html_self_contained=True,browser_visual_check='See browser_qa.json if present; static checks alone do not prove rendering',
            source_limitations=audit['data'],strict_paper_replication_complete=False)
(out/'self_check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(result,ensure_ascii=False,indent=2))
