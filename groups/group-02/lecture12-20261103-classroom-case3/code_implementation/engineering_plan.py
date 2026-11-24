#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lecture12 案例三（锂离子电池回收）成员 A 中期建模：功能分区与重点工程清单骨架。

职责边界：
    1. 只搭建“园区功能分区 + 五项以上重点工程”的结构与因果接口；
    2. 设计规模、设备台数、CAPEX/OPEX 一律不产出数值：规模受 M01/M02/M09 阻断，
       投资受 M12 阻断（属成员 C 职责），本脚本只输出 null + 阻断编号；
    3. 边界声明：仅回收园区，不汇总邦普时代正极材料与邦普宜化配套原料（见 case_definition）。

AI 辅助说明：
    提示词摘要：“按 A 组分工要求生成工程-01 至工程-06 的项目清单与功能分区骨架，字段包含
    工序衔接、关键设备、设计规模、投资与缺失输入；所有数值为空并以 null 输出”。
    人工复核：需成员 A 与成员 C 共同确认工程边界与投资口径。

运行：python code_implementation/engineering_plan.py
输出：data_cohort/engineering_project_catalog.csv、functional_zones.csv、capacity_interfaces.csv
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mfa_model import (  # noqa: E402  同目录复用校验与闸门逻辑
    WORKDIR,
    load_handoff,
    module_readiness,
    validate_dataset,
    write_csv,
    fmt,
)

