#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""案例二：工业园区 CO2 捕集 + 绿氢合成绿色甲醇 的 MFA-LCA-TEA 联动核算。

功能单位：1 t（1000 kg）聚合级精甲醇，门到门（Cradle-to-Gate）。

脚本覆盖讲义三项核心任务：
  1. 反应-循环回路物料衡算（单程转化率 25%、分流比 99% 循环 / 1% 驰放），
     求解循环比、总碳利用率，并做 C/H/O 元素闭合校验；
  2. 绿电悖论 LCA 双情景核算；
  3. 电价 0.05~0.60 元/kWh 的 LCOM / 绿色溢价 / MAC 敏感性，
     以及碳价 100 元/t 下的商业自平衡临界电价；
  4. 课堂研讨题：光伏-自备电混供的最低绿电占比。

数据源：../case_files/data_cohort/ 下三份 CSV。
输出：results_summary.json、results_table.csv、tea_sensitivity.csv、lca_summary.csv
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
DATA_DIR = HERE.parent / "case_files" / "data_cohort"

# ---- 分子量与原子量（与讲义一致） ----
M_CO2 = 44.01
M_H2 = 2.016
M_MEOH = 32.04
M_H2O = 18.016
M_O2 = 31.998
A_C, A_H, A_O = 12.011, 1.008, 15.999

# ---- 讲义给定工况 ----
X_SP = 0.25            # 反应器 CO2 单程转化率
RECYCLE_FRAC = 0.99    # 分离器气相中回流比例，其余 1% 驰放
FOSSIL_PRICE = 2500.0  # 煤制甲醇市场价，元/t
FOSSIL_GWP = 2600.0    # 煤制甲醇全生命周期碳足迹，kg CO2e/t
CARBON_PRICE = 100.0   # 全国碳市场碳价，元/t CO2e
E_TOTAL = 10826.0      # 吨甲醇综合电耗，kWh/t
CO2_CREDIT = 1423.0    # 原料 CO2 固定信用，kg CO2e/t

# 课堂研讨题参数
EF_COAL = 0.75         # 自备燃煤电碳因子，kg CO2e/kWh
EF_PV = 0.04           # 屋顶光伏碳因子，kg CO2e/kWh


# =====================================================================
# 数据读取
# =====================================================================
def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    mfa = pd.read_csv(DATA_DIR / "mfa_reaction_recycle_balance.csv")
    lci = pd.read_csv(DATA_DIR / "lca_grid_scenarios_lci.csv")
    tea = pd.read_csv(DATA_DIR / "tea_lcom_sensitivity_data.csv")
    return mfa, lci, tea


def stream_row(mfa: pd.DataFrame, name: str) -> pd.Series:
    rows = mfa.loc[mfa["stream_name"] == name]
    if len(rows) != 1:
        raise KeyError(f"物流 {name} 记录数为 {len(rows)}，应为 1")
    return rows.iloc[0]


def mass(mfa: pd.DataFrame, name: str) -> float:
    return float(stream_row(mfa, name)["mass_flow_per_ton_product_kg"])


def kmol(mfa: pd.DataFrame, name: str) -> float:
    return float(stream_row(mfa, name)["molar_flow_per_ton_product_kmol"])


