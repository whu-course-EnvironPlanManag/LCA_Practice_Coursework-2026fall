from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
CASE_DIR = BASE_DIR.parent / "case_files"
DATA_DIR = CASE_DIR / "data_cohort"
GREEN_ELECTRICITY_EMISSION_FACTOR = 0.03
GREEN_ELECTRICITY_PRICE = 0.70
SENSITIVITY_YIELD = 0.70


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def to_float(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace(",", "").str.replace("%", ""), errors="coerce")


def get_value(frame: pd.DataFrame, column: str, key: str, value_column: str) -> float:
    values = frame.loc[frame[column] == key, value_column]
    if len(values) != 1:
        raise ValueError(f"Expected exactly one {key!r} row in {column}, found {len(values)}")
    value = float(values.iloc[0])
    if pd.isna(value):
        raise ValueError(f"Missing numeric value for {key!r} in {value_column}")
    return value


def load_mfa_data() -> tuple[pd.DataFrame, float]:
    mfa = read_csv(DATA_DIR / "mfa_mass_balance.csv")
    required_columns = {"Stage", "Flow_Type", "Substance_Good", "Mass_kg"}
    missing_columns = required_columns.difference(mfa.columns)
    if missing_columns:
        raise ValueError(f"MFA data is missing required columns: {', '.join(sorted(missing_columns))}")

    mfa["Mass_kg"] = to_float(mfa["Mass_kg"])
    if mfa["Mass_kg"].isna().any():
        raise ValueError("MFA data contains a missing or non-numeric mass")

    flows = mfa.loc[~mfa["Stage"].eq("Balance_Check")]
    input_mass = float(flows.loc[flows["Flow_Type"].eq("Raw_Material"), "Mass_kg"].sum())
    output_mass = float(flows.loc[~flows["Flow_Type"].eq("Raw_Material"), "Mass_kg"].sum())
    if input_mass <= 0 or abs(input_mass - output_mass) > 1e-6:
        raise ValueError(
            f"MFA mass balance failed: inputs={input_mass:g} kg, outputs={output_mass:g} kg"
        )
    return flows, input_mass


def compute_green_lca() -> dict:
    lci = read_csv(DATA_DIR / "lci_emission_factors.csv")
    lci["Carbon_Footprint_kgCO2e"] = to_float(lci["Carbon_Footprint_kgCO2e"])
    lci["Amount_per_t_rPET"] = to_float(lci["Amount_per_t_rPET"])
    lci["Emission_Factor"] = to_float(lci["Emission_Factor"])

    electricity_kwh = get_value(lci, "Flow_Name", "Electricity_Grid", "Amount_per_t_rPET")
    baseline_grid = get_value(
        lci, "Flow_Name", "Electricity_Grid", "Carbon_Footprint_kgCO2e"
    )
    green_grid = electricity_kwh * GREEN_ELECTRICITY_EMISSION_FACTOR

    net_total = get_value(lci, "Flow_Name", "Net_Total_GWP", "Carbon_Footprint_kgCO2e")
    green_total = net_total - (baseline_grid - green_grid)

    virgin_benchmark = get_value(lci, "Flow_Name", "Virgin_PET_Benchmark", "Carbon_Footprint_kgCO2e")
    reduction_pct = (virgin_benchmark - green_total) / virgin_benchmark * 100.0

    return {
        "baseline_net_gwp": net_total,
        "electricity_kwh_per_t": electricity_kwh,
        "green_power_grid_kgco2e": green_grid,
        "green_net_gwp": green_total,
        "virgin_benchmark": virgin_benchmark,
        "reduction_pct": reduction_pct,
    }


def compute_green_lcop() -> dict:
    tea = read_csv(DATA_DIR / "tea_cost_parameters.csv")
    tea["Value"] = to_float(tea["Value"])

    lcop_baseline = get_value(tea, "Parameter_Name", "Unit_LCOP", "Value")
    electricity_price_baseline = get_value(tea, "Parameter_Name", "Electricity_Industrial", "Value")
    electricity_kwh_per_t = compute_green_lca()["electricity_kwh_per_t"]
    electricity_delta = (
        GREEN_ELECTRICITY_PRICE - electricity_price_baseline
    ) * electricity_kwh_per_t
    lcop_green = lcop_baseline + electricity_delta
    increase_pct = electricity_delta / lcop_baseline * 100.0

    return {
        "electricity_price_baseline": electricity_price_baseline,
        "electricity_price_green": GREEN_ELECTRICITY_PRICE,
        "electricity_kwh_per_t": electricity_kwh_per_t,
        "electricity_delta_rmb_per_t": electricity_delta,
        "lcop_baseline": lcop_baseline,
        "lcop_green": lcop_green,
        "lcop_increase_pct": increase_pct,
    }


