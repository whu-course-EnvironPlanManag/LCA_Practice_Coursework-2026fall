# -*- coding: utf-8 -*-
"""任务4：从任务3实际锚点B绘制10万吨/年物质与能量流向图。

物质流分析 MFA (Material Flow Analysis)、能量流分析 EFA (Energy Flow
Analysis)、全生命周期评价 LCA (Life Cycle Assessment)、技术经济分析
TEA (Techno-Economic Analysis)。本任务只做已有结果的核验、尺度换算及
拓扑展示，不新增反应、动力学、LCA或成本经验公式，不修改报告。

依据：background_engineering_docs.md第1节工艺拓扑及第2节反应/电耗；
lecture10_task_manual.md任务4；同组CSV；任务3输出task3_anchors.csv。
1. 读取唯一Anchor_B_Knee_Point，以任务3函数重新核对所有已导出的数值字段。
   缺失/过期/被否决的锚点直接报错，不回退到模板硬编码的f=1,p=0.0216。
2. 合成段物流及回用水来自任务1同一纯组分模型；CO2、H2、甲醇、循环气、
   驰放气与生成水按 kg/t * 100000 t/y / 1000 换算为t/y。
3. 电耗直接取任务3读取的工程背景/LCI四工段定额，不根据箭头宽度推算。
   GWh/y = kWh/t * t/y / 1e6；份额 = 分项电耗/总电耗。
4. 净除盐水、氧气采用原始CSV工程定额，均标注[quota]；模型反应水全部
   回流是原理想冷凝模型及背景拓扑的边界。电解槽显示供水=净补水+回用水，
   与H2+氧气定额之差独立报告，不用补差法虚构排水或损失物流。
5. 冷却补水=任务2综合取水量-CSV净除盐水定额；合成段元素校验不代表
   未闭合的电解槽工程定额也通过。分子量舍入导致的小质量差额单独保留。
6. 原模板46.40万吨/年回流、5.75万吨/年回用水均是参考工况，不能直接
   冒充锚点B；不添加无定量依据的蒸汽回收/热功率/容量优化结论。

图为带定量标注的工艺拓扑，不以线宽表达质量比例；实线表示过程物流，
蓝色虚线表示水回用。输出同组figures_output/fig1_mfa_process_flow.png，
300 DPI；另存可编辑SVG/PDF、物流/能耗CSV和来源审计JSON。
--self-test运行自检；--alignment-helper可指定已用的科研绘图对齐工具。
"""

import argparse
import copy
import hashlib
import importlib.util
import json
import math
import re
from pathlib import Path
import sys
import unittest

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle
from matplotlib.path import Path as MplPath
import pandas as pd

try:
    from task1_mfa_recycle_solver import MW, solve_mfa_balance, verify_element_conservation, MASS_COLUMN
    from task3_pareto_frontier_decision import get_model_inputs, simulate_park_methanol_system, ANNUAL_CAPACITY_T
except ModuleNotFoundError:
    from .task1_mfa_recycle_solver import MW, solve_mfa_balance, verify_element_conservation, MASS_COLUMN
    from .task3_pareto_frontier_decision import get_model_inputs, simulate_park_methanol_system, ANNUAL_CAPACITY_T

ROOT = Path(__file__).resolve().parent.parent
ANCHOR_KEY = "Anchor_B_Knee_Point"


def get_figures_output_dir():
    path = ROOT / "figures_output"
    path.mkdir(parents=True, exist_ok=True)
    return path


def validate_anchor(row):
    """拒绝无解/被否决/过期锚点；任务3结果是唯一工况来源。"""
    required = ("f_green", "r_purge", "mfa_feasible", "compliance_status",
                "annual_co2_ton", "annual_h2_ton", "annual_recycle_gas_ton",
                "annual_reaction_water_ton", "annual_power_kwh")
    if any(k not in row for k in required):
        raise ValueError("锚点B缺少工况或年通量字段，请先运行任务3")
    actual = simulate_park_methanol_system(float(row["f_green"]), float(row["r_purge"]))
    if str(row["mfa_feasible"]).lower() != "true" or not actual["mfa_feasible"]:
        raise ValueError("锚点B物料不可行")
    if actual["compliance_status"] == "Redline_Vetoed" or row["compliance_status"] != actual["compliance_status"]:
        raise ValueError("锚点B被否决或状态已过期，请先重跑任务3")
    # 核对全部共同数值字段，不仅核对标题中的两个决策变量。
    for name, value in actual.items():
        if name not in row or isinstance(value, (bool, str)):
            continue
        stored = float(row[name])
        if not math.isfinite(value) or not math.isfinite(stored) or not math.isclose(stored, value, rel_tol=1e-9, abs_tol=1e-6):
            raise ValueError(f"锚点B字段{name}与当前模型不符，请重跑任务3")
    return actual


