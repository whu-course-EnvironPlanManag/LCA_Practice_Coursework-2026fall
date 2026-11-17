# -*- coding: utf-8 -*-
"""任务3：可追溯的MFA-LCA-TEA-Policy网格寻优与300 DPI决策图。

物质流分析 MFA (Material Flow Analysis)、全生命周期评价 LCA (Life Cycle
Assessment)、技术经济分析 TEA (Techno-Economic Analysis)。单位：单吨甲醇。

资料与公式：
* 工程背景2.1/2.2：直接调用任务1纯组分稳态守恒求解器，X=0.25；固定
  CSV新鲜进料及1000 kg产量。某些驰放比无非负解，记录为物料不可行，
  不截断负流量，也不使用框架中的经验碳利用率去代替守恒方程。
* 工程背景2.3：电耗=52*H2+255+155+120。资料没有循环气流量-压缩功
  曲线，故155 kWh保持工程定额；不能推导驰放比引起的真实电耗变化。
* 工程背景3.2、LCA CSV：GWP=电耗*混合电力因子+95-新鲜CO2-氧气信用。
  氧气信用用CSV的95.04，按正的信用量扣除一次，避免原表负号重复使用。
* 手册第二节明确场景：绿电/煤电价格0.20/0.32元/kWh，排放因子
  0.04/0.75 kg/kWh；不混用另一组区域电网0.035/0.55的情景系数。
* TEA CSV：基础成本=混合电费+1238.37元/t非电成本总额；不虚构其细分。
  背景4.1/4.2的8%、20年、8.20亿元CAPEX计算CRF及资本年金作信息核对；
  年金已属于非电成本，不重复加到1238.37上。
* 四张政策卡片：直接调用任务2，获得补贴、碳价、水税、环保税及否决状态。
* 手册任务3：60*50=3000组；剔除物料不可行、政策否决和非有限目标；
  最小化GWP与政策成本，以前沿各目标min-max归一化后的原点欧氏距离选B。
  常数目标归一化为0；若A/B/C重合，报告退化结果，不制造内点拐点。

严格未采用框架内缺乏工程依据的碳损失拟合、储能幂函数、压缩成本幂函数、
以及随驰放比增加的逸散修正。固定电耗与非电定额仅支持基准情景筛选，
不构成具备变负荷设备设计、储能/容量重配成本的完整工程优化结论。

运行本文件生成PNG(300 DPI)、SVG、PDF及CSV/JSON复现数据，均位于同组
figures_output。--self-test仅运行自检；--alignment-helper可指定科研绘图
审计工具audit_panel_alignment.py，执行外部严格对齐检查。默认亦检查实测
绘图区尺寸。程序不读写报告，不执行Git或网络操作。
"""

import argparse
from functools import lru_cache
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import unittest

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd

try:
    from task1_mfa_recycle_solver import load_streams, solve_mfa_balance, verify_element_conservation, MASS_COLUMN
    from task2_policy_vibe_engine import evaluate_policy_compliance
except ModuleNotFoundError:
    from .task1_mfa_recycle_solver import load_streams, solve_mfa_balance, verify_element_conservation, MASS_COLUMN
    from .task2_policy_vibe_engine import evaluate_policy_compliance

ROOT = Path(__file__).resolve().parent.parent
GREEN_PRICE, COAL_PRICE = 0.20, 0.32  # 手册第二节情景设定
GREEN_EF, COAL_EF = 0.04, 0.75
ANNUAL_CAPACITY_T = 100000.0
ANCHOR_KEYS = ("Anchor_A_Cost_Min", "Anchor_B_Knee_Point", "Anchor_C_Deep_Decarb")
MODEL_NOTES = [
    "使用手册光伏/自备煤电场景：价格0.20/0.32，排放因子0.04/0.75。",
    "任务1纯组分模型；原始CSV组成不自洽，不能认证真实全组成工况。",
    "固定新鲜进料、甲醇产量和25%单程转化率；无非负稳态解的驰放比被排除。",
    "电耗与非电成本保持资料定额，缺少变负荷压缩、电力波动和储能成本曲线。",
    "氧气与电解净补水采用CSV工程定额，不声称完成电解槽全物流闭合。",
    "所选场景绿电同时更便宜、更低碳；允许帕累托前沿退化及A/B/C重合。",
    "结果为3000组离散网格中的非支配解，不等同连续全局最优。",
]


