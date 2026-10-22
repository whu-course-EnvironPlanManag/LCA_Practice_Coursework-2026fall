#!/usr/bin/env python3
"""Calculate the PET recycling case and draw its mass-flow process diagram."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import numpy as np
import pandas as pd
import schemdraw
from schemdraw import flow
from schemdraw.elements import Label


CASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = CASE_DIR / "case_files" / "data_cohort"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent


def load_case_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load the three published cohort datasets."""
    mfa = pd.read_csv(DATA_DIR / "mfa_mass_balance.csv")
    lci = pd.read_csv(DATA_DIR / "lci_emission_factors.csv")
    tea = pd.read_csv(DATA_DIR / "tea_cost_parameters.csv")
    return mfa, lci, tea


def get_parameter(tea: pd.DataFrame, name: str) -> float:
    """Return a numeric value from the TEA parameter table."""
    rows = tea.loc[tea["Parameter_Name"] == name, "Value"]
    if len(rows) != 1:
        raise ValueError(f"Expected one TEA parameter named {name!r}, found {len(rows)}")
    return float(rows.iloc[0])


def calculate_results(
    mfa: pd.DataFrame, lci: pd.DataFrame, tea: pd.DataFrame
) -> dict[str, float]:
    """Calculate the source-data baseline, green-power case, and 70% yield case."""
    mfa_flows = mfa.loc[mfa["Stage"] != "Balance_Check"].copy()
    inputs = mfa_flows.loc[mfa_flows["Flow_Type"] == "Raw_Material"]
    outputs = mfa_flows.loc[mfa_flows["Stage"] != "Input"]
    feed_kg = float(inputs["Mass_kg"].sum())
    output_kg = float(outputs["Mass_kg"].sum())
    product_kg = float(
        mfa_flows.loc[mfa_flows["Flow_Type"] == "Main_Product", "Mass_kg"].sum()
    )
    hdpe_kg_per_feed_t = float(
        mfa_flows.loc[mfa_flows["Flow_Type"] == "Co_Product", "Mass_kg"].sum()
    ) / (feed_kg / 1000)
    if not np.isclose(feed_kg, output_kg):
        raise ValueError(f"MFA does not balance: {feed_kg:g} kg in, {output_kg:g} kg out")

    current_yield = product_kg / feed_kg
    if not np.isclose(current_yield, 0.8):
        raise ValueError(f"Expected the published 80% reference yield, got {current_yield:.4%}")

    non_inventory_rows = {"Net_Total_GWP", "Virgin_PET_Benchmark", "Net_GHG_Reduction"}
    inventory = lci.loc[~lci["Flow_Name"].isin(non_inventory_rows)].copy()
    inventory["calculated_gwp"] = (
        pd.to_numeric(inventory["Amount_per_t_rPET"])
        * pd.to_numeric(inventory["Emission_Factor"])
    )
    published_gwp = pd.to_numeric(inventory["Carbon_Footprint_kgCO2e"])
    if not np.allclose(inventory["calculated_gwp"], published_gwp, atol=0.011):
        raise ValueError("LCI row totals do not match activity levels times emission factors")

    baseline_gwp = float(inventory["calculated_gwp"].sum())
    published_net_gwp = float(
        lci.loc[lci["Flow_Name"] == "Net_Total_GWP", "Carbon_Footprint_kgCO2e"].iloc[0]
    )
    if not np.isclose(baseline_gwp, published_net_gwp, atol=0.01):
        raise ValueError(
            f"LCI total mismatch: calculated {baseline_gwp:g}, published {published_net_gwp:g}"
        )

    electricity = inventory.loc[inventory["Flow_Name"] == "Electricity_Grid"].iloc[0]
    electricity_kwh = float(electricity["Amount_per_t_rPET"])
    grid_ef = float(electricity["Emission_Factor"])
    green_ef = 0.03
    green_gwp = baseline_gwp + electricity_kwh * (green_ef - grid_ef)
    virgin_gwp = float(
        lci.loc[
            lci["Flow_Name"] == "Virgin_PET_Benchmark", "Carbon_Footprint_kgCO2e"
        ].iloc[0]
    )

    baseline_lcop = get_parameter(tea, "Unit_LCOP")
    electricity_price = get_parameter(tea, "Electricity_Industrial")
    green_premium = 0.05
    green_lcop_increase = electricity_kwh * green_premium
    green_lcop = baseline_lcop + green_lcop_increase
    green_lcop_increase_pct = green_lcop_increase / baseline_lcop * 100

    yield_70 = 0.70
    feed_t_per_product_t_80 = 1 / current_yield
    feed_t_per_product_t_70 = 1 / yield_70
    feed_scale = feed_t_per_product_t_70 / feed_t_per_product_t_80
    transport_gwp = float(
        inventory.loc[inventory["Flow_Name"] == "Baled_PET_Transport", "calculated_gwp"].iloc[0]
    )
    hdpe_credit = float(
        inventory.loc[
            inventory["Flow_Name"] == "HDPE_Avoided_Burden", "calculated_gwp"
        ].iloc[0]
    )
    # The conservative case scales feed transport but holds the by-product credit
    # at its published value because the perturbed feed composition is unspecified.
    green_gwp_70_fixed_credit = green_gwp + transport_gwp * (feed_scale - 1)
    # A separate boundary case keeps the published HDPE recovery per tonne of feed.
    green_gwp_70_scaled_hdpe = green_gwp + (
        transport_gwp + hdpe_credit
    ) * (feed_scale - 1)

    feedstock_price = get_parameter(tea, "Feedstock_Baled_PET")
    feedstock_cost_80 = feed_t_per_product_t_80 * feedstock_price
    feedstock_cost_70 = feed_t_per_product_t_70 * feedstock_price
    green_lcop_70_fixed_credit = green_lcop + (feedstock_cost_70 - feedstock_cost_80)

    hdpe_price = get_parameter(tea, "HDPE_Flake_Selling_Price")
    hdpe_revenue_80 = (
        hdpe_kg_per_feed_t * feed_t_per_product_t_80 / 1000 * hdpe_price
    )
    hdpe_revenue_70 = (
        hdpe_kg_per_feed_t * feed_t_per_product_t_70 / 1000 * hdpe_price
    )
    green_lcop_70_scaled_hdpe = (
        green_lcop_70_fixed_credit - (hdpe_revenue_70 - hdpe_revenue_80)
    )

    annual_capacity = get_parameter(tea, "Plant_Annual_Capacity")
    annual_feed_demand = get_parameter(tea, "Feedstock_Annual_Demand")
    return {
        "feed_kg": feed_kg,
        "output_kg": output_kg,
        "product_kg": product_kg,
        "hdpe_kg_per_feed_t": hdpe_kg_per_feed_t,
        "yield_pct": current_yield * 100,
        "baseline_gwp": baseline_gwp,
        "green_gwp": green_gwp,
        "virgin_gwp": virgin_gwp,
        "green_reduction_pct": (virgin_gwp - green_gwp) / virgin_gwp * 100,
        "green_avoided_gwp": virgin_gwp - green_gwp,
        "grid_ef": grid_ef,
        "green_ef": green_ef,
        "electricity_kwh": electricity_kwh,
        "baseline_lcop": baseline_lcop,
        "electricity_price": electricity_price,
        "green_premium": green_premium,
        "green_lcop_increase": green_lcop_increase,
        "green_lcop": green_lcop,
        "green_lcop_increase_pct": green_lcop_increase_pct,
        "yield_70_pct": yield_70 * 100,
        "feed_t_per_product_t_80": feed_t_per_product_t_80,
        "feed_t_per_product_t_70": feed_t_per_product_t_70,
        "feed_scale_70_pct": feed_scale,
        "feed_increase_pct_70": (feed_scale - 1) * 100,
        "transport_gwp_80": transport_gwp,
        "hdpe_credit_80": hdpe_credit,
        "green_gwp_70_fixed_credit": green_gwp_70_fixed_credit,
        "green_gwp_70_scaled_hdpe": green_gwp_70_scaled_hdpe,
        "feedstock_cost_80": feedstock_cost_80,
        "feedstock_cost_70": feedstock_cost_70,
        "feedstock_cost_increase_70": feedstock_cost_70 - feedstock_cost_80,
        "green_lcop_70_fixed_credit": green_lcop_70_fixed_credit,
        "hdpe_revenue_80": hdpe_revenue_80,
        "hdpe_revenue_70": hdpe_revenue_70,
        "green_lcop_70_scaled_hdpe": green_lcop_70_scaled_hdpe,
        "annual_capacity": annual_capacity,
        "annual_feed_demand": annual_feed_demand,
        "annual_feed_required_70": annual_capacity / yield_70,
        "annual_output_at_feed_cap_70": annual_feed_demand * yield_70,
    }