def load_anchor_plan(anchor_file=None):
    path = Path(anchor_file) if anchor_file is not None else ROOT / "figures_output/task3_anchors.csv"
    if not path.is_file():
        raise FileNotFoundError(f"缺少{path.name}，请先运行任务3；不使用模板替代数据")
    table = pd.read_csv(path)
    if "anchor" not in table:
        raise ValueError("任务3锚点表缺少anchor字段")
    selected = table.loc[table["anchor"] == ANCHOR_KEY]
    if len(selected) != 1:
        raise ValueError("锚点表必须且只能含一条Anchor_B_Knee_Point")
    row = selected.iloc[0].to_dict()
    actual = validate_anchor(row)
    inputs = get_model_inputs()
    mfa = solve_mfa_balance(0.25, actual["r_purge"], streams=inputs["streams"])
    balance = verify_element_conservation(mfa)
    if not balance["passed"]:
        raise ArithmeticError("合成段元素守恒检查失败，拒绝绘图")
    annual_mass = lambda flow: sum(v * MW[s] for s, v in flow.items()) * ANNUAL_CAPACITY_T / 1000
    masses = {name: annual_mass(flow) for name, flow in mfa["flows_kmol"].items()}
    # 主流程没有独立的液相未知流；粗甲醇=模型中的甲醇+生成水。
    masses["crude_liquid"] = masses["product"] + masses["water"]
    quota = lambda sid: inputs["streams"][sid][MASS_COLUMN] * ANNUAL_CAPACITY_T / 1000
    fresh_water_quota, oxygen_quota = quota("S03"), quota("S05")
    pem_supply = fresh_water_quota + masses["water"]
    # 仅审计缺项；该差值绝不作为虚构的废水/损失边绘制。
    pem_gap = pem_supply - actual["annual_h2_ton"] - oxygen_quota
    total_water = actual["annual_total_water_ton"]
    cooling_makeup = total_water - fresh_water_quota
    if cooling_makeup < 0:
        raise ValueError("综合取水小于净除盐水定额，输入模型边界不一致")
    energy_names = ("PEM electrolysis", "CO2 capture / compression", "Recycle compression / pumps", "Distillation / cooling")
    powers = inputs["power_stages"]
    energies = [{"stage": name, "kwh_per_t": value,
                 "annual_kwh": value * ANNUAL_CAPACITY_T,
                 "annual_gwh": value * ANNUAL_CAPACITY_T / 1e6,
                 "share_pct": value / sum(powers) * 100} for name, value in zip(energy_names, powers)]
    return {"anchor": row, "actual": actual, "mfa": mfa, "balance": balance,
            "annual_capacity_t": ANNUAL_CAPACITY_T, "masses_t_y": masses, "energies": energies,
            "fresh_water_quota_t_y": fresh_water_quota, "oxygen_quota_t_y": oxygen_quota,
            "pem_supply_t_y": pem_supply, "pem_unaccounted_mass_t_y": pem_gap,
            "reference_pem_supply_quota_t_y": quota("S04"),
            "cooling_makeup_t_y": cooling_makeup, "total_withdrawal_t_y": total_water,
            "synthesis_mass_rounding_residual_t_y": mfa["mass_residual_kg"] * ANNUAL_CAPACITY_T / 1000,
            "anchor_file": path}


