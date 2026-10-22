#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
案例一：城市废旧 PET 瓶机械物理再生系统 —— MFA / LCA / TEA 联合核算

功能：
    1. 读取 data_cohort/ 下的三份 CSV，校验 MFA 质量守恒；
    2. 按功能单位（1 t 瓶级 rPET 颗粒）核算 LCA 净碳足迹；
    3. 按年产能折算固定成本，核算 TEA 平准化生产成本 LCOP；
    4. 覆盖四个情景：基准、100% 绿电、低收率(70%)、绿电+低收率。

运行：
    python case1_mfa_lca_tea.py

输出：
    控制台核算过程 + results_summary.json + results_table.csv
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent / "case_files" / "data_cohort"

# ---------------------------------------------------------------- 全局基准参数
REF_YIELD = 0.80                 # 基准主产品收率（80%）
PLANT_CAPACITY_BALES_T = 20_000  # 年处理废瓶砖量（t/a）
CAPEX_RMB = 28_000_000           # 总投资（元）
DEPRECIATION_YEARS = 10
SALVAGE_RATE = 0.05
WACC = 0.08
TAX_RATE = 0.25
RPET_PRICE = 7_600.0             # rPET 售价（元/t）
VIRGIN_PET_GWP = 2_250.0         # 原生 PET 基准碳足迹（kg CO2e/t）

# 讲义第四部分给出的基准 LCOP，用于口径核对（不参与模型计算）
LCOP_HANDOUT = 6_153.4
# 讲义表格中"新鲜水与烧碱药剂"的聚合口径（元/t），与 CSV 分项口径存在差异
HANDOUT_CHEM_AGGREGATE = 115.0


# ---------------------------------------------------------------- 数据读取
def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """读取 MFA、LCI、TEA 三份基础数据集。"""
    mfa = pd.read_csv(DATA_DIR / "mfa_mass_balance.csv", encoding="utf-8-sig")
    lci = pd.read_csv(DATA_DIR / "lci_emission_factors.csv", encoding="utf-8-sig")
    tea = pd.read_csv(DATA_DIR / "tea_cost_parameters.csv", encoding="utf-8-sig")
    return mfa, lci, tea


def _one(series: pd.Series, what: str) -> float:
    """取出唯一值，缺失或重复时直接报错，避免静默取错数。"""
    values = series.dropna().unique()
    if len(values) != 1:
        raise ValueError(f"{what} 期望唯一取值，实际得到 {values.tolist()}")
    return float(values[0])


def build_context(mfa: pd.DataFrame, lci: pd.DataFrame, tea: pd.DataFrame) -> dict:
    """把 CSV 中的参数整理成核算上下文（全部显式命名，便于溯源）。"""

    def ef(flow_name: str) -> float:
        return _one(lci.loc[lci["Flow_Name"] == flow_name, "Emission_Factor"], f"排放因子 {flow_name}")

    def price(name: str) -> float:
        return _one(tea.loc[tea["Parameter_Name"] == name, "Value"], f"TEA 参数 {name}")

    def value(name: str) -> float:
        return _one(tea.loc[tea["Parameter_Name"] == name, "Value"], f"TEA 参数 {name}")

    def mass(stage: str, substance: str) -> float:
        sel = mfa.loc[(mfa["Stage"] == stage) & (mfa["Substance_Good"] == substance), "Mass_kg"]
        return _one(sel, f"MFA 物流 {stage}/{substance}")

    # MFA：每 1000 kg 进料产生的需焚烧固废 = 标签 20 + HDPE 细料损失 5 + 杂色细粉 40
    incin_kg_per_bale = (
        mass("Debaling_Drying", "Labels_PP_PVC")
        + mass("Sink_Float", "HDPE_Fine_Loss")
        + mass("SSP_Extrusion", "Off_Spec_Fines")
    )
    hdpe_kg_per_bale = mass("Sink_Float", "Recovered_HDPE_Flakes")

    fixed_annual = (
        value("Labor_Headcount") * 100_000.0
        + value("Maintenance_Rate") / 100.0 * value("Total_Capital_Investment")
        + value("Total_Capital_Investment") * (1 - value("Salvage_Value_Rate") / 100.0) / value("Depreciation_Period")
    )

    return {
        # LCA 排放因子
        "ef_transport_per_kg": ef("Baled_PET_Transport"),
        "ef_steam": ef("Steam_Natural_Gas"),
        "ef_naoh": ef("NaOH_Chemical"),
        "ef_water": ef("Water_Tap"),
        "ef_wastewater": ef("Wastewater_Treatment"),
        "ef_hdpe": ef("HDPE_Avoided_Burden"),
        # TEA 单价
        "feed_price": price("Feedstock_Baled_PET"),
        "steam_price": price("Steam_Natural_Gas"),
        "naoh_price": price("NaOH_Caustic_Soda"),
        "water_price": price("Fresh_Water"),
        "waste_price": price("Solid_Waste_Disposal"),
        "hdpe_price": price("HDPE_Flake_Selling_Price"),
        # MFA 派生系数（每 1000 kg 瓶砖）
        "incin_kg_per_bale": incin_kg_per_bale,
        "hdpe_kg_per_bale": hdpe_kg_per_bale,
        "fixed_annual": fixed_annual,
        "capex": value("Total_Capital_Investment"),
        "capacity": value("Plant_Annual_Capacity"),
    }


