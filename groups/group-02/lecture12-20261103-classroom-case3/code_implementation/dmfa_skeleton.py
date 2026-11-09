#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lecture12 案例三 · 动态物质流分析（dMFA）接口库与方程自检

定位：
    本文件是**接口库**（寿命分布、退役流量、存量递推、恒等式、在用锂存量）与合成数据自检；
    接入 A_dMFA数据交接包_20261103 的真实计算由 dmfa_yichang.py 完成，两者方程一致：
        L(age)=exp(-(age/scale)^k)；f(age)=L(age-1)-L(age)（尾部不重新归一化）。
    默认不再输出空表，避免覆盖 dmfa_yichang.py 的真实结果；确需空表骨架时加 --emit-skeleton。

为什么单独建这个文件：
    mfa_model.py 是**稳态工序级 MFA**（单一年度 8 万 t/a 工况）；
    dMFA 需要时间维、存量递推与寿命分布，属于另一套方程，故单独成模块、单独出 CSV，
    避免把"时序外推"混进已解锁的稳态结果。

本模块只做四件事：
    1. 定义时间轴（默认 2026–2040，来自任务书第 79 行的规划期示例，具体区间待组内确认）；
    2. 给出可在数据解锁后直接调用的函数：寿命分布、退役流量、在用存量递推、
       存量-流量恒等式校验、在用锂存量；
    3. 把 dMFA 专属的缺失输入登记为 DMFA-01 至 DMFA-07（**本模块新增，不在 A 交接包内**），
       并输出"空表"骨架 CSV；
    4. 用合成数据做接口自检（仅验证方程实现正确，合成值**不写入任何 CSV、不进入报告**）。

红线（与交接包一致）：
    - 缺数一律 None，不填 0；输出 CSV 的空单元格表示"无数据"；
    - 不激活任何未选定参数，不臆造寿命分布、收集率或历史装机量；
    - 全厂 Li 守恒仍由 mfa_model.li_balance_check() 判定，本模块不另立容差。

AI 辅助说明：
    提示词摘要：“为 dMFA 搭接口骨架：时间轴、Weibull 寿命分布、退役流量、在用存量递推、
    存量-流量恒等式、在用锂存量、缺失输入登记；所有输出保持空值，仅用合成数据做自检”。
    人工复核：成员 A 需确认规划期区间、收集率口径（正规收集率 vs 总回收率）与梯次延寿期。

运行：
    python code_implementation/dmfa_skeleton.py                 # 生成空表骨架
    python code_implementation/dmfa_skeleton.py --self-test      # 额外打印接口自检结果
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

WORKDIR = Path(__file__).resolve().parent.parent
DATA_DIR = WORKDIR / "data_cohort"

DEFAULT_HORIZON = (2026, 2040)          # 任务书 L79 示例区间，待组内确认
HORIZON_NOTE = "情景假设：任务书给出 2026–2040 / 2026–2050 两种示例，本骨架默认前者，可在命令行覆盖"
STOCK_FLOW_TOL = 1e-6                   # 存量-流量恒等式相对容差（仅结构校验用）
LI_TOL = 5e-4                           # 与 mfa_model / 交接包保持一致


# ----------------------------------------------------------------------------- 时间序列
@dataclass
class Series:
    """逐年序列：缺数用 None 表示，禁止以 0 占位。"""
    name: str
    unit: str
    values: dict[int, float | None]

    def years(self) -> list[int]:
        return sorted(self.values)

    def is_empty(self) -> bool:
        return all(v is None for v in self.values.values())


def empty_series(name: str, unit: str, horizon: tuple[int, int]) -> Series:
    start, end = horizon
    return Series(name, unit, {y: None for y in range(start, end + 1)})


