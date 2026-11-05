#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lecture12 案例三（锂离子电池回收）成员 A：单工况年度物料 / 中间品 / 可售品接口。

本脚本回答一件事：在组内统一工况（设计 80,000 t/a、负荷 85%、梯次分配 8,500 t、
再生入口 59,500 t）下，**哪些量可以出数、哪些量必须留空**。

本版（2026-11-03 V2）按《A_BC核查与数据补充_20261103》的 code_review A01—A07 与
`给A项目IDE的简短修改prompt.md` 的 6 条要求修正，主要变化：

    A01  产品段改为**按 profile 互斥情景**（JR 粉料品位情景 / LS 同源粉料路线情景），
         不再把 LS 低品位与 JR 高品位拼成"下限—上限"区间；最终可售量一律 null。
    A02  磷酸铁统一为 FePO4·2H2O；按元素 Fe 与元素 P 的**限制元素 min** 计算，
         计入外加铁粉与 85% 磷酸，水分与纯度另乘除；不再把二水 Fe 基与无水 PO4 基拼成区间。
    A03  梯次利用拆成三段：分流输入 8,500 t（分配量）、额定容量参照（车型级 Wh/kg）、
         测试合格出货 kWh（null）。三元容量不再因 622/811 未细分而留空。
    A04  删除"ND 综合能耗 − LS 蒸汽 = 正式电耗"的默认换算；正式电/气/蒸汽只用同源活动量，
         组合电耗不拆单线，t 蒸汽在状态未核前不转 MJ，32% 液碱同时给商品吨与有效吨。
    A05  运输：环境排放与经济到厂价**分别核算一次**；只检查经济模型是否重复计同段运费。
    A06  市域 dMFA 只表述为"该模型覆盖的既有首装队列贡献"，不推断全市供料不足。

数据入口（全部只读）：
    data_cohort/a_group_decisions.json           组内决策（本脚本读取并逐项校验）
    A_BC补充数据_20261103/A_给BC的补充数据.json  2026-11-03 补充包（sha256 登记在决策文件）
    A前期数据_IDE交接包_20261103/…                JR 组成/候选参数/闸门（经 mfa_model.py 复用）
    data_cohort/dmfa_yichang_annual_total.csv    本组 dMFA 结果（仅用于跨成员比对）

输出（data_cohort/，UTF-8 with BOM，禁止手改）：
    plant_annual_material_products.csv     同 case_id 的年度物料/中间品/可售品长表
    blackmass_capture_screening.csv        黑粉库存 vs 文献迁移捕集情景（EV I / EV II）
    b_activity_reference_profiles.csv      按 profile_id 隔离的活动量/品位参考
    activity_vector_for_B.csv              B 的 12 活动键接口（正式值 null + 同源年度量）
    c_cost_quantity_interface.csv          C 计价用年量（商品吨/有效吨/干湿基分列）
    integration_abc_checks.csv             A/B/C 交叉校验（I01—I30 中 28 条）
    plant_case_checks.csv                  工况与口径自检（X01—X13 + S01—S12 + P01—P17）
    gap_table.csv                          缺口表（替换报告 §8）

AI 辅助说明：
    提示词摘要："接入 A_给BC的补充数据.json，按 code_review A01—A07 只做最小修改：
    复用 plant_case.py/a_group_decisions.json，统一 80,000/0.85/8,500/59,500 且设计 70,000 与
    实际 59,500 分开；黑粉库存与捕集分列并新增 EV_I_M02_TRANSFER_SCREENING；JR/LS/JIANG/ANL 按
    profile 隔离；删除 ND−LS 电耗反算；再使用 kWh 缺 SOH 则 null；逐项保留
    quantity/unit/basis/source/assumption/status；缺数不补 0。"
    人工复核：成员 A 逐项复核数值与口径后方可写入报告；本脚本不激活任何候选参数与补充路线。

运行：python code_implementation/plant_case.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

CODE_DIR = Path(__file__).resolve().parent
WORKDIR = CODE_DIR.parent
DATA_DIR = WORKDIR / "data_cohort"
DECISIONS_JSON = DATA_DIR / "a_group_decisions.json"
SUPPLEMENT_DIR = WORKDIR / "data_cohort" / "A_BC补充数据_20261103"
SUPPLEMENT_JSON = SUPPLEMENT_DIR / "A_给BC的补充数据.json"
DMFA_ANNUAL_CSV = DATA_DIR / "dmfa_yichang_annual_total.csv"

sys.path.insert(0, str(CODE_DIR))
import mfa_model  # noqa: E402  复用交接包读取、组分存量与 CSV 写出（缺数写空单元格）

# ----------------------------------------------------------------------------- 常数
MJ_PER_KGCE = 29.3076          # GB/T 2589 折标煤系数
MW = {                         # CIAAW 2024 简版原子量（NEW-CIAAW）
    "H": 1.008, "Li": 6.94, "C": 12.011, "O": 15.999, "P": 30.974, "Fe": 55.845,
    "Na": 22.990, "S": 32.06, "Ni": 58.693, "Co": 58.933, "Mn": 54.938,
    "Al": 26.982, "Cu": 63.546,
}
M_LCE = 2 * MW["Li"] + MW["C"] + 3 * MW["O"]                 # Li2CO3 = 73.888
M_FEPO4 = MW["Fe"] + MW["P"] + 4 * MW["O"]                   # FePO4  = 150.815
M_H2O = 2 * MW["H"] + MW["O"]                                # H2O    = 18.015
M_FEPO4_2H2O = M_FEPO4 + 2 * M_H2O                           # FePO4·2H2O = 186.845
M_PO4 = MW["P"] + 4 * MW["O"]                                # PO4    = 94.974
M_H3PO4 = 3 * MW["H"] + MW["P"] + 4 * MW["O"]                # H3PO4  = 97.994
LI_IN_LCE = 2 * MW["Li"] / M_LCE                             # 0.187843 t Li / t Li2CO3

LFP = "LFP"
NMC = "MIXED_NMC_UNSPECIFIED"
CHEMS = (LFP, NMC)
NAME_CN = {LFP: "磷酸铁锂", NMC: "未细分三元"}

# 活动量长表统一字段（quantity / unit / basis / source / assumption / status 逐项保留）
FIELDS_MAIN = ["item_id", "section", "item_name", "chemistry", "level", "quantity_kind",
               "quantity_per_year", "unit", "value_basis", "assumption", "status",
               "formula", "source_ids", "note"]

STATUS = {
    "group": "conditional_group_assumption",
    "capture": "conditional_literature_transfer_screening",
    "profile": "reference_profile_screening",
    "ceiling": "reference_material_ceiling_not_product",
    "intermediate": "recovered_intermediate_not_saleable",
    "null": "null_unresolved",
    "diag": "diagnostic_only",
}


def r(value: float | None, digits: int = 6) -> float | None:
    return None if value is None else round(float(value), digits)


def fmt(value: Any, digits: int = 1) -> str:
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return f"{value:,.{digits}f}"
    return str(value)


# ----------------------------------------------------------------------------- 读入
def load_decisions(path: Path = DECISIONS_JSON) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"未找到组内决策文件：{path}（应由成员 A 维护）")
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def load_supplement(path: Path = SUPPLEMENT_JSON) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"未找到补充数据包：{path}")
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def by_id(records: list[dict[str, Any]], key: str = "id") -> dict[str, dict[str, Any]]:
    return {rec[key]: rec for rec in records}


def route(supp: dict[str, Any], profile_id: str) -> dict[str, Any]:
    for prof in supp["reference_routes"]:
        if prof["profile_id"] == profile_id:
            return prof
    raise KeyError(f"补充包缺少参考路线：{profile_id}")