def draw_process_diagram(mfa: pd.DataFrame, output_dir: Path) -> None:
    """Draw the documented process topology with mass labels from the MFA CSV."""
    output_dir.mkdir(parents=True, exist_ok=True)
    process_flow = mfa.loc[mfa["Stage"] != "Balance_Check"].copy()

    def mass(flow_type: str) -> float:
        rows = process_flow.loc[process_flow["Flow_Type"] == flow_type, "Mass_kg"]
        return float(rows.sum())

    input_mass = mass("Raw_Material")
    product_mass = mass("Main_Product")
    hdpe_mass = mass("Co_Product")
    waste_mass = mass("Waste")
    if not np.isclose(input_mass, product_mass + hdpe_mass + waste_mass):
        raise ValueError("The process diagram cannot be drawn from an unbalanced MFA dataset")

    stage_masses = {
        "labels_dirt": float(
            process_flow.loc[
                process_flow["Substance_Good"].isin(["Labels_PP_PVC", "Surface_Dirt_Sand"]),
                "Mass_kg",
            ].sum()
        ),
        "wash": float(
            process_flow.loc[
                process_flow["Substance_Good"] == "Adhesives_Residue_COD", "Mass_kg"
            ].sum()
        ),
        "hdpe_loss": float(
            process_flow.loc[
                process_flow["Substance_Good"] == "HDPE_Fine_Loss", "Mass_kg"
            ].sum()
        ),
        "off_spec": float(
            process_flow.loc[
                process_flow["Substance_Good"] == "Off_Spec_Fines", "Mass_kg"
            ].sum()
        ),
    }
    remaining_mass = [
        input_mass,
        input_mass - stage_masses["labels_dirt"],
        input_mass - stage_masses["labels_dirt"] - stage_masses["wash"],
        input_mass
        - stage_masses["labels_dirt"]
        - stage_masses["wash"]
        - hdpe_mass
        - stage_masses["hdpe_loss"],
        product_mass,
        product_mass,
    ]

    colors = {
        "ink": "#17324D",
        "line": "#58748C",
        "main": "#E8F2F8",
        "input": "#DCEFE5",
        "product": "#C8E7D2",
        "waste": "#FFF0DB",
        "coproduct": "#E9E2F6",
        "muted": "#40566B",
        "accent": "#B75B28",
    }
    centers = [1.4, 4.9, 8.4, 11.9, 15.4, 18.9, 22.4]
    process_width = 2.7
    process_height = 1.45
    process_labels = [
        "1  拆包筛选\n干式脱标",
        "2  湿式粉碎\n85°C 热碱洗",
        "3  密度浮选\nHDPE 上浮 / PET 下沉",
        "4  光学色选\n脱水与干燥",
        "5  真空挤出造粒\nSSP 固相增粘",
    ]

    drawing = schemdraw.Drawing(show=False, dpi=300, inches_per_unit=0.55)
    drawing.config(font="Microsoft YaHei", fontsize=10, lw=1.5)
    drawing.add(
        Label(
            "城市废旧 PET 机械物理再生工艺物质流程图",
            fontsize=18,
            color=colors["ink"],
        ).at((12, 5.05))
    )
    drawing.add(
        Label(
            "系统边界：1,000 kg 混合废 PET 瓶砖输入；物质流量标注为 kg / 批次",
            fontsize=10,
            color=colors["muted"],
        ).at((12, 4.48))
    )

    drawing.add(
        flow.Terminal(
            w=2.45,
            h=1.2,
            fill=colors["input"],
            color=colors["ink"],
            lw=1.6,
        )
        .label(f"原料输入\n废 PET 瓶砖\n{input_mass:,.0f} kg", fontsize=9.5)
        .at((centers[0], 0))
        .anchor("center")
    )
    for x, label in zip(centers[1:6], process_labels):
        drawing.add(
            flow.Process(
                w=process_width,
                h=process_height,
                fill=colors["main"],
                color=colors["ink"],
                lw=1.6,
            )
            .label(label, fontsize=9.5)
            .at((x, 0))
            .anchor("center")
        )
    drawing.add(
        flow.Terminal(
            w=2.65,
            h=1.2,
            fill=colors["product"],
            color=colors["ink"],
            lw=1.6,
        )
        .label(f"主产品\n瓶级 rPET 颗粒\n{product_mass:,.0f} kg", fontsize=9.5)
        .at((centers[6], 0))
        .anchor("center")
    )

    widths = [2.45] + [process_width] * 5 + [2.65]
    for index in range(6):
        x_start = centers[index] + widths[index] / 2
        x_end = centers[index + 1] - widths[index + 1] / 2
        drawing.add(
            flow.Arrow(
                arrowwidth=0.12,
                arrowlength=0.22,
                color=colors["line"],
                lw=1.8,
            )
            .at((x_start, 0))
            .to((x_end, 0))
        )
        drawing.add(
            Label(
                f"{remaining_mass[index]:,.0f} kg",
                fontsize=8.5,
                color=colors["muted"],
            ).at(((x_start + x_end) / 2, 0.36))
        )

    branch_specs = [
        (centers[1], process_height / 2, 3.15, "top", colors["waste"],
         f"标签膜 20 kg + 泥沙 25 kg\n预处理杂质：{stage_masses['labels_dirt']:,.0f} kg"),
        (centers[2], -process_height / 2, -3.05, "bottom", colors["waste"],
         f"洗涤胶水与 COD 杂质\n污水处理：{stage_masses['wash']:,.0f} kg"),
        (centers[3], process_height / 2, 3.15, "top", colors["coproduct"],
         f"副产品：回收 HDPE 碎料\n外售：{hdpe_mass:,.0f} kg"),
        (centers[3], -process_height / 2, -3.05, "bottom", colors["waste"],
         f"HDPE 细屑夹带损失\n沉渣：{stage_masses['hdpe_loss']:,.0f} kg"),
        (centers[4], process_height / 2, 3.15, "top", colors["waste"],
         f"杂色片与超细粉\n剔除：{stage_masses['off_spec']:,.0f} kg"),
    ]
    for x, process_edge_y, branch_center_y, direction, fill, text in branch_specs:
        branch_height = 1.2
        if direction == "top":
            arrow_start = (x, process_edge_y)
            arrow_end = (x, branch_center_y - branch_height / 2)
            branch_anchor = "center"
        else:
            arrow_start = (x, process_edge_y)
            arrow_end = (x, branch_center_y + branch_height / 2)
            branch_anchor = "center"
        drawing.add(
            flow.Arrow(
                arrowwidth=0.12,
                arrowlength=0.22,
                color=colors["accent"],
                lw=1.6,
            )
            .at(arrow_start)
            .to(arrow_end)
        )
        drawing.add(
            flow.Process(
                w=3.05,
                h=branch_height,
                fill=fill,
                color=colors["accent"],
                lw=1.25,
            )
            .label(text, fontsize=8.5)
            .at((x, branch_center_y))
            .anchor(branch_anchor)
        )

    drawing.add(
        Label(
            f"总输入 {input_mass:,.0f} kg = 主产品 {product_mass:,.0f} kg"
            f" + 副产品 {hdpe_mass:,.0f} kg + 废物流 {waste_mass:,.0f} kg",
            fontsize=10,
            color=colors["ink"],
        ).at((12, -4.18))
    )

    png_path = output_dir / "process_flow_diagram.png"
    svg_path = output_dir / "process_flow_diagram.svg"
    drawing.save(str(svg_path), transparent=False)
    svg_text = svg_path.read_text(encoding="utf-8")
    svg_path.write_text(
        "\n".join(line.rstrip() for line in svg_text.splitlines()) + "\n",
        encoding="utf-8",
    )
    drawing.save(str(png_path), transparent=False, dpi=300)