# ----------------------------------------------------------------------------- 核心方程
def weibull_pmf(k: float | None, scale_year: float | None, taus: Sequence[int],
                normalize: bool = False) -> list[float] | None:
    """Weibull 寿命分布的离散概率质量：f(τ) = F(τ) − F(τ−1)，τ 以年计。

    k=None 或 scale_year=None 时返回 None（不臆造寿命参数）。
    默认 **不重归一化**（normalize=False），与交接包 lifetime_tail.renormalize_truncated_pmf=False 一致：
    截断尾部质量显式保留在 Σf < 1 中，由调用方用 L(T)=1−Σf 交代存活比例，
    不得把尾部摊回各年——否则会人为放大退役量。
    """
    if k is None or scale_year is None:
        return None
    if k <= 0 or scale_year <= 0:
        raise ValueError("Weibull 参数必须为正")
    cdf = lambda t: 0.0 if t <= 0 else 1.0 - math.exp(-((t / scale_year) ** k))
    pmf = [cdf(t) - cdf(t - 1) for t in taus]
    total = sum(pmf)
    if total <= 0:
        raise ValueError("寿命分布总概率为 0，请检查参数")
    return [p / total for p in pmf] if normalize else pmf


def weibull_survival(k: float, scale_year: float, age: float) -> float:
    """L(age) = exp(−(age/scale)^k)；age=0 返回 1（年末入队、进入年龄 0）。"""
    if k <= 0 or scale_year <= 0:
        raise ValueError("Weibull 参数必须为正")
    return 1.0 if age <= 0 else math.exp(-((age / scale_year) ** k))


def weibull_exit_pmf(k: float, scale_year: float, max_age: int = 80) -> list[float]:
    """f(age) = L(age−1) − L(age)，age ≥ 1；与 F(age)−F(age−1) 等价，尾部不归一化。"""
    return [weibull_survival(k, scale_year, a - 1) - weibull_survival(k, scale_year, a)
            for a in range(1, max_age + 1)]


def retirement_flow(installations: Series,
                    life_pmf: list[float] | None,
                    collection_rate: float | None,
                    delay_offset: int = 1) -> tuple[Series, Series]:
    """由历史装机量 + 寿命分布 + 正规收集率计算退役量与已收集量。

    公式：R(t) = Σ_τ I(t−τ)·f(τ)；  已收集量 = R(t)·c
    其中 τ 从 delay_offset 起计；历史装机量不足的年份返回 None（不推进任何数值）。
    """
    if life_pmf is None or collection_rate is None:
        return empty_series("retired_pack", "t/a", (min(installations.years()), max(installations.years()))), \
               empty_series("collected_pack", "t/a", (min(installations.years()), max(installations.years())))
    years = installations.years()
    retired = Series("retired_pack", "t/a", {})
    collected = Series("collected_pack", "t/a", {})
    for y in years:
        tau_terms = [(tau, life_pmf[tau - delay_offset]) for tau in range(delay_offset, delay_offset + len(life_pmf))]
        missing = [tau for tau, _ in tau_terms if installations.values.get(y - tau) is None]
        if missing:
            retired.values[y] = None
            collected.values[y] = None
            continue
        total = sum(installations.values[y - tau] * w for tau, w in tau_terms)  # type: ignore[operator]
        retired.values[y] = total
        collected.values[y] = total * collection_rate
    return retired, collected


def first_retirement_year(retired: Series) -> int | None:
    """第一个可算出退役量的年份（决定存量递推的起点）。"""
    for y in retired.years():
        if retired.values[y] is not None:
            return y
    return None


def in_use_stock(installations: Series,
                 retired: Series,
                 initial_stock: float | None) -> tuple[Series, str]:
    """在用存量递推：S(t) = S(t−1) + I(t) − R(t)。

    initial_stock 未定则整条序列为 None（不以 0 起算）；递推从第一个可算退役量的年份开始，
    该年之前留空，避免把"历史不足"误写成"存量 = 0"。
    """
    years = installations.years()
    stock = Series("in_use_stock", "t", {})
    if initial_stock is None:
        for y in years:
            stock.values[y] = None
        return stock, "not_available(initial_stock 未定，禁止以 0 起算)"
    start = first_retirement_year(retired)
    if start is None:
        for y in years:
            stock.values[y] = None
        return stock, "not_available(退役流量未定，无递推起点)"
    prev: float | None = initial_stock
    for y in years:
        if y < start:
            stock.values[y] = None
            continue
        inflow, outflow = installations.values.get(y), retired.values.get(y)
        if prev is None or inflow is None or outflow is None:
            stock.values[y] = None
            prev = None
            continue
        prev = prev + inflow - outflow
        stock.values[y] = prev
    complete = all(stock.values[y] is not None for y in range(start, years[-1] + 1))
    return stock, "computed" if complete else "partial"


