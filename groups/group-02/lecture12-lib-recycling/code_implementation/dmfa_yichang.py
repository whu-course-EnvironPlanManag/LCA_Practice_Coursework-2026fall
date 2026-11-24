#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lecture12 案例三 · 宜昌市域动态物质流分析（dMFA）计算 · 成员 A

数据入口：
    A_dMFA数据交接包_20261103/yichang_dmfa_dataset.json（Codex 交接快照，只读、未修改）
    A_dMFA数据交接包_20261103/README_数据口径与使用顺序.md、IDE_数据接入提示词.md

本脚本做什么：
    1. 读入并校验交接数据集（结构、口径、来源引用、与旧包一致性标记）；
    2. 按 conditional_case_definitions 显式选取 C065 / C085 / C100 三个收集率情景；
    3. 计算 2010—2025 新车首装电池队列的：首装流入、首次退出、正规收集、在用存量；
    4. 计算 2026—2040 该批既有队列的剩余释放（标题与列名均标注"首装队列贡献"）；
    5. 对 LFP 部分按车型配套含锂强度换算 Li 存量/退出/收集，未细分三元 Li 保持 null；
    6. 输出存量-流量恒等式与 Li 恒等式校验，写 CSV 供报告与 B/C 成员引用。

口径红线（与交接包 execution_contract 一致）：
    - 年末入队、年龄 0 进入、首次退出从年龄 1 起（A17）；
    - 生存函数 L(age)=exp(-(age/scale)^k)，退出 f(age)=L(age-1)-L(age)，**寿命尾部不重新归一化**；
    - 退出量先算，正规收集 = 情景 c × 退出量，c 缺失不影响退出量本身；
    - 未细分三元含 Li 为 null，不取 622/811 平均、不填 0；
    - 正规收集 ≠ 进入再生 ≠ 进入园区；M01、D-PARK-LINK 未解锁，故不出园区进料；
    - 8 万 t/a 园区来料与本市装机不是同一流量，禁止相加或互推。

AI 辅助说明：
    提示词摘要："接入 yichang_dmfa_dataset.json，按 execution_contract 显式选三个收集率情景，
    算 2010—2025 首装队列的存量/退出/收集，算 2026—2040 既有队列剩余释放，LFP 部分出 Li，
    未细分三元留 null，做存量-流量与 Li 恒等式校验"。
    人工复核：成员 A 已核对 lifetime_tail 不归一化、collected≠recycled、cohort 边界不补零。

运行：
    python code_implementation/dmfa_yichang.py
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any

WORKDIR = Path(__file__).resolve().parent.parent
DATASET_DIR = WORKDIR / "data_cohort" / "A_dMFA数据交接包_20261103"
DATASET_JSON = DATASET_DIR / "yichang_dmfa_dataset.json"
DATA_DIR = WORKDIR / "data_cohort"

CHEM_LFP = "LFP"
CHEM_NMC = "MIXED_NMC_UNSPECIFIED"
LIFETIME_CHEM = (CHEM_LFP, CHEM_NMC)
# 车辆类别顺序固定，便于报告与图一致
CLASS_ORDER = ("BEV", "PHEV", "BUS_PROXY", "MEDIUM_TRUCK_PROXY")

MAX_AGE = 80                 # 生存函数求和上限（f(80) 已 < 1e-12，尾部质量显式保留）
IDENT_TOL = 1e-9             # 结构恒等式容差（浮点累加误差级，非物理容差）
LI_TOL = 5e-4                # 与 mfa_model / 交接包一致：严格小于 0.05%

REQUIRED_TOP_KEYS = (
    "dataset", "conventions", "study_boundaries", "sources", "assumptions", "observations",
    "dmfa_inputs", "chemistry_scenarios", "analysis_modes", "conditional_case_definitions",
    "execution_contract", "module_gates", "unresolved_inputs", "integration_notes",
    "legacy_park_handoff",
)


# ----------------------------------------------------------------------------- 读入
def load_dataset(path: Path = DATASET_JSON) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        raw = json.load(fh)
    if "yichang_dmfa_dataset" in raw:          # 兼容被包一层的写法
        raw = raw["yichang_dmfa_dataset"]
    return raw