# ---------------------------------------------------------------- 情景定义
@dataclass(frozen=True)
class Scenario:
    key: str
    label: str
    yield_rate: float
    electricity_ef: float      # kg CO2e/kWh
    electricity_price: float   # 元/kWh


SCENARIOS = [
    Scenario("baseline", "基准情景（常规工业电网）", REF_YIELD, 0.55, 0.65),
    Scenario("green", "绿电情景（100% 风光绿电）", REF_YIELD, 0.03, 0.70),
    Scenario("low_yield", "低收率情景（收率 70%，常规电网）", 0.70, 0.55, 0.65),
    Scenario("green_low_yield", "绿电 + 低收率（收率 70%）", 0.70, 0.03, 0.70),
]


# ---------------------------------------------------------------- 核算主体
def evaluate(sc: Scenario, ctx: dict) -> dict:
    """
    以 1 t rPET 为功能单位核算。

    规模折算假设：电、汽、碱、水、污水与固废均按"进料量"成比例变化。
    基准 80% 收率下 1 t rPET 对应 1.25 t 瓶砖，因此收率 Y 时的折算系数为
    scale = 0.80 / Y。
    """
    y = sc.yield_rate
    scale = REF_YIELD / y

    feed_t = 1.0 / y                                     # t 瓶砖 / t rPET
    incin_t = ctx["incin_kg_per_bale"] / 1000.0 * feed_t  # t 固废 / t rPET
    hdpe_t = ctx["hdpe_kg_per_bale"] / 1000.0 * feed_t    # t HDPE / t rPET

    # ---- LCA 清单（kg CO2e / t rPET）
    lca_items = {
        "原料运输": feed_t * 1000.0 * ctx["ef_transport_per_kg"],
        "电力消耗": 850.0 * scale * sc.electricity_ef,
        "热洗蒸汽": 2.0 * scale * ctx["ef_steam"],
        "烧碱药剂": 15.0 * scale * ctx["ef_naoh"],
        "新鲜水": 2.5 * scale * ctx["ef_water"],
        "污水处理": 2.2 * scale * ctx["ef_wastewater"],
        "副产 HDPE 信用": -hdpe_t * 1000.0 * ctx["ef_hdpe"],
    }
    gwp = sum(lca_items.values())
    reduction = (VIRGIN_PET_GWP - gwp) / VIRGIN_PET_GWP

    # ---- TEA 变动成本（元 / t rPET）
    variable_items = {
        "原料废瓶砖": feed_t * ctx["feed_price"],
        "电力动力": 850.0 * scale * sc.electricity_price,
        "天然气蒸汽": 2.0 * scale * ctx["steam_price"],
        "烧碱药剂": 15.0 * scale / 1000.0 * ctx["naoh_price"],
        "新鲜水": 2.5 * scale * ctx["water_price"],
        "固废处置": incin_t * ctx["waste_price"],
        "副产 HDPE 抵扣": -hdpe_t * ctx["hdpe_price"],
    }
    variable_cost = sum(variable_items.values())

    # ---- 固定成本按当年产量摊薄（收率下降 → 产量下降 → 吨成本上升）
    output_t = PLANT_CAPACITY_BALES_T * y
    depreciation = ctx["capex"] * (1 - SALVAGE_RATE) / DEPRECIATION_YEARS
    fixed_per_t = ctx["fixed_annual"] / output_t
    lcop = variable_cost + fixed_per_t

    # ---- 经济性指标
    gross_per_t = RPET_PRICE - lcop
    gross_annual = gross_per_t * output_t
    net_cash = gross_annual * (1 - TAX_RATE) + depreciation
    payback_static = ctx["capex"] / net_cash

    cumulative = -ctx["capex"]
    payback_dynamic = None
    for year in range(1, DEPRECIATION_YEARS + 1):
        discounted = net_cash / (1 + WACC) ** year
        if cumulative + discounted >= 0:
            payback_dynamic = year - 1 + (-cumulative) / discounted
            break
        cumulative += discounted

    return {
        "key": sc.key,
        "label": sc.label,
        "yield_rate": y,
        "electricity_ef": sc.electricity_ef,
        "electricity_price": sc.electricity_price,
        "feedstock_t_per_t": feed_t,
        "lca_items": lca_items,
        "gwp": gwp,
        "reduction_vs_virgin": reduction,
        "variable_items": variable_items,
        "variable_cost": variable_cost,
        "fixed_cost_per_t": fixed_per_t,
        "lcop": lcop,
        "output_t": output_t,
        "gross_per_t": gross_per_t,
        "gross_annual": gross_annual,
        "payback_static": payback_static,
        "payback_dynamic": payback_dynamic,
    }