def get_figures_output_dir():
    path = ROOT / "figures_output"
    path.mkdir(parents=True, exist_ok=True)
    return path


@lru_cache(maxsize=1)
def get_model_inputs():
    streams = load_streams()
    lci = pd.read_csv(ROOT / "data_cohort/lca_grid_scenarios_lci.csv", index_col="lci_inventory_item")
    tea = pd.read_csv(ROOT / "data_cohort/tea_lcom_sensitivity_data.csv")
    if not lci.index.is_unique or tea.empty:
        raise ValueError("LCI编号必须唯一，TEA输入不能为空")
    non_electric = tea["non_electricity_cost_rmb_per_t"].to_numpy(dtype=float)
    if not np.isfinite(non_electric).all() or not np.all(non_electric == non_electric[0]):
        raise ValueError("TEA非电成本必须为一致的有限工程定额")
    stage_names = ("Electricity_PEM_Electrolysis", "Electricity_CO2_Compression",
                   "Electricity_Recycle_Compressor", "Electricity_Distillation_Cooling")
    powers = [float(lci.loc[name, "flow_per_ton_product"]) for name in stage_names]
    if not all(math.isfinite(v) and v > 0 for v in powers):
        raise ValueError("各工段电耗必须为正有限值")
    if not np.allclose(powers, [streams["S02"][MASS_COLUMN] * 52, 255, 155, 120], rtol=0, atol=1e-8):
        raise ValueError("LCI电耗与工程背景2.3不符，拒绝静默更改定额")
    e_total = sum(powers)
    reconstructed = tea["electricity_price_rmb_per_kwh"] * e_total + non_electric[0]
    if not np.allclose(reconstructed, tea["lcom_rmb_per_t"], rtol=0, atol=0.005):
        raise ValueError("TEA总成本与电费+非电定额不一致")
    oxygen_credit = -float(lci.loc["Byproduct_Oxygen_Credit", "gwp_scenario_a_kgCO2e"])
    infra = sum(float(lci.loc[s, "gwp_scenario_a_kgCO2e"])
                for s in ("Direct_Fugitive_Emissions", "Infrastructure_and_Catalyst"))
    if not math.isclose(oxygen_credit, streams["S05"][MASS_COLUMN] * 0.06, abs_tol=1e-8):
        raise ValueError("氧气工程定额与LCI信用不符")
    crf = 0.08 * (1.08 ** 20) / (1.08 ** 20 - 1)
    capital_annuity = 820000000 * crf / ANNUAL_CAPACITY_T
    return {"streams": streams, "power_stages": powers, "e_total_kwh": e_total,
            "non_electric_cost": float(non_electric[0]), "infra": infra,
            "oxygen_credit": oxygen_credit, "crf": crf,
            "capital_annuity_rmb_per_t": capital_annuity}


@lru_cache(maxsize=128)
def _mfa_at_purge(r_purge):
    try:
        model = solve_mfa_balance(0.25, r_purge, streams=get_model_inputs()["streams"])
    except ValueError as error:
        return None, str(error)
    if not verify_element_conservation(model)["passed"]:
        raise ArithmeticError("任务1模型元素守恒检查失败")
    return model, ""