FUNCTIONAL_ZONES = (
    {
        "zone_id": "Z1", "name": "来料接收与暂存区",
        "function": "退役整包接收、称重登记、外观与绝缘检测、放电前分区暂存",
        "layout_requirement": "布置于园区主导风向下风向、靠近厂界物流门；暂存区独立防火分区，"
                              "与其他功能区之间留置安全缓冲；电池不露天存放（R08-1）",
        "safety_buffer_note": "与拆解区、成品区的防火间距按现行《建筑设计防火规范》核定，"
                              "本阶段不填数值（土建参数未定）",
        "area_m2": None, "capacity_t_a": None,
        "missing_input_ids": "M01;M02;M09",
        "status": "not_ready_numeric",
    },
    {
        "zone_id": "Z2", "name": "放电与智能拆解区",
        "function": "盐水/低温放电、拆包、模组与电芯分离、外壳与线束分解",
        "layout_requirement": "应与 Z1 同侧连续布置以缩短整包运输距离；放电区独立防腐蚀地面与"
                              "废水收集沟，拆解工位按防爆分区划分（GB 50058 待核定）",
        "safety_buffer_note": "涉电解液与残余电荷作业，须与办公区、成品库分离；数值间距待核定",
        "area_m2": None, "capacity_t_a": None,
        "missing_input_ids": "M01;M02;M09",
        "status": "not_ready_numeric",
    },
    {
        "zone_id": "Z3", "name": "破碎分选区",
        "function": "粗破、细破、磁选、涡流分选、气流分选、收尘与黑粉收集",
        "layout_requirement": "位于 Z2 与 Z4 之间，便于黑粉密闭输送；破碎段设独立收尘与氮气保护，"
                              "产尘工段与其他区之间设隔离墙",
        "safety_buffer_note": "粉尘爆炸风险工段，需按粉尘防爆要求设泄爆与隔爆；间距待核定",
        "area_m2": None, "capacity_t_a": None,
        "missing_input_ids": "M02;M09",
        "status": "not_ready_numeric",
    },
    {
        "zone_id": "Z4", "name": "湿法冶金与直接再生主工艺区",
        "function": "黑粉浸出（酸/碱体系）、除杂、萃取或沉淀、补锂再生与前驱体合成",
        "layout_requirement": "按物料流向自北向南串联布置反应、固液分离与结晶工段；酸碱罐区独立成组，"
                              "设围堰与事故收集池",
        "safety_buffer_note": "酸碱与双氧水储存区按腐蚀性介质要求与人员密集区分隔；数值待核定",
        "area_m2": None, "capacity_t_a": None,
        "missing_input_ids": "M03;M05;M06;M07;M09",
        "status": "not_ready_numeric",
    },
    {
        "zone_id": "Z5", "name": "产品与副产品区",
        "function": "碳酸锂、磷酸铁、硫酸盐副产品包装、检验、仓储与外运",
        "layout_requirement": "靠近园区成品出入口，与主工艺区以输送管线连接；设置独立成品库与"
                              "不合格品隔离区",
        "safety_buffer_note": "与 Z4 之间以满足工艺输送与消防要求的最小间距布置；数值待核定",
        "area_m2": None, "capacity_t_a": None,
        "missing_input_ids": "M03;M05;M09",
        "status": "not_ready_numeric",
    },
    {
        "zone_id": "Z6", "name": "废水与尾气治理区",
        "function": "含重金属废水处理、蒸发结晶、尾气洗涤与活性炭吸附、回用水池",
        "layout_requirement": "布置于园区主导风向下风向、地势较低处，紧邻 Z4 便于废液自流收集；"
                              "与 Z4 之间设事故水池",
        "safety_buffer_note": "按排污许可与环评要求确定卫生防护距离；本阶段不填数值（R01-1）",
        "area_m2": None, "capacity_t_a": None,
        "missing_input_ids": "M06;M07;M09",
        "status": "not_ready_numeric",
    },
    {
        "zone_id": "Z7", "name": "固废与危废暂存区",
        "function": "一般工业固废与危险废物分类暂存、台账管理、委外资质单位转运",
        "layout_requirement": "独立设置、硬化防渗地面、分区标识；危废暂存间靠近园区次入口便于专用车辆进出"
                              "（R08-1：危废与一般固废分别贮存）",
        "safety_buffer_note": "与办公区、成品库保持隔离；具体间距待环评与安评核定",
        "area_m2": None, "capacity_t_a": None,
        "missing_input_ids": "M02;M06;M07;M09",
        "status": "not_ready_numeric",
    },
    {
        "zone_id": "Z8", "name": "公用工程、检测与办公区",
        "function": "变配电、压缩空气、蒸汽、循环水、检化验室、中控与办公",
        "layout_requirement": "布置于园区上风向一侧，与生产区分区管理；检化验室靠近 Z4 与 Z5 便于取样",
        "safety_buffer_note": "人员密集场所与危险工段之间按防火与卫生防护要求分隔；数值待核定",
        "area_m2": None, "capacity_t_a": None,
        "missing_input_ids": "M06;M09",
        "status": "not_ready_numeric",
    },
)