# ---------------------------------------------------------------- 结果输出
def mfa_balance_check(mfa: pd.DataFrame) -> dict:
    """校验质量守恒，并返回物流汇总。"""
    body = mfa[mfa["Stage"] != "Balance_Check"]
    total_in = float(body.loc[body["Stage"] == "Input", "Mass_kg"].sum())
    total_out = float(body.loc[body["Stage"] != "Input", "Mass_kg"].sum())
    return {
        "total_in": total_in,
        "total_out": total_out,
        "balanced": abs(total_in - total_out) < 1e-6,
        "error": total_in - total_out,
    }


def print_report(results: list[dict], balance: dict) -> None:
    line = "=" * 78

    print(line)
    print("案例一  MFA - LCA - TEA 联合核算")
    print(line)

    print("\n【MFA 质量守恒校验】")
    print(f"  输入合计 : {balance['total_in']:>10.2f} kg")
    print(f"  输出合计 : {balance['total_out']:>10.2f} kg")
    print(f"  闭合误差 : {balance['error']:>10.2f} kg  ->  {'通过' if balance['balanced'] else '不通过'}")

    base = next(r for r in results if r["key"] == "baseline")

    for r in results:
        print("\n" + "-" * 78)
        print(f"情景：{r['label']}")
        print(f"  收率 Y={r['yield_rate']:.0%}   电耗因子={r['electricity_ef']:.2f} kg CO2e/kWh   "
              f"电价={r['electricity_price']:.2f} 元/kWh   吨产品耗瓶砖={r['feedstock_t_per_t']:.4f} t")

        print("\n  LCA 清单（kg CO2e / t rPET）：")
        for name, value in r["lca_items"].items():
            print(f"    {name:<16}{value:>10.3f}")
        print(f"    {'净碳足迹':<16}{r['gwp']:>10.3f}")
        print(f"    相对原生 PET 减碳 {r['reduction_vs_virgin']:.2%}"
              f"（原生基准 {VIRGIN_PET_GWP:.0f}）")

        print("\n  TEA 成本（元 / t rPET）：")
        for name, value in r["variable_items"].items():
            print(f"    {name:<16}{value:>10.3f}")
        print(f"    {'变动成本小计':<16}{r['variable_cost']:>10.3f}")
        print(f"    {'固定成本摊薄':<16}{r['fixed_cost_per_t']:>10.3f}")
        print(f"    {'LCOP':<16}{r['lcop']:>10.3f}")
        print(f"    年产量 {r['output_t']:.0f} t   吨毛利 {r['gross_per_t']:.1f} 元  "
              f"年毛利 {r['gross_annual'] / 1e4:.1f} 万元")
        dyn = f"{r['payback_dynamic']:.2f}" if r["payback_dynamic"] else "未回收"
        print(f"    静态回收期 {r['payback_static']:.2f} 年   动态回收期 {dyn} 年")

    # ---- 情景对比
    green = next(r for r in results if r["key"] == "green")
    low = next(r for r in results if r["key"] == "low_yield")
    print("\n" + line)
    print("【跨维联动与口径核对】")
    print(line)
    print(f"  绿电情景净碳足迹 {green['gwp']:.1f} kg CO2e/t，较基准 {base['gwp']:.1f} 下降 "
          f"{base['gwp'] - green['gwp']:.1f}（{(base['gwp'] - green['gwp']) / base['gwp']:.1%}）")
    print(f"  绿电情景 LCOP {green['lcop']:.1f} 元/t，较基准 {base['lcop']:.1f} 增加 "
          f"{green['lcop'] - base['lcop']:.1f} 元/t（+{(green['lcop'] / base['lcop'] - 1):.2%}）")
    print(f"  收率降至 70%：净碳足迹 {low['gwp']:.1f}（+{low['gwp'] - base['gwp']:.1f}），"
          f"LCOP {low['lcop']:.1f}（+{low['lcop'] - base['lcop']:.1f}）")

    # 讲义 6153.4 与 CSV 分项口径的差异分解
    chem_itemized = (
        base["variable_items"]["烧碱药剂"] + base["variable_items"]["新鲜水"]
    )
    chem_gap = HANDOUT_CHEM_AGGREGATE - chem_itemized
    dep_handout = CAPEX_RMB * (1 - SALVAGE_RATE) / DEPRECIATION_YEARS / 16_000  # 166.25 元/t
    mgmt_gap = 196.4 - dep_handout
    print("\n  基线 LCOP 口径核对：")
    print(f"    CSV 分项口径计算值        {base['lcop']:.2f} 元/t")
    print(f"    讲义基准值                {LCOP_HANDOUT:.2f} 元/t")
    print(f"    差额                      {LCOP_HANDOUT - base['lcop']:.2f} 元/t")
    print(f"      其中：水+碱聚合口径差    {chem_gap:.2f}（讲义 115.0 vs 分项 {chem_itemized:.2f}）")
    print(f"            管理保险费未分项    {mgmt_gap:.2f}（讲义 196.4 含折旧 {dep_handout:.2f}）")
    print("    说明：差额源于讲义汇总表口径，不影响情景间的增量结论。")