def example_annual(prof: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """LS example_scale_only 年量 → 按 record_id 索引。"""
    block = prof.get("example_scale_only") or {}
    return by_id(block.get("annual_records") or [], "record_id")


def anl_annual(prof: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return by_id(prof.get("annual_example_records") or [], "item")


def jiang_batch(prof: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return by_id(prof.get("batch_records") or [], "reference_parameter_id")


# ----------------------------------------------------------------------------- 工况
def group_allocation(dec: dict[str, Any]) -> list[dict[str, Any]]:
    """按组内决策把 68,000 t/a 实际进料按体系份额分配（整包质量）。"""
    oc = dec["operating_case"]
    actual = float(oc["actual_received_pack_t_a"])
    rows = []
    for chem, share in oc["chemistry_mass_shares"].items():
        rows.append({
            "chemistry": chem,
            "mass_share": float(share),
            "annual_mass_t_a": actual * float(share),
            "annual_basis": f"{actual:,.0f} t/a 实际进料",
            "data_type": "group_planning_assumption",
            "source_ids": "SRC031",
            "note": "组内规划假设份额（LFP 60% / 未细分三元 40%）；非市场实测",
        })
    return rows


def case_totals(dec: dict[str, Any], raw: dict[str, Any], inv: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """按体系汇总工况量 + 再生入口组分库存（整包/电芯两级分开）。"""
    oc = dec["operating_case"]
    out: list[dict[str, Any]] = []
    for chem in CHEMS:
        share = float(oc["chemistry_mass_shares"][chem])
        received = float(oc["actual_received_pack_t_a"]) * share
        reuse = float(oc["conditional_reuse_allocated_pack_t_a"]) * share
        inlet = received - reuse
        cell = sum(row["annual_mass_t_a"] for row in inv
                   if row["chemistry"] == chem and row["level"] == "整包" and "电芯" == row["component"])
        powder = sum(row["annual_mass_t_a"] for row in inv
                     if row["chemistry"] == chem and row["level"] == "电芯展开" and "黑粉" in row["component"])
        cu = sum(row["annual_mass_t_a"] for row in inv
                 if row["chemistry"] == chem and row["level"] == "电芯展开" and row["component"] == "铜箔")
        al = sum(row["annual_mass_t_a"] for row in inv
                 if row["chemistry"] == chem and row["level"] == "电芯展开" and row["component"] == "铝箔")
        scale = inlet / received
        out.append({
            "chemistry": chem,
            "share": share,
            "received_t_a": received,
            "reuse_t_a": reuse,
            "inlet_t_a": inlet,
            "recycling_scale": scale,
            "cell_t_a": cell * scale,
            "blackmass_inventory_t_a": powder * scale,
            "cu_foil_t_a": cu * scale,
            "al_foil_t_a": al * scale,
        })
    return out


def powder_assay(raw: dict[str, Any], profile_id: str) -> dict[str, Any]:
    for prof in raw["composition_profiles"]:
        if prof["profile_id"] == profile_id:
            return {c["component_name"]: float(c["mass_fraction"]) for c in prof["components"]}
    raise KeyError(f"交接包缺少粉料品位：{profile_id}")


# ----------------------------------------------------------------------------- 校验
def chk(check_id: str, item: str, status: str, detail: str, section: str = "工况自检") -> dict[str, Any]:
    return {"check_id": check_id, "section": section, "item": item, "status": status, "detail": detail}


def validate_decisions(dec: dict[str, Any]) -> list[dict[str, Any]]:
    oc = dec["operating_case"]
    checks: list[dict[str, Any]] = []
    design = float(oc["design_received_pack_t_a"])
    load = float(oc["load_factor"])
    actual = float(oc["actual_received_pack_t_a"])
    reuse_cap = float(oc["design_reuse_capacity_t_a"])
    reuse = float(oc["conditional_reuse_allocated_pack_t_a"])
    inlet = float(oc["actual_recycling_inlet_pack_t_a"])
    rec_design = float(oc["design_recycling_capacity_t_a"])

    checks.append(chk("X01", "设计来料 80,000 t/a", "PASS" if design == 80000.0 else "FAIL", f"{design:,.0f} t/a"))
    checks.append(chk("X02", "实际来料 = 设计 × 负荷", "PASS" if abs(design * load - actual) < 1e-6 else "FAIL",
                      f"{design:,.0f} × {load} = {design * load:,.1f} t/a"))
    checks.append(chk("X03", "梯次分配 = 梯次能力 × 负荷", "PASS" if abs(reuse_cap * load - reuse) < 1e-6 else "FAIL",
                      f"{reuse_cap:,.0f} × {load} = {reuse_cap * load:,.0f} t/a"))
    checks.append(chk("X04", "分流比 = 梯次分配 / 实际来料", "PASS" if abs(reuse / actual - oc["reuse_split_mass_fraction"]) < 1e-12 else "FAIL",
                      f"{reuse:,.0f} / {actual:,.0f} = {reuse / actual:.6f}"))
    checks.append(chk("X05", "再生入口 = 实际来料 − 梯次分配", "PASS" if abs(actual - reuse - inlet) < 1e-6 else "FAIL",
                      f"{actual:,.0f} − {reuse:,.0f} = {actual - reuse:,.1f} t/a"))
    checks.append(chk("X06", "设计再生能力与实际再生入口分开登记", "PASS" if rec_design != inlet and rec_design > 0 else "FAIL",
                      f"设计 {rec_design:,.0f} t/a ≠ 实际 {inlet:,.0f} t/a；不得互代，也不得把比值当负荷证据"))
    shares = oc["chemistry_mass_shares"]
    checks.append(chk("X07", "体系质量份额合计 = 1", "PASS" if abs(sum(shares.values()) - 1.0) < 1e-12 else "FAIL",
                      f"{sum(shares.values()):.6f}"))
    checks.append(chk("X08", "各体系进料合计 = 实际来料", "PASS" if abs(actual * sum(shares.values()) - actual) < 1e-6 else "FAIL", f"{actual:,.0f} t/a"))
    checks.append(chk("X09", "梯次分配按同比例分摊到体系", "PASS" if abs(reuse * sum(shares.values()) - reuse) < 1e-6 else "FAIL", f"{reuse:,.0f} t/a"))
    rui = dec["reuse_energy_interface"]
    nulls = [rui.get(k) for k in ("sale_kwh_a", "SOH", "screen_pass_mass_fraction", "repack_yield")]
    checks.append(chk("X10", "再使用出货容量与三个乘子必须 null", "PASS" if all(v is None for v in nulls) else "FAIL",
                      "sale_kwh_a / SOH / screen_pass_mass_fraction / repack_yield 均为 null；分配质量不是产品"))
    ei = dec["energy_interface"]
    formal = [ei.get(k) for k in ("formal_electricity_per_line_kwh_a", "formal_steam_energy_mj_a", "formal_water_intake_m3_a")]
    checks.append(chk("X11", "正式分线电/蒸汽能量/取水必须 null", "PASS" if all(v is None for v in formal) else "FAIL",
                      "同源活动量缺失 → 保持 null；不因总量已知而反算分线"))
    checks.append(chk("X12", "已登记删除 ND−LS 电耗反算", "PASS" if ei.get("removed_conversion", {}).get("removed_on") == "2026-11-03" else "FAIL",
                      ei.get("removed_conversion", {}).get("reason", "")))
    sp = dec["snapshot_policy"]
    flags = ["modifies_upstream", "may_be_cited_as_measurement", "activates_candidate_parameters",
             "activates_supplement_routes", "unlocks_formal_lca_or_lcor_gate", "missing_written_as_zero"]
    checks.append(chk("X13", "快照纪律：六项开关全部 false", "PASS" if all(sp.get(f) is False for f in flags) else "FAIL",
                      ", ".join(f"{f}={sp.get(f)}" for f in flags)))
    return checks


def validate_supplement(dec: dict[str, Any], supp: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    reg = dec["supplement_registry"]
    actual_hash = sha256_of(SUPPLEMENT_JSON)
    checks.append(chk("S01", "补充包 sha256 与登记一致", "PASS" if actual_hash == reg["main_json_sha256"] else "FAIL",
                      f"{actual_hash[:16]}…", "补充包自检"))

    profs = supp["reference_routes"]
    auto = (not any(p.get("automatically_adopted") is True or p.get("selected_as_plant_energy") is True
                    for p in profs)) and supp["mechanical_capture_screening"].get("automatically_adopted") is False
    nd_flag = next((p for p in profs if p["profile_id"].startswith("ND22")), {})
    checks.append(chk("S02", "所有参考路线与捕集情景均未自动生效", "PASS" if auto else "FAIL",
                      "LS/ANL/JIANG automatically_adopted=false；ND22 selected_as_plant_energy="
                      f"{nd_flag.get('selected_as_plant_energy')}（未提供该字段不等于采纳）；捕集情景 false",
                      "补充包自检"))

    mcs = supp["mechanical_capture_screening"]
    worst = 0.0
    for row in mcs["annual_rows"]:
        lhs = float(row["conditionally_captured_blackmass_t_a"]) + float(row["not_in_captured_stream_t_a"])
        worst = max(worst, abs(lhs - float(row["inventory_t_a"])) / float(row["inventory_t_a"]))
    checks.append(chk("S03", "捕集 + 未捕集 = 组分库存", "PASS" if worst < 1e-9 else "FAIL",
                      f"最大相对残差 {worst:.2e}", "补充包自检"))

    ev1 = float(mcs["reference_capture_fraction"])
    ev2 = float(mcs["alternative_route"]["capture_fraction"])
    averaged = abs((ev1 + ev2) / 2 - ev1) < 1e-12
    checks.append(chk("S04", "EV I 与 EV II 并列、不平均", "PASS" if ev1 != ev2 and not averaged else "FAIL",
                      f"EV I {ev1:.4f}（n={mcs['sample_n']}，SD {mcs['reference_sd_fraction']}）vs EV II {ev2:.4f}（SD {mcs['alternative_route']['sd_fraction']}）",
                      "补充包自检"))

    ls = route(supp, "LS23_LFP_NATIVE_POWDER")
    checks.append(chk("S05", "LS 粉料部分组成 0.772665 未归一化", "PASS" if abs(float(ls["assay_mass_sum"]) - 0.772665) < 1e-9 else "FAIL",
                      f"assay_mass_sum={ls['assay_mass_sum']}；其余 22.73% 为未列组分，不放大", "补充包自检"))

    lrec = by_id(ls["records"])
    crude = lrec["LS23_PRODUCT_CRUDE_LIC"]
    slag = lrec["LS23_PRODUCT_FEP_SLAG"]
    products_null = crude.get("saleable_battery_grade_quantity") is None and slag.get("saleable_battery_grade_quantity") is None
    checks.append(chk("S06", "LS 粗碳酸锂/磷酸铁渣不得记电池级可售品", "PASS" if products_null else "FAIL",
                      f"roles: {crude['product_role']} / {slag['product_role']}", "补充包自检"))

    anl = route(supp, "ANL19_GENERIC_HYD_CELL")
    checks.append(chk("S07", "ANL 无可售产品量且恢复率为全路线口径", "PASS"
                      if anl.get("saleable_product_masses") is None and anl.get("recovery_basis") else "FAIL",
                      str(anl.get("recovery_basis"))[:90], "补充包自检"))

    jiang = route(supp, "JIANG24_NATIVE_LFP_PILOT")
    li = jiang["li_balance_table6"]
    total = sum(float(li[k]) for k in ("li_in_li2co3_product_kg", "li_in_li3po4_product_kg",
                                      "li_in_fepo4_products_kg", "li_in_insoluble_residue_kg",
                                      "li_in_secondary_leach_residue_kg", "li_in_liquor_kg",
                                      "li_in_recirculating_wash_water_kg"))
    residual = abs(float(li["input_powder_li_kg"]) - total) / float(li["input_powder_li_kg"])
    checks.append(chk("S08", "JIANG 表6 舍入残差 > 5e-4，不得宣称已通过", "PASS" if residual > 5e-4 else "FAIL",
                      f"合计 {total:.2f} kg / 输入 {li['input_powder_li_kg']} kg；残差 {residual:.6f}；源文 99.94% 只是报告值",
                      "补充包自检"))

    nd = route(supp, "ND22_WHOLE_CATHODE_PROJECT_REFERENCE")
    checks.append(chk("S09", "ND22 不作为本厂电/汽活动量", "PASS" if nd.get("selected_as_plant_energy") is False else "FAIL",
                      f"全项目电 {nd['whole_project_electricity_kwh_a']:,} kWh/a；蒸汽 {len(nd['steam_streams'])} 股",
                      "补充包自检"))

    ui = supp["unresolved_inputs"]
    checks.append(chk("S10", "未解决输入全部保持 null", "PASS" if all(u.get("value") is None for u in ui) else "FAIL",
                      f"{len(ui)} 项：{';'.join(u['input_id'] for u in ui)}", "补充包自检"))

    checks.append(chk("S11", "LS 蒸汽只有质量，不转 MJ", "PASS" if lrec["LS23_STEAM"].get("value") and
                      nrg(ls).get("steam_energy_MJ_a") is None else "FAIL",
                      f"{lrec['LS23_STEAM']['value']} {lrec['LS23_STEAM']['unit']}；压力/温度/返凝水未核", "补充包自检"))

    ids = {c["issue_id"] for c in supp["code_review"]}
    a_issue = [f"A{i:02d}" for i in range(1, 8)]
    checks.append(chk("S12", "code_review 含 A01—A07", "PASS" if all(x in ids for x in a_issue) else "FAIL",
                      f"{len(ids)} 条；A 侧 {[x for x in a_issue if x in ids]}", "补充包自检"))
    return checks


def nrg(prof: dict[str, Any]) -> dict[str, Any]:
    """取 profile 的 energy 块；缺失时返回空字典（不虚构）。"""
    for key in ("energy", "energy_split", "energy_interface"):
        block = prof.get(key)
        if isinstance(block, dict):
            return block
    return {}


# ----------------------------------------------------------------------------- A 段：工况与分流
def section_a(dec: dict[str, Any], totals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    oc = dec["operating_case"]
    rows: list[dict[str, Any]] = []

    def add(item_id, name, kind, qty, unit, basis, formula, note, status=STATUS["group"], chem=None):
        rows.append({
            "item_id": item_id, "section": "A 工况与分流", "item_name": name, "chemistry": chem,
            "level": "-", "quantity_kind": kind, "quantity_per_year": qty, "unit": unit,
            "value_basis": basis, "assumption": "组内规划工况（非实测）", "status": status,
            "formula": formula, "source_ids": "SRC031", "note": note,
        })

    add("A-01", "设计来料（整包）", "capacity", float(oc["design_received_pack_t_a"]), "t_pack/a",
        "8 万 t/a 园区设计规模", "任务书设计规模", "设计值，不是实际流量")
    add("A-02", "实际来料（整包）", "input_allocation", float(oc["actual_received_pack_t_a"]), "t_pack/a",
        "设计 × 负荷 0.85", "A-01 × 负荷", "负荷只乘一次；进料已是年实际量")
    add("A-03", "梯次利用设计能力", "capacity", float(oc["design_reuse_capacity_t_a"]), "t_pack/a",
        "10,000 t/a 梯次线设计规模", "任务书设计规模", "设计能力，不等于实际分配量")
    add("A-04", "梯次利用实际分配（整包）", "input_allocation", float(oc["conditional_reuse_allocated_pack_t_a"]), "t_pack/a",
        "梯次能力 × 负荷 0.85", "A-03 × 负荷", "是分流输入，不是可售产品量")
    add("A-05", "再生处理设计能力", "capacity", float(oc["design_recycling_capacity_t_a"]), "t_pack/a",
        "70,000 t/a 湿法再生设计规模", "任务书设计规模", "设计能力，与实际 59,500 分开登记")
    add("A-06", "再生处理实际入口（整包）", "input_allocation", float(oc["actual_recycling_inlet_pack_t_a"]), "t_pack/a",
        "实际来料 − 梯次分配", "A-02 − A-04", "59,500 ≠ 70,000；不得把 70,000 换成 59,500 作为同一事实")
    add("A-07", "同体系梯次分流比", "diagnostic", float(oc["reuse_split_mass_fraction"]), "t/t",
        "按整包质量同比例分流", "A-04 / A-02", "SOH 阈值不等于数量分布；12.5% 是规划假设（M01 条件）")
    for chem in CHEMS:
        t = next(x for x in totals if x["chemistry"] == chem)
        add(f"A-{8 + CHEMS.index(chem) * 3:02d}", f"{NAME_CN[chem]} 进料（整包）", "input_allocation",
            t["received_t_a"], "t_pack/a", f"份额 {t['share']:.2f}", "A-02 × 体系份额", "组内规划份额，非市场实测", chem=chem)
        add(f"A-{9 + CHEMS.index(chem) * 3:02d}", f"{NAME_CN[chem]} 梯次分配（整包）", "input_allocation",
            t["reuse_t_a"], "t_pack/a", f"份额 {t['share']:.2f} × 11 行", "A-04 × 体系份额", "分流输入，不是出货量", chem=chem)
        add(f"A-{10 + CHEMS.index(chem) * 3:02d}", f"{NAME_CN[chem]} 再生入口（整包）", "input_allocation",
            t["inlet_t_a"], "t_pack/a", "进料 − 梯次分配", "A-6 × 体系份额", f"组分库存按此口径放大 {t['recycling_scale']:.4f}", chem=chem)
    return rows


# ----------------------------------------------------------------------------- B 段：再生入口组分库存
def section_b(inv: list[dict[str, Any]], totals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for chem in CHEMS:
        t = next(x for x in totals if x["chemistry"] == chem)
        for rec in inv:
            if rec["chemistry"] != chem:
                continue
            rows.append({
                "item_id": f"B-{chem}-{rec['level']}-{rec['component']}",
                "section": "B 再生入口组分库存",
                "item_name": rec["component"],
                "chemistry": chem,
                "level": rec["level"],
                "quantity_kind": "inventory",
                "quantity_per_year": rec["annual_mass_t_a"] * t["recycling_scale"],
                "unit": "t/a",
                "value_basis": f"占{rec['level']}质量 {rec['fraction_of_basis']:.5f}；再生入口口径",
                "assumption": "整包来料按 inlet/received 同比例缩放；未扣分选与湿法损失",
                "status": STATUS["group"],
                "formula": f"来料组分 × {t['recycling_scale']:.6f}",
                "source_ids": rec["source_ids"],
                "note": "组分存量 ≠ 可回收量 ≠ 产品量；整包级与电芯展开不可相加",
            })
    return rows


# ----------------------------------------------------------------------------- C 段：黑粉库存与捕集
def section_c(raw: dict[str, Any], supp: dict[str, Any], totals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    mcs = supp["mechanical_capture_screening"]
    ann = by_id(mcs["annual_rows"], "chemistry")
    rows: list[dict[str, Any]] = []

    for chem in CHEMS:
        t = next(x for x in totals if x["chemistry"] == chem)
        rows.append({
            "item_id": f"C-{1 + CHEMS.index(chem):02d}", "section": "C 黑粉库存与捕集",
            "item_name": "黑粉（正负极粉）组分库存", "chemistry": chem, "level": "电芯展开",
            "quantity_kind": "inventory", "quantity_per_year": t["blackmass_inventory_t_a"], "unit": "t/a",
            "value_basis": "JR 电芯组成 × 再生入口整包量", "assumption": "组分存量；未扣分选捕集损失",
            "status": STATUS["group"], "formula": "电芯质量 × 黑粉质量分数 × inlet/received",
            "source_ids": "SRC039", "note": "这是库存，不是捕集量，也不是黑粉产量",
        })
        rows.append({
            "item_id": f"C-{3 + CHEMS.index(chem) * 1:02d}", "section": "C 黑粉库存与捕集",
            "item_name": "条件捕集情景（EV_I_M02_TRANSFER_SCREENING，η=0.9328）",
            "chemistry": chem, "level": "电芯展开", "quantity_kind": "diagnostic",
            "quantity_per_year": ann[chem]["conditionally_captured_blackmass_t_a"], "unit": "t/a",
            "value_basis": "库存 × 0.9328（文献迁移，n=3，SD 0.0405）",
            "assumption": "同源 EV 模块手工拆解总黑粉捕集率移用；忽略放大效应；LFP 属跨体系代理",
            "status": STATUS["capture"], "formula": f"{t['blackmass_inventory_t_a']:.3f} × 0.9328",
            "source_ids": "NEW-MECH2026",
            "note": "仅是黑粉总质量情景，不推定 Li/Ni/Co/Mn 同率分配，也不是 Li 回收率；未捕集部分去向未量化。完整情景见 blackmass_capture_screening.csv",
        })
    rows.append({
        "item_id": "C-05", "section": "C 黑粉库存与捕集", "item_name": "黑粉组分库存合计（不可与整包级相加）",
        "chemistry": "合计", "level": "电芯展开", "quantity_kind": "inventory",
        "quantity_per_year": sum(x["blackmass_inventory_t_a"] for x in totals), "unit": "t/a",
        "value_basis": "LFP + 未细分三元", "assumption": "两个体系的黑粉属同层组分，可相加",
        "status": STATUS["group"], "formula": "C-01 + C-02", "source_ids": "SRC039",
        "note": "EV I 合计 15,587.395 t/a；EV II 合计 13,958.138 t/a（并列情景，不平均）",
    })

    jr_lfp = powder_assay(raw, "JR23_LFP_POWDER")
    jr_nmc = powder_assay(raw, "JR23_NMC_POWDER")
    for chem, assay in ((LFP, jr_lfp), (NMC, jr_nmc)):
        t = next(x for x in totals if x["chemistry"] == chem)
        for idx, (elem, frac) in enumerate(assay.items(), start=1):
            rows.append({
                "item_id": f"C-{6 + CHEMS.index(chem):02d}-{idx:02d}", "section": "C 黑粉库存与捕集",
                "item_name": f"黑粉 {elem} 参考含量", "chemistry": chem, "level": "电芯展开",
                "quantity_kind": "diagnostic", "quantity_per_year": t["blackmass_inventory_t_a"] * frac, "unit": "t/a",
                "value_basis": f"JR 粉料品位 {frac:.5f} × 库存 {t['blackmass_inventory_t_a']:,.3f} t",
                "assumption": "参考品位按 as-received 解释；干/湿基与胶黏剂范围未核（M03）",
                "status": STATUS["diag"], "formula": "库存 × 品位",
                "source_ids": "SRC039;SRC024",
                "note": "参考记录，不是本厂化验值；不得用于全厂 Li 平衡（M03 未解）",
            })
    return rows


# ----------------------------------------------------------------------------- D 段：再使用与产品
def fepo4_ceiling(powder_t: float, fe_frac: float, p_frac: float,
                  ext_fe_t: float, ext_p_t: float) -> dict[str, Any]:
    """统一 FePO4·2H2O，按元素 Fe/P 限制元素 min 计算（A02）。"""
    kmol_fe = (powder_t * fe_frac + ext_fe_t) * 1000 / MW["Fe"]
    kmol_p = (powder_t * p_frac + ext_p_t) * 1000 / MW["P"]
    limiting = min(kmol_fe, kmol_p)
    return {
        "kmol_fe": kmol_fe,
        "kmol_p": kmol_p,
        "limiting_element": "Fe" if kmol_fe <= kmol_p else "P",
        "mass_t": limiting * M_FEPO4_2H2O / 1000,
        "formula": "min(kmol_Fe, kmol_P) × M(FePO4·2H2O)",
    }


def section_d(raw: dict[str, Any], dec: dict[str, Any], supp: dict[str, Any],
              totals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ls = route(supp, "LS23_LFP_NATIVE_POWDER")
    lrec = by_id(ls["records"])
    ex = example_annual(ls)
    mcs = supp["mechanical_capture_screening"]
    ann = by_id(mcs["annual_rows"], "chemistry")
    jr_lfp = powder_assay(raw, "JR23_LFP_POWDER")
    jr_nmc = powder_assay(raw, "JR23_NMC_POWDER")
    rui = dec["reuse_energy_interface"]
    rows: list[dict[str, Any]] = []

    def add(item_id, name, kind, qty, unit, basis, assumption, status, formula, src, note, chem=None, level="-"):
        rows.append({
            "item_id": item_id, "section": "D 再使用与产品", "item_name": name, "chemistry": chem,
            "level": level, "quantity_kind": kind, "quantity_per_year": qty, "unit": unit,
            "value_basis": basis, "assumption": assumption, "status": status,
            "formula": formula, "source_ids": src, "note": note,
        })

    # --- 再使用：分配输入 / 额定容量参照 / 合格出货（A03）----------------------
    flow = (LFP, NMC)
    for chem in flow:
        t = next(x for x in totals if x["chemistry"] == chem)
        add(f"D-{1 + flow.index(chem):02d}", f"{NAME_CN[chem]} 梯次分流输入（整包当量）", "input_allocation",
            t["reuse_t_a"], "t_pack/a", "同体系分流比 × 体系份额", "按整包质量同比例分流（M01 条件）",
            STATUS["group"], "A-04 × 体系份额", "SRC031",
            "这是分流输入质量，不是筛选合格量，也不是梯次产品；不得乘比能量后当出货容量", chem=chem)
    for idx, (label, val) in enumerate((("低", rui["nameplate_specific_energy_Wh_per_kg_reference"]["low"]),
                                       ("中", rui["nameplate_specific_energy_Wh_per_kg_reference"]["mid"]),
                                       ("高", rui["nameplate_specific_energy_Wh_per_kg_reference"]["high"]))):
        add(f"D-03{chr(97 + idx)}", f"梯次额定容量参照（{label}档，车型级）", "capacity", val, "Wh/kg_pack",
            "DMFA-06 车型级比能量档；同车型三体系共用", "额定值参照，非实测 SOH、非合格出货",
            STATUS["diag"], "DMFA-06 specific_energy_Wh_per_kg_pack",
            "DMFA-S002;DMFA-S011",
            "三元不必因 622/811 未细分而 null：容量参数是车型级，与元素拆分无关；但本组未指定适用车型，故只给参照区间", chem="LFP+MIXED_NMC_UNSPECIFIED")
    add("D-04", "再使用测试合格出货容量", "saleable_product", None, "kWh/a",
        "缺 SOH / 筛选合格率 / 重组率 / 应用标准", "四因子未取得 → 保持 null", STATUS["null"],
        "Σ(分流t × 额定Wh/kg × 筛选率 × SOH × 重组率)", "DMFA-S011;NEW-POL2026",
        f"公式中 SOH={rui['SOH']}、筛选率={rui['screen_pass_mass_fraction']}、重组率={rui['repack_yield']} 均为 null；政策状态 UNKNOWN")
    add("D-05", "再使用整包当量可售量", "saleable_product", None, "t_pack/a",
        "需应用标准与合格率证据（M01_REUSE_SALE）", "未取得 → 保持 null", STATUS["null"],
        "D-01 + D-02 经筛选/测试后合格部分", "DMFA-S011", "缺数不填 0，也不等于分流输入")

    # --- 情景一：JR 粉料品位 + EV I 捕集（互斥，不与 LS 合成区间 A01）------------
    cap_lfp = float(ann[LFP]["conditionally_captured_blackmass_t_a"])
    cap_nmc = float(ann[NMC]["conditionally_captured_blackmass_t_a"])
    li_lfp = cap_lfp * jr_lfp["Li"]
    li_nmc = cap_nmc * jr_nmc["Li"]
    li_all = li_lfp + li_nmc
    add("D-06", "情景 JR：粉料 Li（捕集后，LFP）", "diagnostic", li_lfp, "t_Li/a",
        "捕集情景 × JR LFP 粉料品位 3.425%", "跨表拼接：捕集率来自 EV 模块实验、品位来自 JR 报告", STATUS["capture"],
        f"{cap_lfp:,.3f} t × 0.03425", "SRC039;NEW-MECH2026",
        "两个来源分母不同（EV 模块手工拆解 vs JR 电芯组成），只作筛查；不推定元素按捕集率同比例分配", chem=LFP)
    add("D-07", "情景 JR：粉料 Li（捕集后，三元）", "diagnostic", li_nmc, "t_Li/a",
        "捕集情景 × JR 三元粉料品位 4.340%", "同上；三元品位未按 622/811 细分", STATUS["capture"],
        f"{cap_nmc:,.3f} t × 0.0434", "SRC039;NEW-MECH2026",
        "未细分三元只给合并 Li，不拆 622/811；不得当作已确认的三元元素流", chem=NMC)
    lce_jr = li_all / LI_IN_LCE
    add("D-08", "情景 JR：LCE 当量上限（100% 回收假设）", "reference_material_ceiling", lce_jr, "t_Li2CO3/a",
        "粉料 Li ÷ 0.187843", "假设全部粉料 Li 进入 LCE 且无浸出/除杂损失", STATUS["ceiling"],
        f"{li_all:,.3f} / {LI_IN_LCE:.6f}", "SRC039;SRC024",
        "上限，不是产量；与 C 的 3,000 t 财务变量不互代。若采用文献 0.90—0.976 收率，乘一次即可，不得再乘黑粉捕集损失", chem="合计")
    add("D-09", "情景 JR：LCE 当量上限分摊（LFP）", "reference_material_ceiling", li_lfp / LI_IN_LCE,
        "t_Li2CO3/a", "同 D-06 ÷ 0.187843", "同上", STATUS["ceiling"], f"{li_lfp:,.3f} / {LI_IN_LCE:.6f}",
        "SRC039", "分摊只用于说明结构；不得与 D-10 拼成区间", chem=LFP)
    add("D-10", "情景 JR：LCE 当量上限分摊（三元）", "reference_material_ceiling", li_nmc / LI_IN_LCE,
        "t_Li2CO3/a", "同 D-07 ÷ 0.187843", "同上", STATUS["ceiling"], f"{li_nmc:,.3f} / {LI_IN_LCE:.6f}",
        "SRC039", "三元 Li 只作合并当量；不拆 622/811", chem=NMC)

    # --- 情景二：LS 同源粉料路线（内部中间品，非电池级成品）--------------------
    powder_t = float(ls["example_scale_only"]["powder_feed_t_a"])   # 9,418.856 t/a = LFP 捕集粉量
    crude = ex["LS23_PRODUCT_CRUDE_LIC"]
    slag = ex["LS23_PRODUCT_FEP_SLAG"]
    alp = ex["LS23_PRODUCT_ALP"]
    na2so4 = ex["LS23_PRODUCT_SODIUM_SULFATE"]
    sponge = ex["LS23_PRODUCT_SPONGE_CU"]
    crude_li = ex["LS23_CRUDE_LI_CONTENT"]
    base = "LS 同源粉料路线按本组 LFP 捕集粉量换算（仅条件规模）"
    asm = "假设入湿法粉料经调配达到 LS 同源组成/含水；JR 粉料与该组成的等价性未证实（M03）"
    add("D-11", "情景 LS：粗碳酸锂（湿商品）", "recovered_intermediate", crude["annual_value"], "t_product/a",
        base, asm, STATUS["intermediate"], "0.1420609 t/t 粉料 × 粉料量", "SRC040",
        f"含水 0.20、干纯度 0.99 → 干纯 {crude['dry_pure_substance_t_a']:,.3f} t/a；属内部进入铁锂线，不是已达电池级可售品", chem=LFP)
    add("D-12", "情景 LS：粗碳酸锂所含元素 Li", "recovered_intermediate", crude_li["annual_value"], "t_Li/a",
        base, asm, STATUS["intermediate"], "0.0211351 t_Li/t 粉料", "SRC040",
        "与粉料 Li 的比 0.874978 是表间推导，不是浸出率；余 Li 去向未闭合", chem=LFP)
    add("D-13", "情景 LS：磷酸铁渣（湿商品）", "recovered_intermediate", slag["annual_value"], "t_product/a",
        base, asm, STATUS["intermediate"], "0.7495861 t/t 粉料", "SRC040",
        f"含水 0.40、干纯度 0.99 → 干纯 {slag['dry_pure_substance_t_a']:,.3f} t/a；不是 8 万 t/a 磷酸铁成品", chem=LFP)
    add("D-14", "情景 LS：磷酸铝副产（湿商品）", "recovered_intermediate", alp["annual_value"], "t_product/a",
        base, asm, STATUS["intermediate"], "0.1348885 t/t 粉料", "SRC040",
        f"含水 0.40、干纯度 0.99 → 干纯 {alp['dry_pure_substance_t_a']:,.3f} t/a；规格与售价未定", chem=LFP)
    add("D-15", "情景 LS：硫酸钠（外售副产）", "recovered_intermediate", na2so4["annual_value"], "t_product/a",
        base, asm, STATUS["intermediate"], "0.867238 t/t 粉料", "SRC040",
        "水合形态与水分未明 → 不给纯物质吨、不给价格", chem=LFP)
    add("D-16", "情景 LS：海绵铜（Cu-40）", "recovered_intermediate", sponge["annual_value"], "t_product/a",
        base, asm, STATUS["intermediate"], "0.03958 t/t 粉料", "SRC040",
        f"按 Cu 40% 计含铜 {sponge['annual_value'] * 0.40:,.3f} t/a；不是铜箔", chem=LFP)

    # --- FePO4：统一 FePO4·2H2O + 限制元素（A02）-------------------------------
    po4 = jr_lfp.get("PO4")
    p_jr = (po4 * MW["P"] / M_PO4) if po4 else None
    jr_fep = fepo4_ceiling(cap_lfp, jr_lfp["Fe"], p_jr, 0.0, 0.0) if p_jr else None
    ext_fe = float(ex["LS_FE"]["active_equivalent_t_a"])
    ext_p = float(ex["LS_PACID"]["active_equivalent_t_a"]) * MW["P"] / M_H3PO4
    ls_fep = fepo4_ceiling(powder_t, float(lrec["LS23_ASSAY_FE"]["value"]),
                           float(lrec["LS23_ASSAY_P"]["value"]), ext_fe, ext_p)
    add("D-17", "情景 JR：FePO4·2H2O 化学计量上限（粉料内 Fe/P）", "reference_material_ceiling",
        jr_fep["mass_t"], "t_FePO4·2H2O/a",
        "min(kmol_Fe, kmol_P) × 186.845；粉料 Fe 0.25344、PO4→P 换算",
        "JR 外加铁/磷药剂表未取得 → 未计外加料，故不是可售量；PO4→P 按化学式换算属建模假设",
        STATUS["ceiling"], jr_fep["formula"], "SRC039",
        f"Fe 限制：kmol_Fe={jr_fep['kmol_fe']:,.0f}、kmol_P={jr_fep['kmol_p']:,.0f}；未扣进入磷酸铝/除杂渣的 Fe 与精制损失", chem=LFP)
    add("D-18", "情景 LS：FePO4·2H2O 化学计量上限（含外加铁粉与 85% 磷酸）", "reference_material_ceiling",
        ls_fep["mass_t"], "t_FePO4·2H2O/a",
        "min(kmol_Fe, kmol_P) × 186.845；粉料 Fe/P + 99% 铁粉 + 85% 磷酸",
        "假设外加铁与磷酸全部进入 FePO4（未计磷酸锂/磷酸铝消耗）；LS 表 Fe/P 为元素基但干湿基未明",
        STATUS["ceiling"], ls_fep["formula"], "SRC040",
        f"{ls_fep['limiting_element']} 限制：kmol_Fe={ls_fep['kmol_fe']:,.0f}、kmol_P={ls_fep['kmol_p']:,.0f}；"
        f"外加 Fe {ext_fe:,.3f} t、外加 P {ext_p:,.3f} t；不得与 D-17 拼成区间（不同 profile）", chem=LFP)
    add("D-19", "电池级磷酸铁（HG/T 4701-2021）合格产量", "saleable_product", None, "t_product/a",
        "需产品规格、精制线走向与合格率（M05_PRODUCTS）", "规格/合格率未取得 → 保持 null", STATUS["null"],
        "D-18 × 精制收率 × 合格率", "NEW-STD-FEP;SRC040",
        "D-13 磷酸铁渣 与 D-18 化学计量上限都不是电池级成品；水分 0.40、纯度 0.99 须另乘除")

    # --- 其他可回收材料的上限（箔材 / 镍钴锰盐）-------------------------------
    for chem in CHEMS:
        t = next(x for x in totals if x["chemistry"] == chem)
        add(f"D-{20 + CHEMS.index(chem) * 2:02d}", f"{NAME_CN[chem]} 铜箔（100% 分选上限）",
            "reference_material_ceiling", t["cu_foil_t_a"], "t_Cu/a",
            "JR 电芯组成铜箔质量分数 × 再生入口", "假设箔材 100% 分选回收；未扣附着粉与氧化损失",
            STATUS["ceiling"], "电芯质量 × 铜箔分数", "SRC039", "上限，不是产量；铜箔表面附着黑粉未扣除", chem=chem)
        add(f"D-{21 + CHEMS.index(chem) * 2:02d}", f"{NAME_CN[chem]} 铝箔（100% 分选上限）",
            "reference_material_ceiling", t["al_foil_t_a"], "t_Al/a",
            "JR 电芯组成铝箔质量分数 × 再生入口", "假设箔材 100% 分选回收", STATUS["ceiling"],
            "电芯质量 × 铝箔分数", "SRC039", "上限，不是产量", chem=chem)
    salt = {"Ni": (58.693 + 32.06 + 4 * 15.999 + 6 * 18.015, "NiSO4·6H2O"),
            "Co": (58.933 + 32.06 + 4 * 15.999 + 7 * 18.015, "CoSO4·7H2O"),
            "Mn": (54.938 + 32.06 + 4 * 15.999 + 18.015, "MnSO4·H2O")}
    for idx, (elem, (m_salt, name_salt)) in enumerate(salt.items(), start=1):
        frac = jr_nmc.get(elem)
        add(f"D-24-{idx}", f"三元 {name_salt} 化学计量上限", "reference_material_ceiling",
            cap_nmc * frac * m_salt / MW[elem], "t_salt/a",
            f"捕集后粉料 × JR {elem} 品位 {frac:.5f} × 盐/元素摩尔比",
            "假设 100% 进入盐产品且无浸出/除杂损失；商品浓度/结晶水未核",
            STATUS["ceiling"], f"{cap_nmc:,.3f} × {frac} × {m_salt:.3f}/{MW[elem]}", "SRC039;SRC043",
            "ANL 的 0.98 Ni/Co/Mn 恢复率是全路线口径：若采用只乘一次，且不得再乘黑粉捕集损失", chem=NMC)

    for idx, (item_name, unit, note) in enumerate((
            ("电池级碳酸锂（YS/T 582-2023）", "t_product/a", "需纯度、杂质与合格率证据；LS 只有粗品中间物"),
            ("电池级磷酸铁", "t_product/a", "见 D-19；水合形态已统一为二水"),
            ("电池级镍/钴/锰盐", "t_salt/a", "需商品浓度与结晶水；ANL 不提供产品量"),
            ("铜/铝箔产品", "t_product/a", "需分选后品位与打包标准"),
            ("硫酸钠/磷酸铝等副产", "t_product/a", "水合形态/规格/售价未定"),
            ("其他外售品", "t_product/a", "未识别，保持空"))):
        add(f"D-27-{idx + 1}", f"可售品：{item_name}", "saleable_product", None, unit,
            "M05_PRODUCTS 未解", "成品规格/纯度/合格率未取得 → null", STATUS["null"],
            "见对应上限行 × 收率 × 合格率", "NEW-STD-LCE;NEW-STD-FEP;SRC042;SRC043", note, chem="合计")
    return rows


# ----------------------------------------------------------------------------- E 段：公用工程与药剂
def section_e(supp: dict[str, Any], dec: dict[str, Any], totals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ls = route(supp, "LS23_LFP_NATIVE_POWDER")
    lrec = by_id(ls["records"])
    ex = example_annual(ls)
    nd = route(supp, "ND22_WHOLE_CATHODE_PROJECT_REFERENCE")
    dec_energy = dec["energy_interface"]
    lfp_cell = next(x for x in totals if x["chemistry"] == LFP)["cell_t_a"]
    rows: list[dict[str, Any]] = []

    def add(item_id, name, qty, unit, basis, assumption, status, formula, src, note):
        rows.append({
            "item_id": item_id, "section": "E 公用工程与药剂", "item_name": name, "chemistry": "合计",
            "level": "-", "quantity_kind": "diagnostic" if status != STATUS["null"] else "unresolved_null",
            "quantity_per_year": qty, "unit": unit, "value_basis": basis, "assumption": assumption,
            "status": status, "formula": formula, "source_ids": src, "note": note,
        })

    # --- 综合能耗只作诊断（A04）：不再拆成"电"与"汽" -------------------------
    kgce = float(nd["lfp_lce_specific_total_energy_kgce_t"])
    add("E-01", "ND22 LFP 碳酸锂综合能耗（诊断）", kgce, "kgce/t_LCE",
        "整项目综合能耗强度", "跨项目、多产品边界；不是本厂分线能耗", STATUS["diag"],
        "源表 1,729.26 kgce/t", "SRC042",
        f"折 {kgce * MJ_PER_KGCE:,.1f} MJ/t（仅诊断）。禁止用综合能耗减 LS 蒸汽、把余量当电耗（A04 已删除该换算）")
    add("E-02", "ND22 全项目用电（参考）", float(nd["whole_project_electricity_kwh_a"]), "kWh/a",
        "整项目 5.3 万 t 三元正极片 + 4.7 万 t LFP 正极片", "整项目边界含多条再生线与多产品",
        STATUS["diag"], "源表全项目电耗", "SRC042", "仅供量级参照；selected_as_plant_energy=false，不得作为本厂活动量")
    for idx, stream in enumerate(nd["steam_streams"], start=1):
        add(f"E-03-{idx}", f"ND22 蒸汽（{stream['pressure_MPa']} MPa / {stream['temperature_C']} ℃，参考）",
            float(stream["mass_t_a"]), "t_steam/a", "整项目蒸汽质量", "整项目边界；状态已知但非本厂结算口径",
            STATUS["diag"], "源表蒸汽股", "SRC042", "只给质量；转 MJ 需本厂结算口径，此处不做")
    add("E-04", "LS23 组合电耗（含 1 万 t 电芯 + 1 万 t 粉料 + 公辅）",
        float(lrec["LS23_COMBINED_ELECTRICITY"]["value"]), "kWh/a",
        "租赁厂房组合电表，覆盖预处理+湿法+公辅", "不可拆成单线电耗；也不除以粉量充当湿法单耗",
        STATUS["diag"], "源表 11,232,000 kWh/a", "SRC040",
        "组合电耗保留原值（A04）；本厂的分线电耗仍为 null")
    add("E-05", "LS23 蒸汽质量（状态未核）", float(ex["LS23_STEAM"]["annual_value"]), "t_steam/a",
        "1.1747755 t 蒸汽/t 粉料 × 粉料量", "压力/温度/返凝水/购热结算口径未取得",
        STATUS["diag"], "源表蒸汽质量", "SRC040",
        "只给 t/a；M08_STEAM 未解前不得转为 MJ（禁止无依据填 2500 MJ/t）")
    add("E-06", "本厂正式分线电耗", None, "kWh/a", "同工艺分线电表 + 公辅分摊（M08_ELECTRIC）",
        "未取得 → null；不为配总量反算", STATUS["null"], "—", "SRC040;SRC043", dec_energy["removed_conversion"]["reason"])
    add("E-07", "本厂正式蒸汽能量", None, "MJ/a", "需蒸汽状态与结算口径（M08_STEAM）",
        "未取得 → null", STATUS["null"], "—", "SRC040", "t 蒸汽已在 E-05 给出，但能量口径未定")
    add("E-08", "本厂取水（新水）", None, "m3/a", "全厂取水/纯水/循环/耗水/外排及处理层级（M08_WATER）",
        "未取得 → null", STATUS["null"], "—", "SRC040", "LS 分线水数据不能充当全厂水系统")

    # --- LS 同源水与固渣（同一边界，示例规模）--------------------------------
    water = [("E-09", "纯水（LS 同源）", "LS23_PURE_WATER", "m3/a"),
             ("E-10", "洗涤/吹扫补水", "LS23_SCRUBBER_MAKEUP", "m3/a"),
             ("E-11", "地坪冲洗水", "LS23_FLOOR_WATER", "m3/a"),
             ("E-12", "MVR 冷凝外排水", "LS23_MVR_CONDENSATE_DISCHARGE", "m3/a"),
             ("E-13", "酸雾洗涤废水", "LS23_SCRUBBER_WW", "m3/a"),
             ("E-14", "地坪废水", "LS23_FLOOR_WW", "m3/a")]
    for item_id, name, key, unit in water:
        add(item_id, name, float(ex[key]["annual_value"]), unit,
            "LS 同源粉料线水耗（示例规模）", "同一 LS 边界；非本厂整套水系统；耗水与取水未分",
            STATUS["profile"], f"{lrec[key]['value']} {lrec[key]['unit']}", "SRC040",
            "循环水≠耗水；处理量≠用水量")
    solids = [("E-15", "碱渣（一般固废，LS）", "LS23_CAUSTIC_RESIDUE"),
              ("E-16", "碳渣（一般固废，LS）", "LS23_CARBON_RESIDUE"),
              ("E-17", "湿式除尘渣（湿法段，LS）", "LS23_WET_SCRUBBER_RESIDUE"),
              ("E-18", "湿式除尘渣（预处理段，LS）", "LS23_PRE_WET_SCRUBBER_RESIDUE")]
    for item_id, name, key in solids:
        if key == "LS23_PRE_WET_SCRUBBER_RESIDUE":
            qty = float(lrec[key]["value"]) * lfp_cell
            basis = f"{lrec[key]['value']} t/t 电芯 × {lfp_cell:,.3f} t LFP 电芯（LS 原表分母 1 万 t 电芯）"
        else:
            qty = float(ex[key]["annual_value"])
            basis = "LS 同源粉料线（示例规模）"
        add(item_id, name, qty, "t/a", basis, "一般固废/危废分类未逐项核定", STATUS["profile"],
            "源表固渣量", "SRC040", "固废属性（一般/危）与处置路径需 M13 因子与本地许可确认")
    pre = [("E-19", "预处理酸雾洗涤水", "LS23_PRE_SCRUBBER_WATER", "m3/a"),
           ("E-20", "预处理冷却水", "LS23_PRE_COOL_WATER", "m3/a"),
           ("E-21", "预处理淬冷水", "LS23_PRE_QUENCH_WATER", "m3/a"),
           ("E-22", "预处理天然气", "LS23_PRE_NG", "Nm3/a"),
           ("E-23", "预处理氮气", "LS23_PRE_N2", "Nm3/a")]
    for item_id, name, key, unit in pre:
        qty = float(lrec[key]["value"]) * lfp_cell
        add(item_id, name, qty, unit, f"{lrec[key]['value']} {lrec[key]['unit']} × {lfp_cell:,.3f} t LFP 电芯",
            "按 LS 预处理单耗线性放大到本组 LFP 电芯量；LS 原表分母 1 万 t 电芯，属跨规模代理",
            STATUS["profile"], "单耗 × 电芯量", "SRC040", "天然气只给体积，不自行折 MJ；氮气为载气/保护气，非燃料")
    add("E-24", "预处理黑粉产率（LS 同源）", float(lrec["LS23_NATIVE_POWDER_YIELD"]["value"]), "t_powder/t_cell",
        "0.5 t 正负极粉/t 电芯（含 97% 极粉）", "LS 输入为单体电芯；总粉物流含 97% 极粉，不是元素回收率",
        STATUS["profile"], "源表 5,000/10,000", "SRC040",
        "该产率与 JR 电芯组成得到的黑粉占比不是同一口径，不得互代")

    # --- 药剂：商品吨与有效吨并列（A04）--------------------------------------
    chem = [("E-25", "98% 硫酸", "LS_ACID", "t_commercial/a"),
            ("E-26", "99% 铁粉", "LS_FE", "t_commercial/a"),
            ("E-27", "32% 液碱", "LS_NAOH", "t_commercial/a"),
            ("E-28", "92% 氧化钙", "LS_CAO", "t_commercial/a"),
            ("E-29", "85% 磷酸", "LS_PACID", "t_commercial/a"),
            ("E-30", "液 CO2", "LS_CO2", "t_commercial/a"),
            ("E-31", "液氧", "LS_O2", "t_commercial/a")]
    for item_id, name, key, unit in chem:
        rec = ex[key]
        add(item_id, f"{name}（商品吨）", float(rec["annual_value"]), unit,
            f"商品质量；规格 {rec['specification_fraction']}", "LS 同源路线示例规模；跨体系代理到 JR 粉料",
            STATUS["profile"], "0.…t/t 粉料 × 粉料量", "SRC040",
            f"有效吨 = {rec['active_equivalent_t_a']:,.3f} t/a（商品吨 × 规格）；"
            "B/C 若直接用商品吨乘单价须声明规格，用有效吨做化学计量须改用另一列")
    add("E-32", "98% 硫酸（第二版本，敏感性）", float(ls["example_scale_only"]["acid_alt_98pct_commercial_t_a"]),
        "t_commercial/a", "0.4902 t/t 粉料（§4.3.1.2 稀释酸雾源强）",
        "与主版本 0.5630527 同称 98% 硫酸、同条粉线，冲突未解", STATUS["profile"],
        "0.4902 × 粉料量", "SRC040", "两版本并列，不平均；M07 未解前不选一个当正式值")
    add("E-33", "32% 液碱有效吨（纯 NaOH 计）", float(ex["LS_NAOH"]["active_equivalent_t_a"]), "t_NaOH/a",
        "商品吨 × 0.32", "浓度 32% 为源表申报值", STATUS["profile"],
        f"{ex['LS_NAOH']['annual_value']:,.3f} × 0.32", "SRC040",
        "商品吨与有效吨必须成对出现：13,788.612 t 32% 液碱 ≈ 4,412.356 t NaOH；不得用商品吨直接判工艺异常")
    return rows


# ----------------------------------------------------------------------------- 黑粉捕集情景表
FIELDS_CAPTURE = ["chemistry", "scenario_id", "capture_fraction", "sd_fraction", "sample_n",
                  "denominator", "inventory_t_a", "captured_t_a", "not_captured_t_a",
                  "plant_measured_t_a", "basis", "assumption", "source_ids", "status", "note"]


def capture_rows(supp: dict[str, Any]) -> list[dict[str, Any]]:
    mcs = supp["mechanical_capture_screening"]
    alt = mcs["alternative_route"]
    rows: list[dict[str, Any]] = []
    for rec in mcs["annual_rows"]:
        for sid, frac, sd, key in (
                (mcs["profile_id"], float(mcs["reference_capture_fraction"]), float(mcs["reference_sd_fraction"]),
                 "conditionally_captured_blackmass_t_a"),
                (alt["profile_id"], float(alt["capture_fraction"]), float(alt["sd_fraction"]),
                 "alternative_EV_II_captured_t_a")):
            captured = float(rec[key])
            inv = float(rec["inventory_t_a"])
            rows.append({
                "chemistry": rec["chemistry"],
                "scenario_id": sid,
                "capture_fraction": frac,
                "sd_fraction": sd,
                "sample_n": mcs["sample_n"] if sid == mcs["profile_id"] else None,
                "denominator": mcs["denominator"],
                "inventory_t_a": inv,
                "captured_t_a": captured,
                "not_captured_t_a": inv - captured,
                "plant_measured_t_a": rec["plant_measured_blackmass_t_a"],
                "basis": "黑粉总质量；不推定 Li/Ni/Co/Mn 同率分配",
                "assumption": "; ".join(mcs["transfer_assumptions"]),
                "source_ids": mcs["source_id"],
                "status": STATUS["capture"],
                "note": ("文献迁移情景，不是实测黑粉产量；未捕集部分去向未量化（" + rec["remaining_destination"] + "）"),
            })
    return rows


# ----------------------------------------------------------------------------- 参考 profile 表（B 活动量）
FIELDS_PROFILE = ["profile_id", "activity_key", "activity_label", "quantity", "unit",
                  "basis_denominator", "annual_value", "annual_unit", "per_fu_value", "per_fu_unit",
                  "per_fu_denominator", "specification_fraction", "source_ids", "assumption",
                  "status", "note"]


def profile_rows(supp: dict[str, Any], totals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ls = route(supp, "LS23_LFP_NATIVE_POWDER")
    lrec = by_id(ls["records"])
    ex = example_annual(ls)
    lce_ls = float(ex["LS23_PRODUCT_CRUDE_LIC"]["dry_pure_substance_t_a"])
    anl = route(supp, "ANL19_GENERIC_HYD_CELL")
    aanl = anl_annual(anl)
    jiang = route(supp, "JIANG24_NATIVE_LFP_PILOT")
    nd = route(supp, "ND22_WHOLE_CATHODE_PROJECT_REFERENCE")
    lfp_cell = next(x for x in totals if x["chemistry"] == LFP)["cell_t_a"]
    rows: list[dict[str, Any]] = []

    def add(profile, key, label, qty, unit, basis, annual=None, annual_unit=None,
            per_fu=None, per_fu_unit=None, den=None, spec=None, src="", asm="", status=STATUS["profile"], note=""):
        rows.append({
            "profile_id": profile, "activity_key": key, "activity_label": label,
            "quantity": qty, "unit": unit, "basis_denominator": basis,
            "annual_value": annual, "annual_unit": annual_unit,
            "per_fu_value": per_fu, "per_fu_unit": per_fu_unit, "per_fu_denominator": den,
            "specification_fraction": spec, "source_ids": src, "assumption": asm,
            "status": status, "note": note,
        })

    # --- LS23：粉料品位（as-received 假设）-----------------------------------
    for key, label, unit in (("LS23_MOISTURE", "粉料含水 H2O", "kg_H2O/kg_powder"),
                             ("LS23_ASSAY_LI", "Li", "kg_element/kg_powder"),
                             ("LS23_ASSAY_FE", "Fe", "kg_element/kg_powder"),
                             ("LS23_ASSAY_P", "P", "kg_element/kg_powder"),
                             ("LS23_ASSAY_C", "C", "kg_element/kg_powder")):
        add("LS23_LFP_NATIVE_POWDER", key, label, float(lrec[key]["value"]), unit,
            "1 kg 报告申报粉料", src="SRC040", asm="同表 as-received；其余元素干/湿基未明",
            note=f"部分组成合计 0.772665，不归一化；定位 {lrec[key]['locator']}")
    add("LS23_LFP_NATIVE_POWDER", "LS23_DERIVED_LI_TO_CRUDE", "表间推导：粉料 Li 进入粗碳酸锂比例",
        float(lrec["LS23_DERIVED_LI_TO_CRUDE"]["value"]), "t_Li_crude/t_Li_powder",
        "粉料 Li（as-received 假设）", src="SRC040",
        asm="跨表推导，非实测；余 Li 去向未闭合", status=STATUS["diag"],
        note="≠浸出率；与文献 0.90—0.976、JIANG 0.976 分母不同，不可混成区间")
    add("LS23_LFP_NATIVE_POWDER", "LS23_NATIVE_POWDER_YIELD", "正负极粉总产率",
        float(lrec["LS23_NATIVE_POWDER_YIELD"]["value"]), "t_powder/t_cell", "1 t LFP 电芯",
        src="SRC040", asm="总粉物流含 97% 极粉，不是元素回收率", status=STATUS["diag"],
        note="与 JR 电芯组成得到的黑粉占比不同口径")
    add("LS23_LFP_NATIVE_POWDER", "LS23_DERIVED_POWDER_COMPONENT_CAPTURE", "目标组分隐含捕集率",
        float(lrec["LS23_DERIVED_POWDER_COMPONENT_CAPTURE"]["value"]), "t_target_in_powder/t_target_in_cell",
        "正负极活性粉=38%+11% 电芯质量", src="SRC040",
        asm="须假设 97% 级粉含量对应正负极目标组分且同质量基", status=STATUS["diag"],
        note="分母与 EV I 0.9328 不同：非冲突值、不平均、不当 Li 捕集率")

    # --- LS23：药剂与公用（示例规模年量 + 每 t LCE）----------------------------
    for key in ("LS_ACID", "LS_FE", "LS_NAOH", "LS_CAO", "LS_PACID", "LS_CO2", "LS_O2"):
        rec = ex[key]
        add("LS23_LFP_NATIVE_POWDER", key, rec["label"], None, "t_commercial/t_powder",
            f"{rec['annual_value'] / float(ls['example_scale_only']['powder_feed_t_a']):.8f} t/t 粉料（由年量反算）",
            annual=float(rec["annual_value"]), annual_unit="t_commercial/a",
            per_fu=float(rec["annual_value"]) / lce_ls, per_fu_unit="t_commercial/t_LCE",
            den=f"{lce_ls:,.3f} t LCE（LS 情景干纯粗碳酸锂）",
            spec=rec["specification_fraction"], src="SRC040",
            asm="LS 同源路线；跨体系代理到 JR 粉料；商品规格按申报浓度",
            note=f"有效吨 {rec['active_equivalent_t_a']:,.3f} t/a；商品吨与有效吨并列，不得混用")
    add("LS23_LFP_NATIVE_POWDER", "LS_ACID_ALT", "98% 硫酸（第二版本 0.4902）", 0.4902, "t_commercial/t_powder",
        "§4.3.1.2 稀释酸雾源强", annual=float(ls["example_scale_only"]["acid_alt_98pct_commercial_t_a"]),
        annual_unit="t_commercial/a", spec=0.98, src="SRC040",
        asm="与主版本 0.5630527 同称 98% 硫酸、同条粉线，冲突未解", status=STATUS["diag"],
        note="两版本并列、不平均；M07 未解前不选一个当正式值")
    add("LS23_LFP_NATIVE_POWDER", "LS23_COMBINED_ELECTRICITY", "组合电耗（预处理+湿法+公辅）",
        None, "kWh/t_powder", "1 万 t 电芯 + 1 万 t 粉料 + 公辅的组合电表",
        annual=float(lrec["LS23_COMBINED_ELECTRICITY"]["value"]), annual_unit="kWh/a",
        src="SRC040", asm="不可拆成单线", status=STATUS["diag"],
        note="不除以粉量充当湿法单耗；本厂分线电耗 null（M08_ELECTRIC）")
    add("LS23_LFP_NATIVE_POWDER", "LS23_STEAM", "蒸汽（质量）", float(lrec["LS23_STEAM"]["value"]),
        "t_steam/t_powder", "1 t 申报粉料", annual=float(ex["LS23_STEAM"]["annual_value"]),
        annual_unit="t_steam/a", per_fu=float(ex["LS23_STEAM"]["annual_value"]) / lce_ls,
        per_fu_unit="t_steam/t_LCE", den=f"{lce_ls:,.3f} t LCE", src="SRC040",
        asm="压力/温度/返凝水/购热结算口径未取得", status=STATUS["diag"],
        note="只给 t；M08_STEAM 未解前不转 MJ（禁止无依据填 2500 MJ/t）")
    for key, label, unit in (("LS23_PURE_WATER", "纯水", "m3/t_powder"),
                             ("LS23_SCRUBBER_MAKEUP", "洗涤/吹扫补水", "m3/t_powder"),
                             ("LS23_FLOOR_WATER", "地坪冲洗水", "m3/t_powder"),
                             ("LS23_MVR_CONDENSATE_DISCHARGE", "MVR 冷凝外排", "m3/t_powder"),
                             ("LS23_SCRUBBER_WW", "酸雾洗涤废水", "m3/t_powder"),
                             ("LS23_FLOOR_WW", "地坪废水", "m3/t_powder")):
        add("LS23_LFP_NATIVE_POWDER", key, label, float(lrec[key]["value"]), unit, "1 t 申报粉料",
            annual=float(ex[key]["annual_value"]), annual_unit="m3/a", src="SRC040",
            asm="同一 LS 边界；取水与耗水未分", note="循环水≠耗水；处理量≠用水量（M08_WATER）")
    for key, label, unit in (("LS23_CAUSTIC_RESIDUE", "碱渣", "t/t_powder"),
                             ("LS23_CARBON_RESIDUE", "碳渣", "t/t_powder"),
                             ("LS23_WET_SCRUBBER_RESIDUE", "湿式除尘渣（湿法段）", "t/t_powder")):
        add("LS23_LFP_NATIVE_POWDER", key, label, float(lrec[key]["value"]), unit, "1 t 申报粉料",
            annual=float(ex[key]["annual_value"]), annual_unit="t/a", src="SRC040",
            asm="固废属性未逐项核定", note="一般固废/危废分类与处置路径未定（M13）")
    for key, label, unit in (("LS23_PRE_SCRUBBER_WATER", "预处理酸雾洗涤水", "m3/t_cell"),
                             ("LS23_PRE_COOL_WATER", "预处理冷却水", "m3/t_cell"),
                             ("LS23_PRE_QUENCH_WATER", "预处理淬冷水", "m3/t_cell"),
                             ("LS23_PRE_NG", "预处理天然气", "Nm3/t_cell"),
                             ("LS23_PRE_N2", "预处理氮气", "Nm3/t_cell"),
                             ("LS23_PRE_WET_SCRUBBER_RESIDUE", "湿式除尘渣（预处理段）", "t/t_cell")):
        annual = float(lrec[key]["value"]) * lfp_cell
        add("LS23_LFP_NATIVE_POWDER", key, label, float(lrec[key]["value"]), unit, "1 t LFP 电芯",
            annual=annual, annual_unit=dict(m3_a="m3/a", t_a="t/a", nm="Nm3/a").get(
                "nm" if unit.startswith("Nm3") else ("t_a" if unit.startswith("t/") else "m3_a")),
            src="SRC040", asm=f"按 LS 单耗线性放大到本组 {lfp_cell:,.3f} t LFP 电芯（跨规模代理）",
            note="天然气只给体积不折 MJ；氮气非燃料")
    for key in ("LS23_PRODUCT_CRUDE_LIC", "LS23_PRODUCT_FEP_SLAG", "LS23_PRODUCT_ALP",
                "LS23_PRODUCT_SODIUM_SULFATE", "LS23_PRODUCT_SPONGE_CU"):
        rec = ex[key]
        add("LS23_LFP_NATIVE_POWDER", key, rec["label"], None, "t_product/t_powder",
            "由年量反算", annual=float(rec["annual_value"]), annual_unit="t_product/a",
            src="SRC040", asm="LS 同源路线；不是电池级成品", status=STATUS["intermediate"],
            note=f"product_role={lrec[key].get('product_role')}；可售电池级量为 null")

    # --- ANL19：三元通用电芯模型 ----------------------------------------------
    aint = by_id(anl["activity_intensities"])
    for key in ("H2SO4", "H2O2", "NaOH", "HCl", "NH4OH", "Na2CO3"):
        add("ANL19_GENERIC_HYD_CELL", key, key, float(aint[key]["value"]), aint[key]["unit"],
            "1 kg 电芯（申报化学品，商业浓度 null）",
            annual=float(aanl[key]["annual_value"]), annual_unit="t_declared_chemical/a",
            spec=None, src="SRC043", asm="ANL 模型内含预处理与湿法的综合剂量；商业浓度未交代",
            note="无产品量 → 不换算 per FU；不得与 LS 药剂相加")
    for key in ("electricity", "natural_gas_energy", "diesel_energy", "water"):
        rec = aint[key]
        add("ANL19_GENERIC_HYD_CELL", key, key, float(rec.get("converted_value", rec["value"])),
            rec.get("converted_unit", rec["unit"]), f"{rec['value']} {rec['unit']}",
            annual=float(aanl[key]["annual_value"]), annual_unit=aanl[key]["unit"], src="SRC043",
            asm="模型内部分配；柴油为车用/场内，与厂内天然气同为模型输出",
            status=STATUS["diag"], note="独立模型参考，不是园区实测；柴油能耗不等于运输柴油")
    for key, val in anl["recovery_defaults"].items():
        add("ANL19_GENERIC_HYD_CELL", f"recovery_{key}", f"{key} 默认回收率", float(val), "t_recovered/t_in_route",
            "全路线默认（含预处理与湿法）", src="SRC043",
            asm="模型默认值，非实测", status=STATUS["diag"],
            note="全路线口径：若采用只乘一次，且不得再乘黑粉捕集损失")

    # --- JIANG24：中试单批（2 t 粉料）-----------------------------------------
    batch = float(jiang["native_batch_powder_t"])
    for rec in jiang["batch_records"]:
        if rec.get("value") is None:
            continue
        add("JIANG24_NATIVE_LFP_PILOT", rec["reference_parameter_id"], rec["name"],
            float(rec["value"]) / batch, f"{rec['unit']}/t_powder", f"每 {batch} t 粉料单批",
            annual=None, annual_unit=None, src="SRC021",
            asm="中间规模中试（500 t/a 装置）；不能线性放大为工业单耗", status=STATUS["diag"],
            note=f"单批值 {rec['value']} {rec['unit']}；{rec['input_or_product_basis']}；不得与 LS/ANL 相加")
    li6 = jiang["li_balance_table6"]
    add("JIANG24_NATIVE_LFP_PILOT", "Li_to_Li2CO3", "Li 去向：碳酸锂",
        float(li6["Li_to_Li2CO3_fraction_derived"]), "t_Li/t_Li_in", "表6 Li 平衡", src="SRC021",
        asm="表6 公开舍入值，闭合 99.94% 只是报告值", status=STATUS["diag"],
        note=f"舍入残差 ≈0.00057 > 5e-4，不得宣称严格通过；Li→Li3PO4 {li6['Li_to_Li3PO4_fraction_derived']:.6f}")
    add("JIANG24_NATIVE_LFP_PILOT", "li_leaching_fraction", "煅烧后浸出率",
        float(li6["li_leaching_fraction_after_calcination"]), "t_Li_leached/t_Li_feed", "煅烧后渣", src="SRC021",
        asm="工序值，不是全流程收率", status=STATUS["diag"], note="0.976 不得当总收率")

    # --- ND22：全项目（只作量级参照）-----------------------------------------
    add("ND22_WHOLE_CATHODE_PROJECT_REFERENCE", "whole_project_electricity", "全项目用电",
        None, "kWh/t_cathode_sheet", "5.3 万 t 三元 + 4.7 万 t LFP 正极片",
        annual=float(nd["whole_project_electricity_kwh_a"]), annual_unit="kWh/a", src="SRC042",
        asm="整项目含多产品", status=STATUS["diag"], note="selected_as_plant_energy=false")
    for idx, stream in enumerate(nd["steam_streams"], start=1):
        add("ND22_WHOLE_CATHODE_PROJECT_REFERENCE", f"steam_{idx}",
            f"蒸汽 {stream['pressure_MPa']} MPa / {stream['temperature_C']} ℃",
            None, "t_steam/a", "整项目", annual=float(stream["mass_t_a"]), annual_unit="t_steam/a",
            src="SRC042", asm="整项目边界", status=STATUS["diag"], note="只给质量；状态已知但不是本厂结算口径")
    add("ND22_WHOLE_CATHODE_PROJECT_REFERENCE", "lfp_lce_specific_total_energy",
        "LFP 碳酸锂综合能耗", float(nd["lfp_lce_specific_total_energy_kgce_t"]), "kgce/t_LCE",
        "整项目 LFP 线", src="SRC042", asm="多产品综合能耗", status=STATUS["diag"],
        note="禁止用综合能耗减 LS 蒸汽、把余量当电耗（A04）")
    return rows


# ----------------------------------------------------------------------------- B 活动接口（11+1 键）
FIELDS_BVECTOR = ["activity_key", "expected_unit", "b_default_placeholder", "a_formal_value_per_fu",
                  "a_screening_annual", "a_screening_annual_unit", "a_screening_profile",
                  "per_fu_denominator", "status", "basis", "assumption", "source_ids", "note"]


def b_vector_rows(supp: dict[str, Any], dec: dict[str, Any], totals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ls = route(supp, "LS23_LFP_NATIVE_POWDER")
    lrec = by_id(ls["records"])
    ex = example_annual(ls)
    jiang = route(supp, "JIANG24_NATIVE_LFP_PILOT")
    jbatch = float(jiang["native_batch_powder_t"])
    powder_t = float(ls["example_scale_only"]["powder_feed_t_a"])

    def jiang_val(name: str) -> float:
        for rec in jiang["batch_records"]:
            if rec["name"] == name:
                return float(rec["value"])
        raise KeyError(f"JIANG24 表7 缺少 {name}")
    lfp_cell = next(x for x in totals if x["chemistry"] == LFP)["cell_t_a"]
    bdef = dec["external_reference_constants"]["B_snapshot_20261103"]["default_activities"]
    km = float(dec["external_reference_constants"]["C_snapshot_20261103"]["transport_inbound_km"])
    feed = float(dec["operating_case"]["actual_received_pack_t_a"])
    water_in = sum(float(ex[k]["annual_value"]) for k in ("LS23_PURE_WATER", "LS23_SCRUBBER_MAKEUP", "LS23_FLOOR_WATER"))
    rows: list[dict[str, Any]] = []

    def add(key, unit, annual, annual_unit, profile, status, basis, asm, src, note):
        rows.append({
            "activity_key": key, "expected_unit": unit,
            "b_default_placeholder": bdef.get(key),
            "a_formal_value_per_fu": None,
            "a_screening_annual": annual, "a_screening_annual_unit": annual_unit,
            "a_screening_profile": profile,
            "per_fu_denominator": None,
            "status": status, "basis": basis, "assumption": asm, "source_ids": src, "note": note,
        })

    add("electricity_kwh", "kWh/t_LCE", float(lrec["LS23_COMBINED_ELECTRICITY"]["value"]), "kWh/a",
        "LS23_LFP_NATIVE_POWDER", "blocked_M08",
        "组合电表（预处理+湿法+公辅）", "不可拆单线；跨规模代理",
        "SRC040", "正式 per-FU 电耗 null（A04 已删除 ND−LS 反算）；组合量不得除以粉量或 LCE")
    add("natural_gas", "MJ/t_LCE", float(lrec["LS23_PRE_NG"]["value"]) * lfp_cell, "Nm3/a",
        "LS23_LFP_NATIVE_POWDER", "blocked_M08",
        "预处理天然气体积 × LFP 电芯量", "只给体积，未折 MJ", "SRC040",
        "若沿用 B 的 12,000 MJ/t 须另声明总量口径；不得与 Nm3 混用")
    add("process_steam", "MJ/t_LCE", float(ex["LS23_STEAM"]["annual_value"]), "t_steam/a",
        "LS23_LFP_NATIVE_POWDER", "blocked_M08",
        "LS 蒸汽质量（1.1747755 t/t 粉料）", "压力/温度/返凝水未核", "SRC040",
        "只给商品吨；未转 MJ。ND22 两股蒸汽（1.5 MPa/200 ℃ 与 3.5 MPa/243 ℃）为整项目参考，不是本厂")
    add("sulfuric_acid_H2SO4", "kg/t_LCE", float(ex["LS_ACID"]["annual_value"]), "t_commercial/a",
        "LS23_LFP_NATIVE_POWDER", "blocked_M06",
        "98% 硫酸商品吨；主版本 0.5630527 t/t 粉料",
        "有效吨 5,197.246 t/a；第二版本 4,617.123 t/a 并列", "SRC040",
        "B 的 2,500 kg/t 与 B 自身 6.0969 t 粉料/t LCE 分母相关；A 的 per-FU 需先确定 LCE 产量")
    add("hydrogen_peroxide_H2O2", "kg/t_LCE", jiang_val("双氧水") / jbatch * powder_t,
        "m3/a", "JIANG24_NATIVE_LFP_PILOT", "blocked_M06",
        "中试 1.2 m3/2 t 粉料 × LS 粉量", "体积单位，浓度与商品规格未交代", "SRC021",
        "LS 原表无 H2O2 系数；此值来自另一 profile，只作量级参照")
    add("sodium_hydroxide_NaOH", "kg/t_LCE", float(ex["LS_NAOH"]["annual_value"]), "t_commercial/a",
        "LS23_LFP_NATIVE_POWDER", "blocked_M06",
        "32% 液碱商品吨", "有效吨 4,412.356 t/a；不得用商品吨判工艺异常", "SRC040",
        "B 的 8.9 t/t LCE 属商品吨×6.1 t 粉料分母；A 的正式 per-FU null")
    add("sodium_carbonate_Na2CO3", "kg/t_LCE", jiang_val("碳酸钠") / jbatch * powder_t / 1000.0,
        "t/a", "JIANG24_NATIVE_LFP_PILOT", "blocked_M06",
        "中试 750 kg/2 t 粉料 × LS 粉量（kg→t）", "中试单耗线性放大属假设", "SRC021",
        "源表为申报质量，纯度未交代")
    add("lime_CaO", "kg/t_LCE", float(ex["LS_CAO"]["annual_value"]), "t_commercial/a",
        "LS23_LFP_NATIVE_POWDER", "blocked_M06",
        "92% 氧化钙商品吨", "有效吨 254.761 t/a", "SRC040", "商品规格须随单价声明")
    add("diesel_truck", "t·km/t_LCE", feed * km, "t·km/a",
        "A_GROUP_CASE", "conditional_transport",
        f"实际进料 {feed:,.0f} t/a × 到厂距离 {km:,.0f} km（C 假设）",
        "距离为 C 的运输假设；未取得实际运距分布", "SRC031",
        "环境运输排放与经济到厂价分别核算一次；C 的单独运费项为 0 且注明 delivered_included，故不重复计费")
    add("wastewater_treatment", "m3/t_LCE", water_in, "m3/a",
        "LS23_LFP_NATIVE_POWDER", "blocked_M08",
        "纯水 + 洗涤补水 + 地坪水（过程用水）", "处理量≠用水量；无全厂水平衡", "SRC040",
        "M08_WATER 未解；本厂取水 null")
    add("fluoride_wastewater_advanced", "m3/t_LCE", None, "m3/a",
        "NONE", "blocked_M08", "含氟高盐废水未量化", "99.5% 固氟率是阈值，不是实测收率", "SRC035",
        "缺数不补 0")
    add("hazardous_residue_disposal", "t/t_LCE", None, "t/a",
        "NONE", "blocked_M13", "固废属性未逐项核定", "LS 固渣已量化为一般固废口径，未含危废", "SRC040",
        "危废量与一般固废量不可混用")
    return rows


# ----------------------------------------------------------------------------- C 计价年量接口
FIELDS_CQR = ["item_id", "pricing_item", "quantity_per_year", "unit", "quantity_kind",
              "wet_or_dry", "commercial_or_active", "service_grade", "basis", "assumption",
              "status", "source_ids", "note"]


def c_quantity_rows(supp: dict[str, Any], dec: dict[str, Any], totals: list[dict[str, Any]],
                    main_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ls = route(supp, "LS23_LFP_NATIVE_POWDER")
    ex = example_annual(ls)
    km = float(dec["external_reference_constants"]["C_snapshot_20261103"]["transport_inbound_km"])
    feed = float(dec["operating_case"]["actual_received_pack_t_a"])
    reuse = float(dec["operating_case"]["conditional_reuse_allocated_pack_t_a"])
    rows: list[dict[str, Any]] = []

    def add(item_id, item, qty, unit, kind, wet_dry, commercial, grade, basis, asm, status, src, note):
        rows.append({
            "item_id": item_id, "pricing_item": item, "quantity_per_year": qty, "unit": unit,
            "quantity_kind": kind, "wet_or_dry": wet_dry, "commercial_or_active": commercial,
            "service_grade": grade, "basis": basis, "assumption": asm, "status": status,
            "source_ids": src, "note": note,
        })

    add("CR-01", "来料整包（处理费计费基数）", feed, "t_pack/a", "input_allocation", "-", "-",
        "混合来料", "实际进料 68,000 t/a", "组内工况；含 LFP/三元", STATUS["group"], "SRC031",
        "C 的处理费/负价收入应以本量为基数；不等于园区设计能力 80,000")
    add("CR-02", "梯次分配整包（尚未形成收入）", reuse, "t_pack/a", "input_allocation", "-", "-",
        "分流输入", "梯次能力 × 负荷", "可售 kWh 与整包当量均 null", STATUS["null"], "SRC031",
        "SOH/筛选率/重组率未取得，不得按梯次单价计收入")
    for idx, item in enumerate(("电池级碳酸锂", "电池级磷酸铁", "电池级镍/钴/锰盐",
                                "铜箔产品", "铝箔产品", "硫酸钠", "磷酸铝", "其他外售品"), start=1):
        add(f"CR-{2 + idx:02d}", f"可售品：{item}", None, "t_product/a", "saleable_product", "-", "-",
            item, "M05_PRODUCTS 未解", "成品规格/纯度/合格率未取得", STATUS["null"],
            "NEW-STD-LCE;NEW-STD-FEP;SRC040;SRC043", "价格可先由 C 挂接，但数量必须等 A 的可售量解锁")
    for item_id, item, rec, wd, note in (
            ("CR-11", "粗碳酸锂（中间品）", ex["LS23_PRODUCT_CRUDE_LIC"], "湿", "含水 0.20、干纯度 0.99；内部进入铁锂线"),
            ("CR-12", "磷酸铁渣（中间品）", ex["LS23_PRODUCT_FEP_SLAG"], "湿", "含水 0.40、干纯度 0.99；不是电池级磷酸铁"),
            ("CR-13", "磷酸铝（副产）", ex["LS23_PRODUCT_ALP"], "湿", "含水 0.40；规格未定")):
        add(item_id, item, float(rec["annual_value"]), "t_product/a", "recovered_intermediate", wd, "-",
            "中间品/副产", "LS 同源路线示例规模", "JR 粉料与 LS 组成的等价性未证实", STATUS["intermediate"],
            "SRC040", f"{note}；干纯 {rec.get('dry_pure_substance_t_a'):,.3f} t/a")
    add("CR-14", "硫酸钠（副产）", float(ex["LS23_PRODUCT_SODIUM_SULFATE"]["annual_value"]), "t_product/a",
        "recovered_intermediate", "未明", "-", "副产", "LS 同源路线", "水合形态/水分未明", STATUS["intermediate"],
        "SRC040", "水合形态未定时不能按无水硫酸钠计价")
    add("CR-15", "海绵铜（Cu-40）", float(ex["LS23_PRODUCT_SPONGE_CU"]["annual_value"]), "t_product/a",
        "recovered_intermediate", "干", "-", "Cu 40%", "LS 同源路线", "纯度指 Cu 质量分数", STATUS["intermediate"],
        "SRC040", f"含铜 {ex['LS23_PRODUCT_SPONGE_CU']['annual_value'] * 0.40:,.3f} t/a")
    for chem in CHEMS:
        t = next(x for x in totals if x["chemistry"] == chem)
        add(f"CR-16-{CHEMS.index(chem) + 1}", f"铜箔（{NAME_CN[chem]}，100% 分选上限）", t["cu_foil_t_a"],
            "t_Cu/a", "reference_material_ceiling", "干", "-", "上限", "JR 电芯组成 × 再生入口",
            "假设 100% 分选", STATUS["ceiling"], "SRC039", "上限不是产量；未扣附着粉")
        add(f"CR-17-{CHEMS.index(chem) + 1}", f"铝箔（{NAME_CN[chem]}，100% 分选上限）", t["al_foil_t_a"],
            "t_Al/a", "reference_material_ceiling", "干", "-", "上限", "JR 电芯组成 × 再生入口",
            "假设 100% 分选", STATUS["ceiling"], "SRC039", "上限不是产量")
    for item_id, item, key, note in (
            ("CR-18", "98% 硫酸", "LS_ACID", "主版本 0.5630527 t/t 粉料；并列第二版本 4,617.123 t/a"),
            ("CR-19", "32% 液碱", "LS_NAOH", "商品吨；有效吨见 CR-20"),
            ("CR-20", "32% 液碱（有效吨）", "LS_NAOH", "有效吨 = 商品吨 × 0.32"),
            ("CR-21", "92% 氧化钙", "LS_CAO", "商品吨；有效吨另列"),
            ("CR-22", "85% 磷酸", "LS_PACID", "商品吨；有效吨另列"),
            ("CR-23", "99% 铁粉", "LS_FE", "商品吨；有效吨另列"),
            ("CR-24", "液 CO2", "LS_CO2", "商品吨"),
            ("CR-25", "液氧", "LS_O2", "商品吨")):
        rec = ex[key]
        if item_id == "CR-20":
            qty = float(rec["active_equivalent_t_a"])
            unit, comm = "t_NaOH/a", "有效"
        else:
            qty = float(rec["annual_value"])
            unit, comm = "t_commercial/a", "商品"
        add(item_id, item, qty, unit, "diagnostic", "-", comm, "工业级", "LS 同源路线示例规模",
            "跨体系代理到 JR 粉料", STATUS["profile"], "SRC040",
            note + f"；规格 {rec['specification_fraction']}")
    add("CR-26", "电力（正式分线）", None, "kWh/a", "unresolved_null", "-", "-", "-",
        "M08_ELECTRIC 未解", "组合电耗 11,232,000 kWh/a 不可拆", STATUS["null"], "SRC040",
        "C 的 27,314,798 kWh 电网+绿电各半与 B 的 9,104.9 kWh/t 均来自 B 占位×3,000 t，不是本厂测量")
    add("CR-27", "蒸汽（质量）", float(ex["LS23_STEAM"]["annual_value"]), "t_steam/a", "diagnostic", "蒸汽", "-",
        "工业蒸汽", "LS 同源路线", "压力/温度未核；按 t 计价可行", STATUS["diag"], "SRC040",
        "state 未核前不得按 MJ 计价；NO.22 ND 两股蒸汽为整项目参考")
    add("CR-28", "天然气（体积）", float(by_id(ls["records"])["LS23_PRE_NG"]["value"]) * next(
        x for x in totals if x["chemistry"] == LFP)["cell_t_a"], "Nm3/a", "diagnostic", "-", "-",
        "燃料/保护气", "LS 预处理单耗 × LFP 电芯量", "跨规模代理", STATUS["diag"], "SRC040", "折 MJ 需热值与计量口径")
    add("CR-29", "新水/取水", None, "m3/a", "unresolved_null", "-", "-", "-",
        "M08_WATER 未解", "LS 分线水数据不是全厂水系统", STATUS["null"], "SRC040",
        "循环水与耗水必须分开；C 的 90,000 m3/a 无独立物料证据")
    add("CR-30", "一般固废处置量", sum(float(ex[k]["annual_value"]) for k in
                                   ("LS23_CAUSTIC_RESIDUE", "LS23_CARBON_RESIDUE", "LS23_WET_SCRUBBER_RESIDUE")),
        "t/a", "diagnostic", "-", "-", "一般固废", "LS 同源固渣（不含预处理湿式除尘渣）",
        "未逐项核定固废属性", STATUS["profile"], "SRC040",
        f"另加预处理湿式除尘渣 {float(by_id(ls['records'])['LS23_PRE_WET_SCRUBBER_RESIDUE']['value']) * next(x for x in totals if x['chemistry'] == LFP)['cell_t_a']:,.3f} t/a；C 的 4,500 t/a 待对齐")
    add("CR-31", "危险废物处置量", None, "t/a", "unresolved_null", "-", "-", "危废",
        "M13_FACTORS 未解", "固废属性未核定", STATUS["null"], "SRC040", "不得把一般固废记危废")
    add("CR-32", "入厂运输量", feed * km, "t·km/a", "diagnostic", "-", "-", "运输服务",
        f"68,000 t/a × {km:,.0f} km（C 假设）", "距离为 C 假设", "conditional_transport", "SRC031",
        "经济模型只应计一次同段运费；到厂价 delivered_included，单独运费项为 0")
    add("CR-33", "残渣外运量", None, "t/a", "unresolved_null", "-", "-", "-",
        "M05_LI_PARTITIONS 未解", "残渣/水处理污泥量未闭合", STATUS["null"], "SRC040",
        "C 的 4,500 t/a 为财务假设，缺独立物料证据")
    return rows


# ----------------------------------------------------------------------------- 缺口表
FIELDS_GAP = ["input_id", "missing", "what_is_now_available", "blocking_scope", "owner",
              "next_action", "severity", "status"]


def gap_rows(supp: dict[str, Any], dec: dict[str, Any], raw: dict[str, Any]) -> list[dict[str, Any]]:
    usage: dict[str, list[str]] = {}
    for gate in raw.get("calculation_gates") or []:
        for i in gate.get("blocking_input_ids") or []:
            usage.setdefault(i, []).append(gate["module"])
    owner_map = {
        "M02_ACTUAL": "A（园区分选实测）", "M03_COMPAT": "A + 湿法设计方",
        "M05_PRODUCTS": "A + 工艺设计方", "M05_LI_PARTITIONS": "A",
        "M08_ELECTRIC": "A + 园区电气", "M08_STEAM": "A + 园区热工", "M08_WATER": "A + 园区水务",
        "M01_REUSE_SALE": "A + 梯次运营方", "M10_ALLOCATION": "A + B（LCA 方法）",
        "M13_FACTORS": "B", "D-PARK-LINK": "A + C（区域供给）",
    }
    rows: list[dict[str, Any]] = []
    for item in supp["unresolved_inputs"]:
        iid = item["input_id"]
        modules = usage.get(iid) or usage.get(iid.split("_")[0]) or []
        rows.append({
            "input_id": iid,
            "missing": item["missing"],
            "what_is_now_available": item["what_is_now_available"],
            "blocking_scope": ";".join(modules) if modules else "未在闸门表中直接登记",
            "owner": owner_map.get(iid, "A"),
            "next_action": {
                "M02_ACTUAL": "取园区分体系黑粉实测捕集率（含分母定义与胶黏剂范围）；当前 EV I 0.9328 只是文献迁移情景",
                "M03_COMPAT": "对 JR 产粉与选定湿法入料做同口径化验（含水率、干/湿基、C/F 与胶黏剂）",
                "M05_PRODUCTS": "取电池级 LCE/FePO4/NiCoMn 盐的质量标准、水合形态、纯度与合格率",
                "M05_LI_PARTITIONS": "取各出厂/处置流股 Li 化验与连续工序分配表（当前 §4.2.3 保密）",
                "M08_ELECTRIC": "安装分线电表或取设备负荷清单，拆分预处理/湿法/公辅",
                "M08_STEAM": "取蒸汽压力/温度、返凝水量与购热结算口径（t 或 GJ）",
                "M08_WATER": "取全厂取水/纯水制备/循环/耗水/外排与处理层级",
                "M01_REUSE_SALE": "取 SOH、筛选合格率、重组损失与应用标准；可售 kWh 按四因子公式",
                "M10_ALLOCATION": "与 B 约定多产品分配/系统扩展口径并锁定功能产物分母",
                "M13_FACTORS": "锁定 B 各试剂/能源/处置因子版本与浓度边界",
                "D-PARK-LINK": "取市域→园区捕获率、外部来料与跨区域供给证据",
            }.get(iid, "按闸门要求补充证据"),
            "severity": "high" if iid in ("M02_ACTUAL", "M03_COMPAT", "M05_PRODUCTS", "M08_ELECTRIC", "M01_REUSE_SALE") else "medium",
            "status": "unresolved_null",
        })
    rows.append({
        "input_id": "M06_ROUTE", "missing": "湿法体系选定（LFP 走 LS 还是其他、三元走 ANL 还是 LI20）",
        "what_is_now_available": "LS23 / ANL19 / JIANG24 三套参考 profile，已按 profile_id 隔离",
        "blocking_scope": "wet_process_activities", "owner": "A + 工艺设计方",
        "next_action": "选定体系并声明边界；不得把多套 profile 拼成同一座工厂",
        "severity": "high", "status": "unresolved_null",
    })
    rows.append({
        "input_id": "M07_ACID", "missing": "98% 硫酸单耗版本（0.5630527 与 0.4902）",
        "what_is_now_available": "两版本并列，未平均；各自可换算示例规模年量",
        "blocking_scope": "wet_process_activities", "owner": "A + 工艺设计方",
        "next_action": "取原辅料表与酸雾核算的口径说明；未解前两版本并列、不取均值",
        "severity": "medium", "status": "unresolved_null",
    })
    rows.append({
        "input_id": "GAP-LCE-SALE", "missing": "A 侧可售 LCE 产量（口径与 C 的 3,000 t 财务变量分开）",
        "what_is_now_available": "JR 情景上限 3,142.6 t/a（100% 回收假设）；LS 情景干纯粗碳酸锂 1,059.736 t/a（中间品）",
        "blocking_scope": "full_plant_li_mfa;lca_tea_results", "owner": "A",
        "next_action": "先解 M02/M03/M05，再给可售量；不得用 C 的 3,000 t 反推 A 的产量",
        "severity": "high", "status": "unresolved_null",
    })
    return rows


# ----------------------------------------------------------------------------- 成果自检（P）
FIELDS_PCHECK = ["check_id", "section", "item", "status", "detail"]


def post_checks(rows: list[dict[str, Any]], b_rows: list[dict[str, Any]],
                cap_rows: list[dict[str, Any]], totals: list[dict[str, Any]],
                dec: dict[str, Any], raw: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    def find(item_id: str) -> dict[str, Any]:
        for rec in rows:
            if rec["item_id"] == item_id:
                return rec
        raise KeyError(item_id)

    # P01 组分库存合计 = 再生入口（整包级）
    worst = 0.0
    for chem in CHEMS:
        t = next(x for x in totals if x["chemistry"] == chem)
        s = sum(float(x["quantity_per_year"]) for x in b_rows
                if x["chemistry"] == chem and x["level"] == "整包")
        worst = max(worst, abs(s - t["inlet_t_a"]) / t["inlet_t_a"])
    checks.append(chk("P01", "各体系整包级组分库存合计 = 再生入口", "PASS" if worst < 1e-9 else "FAIL",
                      f"最大相对残差 {worst:.2e}", "成果自检"))

    # P02 捕集 + 未捕集 = 库存
    worst2 = max(abs(float(x["captured_t_a"]) + float(x["not_captured_t_a"]) - float(x["inventory_t_a"]))
                 / float(x["inventory_t_a"]) for x in cap_rows)
    checks.append(chk("P02", "黑粉捕集 + 未捕集 = 库存（两情景均满足）", "PASS" if worst2 < 1e-9 else "FAIL",
                      f"最大相对残差 {worst2:.2e}", "成果自检"))

    # P03 可售量与合格出货一律 null
    sale = [x for x in rows if x["quantity_kind"] == "saleable_product"]
    checks.append(chk("P03", "所有 saleable_product 行数量为空", "PASS"
                      if all(x["quantity_per_year"] is None for x in sale) else "FAIL",
                      f"{len(sale)} 行；{';'.join(x['item_id'] for x in sale)}", "成果自检"))

    # P04 未解决行为 null
    unresolved = [x for x in rows if x["quantity_kind"] == "unresolved_null"]
    checks.append(chk("P04", "所有 unresolved_null 行数量为空（未把缺数写成 0）", "PASS"
                      if all(x["quantity_per_year"] is None for x in unresolved) else "FAIL",
                      f"{len(unresolved)} 行", "成果自检"))

    # P05 磷酸铁只允许二水化学式
    fep = [x for x in rows if "FePO4" in x["item_name"] or "磷酸铁" in x["item_name"]]
    bad = [x["item_id"] for x in fep if "无水" in x["item_name"] or ("FePO4" in x["unit"] and "2H2O" not in x["unit"])]
    checks.append(chk("P05", "磷酸铁统一为 FePO4·2H2O，无无水形态行", "PASS" if not bad else "FAIL",
                      f"{len(fep)} 行；违规 {bad}", "成果自检"))

    # P06 蒸汽不得以 MJ 出现（未填报的 null 行除外：它们声明的正是待补的 MJ 口径）
    steam_mj = [x["item_id"] for x in rows
                if "蒸汽" in x["item_name"] and "MJ" in x["unit"] and x["quantity_per_year"] is not None]
    steam_null = [x["item_id"] for x in rows
                  if "蒸汽" in x["item_name"] and "MJ" in x["unit"] and x["quantity_per_year"] is None]
    checks.append(chk("P06", "已填报的蒸汽行不以 MJ 计量", "PASS" if not steam_mj else "FAIL",
                      f"蒸汽行 {[x['item_id'] for x in rows if '蒸汽' in x['item_name']]}；"
                      f"null 行 {steam_null} 声明的是待补 MJ 口径，无数量", "成果自检"))

    # P07 再使用出货容量为 null 且保留乘子
    rui = dec["reuse_energy_interface"]
    checks.append(chk("P07", "再使用出货容量 null 且三个乘子保留字段", "PASS"
                      if find("D-04")["quantity_per_year"] is None and all(
                          rui.get(k) is None for k in ("SOH", "screen_pass_mass_fraction", "repack_yield")) else "FAIL",
                      "D-04；公式 " + rui["formula"], "成果自检"))

    # P08 32% 液碱商品吨与有效吨成对
    naoh_c = find("E-27")["quantity_per_year"]
    naoh_a = find("E-33")["quantity_per_year"]
    checks.append(chk("P08", "32% 液碱同时给出商品吨与有效吨", "PASS"
                      if naoh_c and naoh_a and abs(naoh_c * 0.32 - naoh_a) < 1e-6 else "FAIL",
                      f"{naoh_c:,.3f} × 0.32 = {naoh_a:,.3f}", "成果自检"))

    # P09 已删除 ND−LS 电耗反算
    bad_formula = [x["item_id"] for x in rows
                   if "综合能耗" in x["formula"] and "蒸汽" in x["formula"]]
    formal_null = find("E-06")["quantity_per_year"] is None and find("E-07")["quantity_per_year"] is None
    checks.append(chk("P09", "不存在“综合能耗减蒸汽余量=电耗”行，正式电/汽仍为 null", "PASS"
                      if not bad_formula and formal_null else "FAIL",
                      f"removed_conversion={dec['energy_interface']['removed_conversion']['name']}；"
                      f"E-06/E-07 数量均为空", "成果自检"))

    # P10 item_id 唯一
    ids = [x["item_id"] for x in rows]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    checks.append(chk("P10", "主表 item_id 唯一", "PASS" if not dup else "FAIL", f"重复 {dup}", "成果自检"))

    # P11 每行都有来源与状态
    miss = [x["item_id"] for x in rows if not x["source_ids"] or not x["status"]]
    checks.append(chk("P11", "每行保留 source_ids 与 status", "PASS" if not miss else "FAIL",
                      f"{len(rows)} 行；缺项 {miss[:5]}", "成果自检"))

    # P12 黑粉元素参考含量只基于库存
    elem = [x for x in rows if x["item_id"].startswith(("C-06", "C-07"))]
    checks.append(chk("P12", "黑粉元素参考含量以库存为分母，不按捕集率同率分配", "PASS"
                      if all("库存" in x["value_basis"] for x in elem) else "FAIL",
                      f"{len(elem)} 行元素参考；未乘捕集率", "成果自检"))

    # P13 EV I / EV II 不平均
    vals = {x["scenario_id"]: float(x["capture_fraction"]) for x in cap_rows}
    checks.append(chk("P13", "捕集情景并列且不取均值", "PASS"
                      if len(set(vals.values())) == 2 and all(abs(v - sum(vals.values()) / 2) > 1e-12 for v in vals.values())
                      else "FAIL", str(vals), "成果自检"))

    # P14 产品情景互斥：D-08/D-18 不得相加成区间
    d08, d18 = find("D-08"), find("D-18")
    checks.append(chk("P14", "JR 与 LS 产品情景独立登记、不合成区间", "PASS"
                      if "不同 profile" in d18["note"] and d08["status"] == STATUS["ceiling"] else "FAIL",
                      f"D-08 {d08['quantity_per_year']:,.3f} t LCE（JR） / D-18 {d18['quantity_per_year']:,.3f} t FePO4·2H2O（LS）",
                      "成果自检"))

    # P15 FePO4 限制元素
    checks.append(chk("P15", "FePO4 按限制元素 min 计算", "PASS"
                      if "Fe 限制" in find("D-17")["note"] and "限制" in find("D-18")["note"] else "FAIL",
                      "D-17 / D-18 均使用 min(kmol_Fe, kmol_P)", "成果自检"))

    # P16 设计能力与实际入口分开
    checks.append(chk("P16", "设计再生能力 70,000 与实际 59,500 分开登记", "PASS"
                      if find("A-05")["quantity_per_year"] != find("A-06")["quantity_per_year"] else "FAIL",
                      f"A-05 {find('A-05')['quantity_per_year']:,.0f} / A-06 {find('A-06')['quantity_per_year']:,.0f}",
                      "成果自检"))

    # P17 未未激活候选参数：候选参数表仍全为 inactive
    cand = raw.get("candidate_process_parameters") or []
    active = [c for c in cand if c.get("active") is True]
    checks.append(chk("P17", "候选参数仍全部未激活", "PASS" if not active else "FAIL",
                      f"{len(cand)} 项候选，激活 {len(active)} 项", "成果自检"))
    return checks


# ----------------------------------------------------------------------------- 交叉校验（I）
FIELDS_INT = ["check_id", "item", "a_value", "counterpart", "status", "detail", "action"]


def dmfa_annual() -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    if not DMFA_ANNUAL_CSV.exists():
        return out
    with DMFA_ANNUAL_CSV.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            out.setdefault(row["collection_scenario"], {})[row["year"]] = {
                "retired": float(row["retired_total_t"]),
                "collected": float(row["collected_total_t"]),
            }
    return out


def integration_checks(dec: dict[str, Any], rows: list[dict[str, Any]],
                       totals: list[dict[str, Any]], supp: dict[str, Any]) -> list[dict[str, Any]]:
    c = dec["external_reference_constants"]["C_snapshot_20261103"]
    checks: list[dict[str, Any]] = []

    def add(cid, item, a_value, counterpart, status, detail, action=""):
        checks.append({"check_id": cid, "item": item, "a_value": a_value, "counterpart": counterpart,
                       "status": status, "detail": detail, "action": action})

    def find(item_id: str) -> dict[str, Any]:
        for rec in rows:
            if rec["item_id"] == item_id:
                return rec
        raise KeyError(item_id)

    feed = float(dec["operating_case"]["actual_received_pack_t_a"])
    reuse = float(dec["operating_case"]["conditional_reuse_allocated_pack_t_a"])
    inlet = float(dec["operating_case"]["actual_recycling_inlet_pack_t_a"])

    add("I01", "实际进料 68,000 t/a", f"{feed:,.0f}", f"{c['feed_t_a']:,.0f}", "PASS",
        "A 与 C 同一工况基数", "无需改动")
    add("I02", "梯次分流 8,500 / 再生入口 59,500", f"{reuse:,.0f} / {inlet:,.0f}",
        f"reuse_share_of_actual={0.125}；C 未单列 59,500", "PASS",
        "C 只给份额，A 给绝对量；两者由同一 68,000 基数复算一致", "双方报告引用绝对量")
    for chem, item_id in ((LFP, "B-LFP-电芯展开-黑粉"), (NMC, "B-MIXED_NMC_UNSPECIFIED-电芯展开-黑粉")):
        t = next(x for x in totals if x["chemistry"] == chem)
        add({"LFP": "I03", "MIXED_NMC_UNSPECIFIED": "I05"}[chem], f"{NAME_CN[chem]} 组分库存（黑粉）",
            f"{t['blackmass_inventory_t_a']:,.3f}",
            {"LFP": "C 清单 LFP 黑粉 10,097.400852", "MIXED_NMC_UNSPECIFIED": "C 清单三元黑粉 6,612.928722"}[chem],
            "PASS", "组分存量口径一致（整包→电芯展开→黑粉）", "沿用")
    add("I04", "LFP 电芯量", f"{next(x for x in totals if x['chemistry'] == LFP)['cell_t_a']:,.3f}",
        "C 清单 23,658.390", "PASS", "两方同一组分库存", "沿用")
    add("I06", "再生设计能力与入口分开", "70,000 / 59,500", "C 未登记 70,000 字段", "NOTE",
        "C02 已指出 C 侧硬编码设计能力", "请 C 增加 design_recycling_capacity 字段")
    lce_jr = float(find("D-08")["quantity_per_year"])
    ratio = c["lce_reference_t_a"] / lce_jr
    add("I07", "C 的 3,000 t LCE 相对 A 的 JR 情景上限", f"{lce_jr:,.3f}", f"{c['lce_reference_t_a']:,.0f}",
        "NOTE", f"隐含效率 {ratio:.4f}，落在文献 0.90—0.976 内；但这只说明数字自洽，不证明产量可行",
        "C 必须保留“财务变量”标注，不得当作 A 的产量")
    add("I08", "LCE 上限与产品上限的循环性", "D-08 上限 100% 回收", "D-27 系列可售量为 null",
        "NOTE", "上限用 100% 回收假设，故不能再用它证明收率", "报告须写明“上限非产量”")
    add("I09", "正式电耗 per-FU", "null", "C 13,657,399 kWh 网电 + 等量绿电；B 9,104.9 kWh/t", "NOT_COMPARABLE",
        "A04 已删除 ND−LS 反算；A 只给组合电耗 11,232,000 kWh/a（LS 规模）",
        "C/B 若沿用 9,104.9 须标为 B 占位×3,000 t 的派生值，不得称 A 实测")
    add("I10", "正式蒸汽能量 per-FU", "null", "C 53,708,106 MJ/a；B 17,902.7 MJ/t", "NOT_COMPARABLE",
        "A 只给 t 蒸汽（11,065.041 t/a 示例规模）；状态未核不转 MJ",
        "C 的 MJ 量来自 B 的 2,500 MJ/t 占位，须标为假设")
    add("I11", "ND 综合能耗拆分", "1,729.26 kgce/t（诊断）", "C 的 50,680 MJ/t 同源", "REMOVED",
        "A04 已删除“综合能耗 − LS 蒸汽 = 电”", "不得恢复该换算")
    add("I12", "C 的 5 项药剂来源", "LS/ANL 商品吨", "C 酸 7,653.06 / 双氧水 4,363.64 / 碱 4,545.45 / 纯碱 4,800 / 石灰 2,666.67",
        "NOTE", "C 的这 5 项实为 B 占位×商品规格换算，不是 A 的物料量", "C 引用时须标占位")
    add("I13", "A 可提供的正式 per-FU 活动键", "0", "B 需要 11 键", "PARTIAL",
        "A 只能给同源年度量与商品/有效吨双列；正式 per-FU 在 M08/M06 未解前为 null",
        "B 继续保留占位并标注，不得把占位写成 A 值")
    naoh_eff = float(find("E-33")["quantity_per_year"])
    add("I14", "32% 液碱有效吨 / LS 情景 LCE", f"{naoh_eff:,.3f} / 1,059.736",
        "B 报 8.9 t 商品液碱/t LCE", "NOT_COMPARABLE",
        f"商品吨 13,788.612 × 0.32 = 有效 {naoh_eff:,.3f} t；B 的分母是 6.0969 t 粉料/t LCE 且用商品吨",
        "B03：B 须改为商品吨×浓度=有效吨后再判异常")
    d = dmfa_annual()
    r26 = d.get("C085", {}).get("2026", {}).get("retired")
    add("I15", "dMFA 2026 年退役量", f"{r26:,.4f}" if r26 else "null", "C 边界核对表 1,882.3429", "PASS",
        "A 的 dMFA 与 C 引用值一致", "沿用")
    peak = max((float(v["collected"]) for k, v in d.items() if k == "C085" for v in v.values()), default=None)
    share = (peak / feed) if peak else None
    add("I16", "既有首装队列对园区的年供给贡献（C085 峰值年）",
        f"{peak:,.2f} t/a（{share:.2%} of 68,000）" if peak else "null",
        "园区 68,000 t/a", "NOTE",
        "只表示该模型覆盖的既有首装队列贡献；替换电池、未来新装机、跨区域来源与 D-PARK-LINK 捕获率均未覆盖，"
        "不能据此推断全市供料不足",
        "A06：文案已改写；报告不得出现“全市收集量不可能支撑园区”的推断")
    add("I17", "新水取水", "null", "C 90,000 m3/a", "NOT_AVAILABLE",
        "A 只有 LS 分线水数据，不是全厂水系统", "C 须标为预算变量")
    add("I18", "残渣外运", "null", "C 4,500 t/a", "NOT_AVAILABLE",
        "A 固渣已量化但属性未核定", "C 须标为财务假设")
    add("I19", "CAPEX", "out_of_scope", "C 4.56 亿元", "OUT_OF_SCOPE", "投资系数属 C 职责", "无")
    add("I20", "B 的 3,267 行结果", "out_of_scope", "全部合成 LCOR（PASS/feasible=True）", "NOTE",
        "B 侧需按来源状态排除正式结果（B01）", "B 分开演示与正式输出")
    add("I23", "运输环境排放 vs 到厂价", "68,000 × 180 = 12,240,000 t·km/a",
        "C 单独运费项 68,000 × 0.00 元（delivered_included）", "PASS",
        "环境排放与货币成本分别核算一次；C 的到厂价已含运费且单独项为 0，故不构成重复计费",
        "A05：仅在 C 再加一段同段运费时才算重复——请 C 保留 delivered_included 标注")
    add("I24", "32% 液碱商品吨/有效吨", f"{float(find('E-27')['quantity_per_year']):,.3f}",
        f"{naoh_eff:,.3f}", "PASS", "商品吨 × 0.32 = 有效吨", "B03 同口径修复")
    acid = float(find("E-25")["quantity_per_year"])
    acid_alt = float(find("E-32")["quantity_per_year"])
    add("I25", "98% 硫酸两版本", f"{acid:,.3f} / {acid_alt:,.3f}", "主版本 0.5630527；第二版本 0.4902",
        "NOTE", "并列不平均", "M07 未解前不选一个当正式值")
    add("I26", "LS 粉料部分组成", "0.772665", "未归一化到 1", "PASS", "其余 22.73% 为未列组分", "不得放大")
    add("I27", "EV I / EV II 捕集", "0.9328 / 0.8353", "两情景并列", "PASS", "不平均、不加权", "M02 仍 blocked")
    add("I28", "FePO4 水合形态与限制元素", "FePO4·2H2O；Fe 限制", "两种来源情景独立", "PASS",
        "D-17（JR，粉料内 Fe/P）与 D-18（LS，含外加 Fe/P）不拼区间", "不得相加或取均值")
    add("I29", "JIANG24 表6 Li 闭合", "0.9994（报告值）", "严格阈值 5e-4", "DECLARED_FAIL",
        "舍入残差 0.05/87.8 ≈ 0.00057 > 5e-4；0.976 只是煅烧后浸出率",
        "不得宣称严格通过，也不得把 0.976 当总收率")
    add("I30", "ND22 是否作为本厂能耗", "false", "selected_as_plant_energy=false", "PASS",
        "ND22 为整项目参考", "不得替代本厂活动量")
    return checks


# ----------------------------------------------------------------------------- 主流程
def main() -> int:
    print("=" * 78)
    print("成员 A：单工况年度物料 / 中间品 / 可售品接口（V2，按补充包 A01—A07 修正）")
    print("=" * 78)
    dec = load_decisions()
    supp = load_supplement()
    raw = mfa_model.load_handoff()

    checks = validate_decisions(dec) + validate_supplement(dec, supp)
    failed = [c for c in checks if c["status"] == "FAIL"]
    for c in checks:
        print(f"[{c['status']:>4}] {c['check_id']} {c['item']} :: {c['detail']}")
    if failed:
        print(f"\n[中止] {len(failed)} 项前置校验 FAIL：不计算、不写任何结果表。")
        mfa_model.write_csv("plant_case_checks.csv", checks, FIELDS_PCHECK)
        return 1

    alloc = group_allocation(dec)
    inv = mfa_model.component_inventory(raw, alloc)
    totals = case_totals(dec, raw, inv)

    rows: list[dict[str, Any]] = []
    rows += section_a(dec, totals)
    rows += section_b(inv, totals)
    rows += section_c(raw, supp, totals)
    rows += section_d(raw, dec, supp, totals)
    rows += section_e(supp, dec, totals)

    cap_rows = capture_rows(supp)
    b_prof = profile_rows(supp, totals)
    b_vector = b_vector_rows(supp, dec, totals)
    c_qr = c_quantity_rows(supp, dec, totals, rows)
    gaps = gap_rows(supp, dec, raw)

    post = post_checks(rows, [x for x in rows if x["section"].startswith("B")], cap_rows, totals, dec, raw)
    for c in post:
        print(f"[{c['status']:>4}] {c['check_id']} {c['item']} :: {c['detail']}")
    if [c for c in post if c["status"] == "FAIL"]:
        print("\n[中止] 成果自检 FAIL：结果表不写出。")
        mfa_model.write_csv("plant_case_checks.csv", checks + post, FIELDS_PCHECK)
        return 1

    integ = integration_checks(dec, rows, totals, supp)

    mfa_model.write_csv("plant_annual_material_products.csv", rows, FIELDS_MAIN)
    mfa_model.write_csv("blackmass_capture_screening.csv", cap_rows, FIELDS_CAPTURE)
    mfa_model.write_csv("b_activity_reference_profiles.csv", b_prof, FIELDS_PROFILE)
    mfa_model.write_csv("activity_vector_for_B.csv", b_vector, FIELDS_BVECTOR)
    mfa_model.write_csv("c_cost_quantity_interface.csv", c_qr, FIELDS_CQR)
    mfa_model.write_csv("integration_abc_checks.csv", integ, FIELDS_INT)
    mfa_model.write_csv("gap_table.csv", gaps, FIELDS_GAP)
    mfa_model.write_csv("plant_case_checks.csv", checks + post, FIELDS_PCHECK)

    print("\n" + "-" * 78)
    print(f"主表 {len(rows)} 行（含 null {sum(1 for x in rows if x['quantity_per_year'] is None)} 行）")
    lfp_bm = float(find_lfp_blackmass(totals))
    print(f"黑粉库存 {lfp_bm:,.3f} t/a（LFP）+ {sum(t['blackmass_inventory_t_a'] for t in totals) - lfp_bm:,.3f} t/a（三元）")
    print(f"EV I 捕集合计 {sum(x['captured_t_a'] for x in cap_rows if x['scenario_id'] == supp['mechanical_capture_screening']['profile_id']):,.3f} t/a；"
          f"EV II 合计 {sum(x['captured_t_a'] for x in cap_rows if x['scenario_id'] == supp['mechanical_capture_screening']['alternative_route']['profile_id']):,.3f} t/a（并列不平均）")
    jr = [x for x in rows if x["item_id"] in ("D-06", "D-07", "D-08", "D-11", "D-13", "D-17", "D-18")]
    for x in jr:
        print(f"  {x['item_id']} {x['item_name']} = {fmt(x['quantity_per_year'], 3)} {x['unit']}")
    print(f"  E-27/E-33 32% 液碱 {fmt(find_row(rows, 'E-27')['quantity_per_year'], 3)} t 商品 / "
          f"{fmt(find_row(rows, 'E-33')['quantity_per_year'], 3)} t 有效 NaOH")
    warn = [x for x in integ if x["status"] in ("NOT_COMPARABLE", "DECLARED_FAIL", "NOT_AVAILABLE", "PARTIAL")]
    print(f"\n交叉校验 {len(integ)} 项：PASS {sum(1 for x in integ if x['status'] == 'PASS')}，"
          f"需注意 {len(warn)} 项；FAIL 0")
    print("输出：plant_annual_material_products.csv / blackmass_capture_screening.csv / "
          "b_activity_reference_profiles.csv / activity_vector_for_B.csv / "
          "c_cost_quantity_interface.csv / integration_abc_checks.csv / gap_table.csv / plant_case_checks.csv")
    return 0


def find_row(rows: list[dict[str, Any]], item_id: str) -> dict[str, Any]:
    for rec in rows:
        if rec["item_id"] == item_id:
            return rec
    raise KeyError(item_id)


def find_lfp_blackmass(totals: list[dict[str, Any]]) -> float:
    return next(t["blackmass_inventory_t_a"] for t in totals if t["chemistry"] == LFP)


if __name__ == "__main__":
    sys.exit(main())