PROJECT_CATALOG = (
    {
        "project_id": "工程-01", "name": "来料接收、暂存与智能仓储工程",
        "category": "辅助工程", "process_stage": "S1", "zone_id": "Z1",
        "function": "整包称重登记、绝缘与外观检测、SOH 抽检、分区暂存与批次追溯",
        "key_equipment": "地磅与自动登记系统；绝缘/耐压检测台；红外热像巡检；分区货架与温湿度监测；"
                         "消防水系统与事故收集沟",
        "design_capacity_t_a": None, "capacity_basis": "整包来料 ×（1 − 梯次利用分流 M01）",
        "capex_yi_yuan": None, "opex_yuan_t": None, "product_or_service": "—",
        "missing_input_ids": "M01;M02;M09;M12",
        "status": "not_ready_numeric",
        "note": "仓储面积与货位数取决于 M01 分流后的实际入库量与暂存周期，两者均未定",
    },
    {
        "project_id": "工程-02", "name": "放电与智能拆解工程",
        "category": "主体工程", "process_stage": "S1–S2", "zone_id": "Z2",
        "function": "整包放电、拆包、模组与电芯分离、外壳/线束/BMS 分解与分类收集",
        "key_equipment": "放电槽与盐水电导监控；拆包机；模组拆解工位；电芯切壳/去盖设备；"
                         "BMS 与线束拆解台；废气收集罩",
        "design_capacity_t_a": None, "capacity_basis": "放电后整包处理量 = 来料 ×（1 − M01）",
        "capex_yi_yuan": None, "opex_yuan_t": None, "product_or_service": "拆解产物（外壳、集流体、模组）",
        "missing_input_ids": "M01;M02;M09;M12",
        "status": "not_ready_numeric",
        "note": "线体节拍与工位数需按 M09 年运行小时反算，当前未定",
    },
    {
        "project_id": "工程-03", "name": "破碎分选与黑粉制备工程",
        "category": "主体工程", "process_stage": "S2", "zone_id": "Z3",
        "function": "电芯粗破与细破、磁选/涡流/气流分选、铜铝箔与隔膜分离、黑粉收集与密闭输送",
        "key_equipment": "粗破机；细破机；磁选机；涡流分选机；气流分选床；布袋收尘与氮气保护系统；"
                         "黑粉密闭输送与称重",
        "design_capacity_t_a": None, "capacity_basis": "电芯质量 × 黑粉分数 × 分选收率（M02 未定）",
        "capex_yi_yuan": None, "opex_yuan_t": None, "product_or_service": "黑粉（含胶黏剂）、铜箔、铝箔、隔膜",
        "missing_input_ids": "M02;M09;M12",
        "status": "not_ready_numeric",
        "note": "黑粉产率与分选收率（M02）未定，无法反算设备处理能力与台数",
    },
    {
        "project_id": "工程-04", "name": "湿法冶金浸出与产品精炼工程",
        "category": "主体工程", "process_stage": "S3–S4", "zone_id": "Z4",
        "function": "黑粉浸出（酸/碱体系）、除杂净化、锂与铁磷分离、碳酸锂与磷酸铁制备、副产品回收",
        "key_equipment": "浸出反应釜与搅拌系统；压滤/离心固液分离；除杂与萃取设备；"
                         "碳酸锂沉淀与干燥线；磷酸铁合成与煅烧线；酸碱储罐与计量",
        "design_capacity_t_a": None, "capacity_basis": "黑粉量 × 各段浸出率与回收率（M03/M05 未定）",
        "capex_yi_yuan": None, "opex_yuan_t": None, "product_or_service": "电池级碳酸锂、磷酸铁、硫酸盐副产品",
        "missing_input_ids": "M03;M05;M06;M07;M09;M12",
        "status": "not_ready_numeric",
        "note": "工艺路线（湿法 vs 直接再生）与药剂单耗均未选定，设备清单无法定型",
    },
    {
        "project_id": "工程-05", "name": "黑粉直接再生修复工程（可选并行路线）",
        "category": "主体工程", "process_stage": "S3", "zone_id": "Z4",
        "function": "黑粉补锂、固相烧结修复与复配，产出再生正极材料",
        "key_equipment": "补锂混料机；气氛烧结炉；破碎分级与磁选除铁；产品复配与检测",
        "design_capacity_t_a": None, "capacity_basis": "黑粉量 × 可再生比例（M05 未定）",
        "capex_yi_yuan": None, "opex_yuan_t": None, "product_or_service": "再生正极材料（LFP/NMC）",
        "missing_input_ids": "M03;M05;M07;M09;M12",
        "status": "not_ready_numeric",
        "note": "与工程-04 为互斥/互补路线，需组内先确定主工艺路线（M03）后再取舍",
    },
    {
        "project_id": "工程-06", "name": "废水、尾气与固废治理工程",
        "category": "环保工程", "process_stage": "S5", "zone_id": "Z6/Z7",
        "function": "含重金属废水处理与回用、蒸发结晶、尾气洗涤与吸附、危废分类暂存与委外",
        "key_equipment": "中和沉淀与混凝系统；膜浓缩与蒸发结晶；尾气洗涤塔与活性炭吸附；"
                         "危废暂存间与防渗地面；在线监测",
        "design_capacity_t_a": None, "capacity_basis": "废水量与药剂单耗（M06/M07 未定）",
        "capex_yi_yuan": None, "opex_yuan_t": None, "product_or_service": "回用水、达标排放、委外处置服务",
        "missing_input_ids": "M06;M07;M09;M12",
        "status": "not_ready_numeric",
        "note": "排放标准适用性与药剂单耗均未定；治理规模必须随主工艺路线确定后反算",
    },
)

