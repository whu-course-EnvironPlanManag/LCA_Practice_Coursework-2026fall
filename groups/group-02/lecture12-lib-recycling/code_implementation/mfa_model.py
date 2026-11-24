#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lecture12 案例三（锂离子电池回收）成员 A 中期建模：来料通量分配 / 组分存量 / Li 守恒接口。

职责边界（来自 A前期数据_IDE交接包_20261103/README_交给IDE前先读.md 与 IDE启动提示词.md）：
    1. 读取并校验 a_phase1_ide_handoff.json（只读，不改动、不覆盖原始快照）；
    2. 只计算 handoff 明确放开的模块：
         json_loading_and_validation / received_pack_intake_allocation / received_component_inventory；
    3. 为后续湿法/直接再生物质流预留接口，但阻断项未解除前一律不产出数值；
    4. 缺失值保持为 None（缺数不等于 0），不替缺失数据编造产率、品位或投资；
    5. 提供 Li 元素守恒核验函数：in_Li == 0 时判定 undefined（不是 PASS）。

AI 辅助说明（按作业任务书要求记录）：
    提示词摘要：“读取 A 交接包 JSON，按 calculation_gates 只实现 ready 模块；实现来料分配与
    组分存量核算、Li 守恒接口、缺失项报告；禁止填充缺失值、禁止归一化部分组成、禁止输出
    未解锁的湿法流量；导出 CSV 到 data_cohort/”。
    人工复核：本脚本所有计算口径需由成员 A 逐项复核后方可写入报告。

