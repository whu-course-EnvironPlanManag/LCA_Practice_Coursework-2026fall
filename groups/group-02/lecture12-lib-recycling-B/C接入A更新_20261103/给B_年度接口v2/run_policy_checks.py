import json
from pathlib import Path
from policy_engine import evaluate_policy
p=Path(__file__).resolve().parent
b=json.loads((p/'C_to_B_annual_bundle_v2.json').read_text(encoding='utf-8'))
for x in b['policy_results']:
 r=evaluate_policy(x['input'],policy_path=p/'policy_parameters.json',profile=x['result']['profile'])
 print(r['case_id'],r['status'])