def stock_flow_identity_check(installations: Series, retired: Series,
                              initial_stock: float | None, final_stock: float | None,
                              start_year: int | None = None,
                              end_year: int | None = None) -> dict[str, object]:
    """存量-流量恒等式：ΣI − ΣR − (S_end − S_start) = 0（相对容差 STOCK_FLOW_TOL）。

    initial_stock 指 start_year−1 年的存量；窗口内任一年缺数则返回 not_available。
    """
    start = start_year if start_year is not None else first_retirement_year(retired)
    if start is None or initial_stock is None or final_stock is None:
        return {"status": "not_available", "residual": None,
                "note": "递推起点/初始存量/末期存量缺失，不以 0 代入"}
    end = end_year if end_year is not None else installations.years()[-1]
    if any(installations.values.get(y) is None or retired.values.get(y) is None for y in range(start, end + 1)):
        return {"status": "partial", "residual": None, "note": "窗口内存在缺失年份，仅可作局部校验"}
    inflow = sum(installations.values[y] for y in range(start, end + 1))  # type: ignore[misc]
    outflow = sum(retired.values[y] for y in range(start, end + 1))  # type: ignore[misc]
    residual = inflow - outflow - (final_stock - initial_stock)
    rel = abs(residual) / max(abs(inflow), 1e-12)
    return {"status": "pass" if rel < STOCK_FLOW_TOL else "fail", "residual": residual,
            "relative_error": rel, "note": f"容差 {STOCK_FLOW_TOL}"}


def li_in_use_stock(stock: Series, li_fraction_of_pack: float | None) -> Series:
    """在用锂存量 = 在用整包存量 × 整包 Li 质量分数。

    整包 Li 质量分数依赖粉料品位基准确认（M02/M03 与湿基/元素基口径），当前为 None，
    因此结果整列 None。
    """
    out = Series("li_in_use_stock", "t Li", {})
    for y, v in stock.values.items():
        out.values[y] = None if (v is None or li_fraction_of_pack is None) else v * li_fraction_of_pack
    return out


# ----------------------------------------------------------------------------- 缺失输入登记
DMFA_GAPS = (
    {"gap_id": "DMFA-01", "key": "历史/情景装机流入量 I(t)，分 LFP 与 NMC",
     "unit": "t/a 或 GWh/a", "reason": "任务书核心问题要求预测规划期退役量，但交接包只给了单一年度 8 万 t/a 规划来料",
     "source_candidates": "文献 3（Wu et al., 2024）、文献 5（Zhang et al., 2025）的装机/保有量序列",
     "blocks": "退役流量、在用存量、在用锂存量"},
    {"gap_id": "DMFA-02", "key": "动力电池寿命分布形状参数 k（Weibull）",
     "unit": "—", "reason": "任务书要求声明寿命分布参数出处；交接包未提供",
     "source_candidates": "文献 3/5 的退役年限分布或 GB/T 34015 系列梯次判定口径",
     "blocks": "退役流量"},
    {"gap_id": "DMFA-03", "key": "寿命分布尺度参数 scale（年）",
     "unit": "a", "reason": "同上",
     "source_candidates": "文献 3/5", "blocks": "退役流量"},
    {"gap_id": "DMFA-04", "key": "正规收集率 c（分年份或情景）",
     "unit": "%", "reason": "任务书核心问题要求协同考虑正规收集率；交接包未提供",
     "source_candidates": "工信部规范条件（R02 类政策文件）、文献 5",
     "blocks": "已收集量、再生处理量"},
    {"gap_id": "DMFA-05", "key": "规划期初在用整包存量 S(0)",
     "unit": "t", "reason": "存量递推的初值；未定则不得以 0 起算",
     "source_candidates": "区域保有量统计或文献 3 的区域在用存量",
     "blocks": "在用存量、在用锂存量"},
    {"gap_id": "DMFA-06", "key": "整包级 Li 质量分数（元素基、干基）",
     "unit": "kg Li/t 整包", "reason": "粉料品位基准未确认（JR23_NMC 0.0434 / JR23_LFP 0.03425 仅参考）",
     "source_candidates": "交接包 reference_li_assay.csv + M02 分选收率",
     "blocks": "在用锂存量"},
    {"gap_id": "DMFA-07", "key": "收集点/梯次中心/再生基地的空间参数（数量、运输半径）",
     "unit": "—", "reason": "任务书空间网络优化问题的输入；属规划扩展，交接包未涉及",
     "source_candidates": "文献 5、区域路网与行政区划数据",
     "blocks": "空间网络布局（本骨架未实现）"},
)