def simulate_park_methanol_system(f_green: float, r_purge: float) -> dict:
    """模拟一组指定范围工况；物料无解时保留该候选的失败记录，不编造目标。"""
    if not math.isfinite(f_green) or not 0 <= f_green <= 1:
        raise ValueError("f_green必须在[0,1]内")
    if not math.isfinite(r_purge) or not 0.004 <= r_purge <= 0.045:
        raise ValueError("r_purge必须在任务3指定的[0.004,0.045]内")
    inputs = get_model_inputs()
    result = {"f_green": float(f_green), "r_purge": float(r_purge)}
    model, reason = _mfa_at_purge(float(r_purge))
    result.update({"mfa_feasible": model is not None, "mfa_failure_reason": reason,
                   "compliance_status": "MFA_Infeasible", "gwp_net": math.nan,
                   "lcom_policy_adjusted": math.nan, "mac_policy_adjusted": math.nan})
    if model is None:
        return result
    e_total = inputs["e_total_kwh"]
    ef_blended = f_green * GREEN_EF + (1 - f_green) * COAL_EF
    price_blended = f_green * GREEN_PRICE + (1 - f_green) * COAL_PRICE
    gwp = e_total * ef_blended + inputs["infra"] - model["m_co2_fresh_kg"] - inputs["oxygen_credit"]
    base_lcom = e_total * price_blended + inputs["non_electric_cost"]
    policy = evaluate_policy_compliance(gwp, base_lcom, e_total, f_green, r_purge)
    result.update({"eta_carbon": model["eta_carbon"] * 100,
                   "fresh_co2_kg": model["m_co2_fresh_kg"], "fresh_h2_kg": model["m_h2_fresh_kg"],
                   "recycle_gas_kg": model["m_gas_recycle_kg"], "purge_gas_kg": model["m_gas_purge_kg"],
                   "reaction_water_kg": model["m_h2o_gen_kg"], "e_total_kwh": e_total,
                   "ef_grid_blended": ef_blended, "electricity_price_rmb_per_kwh": price_blended,
                   "gwp_net": gwp, "base_lcom": base_lcom,
                   "lcom_policy_adjusted": policy["lcom_policy_adjusted"],
                   "mac_policy_adjusted": policy["mac_policy_adjusted"],
                   "compliance_status": policy["compliance_status"],
                   "water_use_actual_t_per_t": policy["water_use_actual_t_per_t"],
                   "capital_annuity_rmb_per_t": inputs["capital_annuity_rmb_per_t"],
                   "annual_co2_ton": model["m_co2_fresh_kg"] * ANNUAL_CAPACITY_T / 1000,
                   "annual_h2_ton": model["m_h2_fresh_kg"] * ANNUAL_CAPACITY_T / 1000,
                   "annual_recycle_gas_ton": model["m_gas_recycle_kg"] * ANNUAL_CAPACITY_T / 1000,
                   "annual_reaction_water_ton": model["m_h2o_gen_kg"] * ANNUAL_CAPACITY_T / 1000,
                   "annual_oxygen_quota_ton": inputs["streams"]["S05"][MASS_COLUMN] * ANNUAL_CAPACITY_T / 1000,
                   "annual_demin_makeup_quota_ton": inputs["streams"]["S03"][MASS_COLUMN] * ANNUAL_CAPACITY_T / 1000,
                   "annual_total_water_ton": policy["water_use_actual_t_per_t"] * ANNUAL_CAPACITY_T,
                   "annual_power_kwh": e_total * ANNUAL_CAPACITY_T})
    result.update(policy["policy_breakdown"])
    return result


def run_grid():
    """60档绿电比例、50档驰放比，包含两端点，完整保留3000条记录。"""
    rows = []
    for fg in np.linspace(0, 1, 60):
        for rp in np.linspace(0.004, 0.045, 50):
            rows.append({"case_id": len(rows), **simulate_park_methanol_system(float(fg), float(rp))})
    return pd.DataFrame(rows)


def extract_pareto_frontier_and_anchors(df: pd.DataFrame):
    """严格非支配判定，保留目标完全相同的等价解；确定性地处理并列锚点。"""
    finite = np.isfinite(df[["gwp_net", "lcom_policy_adjusted"]].to_numpy(dtype=float)).all(axis=1)
    valid = df.loc[df["mfa_feasible"].eq(True) & ~df["compliance_status"].isin(
        ["Redline_Vetoed", "MFA_Infeasible"]) & finite].copy()
    if valid.empty:
        raise ValueError("没有物料可行且政策合规的有限目标工况")
    valid = valid.sort_values(["gwp_net", "lcom_policy_adjusted", "case_id"], kind="stable").reset_index(drop=True)
    points = valid[["gwp_net", "lcom_policy_adjusted"]].to_numpy(dtype=float)
    keep = [not np.any(np.all(points <= p, axis=1) & np.any(points < p, axis=1)) for p in points]
    frontier = valid.loc[keep].copy().reset_index(drop=True)
    objective_columns = ["gwp_net", "lcom_policy_adjusted"]
    values = frontier[objective_columns].to_numpy(dtype=float)
    ranges = np.ptp(values, axis=0)
    norm = np.zeros_like(values)
    np.divide(values - values.min(axis=0), ranges, out=norm, where=ranges > 0)
    frontier["normalized_gwp"], frontier["normalized_lcom"] = norm[:, 0], norm[:, 1]
    frontier["utopia_distance"] = np.linalg.norm(norm, axis=1)
    anchors = {
        ANCHOR_KEYS[0]: frontier.loc[frontier["lcom_policy_adjusted"].idxmin()].copy(),
        ANCHOR_KEYS[1]: frontier.loc[frontier["utopia_distance"].idxmin()].copy(),
        ANCHOR_KEYS[2]: frontier.loc[frontier["gwp_net"].idxmin()].copy(),
    }
    return frontier, anchors


