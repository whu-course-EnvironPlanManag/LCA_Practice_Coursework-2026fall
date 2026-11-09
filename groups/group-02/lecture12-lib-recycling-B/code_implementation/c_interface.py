# -*- coding: utf-8 -*-
"""
成员B与成员C、成员A的接口适配器（对接层）。

用途：
  将B情景仿真中原先的占位桩（policy_check_stub / lcor_stub）替换为对成员C
  真实引擎的调用：
    * 政策合规  -> policy_engine.evaluate_policy
    * 技术经济(LCOR) -> tea_model.evaluate_tea
  同时明确B的数据边界：B只负责环境端(gwp/水耗/电热)，政策与经济口径一律以
  C的引擎为准；B不复制、不伪造C的价格/数量。

AI Prompt（记录）：
  将B的 policy_check_stub / lcor_stub 替换为调用C的 evaluate_policy /
  evaluate_tea，并在C完整TEA数据未就绪时不伪造LCOR数值。
人工核验：待成员C复核政策规则映射与TEA口径；成员A复核年度数量与LCE产量入口。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]          # groups/group-02
_C_CODE = _ROOT / "lecture12-lib-recycling" / "code_implementation"
_C_DATA = _ROOT / "lecture12-lib-recycling" / "data_cohort"

if str(_C_CODE) not in sys.path:
    sys.path.insert(0, str(_C_CODE))

from policy_engine import evaluate_policy            # noqa: E402
from tea_model import evaluate_tea                   # noqa: E402


# 折标系数（与B scenario_analysis 中原折标口径一致）
KWH_TO_KGCE = 0.1229
MJ_TO_KGCE = 1.0 / 29.3076

# ---------------------------------------------------------------------------
# 缺失分支指标的“未选定值”试用填充（默认关；仅用于方法校验，非实测、非最终结果）
# 来源：A 的 reference_policies（R09/R10/R11 规范阈值）+ C 的 policy_parameters.json
#        中 TASK_CN2024 项（cu/al 回收率、固氟、研发占比）。
# 注意：这些是“达标阈值”而非“实测收率”，直接填充会造成“恰好达标=>全 PASS”的同义反复，
#       只能用于验证优化代码路径，最终须以 A 的 M02/M05/M06 实测分支指标替换。
# ---------------------------------------------------------------------------
_USE_PROVISIONAL_BRANCH = (os.environ.get("USE_PROVISIONAL_BRANCH_METRICS", "0") == "1"
                            or os.environ.get("USE_ALL_A_DATA", "0") == "1")
# 透出给 scenario_analysis：用于标记每行结果的“政策判定来源”，把阈值试填结果从正式结论中排除。
USE_PROVISIONAL_BRANCH = _USE_PROVISIONAL_BRANCH

_PROVISIONAL_BRANCH_METRICS = {
    "li_smelting_recovery": 0.90,          # A R10-1 冶炼锂回收率阈值
    "ni_smelting_recovery": 0.98,          # A R10-2 冶炼镍回收率阈值
    "co_smelting_recovery": 0.98,          # A R10-2 冶炼钴回收率阈值
    "mn_smelting_recovery": 0.98,          # A R10-2 冶炼锰回收率阈值
    "cu_recovery": 0.98,                   # C TASK_CN2024（铜回收率，任务书口径）
    "al_recovery": 0.98,                   # C TASK_CN2024（铝回收率，任务书口径）
    "electrode_powder_recovery": 0.98,     # A R09-1 电极粉料回收率阈值
    "powder_al_impurity": 0.01,            # A R09-2 杂质铝<1.5%，取1.0%用于校验
    "powder_cu_impurity": 0.01,            # A R09-3 杂质铜<1.5%，取1.0%用于校验
    "fluorine_fixation": 0.995,            # C TASK_CN2024（固氟率，任务书口径）
    "process_wastewater_reuse": 0.90,      # A R11-2 工艺废水循环利用率阈值
    "repair_material_recovery": 0.99,      # A R10-3 材料修复回收占比阈值
    "rd_revenue_fraction": 0.03,           # CN_RD 研发投入占比阈值（经济口径待 C 补）
}


def _route(process_mix: float) -> str:
    pm = float(process_mix)
    if pm == 0.0:
        return "smelting"
    if pm == 1.0:
        return "repair"
    return "mixed"


def _build_policy_case(case_id, activities, process_mix, evaluation_date: str = "2030-12-31",
                       branch_metrics: dict | None = None) -> dict:
    """按C政策引擎的case结构构造输入；B仅提供环境与锂回收能力相关的可计算指标。

    branch_metrics：可选的分支级指标字典（如文献迁移层的忠实/代理值）；传入时
    直接填充并计算吨LCE综合能耗，优先级高于阈值试用填充（讨论中的 _PROVISIONAL_BRANCH_METRICS）。
    """
    pm = float(process_mix)
    heat = activities.get("natural_gas", 0.0) + activities.get("process_steam", 0.0)
    energy = activities["electricity_kwh"] * KWH_TO_KGCE + heat * MJ_TO_KGCE

    case = {
        "case_id": str(case_id),
        "evaluation_date": evaluation_date,
        "route": _route(pm),
        "metals_present": ["Li", "Ni", "Co", "Mn", "Cu", "Al"],
        "eu_material_recovery_scope": False,
        "eu_new_battery_scope": False,
        "produces_lithium_carbonate": pm < 1.0,
        "metrics": {
            "recycling_capacity_t_per_year": 70000,
        },
    }
    if pm == 0.0:
        # 纯湿法：冶炼锂回收率与吨LCE综合能耗可判定；其余回收率/杂质指标由A补充后判定。
        case["metrics"]["li_smelting_recovery"] = 0.90
        case["metrics"]["lce_energy_kgce_per_t"] = energy
    if branch_metrics is not None:
        # 文献迁移层：以文献/规范代理值补齐分支指标（结果标记 literature，不视为正式）。
        case["metrics"].update(branch_metrics)
        case["metrics"]["lce_energy_kgce_per_t"] = energy
    elif _USE_PROVISIONAL_BRANCH:
        # 试用填充：以 A/C 的规范阈值/任务书口径补齐缺失分支指标（非实测，仅方法校验）。
        case["metrics"].update(_PROVISIONAL_BRANCH_METRICS)
        case["metrics"]["lce_energy_kgce_per_t"] = energy
    # 混合(0<pm<1)需分支级回收率、纯修复(pm==1)需材料修复率，均由A提供；未启用填充时留UNKNOWN。
    return case


def policy_check(case_id, activities, process_mix, branch_metrics: dict | None = None):
    """调用C政策引擎。返回 (evaluate_policy结果dict, FAIL规则列表)。"""
    case = _build_policy_case(case_id, activities, process_mix, branch_metrics=branch_metrics)
    result = evaluate_policy(case, profile="coursework")
    failures = [c for c in result["checks"] if c["status"] == "FAIL"]
    return result, failures


def _load_economic_case() -> dict:
    p = _C_DATA / "tea_case_economic_intake.json"
    return json.loads(p.read_text(encoding="utf-8"))


def _missing_tea_fields(case: dict) -> list:
    """与C handoff_analysis.completion_check 一致的必要字段核对。"""
    missing: list = []
    for key in ("price_year", "fu_per_year", "capex", "discount_rate", "operating_years"):
        if case.get(key) is None:
            missing.append(key)
    for section in ("cost_items", "revenue_items"):
        for row in case.get(section, []):
            for key in ("quantity_per_year", "unit_price"):
                if row.get(key) is None:
                    missing.append(f"{section}.{row.get('name')}.{key}")
    return missing


def lcor_estimate(activities, green_ratio, lithium_price_usd, process_mix):
    """经C的 tea_model 计算LCOR。

    C当前经济录入中 fu_per_year 及各项 quantity_per_year 仍未齐（由A年度数量、
    C价格证据补齐），因此本函数在数据齐备前返回未就绪，而非沿用B旧占位数值。
    至于锂价外部情景联动，统一走 C 的 price_link 机制，待数量齐后接入。
    """
    case = _load_economic_case()
    missing = _missing_tea_fields(case)
    if missing:
        return float("nan"), f"NOT_READY_{len(missing)}_missing_fields"

    result = evaluate_tea(case)
    return float(result["base_lcor_per_fu"]), "OK"