def export_flow_data(plan):
    output = get_figures_output_dir()
    m, a = plan["masses_t_y"], plan["actual"]
    edges = [
        ("fresh_co2", "CO2 capture", "Mixer", a["annual_co2_ton"], "model / source feed"),
        ("fresh_h2", "PEM", "Mixer", a["annual_h2_ton"], "model / source feed"),
        ("reactor_in", "Mixer", "Reactor", m["reactor_in"], "stoichiometric model"),
        ("reactor_out", "Reactor", "Separator", m["reactor_out"], "stoichiometric model"),
        ("separator_gas", "Separator", "Gas splitter", m["offgas"], "stoichiometric model"),
        ("recycle", "Gas splitter / compression", "Mixer", m["recycle"], "stoichiometric model"),
        ("purge", "Gas splitter", "Boiler", m["purge"], "stoichiometric model"),
        ("crude_liquid", "Separator", "Distillation", m["crude_liquid"], "stoichiometric model"),
        ("product", "Distillation", "Methanol product", m["product"], "stoichiometric model"),
        ("water_reuse", "Distillation", "PEM", m["water"], "model water / complete recovery boundary"),
        ("fresh_water", "Fresh demin water", "PEM", plan["fresh_water_quota_t_y"], "CSV engineering quota"),
        ("oxygen", "PEM", "O2 coproduct", plan["oxygen_quota_t_y"], "CSV engineering quota; PEM not fully closed"),
        ("cooling_makeup", "Fresh water", "Cooling utilities", plan["cooling_makeup_t_y"], "policy water model; shown in note"),
    ]
    pd.DataFrame(edges, columns=["stream", "source", "target", "annual_ton", "basis"]).to_csv(
        output / "task4_material_flows.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(plan["energies"]).to_csv(output / "task4_energy_flows.csv", index=False, encoding="utf-8-sig")
    sources = [ROOT / "task_docs/background_engineering_docs.md", ROOT / "task_docs/lecture10_task_manual.md",
               ROOT / "data_cohort/mfa_reaction_recycle_balance.csv", ROOT / "data_cohort/lca_grid_scenarios_lci.csv",
               ROOT / "data_cohort/policy_clauses_pack.md", ROOT / "data_cohort/tea_lcom_sensitivity_data.csv",
               plan["anchor_file"], Path(__file__),
               ROOT / "code_implementation/task1_mfa_recycle_solver.py",
               ROOT / "code_implementation/task2_policy_vibe_engine.py",
               ROOT / "code_implementation/task3_pareto_frontier_decision.py"]
    audit = {k: v for k, v in plan.items() if k not in ("anchor", "actual", "mfa", "anchor_file")}
    audit["anchor_decisions"] = {k: plan["actual"][k] for k in ("f_green", "r_purge", "eta_carbon", "gwp_net", "lcom_policy_adjusted")}
    audit["sources_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    audit["limitations"] = ["Single-pass synthesis uses the task1 pure-component, complete-condensation model.",
                            "Oxygen and fresh demin water are source quotas, not a certified electrolyzer stoichiometric balance.",
                            "PEM mass gap is unaccounted input/output information, not an inferred wastewater stream.",
                            "Electricity is fixed source quota; no variable-load compressor law or heat-recovery duty is invented.",
                            "Arrow widths are schematic, not a mass-proportional Sankey encoding."]
    (output / "task4_model_audit.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def draw_mfa_process_flow(output_filename="fig1_mfa_process_flow.png", alignment_helper=None):
    if Path(output_filename).name != output_filename or Path(output_filename).suffix.lower() != ".png":
        raise ValueError("图片文件名必须为同组figures_output内的PNG文件名")
    plan = load_anchor_plan()
    export_flow_data(plan)
    m, a, e = plan["masses_t_y"], plan["actual"], plan["energies"]
    output = get_figures_output_dir()
    stem = Path(output_filename).stem
    plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["DejaVu Sans"],
                         "font.size": 10, "svg.fonttype": "none", "pdf.fonttype": 42})
    fig, ax = plt.subplots(figsize=(16, 10.4), dpi=300)
    fig.subplots_adjust(left=0.025, right=0.985, bottom=0.245, top=0.88)
    ax.set(xlim=(0, 144), ylim=(0, 100))
    ax.axis("off")
    ink, gas, water = "#263746", "#486f7a", "#2870a2"

    def unit(x, y, w, h, lines):
        ax.add_patch(Rectangle((x, y), w, h, facecolor="#f4f7f8", edgecolor=ink, lw=1.0))
        ax.text(x + w / 2, y + h / 2, "\n".join(lines), ha="center", va="center", fontsize=10,
                linespacing=1.5, color=ink)

    def label(x, y, text, size=10):
        ax.text(x, y, text, ha="center", va="center", fontsize=size, color=ink, linespacing=1.4)

    def arrow(points, color=ink, dashed=False):
        path = MplPath(points, [MplPath.MOVETO] + [MplPath.LINETO] * (len(points) - 1))
        ax.add_patch(FancyArrowPatch(path=path, arrowstyle="-|>", mutation_scale=13,
                                    linewidth=1.3, linestyle="--" if dashed else "-", color=color))

    def flow(value):
        return f"{value:,.2f} t/y"

    unit(25, 76, 20, 12, ["CO2 capture", flow(a["annual_co2_ton"]), f"{e[1]['annual_gwh']:.2f} GWh/y"])
    unit(25, 26, 20, 14, ["PEM electrolysis", flow(a["annual_h2_ton"]) + " H2", f"{e[0]['annual_gwh']:.2f} GWh/y"])
    unit(56, 52, 14, 14, ["Gas mixer", "+ preheat"])
    unit(78, 52, 16, 14, ["Catalytic synthesis", "CO2 conversion", "25.0% per pass"])
    unit(102, 52, 16, 14, ["Cooling /", "gas-liquid", "separation"])
    unit(78, 81, 16, 15, ["Recycle compressor", flow(m["recycle"]), f"{e[2]['annual_gwh']:.2f} GWh/y [quota]"])
    unit(128, 69, 15, 12, ["Purge to boiler", flow(m["purge"]), f"{a['r_purge']:.2%} split"])
    unit(102, 22, 16, 14, ["Double-column", "distillation", f"{e[3]['annual_gwh']:.2f} GWh/y"])

    # 新鲜进料与主反应-分离路径。
    arrow([(35, 94), (35, 88)])
    label(35, 98, "Captured CO2 feed")
    arrow([(45, 82), (52, 82), (52, 63), (56, 63)])
    arrow([(45, 37), (50, 37), (50, 57), (56, 57)], gas)
    label(43, 46, "Fresh green H2")
    arrow([(70, 59), (78, 59)])
    label(74, 71, "Reactor inlet\n" + flow(m["reactor_in"]), 9)
    arrow([(94, 59), (102, 59)])
    label(98, 71, "Reactor outlet\n" + flow(m["reactor_out"]), 9)
    # 分流节点：先显示脱出气相，再闭环返回混合器；非外部输入。
    arrow([(110, 66), (110, 75)], gas)
    ax.plot(110, 75, "o", color=gas, markersize=3)
    arrow([(110, 75), (110, 89), (94, 89)], gas)
    arrow([(78, 89), (63, 89), (63, 66)], gas)
    label(71, 77, f"{1-a['r_purge']:.2%} return", 9)
    arrow([(110, 75), (128, 75)], gas)
    label(118, 95, "Separator gas\n" + flow(m["offgas"]), 9)
    # 液体进精馏，甲醇外送，生成水回用；回用水用同一模型值。
    arrow([(110, 52), (110, 36)])
    label(126, 46, "Crude liquid\n" + flow(m["crude_liquid"]), 9)
    arrow([(118, 29), (139, 29)])
    label(130, 20, "Methanol product\n" + flow(m["product"]), 10)
    arrow([(102, 29), (70, 29), (70, 33), (45, 33)], water, True)
    label(75, 22, "Reaction-water reuse\n" + flow(m["water"]), 10)
    arrow([(3, 33), (25, 33)], water)
    label(13, 40, "Fresh demin water [quota]\n" + flow(plan["fresh_water_quota_t_y"]), 9)
    arrow([(35, 26), (35, 17)])
    label(35, 11, "O2 coproduct [quota]\n" + flow(plan["oxygen_quota_t_y"]), 10)

    fig.suptitle("100,000 t/y green methanol: material and electricity flows", fontsize=16, y=0.975)
    fig.text(0.5, 0.925, f"Actual task3 anchor B | Renewable share {a['f_green']:.1%} | Purge {a['r_purge']:.2%} | Carbon utilization {a['eta_carbon']:.4f}%",
             ha="center", fontsize=11)
    totals = sum(item["annual_gwh"] for item in e)
    fig.text(0.035, 0.205, f"Annual electricity: {totals:,.2f} GWh  |  PEM {e[0]['share_pct']:.2f}%  |  CO2 capture {e[1]['share_pct']:.2f}%  |  Recycle {e[2]['share_pct']:.2f}%  |  Distillation {e[3]['share_pct']:.2f}%", fontsize=10)
    fig.text(0.035, 0.165, "Basis: pure-component synthesis model; [quota]: source engineering values. Dashed blue: internal water reuse; widths are schematic.", fontsize=9)
    fig.text(0.035, 0.128, f"PEM supply = fresh quota + modelled reuse = {plan['pem_supply_t_y']:,.2f} t/y; H2 + O2 quota = {a['annual_h2_ton']+plan['oxygen_quota_t_y']:,.2f} t/y.", fontsize=9)
    fig.text(0.035, 0.095, f"Unaccounted PEM mass: {plan['pem_unaccounted_mass_t_y']:,.2f} t/y. Missing outlet information is not assigned to wastewater or another invented flow.", fontsize=9)
    fig.text(0.035, 0.062, f"Cooling make-up (policy model): {plan['cooling_makeup_t_y']:,.2f} t/y; total fresh withdrawal: {plan['total_withdrawal_t_y']:,.2f} t/y. Reuse is an internal flow.", fontsize=9)
    fig.text(0.035, 0.029, f"Synthesis C/H/O checks passed. Source molecular-weight rounding leaves {plan['synthesis_mass_rounding_residual_t_y']:.3f} t/y mass residual; PEM quotas are not fully closed.", fontsize=9)
    fig.canvas.draw()
    if alignment_helper is not None:
        spec = importlib.util.spec_from_file_location("task4_alignment_auditor", alignment_helper)
        auditor = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = auditor
        spec.loader.exec_module(auditor)
        require_matplotlib_panel_alignment = auditor.require_matplotlib_panel_alignment
        require_matplotlib_panel_alignment(fig, json_out=output / "task4_plot_alignment.json", axes=[ax], strict=True)
    fig.savefig(output / output_filename, dpi=300)
    fig.savefig(output / (stem + ".svg"))
    # 移除绘图器附带的外部DTD声明；保留全部可编辑矢量元素和文字。
    svg_path = output / (stem + ".svg")
    svg_text = re.sub(r"<!DOCTYPE[^>]*>", "", svg_path.read_text(encoding="utf-8"))
    svg_path.write_text("\n".join(line.rstrip() for line in svg_text.splitlines()) + "\n", encoding="utf-8")
    fig.savefig(output / (stem + ".pdf"))
    plt.close(fig)
    print(f"锚点B：f_green={a['f_green']:.6f}，r_purge={a['r_purge']:.6f}")
    print(f"循环气：{m['recycle']:,.6f} t/y；水回用：{m['water']:,.6f} t/y；年用电：{totals:.6f} GWh")
    print(f"[数据边界] 电解槽工程定额与模型回用水存在未闭合差额{plan['pem_unaccounted_mass_t_y']:,.6f} t/y，未虚构缺失物流。")
    print("图片已保存：", output / output_filename)
    return plan