REUSE_LINK = {"gap_id": "M01", "key": "梯次利用分流比 f_reuse",
              "note": "沿用交接包编号（未解决输入 M01）：梯次分流决定退役包进入再生环节的比例"}


def readiness_rows() -> list[dict[str, object]]:
    rows = [
        {"module": "time_axis", "status": "READY(assumption)",
         "blocking": "—", "note": HORIZON_NOTE},
        {"module": "installation_inflow_series", "status": "BLOCKED", "blocking": "DMFA-01",
         "note": "无逐年装机/流入序列，时序无法起算"},
        {"module": "lifetime_distribution", "status": "BLOCKED", "blocking": "DMFA-02;DMFA-03",
         "note": "Weibull 参数未定；接口 weibull_pmf() 已实现"},
        {"module": "retirement_flow", "status": "BLOCKED", "blocking": "DMFA-01;DMFA-02;DMFA-03;DMFA-04",
         "note": "接口 retirement_flow() 已实现"},
        {"module": "in_use_stock", "status": "BLOCKED", "blocking": "DMFA-01;DMFA-05",
         "note": "接口 in_use_stock() 已实现；初值未定则整列为空"},
        {"module": "reuse_split", "status": "BLOCKED", "blocking": "M01",
         "note": REUSE_LINK["note"]},
        {"module": "li_in_use_stock", "status": "BLOCKED", "blocking": "DMFA-06;M02",
         "note": "接口 li_in_use_stock() 已实现"},
        {"module": "stock_flow_identity_check", "status": "BLOCKED", "blocking": "DMFA-01;DMFA-05",
         "note": "校验函数已实现，容差 1e-6（结构校验用，非 Li 守恒容差）"},
        {"module": "spatial_network_optimization", "status": "NOT_IMPLEMENTED", "blocking": "DMFA-07",
         "note": "本骨架只到园区尺度，空间网络属后续扩展"},
    ]
    return rows


# ----------------------------------------------------------------------------- 输出
def write_csv(name: str, rows: list[dict[str, object]], fieldnames: list[str]) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = DATA_DIR / name
    with out.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: ("" if row.get(k) is None else row.get(k)) for k in fieldnames})
    return out


def time_axis_rows(horizon: tuple[int, int]) -> list[dict[str, object]]:
    start, end = horizon
    rows = []
    for y in range(start, end + 1):
        rows.append({
            "year": y,
            "install_inflow_t": None,
            "retired_pack_t": None,
            "collected_pack_t": None,
            "to_reuse_t": None,
            "to_recycle_t": None,
            "in_use_stock_t": None,
            "li_in_use_stock_t": None,
            "status": "not_available(缺 DMFA-01/02/03/04/05/06 与 M01)",
        })
    return rows


