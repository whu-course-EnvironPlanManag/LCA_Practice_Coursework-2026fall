#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lecture12 案例三 · 成员 A：R1 背景情景 —— 宜昌 2026—2040 未来 dMFA 探索表。

本脚本只做一件事：把 R1 快照里 `dmfa_future_2026_2040`（Codex 推算的未来首装 + 替换 +
车辆寿命退役 + c=0.80 收集）落成 CSV，并做可复现校验与纪律标注。

与 dmfa_yichang.py（2010—2025 既有首装队列）并列、不叠加：
    - dmfa_yichang.py 的 2026—2040 是“既有队列剩余释放”；
    - 本表的 2026—2040 是“未来新增首装 + 替换”探索情景，两套口径不可相加。

新增情景假设（非完整复现文献）：首装增长率 5%/a、车辆与电池寿命相互独立、
存续车辆失效包立即替换、替换同体系同质量、跨市迁移不计。

数据入口（只读）：data_cohort/a_group_r1_scenario_20261104.json

输出（data_cohort/，带 dmfa_r1_future 前缀，禁止手改）：
    dmfa_r1_future_annual_inflow.csv   2026—2040 分体系首装/替换流入
    dmfa_r1_future_check.csv           校核年退出/存量和 c=0.80 收集量
    dmfa_r1_future_summary.csv         参数、条件库存、供需量比与纪律

运行：python code_implementation/dmfa_future_r1.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

CODE_DIR = Path(__file__).resolve().parent
WORKDIR = CODE_DIR.parent
DATA_DIR = WORKDIR / "data_cohort"
R1_JSON = DATA_DIR / "a_group_r1_scenario_20261104.json"

sys.path.insert(0, str(CODE_DIR))
import mfa_model  # noqa: E402

FIELDS_INFLOW = ["year", "LFP_first_t_pack_a", "LFP_replace_t_pack_a",
                 "NMC_first_t_pack_a", "NMC_replace_t_pack_a",
                 "total_first_t_pack_a", "total_replace_t_pack_a", "note"]
FIELDS_CHECK = ["year", "total_exit_t_pack_a", "year_end_stock_t_pack",
                "collected_c080_t_pack_a", "demand_ratio_vs_68000", "note"]
FIELDS_SUMMARY = ["key", "value", "unit", "attribute", "note"]
FIELDS_CHK = ["check_id", "item", "status", "detail"]


