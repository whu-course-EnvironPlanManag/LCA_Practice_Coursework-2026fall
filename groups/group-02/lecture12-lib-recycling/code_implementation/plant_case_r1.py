#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lecture12 案例三（锂离子电池回收）· 成员 A：R1 背景情景（2026-11-04）年度接口。

本脚本是 plant_case.py（59,500 t/a 原情景）的**并列第二情景**，二者不覆盖、不取平均：
    - 分流：新增 q=0.90 / y=0.97 / SOH=0.80，梯次弃用回流使再生入口由 59,500 → 60,579.50 t/a
    - 后续 LFP/三元/能耗/梯次量均随 R1 口径重算

数据入口（全部只读）：
    data_cohort/a_group_r1_scenario_20261104.json   R1 快照（automatically_adopted=false）
    data_cohort/a_group_decisions.json              组内决策（复用快照登记纪律）

纪律（与 decisions.scenario_r1_registry.not_adopted 一致）：
    - 缺数保持 null 不补 0；湿产品与折干纯物质量是同一物流不同表述，不重复计产量/收入；
    - 0.50 是 t 总粉/t 电芯产率，不是黑粉捕集率（M02_ACTUAL 仍缺失）；
    - 粗碳酸锂/磷酸铁渣/元素回收量不是合格电池级成品（GAP-LCE-SALE 仍缺失）；
    - 硫酸主/备选不平均、蒸汽热态未知不转 MJ、622/811 是技术端点不是本地拆分。

输出（data_cohort/，带 r1 前缀，禁止手改）：
    plant_r1_scenario_products.csv    R1 分流 + LFP 主物料 + 粉料元素 + 药剂 + NMC + 能耗 + 梯次长表
    plant_r1_scenario_checks.csv      R1 情景自检（fail-fast：任一 FAIL 不写结果表）

运行：python code_implementation/plant_case_r1.py
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
DECISIONS_JSON = DATA_DIR / "a_group_decisions.json"

sys.path.insert(0, str(CODE_DIR))
import mfa_model  # noqa: E402  复用 write_csv（utf-8-sig、None 写空单元格）

LFP = "LFP"
NMC = "MIXED_NMC_UNSPECIFIED"

FIELDS_R1 = ["item_id", "block", "item_name", "chemistry", "quantity_kind",
             "quantity_per_year", "unit", "value_basis", "attribute", "status",
             "formula", "source", "note"]
FIELDS_CHK = ["check_id", "item", "status", "detail"]

ATTR = {"group": "组内设定", "lit": "文献原值", "transfer": "文献迁移",
        "scenario": "情景假设", "none": "无"}

KIND = {
    "capacity": "capacity",
    "input": "input_allocation",
    "intermediate": "recovered_intermediate",
    "ceiling": "reference_material_ceiling",
    "scenario_value": "scenario_value",
    "loss": "element_loss_stream",
    "diag": "diagnostic",
    "null": "null_missing",
}

LOSS_STREAM_LABELS = [
    ("leaching_residue", "浸出渣（磷铁富渣）夹带 Li"),
    ("wastewater", "洗涤废水 Li"),
    ("carbon_residue", "负极碳渣/滤渣夹带 Li"),
    ("other_unlocated", "其他未定位损耗 Li"),
]


def load_r1(path: Path = R1_JSON) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"未找到 R1 快照：{path}")
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def load_decisions(path: Path = DECISIONS_JSON) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def near(a: float, b: float, rel: float = 1e-4, abs_tol: float = 0.05) -> bool:
    return abs(a - b) <= max(abs_tol, abs(b) * rel)


def li_loss_streams(li: dict[str, Any]) -> list[dict[str, Any]]:
    """把 loss_Li_t_a 按 loss_split_fraction_of_loss 拆成四个命名 Li 损耗流股。"""
    fracs = li["loss_split_fraction_of_loss"]
    total = float(li["loss_Li_t_a"])
    out = []
    for key, label in LOSS_STREAM_LABELS:
        frac = float(fracs[key])
        out.append({"key": key, "label": label, "fraction": frac,
                    "mass_t_a": round(total * frac, 6)})
    return out


