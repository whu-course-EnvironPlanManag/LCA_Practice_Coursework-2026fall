# -*- coding: utf-8 -*-
"""一键运行入口：任务1→2→3 全流程（数据加载、MFA 建模、守恒自检、
桑基图、2050 情景、交叉敏感性回归、基准对照表）。

用法：python run_all.py
所有路径均相对本文件解析，输出写入 output/ 目录。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import pandas as pd

import config as C
import data_load as D
import params_si as P
from acs_model import ACSModel, acs_annual_table, verify_mass_balance as vmb_acs
from mfa_model import GlobalPModel, build_annual_table, verify_mass_balance as vmb_all
import sankey
import scenarios
import cross_sensitivity as xs

SEP = "=" * 62


def task1():
    print(SEP)
    print("任务1：农田种植子系统（ACS）2022 年磷流动")
    print(SEP)
    m = ACSModel(2022)
    f = m.flows()
    for k, v in f.items():
        if k in ("PUE_c", "Fert_share"):
            print(f"  {k:<22} {v * 100:8.2f} %")
        else:
            print(f"  {k:<22} {v / C.T_PER_MT:8.3f} Mt P")
    rel = vmb_acs(f)
    print(f"  [守恒自检] 相对误差 = {rel:.2e} < 1e-4 通过")
    tbl = acs_annual_table()
    tbl.to_csv(C.CSV_DIR / "acs_annual_flows.csv", encoding="utf-8-sig")
    return tbl


def task2():
    print(SEP)
    print("任务2：五子系统全球磷 MFA（1961-2022）")
    print(SEP)
    tbl = build_annual_table()
    tbl.to_csv(C.CSV_DIR / "mfa_annual_flows.csv", encoding="utf-8-sig")
    cols = ["PR_input", "Fertilizer", "ACS_input", "ACS_harvest", "ACS_water_loss",
            "ACS_legacy_delta", "LBS_feed_input", "LBS_product", "LBS_manure", "RCS_excreta"]
    print((tbl.loc[[1961, 1980, 2000, 2010, 2021, 2022], cols] / C.T_PER_MT).round(2).to_string())
    flows = GlobalPModel(2022).subsystem_flows()
    rel = vmb_all(flows)
    print(f"  [全系统守恒自检] 相对误差 = {rel:.2e} < 1e-4 通过")
    sankey.build_sankey()
    return tbl


def task3():
    print(SEP)
    print("任务3：2050 年 3R 情景与交叉敏感性回归")
    print(SEP)
    sdf = scenarios.scenario_table()
    sdf.to_csv(C.CSV_DIR / "scenarios_2050.csv", encoding="utf-8-sig")
    print("2050/2022 人口比 = %.4f" % scenarios.pop_ratio())
    print(sdf[["fert", "NPR", "CFR", "Loss", "NPR_vs_BAU%", "CFR_vs_BAU%", "Loss_vs_BAU%"]]
          .round(2).to_string())
    print(SEP)
    results, best = xs.run()
    all_df = pd.concat(results.values(), ignore_index=True)
    all_df.to_csv(C.CSV_DIR / "cross_sensitivity_66.csv", encoding="utf-8-sig")
    print(f"选用切片: {best}（66 组合结果已存 cross_sensitivity_66.csv）")
    types = results[best]["interaction_type"].value_counts()
    print(types.to_string())
    return sdf, all_df, best


def benchmarks(tbl):
    """核心指标基准对照表（复现值 vs 论文标称值）。"""
    fert = tbl["Fertilizer"] / C.T_PER_MT
    rows = [
        ("矿物磷肥投入 1961 (Mt P)", fert.loc[1961], 4.9),
        ("矿物磷肥投入 2022 (Mt P)", fert.loc[2022], 20.5),
        ("种植业 PUE 2022 (%)", tbl["PUE_c"].loc[2022] * 100, 31.0),
        ("化肥占 ACS 可利用输入 2022 (%)", tbl["Fert_share"].loc[2022] * 100, 64.0),
        ("累计磷矿进入社会系统 (Mt P)", tbl["PR_input"].sum() / C.T_PER_MT, 1153.0),
        ("全球作物纯磷产出 2022 (Mt P)",
         D.global_category_yearly().loc[2022].sum(), 80.0),
    ]
    df = pd.DataFrame(rows, columns=["指标", "复现值", "论文标称值"])
    df["相对偏差%"] = (df["复现值"] / df["论文标称值"] - 1) * 100
    df.to_csv(C.CSV_DIR / "benchmark_comparison.csv", index=False, encoding="utf-8-sig")
    print(df.round(2).to_string(index=False))
    return df


def main():
    print("第十五讲论文复现：全球人为磷流动（Liu et al. 2026, PNAS）")
    print(f"输出目录: {C.OUTPUT_DIR}\n")
    task1()
    tbl = task2()
    task3()
    print(SEP)
    print("核心指标基准对照")
    print(SEP)
    benchmarks(tbl)
    print("\n全部任务完成，输出见 output/csv 与 output/html。")


if __name__ == "__main__":
    main()