def source_index(raw: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {s["source_id"]: s for s in raw.get("sources", []) if "source_id" in s}


# ----------------------------------------------------------------------------- 结构
def survival(k: float, scale_year: float, age: float) -> float:
    """L(age) = exp(−(age/scale)^k)，age=0 时为 1（年末入队、进入年龄 0）。"""
    if age <= 0:
        return 1.0
    return math.exp(-((age / scale_year) ** k))


def exit_pmf(k: float, scale_year: float, max_age: int = MAX_AGE) -> list[float]:
    """f(age) = L(age−1) − L(age)，age ≥ 1；**不做尾部重归一化**（lifetime_tail=False）。"""
    return [survival(k, scale_year, a - 1) - survival(k, scale_year, a) for a in range(1, max_age + 1)]


def mean_lifetime(k: float, scale_year: float) -> float:
    return scale_year * math.gamma(1.0 + 1.0 / k)


# ----------------------------------------------------------------------------- 校验
def validate_dataset(raw: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    srcs = source_index(raw)

    def add(cid: str, item: str, ok: bool, detail: str) -> None:
        checks.append({"check_id": cid, "item": item, "status": "PASS" if ok else "FAIL", "detail": detail})

    # D01 顶层结构
    missing = [k for k in REQUIRED_TOP_KEYS if k not in raw]
    add("D01", "顶层必需键完整", not missing, "缺失：" + ",".join(missing) if missing else f"{len(REQUIRED_TOP_KEYS)} 个键齐全")
    ds = raw.get("dataset", {})
    add("D02", "数据集标志与模型未执行状态",
        ds.get("conditional_dmfa_inputs_ready") is True and ds.get("retirement_model_executed") is False,
        f"schema={ds.get('schema_version')}；conditional_ready={ds.get('conditional_dmfa_inputs_ready')}；"
        f"retirement_model_executed={ds.get('retirement_model_executed')}")

    # D03 来源引用可解析
    unresolved_refs: list[str] = []
    d = raw["dmfa_inputs"]
    for block in d.values():
        for sid in (block.get("source_ids") or []):
            if sid not in srcs:
                unresolved_refs.append(sid)
    add("D03", "DMFA 来源引用可解析", not unresolved_refs,
        ("未解析：" + ";".join(sorted(set(unresolved_refs)))) if unresolved_refs else "全部来源引用均可解析")

    # D04 首装记录连续且非空
    recs = d["DMFA-01"]["annual_records"]
    years = [r["year"] for r in recs]
    add("D04", "DMFA-01 年度记录 2010—2025 连续",
        years == list(range(2010, 2026)),
        f"{len(recs)} 条，{years[0]}—{years[-1]}")
    nulls = [r["year"] for r in recs if r.get("first_install_pack_mass_t") is None]
    add("D05", "首装包质量无缺失", not nulls, "缺失年份：" + ",".join(map(str, nulls)) if nulls else "16 年全部有值（条件重建）")

    # D06 车型份额与包质量自洽
    protos = d["DMFA-01"]["vehicle_class_prototypes"]
    share_sum = sum(p["share"] for p in protos)
    mass_ok = all(abs(p["pack_mass_kg"] - p["capacity_kWh"] * 1000.0 / p["specific_energy_Wh_per_kg"]) < 1e-9
                  for p in protos if p["specific_energy_Wh_per_kg"])
    add("D06", "车型份额合计为 1 且包质量=容量/比能量",
        abs(share_sum - 1.0) < 1e-12 and mass_ok,
        f"Σshare={share_sum:.12f}；包质量换算逐类一致")

    # D07 化学情景：分体系年度质量与首装总量一致
    chem_records = raw["chemistry_scenarios"][0]["annual_pack_mass_records"]
    worst = 0.0
    for r in recs:
        total = r["first_install_pack_mass_t"]
        split = sum((c.get("LFP") or 0.0) + (c.get("MIXED_NMC_UNSPECIFIED") or 0.0) for c in chem_records if c["year"] == r["year"])
        worst = max(worst, abs(split - total) / max(total, 1e-12)) if total else worst
    add("D07", "化学情景分体系质量合计=首装总量", worst < 1e-9, f"最大相对偏差={worst:.3e}")

    # D08 寿命参数
    params = {p["chemistry"]: p for p in d["DMFA-02"]["parameters"]}
    ok_life = all(c in params and params[c]["k"] > 0 and params[c]["scale_year"] > 0 for c in LIFETIME_CHEM)
    mean_ok = all(abs(mean_lifetime(params[c]["k"], params[c]["scale_year"])
                      - params[c]["mean_lifetime_year_derived"]) < 1e-9 for c in LIFETIME_CHEM)
    add("D08", "LFP/三元寿命参数存在且均值可复算", ok_life and mean_ok,
        f"LFP k={params[CHEM_LFP]['k']},scale={params[CHEM_LFP]['scale_year']}；"
        f"三元 k={params[CHEM_NMC]['k']},scale={params[CHEM_NMC]['scale_year']}")

    # D09 尾部不归一化、生存函数单调
    tail = raw["execution_contract"].get("lifetime_tail", {})
    ok_tail = tail.get("renormalize_truncated_pmf") is False and tail.get("retain_surviving_tail") is True
    mono = all(survival(params[c]["k"], params[c]["scale_year"], a)
               >= survival(params[c]["k"], params[c]["scale_year"], a + 1) for c in LIFETIME_CHEM for a in range(0, 40))
    add("D09", "寿命尾部不重归一化且 L(age) 单调不增", ok_tail and mono,
        "lifetime_tail.renormalize_truncated_pmf=False；L(age) 0—40 年逐点不增")

    # D10 收集率情景
    scen = {s["scenario_id"]: s for s in d["DMFA-04"]["scenarios"]}
    cases = raw["conditional_case_definitions"]
    used = {c["collection_scenario_id"] for c in cases}
    ok_c = (used == set(scen)
            and all(0.0 <= scen[cid]["value"] <= 1.0 for cid in used)
            and all(c["input_reconstruction_id"] == d["DMFA-01"]["reconstruction_id"] for c in cases))
    add("D10", "三个收集率情景齐全、0≤c≤1 且案例引用一致", ok_c,
        ";".join(f"{k}={v['value']}" for k, v in sorted(scen.items())) + f"；案例 {len(cases)} 个")

    # D11 Li 强度：分钟级换算与 null 约定
    li = d["DMFA-06"]
    prof = {(p["class_id"], p["chemistry"]): p for p in li["profiles"]}
    conv_ok = all(abs(p["value_kg_Li_per_t_pack"] - p["intensity_kg_Li_per_kWh"] * p["specific_energy_Wh_per_kg_pack"]) < 1e-9
                  for p in li["profiles"] if p["value_kg_Li_per_t_pack"] is not None)
    null_ok = all(p["value_kg_Li_per_t_pack"] is None for p in li["profiles"] if p["chemistry"] == CHEM_NMC)
    add("D11", "Li 强度换算一致且未细分三元为 null", conv_ok and null_ok,
        f"{len(prof)} 条车型×体系记录；三元全部 null（不平均 622/811）")

    # D12 未解锁模块不得产出数值
    gates = {g["module"]: g for g in raw["module_gates"]}
    forb = [m for m, g in gates.items() if not g.get("ready")]
    add("D12", "未就绪模块保持阻断（不补零）", len(forb) == 6,
        f"阻断模块 {len(forb)} 个：" + ";".join(forb))

    # D13 未解决输入全部 null
    un = raw["unresolved_inputs"]
    add("D13", "未解决输入 11 项保持 null",
        len(un) == 11 and all(u.get("value") is None for u in un if "value" in u),
        f"{len(un)} 项：" + ",".join(u["input_id"] for u in un))
    return checks


# ----------------------------------------------------------------------------- 计算
def cohort_inflows(raw: dict[str, Any]) -> dict[tuple[str, str], dict[int, float]]:
    """返回 {(chemistry, class_id): {year: t_pack/a}}，直接取交接包逐类分体系质量。"""
    out: dict[tuple[str, str], dict[int, float]] = {}
    for rec in raw["dmfa_inputs"]["DMFA-01"]["annual_records"]:
        for cls in rec["classes"]:
            out.setdefault((CHEM_LFP, cls["class_id"]), {})[rec["year"]] = cls["lfp_pack_mass_t_H"]
            out.setdefault((CHEM_NMC, cls["class_id"]), {})[rec["year"]] = cls["nmc_unspecified_pack_mass_t_H"]
    return out


def chemistry_series(inflows: dict[tuple[str, str], dict[int, float]], chem: str) -> dict[int, float]:
    series: dict[int, float] = {}
    for (c, _cls), vals in inflows.items():
        if c != chem:
            continue
        for y, v in vals.items():
            series[y] = series.get(y, 0.0) + v
    return series


def li_intensity(raw: dict[str, Any], chem: str) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    for p in raw["dmfa_inputs"]["DMFA-06"]["profiles"]:
        if p["chemistry"] == chem:
            out[p["class_id"]] = p["value_kg_Li_per_t_pack"]
    return out


def run_case(raw: dict[str, Any], case: dict[str, Any],
             inflows: dict[tuple[str, str], dict[int, float]]) -> dict[str, Any]:
    """单个情景（收集率 c）的首装队列 dMFA。"""
    params = {p["chemistry"]: p for p in raw["dmfa_inputs"]["DMFA-02"]["parameters"]}
    c_rate = next(s["value"] for s in raw["dmfa_inputs"]["DMFA-04"]["scenarios"]
                  if s["scenario_id"] == case["collection_scenario_id"])
    years_hist = [r["year"] for r in raw["dmfa_inputs"]["DMFA-01"]["annual_records"]]
    years_all = list(range(years_hist[0], 2041))

    by_chem: dict[str, dict[str, Any]] = {}
    for chem in LIFETIME_CHEM:
        k, scale = params[chem]["k"], params[chem]["scale_year"]
        f = exit_pmf(k, scale)
        I = chemistry_series(inflows, chem)
        retired, collected, stock = {}, {}, {}
        for t in years_all:
            r = sum(I.get(t - age, 0.0) * f[age - 1] for age in range(1, min(MAX_AGE, t - years_hist[0] + 1)))
            s = sum(I.get(t - age, 0.0) * survival(k, scale, age)
                    for age in range(0, min(MAX_AGE, t - years_hist[0] + 1)))
            retired[t], stock[t] = r, s
            collected[t] = c_rate * r
        by_chem[chem] = {"install": I, "retired": retired, "collected": collected, "stock": stock, "k": k, "scale": scale}

    # Li：仅 LFP 可算（按车型配套强度），未细分三元整列 null
    inten = li_intensity(raw, CHEM_LFP)
    li_stock, li_ret, li_col = {}, {}, {}
    for t in years_all:
        stock_li = 0.0
        ret_li = 0.0
        for cls in CLASS_ORDER:
            masses = inflows.get((CHEM_LFP, cls), {})
            w = inten[cls]
            stock_li += sum(masses.get(t - age, 0.0) * survival(by_chem[CHEM_LFP]["k"], by_chem[CHEM_LFP]["scale"], age)
                            for age in range(0, min(MAX_AGE, t - years_hist[0] + 1))) * w
            ret_li += sum(masses.get(t - age, 0.0) * exit_pmf_cache[CHEM_LFP][age - 1]
                          for age in range(1, min(MAX_AGE, t - years_hist[0] + 1))) * w
        li_stock[t], li_ret[t], li_col[t] = stock_li, ret_li, c_rate * ret_li

    # 存量-流量恒等式（分体系）；2009-12-31 队列初值 0（A01），不是实测存量
    ident = {}
    s0 = {chem: 0.0 for chem in LIFETIME_CHEM}
    for chem in LIFETIME_CHEM:
        inflow_sum = sum(by_chem[chem]["install"].get(y, 0.0) for y in years_hist)
        out_sum = sum(by_chem[chem]["retired"][y] for y in years_all)
        final = by_chem[chem]["stock"][years_all[-1]]
        residual = inflow_sum - out_sum - (final - s0[chem])
        rel = abs(residual) / max(inflow_sum, 1e-12)
        ident[chem] = {"status": "PASS" if rel < IDENT_TOL else "FAIL", "residual": residual, "rel": rel,
                       "inflow_sum": inflow_sum, "outflow_sum": out_sum, "s0": s0[chem], "final": final}
    li_install_sum = sum(
        sum(inflows.get((CHEM_LFP, cls), {}).get(y, 0.0) * inten[cls] for cls in CLASS_ORDER) for y in years_hist)
    li_residual = li_install_sum - sum(li_ret[t] for t in years_all) - (li_stock[years_all[-1]] - 0.0)
    li_rel = abs(li_residual) / max(li_install_sum, 1e-12)
    ident[CHEM_LFP + "_Li"] = {"status": "PASS" if li_rel < IDENT_TOL else "FAIL", "residual": li_residual,
                               "rel": li_rel, "inflow_sum": li_install_sum,
                               "outflow_sum": sum(li_ret[t] for t in years_all),
                               "s0": 0.0, "final": li_stock[years_all[-1]]}

    return {"case": case, "c_rate": c_rate, "by_chem": by_chem, "li": {"stock": li_stock, "retired": li_ret,
            "collected": li_col}, "ident": ident, "years_hist": years_hist, "years_all": years_all}


exit_pmf_cache: dict[str, list[float]] = {}


def prepare(raw: dict[str, Any]) -> None:
    params = {p["chemistry"]: p for p in raw["dmfa_inputs"]["DMFA-02"]["parameters"]}
    for chem in LIFETIME_CHEM:
        exit_pmf_cache[chem] = exit_pmf(params[chem]["k"], params[chem]["scale_year"])


# ----------------------------------------------------------------------------- 输出
def fmt(v: Any, digits: int = 6) -> Any:
    if v is None:
        return None
    if isinstance(v, float):
        return f"{v:.{digits}f}"
    return v


def write_csv(name: str, rows: list[dict[str, Any]], fieldnames: list[str]) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = DATA_DIR / name
    with out.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({k: ("" if row.get(k) is None else row.get(k)) for k in fieldnames})
    return out


def detail_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for rec in records:
        case_id = rec["case"]["case_id"]
        hist_end, all_end = rec["years_hist"][-1], rec["years_all"][-1]
        for t in rec["years_all"]:
            mode = "historical_first_service_cohorts" if t <= hist_end else "closed_historical_cohort_release"
            for chem in LIFETIME_CHEM:
                seg = rec["by_chem"][chem]
                install = seg["install"].get(t)
                li_stock = rec["li"]["stock"][t] if chem == CHEM_LFP else None
                li_ret = rec["li"]["retired"][t] if chem == CHEM_LFP else None
                li_col = rec["li"]["collected"][t] if chem == CHEM_LFP else None
                rows.append({
                    "case_id": case_id,
                    "collection_scenario": rec["case"]["collection_scenario_id"],
                    "collection_rate": fmt(rec["c_rate"]),
                    "year": t,
                    "mode": mode,
                    "chemistry": chem,
                    "install_inflow_t": fmt(install),
                    "retired_pack_t": fmt(seg["retired"][t]),
                    "collected_pack_t": fmt(seg["collected"][t]),
                    "in_use_stock_t": fmt(seg["stock"][t]),
                    "li_in_use_kg": fmt(li_stock, 3),
                    "li_retired_kg": fmt(li_ret, 3),
                    "li_collected_kg": fmt(li_col, 3),
                    "li_status": "partial_LFP_only" if chem == CHEM_LFP else "null_unresolved_D06-NMC",
                    "install_status": ("reconstructed_conditional" if t <= hist_end
                                       else "excluded_by_cohort_definition_not_zero"),
                })
    return rows


def total_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for rec in records:
        case_id = rec["case"]["case_id"]
        hist_end = rec["years_hist"][-1]
        for t in rec["years_all"]:
            ins = sum(rec["by_chem"][c]["install"].get(t, 0.0) for c in LIFETIME_CHEM)
            ret = sum(rec["by_chem"][c]["retired"][t] for c in LIFETIME_CHEM)
            col = sum(rec["by_chem"][c]["collected"][t] for c in LIFETIME_CHEM)
            sto = sum(rec["by_chem"][c]["stock"][t] for c in LIFETIME_CHEM)
            rows.append({
                "case_id": case_id,
                "collection_scenario": rec["case"]["collection_scenario_id"],
                "year": t,
                "mode": "historical_first_service_cohorts" if t <= hist_end else "closed_historical_cohort_release",
                "install_total_t": fmt(ins) if t <= hist_end else None,
                "retired_total_t": fmt(ret),
                "collected_total_t": fmt(col),
                "in_use_stock_total_t": fmt(sto),
                "li_in_use_kg_LFP_only": fmt(rec["li"]["stock"][t], 3),
                "li_retired_kg_LFP_only": fmt(rec["li"]["retired"][t], 3),
                "li_collected_kg_LFP_only": fmt(rec["li"]["collected"][t], 3),
                "scope_note": ("2010—2025 首装队列贡献；2026 起无新增，不代表全市未来流入为 0"
                               if t > hist_end else "2010—2025 新车首装队列（条件重建，非实测注册）"),
            })
    return rows


def summary_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for rec in records:
        yrs, hist_end = rec["years_all"], rec["years_hist"][-1]
        ins_sum = sum(rec["by_chem"][c]["install"].get(y, 0.0) for c in LIFETIME_CHEM for y in rec["years_hist"])
        ret_sum = sum(rec["by_chem"][c]["retired"][y] for c in LIFETIME_CHEM for y in yrs)
        col_sum = sum(rec["by_chem"][c]["collected"][y] for c in LIFETIME_CHEM for y in yrs)
        sto = {y: sum(rec["by_chem"][c]["stock"][y] for c in LIFETIME_CHEM) for y in yrs}
        peak_y = max(yrs, key=lambda y: sum(rec["by_chem"][c]["retired"][y] for c in LIFETIME_CHEM))
        peak_v = sum(rec["by_chem"][c]["retired"][peak_y] for c in LIFETIME_CHEM)
        lfp_ret_sum = sum(rec["li"]["retired"][y] for y in yrs)
        lfp_col_sum = sum(rec["li"]["collected"][y] for y in yrs)
        rows.append({
            "case_id": rec["case"]["case_id"],
            "collection_scenario": rec["case"]["collection_scenario_id"],
            "collection_rate": fmt(rec["c_rate"]),
            "cum_first_install_2010_2025_t": fmt(ins_sum, 3),
            "cum_retired_2010_2040_t": fmt(ret_sum, 3),
            "peak_retirement_year": peak_y,
            "peak_retirement_t": fmt(peak_v, 3),
            "cum_collected_2010_2040_t": fmt(col_sum, 3),
            "stock_2025_t": fmt(sto[hist_end], 3),
            "stock_2040_t": fmt(sto[yrs[-1]], 3),
            "li_LFP_stock_2025_kg": fmt(rec["li"]["stock"][hist_end], 3),
            "li_LFP_cum_retired_kg": fmt(lfp_ret_sum, 3),
            "li_LFP_cum_collected_kg": fmt(lfp_col_sum, 3),
            "stock_flow_identity_LFP": rec["ident"][CHEM_LFP]["status"],
            "stock_flow_identity_NMC": rec["ident"][CHEM_NMC]["status"],
            "li_identity_LFP": rec["ident"][CHEM_LFP + "_Li"]["status"],
            "scope_note": "首装队列贡献，非全市总退役/总在用；正规收集≠进入再生≠进入园区",
        })
    return rows


def parameter_rows(raw: dict[str, Any], records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    d = raw["dmfa_inputs"]
    params = {p["chemistry"]: p for p in d["DMFA-02"]["parameters"]}
    rows: list[dict[str, Any]] = []
    rows.append({
        "parameter_id": "DMFA-01", "value": "2010—2025 条件重建", "unit": "t_pack/a",
        "status": "resolved_conditional_reconstruction",
        "source": ";".join(sorted({sid for rec in d["DMFA-01"]["annual_records"] for sid in rec["source_ids"]}))
                  + " / YC_DMFA01_RECON_V2",
        "note": "逐年新增车辆×车型原型×化学情景；非宜昌实测注册序列",
    })
    for chem in (CHEM_LFP, CHEM_NMC):
        p = params[chem]
        rows.append({
            "parameter_id": "DMFA-02/03", "value": f"k={p['k']}; scale={p['scale_year']} a",
            "unit": "1 / a", "status": "resolved_literature_proxy",
            "source": ";".join(p["source_ids"]) + f"（{p['locator']}）",
            "note": f"{chem}；派生平均寿命={p['mean_lifetime_year_derived']:.4f} a；"
                    f"尾部不重归一化、k/scale 不随车型变化（A14）",
        })
    for s in d["DMFA-04"]["scenarios"]:
        rows.append({
            "parameter_id": "DMFA-04", "value": s["value"], "unit": s["unit"],
            "status": "resolved_literature_scenario_not_local_observation",
            "source": ";".join(s["source_ids"]) + f"（{s['locator']}）",
            "note": f"{s['scenario_id']}；正规收集≠进入再生；本地观测缺失（D04-OBS）",
        })
    rows.append({
        "parameter_id": "DMFA-05", "value": 0.0, "unit": "t_pack",
        "status": "assumption_cohort_initial_state",
        "source": ";".join(d["DMFA-05"]["cohort_initial_state"].get("assumption_ids", [])),
        "note": "2009-12-31 建模首装队列为 0（A01）；不是宜昌真实存量 0；城市实际存量 D05-FLEET 仍未解",
    })
    for p in d["DMFA-06"]["profiles"]:
        if p["chemistry"] != CHEM_LFP:
            continue
        rows.append({
            "parameter_id": "DMFA-06", "value": round(p["value_kg_Li_per_t_pack"], 3), "unit": "kg Li/t pack",
            "status": "resolved_class_matched_proxy",
            "source": ";".join(p["source_ids"]),
            "note": f"{p['class_id']}×LFP；由 {p['intensity_kg_Li_per_kWh']} kg Li/kWh × "
                    f"{p['specific_energy_Wh_per_kg_pack']} Wh/kg 换算；未细分三元不平均",
        })
    rows.append({
        "parameter_id": "DMFA-07", "value": None, "unit": "—",
        "status": "unresolved_optional_spatial_extension",
        "source": "D07-SPATIAL",
        "note": "持证回收企业数量与运输半径未解；本脚本不做空间优化",
    })
    rows.append({
        "parameter_id": "M01", "value": None, "unit": "kg_reuse/kg_retired",
        "status": "unresolved_legacy_park_boundary",
        "source": "旧园区交接包 M01",
        "note": "梯次分流未解，故本脚本只出 collected_after_first_service，不出进入再生/进入园区量",
    })
    rows.append({
        "parameter_id": "D-PARK-LINK", "value": None, "unit": "kg_park_feed/kg_collected",
        "status": "unresolved_city_to_park_link",
        "source": "city_to_park_feed 闸门",
        "note": "市域正规收集不能直接当 8 万 t/a 园区来料；两者口径与边界不同",
    })
    return rows


def readiness_rows(raw: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for g in raw["module_gates"]:
        rows.append({
            "module": g["module"],
            "status": "READY(conditional)" if g.get("ready") else "BLOCKED",
            "blocking": ";".join(g.get("blocking_input_ids") or []) or "—",
            "conditions": ";".join(g.get("conditions") or []) or "—",
        })
    return rows


def print_result(records: list[dict[str, Any]]) -> None:
    print("\n[4] 情景结果（首装队列贡献，单位 t 整包）")
    print(f"    {'案例':<24}{'c':>6}{'累计首装':>12}{'累计退出':>12}{'累计收集':>12}{'2025存量':>12}{'2040存量':>12}")
    for rec in records:
        yrs, hist_end = rec["years_all"], rec["years_hist"][-1]
        ins = sum(rec["by_chem"][c]["install"].get(y, 0.0) for c in LIFETIME_CHEM for y in rec["years_hist"])
        ret = sum(rec["by_chem"][c]["retired"][y] for c in LIFETIME_CHEM for y in yrs)
        col = sum(rec["by_chem"][c]["collected"][y] for c in LIFETIME_CHEM for y in yrs)
        s25 = sum(rec["by_chem"][c]["stock"][hist_end] for c in LIFETIME_CHEM)
        s40 = sum(rec["by_chem"][c]["stock"][yrs[-1]] for c in LIFETIME_CHEM)
        print(f"    {rec['case']['case_id']:<24}{rec['c_rate']:>6.2f}{ins:>12,.0f}{ret:>12,.0f}"
              f"{col:>12,.0f}{s25:>12,.0f}{s40:>12,.0f}")
    print("    说明：退出量与收集率无关；收集量=c×退出量，c 只影响收集，不影响退出。")


def print_identity(records: list[dict[str, Any]]) -> None:
    print("\n[5] 恒等式校验")
    for rec in records:
        for key, val in rec["ident"].items():
            print(f"    {rec['case']['case_id']:<24}{key:<20}{val['status']:<6}"
                  f"残差={val['residual']:+.3e}  相对={val['rel']:.3e}")
    print(f"    容差 {IDENT_TOL:g}（浮点结构校验）；Li 平衡仍以 {LI_TOL:g} 为严格上限")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="宜昌市域 dMFA 计算（首装队列 + 三收集率情景）")
    ap.add_argument("--dataset", type=Path, default=DATASET_JSON)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    raw = load_dataset(args.dataset)
    prepare(raw)
    print("=" * 78)
    print("宜昌市域 dMFA（成员 A）｜数据：A_dMFA数据交接包_20261103/yichang_dmfa_dataset.json")
    print("=" * 78)
    print(f"边界：{raw['study_boundaries']['primary_region']} / {raw['study_boundaries']['primary_layer']}；"
          f"历史 {raw['study_boundaries']['history']['start_year']}—{raw['study_boundaries']['history']['end_year']}，"
          f"外推至 2040（仅既有队列剩余释放）")

    print("\n[1] 数据校验")
    checks = validate_dataset(raw)
    for c in checks:
        print(f"    {c['status']:<4} {c['check_id']} {c['item']} — {c['detail']}")
    write_csv("dmfa_validation_checks.csv", checks, ["check_id", "item", "status", "detail"])
    # A07 fail-fast：校验 FAIL 后不进入计算，也不写任何结果表（只保留校验记录本身）
    failed = [c for c in checks if c["status"] != "PASS"]
    if failed:
        print(f"\n[中止] 数据校验 {len(failed)} 项 FAIL：不计算、不写结果表。")
        for c in failed:
            print(f"    - {c['check_id']} {c['item']}：{c['detail']}")
        return 1

    inflows = cohort_inflows(raw)
    records = [run_case(raw, case, inflows) for case in raw["conditional_case_definitions"]]

    print("\n[2] 参数（已解析部分）")
    for row in parameter_rows(raw, records):
        print(f"    {row['parameter_id']:<10} {str(row['value']):<28} {row['unit']:<12} {row['status']}")

    print("\n[3] 模块状态（来自数据集 module_gates，未就绪模块不出数值）")
    for row in readiness_rows(raw):
        print(f"    {row['status']:<20}{row['module']:<44}{row['blocking']}")

    print_result(records)
    print_identity(records)

    # A07：恒等式核验通过后才写结果表
    bad_ident = [(rec["case"]["case_id"], key, val)
                 for rec in records for key, val in rec["ident"].items() if val["status"] != "PASS"]
    if bad_ident:
        print(f"\n[中止] 恒等式未通过（{len(bad_ident)} 项）：不写结果表。")
        for case_id, key, val in bad_ident:
            print(f"    - {case_id} {key} 残差={val['residual']:+.3e} 相对={val['rel']:.3e}")
        return 1
    print(f"    PASS 恒等式全部通过（容差 {IDENT_TOL:g}；Li 严格上限 {LI_TOL:g}），开始写结果表")

    # 领域约束（写表前判定，避免"先写后断"）
    last = records[0]["years_all"][-1]
    if not all(rec["li"]["stock"][y] >= 0 for rec in records for y in rec["years_all"]):
        print("\n[中止] LFP 在用锂存量出现负值：不写结果表。")
        return 1
    if not all(rec["by_chem"][c]["retired"][y] >= 0
               for rec in records for c in LIFETIME_CHEM for y in rec["years_all"]):
        print("\n[中止] 退役量出现负值：不写结果表。")
        return 1
    if records[0]["by_chem"][CHEM_LFP]["install"].get(last) is not None:
        print("\n[中止] 2026 起出现未来首装量（应由 cohort 定义排除）：不写结果表。")
        return 1
    if not any(p["chemistry"] == CHEM_NMC and p["value_kg_Li_per_t_pack"] is None
               for p in raw["dmfa_inputs"]["DMFA-06"]["profiles"]):
        print("\n[中止] 三元 Li 未被保持为 null：不写结果表。")
        return 1

    write_csv("dmfa_parameters.csv", parameter_rows(raw, records),
              ["parameter_id", "value", "unit", "status", "source", "note"])
    write_csv("dmfa_module_readiness.csv", readiness_rows(raw), ["module", "status", "blocking", "conditions"])
    write_csv("dmfa_yichang_by_chemistry.csv", detail_rows(records),
              ["case_id", "collection_scenario", "collection_rate", "year", "mode", "chemistry",
               "install_inflow_t", "retired_pack_t", "collected_pack_t", "in_use_stock_t",
               "li_in_use_kg", "li_retired_kg", "li_collected_kg", "li_status", "install_status"])
    write_csv("dmfa_yichang_annual_total.csv", total_rows(records),
              ["case_id", "collection_scenario", "year", "mode", "install_total_t", "retired_total_t",
               "collected_total_t", "in_use_stock_total_t", "li_in_use_kg_LFP_only",
               "li_retired_kg_LFP_only", "li_collected_kg_LFP_only", "scope_note"])
    write_csv("dmfa_yichang_summary.csv", summary_rows(records),
              ["case_id", "collection_scenario", "collection_rate", "cum_first_install_2010_2025_t",
               "cum_retired_2010_2040_t", "peak_retirement_year", "peak_retirement_t",
               "cum_collected_2010_2040_t", "stock_2025_t", "stock_2040_t", "li_LFP_stock_2025_kg",
               "li_LFP_cum_retired_kg", "li_LFP_cum_collected_kg", "stock_flow_identity_LFP",
               "stock_flow_identity_NMC", "li_identity_LFP", "scope_note"])

    print("\n[6] 输出")
    print("    → data_cohort/dmfa_validation_checks.csv、dmfa_parameters.csv、dmfa_module_readiness.csv、")
    print("      dmfa_yichang_by_chemistry.csv、dmfa_yichang_annual_total.csv、dmfa_yichang_summary.csv")
    print("    PASS 校验全通过、恒等式全通过、无非负异常、未来首装未补零、三元 Li 保持 null")
    print("\n完成：市域首装队列 dMFA 已出数；全市总预测/替换电池/市域→园区链接仍阻断。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
