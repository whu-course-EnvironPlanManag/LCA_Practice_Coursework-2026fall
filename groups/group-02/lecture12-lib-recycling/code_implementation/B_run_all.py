# -*- coding: utf-8 -*-
"""
成员 B 一键复现编排脚本
=========================================================
按依赖顺序执行：
  1. scenario_analysis.py  重写 data_cohort/scenario_results.csv（含 LCOR 数值）
  2. optimization.py        读 CSV，输出环境维度图；若检测到 LCOR 就绪，
                            自动生成 B-4 帕累托前沿与推荐锚点

LCOR 就绪判定位于 optimization.make_charts 内部（读 CSV 判断 formal_result_eligible，
即「非合成 LCOR 且非阈值试填政策」的正式可行结果）；本脚本在各步骤结束后读取 CSV
汇总就绪状态，便于成员 C 补齐完整 TEA 后一键重跑，无需逐条手工调用。

AI 提示词（记录）：将 B 的情景仿真与寻优合并为一个按序调用的一键脚本，并在
结束时输出 LCOR 就绪状态汇总。
人工核验：仅承接既有两脚本，不新增、不改动任何数值计算逻辑。

文件监听模式：`python run_all.py --watch` 监视成员 C 的年度接口 v2
    给B_年度接口v2/C_to_B_existing_case_status_v2.json，文件变化即自动重跑一次流水线，Ctrl+C 退出。
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

_BASE = os.path.dirname(os.path.abspath(__file__))
_RESULTS = os.path.join(_BASE, "..", "data_cohort", "scenario_results.csv")
_FIG = os.path.join(_BASE, "..", "figures_output")
_STEP1 = os.path.join(_BASE, "scenario_analysis.py")
_STEP2 = os.path.join(_BASE, "optimization.py")
_C_JSON = Path(__file__).resolve().parents[1] / "data_cohort" / "给B_年度接口v2" / "C_to_B_existing_case_status_v2.json"


def _run(script: str) -> int:
    print(f"\n========== 运行 {os.path.basename(script)} ==========")
    return subprocess.call([sys.executable, script], cwd=_BASE)


def _summarize() -> None:
    df = pd.read_csv(_RESULTS, encoding="utf-8")
    lcor_ready = int(df["lcor_rmb_per_t"].notna().sum())
    feas = int(df["feasible"].sum())
    formal = int(df["formal_result_eligible"].sum()) if "formal_result_eligible" in df.columns else 0
    grade = ""
    if "result_grade" in df.columns:
        grade = str(df["result_grade"].value_counts().to_dict())
    annual_not_ready = int((df["c_annual_tea_status"] == "NOT_READY_ANNUAL_V2").sum()) if "c_annual_tea_status" in df.columns else 0
    provisional = ("result_grade" in df.columns
                   and (df["result_grade"] == "provisional_all_a").any())
    literature = ("literature_scenario" in df.columns
                  and (df["literature_scenario"] != "").any())
    pareto_png = os.path.join(_FIG, "fig_b4_pareto_frontier.png")

    print("\n========== 汇总 ==========")
    print(f"  总工况        {len(df)}")
    print(f"  可行工况(feasible)      {feas}")
    print(f"  LCOR 非空数   {lcor_ready}")
    print(f"  正式结果 eligible       {formal}")
    if grade:
        print(f"  结果等级 result_grade   {grade}")
    print(f"  C年度接口v2 未就绪工况   {annual_not_ready}（NOT_READY_ANNUAL_V2）")

    if literature:
        faithful_infeasible = int((df["result_grade"] == "literature_infeasible").sum())
        print(f"  文献迁移情景  文献值 faithful 不可行={faithful_infeasible}；proxy 可行={feas}")
        print("  状态          文献迁移完成：忠实值无可行解 + proxy 口径 B-4（文献迁移 literature，非A实测/非C正式TEA）")
    elif formal and provisional:
        print("  状态          试算完成（PROVISIONAL）：已用 A 全部候选/合成值生成 B-4 帕累托前沿（试算）")
    elif formal:
        print("  状态          就绪：已生成帕累托前沿与推荐锚点")
    else:
        print("  状态          未就绪：仅输出环境维度图；B-4 待正式政策指标与成员 C 完整 TEA")
        if not os.path.exists(pareto_png):
            print("  B-4 图        未生成（符合预期）")


def run_once() -> int:
    """按序执行一次完整流水线。"""
    rc1 = _run(_STEP1)
    rc2 = _run(_STEP2)
    _summarize()
    return rc1 or rc2


def _file_hash(path: Path) -> str | None:
    """返回文件内容 MD5；文件不存在时返回 None。"""
    if not path.exists():
        return None
    return hashlib.md5(path.read_bytes()).hexdigest()


def watch(interval: float = 5.0) -> int:
    """轮询监视成员 C 的 tea_case_economic_intake.json，变化即自动重跑。"""
    print(f"[监听] 监视文件：{_C_JSON}")
    print("[监听] 检测到内容变化自动重跑流水线（Ctrl+C 退出）。")
    last = _file_hash(_C_JSON)
    try:
        while True:
            time.sleep(interval)
            cur = _file_hash(_C_JSON)
            if cur is None:
                continue
            if last is not None and cur == last:
                continue
            print("\n[监听] 检测到文件变化，自动重跑流水线")
            rc = run_once()
            if rc:
                print(f"[监听] 流水线返回码 {rc}")
            last = cur
    except KeyboardInterrupt:
        print("\n[监听] 已停止")
    return 0


def main() -> int:
    if "--watch" in sys.argv or "-w" in sys.argv:
        return watch()
    return run_once()


if __name__ == "__main__":
    sys.exit(main())