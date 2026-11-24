# -*- coding: utf-8 -*-
"""
成员 B · 任务三：多情景仿真（≥500 组工况）
=========================================================
统筹调用成员 A 的工序活动量（占位）、本模块 LCA 核算，并经由 c_interface
调用成员 C 真实经济/政策引擎，遍历决策变量与外部情景的笛卡尔积，
保存全部参数、结果与不可行原因。

决策变量（可调，属规划可控变量）：
  green_ratio ∈ [0, 1]      园区绿电消纳比例
  process_mix ∈ [0, 1]      直接正极再生占比（0=纯湿法，1=纯直接再生）

外部情景（与决策变量分离，属外部不确定因素）：
  grid_ef            ∈ {0.314, 0.556, 0.749}  区域电网碳强度（文献6）
  lithium_price_usd  ∈ {10000, 22000, 50000}  碳酸锂价格（文献2 低价/基准/高价）
  energy_efficiency  ∈ {0.80, 1.00, 1.20}     工艺能效等级（低效/基准/高效）

输出：data_cohort/scenario_results.csv（含不可行工况及其失效原因）
"""

from __future__ import annotations

import os
from itertools import product

import numpy as np
import pandas as pd

from lca_model import LCAModel, VIRGIN_BENCHMARKS
from c_interface import policy_check, lcor_estimate, USE_PROVISIONAL_BRANCH
import c_annual_interface
import literature_override

_BASE = os.path.dirname(os.path.abspath(__file__))
_OUT = os.path.join(_BASE, "..", "data_cohort", "scenario_results.csv")

# 是否启用成员 A 候选能量参数（ND_SEC 综合能耗 + LS_STEAM 蒸汽）。
# 默认关，保持占位基准不变；ON 时用 A 候选值替换电/热活动量（试剂仍为占位，见 a_candidate_override.py）。
_USE_A = os.environ.get("USE_A_CANDIDATES", "0") == "1"

# 是否用合成 LCOR 占位（仅当成员 C 真实 TEA 未就绪时）。默认关。
# 目的：方法校验——验证“feasible>0 且 LCOR 非空”时帕累托寻优与 B-4 制图代码路径可跑通。
# 该 LCOR 是显式占位（无经济意义），最终必须替换为成员 C 的 evaluate_tea 真实输出。
_USE_PROVISIONAL_LCOR = os.environ.get("USE_PROVISIONAL_LCOR", "0") == "1"

# 主开关：启用 A 全部数据（含未选定的 not_adopted 试剂），并以候选/合成值完成全部 B 任务
# （生成 B-4 帕累托前沿，标记为试算 PROVISIONAL）。默认关，保持严格正式口径。
_USE_ALL_A = os.environ.get("USE_ALL_A_DATA", "0") == "1"
if _USE_ALL_A:
    _USE_A = True
    _USE_PROVISIONAL_LCOR = True

# 文献迁移覆盖：用成员 A 所缺分支指标的文献/规范代理值补齐（非实测、非正式）。
# 取值：0 / faithful / proxy / both(=1)。启用时自动启用合成 LCOR 以生成 B-4（忠实情景不可行）。
_USE_LITERATURE = os.environ.get("USE_LITERATURE_OVERRIDE", "0")
_LIT_ACTIVE = _USE_LITERATURE in ("1", "both", "faithful", "proxy")
if _LIT_ACTIVE:
    _USE_PROVISIONAL_LCOR = True

# 决策变量与情景网格
_GREEN = np.linspace(0.0, 1.0, 11)
_PROCESS = np.linspace(0.0, 1.0, 11)
_GRID_EF = [0.314, 0.556, 0.749]
_LI_PRICE = [10000.0, 22000.0, 50000.0]
_EFF = [0.80, 1.00, 1.20]


