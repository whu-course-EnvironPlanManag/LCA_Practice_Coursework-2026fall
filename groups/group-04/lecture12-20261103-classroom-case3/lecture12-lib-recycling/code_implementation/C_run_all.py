# -*- coding: utf-8 -*-
"""C_run_all.py —— 一键复现：01→06 计算 + 07 出图"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STEPS = ["C_env_performance.py", "C_water_carbon.py", "C_pareto.py",
         "C_finance.py", "C_techenomics.py", "C_sensitivity.py", "C_figures.py"]

for step in STEPS:
    print(f"\n>>> {step}")
    r = subprocess.run([sys.executable, os.path.join(HERE, step)], cwd=HERE)
    if r.returncode != 0:
        raise SystemExit(f"{step} 失败（returncode={r.returncode}）")
print("\n全部完成：data_cohort/ 与 figures_output/ 已更新")