# =====================================================================
# 模块一：MFA 反应-循环回路
# =====================================================================
def mfa_analysis(mfa: pd.DataFrame) -> dict:
    """节点质量守恒 + 循环回路解析 + C/H/O 元素闭合。"""
    names = {
        "co2": "Fresh_CO2_Feed",
        "h2": "Fresh_H2_Feed",
        "water_net": "Demineralized_Water_Net",
        "water_total": "Electrolyzer_Total_Water",
        "o2": "Byproduct_Oxygen",
        "recycle": "Recycle_Gas_Loop",
        "reactor_in": "Reactor_Inlet_Mix",
        "reactor_out": "Reactor_Outlet_Stream",
        "crude": "Crude_Methanol_Liquid",
        "offgas": "Separator_Offgas",
        "purge": "Purge_Gas",
        "product": "Refined_Methanol_Product",
        "bottoms": "Distillation_Bottoms_Water",
    }

    # --- 1) 各节点质量守恒（单位 kg/t 甲醇） ---
    checks = [
        ("混合器：CO2+H2+循环气 = 反应器进料",
         mass(mfa, names["co2"]) + mass(mfa, names["h2"]) + mass(mfa, names["recycle"]),
         mass(mfa, names["reactor_in"])),
        ("反应器：进料 = 出料（质量守恒）",
         mass(mfa, names["reactor_in"]), mass(mfa, names["reactor_out"])),
        ("冷凝分离：出料 = 粗甲醇 + 气相",
         mass(mfa, names["reactor_out"]),
         mass(mfa, names["crude"]) + mass(mfa, names["offgas"])),
        ("循环分流：气相 = 循环气 + 驰放气",
         mass(mfa, names["offgas"]),
         mass(mfa, names["recycle"]) + mass(mfa, names["purge"])),
        ("精馏：粗甲醇 = 产品 + 生成水",
         mass(mfa, names["crude"]),
         mass(mfa, names["product"]) + mass(mfa, names["bottoms"])),
        ("电解槽进水：总进水 = 净补水 + 精馏回流水",
         mass(mfa, names["water_total"]),
         mass(mfa, names["water_net"]) + mass(mfa, names["bottoms"])),
    ]
    balance_rows = []
    for label, lhs, rhs in checks:
        residual = lhs - rhs
        balance_rows.append({
            "node": label,
            "in_kg": round(lhs, 2),
            "out_kg": round(rhs, 2),
            "residual_kg": round(residual, 2),
            "residual_pct": round(100 * residual / lhs, 4) if lhs else 0.0,
            "passed": abs(residual) <= 0.5,
        })

    # --- 2) 循环比 ---
    fresh_mass = mass(mfa, names["co2"]) + mass(mfa, names["h2"])
    fresh_kmol = kmol(mfa, names["co2"]) + kmol(mfa, names["h2"])
    recycle_ratio_mass = mass(mfa, names["reactor_in"]) / fresh_mass
    recycle_ratio_molar = kmol(mfa, names["reactor_in"]) / fresh_kmol
    backflow_ratio = mass(mfa, names["recycle"]) / fresh_mass

    # --- 3) 回路代数解：单程 25%、99% 回流下的稳态 ---
    fresh_co2 = kmol(mfa, names["co2"])
    inlet_co2 = fresh_co2 / (1.0 - RECYCLE_FRAC * (1.0 - X_SP))
    reacted_co2 = X_SP * inlet_co2
    recycle_co2 = RECYCLE_FRAC * (1.0 - X_SP) * inlet_co2
    purge_co2 = (1.0 - RECYCLE_FRAC) * (1.0 - X_SP) * inlet_co2
    loop_meoh_kmol = reacted_co2                 # 近似：转化碳全部进入甲醇
    loop_meoh_kg = loop_meoh_kmol * M_MEOH
    loop_carbon_util = reacted_co2 / fresh_co2

    # --- 4) 数据口径的碳利用率 ---
    product_kmol = kmol(mfa, names["product"])   # 纯甲醇，1 kmol 对应 1 kmol C
    carbon_util = product_kmol / fresh_co2
    purge_c_kmol = fresh_co2 - product_kmol
    purge_c_kg = purge_c_kmol * A_C

    # --- 5) C/H/O 元素闭合（合成岛边界：CO2 + H2 进；甲醇 + 生成水 + 驰放气出） ---
    h2_kmol = kmol(mfa, names["h2"])
    water_kmol = kmol(mfa, names["bottoms"])
    ele_in = {
        "C": fresh_co2,                          # kmol C
        "H": 2.0 * h2_kmol,                      # kmol H
        "O": 2.0 * fresh_co2,                    # kmol O
    }
    product_e = {"C": product_kmol, "H": 4.0 * product_kmol, "O": product_kmol}
    water_e = {"H": 2.0 * water_kmol, "O": water_kmol}
    purge_e = {k: ele_in[k] - product_e.get(k, 0.0) - water_e.get(k, 0.0) for k in ele_in}

    atom_mass = {"C": A_C, "H": A_H, "O": A_O}
    purge_elem_kg = {k: purge_e[k] * atom_mass[k] for k in purge_e}
    purge_mass = mass(mfa, names["purge"])
    purge_inerts = purge_mass - sum(purge_elem_kg.values())

    # 按 CSV 组分正算驰放气元素量，作为独立校核
    row = stream_row(mfa, names["purge"])
    comp = {
        "CO2": row["co2_wt_pct"] / 100,
        "H2": row["h2_wt_pct"] / 100,
        "MeOH": row["meoh_wt_pct"] / 100,
        "H2O": row["h2o_wt_pct"] / 100,
        "O2": row["o2_wt_pct"] / 100,
    }
    species_e = {
        "CO2": {"C": A_C / M_CO2, "O": 2 * A_O / M_CO2},
        "H2": {"H": 2 * A_H / M_H2},
        "MeOH": {"C": A_C / M_MEOH, "H": 4 * A_H / M_MEOH, "O": A_O / M_MEOH},
        "H2O": {"H": 2 * A_H / M_H2O, "O": A_O / M_H2O},
        "O2": {"O": 1.0},
    }
    purge_raw = {k: 0.0 for k in ("C", "H", "O")}
    for sp, frac in comp.items():
        for elem, share in species_e[sp].items():
            purge_raw[elem] += purge_mass * frac * share

    element_rows = []
    for k in ("C", "H", "O"):
        residual = purge_raw[k] - purge_elem_kg[k]
        element_rows.append({
            "element": k,
            "input_kg": round(ele_in[k] * atom_mass[k], 3),
            "product_kg": round(product_e.get(k, 0.0) * atom_mass[k], 3),
            "water_kg": round(water_e.get(k, 0.0) * atom_mass[k], 3),
            "purge_by_difference_kg": round(purge_elem_kg[k], 3),
            "purge_from_csv_kg": round(purge_raw[k], 3),
            "csv_minus_closure_kg": round(residual, 3),
            "closure_error_pct": 0.0,
        })

    return {
        "streams": {k: {"mass_kg": mass(mfa, v), "kmol": kmol(mfa, v)} for k, v in names.items()},
        "node_balance": balance_rows,
        "node_all_passed": all(r["passed"] for r in balance_rows),
        "recycle_ratio_mass": recycle_ratio_mass,
        "recycle_ratio_molar": recycle_ratio_molar,
        "backflow_ratio_mass": backflow_ratio,
        "loop": {
            "fresh_co2_kmol": fresh_co2,
            "reactor_inlet_co2_kmol": inlet_co2,
            "reacted_co2_kmol": reacted_co2,
            "recycle_co2_kmol": recycle_co2,
            "purge_co2_kmol": purge_co2,
            "meoh_kmol": loop_meoh_kmol,
            "meoh_kg": loop_meoh_kg,
            "carbon_utilization": loop_carbon_util,
        },
        "carbon": {
            "fresh_c_kmol": fresh_co2,
            "product_c_kmol": product_kmol,
            "utilization": carbon_util,
            "purge_c_kmol": purge_c_kmol,
            "purge_c_kg": purge_c_kg,
            "doc_utilization": 0.96,
            "deviation_pp": (carbon_util - 0.96) * 100,
        },
        "elements": element_rows,
        "purge_inerts_kg": purge_inerts,
        "purge_elements_kg": purge_elem_kg,
    }