def load_r1(path: Path = R1_JSON) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def checks(d: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    rows = d["annual_inflow_t_pack_a_rows"]

    def add(cid, item, ok, detail):
        out.append({"check_id": cid, "item": item,
                    "status": "PASS" if ok else "FAIL", "detail": detail})

    add("D-R1-01", "未来 LFP+三元份额=1",
        abs(d["future_LFP_share"] + d["future_NMC_share"] - 1.0) < 1e-9,
        f"{d['future_LFP_share']}+{d['future_NMC_share']}={d['future_LFP_share'] + d['future_NMC_share']:.12f}")
    add("D-R1-02", "未来流入 15 年连续 2026—2040",
        [r["year"] for r in rows] == list(range(2026, 2041)),
        f"{len(rows)} 行，2026—2040")
    add("D-R1-03", "2026 首装=2025×(1+0.05)",
        abs(rows[0]["LFP_first"] + rows[0]["NMC_first"] - d["base_year_2025_install_t_a"] * 1.05) < 0.01,
        f"{rows[0]['LFP_first'] + rows[0]['NMC_first']:.4f} vs {d['base_year_2025_install_t_a'] * 1.05:.4f}")
    add("D-R1-04", "2030 收集=退出×0.80",
        abs(d["collection_results"][0]["collected_t_pack_a"] - d["check_rows"][0]["total_battery_exit_t_pack_a"] * 0.80) < 1e-3,
        f"{d['collection_results'][0]['collected_t_pack_a']:.4f} = {d['check_rows'][0]['total_battery_exit_t_pack_a']}×0.80")
    add("D-R1-05", "2040 收集=退出×0.80",
        abs(d["collection_results"][1]["collected_t_pack_a"] - d["check_rows"][2]["total_battery_exit_t_pack_a"] * 0.80) < 1e-3,
        f"{d['collection_results'][1]['collected_t_pack_a']:.4f} = {d['check_rows'][2]['total_battery_exit_t_pack_a']}×0.80")
    add("D-R1-06", "供需量比=收集/68000",
        abs(d["collection_results"][0]["demand_ratio_vs_68000"] - d["collection_results"][0]["collected_t_pack_a"] / 68000) < 5e-4
        and abs(d["collection_results"][1]["demand_ratio_vs_68000"] - d["collection_results"][1]["collected_t_pack_a"] / 68000) < 5e-4,
        f"2030 {d['collection_results'][0]['demand_ratio_vs_68000']*100:.2f}% / 2040 {d['collection_results'][1]['demand_ratio_vs_68000']*100:.2f}%")
    return out


def inflow_rows(d: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for r in d["annual_inflow_t_pack_a_rows"]:
        out.append({
            "year": r["year"],
            "LFP_first_t_pack_a": r["LFP_first"],
            "LFP_replace_t_pack_a": r["LFP_replace"],
            "NMC_first_t_pack_a": r["NMC_first"],
            "NMC_replace_t_pack_a": r["NMC_replace"],
            "total_first_t_pack_a": round(r["LFP_first"] + r["NMC_first"], 6),
            "total_replace_t_pack_a": round(r["LFP_replace"] + r["NMC_replace"], 6),
            "note": "首装增长率 5%/a；替换=存续车辆电池失效立即同体系同质量换包（情景假设）",
        })
    return out


def check_rows(d: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    col = {c["year"]: c for c in d["collection_results"]}
    for r in d["check_rows"]:
        c = col.get(r["year"])
        out.append({
            "year": r["year"],
            "total_exit_t_pack_a": r["total_battery_exit_t_pack_a"],
            "year_end_stock_t_pack": r["year_end_total_stock_t_pack"],
            "collected_c080_t_pack_a": c["collected_t_pack_a"] if c else None,
            "demand_ratio_vs_68000": c["demand_ratio_vs_68000"] if c else None,
            "note": "退出含换下电池+随车报废电池，未乘收集率、未扣梯次及其他企业分流",
        })
    return out


def summary_rows(d: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    def add(k, v, unit, attr, note=""):
        out.append({"key": k, "value": v, "unit": unit, "attribute": attr, "note": note})
    s = d["2025_end_conditional_stock_t"]
    add("scenario_id", "R1_PLANNING_20261104", "-", "情景假设", "背景情景，automatically_adopted=false")
    add("base_year_2025_install", d["base_year_2025_install_t_a"], "t整包/a", "文献迁移", "沿用原 A 条件重建")
    add("first_install_growth_rate", d["first_install_growth_rate"], "1/a", "情景假设", "5%/a")
    add("future_LFP_share", d["future_LFP_share"], "1", "情景假设", "固定")
    add("future_NMC_share", d["future_NMC_share"], "1", "情景假设", "固定")
    add("vehicle_life_k", d["vehicle_life_k_weibull"], "-", "文献原值", "Zhang 2025 SI Table 2")
    add("vehicle_life_lambda", d["vehicle_life_lambda_year"], "年", "文献原值", "Zhang 2025 SI Table 2")
    add("collection_rate_c", d["collection_rate_scenario_c"], "1", "情景假设", "c=0.80")
    add("vehicle_battery_independent", d["vehicle_battery_independent_lifetime"], "-", "情景假设", "相互独立")
    add("broken_immediate_replace", d["broken_battery_immediate_replace"], "-", "情景假设", "存续车辆失效包立即替换")
    add("cross_city_migration", d["cross_city_migration_ignored"], "-", "情景假设", "不计迁移")
    add("2025_end_stock_LFP", s["LFP"], "t整包", "情景重建", "99,750 辆车锚点，非宜昌实测库存")
    add("2025_end_stock_NMC", s["NMC"], "t整包", "情景重建", "同上")
    add("2025_end_stock_total", s["total"], "t整包", "情景重建", "同上")
    return out


def main() -> int:
    print("=" * 78)
    print("成员 A：R1 背景情景 —— 宜昌 2026—2040 未来 dMFA 探索表")
    print("=" * 78)
    r1 = load_r1()
    d = r1["dmfa_future_2026_2040"]

    chk = checks(d)
    for c in chk:
        print(f"[{c['status']:>4}] {c['check_id']} {c['item']} :: {c['detail']}")
    failed = [c for c in chk if c["status"] == "FAIL"]
    if failed:
        print(f"\n[中止] {len(failed)} 项失败：不写表。")
        mfa_model.write_csv("dmfa_r1_future_checks.csv", chk, FIELDS_CHK)
        return 1

    mfa_model.write_csv("dmfa_r1_future_checks.csv", chk, FIELDS_CHK)
    mfa_model.write_csv("dmfa_r1_future_annual_inflow.csv", inflow_rows(d), FIELDS_INFLOW)
    mfa_model.write_csv("dmfa_r1_future_check.csv", check_rows(d), FIELDS_CHECK)
    mfa_model.write_csv("dmfa_r1_future_summary.csv", summary_rows(d), FIELDS_SUMMARY)

    print("\n" + "-" * 78)
    print("输出：dmfa_r1_future_annual_inflow.csv / dmfa_r1_future_check.csv / "
          "dmfa_r1_future_summary.csv / dmfa_r1_future_checks.csv")
    print("纪律：未来存量与收集量为条件情景值，非宜昌实测；退出量未扣梯次与其他企业分流；供需量比≠园区进料")
    return 0


if __name__ == "__main__":
    sys.exit(main())