def compute_sensitivity() -> dict:
    lca = compute_green_lca()
    tea = compute_green_lcop()
    mfa, input_mass = load_mfa_data()

    product_mass = get_value(mfa, "Flow_Type", "Main_Product", "Mass_kg")
    coproduct_mass = get_value(mfa, "Flow_Type", "Co_Product", "Mass_kg")
    baseline_yield = product_mass / input_mass
    yield_scale = baseline_yield / SENSITIVITY_YIELD

    lci = read_csv(DATA_DIR / "lci_emission_factors.csv")
    lci["Carbon_Footprint_kgCO2e"] = to_float(lci["Carbon_Footprint_kgCO2e"])
    transport_gwp = get_value(lci, "Flow_Name", "Baled_PET_Transport", "Carbon_Footprint_kgCO2e")
    hdpe_credit = get_value(lci, "Flow_Name", "HDPE_Avoided_Burden", "Carbon_Footprint_kgCO2e")
    # Adjust only burdens and credits linked to the extra feed; the data does
    # not provide yield-dependent utility or waste-treatment coefficients.
    transport_gwp_change = transport_gwp * (yield_scale - 1)
    hdpe_credit_change = hdpe_credit * (yield_scale - 1)
    gwp_70 = (
        lca["green_net_gwp"]
        + transport_gwp_change
        + hdpe_credit_change
    )

    tea_data = read_csv(DATA_DIR / "tea_cost_parameters.csv")
    tea_data["Value"] = to_float(tea_data["Value"])
    feedstock_price = get_value(tea_data, "Parameter_Name", "Feedstock_Baled_PET", "Value")
    hdpe_price = get_value(tea_data, "Parameter_Name", "HDPE_Flake_Selling_Price", "Value")
    feedstock_increase = (1 / SENSITIVITY_YIELD - 1 / baseline_yield) * feedstock_price
    hdpe_revenue_increase = (
        coproduct_mass / product_mass * (yield_scale - 1) * hdpe_price
    )
    lcop_70 = tea["lcop_green"] + feedstock_increase - hdpe_revenue_increase

    return {
        "yield_scale": yield_scale,
        "baseline_yield": baseline_yield,
        "gwp_yield_70_pct": gwp_70,
        "lcop_yield_70": lcop_70,
        "gwp_increase_vs_green": gwp_70 - lca["green_net_gwp"],
        "lcop_increase_vs_green": lcop_70 - tea["lcop_green"],
        "transport_gwp_change": transport_gwp_change,
        "hdpe_credit_change": hdpe_credit_change,
        "feedstock_increase_rmb_per_t": feedstock_increase,
        "hdpe_revenue_increase_rmb_per_t": hdpe_revenue_increase,
    }