运行：python code_implementation/mfa_model.py
输出：data_cohort/*.csv（UTF-8 with BOM，便于 Excel 打开）
"""

from __future__ import annotations

import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

WORKDIR = Path(__file__).resolve().parent.parent
HANDOFF_DIR = WORKDIR / "data_cohort" / "A前期数据_IDE交接包_20261103"
HANDOFF_JSON = HANDOFF_DIR / "a_phase1_ide_handoff.json"
DATA_DIR = WORKDIR / "data_cohort"

REQUIRED_TOP_KEYS = (
    "dataset", "conventions", "case_definition", "sources", "source_aliases",
    "baseline_inputs", "composition_profiles", "candidate_process_parameters",
    "reference_literature_parameters", "reference_policies", "evidence_register",
    "unresolved_inputs", "calculation_gates", "integration_notes",
    "ide_bootstrap_instructions", "data_dictionary",
)

FRACTION_TOL = 1e-9          # 组成分数求和容差（complete_partition）
LI_REL_TOL = 5e-4            # 全厂 Li 守恒相对误差上限（严格小于，见 conventions）
ZERO_LI_BEHAVIOR = "undefined_not_pass"

STAGE_DEFINITION = (
    # (stage_id, 名称, 主要输入, 主要输出, 阻断输入)
    ("S1", "来料接收与放电", "整包退役电池", "放电后整包 / 拆解前暂存", ("M01", "M02")),
    ("S2", "机械拆解与破碎分选", "放电后整包", "外壳 / 集流体 / 铜铝箔 / 隔膜 / 电解液 / 黑粉", ("M02",)),
    ("S3", "湿法浸出或直接再生", "黑粉（含胶黏剂）", "浸出液 / 浸出渣 / 再生前驱体", ("M03", "M05", "M06", "M07")),
    ("S4", "产品精炼与副产品", "浸出液 / 前驱体", "碳酸锂 / 磷酸铁 / 硫酸盐副产品", ("M03", "M05")),
    ("S5", "污染治理与公用工程", "废水 / 尾气 / 固废", "达标排放 / 委外处置 / 回用水", ("M06", "M07")),
)


# ----------------------------------------------------------------------------- 基础 IO
def load_handoff(path: Path = HANDOFF_JSON) -> dict[str, Any]:
    """只读加载交接包；文件不存在时直接报错，不做任何兜底猜测。"""
    if not path.exists():
        raise FileNotFoundError(
            f"未找到交接包：{path}\n请确认 A前期数据_IDE交接包_20261103 目录与仓库同层级存在。"
        )
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def write_csv(name: str, rows: list[dict[str, Any]], fieldnames: list[str]) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = DATA_DIR / name
    with out.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: ("" if row.get(k) is None else row.get(k)) for k in fieldnames})
    return out


def fmt(value: Any, digits: int = 3) -> str:
    if value is None:
        return "未定义"
    if isinstance(value, float):
        return f"{value:,.{digits}f}"
    return str(value)


# ----------------------------------------------------------------------------- 校验
@dataclass
class Check:
    check_id: str
    item: str
    status: str          # PASS / FAIL / NOTE
    detail: str = ""


def _gate_closure(gate_map: dict[str, dict], module: str) -> set[str]:
    """按依赖关系递归求阻断输入集合（direct ∪ 依赖模块的阻断集合）。"""
    gate = gate_map[module]
    blocking = set(gate.get("direct_blocking_input_ids") or [])
    for dep in gate.get("depends_on_modules") or []:
        if dep in gate_map:
            blocking |= _gate_closure(gate_map, dep)
    return blocking


def validate_dataset(raw: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []

    missing = [k for k in REQUIRED_TOP_KEYS if k not in raw]
    checks.append(Check("V01", "顶层字段完整性", "PASS" if not missing else "FAIL",
                        "16 个顶层字段齐全" if not missing else f"缺失：{missing}"))

    ds = raw.get("dataset", {})
    checks.append(Check("V02", "schema_version", "PASS" if ds.get("schema_version") == "1.0.0" else "FAIL",
                        f"schema_version={ds.get('schema_version')}"))
    checks.append(Check("V03", "coding_ready", "PASS" if ds.get("coding_ready") is True else "FAIL",
                        f"coding_ready={ds.get('coding_ready')}"))
    checks.append(Check("V04", "full_process_model_ready 必须为 false",
                        "PASS" if ds.get("full_process_model_ready") is False else "FAIL",
                        "交接包声明全流程模型未就绪，禁止产出全厂流量" if ds.get("full_process_model_ready") is False
                        else "交接包声明与预期不符"))
    checks.append(Check("V05", "原始快照未被改写",
                        "PASS" if ds.get("source_documents_modified") is False else "NOTE",
                        f"source_documents_modified={ds.get('source_documents_modified')}；本脚本只读"))

    base = raw.get("baseline_inputs", {})
    shares = base.get("incoming_pack_chemistry_mass_shares") or []
    share_sum = sum(float(s.get("value") or 0) for s in shares)
    checks.append(Check("V06", "来料体系质量份额合计为 1",
                        "PASS" if abs(share_sum - 1.0) <= FRACTION_TOL else "FAIL",
                        f"合计={share_sum:.12f}；数据性质={base.get('chemistry_shares_data_type')}"))

    profiles = {p["profile_id"]: p for p in raw.get("composition_profiles", [])}
    selected = base.get("selected_front_end_profile_ids") or []
    absent = [pid for pid in selected if pid not in profiles]
    ineligible = [pid for pid in selected if pid in profiles and not profiles[pid].get("eligible_for_received_component_inventory")]
    checks.append(Check("V07", "选用的前段组成代理存在且可用于来料组分核算",
                        "PASS" if not absent and not ineligible else "FAIL",
                        f"选用 {len(selected)} 个；缺失 {absent}；不可用 {ineligible}"))

    frac_bad = [
        f"{p['profile_id']}:{c['component_id']}={c['mass_fraction']}"
        for p in raw.get("composition_profiles", []) for c in p["components"]
        if not (0.0 <= float(c["mass_fraction"]) <= 1.0)
    ]
    checks.append(Check("V08", "组分分数均位于 [0,1]", "PASS" if not frac_bad else "FAIL",
                        "全部合规" if not frac_bad else f"越界：{frac_bad[:5]}"))

    sum_bad, partial = [], []
    for p in raw.get("composition_profiles", []):
        total = sum(float(c["mass_fraction"]) for c in p["components"])
        if p.get("complete_partition"):
            if abs(total - 1.0) > FRACTION_TOL:
                sum_bad.append(f"{p['profile_id']}={total:.12f}")
        else:
            partial.append(f"{p['profile_id']}={total:.6f}")
    checks.append(Check("V09", "完整分配的组成合计为 1", "PASS" if not sum_bad else "FAIL",
                        "全部合规" if not sum_bad else f"偏差：{sum_bad}"))
    checks.append(Check("V10", "部分组成不得归一化", "PASS",
                        "未归一化；仅记录原始合计：" + "；".join(partial) if partial else "无部分组成"))

    cands = raw.get("candidate_process_parameters", [])
    active = [c["parameter_id"] for c in cands if c.get("active") or c.get("usable_for_calculation")]
    checks.append(Check("V11", "候选工艺参数不得默认启用", "PASS" if not active else "FAIL",
                        f"共 {len(cands)} 个候选，启用 {len(active)} 个" + (f"：{active}" if active else "")))

    unresolved = raw.get("unresolved_inputs", [])
    invented = [u["input_id"] for u in unresolved if u.get("value") not in (None, "", [])]
    checks.append(Check("V12", "未解决输入必须保持空值（缺数≠0）", "PASS" if not invented else "FAIL",
                        f"共 {len(unresolved)} 项；已填数值 {invented}" if invented else f"共 {len(unresolved)} 项，全部为 null"))

    if base.get("activated_hydrometallurgical_profile_id") is not None:
        checks.append(Check("V13", "未擅自激活湿法模块", "FAIL",
                            f"activated={base.get('activated_hydrometallurgical_profile_id')}"))
    else:
        checks.append(Check("V13", "未擅自激活湿法模块", "PASS",
                            f"activated_hydrometallurgical_profile_id=None；启用参数 {len(base.get('activated_process_parameter_ids') or [])} 个"))

    gates = {g["module"]: g for g in raw.get("calculation_gates", [])}
    unknown_ids: list[str] = []
    unresolved_ids = {u["input_id"] for u in unresolved}
    for g in gates.values():
        unknown_ids += [i for i in (g.get("blocking_input_ids") or []) if i not in unresolved_ids]
    checks.append(Check("V14", "闸门阻断项均指向已登记未解决输入", "PASS" if not unknown_ids else "FAIL",
                        "全部可追溯" if not unknown_ids else f"未知编号：{sorted(set(unknown_ids))}"))

    closure_bad = []
    for module, g in gates.items():
        computed = _gate_closure(gates, module)
        if set(g.get("blocking_input_ids") or []) != computed:
            closure_bad.append(f"{module}: 申报{sorted(g.get('blocking_input_ids') or [])} vs 计算{sorted(computed)}")
    checks.append(Check("V15", "闸门阻断项等于依赖闭包", "PASS" if not closure_bad else "FAIL",
                        f"{len(gates)} 个模块全部一致" if not closure_bad else "；".join(closure_bad[:3])))

    ready_but_blocked = [m for m, g in gates.items() if g.get("ready") and (g.get("blocking_input_ids") or [])]
    checks.append(Check("V16", "ready 模块不得残留阻断项", "PASS" if not ready_but_blocked else "FAIL",
                        "全部一致" if not ready_but_blocked else f"异常模块：{ready_but_blocked}"))

    tol = (raw.get("conventions", {}).get("full_li_balance_tolerance") or {})
    tol_ok = abs(float(tol.get("relative_error_max_exclusive") or 0) - LI_REL_TOL) <= 1e-12
    zero_ok = tol.get("zero_input_behavior") == ZERO_LI_BEHAVIOR
    checks.append(Check("V17", "Li 守恒容差与零输入约定", "PASS" if tol_ok and zero_ok else "FAIL",
                        f"严格小于 {tol.get('relative_error_max_exclusive')}；零输入={tol.get('zero_input_behavior')}"))

    return checks


def print_checks(checks: list[Check]) -> None:
    print("[1] 交接包结构校验")
    for c in checks:
        print(f"    {c.check_id} {c.status:<4} {c.item} — {c.detail}")
    failed = [c for c in checks if c.status == "FAIL"]
    print(f"    小结：{len(checks) - len(failed)}/{len(checks)} 通过" + ("" if not failed else f"；失败 {[c.check_id for c in failed]}"))


# ----------------------------------------------------------------------------- 可用模块
def allocate_intake(raw: dict[str, Any]) -> list[dict[str, Any]]:
    """received_pack_intake_allocation：把规划来料按体系质量份额分配（未扣除梯次利用分流）。"""
    base = raw["baseline_inputs"]
    annual = base["annual_received_pack_input"]
    rows = []
    for share in base["incoming_pack_chemistry_mass_shares"]:
        rows.append({
            "chemistry": share["chemistry"],
            "mass_share": float(share["value"]),
            "annual_mass_t_a": annual["value"] * float(share["value"]),
            "annual_basis": f"{annual['value']} {annual['unit']}",
            "data_type": base.get("chemistry_shares_data_type"),
            "source_ids": ";".join(annual.get("source_ids") or []),
            "note": "规划假设，非市场实测份额；梯次利用分流（M01）未扣除",
        })
    return rows


def component_inventory(raw: dict[str, Any], allocation: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """received_component_inventory：整包级组分存量 + 电芯组展开（不与整包级相加）。"""
    profiles = {p["profile_id"]: p for p in raw["composition_profiles"]}
    pair = {"LFP": ("JR23_LFP_PACK", "JR23_LFP_CELL"),
            "MIXED_NMC_UNSPECIFIED": ("JR23_NMC_PACK", "JR23_NMC_CELL")}
    rows: list[dict[str, Any]] = []
    for item in allocation:
        pack_id, cell_id = pair[item["chemistry"]]
        pack, cell = profiles[pack_id], profiles[cell_id]
        intake = item["annual_mass_t_a"]
        cell_frac_of_pack = None
        for comp in pack["components"]:
            frac = float(comp["mass_fraction"])
            if comp["component_kind"] == "component_group" and "电芯" in comp["component_name"]:
                cell_frac_of_pack = frac
        if cell_frac_of_pack is None:
            raise KeyError(f"{pack_id} 未找到电芯组，无法展开电芯级组成")
        for comp in pack["components"]:
            rows.append({
                "chemistry": item["chemistry"],
                "level": "整包",
                "component": comp["component_name"],
                "fraction_of_basis": float(comp["mass_fraction"]),
                "annual_mass_t_a": intake * float(comp["mass_fraction"]),
                "is_additive_with_pack": "是",
                "basis_note": "占整包质量；整包级组分可相加",
                "source_ids": ";".join(comp.get("source_ids") or []),
                "profile_id": pack_id,
            })
        cell_mass = intake * cell_frac_of_pack
        for comp in cell["components"]:
            rows.append({
                "chemistry": item["chemistry"],
                "level": "电芯展开",
                "component": comp["component_name"],
                "fraction_of_basis": float(comp["mass_fraction"]),
                "annual_mass_t_a": cell_mass * float(comp["mass_fraction"]),
                "is_additive_with_pack": "否（属电芯组的展开）",
                "basis_note": f"占电芯质量；电芯质量={cell_frac_of_pack:.5f}×整包",
                "source_ids": ";".join(comp.get("source_ids") or []),
                "profile_id": cell_id,
            })
    return rows


def feedstock_combined(alloc: list[dict[str, Any]], inv: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """任务书要求的 feedstock.csv：来料 + 组分存量的一体化长表（供 B、C 直接取用）。"""
    rows: list[dict[str, Any]] = []
    for a in alloc:
        rows.append({
            "item_id": f"INT-{a['chemistry']}",
            "item_type": "整包来料",
            "chemistry": a["chemistry"],
            "name": "退役动力电池整包",
            "fraction_of_basis": a["mass_share"],
            "annual_mass_t_a": a["annual_mass_t_a"],
            "is_additive_with_intake": "是",
            "source_ids": a["source_ids"],
            "note": a["note"],
        })
    for r in inv:
        rows.append({
            "item_id": f"{r['level']}-{r['component']}",
            "item_type": f"{r['level']}组分",
            "chemistry": r["chemistry"],
            "name": r["component"],
            "fraction_of_basis": r["fraction_of_basis"],
            "annual_mass_t_a": r["annual_mass_t_a"],
            "is_additive_with_intake": r["is_additive_with_pack"],
            "source_ids": r["source_ids"],
            "note": r["basis_note"],
        })
    return rows


def reference_li_assay(raw: dict[str, Any]) -> list[dict[str, Any]]:
    """粉料 Li 品位仅作参考记录：未激活、不可用于全厂 Li 核算。"""
    rows = []
    for prof in raw["composition_profiles"]:
        if "POWDER" not in prof["profile_id"]:
            continue
        for comp in prof["components"]:
            if comp["component_name"] != "Li":
                continue
            frac = float(comp["mass_fraction"])
            rows.append({
                "profile_id": prof["profile_id"],
                "chemistry": prof["chemistry"],
                "li_mass_fraction_of_powder": frac,
                "li_kg_per_t_powder_reference": frac * 1000.0,
                "reported_basis_note": prof.get("reported_basis_note"),
                "eligible_for_full_li_mfa": prof.get("eligible_for_full_li_mfa"),
                "usage_note": "参考量级，不参与全厂 Li 平衡；未确认是否为干基/元素基",
            })
    return rows


def li_balance_check(in_li_kg: float | None, out_li_kg: float | None,
                     tol: float = LI_REL_TOL) -> dict[str, Any]:
    """Li 元素守恒核验。

    规则（conventions.full_li_balance_tolerance）：
      相对误差 = |out - in| / in，必须严格小于 tol；
      in == 0 时判定 undefined_not_pass（零输入不构成守恒证明）；
      in 或 out 缺失（None）时判定 not_available，不得以 0 代入。
    """
    if in_li_kg is None or out_li_kg is None:
        return {"status": "not_available", "relative_error": None,
                "note": "输入或输出 Li 流量缺失（M02/M03/M05），不计算"}
    if in_li_kg == 0:
        return {"status": ZERO_LI_BEHAVIOR, "relative_error": None,
                "note": "输入 Li 为 0，守恒比无定义"}
    rel = abs(out_li_kg - in_li_kg) / in_li_kg
    return {"status": "pass" if rel < tol else "fail", "relative_error": rel,
            "note": f"容差严格小于 {tol}"}


def process_parameter_status(raw: dict[str, Any]) -> list[dict[str, Any]]:
    """未解决输入 + 候选参数状态清单（不填数值）。"""
    rows = []
    for u in raw["unresolved_inputs"]:
        rows.append({
            "parameter_id": u["input_id"],
            "category": "未解决输入",
            "key": u["key"],
            "value": None,
            "unit": u.get("unit"),
            "status": u.get("status"),
            "owner": u.get("owner"),
            "required_for": ";".join(u.get("required_for") or []),
            "description": u.get("description"),
        })
    for c in raw["candidate_process_parameters"]:
        rows.append({
            "parameter_id": c["parameter_id"],
            "category": "候选工艺参数(未启用)",
            "key": c["name"],
            "value": None,
            "unit": f"{c.get('numerator_unit')}/{c.get('denominator_unit')}",
            "status": "inactive_candidate",
            "owner": "A；组内统一",
            "required_for": "；".join(c.get("adoption_status") or []) or "待选定",
            "description": c.get("limitation"),
        })
    return rows


def module_readiness(raw: dict[str, Any]) -> list[dict[str, Any]]:
    gates = {g["module"]: g for g in raw["calculation_gates"]}
    rows = []
    for module, g in gates.items():
        rows.append({
            "module": module,
            "ready": g.get("ready"),
            "blocking_input_ids": ";".join(g.get("blocking_input_ids") or []),
            "depends_on": ";".join(g.get("depends_on_modules") or []),
            "allowed_work": g.get("allowed_work"),
        })
    return rows


def missing_input_report(raw: dict[str, Any]) -> list[dict[str, Any]]:
    gates = raw["calculation_gates"]
    usage: dict[str, list[str]] = {}
    for g in gates:
        for i in g.get("blocking_input_ids") or []:
            usage.setdefault(i, []).append(g["module"])
    rows = []
    for u in raw["unresolved_inputs"]:
        rows.append({
            "input_id": u["input_id"],
            "key": u["key"],
            "unit": u.get("unit"),
            "owner": u.get("owner"),
            "status": u.get("status"),
            "blocks_modules": ";".join(usage.get(u["input_id"], [])) or "(未阻塞任何模块)",
            "description": u.get("description"),
        })
    return rows


def print_stage_interface(blocking: set[str]) -> None:
    print("\n[5] 湿法/直接再生物质流接口（阻断未解除 → 不产出数值）")
    for stage_id, name, inflow, outflow, blockers in STAGE_DEFINITION:
        state = "待解锁" if set(blockers) & blocking else "—"
        print(f"    {stage_id} {name:<12} 入:{inflow}")
        print(f"       {'':12} 出:{outflow}  阻断:{','.join(blockers)}  状态:{state}")
    print("    说明：以上 5 段物质流的 Li 分配系数来自 M02/M03/M05，当前为 null；")
    print("          在 M01–M05 全部解除前，本模块只返回阻断清单，不返回任何 kg 级数值。")


def main() -> int:
    print("=" * 78)
    print("lecture12 案例三 · 成员 A 中期建模（数据校验 + 来料分配 + 组分存量 + Li 接口）")
    print("=" * 78)
    raw = load_handoff()
    print(f"交接包：{HANDOFF_JSON.relative_to(WORKDIR)}")
    print(f"数据性质：{raw['dataset']['dataset_id']} / schema {raw['dataset']['schema_version']} / "
          f"coding_ready={raw['dataset']['coding_ready']} / full_process_model_ready={raw['dataset']['full_process_model_ready']}\n")

    checks = validate_dataset(raw)
    print_checks(checks)
    write_csv("validation_checks.csv",
              [{"check_id": c.check_id, "item": c.item, "status": c.status, "detail": c.detail} for c in checks],
              ["check_id", "item", "status", "detail"])
    if any(c.status == "FAIL" for c in checks):
        print("\n[中止] 结构校验存在 FAIL，按交接包要求停止计算。")
        return 1

    alloc = allocate_intake(raw)
    print("\n[2] 规划来料分配（received_pack_intake_allocation）")
    for row in alloc:
        print(f"    {row['chemistry']:<22} 份额 {row['mass_share']:.0%}  →  {fmt(row['annual_mass_t_a'], 1)} t/a")
    print(f"    合计 {fmt(sum(r['annual_mass_t_a'] for r in alloc), 0)} t/a（= 规划来料，未扣除梯次利用分流）")
    write_csv("feedstock_intake_allocation.csv", alloc,
              ["chemistry", "mass_share", "annual_mass_t_a", "annual_basis", "data_type", "source_ids", "note"])

    inv = component_inventory(raw, alloc)
    print("\n[3] 来料组分存量（received_component_inventory）")
    for chemistry in ("LFP", "MIXED_NMC_UNSPECIFIED"):
        pack_rows = [r for r in inv if r["chemistry"] == chemistry and r["level"] == "整包"]
        cell_rows = [r for r in inv if r["chemistry"] == chemistry and r["level"] == "电芯展开"]
        pack_total = sum(r["annual_mass_t_a"] for r in pack_rows)
        cell_total = sum(r["annual_mass_t_a"] for r in cell_rows)
        intake = next(r["annual_mass_t_a"] for r in alloc if r["chemistry"] == chemistry)
        print(f"    {chemistry}: 整包级 {len(pack_rows)} 组分，合计 {fmt(pack_total, 1)} t/a "
              f"(= 来料 {fmt(intake, 1)}，偏差 {abs(pack_total - intake):.3e} t)")
        print(f"    {'':22}电芯展开 {len(cell_rows)} 组分，合计 {fmt(cell_total, 1)} t/a")
        for r in pack_rows + cell_rows:
            print(f"      [{r['level']}] {r['component']:<12} 分数 {r['fraction_of_basis']:.5f}  "
                  f"{fmt(r['annual_mass_t_a'], 1)} t/a  {r['is_additive_with_pack']}")
    write_csv("received_component_inventory.csv", inv,
              ["chemistry", "level", "component", "fraction_of_basis", "annual_mass_t_a",
               "is_additive_with_pack", "basis_note", "source_ids", "profile_id"])
    feed = feedstock_combined(alloc, inv)
    write_csv("feedstock.csv", feed,
              ["item_id", "item_type", "chemistry", "name", "fraction_of_basis",
               "annual_mass_t_a", "is_additive_with_intake", "source_ids", "note"])
    print(f"    任务书清单：data_cohort/feedstock.csv（{len(feed)} 行 = 来料 {len(alloc)} 行 + 组分 {len(inv)} 行）")

    ref = reference_li_assay(raw)
    print("\n[4] 粉料 Li 品位（仅参考，不可用于全厂 Li 核算）")
    for r in ref:
        print(f"    {r['profile_id']:<18} Li {r['li_mass_fraction_of_powder']:.5f} "
              f"({fmt(r['li_kg_per_t_powder_reference'], 1)} kg Li/t 粉料)  "
              f"eligible_for_full_li_mfa={r['eligible_for_full_li_mfa']}")
    write_csv("reference_li_assay.csv", ref,
              ["profile_id", "chemistry", "li_mass_fraction_of_powder", "li_kg_per_t_powder_reference",
               "reported_basis_note", "eligible_for_full_li_mfa", "usage_note"])

    params = process_parameter_status(raw)
    write_csv("process_parameters.csv", params,
              ["parameter_id", "category", "key", "value", "unit", "status", "owner", "required_for", "description"])
    print(f"\n[6] 参数状态清单：未解决 {sum(1 for p in params if p['category'] == '未解决输入')} 项 + "
          f"候选未启用 {sum(1 for p in params if p['category'] != '未解决输入')} 项 → data_cohort/process_parameters.csv")

    readiness = module_readiness(raw)
    blocked = set()
    for r in readiness:
        if not r["ready"]:
            blocked |= set(filter(None, (r["blocking_input_ids"] or "").split(";")))
    write_csv("module_readiness.csv", readiness, ["module", "ready", "blocking_input_ids", "depends_on", "allowed_work"])
    print("\n[7] 模块闸门状态")
    for r in readiness:
        flag = "READY" if r["ready"] else "BLOCKED"
        print(f"    {flag:<8} {r['module']:<34} 阻断: {r['blocking_input_ids'] or '—'}")

    missing = missing_input_report(raw)
    write_csv("missing_inputs.csv", missing,
              ["input_id", "key", "unit", "owner", "status", "blocks_modules", "description"])
    print(f"\n[8] 缺失输入报告：{len(missing)} 项 → data_cohort/missing_inputs.csv")

    print_stage_interface(blocked)

    li_demo = li_balance_check(None, None)
    print(f"\n[9] Li 守恒接口自检：无输入时状态 = {li_demo['status']}（{li_demo['note']}）")
    zero_demo = li_balance_check(0.0, 5.0)
    print(f"    零输入自检：in=0 → 状态 = {zero_demo['status']}（零输入不得判为 PASS）")

    print("\n" + "=" * 78)
    print("完成：仅输出 ready 模块结果；全厂 Li 物质流（M01–M05）保持未计算。")
    print(f"CSV 输出目录：{DATA_DIR.relative_to(WORKDIR)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
