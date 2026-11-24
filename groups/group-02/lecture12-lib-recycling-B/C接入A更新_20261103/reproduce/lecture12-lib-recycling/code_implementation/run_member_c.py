"""AI Prompt: 提供成员C可复现入口，测试输出与真实工况严格区分。
人工核验修正：尚待成员C复核，所有synthetic结果仅用于软件验证。
"""
import argparse
import csv
import json
from pathlib import Path
from policy_engine import evaluate_policy
from tea_model import evaluate_tea

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description='成员C经济与政策模块')
    parser.add_argument('--tea-case', type=Path, help='真实TEA工况JSON；缺失值将报错')
    parser.add_argument('--policy-case', type=Path, help='真实政策工况JSON（单个对象）')
    parser.add_argument('--profile', choices=['coursework','verified_current'], default='coursework')
    parser.add_argument('--demo', action='store_true', help='只运行合成测试夹具')
    args = parser.parse_args()
    if not (args.demo or args.tea_case or args.policy_case):
        parser.error('请指定--demo或真实工况文件')
    if args.demo and (args.tea_case or args.policy_case):
        parser.error('--demo不可与真实工况同时运行')
    destination = ROOT / 'report' / ('test_outputs' if args.demo else 'computed_outputs')
    destination.mkdir(parents=True, exist_ok=True)
    outputs = {}
    if args.demo or args.tea_case:
        path = Path(__file__).parent / 'fixtures/tea_synthetic.json' if args.demo else args.tea_case
        case = json.loads(path.read_text(encoding='utf-8-sig'))
        if not args.demo and case.get('data_status') != 'reviewed_input':
            raise ValueError('真实工况须在人工核对数据后设置data_status=reviewed_input')
        outputs['tea'] = evaluate_tea(case)
    if args.demo or args.policy_case:
        cases = (json.loads((Path(__file__).parent / 'fixtures/policy_synthetic.json').read_text())
                 if args.demo else [json.loads(args.policy_case.read_text(encoding='utf-8-sig'))])
        outputs['policy'] = [evaluate_policy(c, profile=args.profile) for c in cases]
        with (destination / 'policy_checks.csv').open('w', encoding='utf-8-sig', newline='') as f:
            fields = ['case_id','rule_id','metric','status','actual','operator','threshold','unit','reason','source_id']
            writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader()
            for result in outputs['policy']:
                for row in result['checks']:
                    writer.writerow(dict(case_id=result['case_id'], **row))
    (destination / 'member_c_results.json').write_text(json.dumps(outputs, ensure_ascii=False, indent=2), encoding='utf-8')
    if args.demo:
        print('SYNTHETIC TEST ONLY: not park results')
    if 'tea' in outputs:
        print('TEA:', outputs['tea']['case_id'], 'LCOR=', outputs['tea']['base_lcor_per_fu'])
    for result in outputs.get('policy', []):
        print('POLICY:', result['case_id'], result['profile'], result['status'])
    print(destination)


if __name__ == '__main__':
    main()