# =====================================================================
# 模块二：LCA
# =====================================================================
def lca_analysis(lci: pd.DataFrame) -> dict:
    skip = {
        "Net_Life_Cycle_GWP_Total",
        "Fossil_Benchmark_CtM",
        "Net_GHG_Reduction_vs_Benchmark",
    }
    items = lci.loc[~lci["lci_inventory_item"].isin(skip)].copy()
    gwp_a = float(items["gwp_scenario_a_kgCO2e"].sum())
    gwp_b = float(items["gwp_scenario_b_kgCO2e"].sum())

    net_a = float(lci.loc[lci["lci_inventory_item"] == "Net_Life_Cycle_GWP_Total",
                         "gwp_scenario_a_kgCO2e"].iloc[0])
    net_b = float(lci.loc[lci["lci_inventory_item"] == "Net_Life_Cycle_GWP_Total",
                         "gwp_scenario_b_kgCO2e"].iloc[0])

    rows = []
    for _, r in items.iterrows():
        rows.append({
            "item": r["lci_inventory_item"],
            "stage": r["stage_process"],
            "flow": float(r["flow_per_ton_product"]),
            "unit": r["unit"],
            "gwp_a": float(r["gwp_scenario_a_kgCO2e"]),
            "gwp_b": float(r["gwp_scenario_b_kgCO2e"]),
        })

    def reduction(gwp: float) -> float:
        return (FOSSIL_GWP - gwp) / FOSSIL_GWP

    positive_b = items.loc[items["gwp_scenario_b_kgCO2e"] > 0, "gwp_scenario_b_kgCO2e"].sum()
    electricity_b = items.loc[
        items["lci_inventory_item"].str.startswith("Electricity_"),
        "gwp_scenario_b_kgCO2e",
    ].sum()

    return {
        "items": rows,
        "gwp_a": gwp_a,
        "gwp_b": gwp_b,
        "table_net_a": net_a,
        "table_net_b": net_b,
        "sum_matches_table": abs(gwp_a - net_a) < 0.05 and abs(gwp_b - net_b) < 0.05,
        "reduction_a": reduction(gwp_a),
        "reduction_b": reduction(gwp_b),
        "delta_ghg_t": (FOSSIL_GWP - gwp_a) / 1000.0,
        "electricity_share_b": float(electricity_b) / float(positive_b),
    }


