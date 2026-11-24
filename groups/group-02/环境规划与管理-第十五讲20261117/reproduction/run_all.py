# -*- coding: utf-8 -*-
"""
run_all.py
==========
一键可复现主程序：依次执行
  任务1 数据清洗 + 类别字典核验 + 农田种植系统 (ACS) 公式复现
  任务2 全系统 MFA + 五子系统质量守恒自检 + 扰动检测 + 桑基图
  任务3 2050 BAU/3R 情景 + 政策交叉敏感性回归 + 图件与统计表

运行方式：
    python run_all.py
输出：
    控制台通关信息、sankey_2022.html、scenario_2050.html、
    scenario_2050.csv、sensitivity_results.xlsx、benchmarks.csv
"""

import os
import sys

# 禁用底层 BLAS/OpenMP 多线程，规避 numpy/scipy 间歇性段错误（0xC0000005）
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")
os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import data_loader as dl
from acs_model import ACSPModel, build_sample_params
from mfa_model import GlobalPModel
from sankey import export_sankey
from scenario_2050 import run_scenarios, export_scenario_figure
import sensitivity as sens

_OUT = os.path.dirname(os.path.abspath(__file__))


def sep(title):
    print("\n" + "=" * 72)
    print(f"  {title}")
    print("=" * 72)


def task1():
    """数据清洗 + 类别字典核验 + ACS 公式复现。"""
    sep("任务 1：数据清洗与农田种植系统 (ACS) 公式复现")

    prod = dl.load_product_p()
    category_map = dl.load_category_map()
    check = dl.validate_product_p(prod, category_map)
    crop_2022 = prod[(prod["Year"] == 2022) & (~prod["Category"].isin({"G", "M"}))]["P_kt"].sum()
    animal_2022 = prod[(prod["Year"] == 2022) & (prod["Category"].isin({"G", "M"}))]["P_kt"].sum()
    print("  数据核验：")
    for key, value in check.items():
        print(f"    {key}: {value}")
    print(f"  2022 作物纯磷产出 = {crop_2022/1e3:.2f} Mt P；"
          f"动物纯磷产出 = {animal_2022/1e3:.2f} Mt P")

    crop_params, system_params = build_sample_params()
    acs = ACSPModel(crop_params, system_params)
    flows = acs.run()
    print("\n  ACS 模型流向（示意参数，仅验证公式与守恒逻辑）：")
    for key in ["作物吸收磷 crop_uptake", "作物收获磷 crop_harvest",
                "作物残留磷 crop_residue", "排水淋溶流失 drainage_leaching",
                "大气沉降磷 atmospheric_deposition", "有机肥回用磷 reuse_organic"]:
        print(f"    {key:28s} = {flows[key]:.4f}")
    return acs


def task2(model):
    """全系统 MFA + 守恒 + 桑基图。"""
    sep("任务 2：全系统 MFA 模型 + 守恒自检 + 桑基图")
    model.build_2022_flows()
    model.verify_mass_balance()
    balance_table = model.mass_balance_report()
    print("  分系统守恒（相对误差均需 < 1e-4）：")
    print(balance_table.to_string(index=False, float_format=lambda x: f"{x:.4e}"))
    detected = model.verify_balance_detection()
    print(f"  [PASS] 扰动检测：扰动 P_fert 后，守恒检查可识别非闭合子系统 {detected}")

    sankey_path = export_sankey(model)
    print(f"  [PASS] 桑基图已导出：{sankey_path}")
    return sankey_path


def task3(model):
    """2050 情景 + 政策交叉敏感性回归。"""
    sep("任务 3：2050 BAU/3R 情景 + 政策交叉敏感性回归")

    results, table = run_scenarios(model)
    print("  2050 情景对比：")
    print(table.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    print(f"  2050/2022 人口比 = {results['population_ratio']:.4f}")

    figure_path = export_scenario_figure(table)
    print(f"  [PASS] 情景图已导出：{figure_path}")

    dataset = sens.build_policy_dataset(model)
    coefficients, summary = sens.run_policy_regression(dataset)
    key_interaction = sens.key_interaction_result(coefficients, summary)

    scenario_csv = os.path.join(_OUT, "scenario_2050.csv")
    dataset.to_csv(scenario_csv, index=False, encoding="utf-8-sig")

    xlsx_path = os.path.join(_OUT, "sensitivity_results.xlsx")
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        dataset.to_excel(writer, sheet_name="情景参数与响应", index=False)
        coefficients.to_excel(writer, sheet_name="标准化回归", index=False)
        summary.to_excel(writer, sheet_name="模型摘要", index=False)
        key_interaction.to_excel(writer, sheet_name="关键交互", index=False)
    print(f"  [PASS] 回归结果已导出：{xlsx_path}")

    print("\n  关键交互（S2.2 节肥 × S4.3 粪污还田）：")
    print(key_interaction.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    return results, dataset, coefficients, summary


def main():
    sep("全球人为磷循环 MFA 复现 —— 一键运行")
    print(f"  输出目录：{_OUT}")

    task1()
    model = GlobalPModel()
    sankey_path = task2(model)
    task3(model)

    bench = model.benchmarks()
    bench_path = os.path.join(_OUT, "benchmarks.csv")
    bench.to_csv(bench_path, index=False, encoding="utf-8-sig")
    print("\n" + "=" * 72)
    print("  基准指标对照表（复现值 vs 文献/外部对照）")
    print("=" * 72)
    print(bench.to_string(index=False, float_format=lambda x: f"{x:.4f}"))

    sep("全部任务完成")
    print("  生成文件：")
    print(f"    - {sankey_path}")
    print(f"    - {os.path.join(_OUT, 'scenario_2050.html')}")
    print(f"    - {os.path.join(_OUT, 'scenario_2050.csv')}")
    print(f"    - {os.path.join(_OUT, 'sensitivity_results.xlsx')}")
    print(f"    - {bench_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