class ProcessFlowTests(unittest.TestCase):
    def test_actual_anchor_and_scale(self):
        plan = load_anchor_plan()
        self.assertAlmostEqual(plan["masses_t_y"]["recycle"], plan["anchor"]["annual_recycle_gas_ton"])
        self.assertAlmostEqual(plan["masses_t_y"]["water"], plan["anchor"]["annual_reaction_water_ton"])
        self.assertAlmostEqual(plan["masses_t_y"]["product"], 100000)
        self.assertAlmostEqual(plan["actual"]["annual_co2_ton"], 142300)
        self.assertAlmostEqual(plan["actual"]["annual_h2_ton"], 19800)

    def test_synthesis_units_and_split(self):
        plan = load_anchor_plan()
        m, a = plan["masses_t_y"], plan["actual"]
        self.assertTrue(plan["balance"]["passed"])
        self.assertAlmostEqual(m["offgas"], m["purge"] + m["recycle"])
        self.assertAlmostEqual(m["purge"] / m["offgas"], a["r_purge"])
        self.assertAlmostEqual(m["reactor_out"], m["offgas"] + m["crude_liquid"])
        self.assertAlmostEqual(m["reactor_in"], a["annual_co2_ton"] + a["annual_h2_ton"] + m["recycle"])

    def test_electricity_and_water_boundaries(self):
        plan = load_anchor_plan()
        self.assertAlmostEqual(sum(e["annual_gwh"] for e in plan["energies"]), 1082.6)
        self.assertAlmostEqual(sum(e["share_pct"] for e in plan["energies"]), 100)
        self.assertAlmostEqual(sum(e["annual_kwh"] for e in plan["energies"]), plan["anchor"]["annual_power_kwh"])
        self.assertAlmostEqual(plan["total_withdrawal_t_y"], plan["fresh_water_quota_t_y"] + plan["cooling_makeup_t_y"])
        self.assertGreater(plan["pem_unaccounted_mass_t_y"], 0)
        self.assertAlmostEqual(plan["pem_supply_t_y"], plan["fresh_water_quota_t_y"] + plan["masses_t_y"]["water"])

    def test_stale_or_missing_anchor_is_rejected(self):
        plan = load_anchor_plan()
        bad = copy.deepcopy(plan["anchor"])
        bad["annual_recycle_gas_ton"] += 100
        with self.assertRaises(ValueError):
            validate_anchor(bad)
        bad = copy.deepcopy(plan["anchor"])
        bad["compliance_status"] = "Redline_Vetoed"
        with self.assertRaises(ValueError):
            validate_anchor(bad)
        with self.assertRaises(ValueError):
            validate_anchor({})
        with self.assertRaises(FileNotFoundError):
            load_anchor_plan(ROOT / "__nonexistent_anchor__.csv")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--alignment-helper", type=Path)
    args = parser.parse_args()
    if args.self_test:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(ProcessFlowTests)
        return 0 if unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(suite).wasSuccessful() else 1
    draw_mfa_process_flow(alignment_helper=args.alignment_helper)
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    sys.exit(main())