def parameter_rows(horizon: tuple[int, int]) -> list[dict[str, object]]:
    rows = []
    for gap in DMFA_GAPS:
        rows.append({
            "parameter_id": gap["gap_id"],
            "key": gap["key"],
            "value": None,
            "unit": gap["unit"],
            "status": "unresolved",
            "origin": "本模块新增登记（A 交接包未含）",
            "source_candidate": gap["source_candidates"],
            "blocks": gap["blocks"],
            "reason": gap["reason"],
        })
    rows.append({
        "parameter_id": REUSE_LINK["gap_id"], "key": REUSE_LINK["key"], "value": None,
        "unit": "%", "status": "unresolved", "origin": "A 交接包 unresolved_inputs",
        "source_candidate": "组内口径（SOH 阈值与数量分布）", "blocks": "梯次分流、再生处理量",
        "reason": REUSE_LINK["note"],
    })
    rows.append({
        "parameter_id": "SCENARIO-HORIZON",
        "key": f"规划期 {horizon[0]}–{horizon[1]}",
        "value": f"{horizon[0]}–{horizon[1]}", "unit": "年",
        "status": "assumption_pending_confirmation", "origin": "任务书 L79 示例区间",
        "source_candidate": "assignment_documentation.md L79",
        "blocks": "仅影响时间轴长度，不影响单年方程", "reason": HORIZON_NOTE,
    })
    return rows


# ----------------------------------------------------------------------------- 接口自检
def interface_self_test() -> list[tuple[str, str, str]]:
    """用**合成数据**验证方程实现（合成值不写入 CSV、不进入报告）。"""
    results: list[tuple[str, str, str]] = []

    taus = list(range(1, 31))
    pmf = weibull_pmf(2.5, 12.0, taus)
    tail_survival = 1.0 - sum(pmf)
    ok_tail = abs(tail_survival - weibull_survival(2.5, 12.0, 30)) < 1e-12 and sum(pmf) < 1.0
    results.append(("寿命尾部保留而不重归一化", "PASS" if ok_tail else "FAIL",
                    f"Σf(τ≤30)={sum(pmf):.9f}，L(30)={tail_survival:.9f}（合成参数 k=2.5, scale=12）"))

    pmf_alt = weibull_exit_pmf(2.5, 12.0, 30)
    ok_eq = all(abs(a - b) < 1e-15 for a, b in zip(pmf, pmf_alt))
    results.append(("F 差分与 L 差分等价", "PASS" if ok_eq else "FAIL",
                    "f(age)=F(age)−F(age−1)=L(age−1)−L(age)，30 年逐点一致"))

    synthetic_inflow = Series("I", "t/a", {y: 1000.0 for y in range(1940, 2041)})
    retired, collected = retirement_flow(synthetic_inflow, pmf, 0.5)
    ok = retired.values[2040] is not None and collected.values[2040] == retired.values[2040] * 0.5
    results.append(("退役流量与收集率传导", "PASS" if ok else "FAIL",
                    f"R(2040)={retired.values[2040]:.3f} t，已收集={collected.values[2040]:.3f} t（合成）"))

    stock, state = in_use_stock(synthetic_inflow, retired, initial_stock=8000.0)
    results.append(("在用存量递推", "PASS" if state == "computed" else "FAIL", f"状态={state}（合成初值 8,000 t）"))

    check = stock_flow_identity_check(synthetic_inflow, retired, 8000.0, stock.values[2040])
    residual, rel = check.get("residual"), check.get("relative_error")
    detail = ("残差与相对误差不可算（序列不完整）" if residual is None or rel is None
              else f"残差={residual:.3e}，相对误差={rel:.3e}（合成）")
    results.append(("存量-流量恒等式", str(check["status"]).upper(), detail))

    hijacked, _ = in_use_stock(synthetic_inflow, retired, initial_stock=None)
    results.append(("初值缺失时不归零", "PASS" if hijacked.is_empty() else "FAIL",
                    "初值 None → 整列 None（不出现 0.0）"))

    no_li = li_in_use_stock(stock, li_fraction_of_pack=None)
    results.append(("Li 分数缺失时不出数", "PASS" if no_li.is_empty() else "FAIL",
                    "整包 Li 分数 None → 在用锂存量整列 None"))

    return results