# =====================================================================
# 模块三：TEA 与 MAC
# =====================================================================
def tea_analysis(tea: pd.DataFrame, delta_ghg_t: float) -> dict:
    df = tea.copy()
    df["lcom_calc"] = df["electricity_cost_rmb_per_t"] + df["non_electricity_cost_rmb_per_t"]
    df["green_premium_calc"] = df["lcom_calc"] - FOSSIL_PRICE
    df["mac_calc"] = df["green_premium_calc"] / delta_ghg_t
    df["lcom_check_diff"] = df["lcom_calc"] - df["lcom_rmb_per_t"]
    df["mac_check_diff"] = df["mac_calc"] - df["mac_rmb_per_tCO2e"]

    kwh_per_t = float(df["electricity_cost_rmb_per_t"].iloc[0] /
                      df["electricity_price_rmb_per_kwh"].iloc[0])
    non_elec = float(df["non_electricity_cost_rmb_per_t"].iloc[0])
    carbon_revenue = CARBON_PRICE * delta_ghg_t
    price_breakeven_carbon = (FOSSIL_PRICE + carbon_revenue - non_elec) / kwh_per_t
    price_breakeven_plain = (FOSSIL_PRICE - non_elec) / kwh_per_t

    at = df.loc[(df["electricity_price_rmb_per_kwh"] - 0.35).abs().idxmin()]
    low = df.loc[(df["electricity_price_rmb_per_kwh"] - 0.15).abs().idxmin()]
    grid = df.loc[(df["electricity_price_rmb_per_kwh"] - 0.55).abs().idxmin()]

    return {
        "table": df,
        "kwh_per_t": kwh_per_t,
        "non_electricity_cost": non_elec,
        "carbon_revenue": carbon_revenue,
        "price_breakeven_with_carbon": price_breakeven_carbon,
        "price_breakeven_plain": price_breakeven_plain,
        "scenario_035": at.to_dict(),
        "scenario_015": low.to_dict(),
        "scenario_grid_055": grid.to_dict(),
        "checks_passed": bool(
            df["lcom_check_diff"].abs().max() < 0.1 and df["mac_check_diff"].abs().max() < 0.2
        ),
    }


# =====================================================================
# 模块四：课堂研讨题（光伏占比临界值）
# =====================================================================
def classroom_mix_share() -> dict:
    """设绿电占比为 x，求 GWP_net(x) 恰好等于煤制甲醇基准的临界值。"""
    gwp_coal_only = E_TOTAL * EF_COAL - CO2_CREDIT
    # E*(EF_COAL - (EF_COAL-EF_PV)x) - 1423 <= 2600
    x_min = (EF_COAL - (FOSSIL_GWP + CO2_CREDIT) / E_TOTAL) / (EF_COAL - EF_PV)
    gwp_at = E_TOTAL * (EF_COAL - (EF_COAL - EF_PV) * x_min) - CO2_CREDIT
    return {
        "gwp_coal_only": gwp_coal_only,
        "x_min": x_min,
        "gwp_at_x_min": gwp_at,
        "pv_capacity_factor": 1200.0 / 8000.0,
    }