def _local_alignment_check(fig, axes, output):
    """默认运行的实际绘图区等宽/等高/上下边对齐检查，单位pt，阈值1.5pt。"""
    fig.canvas.draw()
    size = fig.get_size_inches() * 72
    rects = [ax.get_position().bounds for ax in axes]
    measured = np.array([[x * size[0], y * size[1], w * size[0], h * size[1]] for x, y, w, h in rects])
    differences = {"bottom": float(np.ptp(measured[:, 1])), "width": float(np.ptp(measured[:, 2])),
                   "height": float(np.ptp(measured[:, 3])), "top": float(np.ptp(measured[:, 1] + measured[:, 3]))}
    report = {"unit": "pt", "tolerance_pt": 1.5, "panels_xywh": measured.tolist(),
              "differences": differences, "passed": max(differences.values()) <= 1.5}
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if not report["passed"]:
        raise ArithmeticError("决策双子图绘图区未对齐")


def draw_decision_figure(df, frontier, anchors, alignment_helper=None):
    """图a展示目标，图b展示完整决策域与剔除原因；不虚绘单点前沿曲线。"""
    output = get_figures_output_dir()
    plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["DejaVu Sans"],
                         "font.size": 10, "svg.fonttype": "none", "pdf.fonttype": 42,
                         "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(1, 2, figsize=(12.8, 6.2), dpi=300)
    fig.subplots_adjust(left=0.085, right=0.97, bottom=0.265, top=0.79, wspace=0.29)
    categories = (("MFA_Infeasible", "#b4b4b4", "x", "MFA infeasible"),
                  ("Redline_Vetoed", "#b95e55", "x", "Policy veto"),
                  ("Domestic_Compliant", "#72a5b4", "o", "Domestic compliant"),
                  ("RED_III_RFNBO_Certified", "#255d83", "o", "RED III certified"))
    for status, color, marker, label in categories:
        part = df[df["compliance_status"] == status]
        if status != "MFA_Infeasible":
            axes[0].scatter(part["gwp_net"], part["lcom_policy_adjusted"], s=15, c=color,
                            marker=marker, alpha=0.50, linewidths=0.6)
        axes[1].scatter(part["f_green"] * 100, part["r_purge"] * 100, s=9, c=color,
                        marker=marker, alpha=0.65, linewidths=0.5)
    if len(frontier) > 1:
        axes[0].plot(frontier["gwp_net"], frontier["lcom_policy_adjusted"], color="#cb8a24", lw=2)
        axes[1].plot(frontier["f_green"] * 100, frontier["r_purge"] * 100, color="#cb8a24", lw=1.5)
    grouped = {}
    for letter, key in zip("ABC", ANCHOR_KEYS):
        row = anchors[key]
        grouped.setdefault(int(row["case_id"]), {"letters": [], "row": row})["letters"].append(letter)
    for group in grouped.values():
        row = group["row"]
        axes[0].scatter(row["gwp_net"], row["lcom_policy_adjusted"], marker="*", s=170,
                        facecolors="#cb8a24", edgecolors="#333333", linewidths=0.7, zorder=5)
        axes[1].scatter(row["f_green"] * 100, row["r_purge"] * 100, marker="*", s=170,
                        facecolors="#cb8a24", edgecolors="#333333", linewidths=0.7, zorder=5)
    axes[0].axvline(2600, color="#b95e55", ls="--", lw=1)
    axes[0].set(xlabel="Net GWP (kg CO2e / t methanol)", ylabel="Policy-adjusted LCOM (CNY / t)",
                title="Objective space: physically solvable cases")
    axes[1].set(xlabel="Renewable electricity share (%)", ylabel="Purge split (%)",
                title="Decision space: full 3,000-case grid", xlim=(-3, 105), ylim=(0.15, 4.8))
    for label, ax in zip("ab", axes):
        ax.text(-0.13, 1.06, label, transform=ax.transAxes, fontsize=12, fontweight="bold")
        ax.grid(True, color="#e6e6e6", linewidth=0.5)
        ax.set_axisbelow(True)
    coincident = len(grouped) == 1
    anchor_label = "A = B = C: degenerate optimum" if coincident else "A / B / C anchors"
    fig.suptitle("Green methanol planning: source-constrained Pareto screening", fontsize=14, y=0.97)
    fig.text(0.085, 0.865, anchor_label + f"  |  {len(frontier)} nondominated grid case(s)", fontsize=10)
    handles = [Line2D([], [], color=c, marker=m, ls="", markersize=6, label=l)
               for _, c, m, l in categories]
    handles.append(Line2D([], [], color="#cb8a24", marker="*", ls="", markersize=10, label=anchor_label))
    handles.append(Line2D([], [], color="#b95e55", ls="--", lw=1, label="Coal GWP limit (2600)"))
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 0.105), ncol=3,
               frameon=False, fontsize=9, columnspacing=2.1)
    n_invalid = int((~df["mfa_feasible"]).sum())
    fig.text(0.085, 0.045, f"Grid: 60 renewable shares x 50 purge splits; {n_invalid} MFA-infeasible cases excluded from objective space.", fontsize=9)
    fig.text(0.085, 0.017, "Scope: fixed source energy / non-electric quotas; PV 0.20 CNY/kWh, coal 0.32 CNY/kWh. No fitted storage-cost curve.", fontsize=9)
    _local_alignment_check(fig, axes, output / "task3_plot_alignment.json")
    if alignment_helper is not None:
        spec = importlib.util.spec_from_file_location("task3_alignment_auditor", alignment_helper)
        auditor = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = auditor
        spec.loader.exec_module(auditor)
        require_matplotlib_panel_alignment = auditor.require_matplotlib_panel_alignment
        require_matplotlib_panel_alignment(fig, json_out=output / "task3_plot_alignment_external.json",
                                           axes=axes, panel_ids=["a", "b"], require_panel_labels=True,
                                           tolerance_pt=1.5, gutter_tolerance_pt=1.5, strict=True)
    fig.savefig(output / "fig2_pareto_decision_frontier.png", dpi=300)
    fig.savefig(output / "fig2_pareto_decision_frontier.svg")
    fig.savefig(output / "fig2_pareto_decision_frontier.pdf")
    plt.close(fig)