def build_activities(process_mix: float, energy_eff: float) -> dict[str, float]:
    """按工艺配比与能效等级构造工序活动量（成员 A 交付后替换）。

    当 USE_A_CANDIDATES=1 时，电/热两项采用成员 A 候选能量参数：
      电耗 = (ND_SEC 综合能耗 − LS_STEAM 蒸汽热) 折算；热耗 = LS_STEAM 蒸汽；
    试剂项仍为占位（A 的 LS_* 试剂系数换算后 NaOH 单耗物理不合理，详见
    a_candidate_override.py，待 A 的 M06/M07 与 M10 分配口径厘清后再接入）。
    """
    pm = float(process_mix)
    ee = float(energy_eff)

    if _USE_A:
        from a_candidate_override import energy_from_a, reagents_from_a

        e = energy_from_a(pm)
        r = reagents_from_a(pm)
        wet = (1 - pm)  # 湿法/混合线占比；直接再生(pm=1)不消耗湿法试剂
        return {
            "electricity_kwh": e["electricity_kwh"] / ee,
            "natural_gas": 0.0,
            "process_steam": e["heat_mj"] / ee,
            "sulfuric_acid_H2SO4": r["sulfuric_acid_H2SO4_kg"] * wet,
            "hydrogen_peroxide_H2O2": 400.0 * wet,
            "sodium_hydroxide_NaOH": r["sodium_hydroxide_NaOH_kg"] * wet,
            "sodium_carbonate_Na2CO3": 1600.0 * (1 - 0.5 * pm),
            "lime_CaO": r["lime_CaO_kg"] * wet,
            "diesel_truck": 2000.0,
            "wastewater_treatment": 30.0 * (1 - 0.5 * pm),
            "fluoride_wastewater_advanced": 10.0 * (1 - 0.7 * pm),
            "hazardous_residue_disposal": 1.5 * (1 - 0.5 * pm),
        }

    return {
        "electricity_kwh": (12000.0 * (1 - pm) + 6000.0 * pm) / ee,
        "natural_gas": (15000.0 * (1 - pm) + 8000.0 * pm) / ee,
        "sulfuric_acid_H2SO4": 2500.0 * (1 - pm),
        "hydrogen_peroxide_H2O2": 400.0 * (1 - pm),
        "sodium_hydroxide_NaOH": 1500.0 * (1 - 0.7 * pm),
        "sodium_carbonate_Na2CO3": 1600.0 * (1 - 0.5 * pm),
        "lime_CaO": 800.0 * (1 - 0.3 * pm),
        "diesel_truck": 2000.0,
        "wastewater_treatment": 30.0 * (1 - 0.5 * pm),
        "fluoride_wastewater_advanced": 10.0 * (1 - 0.7 * pm),
        "hazardous_residue_disposal": 1.5 * (1 - 0.5 * pm),
    }


# ---------------------------------------------------------------------------
# 成员 C 接口：政策与经济一律经 c_interface 调用成员 C 真实引擎
#   policy_engine.evaluate_policy / tea_model.evaluate_tea，不再使用本文件占位桩。
# ---------------------------------------------------------------------------


def _provisional_lcor(gwp: float, water: float, lithium_price_usd: float) -> float:
    """显式占位 LCOR（仅方法校验用，无经济意义）。

    方向性约定：环境负荷（GWP/水耗）越高、经营成本越高 → LCOR 越高；
    锂价越高 → 产品收益口径下 LCOR 越低。系数全程占位，不追求定量真实。
    """
    return 20000.0 + 4.5 * gwp + 0.15 * water - 0.35 * lithium_price_usd


def _simulate(model: LCAModel, branch_metrics, scenario: str, case_start: int) -> tuple[list, int]:
    """按给定分支指标与情景标签生成一行工况结果。

    scenario ∈ {"default","faithful","proxy"}：
      default → 维持原正式/试算判定；
      faithful/proxy → 文献迁移层（合成 LCOR，结果等级 literature_*）。
    """
    is_lit = scenario in ("faithful", "proxy")
    rows = []
    case_id = case_start
    for pm, gr, ef, lp, ee in product(_PROCESS, _GREEN, _GRID_EF, _LI_PRICE, _EFF):
        acts = build_activities(pm, ee)
        res = model.compute(activities=acts, green_ratio=gr, grid_ef=ef)
        pol, failures = policy_check(case_id, acts, pm, branch_metrics=branch_metrics)
        lcor, tea_status = lcor_estimate(acts, gr, lp, pm)
        if _USE_PROVISIONAL_LCOR and (lcor is None or (isinstance(lcor, float) and np.isnan(lcor))):
            lcor = _provisional_lcor(res.gwp_kgco2e, res.water_l, lp)
            tea_status = "PROVISIONAL_SYNTHETIC_LCOR"
        lcor_is_nan = lcor is None or (isinstance(lcor, float) and np.isnan(lcor))

        if is_lit:
            # 文献迁移：可行 + LCOR 非空即列 literature 结果（faithful 会因 cu/al/powder FAIL 不可行）。
            formal_eligible = bool((not lcor_is_nan) and bool(pol["feasible"]))
            result_grade = "literature_migration" if pol["feasible"] else "literature_infeasible"
            policy_source = "literature_faithful" if scenario == "faithful" else "literature_proxy"
        elif _USE_ALL_A:
            formal_eligible = bool((not lcor_is_nan) and bool(pol["feasible"]))
            result_grade = "provisional_all_a"
            policy_source = "provisional_branch_filled" if USE_PROVISIONAL_BRANCH else "formal_engine"
        else:
            lcor_formal = (not lcor_is_nan) and tea_status == "OK"
            policy_formal = (not USE_PROVISIONAL_BRANCH) and bool(pol["feasible"])
            formal_eligible = bool(lcor_formal and policy_formal)
            result_grade = "formal" if formal_eligible else "not_ready"
            policy_source = "provisional_branch_filled" if USE_PROVISIONAL_BRANCH else "formal_engine"

        if tea_status == "OK":
            lcor_source = "formal"
        elif tea_status == "PROVISIONAL_SYNTHETIC_LCOR":
            lcor_source = "provisional_synthetic"
        else:
            lcor_source = "not_ready"
        fail_count = sum(1 for c in pol["checks"] if c["status"] == "FAIL")
        unknown_count = sum(1 for c in pol["checks"] if c["status"] == "UNKNOWN")
        gwp_spod = VIRGIN_BENCHMARKS["hard_rock_spodumene"]["gwp"]
        water_salt = VIRGIN_BENCHMARKS["salt_lake_brine"]["water"]
        rows.append({
            "case_id": case_id,
            "green_ratio": round(gr, 4),
            "process_mix": round(pm, 4),
            "grid_ef": ef,
            "lithium_price_usd": lp,
            "energy_efficiency": ee,
            "electricity_kwh": acts["electricity_kwh"],
            "heat_mj": acts.get("process_steam", acts.get("natural_gas", 0.0)),
            "li_recovery": 0.90 + 0.09 * pm,
            "gwp_kgco2e": res.gwp_kgco2e,
            "water_l": res.water_l,
            "delta_gwp_vs_spodumene_pct": (gwp_spod - res.gwp_kgco2e) / gwp_spod * 100.0,
            "delta_water_vs_saltlake_pct": (water_salt - res.water_l) / water_salt * 100.0,
            "lcor_rmb_per_t": lcor,
            "feasible": pol["feasible"],
            "violations": "; ".join(f"{f['rule_id']}:{f['reason']}" for f in failures),
            "c_policy_status": pol["status"],
            "c_policy_fail_count": fail_count,
            "c_policy_unknown_count": unknown_count,
            "c_tea_status": tea_status,
            "lcor_source": lcor_source,
            "policy_source": policy_source,
            "formal_result_eligible": formal_eligible,
            "result_grade": result_grade,
            "literature_scenario": scenario if is_lit else "",
        })
        case_id += 1
    return rows, case_id