# =====================================================================
# 输出
# =====================================================================
def print_report(mfa_res: dict, lca_res: dict, tea_res: dict, mix: dict) -> None:
    line = "=" * 74
    print(line)
    print("案例二  MFA-LCA-TEA 联动核算  |  功能单位：1 t 绿色精甲醇")
    print(line)

    print("\n【一】MFA 节点质量守恒（kg/t 甲醇）")
    for r in mfa_res["node_balance"]:
        flag = "OK" if r["passed"] else "FAIL"
        print(f"  [{flag}] {r['node']}: {r['in_kg']:.2f} vs {r['out_kg']:.2f} "
              f"(Δ={r['residual_kg']:+.2f} kg, {r['residual_pct']:+.4f}%)")
    print(f"  节点闭合总体: {'全部通过' if mfa_res['node_all_passed'] else '存在不闭合节点'}")

    print("\n【二】循环回路")
    rr = mfa_res["recycle_ratio_mass"]
    rm = mfa_res["recycle_ratio_molar"]
    bf = mfa_res["backflow_ratio_mass"]
    print(f"  循环比（反应器总进气/新鲜气，质量基）= {rr:.3f}:1")
    print(f"  循环比（反应器总进气/新鲜气，摩尔基）= {rm:.3f}:1  ← 对应讲义 3.8:1")
    print(f"  回流比（循环气/新鲜气，质量基）= {bf:.3f}:1")
    lp = mfa_res["loop"]
    print(f"  稳态回流解：反应器入口 CO2={lp['reactor_inlet_co2_kmol']:.2f} kmol，"
          f"转化={lp['reacted_co2_kmol']:.2f} kmol，驰放 CO2={lp['purge_co2_kmol']:.3f} kmol")
    print(f"  回路理论甲醇产量={lp['meoh_kg']:.1f} kg（数据值 1000 kg）")
    cb = mfa_res["carbon"]
    print(f"  数据口径碳利用率={cb['utilization']*100:.2f}% "
          f"(讲义 96.0%，偏差 {cb['deviation_pp']:+.2f} pp)")
    print(f"  驰放气带出碳={cb['purge_c_kg']:.2f} kg/t "
          f"({cb['purge_c_kg']/(cb['fresh_c_kmol']*A_C)*100:.2f}% 新鲜碳)")

    print("\n【三】C/H/O 元素闭合（合成岛边界）")
    for e in mfa_res["elements"]:
        print(f"  {e['element']}: 输入 {e['input_kg']:.2f} kg = 产品 {e['product_kg']:.2f} "
              f"+ 生成水 {e['water_kg']:.2f} + 驰放(差减) {e['purge_by_difference_kg']:.2f} kg"
              f" | CSV 组分正算 {e['purge_from_csv_kg']:.2f} kg "
              f"(差 {e['csv_minus_closure_kg']:+.2f})")
    print(f"  差减法闭合误差 0.00%；驰放气惰性组分 {mfa_res['purge_inerts_kg']:.2f} kg")

    print("\n【四】LCA 双情景")
    print(f"  情景 A 100% 绿电：{lca_res['gwp_a']:.2f} kg CO2e/t，"
          f"较煤制甲醇减排 {lca_res['reduction_a']*100:.1f}%")
    print(f"  情景 B 区域电网：{lca_res['gwp_b']:.2f} kg CO2e/t，"
          f"较煤制甲醇 {'减排' if lca_res['reduction_b'] > 0 else '增排'} "
          f"{abs(lca_res['reduction_b'])*100:.1f}%")
    print(f"  清单逐项求和与表内合计一致：{'是' if lca_res['sum_matches_table'] else '否'}")
    print(f"  情景 B 电力排放占比：{lca_res['electricity_share_b']*100:.1f}%")

    print("\n【五】TEA 与 MAC")
    for key, label in (("scenario_015", "0.15 元/kWh 大基地消纳"),
                       ("scenario_035", "0.35 元/kWh 工商业绿电"),
                       ("scenario_grid_055", "0.55 元/kWh 区域电网")):
        s = tea_res[key]
        print(f"  {label}: LCOM={s['lcom_calc']:.2f} 元/t，"
              f"溢价={s['green_premium_calc']:+.2f}，MAC={s['mac_calc']:.2f} 元/t CO2e")
    print(f"  碳价 100 元/t 下的自平衡临界电价 = {tea_res['price_breakeven_with_carbon']:.4f} 元/kWh")
    print(f"  不计碳收益的平价临界电价 = {tea_res['price_breakeven_plain']:.4f} 元/kWh")
    print(f"  与 CSV 列交叉校核：{'通过' if tea_res['checks_passed'] else '不通过'}")

    print("\n【六】课堂研讨：光伏-自备电混供临界绿电占比")
    print(f"  纯自备煤电 GWP={mix['gwp_coal_only']:.1f} kg CO2e/t")
    print(f"  最低绿电占比 x_min={mix['x_min']*100:.2f}%，此时 GWP={mix['gwp_at_x_min']:.1f}")
    print(f"  光伏年利用 1200 h 对 8000 h 连续运行，容量因子仅 {mix['pv_capacity_factor']*100:.1f}%")
    print(line)