def export(results: list[dict], balance: dict) -> None:
    summary = {
        "mfa_balance": balance,
        "scenarios": [{k: v for k, v in r.items() if k not in ("lca_items", "variable_items")}
                      for r in results],
    }
    (BASE_DIR / "results_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    rows = []
    for r in results:
        row = {
            "情景": r["label"],
            "收率": f"{r['yield_rate']:.0%}",
            "电力碳因子_kgCO2e_per_kWh": r["electricity_ef"],
            "电价_元_per_kWh": r["electricity_price"],
            "吨产品耗瓶砖_t": round(r["feedstock_t_per_t"], 4),
            "净碳足迹_kgCO2e_per_t": round(r["gwp"], 2),
            "减碳率_vs原生PET": f"{r['reduction_vs_virgin']:.2%}",
            "变动成本_元_per_t": round(r["variable_cost"], 2),
            "固定成本摊薄_元_per_t": round(r["fixed_cost_per_t"], 2),
            "LCOP_元_per_t": round(r["lcop"], 2),
            "年产量_t": round(r["output_t"], 0),
            "年毛利_万元": round(r["gross_annual"] / 1e4, 2),
            "静态回收期_年": round(r["payback_static"], 2),
            "动态回收期_年": round(r["payback_dynamic"], 2) if r["payback_dynamic"] else None,
        }
        rows.append(row)
    pd.DataFrame(rows).to_csv(BASE_DIR / "results_table.csv", index=False, encoding="utf-8-sig")


def main() -> None:
    mfa, lci, tea = load_data()
    ctx = build_context(mfa, lci, tea)
    balance = mfa_balance_check(mfa)
    if not balance["balanced"]:
        raise SystemExit("MFA 质量不守恒，停止后续核算。")

    results = [evaluate(sc, ctx) for sc in SCENARIOS]
    print_report(results, balance)
    export(results, balance)
    print(f"\n结果已写入：{[p.name for p in (BASE_DIR / 'results_summary.json', BASE_DIR / 'results_table.csv')]}")


if __name__ == "__main__":
    main()
