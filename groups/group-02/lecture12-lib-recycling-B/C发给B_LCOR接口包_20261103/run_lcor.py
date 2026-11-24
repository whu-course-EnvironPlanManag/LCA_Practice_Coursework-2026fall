"""Run C conditional demonstration, not a validated final plant LCOR."""
import json
from pathlib import Path
from tea_model import evaluate_tea
root=Path(__file__).resolve().parent
case=json.loads((root/'conditional_case.json').read_text(encoding='utf-8'))
r=evaluate_tea(case)
print(json.dumps(dict(status='CONDITIONAL_PARTIAL_LCOR_NOT_FINAL',lcor_final_CNY_t_LCE=None,partial_lcor_conditional_CNY_t_LCE=r['base_lcor_per_fu'],annual_LCE_scenario_t=case['fu_per_year'],boundary_id=case['boundary_id'],policy_status='UNKNOWN'),ensure_ascii=False,indent=2))