def print_results(results: dict[str, float]) -> None:
    """Print the key calculated metrics for reproducible verification."""
    print(f"MFA: {results['feed_kg']:.1f} kg input = {results['output_kg']:.1f} kg output")
    print(f"Product yield: {results['yield_pct']:.1f}%")
    print(f"Baseline GWP: {results['baseline_gwp']:.2f} kg CO2e/t rPET")
    print(
        f"100% green-power GWP: {results['green_gwp']:.2f} kg CO2e/t; "
        f"reduction vs virgin PET: {results['green_reduction_pct']:.2f}%"
    )
    print(
        f"Green-power LCOP: {results['green_lcop']:.2f} RMB/t "
        f"(+{results['green_lcop_increase']:.2f} RMB/t, "
        f"+{results['green_lcop_increase_pct']:.2f}%)"
    )
    print(
        f"At 70% yield: feed={results['feed_t_per_product_t_70']:.4f} t/t product, "
        f"green GWP={results['green_gwp_70_fixed_credit']:.2f} kg CO2e/t "
        "(fixed co-product credit)"
    )
    print(
        f"At 70% yield: green GWP={results['green_gwp_70_scaled_hdpe']:.2f} kg CO2e/t "
        "(HDPE recovery per tonne feed held constant)"
    )
    print(
        f"At 70% yield: LCOP={results['green_lcop_70_fixed_credit']:.2f} RMB/t "
        "(fixed co-product revenue)"
    )
    print(
        f"At 70% yield: LCOP={results['green_lcop_70_scaled_hdpe']:.2f} RMB/t "
        "(HDPE recovery per tonne feed held constant)"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for generated figures (default: this script's directory)",
    )
    args = parser.parse_args()

    mfa, lci, tea = load_case_data()
    results = calculate_results(mfa, lci, tea)
    draw_process_diagram(mfa, args.output_dir)
    print_results(results)
    print(f"PNG (300 dpi): {args.output_dir / 'process_flow_diagram.png'}")
    print(f"SVG: {args.output_dir / 'process_flow_diagram.svg'}")


if __name__ == "__main__":
    main()