def export_results(df, frontier, anchors):
    output = get_figures_output_dir()
    df.to_csv(output / "task3_all_scenarios.csv", index=False, encoding="utf-8-sig")
    frontier.to_csv(output / "task3_pareto_frontier.csv", index=False, encoding="utf-8-sig")
    anchor_table = pd.DataFrame([{"anchor": key, **anchors[key].to_dict()} for key in ANCHOR_KEYS])
    anchor_table.to_csv(output / "task3_anchors.csv", index=False, encoding="utf-8-sig")
    sources = ["task_docs/background_engineering_docs.md", "task_docs/lecture10_task_manual.md",
               "data_cohort/mfa_reaction_recycle_balance.csv", "data_cohort/lca_grid_scenarios_lci.csv",
               "data_cohort/tea_lcom_sensitivity_data.csv", "data_cohort/policy_clauses_pack.md",
               "code_implementation/task1_mfa_recycle_solver.py", "code_implementation/task2_policy_vibe_engine.py",
               "code_implementation/task3_pareto_frontier_decision.py"]
    inputs = get_model_inputs()
    audit = {"grid_size": len(df), "grid_dimensions": [60, 50],
             "status_counts": {str(k): int(v) for k, v in df["compliance_status"].value_counts().items()},
             "frontier_count": len(frontier),
             "anchors_coincident": len({int(row["case_id"]) for row in anchors.values()}) == 1,
             "notes": MODEL_NOTES,
             "crf": inputs["crf"], "capital_annuity_rmb_per_t_included_in_non_electric": inputs["capital_annuity_rmb_per_t"],
             "non_electric_total_rmb_per_t": inputs["non_electric_cost"],
             "sources_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sources},
             "figure_contract": {"claim": "Sourced quotas can yield a degenerate, not an interior, Pareto solution.",
                                 "archetype": "quantitative grid", "panel_a": "objectives and policy rejection",
                                 "panel_b": "full decision grid and physical infeasibility",
                                 "size_inches": [12.8, 6.2], "png_dpi": 300,
                                 "uncertainty": "deterministic grid; no empirical confidence intervals"}}
    (output / "task3_model_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return anchor_table


class ParetoTests(unittest.TestCase):
    def test_source_equations(self):
        case = simulate_park_methanol_system(1.0, 0.01)
        self.assertAlmostEqual(case["e_total_kwh"], 10826)
        self.assertAlmostEqual(case["gwp_net"], -990.0)
        self.assertAlmostEqual(case["base_lcom"], 3403.57)
        self.assertAlmostEqual(case["lcom_policy_adjusted"], 1810.235)
        self.assertAlmostEqual(case["annual_co2_ton"], 142300)
        self.assertAlmostEqual(case["annual_power_kwh"], 1082600000)
        self.assertGreater(case["capital_annuity_rmb_per_t"], 835)
        self.assertLess(case["capital_annuity_rmb_per_t"], 836)

    def test_infeasible_is_not_given_fake_objectives(self):
        case = simulate_park_methanol_system(1.0, 0.045)
        self.assertFalse(case["mfa_feasible"])
        self.assertTrue(math.isnan(case["gwp_net"]))
        self.assertTrue(math.isnan(case["lcom_policy_adjusted"]))

    def test_strict_dominance_normalization_and_duplicates(self):
        # 独立算法测试点；仅在自检中使用，绝不进入生产网格或图表。
        df = pd.DataFrame({"case_id": range(7), "gwp_net": [0, 1, 2, 2, 0, -1, -2],
                           "lcom_policy_adjusted": [3, 1, 0, 2, 3, -1, -2],
                           "mfa_feasible": [True] * 6 + [False],
                           "compliance_status": ["Domestic_Compliant"] * 5 + ["Redline_Vetoed", "MFA_Infeasible"]})
        frontier, anchors = extract_pareto_frontier_and_anchors(df)
        self.assertEqual(set(frontier["case_id"]), {0, 1, 2, 4})
        self.assertEqual(anchors[ANCHOR_KEYS[1]]["case_id"], 1)
        self.assertEqual(anchors[ANCHOR_KEYS[0]]["case_id"], 2)
        self.assertEqual(anchors[ANCHOR_KEYS[2]]["case_id"], 0)

    def test_singleton_and_no_feasible_cases(self):
        case = {"case_id": 0, **simulate_park_methanol_system(1, 0.004)}
        df = pd.DataFrame([case])
        frontier, anchors = extract_pareto_frontier_and_anchors(df)
        self.assertEqual(frontier.iloc[0]["utopia_distance"], 0)
        self.assertEqual(len({v["case_id"] for v in anchors.values()}), 1)
        df["compliance_status"] = "Redline_Vetoed"
        with self.assertRaises(ValueError):
            extract_pareto_frontier_and_anchors(df)

    def test_grid_and_every_frontier_point(self):
        df = run_grid()
        self.assertEqual(len(df), 3000)
        self.assertEqual(df[["f_green", "r_purge"]].drop_duplicates().shape[0], 3000)
        frontier, anchors = extract_pareto_frontier_and_anchors(df)
        valid = df[df["mfa_feasible"] & df["compliance_status"].ne("Redline_Vetoed")]
        values = valid[["gwp_net", "lcom_policy_adjusted"]].to_numpy()
        for _, row in frontier.iterrows():
            p = row[["gwp_net", "lcom_policy_adjusted"]].to_numpy(dtype=float)
            self.assertFalse(np.any((values <= p).all(axis=1) & (values < p).any(axis=1)))
        self.assertEqual(len(frontier), 1)  # 当前明确的低价/低碳绿电场景
        self.assertEqual(anchors[ANCHOR_KEYS[1]]["f_green"], 1)
        self.assertEqual(anchors[ANCHOR_KEYS[1]]["r_purge"], 0.004)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--alignment-helper", type=Path)
    args = parser.parse_args()
    if args.self_test:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(ParetoTests)
        return 0 if unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(suite).wasSuccessful() else 1
    df = run_grid()
    frontier, anchors = extract_pareto_frontier_and_anchors(df)
    table = export_results(df, frontier, anchors)
    draw_decision_figure(df, frontier, anchors, args.alignment_helper)
    print(f"网格工况：{len(df)}；状态统计：{df['compliance_status'].value_counts().to_dict()}")
    print(table[["anchor", "f_green", "r_purge", "gwp_net", "base_lcom", "lcom_policy_adjusted", "mac_policy_adjusted"]].to_string(index=False))
    for note in MODEL_NOTES:
        print("[模型边界]", note)
    if len({int(v["case_id"]) for v in anchors.values()}) == 1:
        print("[退化前沿] A=B=C，B只是所要求距离准则的退化解，不存在可识别的内点拐点。")
    print("输出目录：", get_figures_output_dir())
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    sys.exit(main())