def main() -> pd.DataFrame:
    model = LCAModel()
    rows: list = []

    if _LIT_ACTIVE:
        # 双情景：忠实文献值（faithful，不可行）+ 混合口径（proxy，可生成 B-4）。
        want = _USE_LITERATURE  # faithful / proxy / both(=1)
        next_id = 0
        if want in ("faithful", "both", "1"):
            r, next_id = _simulate(model, literature_override.faithful_metrics(),
                                   "faithful", next_id)
            rows.extend(r)
        if want in ("proxy", "both", "1"):
            r, next_id = _simulate(model, literature_override.proxy_metrics(),
                                   "proxy", next_id)
            rows.extend(r)
    else:
        rows, _ = _simulate(model, None, "default", 0)

    df = pd.DataFrame(rows)
    # 非文献迁移时并入成员 C 年度接口 v2 逐工况状态；文献迁移层独立，不套 C 年度正式门槛。
    if not _LIT_ACTIVE:
        df = c_annual_interface.join(df)
        if not _USE_ALL_A:
            df["formal_result_eligible"] = df["formal_result_eligible"] & df["c_annual_formal_result_eligible"]
    os.makedirs(os.path.dirname(_OUT), exist_ok=True)
    df.to_csv(_OUT, index=False, encoding="utf-8")
    return df


if __name__ == "__main__":
    df = main()
    n = len(df)
    status = df["c_policy_status"].value_counts().to_dict()
    print(f"[情景仿真] 总工况 = {n}（>=500 达标）")
    print(f"  政策引擎：PASS={status.get('PASS', 0)}  FAIL={status.get('FAIL', 0)}  UNKNOWN={status.get('UNKNOWN', 0)}")
    print(f"  GWP100  [{df['gwp_kgco2e'].min():,.0f}, {df['gwp_kgco2e'].max():,.0f}] kgCO2e/t")
    print(f"  水耗    [{df['water_l'].min():,.0f}, {df['water_l'].max():,.0f}] L/t")
    if df["lcor_rmb_per_t"].notna().any():
        print(f"  LCOR    [{df['lcor_rmb_per_t'].min():,.0f}, {df['lcor_rmb_per_t'].max():,.0f}] 元/t")
    else:
        print("  LCOR    未就绪（完整TEA缺年度数量/LCE产量，不输出数值）")
    print(f"  TEA状态  {df['c_tea_status'].unique().tolist()}")
    print(f"  正式结果 eligible（非合成LCOR且非阈值试填政策）  {int(df['formal_result_eligible'].sum())}")
    print(f"  结果等级 result_grade  {df['result_grade'].value_counts().to_dict()}")
    if "literature_scenario" in df.columns and (df["literature_scenario"] != "").any():
        print(f"  文献迁移情景  {df['literature_scenario'].value_counts().to_dict()}")
    if status.get("FAIL"):
        print("\n  政策FAIL原因分布：")
        print(df.loc[df["c_policy_status"] == "FAIL", "violations"].value_counts().head(10).to_string())
    print(f"\n  结果已保存：{os.path.abspath(_OUT)}")