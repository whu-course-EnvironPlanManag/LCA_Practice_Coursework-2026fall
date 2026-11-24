# -*- coding: utf-8 -*-
"""顶层一键复现入口：成员 A → 成员 B → 成员 C → 单元测试。

运行方式（任意位置）：
    python code_implementation/run_all.py

依赖：Python 3.10+ 与 pandas / numpy / matplotlib（详见根 README.md「环境依赖」）。
说明：成员 B 的正式 LCOR 依赖成员 C 完整经济录入；在其未就绪时 B 仅输出环境维度图
（NOT_READY 状态），不阻断后续 C 的最终数据与图表生成。
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def run(script):
    print(f"\n{'=' * 64}\n# 运行 {script}\n{'=' * 64}", flush=True)
    subprocess.check_call([sys.executable, os.path.join(HERE, script)], cwd=HERE)


if __name__ == "__main__":
    # 成员 A：工序物质流+元素平衡校验、市域 dMFA、工程清单、R1 工况与 6 图
    run("A_run_all.py")

    # 成员 B：环境因子 + LCA 情景仿真与优化（环境维度图）
    run("B_run_all.py")

    # 成员 C：最终数据表 + 政策判定 + 经济模型 + 图
    run("build_final_data.py")
    run("make_figures.py")

    # 单元测试（任务书 §八 自检：政策规则 ≥3 PASS）
    run("test_policy_engine.py")
    run("test_tea_model.py")
    run("test_lcor_mac_model.py")

    print("\n全部步骤完成：数据、图与结果见 data_cohort/ 与 figures_output/。")