def checks(r1: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    s = r1["reuse_recycling_split"]
    l = r1["LFP_native_process_LS23"]
    p = r1["powder_assay_received_basis"]
    li = r1["LFP_Li_balance"]
    n = r1["NMC_element_recovery_ANL19"]
    ru = r1["reuse_test_capacity"]
    d = r1["dmfa_future_2026_2040"]

    def add(cid, item, ok, detail):
        out.append({"check_id": cid, "item": item,
                    "status": "PASS" if ok else "FAIL", "detail": detail})

    add("R1-S01", "梯次保留=8500·q·y",
        near(s["reuse_retained_pack_equiv_t_a"], 8500 * s["screen_pass_mass_fraction_q"] * s["repack_yield_y"]),
        f"8500×{s['screen_pass_mass_fraction_q']}×{s['repack_yield_y']}={8500 * s['screen_pass_mass_fraction_q'] * s['repack_yield_y']:.4f}")
    add("R1-S02", "弃用回流守恒 850+229.5=8500−7420.5",
        near(s["screen_reject_to_recycling_t_a"] + s["repack_reject_to_recycling_t_a"] + s["reuse_retained_pack_equiv_t_a"], s["reuse_candidate_pack_t_a"]),
        f"{s['screen_reject_to_recycling_t_a']}+{s['repack_reject_to_recycling_t_a']}+{s['reuse_retained_pack_equiv_t_a']}={s['reuse_candidate_pack_t_a']}")
    add("R1-S03", "再生=68000−保留",
        near(s["recycling_pack_equiv_t_a"], 68000 - s["reuse_retained_pack_equiv_t_a"]),
        f"68000−{s['reuse_retained_pack_equiv_t_a']}={68000 - s['reuse_retained_pack_equiv_t_a']:.4f}")
    add("R1-S04", "再生分体系=总×份额",
        near(s["recycling_LFP_t_a"], s["recycling_pack_equiv_t_a"] * 0.6) and near(s["recycling_NMC_t_a"], s["recycling_pack_equiv_t_a"] * 0.4),
        f"LFP {s['recycling_LFP_t_a']:.4f} / NMC {s['recycling_NMC_t_a']:.4f}")
    add("R1-L01", "LFP 电芯=再生LFP×0.6627",
        near(l["cell_t_a"], s["recycling_LFP_t_a"] * l["pack_to_cell_fraction"]),
        f"36347.70×0.6627={s['recycling_LFP_t_a'] * l['pack_to_cell_fraction']:.4f}")
    add("R1-L02", "粉料=电芯×0.50",
        near(l["powder_t_a"], l["cell_t_a"] * 0.50),
        f"24087.62×0.50={l['cell_t_a'] * 0.50:.4f}")
    add("R1-L03", "粗锂折干纯=湿×0.80×0.99",
        near(l["products"]["crude_Li2CO3_dry_pure_t_a"], l["products"]["crude_Li2CO3_wet_t_a"] * 0.80 * 0.99),
        f"{l['products']['crude_Li2CO3_wet_t_a']}×0.80×0.99={l['products']['crude_Li2CO3_wet_t_a'] * 0.80 * 0.99:.4f}")
    add("R1-L04", "磷酸铁渣折干纯=湿×0.60×0.99",
        near(l["products"]["fepo4_slag_dry_pure_t_a"], l["products"]["fepo4_slag_wet_t_a"] * 0.60 * 0.99),
        f"{l['products']['fepo4_slag_wet_t_a']}×0.60×0.99={l['products']['fepo4_slag_wet_t_a'] * 0.60 * 0.99:.4f}")
    add("R1-L05", "粉料 Li 输入=粉料×0.024155",
        near(li["powder_Li_input_t_a"], l["powder_t_a"] * p["Li_mass_fraction"]),
        f"{l['powder_t_a']}×{p['Li_mass_fraction']}={l['powder_t_a'] * p['Li_mass_fraction']:.4f}")

    li_streams = li_loss_streams(li)
    loss_sum = sum(x["mass_t_a"] for x in li_streams)
    out_li = float(li["crude_Li2CO3_Li_t_a"]) + loss_sum
    bal = mfa_model.li_balance_check(float(li["powder_Li_input_t_a"]), out_li)
    add("R1-L06", "损耗=输入−粗锂",
        near(float(li["loss_Li_t_a"]), float(li["powder_Li_input_t_a"]) - float(li["crude_Li2CO3_Li_t_a"])),
        f"{li['powder_Li_input_t_a']}−{li['crude_Li2CO3_Li_t_a']}={li['powder_Li_input_t_a'] - li['crude_Li2CO3_Li_t_a']:.5f}")
    add("R1-L07", "损耗拆分比例之和=1",
        near(sum(x["fraction"] for x in li_streams), 1.0, abs_tol=1e-9),
        f"Σ={sum(x['fraction'] for x in li_streams):.12f}")
    add("R1-L08", "Li 元素守恒闭合（mfa_model 判据 pass）",
        bal["status"] == "pass",
        f"out={out_li:.5f} vs in={li['powder_Li_input_t_a']:.5f}，rel={bal['relative_error']:.2e}")
    add("R1-N01", "三元电芯=再生NMC×0.63466",
        near(n["cell_t_a"], s["recycling_NMC_t_a"] * n["pack_to_cell_fraction"]),
        f"24231.80×0.63466={s['recycling_NMC_t_a'] * n['pack_to_cell_fraction']:.4f}")
    add("R1-E01", "测试电耗=8500×118×(8.72/11.4)",
        near(ru["test_electricity_kwh_a"], 8500 * 118 * (8.72 / 11.4)),
        f"8500×118×(8.72/11.4)={8500 * 118 * (8.72 / 11.4):.4f}")
    add("R1-E02", "交付容量=7420.5×118×0.80",
        near(ru["deliver_usable_kwh_a"], 7420.5 * 118 * 0.80),
        f"7420.5×118×0.80={7420.5 * 118 * 0.80:.4f}")
    add("R1-D01", "未来 LFP+三元份额=1",
        near(d["future_LFP_share"] + d["future_NMC_share"], 1.0, abs_tol=1e-9),
        f"{d['future_LFP_share']}+{d['future_NMC_share']}={d['future_LFP_share'] + d['future_NMC_share']:.12f}")
    add("R1-D02", "2026 首装合计=2025×(1+0.05)",
        near(d["annual_inflow_t_pack_a_rows"][0]["LFP_first"] + d["annual_inflow_t_pack_a_rows"][0]["NMC_first"],
             d["base_year_2025_install_t_a"] * 1.05),
        "增长率 5%/a 与首年流入一致")
    return out


def rows(r1: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    s = r1["reuse_recycling_split"]
    l = r1["LFP_native_process_LS23"]
    p = r1["powder_assay_received_basis"]
    li = r1["LFP_Li_balance"]
    n = r1["NMC_element_recovery_ANL19"]
    e = r1["energy_water"]
    ru = r1["reuse_test_capacity"]

    def add(item_id, block, name, chem, kind, qty, unit, basis, attr, status, formula, src, note):
        out.append({"item_id": item_id, "block": block, "item_name": name, "chemistry": chem,
                    "quantity_kind": kind, "quantity_per_year": qty, "unit": unit,
                    "value_basis": basis, "attribute": attr, "status": status,
                    "formula": formula, "source": src, "note": note})

    add("S-01", "SPLIT", "梯次候选来料（整包当量）", None, KIND["input"], 8500.0, "t_pack/a",
        "整包质量", ATTR["group"], "conditional_group_assumption", "10000×0.85", "组内设定", "")
    add("S-02", "SPLIT", "梯次筛选通过率 q", None, KIND["scenario_value"], 0.90, "1",
        "候选旧电池整包当量", ATTR["scenario"], "scenario_assumption", "情景假设", "无本园区实测", "")
    add("S-03", "SPLIT", "重组保留比例 y", None, KIND["scenario_value"], 0.97, "1",
        "通过筛选旧电池整包当量", ATTR["scenario"], "scenario_assumption", "情景假设", "无本园区实测", "")
    add("S-04", "SPLIT", "保留电池平均 SOH", None, KIND["scenario_value"], 0.80, "1",
        "容量情景", ATTR["scenario"], "scenario_assumption", "容量情景非筛选合格率", "无本园区实测", "")
    add("S-05", "SPLIT", "筛选弃用并返回再生", None, KIND["input"], 850.0, "t_pack/a",
        "整包当量", ATTR["scenario"], "scenario_value", "8500×(1−q)", "情景假设", "返回再生线")
    add("S-06", "SPLIT", "重组弃用并返回再生", None, KIND["input"], 229.5, "t_pack/a",
        "整包当量", ATTR["scenario"], "scenario_value", "8500×q×(1−y)", "情景假设", "返回再生线")
    add("S-07", "SPLIT", "梯次保留旧电池整包当量", None, KIND["intermediate"], s["reuse_retained_pack_equiv_t_a"], "t_pack/a",
        "整包当量（非重组后成品质量）", ATTR["scenario"], "scenario_value", "8500×q×y", "情景假设", "不是加壳重组后成品质量")
    add("S-08", "SPLIT", "再生整包当量", None, KIND["input"], s["recycling_pack_equiv_t_a"], "t_pack/a",
        "整包质量", ATTR["transfer"], "scenario_value", "68000−保留", "文献迁移", "R1 口径")
    add("S-09", "SPLIT", "再生整包当量 LFP", LFP, KIND["input"], s["recycling_LFP_t_a"], "t_pack/a",
        "整包质量", ATTR["group"], "scenario_value", "60579.5×0.60", "组内设定", "")
    add("S-10", "SPLIT", "再生整包当量 未细分三元", NMC, KIND["input"], s["recycling_NMC_t_a"], "t_pack/a",
        "整包质量", ATTR["group"], "scenario_value", "60579.5×0.40", "组内设定", "")

    add("LP-01", "LFP_MAIN", "LFP 电芯（拆解后）", LFP, KIND["input"], l["cell_t_a"], "t_cell/a",
        "整包×0.6627", ATTR["lit"], "literature_transfer", "36347.70×0.6627", "LS23 表3.4-3 比例代理（湖南金瑞）", "整包到电芯比例来自金瑞，电芯之后来自朗赛")
    add("LP-02", "LFP_MAIN", "LFP 粉料（总粉）", LFP, KIND["input"], l["powder_t_a"], "t_powder/a",
        "电芯×0.50", ATTR["lit"], "literature_transfer", "24087.62×0.50", "LS23 原生粉产率", "0.50 是 t总粉/t电芯产率，不是黑粉捕集效率")
    add("LP-03", "LFP_MAIN", "粗 Li2CO3（湿产品）", LFP, KIND["intermediate"], l["products"]["crude_Li2CO3_wet_t_a"], "t/a",
        "湿基", ATTR["transfer"], "recovered_intermediate", "迁移", "LS23 表3.4-1", "水分 0.20、干基纯度 0.99；非合格电池级成品")
    add("LP-04", "LFP_MAIN", "粗 Li2CO3 折干纯", LFP, KIND["intermediate"], l["products"]["crude_Li2CO3_dry_pure_t_a"], "t/a",
        "干基", ATTR["transfer"], "recovered_intermediate", "湿×0.80×0.99", "LS23 表3.4-1", "与 LP-03 同一物流不同表述，不重复计产量/收入")
    add("LP-05", "LFP_MAIN", "FePO4 渣（湿产品）", LFP, KIND["intermediate"], l["products"]["fepo4_slag_wet_t_a"], "t/a",
        "湿基", ATTR["transfer"], "recovered_intermediate", "迁移", "LS23 表3.4-1", "水分 0.40、干基纯度 0.99；非电池级磷酸铁")
    add("LP-06", "LFP_MAIN", "FePO4 渣折干纯", LFP, KIND["intermediate"], l["products"]["fepo4_slag_dry_pure_t_a"], "t/a",
        "干基", ATTR["transfer"], "recovered_intermediate", "湿×0.60×0.99", "LS23 表3.4-1", "与 LP-05 同一物流不同表述")
    add("LP-07", "LFP_MAIN", "铜箔产品", LFP, KIND["intermediate"], l["products"]["cu_foil_t_a"], "t/a",
        "Cu 质量分数 0.97", ATTR["transfer"], "recovered_intermediate", "迁移", "LS23 表3.4-1", "")
    add("LP-08", "LFP_MAIN", "铝箔产品", LFP, KIND["intermediate"], l["products"]["al_foil_t_a"], "t/a",
        "Al 质量分数 0.97", ATTR["transfer"], "recovered_intermediate", "迁移", "LS23 表3.4-1", "")

    add("AS-01", "LFP_ASSAY", "粉料水分", LFP, KIND["scenario_value"], p["moisture"], "1",
        "收到基", ATTR["lit"], "literature_value", "原值 2.15%", "LS23 表3.5-4", "")
    add("AS-02", "LFP_ASSAY", "粉料元素 C 质量分数", LFP, KIND["scenario_value"], p["C_mass_fraction"], "1",
        "元素干湿基未明确", ATTR["lit"], "literature_value", "原值 45.5370%", "LS23 表3.5-4", "")
    add("AS-03", "LFP_ASSAY", "粉料元素 Li 质量分数", LFP, KIND["scenario_value"], p["Li_mass_fraction"], "1",
        "按收到基解释", ATTR["lit"], "literature_value", "原值 2.4155%", "LS23 表3.5-4", "本情景按收到基，不扣水不归一化")
    add("AS-04", "LFP_ASSAY", "粉料元素 F 质量分数", LFP, KIND["scenario_value"], p["F_mass_fraction"], "1",
        "由 11.726 t F/5000 t 粉反推", ATTR["transfer"], "literature_value", "元素平衡推导", "LS23 表4.2-3/印刷页132", "不与他项合称同份化验")
    add("AS-05", "LFP_ASSAY", "湿法粉料胶黏剂残留", LFP, KIND["null"], None, "1",
        "无", ATTR["none"], "null_missing", "", "", "电芯入口胶黏剂含量不能代替粉中残留")

    add("LI-01", "LFP_LI", "粉料 Li 输入", LFP, KIND["scenario_value"], li["powder_Li_input_t_a"], "t元素Li/a",
        "粉料×0.024155", ATTR["transfer"], "scenario_value", "12043.81×0.024155", "LS23 表3.5-4", "")
    add("LI-02", "LFP_LI", "粗碳酸锂中 Li", LFP, KIND["scenario_value"], li["crude_Li2CO3_Li_t_a"], "t元素Li/a",
        "干纯 Li2CO3×0.187843", ATTR["transfer"], "scenario_value", "迁移", "LS23", "")
    for i, x in enumerate(li_loss_streams(li), start=3):
        add(f"LI-0{i}", "LFP_LI", x["label"], LFP, KIND["loss"], x["mass_t_a"], "t元素Li/a",
            f"损耗×{x['fraction']}", ATTR["scenario"], "scenario_loss_assumption",
            f"36.37110×{x['fraction']}", "本研究占位拆分", "损耗比例是显式标注的情景假设，非实测损耗分布")

    add("RG-01", "LFP_REAGENT", "98% 硫酸（主情景）", LFP, KIND["scenario_value"], l["reagents"]["h2so4_98_main_t_commercial_a"], "t商品/a",
        "0.5630527 t商品/t粉", ATTR["transfer"], "scenario_value", "迁移", "LS23 表3.5-1", "与 RG-02 并列不平均")
    add("RG-02", "LFP_REAGENT", "98% 硫酸（独立备选）", LFP, KIND["scenario_value"], l["reagents"]["h2so4_98_alt_t_commercial_a"], "t商品/a",
        "0.4902 t商品/t粉", ATTR["transfer"], "scenario_value", "迁移", "LS23 §4.3.1.2", "与 RG-01 并列不平均；仅适用该 LFP 粉料路线")
    add("RG-03", "LFP_REAGENT", "32% 液碱（预处理+湿法合计）", LFP, KIND["scenario_value"], l["reagents"]["naoh_32_t_commercial_a"], "t商品/a",
        "商品吨", ATTR["transfer"], "scenario_value", "迁移", "LS23 表3.5-1", "商品吨与有效吨须成对")
    add("RG-04", "LFP_REAGENT", "92% 氧化钙（合计）", LFP, KIND["scenario_value"], l["reagents"]["cao_92_t_commercial_a"], "t商品/a",
        "商品吨", ATTR["transfer"], "scenario_value", "迁移", "LS23 表3.5-1", "")
    add("RG-05", "LFP_REAGENT", "85% 磷酸", LFP, KIND["scenario_value"], l["reagents"]["h3po4_85_t_commercial_a"], "t商品/a",
        "商品吨", ATTR["transfer"], "scenario_value", "迁移", "LS23 表3.5-1", "")
    add("RG-06", "LFP_REAGENT", "99% 铁粉", LFP, KIND["scenario_value"], l["reagents"]["fe_powder_99_t_commercial_a"], "t商品/a",
        "商品吨", ATTR["transfer"], "scenario_value", "迁移", "LS23 表3.5-1", "")

    for scen in ("NMC622", "NMC811"):
        d = n[scen]
        add(f"NC-{scen}-01", "NMC", "三元电芯（拆解后）", NMC, KIND["input"], n["cell_t_a"], "t_cell/a",
            "整包×0.63466", ATTR["lit"], "literature_transfer", "24231.80×0.63466", "JR23 比例 + ANL19 组成", "两技术端点情景共用同一电芯量")
        add(f"NC-{scen}-02", "NMC", f"纯 Li2CO3 当量（{scen}）", NMC, KIND["ceiling"], d["pure_Li2CO3_equiv_t_a"], "t/a",
            "正极 Li 回收后折算", ATTR["transfer"], "reference_material_ceiling", "Li回收×M_LCE/2M_Li", "ANL19 Table 4/12", "理论当量，不等于合格商品盐产量")
        add(f"NC-{scen}-03", "NMC", f"回收 Ni（{scen}）", NMC, KIND["ceiling"], d["recovered_Ni_t_a"], "t元素/a",
            "元素基", ATTR["transfer"], "reference_material_ceiling", "电芯×wNi×0.98", "ANL19 Table 4/12", "")
        add(f"NC-{scen}-04", "NMC", f"回收 Co（{scen}）", NMC, KIND["ceiling"], d["recovered_Co_t_a"], "t元素/a",
            "元素基", ATTR["transfer"], "reference_material_ceiling", "电芯×wCo×0.98", "ANL19 Table 4/12", "")
        add(f"NC-{scen}-05", "NMC", f"回收 Mn（{scen}）", NMC, KIND["ceiling"], d["recovered_Mn_t_a"], "t元素/a",
            "元素基", ATTR["transfer"], "reference_material_ceiling", "电芯×wMn×0.98", "ANL19 Table 4/12", "")
        add(f"NC-{scen}-06", "NMC", f"回收 Cu（{scen}）", NMC, KIND["ceiling"], d["recovered_Cu_t_a"], "t元素/a",
            "元素基", ATTR["transfer"], "reference_material_ceiling", "电芯×wCu×0.90", "ANL19 Table 4/12", "")
        add(f"NC-{scen}-07", "NMC", f"回收 Al（{scen}）", NMC, KIND["ceiling"], d["recovered_Al_t_a"], "t元素/a",
            "元素基", ATTR["transfer"], "reference_material_ceiling", "电芯×wAl×0.90", "ANL19 Table 4/12", "")
        add(f"NC-{scen}-08", "NMC", f"沉锂模块 Na2CO3 商品（{scen}）", NMC, KIND["scenario_value"], d["na2co3_commercial_t_a"], "t商品/a",
            "碳酸根全由 Na2CO3 提供", ATTR["scenario"], "scenario_value", "纯LCE×105.988/73.888×1.10/0.99", "新增反应模块", "替换原碳酸钠项，不重复添加，并同步核算新增钠与水")

    add("EN-01", "ENERGY", "LFP 组合电耗（α=0.50 分摊）", LFP, KIND["diag"], e["LFP_combined_electricity_kwh_a"], "kWh/a",
        "11,232,000×分摊", ATTR["scenario"], "diagnostic", "11,232,000×[0.5×电芯/10000+0.5×粉料/10000]", "LS23 表3.5-1", "α=0.50 分摊假设；α=0/1 对应 13.53/27.06 GWh/a")
    add("EN-02", "ENERGY", "LFP 湿法蒸汽（质量）", LFP, KIND["diag"], e["LFP_steam_t_a"], "t蒸汽/a",
        "蒸汽质量", ATTR["transfer"], "diagnostic", "迁移", "LS23 表3.5-1", "热态及返凝未知，不转 MJ")
    add("EN-03", "ENERGY", "LFP 预处理天然气", LFP, KIND["diag"], e["LFP_ng_nm3_a"], "Nm³/a",
        "体积", ATTR["transfer"], "diagnostic", "迁移", "LS23 预处理清单", "不折 MJ")
    add("EN-04", "ENERGY", "LFP 已列分线自来水补水", LFP, KIND["diag"], e["LFP_tap_water_m3_a"], "m³/a",
        "分线", ATTR["transfer"], "diagnostic", "迁移", "LS23 §4.2.8.1", "不含共享生活/检验用水")
    add("EN-05", "ENERGY", "LFP 外供纯水", LFP, KIND["diag"], e["LFP_external_pure_water_m3_a"], "m³/a",
        "分列", ATTR["transfer"], "diagnostic", "迁移", "LS23 §4.2.8.1", "与自来水分列")
    add("EN-06", "ENERGY", "LFP 已列相关排口废水小计", LFP, KIND["diag"], e["LFP_listed_wastewater_m3_a"], "m³/a",
        "分列", ATTR["transfer"], "diagnostic", "迁移", "LS23 §4.2.8.1", "非全厂完整外排量")
    add("EN-07", "ENERGY", "三元 ANL 文献电耗代理", NMC, KIND["diag"], e["NMC_electricity_proxy_kwh_a"], "kWh/a",
        "0.125 MJ/kg 退役电芯年化", ATTR["transfer"], "diagnostic", "迁移", "ANL19 Table 10", "尚未复现 EverBatt 完整规模模型")
    add("EN-08", "ENERGY", "三元 ANL 过程用水代理", NMC, KIND["diag"], e["NMC_water_proxy_m3_a"], "m³/a",
        "1 US gal/kg 退役电芯年化", ATTR["transfer"], "diagnostic", "迁移", "ANL19 Table 10", "")
    add("EN-09", "ENERGY", "全厂完整能耗/水平衡", None, KIND["null"], None, "-",
        "无", ATTR["none"], "null_missing", "", "", "各分线量不相加后宣称全厂完整能耗/水平衡")

    add("RU-01", "REUSE", "梯次测试电耗", None, KIND["diag"], ru["test_electricity_kwh_a"], "kWh/a",
        "8500×118×(8.72/11.4)", ATTR["transfer"], "diagnostic", "8500×118×(8.72/11.4)", "JRC Table 7/10", "仅覆盖测试活动，不代表完整梯次工厂能耗")
    add("RU-02", "REUSE", "梯次交付可用容量", None, KIND["intermediate"], ru["deliver_usable_kwh_a"], "kWh/a",
        "7420.5×118×0.80", ATTR["scenario"], "scenario_value", "7420.5×118×0.80", "SOH=0.80 情景", "当年交付可用容量，非年度供电量")
    return out


def main() -> int:
    print("=" * 78)
    print("成员 A：R1 背景情景（2026-11-04）年度接口 —— 与 59,500 t/a 原情景并列")
    print("=" * 78)
    r1 = load_r1()
    load_decisions()  # 仅确认决策文件存在与可解析

    chk = checks(r1)
    for c in chk:
        print(f"[{c['status']:>4}] {c['check_id']} {c['item']} :: {c['detail']}")
    failed = [c for c in chk if c["status"] == "FAIL"]
    if failed:
        print(f"\n[中止] {len(failed)} 项 R1 情景自检 FAIL：不写结果表。")
        mfa_model.write_csv("plant_r1_scenario_checks.csv", chk, FIELDS_CHK)
        return 1

    recs = rows(r1)
    mfa_model.write_csv("plant_r1_scenario_checks.csv", chk, FIELDS_CHK)
    mfa_model.write_csv("plant_r1_scenario_products.csv", recs, FIELDS_R1)

    null_n = sum(1 for x in recs if x["quantity_per_year"] is None)
    by_block: dict[str, int] = {}
    for x in recs:
        by_block[x["block"]] = by_block.get(x["block"], 0) + 1
    print("\n" + "-" * 78)
    print(f"R1 长表 {len(recs)} 行（含 null {null_n} 行）；分块 {by_block}")
    print("输出：plant_r1_scenario_products.csv / plant_r1_scenario_checks.csv")
    print("纪律：q/y/SOH/α 为情景假设；0.50 非捕集率；粗品/元素量非合格商品；622/811 非本地拆分；蒸汽不转 MJ")
    return 0


if __name__ == "__main__":
    sys.exit(main())