def plot_process_flow(output_path: Path, mfa: pd.DataFrame, input_mass: float) -> None:
    chinese_font = font_manager.findfont("Microsoft YaHei")
    plt.rcParams["font.family"] = font_manager.FontProperties(fname=chinese_font).get_name()
    plt.rcParams["axes.unicode_minus"] = False

    fig, ax = plt.subplots(figsize=(16, 8), dpi=300)
    ax.axis("off")
    ax.set_xlim(0, 14.2)
    ax.set_ylim(0.5, 8)
    ax.set_title("废弃 PET 瓶机械物理再生工艺物质流程图", fontsize=17, pad=18)

    node_width, node_height, node_y = 1.5, 1.25, 5.35
    node_x = [0.25, 2.25, 4.25, 6.25, 8.25, 10.25, 12.25]
    nodes = [
        ("废 PET 瓶砖\n1000 kg", "#e8f1ff"),
        ("拆包、筛选\n干式脱标", "#e8f1ff"),
        ("湿式粉碎\n热碱洗", "#e8f1ff"),
        ("密度浮选\nPET / HDPE", "#e8f1ff"),
        ("光学色选\n脱水、干燥", "#e8f1ff"),
        ("真空挤出\nSSP 增粘", "#e8f1ff"),
        ("瓶级 rPET\n主产品 800 kg", "#dff2df"),
    ]

    for x, (label, color) in zip(node_x, nodes):
        rect = plt.Rectangle(
            (x, node_y), node_width, node_height,
            linewidth=1.5, edgecolor="#334155", facecolor=color,
            joinstyle="round",
        )
        ax.add_patch(rect)
        ax.text(
            x + node_width / 2, node_y + node_height / 2, label,
            ha="center", va="center", fontsize=10.5,
        )

    flow_reductions = [
        ("Debaling_Drying", ["Waste"]),
        ("Hot_Washing", ["Waste"]),
        ("Sink_Float", ["Waste", "Co_Product"]),
        ("SSP_Extrusion", ["Waste"]),
        ("SSP_Extrusion", []),
    ]
    stream_masses = [input_mass]
    carried_mass = input_mass
    for stage, flow_types in flow_reductions:
        removed_mass = float(
            mfa.loc[
                mfa["Stage"].eq(stage) & mfa["Flow_Type"].isin(flow_types),
                "Mass_kg",
            ]
            .sum()
        )
        carried_mass -= removed_mass
        stream_masses.append(carried_mass)
    main_product_mass = get_value(mfa, "Flow_Type", "Main_Product", "Mass_kg")
    if abs(carried_mass - main_product_mass) > 1e-6:
        raise ValueError(
            f"Process flow does not match main product: {carried_mass:g} kg != "
            f"{main_product_mass:g} kg"
        )

    for index in range(len(node_x) - 1):
        start = (node_x[index] + node_width, node_y + node_height / 2)
        end = (node_x[index + 1], node_y + node_height / 2)
        ax.annotate(
            "", xy=end, xytext=start,
            arrowprops=dict(arrowstyle="-|>", color="#334155", lw=1.5),
        )
        ax.text(
            (start[0] + end[0]) / 2, start[1] + 0.18,
            f"{stream_masses[index]:g} kg",
            ha="center", va="bottom", fontsize=8.5, color="#334155",
        )

    waste_y, waste_height = 2.0, 1.0
    stage_positions = {
        "Debaling_Drying": node_x[1],
        "Hot_Washing": node_x[2],
        "Sink_Float": node_x[3],
        "SSP_Extrusion": node_x[5],
    }
    outlet_positions = {
        ("Debaling_Drying", "Labels_PP_PVC"): ("废标签 (PP/PVC)", 0.35, 1.45),
        ("Debaling_Drying", "Surface_Dirt_Sand"): ("泥沙与干灰", 1.9, 1.45),
        ("Hot_Washing", "Adhesives_Residue_COD"): ("洗涤胶水及 COD", 3.6, 1.8),
        ("Sink_Float", "HDPE_Fine_Loss"): ("HDPE 碎屑损失", 5.5, 1.5),
        ("Sink_Float", "Recovered_HDPE_Flakes"): ("回收 HDPE 副产品", 7.0, 1.6),
        ("SSP_Extrusion", "Off_Spec_Fines"): ("杂色切片与超细粉", 9.15, 1.8),
    }
    for _, row in mfa.loc[mfa["Flow_Type"].isin(["Waste", "Co_Product"])].iterrows():
        stage = row["Stage"]
        substance = row["Substance_Good"]
        position = outlet_positions.get((stage, substance))
        if position is None:
            raise ValueError(f"No process diagram outlet configured for {stage}/{substance}")
        label, box_x, box_width = position
        box_center = box_x + box_width / 2
        source_x = stage_positions[stage] + node_width / 2
        is_coproduct = row["Flow_Type"] == "Co_Product"
        label = f"{label}\n{row['Mass_kg']:g} kg"
        rect = plt.Rectangle(
            (box_x, waste_y), box_width, waste_height,
            linewidth=1.2, edgecolor="#64748b",
            facecolor="#e6f4ea" if is_coproduct else "#fff1e6",
        )
        ax.add_patch(rect)
        ax.text(
            box_center, waste_y + waste_height / 2, label,
            ha="center", va="center", fontsize=9,
        )
        ax.annotate(
            "", xy=(box_center, waste_y + waste_height),
            xytext=(source_x, node_y),
            arrowprops=dict(arrowstyle="-|>", color="#64748b", lw=1.1),
        )

    ax.text(
        7.0, 0.95,
        f"质量核算：{input_mass:g} kg 进料 = {main_product_mass:g} kg rPET + "
        f"{mfa.loc[mfa['Flow_Type'].eq('Co_Product'), 'Mass_kg'].sum():g} kg 副产品 + "
        f"{mfa.loc[mfa['Flow_Type'].eq('Waste'), 'Mass_kg'].sum():g} kg 工艺损失",
        ha="center", va="center", fontsize=10, color="#334155",
    )
    fig.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    lca = compute_green_lca()
    tea = compute_green_lcop()
    sensitivity = compute_sensitivity()
    mfa, input_mass = load_mfa_data()

    print("=== 案例一 MAF-LCA-TEA 计算结果 ===")
    print(f"1) 绿电驱动下净碳足迹 GWP_green = {lca['green_net_gwp']:.1f} kg CO2e/t")
    print(f"   相对原生 PET 基准的减碳幅度 = {lca['reduction_pct']:.1f}%")
    print(f"2) 绿电溢价导致 LCOP 增加 = {tea['electricity_delta_rmb_per_t']:.1f} RMB/t")
    print(f"   LCOP_baseline = {tea['lcop_baseline']:.1f} RMB/t")
    print(f"   LCOP_green = {tea['lcop_green']:.1f} RMB/t")
    print(f"   LCOP 增幅 = {tea['lcop_increase_pct']:.2f}%")
    print("3) 收率敏感性估算仅调整已知进料运输、原料成本及 HDPE 副产品抵扣")
    print(f"   若收率从 {sensitivity['baseline_yield']:.0%} 降至 70%，则 GWP 估算为 {sensitivity['gwp_yield_70_pct']:.1f} kg CO2e/t")
    print(f"   原料运输 GWP 增加 {sensitivity['transport_gwp_change']:.1f}，HDPE 抵扣变化 {sensitivity['hdpe_credit_change']:.1f} kg CO2e/t")
    print(f"   LCOP 变为 {sensitivity['lcop_yield_70']:.1f} RMB/t")
    print(f"   原料成本增加 {sensitivity['feedstock_increase_rmb_per_t']:.1f}，HDPE 收入增加 {sensitivity['hdpe_revenue_increase_rmb_per_t']:.1f} RMB/t")
    print(f"   绿电情景下，收率下降造成的 GWP 增加 = {sensitivity['gwp_increase_vs_green']:.1f} kg CO2e/t")
    print(f"   绿电情景下，收率下降造成的 LCOP 增加 = {sensitivity['lcop_increase_vs_green']:.1f} RMB/t")
    print("   注：未提供随收率变化的公用工程和废弃物处理系数，这些负荷按不变处理。")

    output_txt = BASE_DIR / "case1_analysis_results.txt"
    with output_txt.open("w", encoding="utf-8") as f:
        f.write("=== 案例一 MAF-LCA-TEA 计算结果 ===\n")
        f.write(f"1) GWP_green = {lca['green_net_gwp']:.1f} kg CO2e/t\n")
        f.write(f"   减碳幅度 = {lca['reduction_pct']:.1f}%\n")
        f.write(f"2) LCOP_green = {tea['lcop_green']:.1f} RMB/t\n")
        f.write(f"   LCOP 增加 = {tea['electricity_delta_rmb_per_t']:.1f} RMB/t\n")
        f.write(f"   增幅 = {tea['lcop_increase_pct']:.2f}%\n")
        f.write("3) 收率敏感性估算仅调整已知进料运输、原料成本及 HDPE 副产品抵扣；")
        f.write("未提供随收率变化的公用工程和废弃物处理系数，这些负荷按不变处理。\n")
        f.write(f"   收率70%时 GWP 估算 = {sensitivity['gwp_yield_70_pct']:.1f} kg CO2e/t\n")
        f.write(f"   运输 GWP 变化 = +{sensitivity['transport_gwp_change']:.1f} kg CO2e/t；")
        f.write(f"HDPE 抵扣变化 = {sensitivity['hdpe_credit_change']:.1f} kg CO2e/t\n")
        f.write(f"   收率70%时 LCOP = {sensitivity['lcop_yield_70']:.1f} RMB/t\n")
        f.write(f"   原料成本增加 = {sensitivity['feedstock_increase_rmb_per_t']:.1f} RMB/t；")
        f.write(f"HDPE 收入增加 = {sensitivity['hdpe_revenue_increase_rmb_per_t']:.1f} RMB/t\n")
        f.write(f"   收率下降造成的 LCOP 增加 = {sensitivity['lcop_increase_vs_green']:.1f} RMB/t\n")

    flow_path = BASE_DIR / "case1_process_flow.png"
    plot_process_flow(flow_path, mfa, input_mass)
    print(f"\n已保存结果文本: {output_txt}")
    print(f"已保存流程图: {flow_path}")


if __name__ == "__main__":
    main()