def export(mfa_res: dict, lca_res: dict, tea_res: dict, mix: dict) -> None:
    summary = {
        "functional_unit": "1 t refined methanol",
        "mfa": {
            "node_all_passed": mfa_res["node_all_passed"],
            "recycle_ratio_mass": round(mfa_res["recycle_ratio_mass"], 4),
            "recycle_ratio_molar": round(mfa_res["recycle_ratio_molar"], 4),
            "backflow_ratio_mass": round(mfa_res["backflow_ratio_mass"], 4),
            "carbon_utilization": round(mfa_res["carbon"]["utilization"], 6),
            "carbon_utilization_doc": mfa_res["carbon"]["doc_utilization"],
            "purge_carbon_kg": round(mfa_res["carbon"]["purge_c_kg"], 3),
            "loop": {k: round(v, 4) for k, v in mfa_res["loop"].items()},
            "elements": mfa_res["elements"],
            "node_balance": mfa_res["node_balance"],
        },
        "lca": {
            "gwp_a_kgco2e_per_t": round(lca_res["gwp_a"], 2),
            "gwp_b_kgco2e_per_t": round(lca_res["gwp_b"], 2),
            "reduction_vs_coal_a_pct": round(lca_res["reduction_a"] * 100, 2),
            "reduction_vs_coal_b_pct": round(lca_res["reduction_b"] * 100, 2),
            "delta_ghg_t_per_t": round(lca_res["delta_ghg_t"], 5),
        },
        "tea": {
            "lcom_015": round(tea_res["scenario_015"]["lcom_calc"], 2),
            "lcom_035": round(tea_res["scenario_035"]["lcom_calc"], 2),
            "lcom_grid_055": round(tea_res["scenario_grid_055"]["lcom_calc"], 2),
            "mac_015": round(tea_res["scenario_015"]["mac_calc"], 2),
            "mac_035": round(tea_res["scenario_035"]["mac_calc"], 2),
            "breakeven_price_with_carbon_100": round(
                tea_res["price_breakeven_with_carbon"], 4),
            "breakeven_price_plain": round(tea_res["price_breakeven_plain"], 4),
        },
        "classroom_mix": {
            "x_min_pct": round(mix["x_min"] * 100, 2),
            "gwp_at_x_min": round(mix["gwp_at_x_min"], 1),
            "pv_capacity_factor_pct": round(mix["pv_capacity_factor"] * 100, 1),
        },
    }
    (HERE / "results_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    # 情景汇总表
    rows = [
        {"scenario": "A 绿电 / 0.15 元", "lcom": tea_res["scenario_015"]["lcom_calc"],
         "gwp": lca_res["gwp_a"], "premium": tea_res["scenario_015"]["green_premium_calc"],
         "mac": tea_res["scenario_015"]["mac_calc"]},
        {"scenario": "A 绿电 / 0.35 元", "lcom": tea_res["scenario_035"]["lcom_calc"],
         "gwp": lca_res["gwp_a"], "premium": tea_res["scenario_035"]["green_premium_calc"],
         "mac": tea_res["scenario_035"]["mac_calc"]},
        {"scenario": "B 电网 / 0.55 元", "lcom": tea_res["scenario_grid_055"]["lcom_calc"],
         "gwp": lca_res["gwp_b"],
         "premium": tea_res["scenario_grid_055"]["green_premium_calc"],
         "mac": tea_res["scenario_grid_055"]["mac_calc"]},
    ]
    pd.DataFrame(rows).to_csv(HERE / "results_table.csv", index=False, encoding="utf-8-sig")

    tea_out = tea_res["table"][[
        "electricity_price_rmb_per_kwh", "electricity_cost_rmb_per_t",
        "non_electricity_cost_rmb_per_t", "lcom_calc", "green_premium_calc", "mac_calc",
    ]].copy()
    tea_out.columns = ["price_rmb_per_kwh", "electricity_cost", "non_electricity_cost",
                       "lcom", "green_premium", "mac"]
    tea_out.to_csv(HERE / "tea_sensitivity.csv", index=False, encoding="utf-8-sig")

    pd.DataFrame(lca_res["items"]).to_csv(
        HERE / "lca_summary.csv", index=False, encoding="utf-8-sig")


def main() -> None:
    mfa, lci, tea = load_data()
    mfa_res = mfa_analysis(mfa)
    lca_res = lca_analysis(lci)
    tea_res = tea_analysis(tea, lca_res["delta_ghg_t"])
    mix = classroom_mix_share()
    print_report(mfa_res, lca_res, tea_res, mix)
    export(mfa_res, lca_res, tea_res, mix)
    print(f"结果已导出至: {HERE}")


if __name__ == "__main__":
    main()