CAPACITY_INTERFACES = (
    {
        "interface_id": "IF-01", "target": "回收处理量（t/a）",
        "formula": "Q_recycle = Q_received × (1 − f_reuse)",
        "inputs": "Q_received=80000 t/a（已定）；f_reuse=M01（null）",
        "status": "blocked_by_M01", "missing_input_ids": "M01",
        "note": "梯次利用分流未定，不得默认全部进入回收",
    },
    {
        "interface_id": "IF-02", "target": "小时处理能力（t/h）",
        "formula": "Q_h = Q_recycle / H_annual",
        "inputs": "H_annual=M09（null）",
        "status": "blocked_by_M09", "missing_input_ids": "M09",
        "note": "年运行小时未定，设备台数与节拍不可反算",
    },
    {
        "interface_id": "IF-03", "target": "黑粉产量（t/a）",
        "formula": "M_powder = M_cell × f_powder × η_sort",
        "inputs": "M_cell 由组成核算（已定）；f_powder=0.4268/0.4378（组成）；η_sort=M02（null）",
        "status": "blocked_by_M02", "missing_input_ids": "M02",
        "note": "分选收率未定，黑粉产量不可定值",
    },
    {
        "interface_id": "IF-04", "target": "锂产品产量（t/a，以 Li 计）",
        "formula": "M_Li_product = M_powder × w_Li × η_leach × η_recovery",
        "inputs": "w_Li 参考 4.34%/3.425%（不可直接用）；η_leach=M03；η_recovery=M05",
        "status": "blocked_by_M03;M05", "missing_input_ids": "M03;M05",
        "note": "粉料 Li 品位基准未确认（湿基/元素基），浸出与回收率均未定",
    },
    {
        "interface_id": "IF-05", "target": "Li 元素守恒核验",
        "formula": "|Li_out − Li_in| / Li_in < 5e-4；Li_in = 0 → undefined",
        "inputs": "Li_in、Li_out 均依赖 M02/M03/M05 的分配系数",
        "status": "blocked_by_M02;M03;M05", "missing_input_ids": "M02;M03;M05",
        "note": "接口已实现（mfa_model.li_balance_check），数据未就绪",
    },
    {
        "interface_id": "IF-06", "target": "投资与成本（亿元 / 元·t⁻¹）",
        "formula": "CAPEX = Σ 设备与土建清单；OPEX = 药剂 + 能源 + 人工 + 折旧",
        "inputs": "设备清单（M03/M05/M09 后定）；价格与系数 M12（null，属成员 C）",
        "status": "blocked_by_M12", "missing_input_ids": "M12",
        "note": "本脚本不产出任何投资数值",
    },
)

SCOPE_BOUNDARY = (
    "园区范围为退役动力电池回收与资源化环节；不包含邦普时代正极材料生产、"
    "邦普宜化配套原料生产，也不自动汇总整园区投资与产值（case_definition.excludes_automatic_aggregation）。"
)


def summarize_readiness(raw: dict) -> dict[str, set[str]]:
    readiness = module_readiness(raw)
    blocked_modules = {r["module"] for r in readiness if not r["ready"]}
    blocking_ids: set[str] = set()
    for r in readiness:
        if not r["ready"]:
            blocking_ids |= set(filter(None, (r["blocking_input_ids"] or "").split(";")))
    return {"blocked_modules": blocked_modules, "blocking_ids": blocking_ids}