# ----------------------------------------------------------------------------- 主流程
def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="dMFA 接口库与方程自检（默认不写空表）")
    parser.add_argument("--start", type=int, default=DEFAULT_HORIZON[0], help="规划期起始年")
    parser.add_argument("--end", type=int, default=DEFAULT_HORIZON[1], help="规划期终止年")
    parser.add_argument("--self-test", action="store_true", help="打印合成数据自检结果")
    parser.add_argument("--emit-skeleton", action="store_true",
                        help="额外输出空表骨架（dmfa_skeleton_*.csv），不覆盖真实结果")
    args = parser.parse_args(argv)
    horizon = (args.start, args.end)
    if horizon[1] <= horizon[0]:
        parser.error("终止年必须大于起始年")

    print("=" * 78)
    print("dMFA 接口库 · 稳态工序 MFA 之外的时间维模块")
    print("=" * 78)
    print(f"规划期参数：{horizon[0]}–{horizon[1]}（{horizon[1] - horizon[0] + 1} 年）｜{HORIZON_NOTE}")
    print("真实市域结果由 dmfa_yichang.py 产出；本文件只提供方程、接口与合成数据自检。\n")

    print("[1] 方程定义")
    print("    (1) 生存函数：L(age)=exp(−(age/scale)^k)，L(0)=1")
    print("    (2) 退役分布：f(age)=L(age−1)−L(age)，age≥1；尾部不重新归一化")
    print("    (3) 退役流量：R(t)=Σ_τ I(t−τ)·f(τ)；已收集 C(t)=c·R(t)")
    print("    (4) 在用存量：S(t)=Σ_u I(u)·L(t−u)（S(0) 必须显式给定，不得默认 0）")
    print("    (5) 在用锂存量：Li(t)=S(t)·w_Li,pack（按车型配套强度，不用粉料品位替代）")
    print("    (6) 结构校验：ΣI − ΣR − (S_end − S_0) ≈ 0（相对容差 1e-6；Li 守恒仍严格 <5e-4）")

    print("\n[2] 接口字段（数值一律来自 A_dMFA数据交接包_20261103，本文件不解释数值）")
    for row in parameter_rows(horizon):
        print(f"    {row['parameter_id']:<10} {row['key']}  [{row['unit']}]")

    print("\n[3] 模块就绪状态：由 dmfa_yichang.py 按数据集 module_gates 输出，本文件不重复维护")

    if args.emit_skeleton:
        print("\n[4] 空表骨架（数值列全部为空，表示无数而非 0）")
        axis = time_axis_rows(horizon)
        print(f"    时间轴 {len(axis)} 行：{horizon[0]}–{horizon[1]}，8 列中 7 列为空")
        write_csv("dmfa_skeleton_time_axis.csv", axis,
                  ["year", "install_inflow_t", "retired_pack_t", "collected_pack_t", "to_reuse_t",
                   "to_recycle_t", "in_use_stock_t", "li_in_use_stock_t", "status"])
        write_csv("dmfa_skeleton_parameters.csv", parameter_rows(horizon),
                  ["parameter_id", "key", "value", "unit", "status", "origin", "source_candidate", "blocks", "reason"])
        write_csv("dmfa_skeleton_readiness.csv", readiness_rows(), ["module", "status", "blocking", "note"])
        print("    → data_cohort/dmfa_skeleton_time_axis.csv、dmfa_skeleton_parameters.csv、dmfa_skeleton_readiness.csv")
        assert len(axis) == horizon[1] - horizon[0] + 1
        assert all(row[k] is None for row in axis for k in
                   ("install_inflow_t", "retired_pack_t", "collected_pack_t", "to_reuse_t",
                    "to_recycle_t", "in_use_stock_t", "li_in_use_stock_t")), "空表不得出现数值"
        print("    PASS 时间轴长度与空值约束（空表不产出任何数值）")

    if args.self_test:
        print("\n[5] 接口自检（**合成数据**，不写入 CSV、不进入报告）")
        for name, status, detail in interface_self_test():
            print(f"    {status:<4} {name} — {detail}")
        print("\n完成：dMFA 方程与接口可用；真实计算由 dmfa_yichang.py 完成。")
    else:
        print("\n完成：接口库已就绪（加 --self-test 查看方程自检）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
