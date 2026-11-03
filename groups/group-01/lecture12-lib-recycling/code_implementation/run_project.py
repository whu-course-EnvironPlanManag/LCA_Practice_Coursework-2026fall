"""一键复现：python code_implementation/run_project.py --exploratory。

提示词：仅调度已经核对的本地脚本，不联网填数；待核情景须显式确认模式。
"""
from pathlib import Path
import argparse
import subprocess
import sys


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exploratory", action="store_true", help="接受这是待核参数的条件情景，不是实证预测")
    args=parser.parse_args()
    if not args.exploratory:
        parser.error("请先阅读data_cohort/README_data_sources.md，再用--exploratory明确运行条件情景")
    folder=Path(__file__).resolve().parent
    commands=[("run_analysis.py", "--self-test"), ("run_analysis.py", "--check-inputs"),
        ("run_analysis.py", "--plot-yearbook"), ("run_analysis.py", "--run", "--exploratory"),
        ("postprocess.py",), ("build_report.py",), ("validate_submission.py",)]
    for name,*flags in commands:
        result=subprocess.run([sys.executable,"-X","utf8",str(folder/name),*flags])
        if result.returncode:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