def main() -> int:
    print("=" * 78)
    print("lecture12 案例三 · 成员 A 中期建模（功能分区 + 重点工程骨架）")
    print("=" * 78)

    raw = load_handoff()
    checks = validate_dataset(raw)
    failed = [c for c in checks if c.status == "FAIL"]
    if failed:
        print(f"[中止] 交接包校验失败：{[c.check_id for c in failed]}")
        return 1
    state = summarize_readiness(raw)
    print(f"交接包校验：{len(checks)} 项全部通过")
    print(f"阻断输入：{';'.join(sorted(state['blocking_ids']))}")
    print(f"阻断模块：{';'.join(sorted(state['blocked_modules']))}\n")

    print("[1] 功能分区（园区布局骨架）")
    for z in FUNCTIONAL_ZONES:
        print(f"    {z['zone_id']} {z['name']}")
        print(f"        功能：{z['function']}")
        print(f"        布局：{z['layout_requirement']}")
        print(f"        面积/规模：{fmt(z['area_m2'])} m² / {fmt(z['capacity_t_a'])} t·a⁻¹  "
              f"→ {z['status']}（阻断 {z['missing_input_ids']}）")
    write_csv("functional_zones.csv", list(FUNCTIONAL_ZONES),
              ["zone_id", "name", "function", "layout_requirement", "safety_buffer_note",
               "area_m2", "capacity_t_a", "missing_input_ids", "status"])

    print("\n[2] 重点工程清单（工程-01 至工程-06）")
    for p in PROJECT_CATALOG:
        print(f"    {p['project_id']} {p['name']}  [{p['category']}｜工序 {p['process_stage']}｜{p['zone_id']}]")
        print(f"        关键设备：{p['key_equipment']}")
        print(f"        设计规模：{fmt(p['design_capacity_t_a'])} t/a（{p['capacity_basis']}）")
        print(f"        投资/成本：CAPEX {fmt(p['capex_yi_yuan'])} 亿元；OPEX {fmt(p['opex_yuan_t'])} 元/t")
        print(f"        状态：{p['status']}（阻断 {p['missing_input_ids']}）；说明：{p['note']}")
    write_csv("engineering_project_catalog.csv", list(PROJECT_CATALOG),
              ["project_id", "name", "category", "process_stage", "zone_id", "function",
               "key_equipment", "design_capacity_t_a", "capacity_basis", "capex_yi_yuan",
               "opex_yuan_t", "product_or_service", "missing_input_ids", "status", "note"])

    print("\n[3] 规模反算接口（仅供后续解锁使用，不填数值）")
    for i in CAPACITY_INTERFACES:
        print(f"    {i['interface_id']} {i['target']}")
        print(f"        公式：{i['formula']}")
        print(f"        状态：{i['status']}（{i['inputs']}）")
    write_csv("capacity_interfaces.csv", list(CAPACITY_INTERFACES),
              ["interface_id", "target", "formula", "inputs", "status", "missing_input_ids", "note"])

    print("\n[4] 边界声明")
    print(f"    {SCOPE_BOUNDARY}")
    print("\n[5] 自检")
    print(f"    工程数量：{len(PROJECT_CATALOG)} 项（要求 ≥5）")
    assert len(PROJECT_CATALOG) >= 5
    numeric_leaks = [p["project_id"] for p in PROJECT_CATALOG
                     if any(p[k] is not None for k in ("design_capacity_t_a", "capex_yi_yuan", "opex_yuan_t"))]
    print(f"    数值泄漏检查：{'无' if not numeric_leaks else numeric_leaks}")
    assert not numeric_leaks, "阻断项未解除，工程清单不得出现规模/投资数值"
    missing_dirs = WORKDIR / "data_cohort"
    print(f"    输出目录：{missing_dirs.relative_to(WORKDIR)}")
    print("\n完成：分区与工程骨架已就位；规模、投资与运行参数等待对应阻断输入解除。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
