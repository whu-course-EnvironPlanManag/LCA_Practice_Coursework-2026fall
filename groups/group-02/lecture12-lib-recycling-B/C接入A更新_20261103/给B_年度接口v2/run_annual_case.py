import json
from pathlib import Path
from annual_tea_interface import evaluate_annual_case
p=Path(__file__).resolve().parent
case=json.loads((p/'annual_case_input.json').read_text(encoding='utf-8'))
print(json.dumps(evaluate_annual_case(case),ensure_ascii=False,indent=2))
