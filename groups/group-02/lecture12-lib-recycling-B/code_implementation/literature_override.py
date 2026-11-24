# -*- coding: utf-8 -*-
"""
文献迁移补充层（成员 B · USE_LITERATURE_OVERRIDE）
=========================================================
把 members A 所缺的分支级指标，用公开文献/工程报告值补齐，并逐项标出来源、
页/表定位与迁移假设。提供两套分支指标与一张「文献值 vs 阈值」诊断表：

  * faithful_metrics()：忠实文献值（cu/al=0.90、电极粉=0.9328），诚实触发
    CN_CU/CN_AL/CN_POWDER 的 FAIL，导致 policy 不可行（feasible=0）。
  * proxy_metrics()：混合口径（Li/Ni/Co/Mn=ANL 文献；cu/al/电极粉=规范阈值
    0.98 代理，明示非文献），可生成 B-4 帕累托前沿。

命名约定：本模块产出是「文献迁移(literature)」情景，不是成员 A 厂房实测、
不是成员 C 正式 TEA；结果等级用 literature_infeasible / literature_migration。
"""
from __future__ import annotations

import json
import os
from pathlib import Path

_BASE = Path(__file__).resolve().parents[1]          # lecture12-lib-recycling-B
_JSON = _BASE / "data_cohort" / "literature_override.json"

# 是否启用文献迁移覆盖。取值：0 / faithful / proxy / both
USE_LITERATURE = os.environ.get("USE_LITERATURE_OVERRIDE", "0")
USE_LITERATURE_ACTIVE = USE_LITERATURE in ("1", "both", "faithful", "proxy")


def _load() -> dict:
    if _JSON.exists():
        return json.loads(_JSON.read_text(encoding="utf-8"))
    return {}


# ---------------------------------------------------------------------------
# 两套分支指标（与 c_interface._build_policy_case 的 metrics 键对齐）
# ---------------------------------------------------------------------------
_FAITHFUL = {
    "li_smelting_recovery": 0.90,        # ANL EverBatt 表12 Li
    "ni_smelting_recovery": 0.98,        # ANL 表12 Ni
    "co_smelting_recovery": 0.98,        # ANL 表12 Co
    "mn_smelting_recovery": 0.98,        # ANL 表12 Mn
    "cu_recovery": 0.90,                 # ANL 表12 Cu（低于 0.98 阈值）
    "al_recovery": 0.90,                 # ANL 表12 Al（低于 0.98 阈值）
    "electrode_powder_recovery": 0.9328, # Yingnakorn 2026 表1 EV I（低于 0.98 阈值）
    "powder_al_impurity": 0.01,          # 规范边界代理（非文献）
    "powder_cu_impurity": 0.01,          # 规范边界代理（非文献）
    "fluorine_fixation": 0.995,          # 任务书代理（非文献）
    "process_wastewater_reuse": 0.90,    # 海洋规范阈值代理（非文献）
    "repair_material_recovery": 0.99,    # 规范阈值代理（非文献）
    "rd_revenue_fraction": 0.03,         # 经济口径代理（非文献）
}

_PROXY = {
    "li_smelting_recovery": 0.90,        # ANL 表12 Li（文献）
    "ni_smelting_recovery": 0.98,        # ANL 表12 Ni（文献）
    "co_smelting_recovery": 0.98,        # ANL 表12 Co（文献）
    "mn_smelting_recovery": 0.98,        # ANL 表12 Mn（文献）
    "cu_recovery": 0.98,                 # 非文献：CN2024 任务书阈值代理
    "al_recovery": 0.98,                 # 非文献：CN2024 任务书阈值代理
    "electrode_powder_recovery": 0.98,   # 非文献：CN2024 规范阈值代理
    "powder_al_impurity": 0.01,          # 规范边界代理（非文献）
    "powder_cu_impurity": 0.01,          # 规范边界代理（非文献）
    "fluorine_fixation": 0.995,
    "process_wastewater_reuse": 0.90,
    "repair_material_recovery": 0.99,
    "rd_revenue_fraction": 0.03,
}


def faithful_metrics() -> dict:
    j = _load()
    m = j.get("branch_metrics_faithful", {}).get("metrics")
    return dict(m) if m else dict(_FAITHFUL)


def proxy_metrics() -> dict:
    j = _load()
    m = j.get("branch_metrics_proxy", {}).get("metrics")
    return dict(m) if m else dict(_PROXY)


def non_literature_fields(variant: str = "faithful") -> list:
    j = _load()
    key = "branch_metrics_faithful" if variant == "faithful" else "branch_metrics_proxy"
    return list(j.get(key, {}).get("non_literature_fields", []))


def diagnostic_rows() -> list:
    """文献值 vs 阈值 比对表（供 strict 情景诊断图）。"""
    j = _load()
    rows = j.get("diagnostic_vs_threshold", [])
    if rows:
        return rows
    return [
        {"metric": "li_smelting_recovery", "label": "锂回收率", "literature": 0.90, "threshold": 0.90, "op": ">="},
        {"metric": "ni_smelting_recovery", "label": "镍回收率", "literature": 0.98, "threshold": 0.98, "op": ">="},
        {"metric": "co_smelting_recovery", "label": "钴回收率", "literature": 0.98, "threshold": 0.98, "op": ">="},
        {"metric": "mn_smelting_recovery", "label": "锰回收率", "literature": 0.98, "threshold": 0.98, "op": ">="},
        {"metric": "cu_recovery", "label": "铜回收率", "literature": 0.90, "threshold": 0.98, "op": ">="},
        {"metric": "al_recovery", "label": "铝回收率", "literature": 0.90, "threshold": 0.98, "op": ">="},
        {"metric": "electrode_powder_recovery", "label": "电极粉捕集率", "literature": 0.9328, "threshold": 0.98, "op": ">="},
    ]


if __name__ == "__main__":
    print("=" * 78)
    print("文献迁移补充层 · 诊断输出")
    print("=" * 78)
    print("[忠实文献值]")
    for k, v in faithful_metrics().items():
        print(f"  {k:<28s} {v:>8.4f}")
    print("\n[文献值 vs 阈值]")
    for r in diagnostic_rows():
        ok = "✓达标" if r["literature"] >= r["threshold"] else "✗不足"
        print(f"  {r['label']:<12s} 文献 {r['literature']:<7} 阈值 {r['threshold']:<6} {ok}")
    print("\n注意：cu/al=0.90、电极粉=0.9328 低于 0.98 阈值 → 忠实情景 policy 不可行；")
    print("      proxy 情景用 0.98 阈值代理（非文献）可生成 B-4。")