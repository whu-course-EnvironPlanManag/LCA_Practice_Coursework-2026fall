#!/usr/bin/env python3
"""Audit the Case 2 source tables, solve the recycle model, and draw outputs."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import schemdraw
from scipy.optimize import fsolve
from schemdraw import flow


CASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = CASE_DIR / "case_files" / "data_cohort"
OUTPUT_DIR = Path(__file__).resolve().parent
MOLECULAR_WEIGHTS = {
    "CO2": 44.009,
    "H2": 2.016,
    "CH3OH": 32.042,
    "H2O": 18.015,
    "O2": 31.998,
}
ELEMENT_MASS_FRACTIONS = {
    "CO2": {"C": 12.011 / MOLECULAR_WEIGHTS["CO2"], "O": 2 * 15.999 / MOLECULAR_WEIGHTS["CO2"]},
    "H2": {"H": 1.0},
    "CH3OH": {
        "C": 12.011 / MOLECULAR_WEIGHTS["CH3OH"],
        "H": 4.032 / MOLECULAR_WEIGHTS["CH3OH"],
        "O": 15.999 / MOLECULAR_WEIGHTS["CH3OH"],
    },
    "H2O": {
        "H": 2.016 / MOLECULAR_WEIGHTS["H2O"],
        "O": 15.999 / MOLECULAR_WEIGHTS["H2O"],
    },
    "O2": {"O": 1.0},
}
COMPOSITION_COLUMNS = {
    "CO2": "co2_wt_pct",
    "H2": "h2_wt_pct",
    "CH3OH": "meoh_wt_pct",
    "H2O": "h2o_wt_pct",
    "O2": "o2_wt_pct",
}


def read_case_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load the three published Case 2 cohort datasets."""
    return (
        pd.read_csv(DATA_DIR / "mfa_reaction_recycle_balance.csv"),
        pd.read_csv(DATA_DIR / "lca_grid_scenarios_lci.csv"),
        pd.read_csv(DATA_DIR / "tea_lcom_sensitivity_data.csv"),
    )


def stream_mass(mfa: pd.DataFrame, stream_name: str) -> float:
    rows = mfa.loc[mfa["stream_name"] == stream_name, "mass_flow_per_ton_product_kg"]
    if len(rows) != 1:
        raise ValueError(f"Expected one MFA stream named {stream_name!r}, found {len(rows)}")
    return float(rows.iloc[0])


def solve_recycle_model(mfa: pd.DataFrame) -> dict[str, float]:
    """Solve a CO2-equivalent, single-component recycle balance from the case data."""
    fresh_co2 = stream_mass(mfa, "Fresh_CO2_Feed")
    separator_offgas = stream_mass(mfa, "Separator_Offgas")
    listed_recycle = stream_mass(mfa, "Recycle_Gas_Loop")
    listed_purge = stream_mass(mfa, "Purge_Gas")
    recycle_fraction = listed_recycle / separator_offgas
    purge_fraction = 1 - recycle_fraction
    single_pass_conversion = 0.25

    def recycle_balance(values: np.ndarray) -> np.ndarray:
        recycle = float(values[0])
        return np.array(
            [recycle - recycle_fraction * (1 - single_pass_conversion) * (fresh_co2 + recycle)]
        )

    solution, info, status, message = fsolve(
        recycle_balance, np.array([fresh_co2 * 2.8]), full_output=True, xtol=1e-12
    )
    if status != 1:
        raise RuntimeError(f"Recycle solver did not converge: {message}")

    recycle = float(solution[0])
    residual = float(recycle_balance(solution)[0])
    reactor_co2 = fresh_co2 + recycle
    reacted_co2 = single_pass_conversion * reactor_co2
    purged_co2_equivalent = purge_fraction * (1 - single_pass_conversion) * reactor_co2
    overall_conversion = 1 - purged_co2_equivalent / fresh_co2
    return {
        "fresh_co2_kg": fresh_co2,
        "listed_recycle_kg": listed_recycle,
        "listed_purge_kg": listed_purge,
        "listed_offgas_kg": separator_offgas,
        "recycle_fraction": recycle_fraction,
        "purge_fraction": purge_fraction,
        "single_pass_conversion": single_pass_conversion,
        "solved_recycle_co2_equivalent_kg": recycle,
        "solved_recycle_ratio": recycle / fresh_co2,
        "listed_total_gas_recycle_ratio": listed_recycle
        / (
            stream_mass(mfa, "Fresh_CO2_Feed")
            + stream_mass(mfa, "Fresh_H2_Feed")
        ),
        "reactor_co2_equivalent_kg": reactor_co2,
        "reacted_co2_equivalent_kg": reacted_co2,
        "purged_co2_equivalent_kg": purged_co2_equivalent,
        "overall_carbon_utilization_pct": overall_conversion * 100,
        "solver_residual_kg": residual,
    }


def calculate_element_mass(row: pd.Series) -> dict[str, float]:
    """Estimate C/H/O masses from the species mass fractions in one CSV stream."""
    total = float(row["mass_flow_per_ton_product_kg"])
    result = {"C": 0.0, "H": 0.0, "O": 0.0}
    for species, column in COMPOSITION_COLUMNS.items():
        species_mass = total * float(row[column]) / 100
        for element, fraction in ELEMENT_MASS_FRACTIONS[species].items():
            result[element] += species_mass * fraction
    return result


def audit_reported_boundary(mfa: pd.DataFrame) -> dict[str, object]:
    """Check external streams as published; internal recycle water is excluded."""
    inputs = mfa.loc[
        mfa["stream_name"].isin(["Fresh_CO2_Feed", "Fresh_H2_Feed", "Demineralized_Water_Net"])
    ]
    outputs = mfa.loc[
        mfa["stream_name"].isin(
            ["Byproduct_Oxygen", "Purge_Gas", "Refined_Methanol_Product"]
        )
    ]
    input_elements = {"C": 0.0, "H": 0.0, "O": 0.0}
    output_elements = {"C": 0.0, "H": 0.0, "O": 0.0}
    for _, row in inputs.iterrows():
        for element, mass in calculate_element_mass(row).items():
            input_elements[element] += mass
    for _, row in outputs.iterrows():
        for element, mass in calculate_element_mass(row).items():
            output_elements[element] += mass

    element_deltas = {}
    for element in input_elements:
        delta = output_elements[element] - input_elements[element]
        element_deltas[element] = {
            "input_kg": input_elements[element],
            "output_kg": output_elements[element],
            "delta_kg": delta,
            "delta_pct_of_input": delta / input_elements[element] * 100
            if input_elements[element]
            else float("nan"),
        }

    input_mass = float(inputs["mass_flow_per_ton_product_kg"].sum())
    output_mass = float(outputs["mass_flow_per_ton_product_kg"].sum())
    return {
        "input_mass_kg": input_mass,
        "output_mass_kg": output_mass,
        "mass_delta_kg": output_mass - input_mass,
        "elements": element_deltas,
    }


def reaction_balance_checks() -> dict[str, dict[str, float]]:
    """Verify the two documented reaction equations independently of bad stream totals."""
    reactions = {
        "CO2 hydrogenation": {
            "input": {"CO2": 1.0, "H2": 3.0},
            "output": {"CH3OH": 1.0, "H2O": 1.0},
        },
        "PEM electrolysis": {
            "input": {"H2O": 2.0},
            "output": {"H2": 2.0, "O2": 1.0},
        },
    }
    atomic_mass = {"C": 12.011, "H": 1.008, "O": 15.999}
    atom_counts = {
        "CO2": {"C": 1, "O": 2},
        "H2": {"H": 2},
        "CH3OH": {"C": 1, "H": 4, "O": 1},
        "H2O": {"H": 2, "O": 1},
        "O2": {"O": 2},
    }
    checks = {}
    for name, sides in reactions.items():
        check = {}
        for element, atom_weight in atomic_mass.items():
            incoming = sum(
                amount * atom_counts[species].get(element, 0) * atom_weight
                for species, amount in sides["input"].items()
            )
            outgoing = sum(
                amount * atom_counts[species].get(element, 0) * atom_weight
                for species, amount in sides["output"].items()
            )
            check[element] = {
                "input_g_per_stoichiometric_extent": incoming,
                "output_g_per_stoichiometric_extent": outgoing,
                "delta_pct": (outgoing - incoming) / incoming * 100 if incoming else 0.0,
            }
        checks[name] = check
    return checks


def analyze_lca(lca: pd.DataFrame) -> dict[str, float]:
    """Recompute LCA totals from inventory rows and compare them with published totals."""
    summary_names = {
        "Net_Life_Cycle_GWP_Total",
        "Fossil_Benchmark_CtM",
        "Net_GHG_Reduction_vs_Benchmark",
    }
    inventory = lca.loc[~lca["lci_inventory_item"].isin(summary_names)]
    green_gwp = float(inventory["gwp_scenario_a_kgCO2e"].sum())
    grid_gwp = float(inventory["gwp_scenario_b_kgCO2e"].sum())
    published_green = float(
        lca.loc[
            lca["lci_inventory_item"] == "Net_Life_Cycle_GWP_Total",
            "gwp_scenario_a_kgCO2e",
        ].iloc[0]
    )
    published_grid = float(
        lca.loc[
            lca["lci_inventory_item"] == "Net_Life_Cycle_GWP_Total",
            "gwp_scenario_b_kgCO2e",
        ].iloc[0]
    )
    fossil = float(
        lca.loc[
            lca["lci_inventory_item"] == "Fossil_Benchmark_CtM",
            "gwp_scenario_a_kgCO2e",
        ].iloc[0]
    )
    electricity_kwh = float(
        lca.loc[
            lca["lci_inventory_item"].str.startswith("Electricity_"),
            "flow_per_ton_product",
        ].sum()
    )
    if not np.isclose(green_gwp, published_green, atol=0.02):
        raise ValueError(
            f"Green LCA total mismatch: calculated {green_gwp:.4f}, published {published_green:.4f}"
        )
    if not np.isclose(grid_gwp, published_grid, atol=0.02):
        raise ValueError(
            f"Grid LCA total mismatch: calculated {grid_gwp:.4f}, published {published_grid:.4f}"
        )
    if not np.isclose(electricity_kwh, 10826.0, atol=0.01):
        raise ValueError(f"Expected 10,826 kWh/t electricity use, got {electricity_kwh:g}")
    green_reduction_pct = (fossil - green_gwp) / fossil * 100
    grid_increase_pct = (grid_gwp - fossil) / fossil * 100
    return {
        "green_gwp": green_gwp,
        "grid_gwp": grid_gwp,
        "published_green_gwp": published_green,
        "published_grid_gwp": published_grid,
        "fossil_gwp": fossil,
        "electricity_kwh": electricity_kwh,
        "green_reduction_pct": green_reduction_pct,
        "grid_increase_pct": grid_increase_pct,
        "avoided_tco2e": (fossil - green_gwp) / 1000,
    }


def analyze_tea(tea: pd.DataFrame, lca_results: dict[str, float]) -> dict[str, object]:
    """Validate TEA data and compute price break-even with a 100 RMB/tCO2e carbon price."""
    required = {
        "electricity_price_rmb_per_kwh",
        "electricity_cost_rmb_per_t",
        "non_electricity_cost_rmb_per_t",
        "lcom_rmb_per_t",
        "fossil_methanol_price_rmb_per_t",
        "green_premium_rmb_per_t",
        "mac_rmb_per_tCO2e",
    }
    missing = required.difference(tea.columns)
    if missing:
        raise ValueError(f"TEA data is missing columns: {sorted(missing)}")

    result = tea.copy()
    result["calculated_lcom_rmb_per_t"] = (
        result["electricity_cost_rmb_per_t"] + result["non_electricity_cost_rmb_per_t"]
    )
    result["calculated_green_premium_rmb_per_t"] = (
        result["calculated_lcom_rmb_per_t"] - result["fossil_methanol_price_rmb_per_t"]
    )
    result["calculated_mac_rmb_per_tCO2e"] = (
        result["calculated_green_premium_rmb_per_t"] / lca_results["avoided_tco2e"]
    )
    result["calculated_electricity_cost_rmb_per_t"] = (
        result["electricity_price_rmb_per_kwh"] * lca_results["electricity_kwh"]
    )

    if not np.allclose(
        result["calculated_electricity_cost_rmb_per_t"],
        result["electricity_cost_rmb_per_t"],
        atol=0.02,
    ):
        raise ValueError("TEA electricity costs do not match price times total electricity use")
    if not np.allclose(
        result["calculated_lcom_rmb_per_t"], result["lcom_rmb_per_t"], atol=0.02
    ):
        raise ValueError("TEA LCOM data does not match electricity plus non-electricity costs")
    if not np.allclose(
        result["calculated_green_premium_rmb_per_t"],
        result["green_premium_rmb_per_t"],
        atol=0.02,
    ):
        raise ValueError("TEA green premiums do not match LCOM minus fossil methanol price")
    if not np.allclose(
        result["calculated_mac_rmb_per_tCO2e"],
        result["mac_rmb_per_tCO2e"],
        atol=0.03,
    ):
        raise ValueError("TEA MAC values do not match green premium divided by avoided GHG")

    carbon_price = 100.0
    carbon_credit_per_t = carbon_price * lca_results["avoided_tco2e"]
    fossil_price = float(result["fossil_methanol_price_rmb_per_t"].iloc[0])
    non_electric = float(result["non_electricity_cost_rmb_per_t"].iloc[0])
    target_lcom = fossil_price + carbon_credit_per_t
    threshold_price = (target_lcom - non_electric) / lca_results["electricity_kwh"]
    market_parity_price = (fossil_price - non_electric) / lca_results["electricity_kwh"]
    return {
        "sensitivity": result,
        "carbon_price_rmb_per_tco2e": carbon_price,
        "carbon_credit_rmb_per_t_product": carbon_credit_per_t,
        "break_even_lcom_rmb_per_t": target_lcom,
        "break_even_electricity_price_rmb_per_kwh": threshold_price,
        "market_parity_electricity_price_rmb_per_kwh": market_parity_price,
    }


def analyze_planning_case(lca_results: dict[str, float]) -> dict[str, float]:
    """Solve the lecture's mixed coal-grid and rooftop-PV carbon threshold."""
    electricity_kwh = lca_results["electricity_kwh"]
    coal_ef = 0.75
    solar_ef = 0.04
    co2_capture_credit = 1423.0
    fossil_gwp = 2600.0
    solar_share_threshold = (
        electricity_kwh * coal_ef - co2_capture_credit - fossil_gwp
    ) / (electricity_kwh * (coal_ef - solar_ef))
    annual_operating_hours = 8000.0
    rooftop_solar_hours = 1200.0
    return {
        "solar_share_threshold": solar_share_threshold,
        "rooftop_solar_capacity_factor": rooftop_solar_hours / annual_operating_hours,
        "capital_cost_multiplier_at_rooftop_solar_utilization": (
            annual_operating_hours / rooftop_solar_hours
        ),
    }


def draw_sensitivity_plot(
    tea_results: dict[str, object], output_dir: Path
) -> None:
    """Plot LCOM, green premium, and MAC across the supplied electricity prices."""
    data = tea_results["sensitivity"]
    prices = data["electricity_price_rmb_per_kwh"]
    threshold = float(tea_results["break_even_electricity_price_rmb_per_kwh"])
    fig, axes = plt.subplots(3, 1, figsize=(10, 10), sharex=True, constrained_layout=True)
    fig.suptitle("Green Methanol: Electricity Price Sensitivity", fontsize=15, weight="bold")

    axes[0].plot(prices, data["calculated_lcom_rmb_per_t"], marker="o", color="#176B87")
    axes[0].set_ylabel("LCOM (RMB/t)")
    axes[0].grid(True, alpha=0.25)

    axes[1].plot(
        prices,
        data["calculated_green_premium_rmb_per_t"],
        marker="o",
        color="#D97706",
    )
    axes[1].axhline(0, color="#555555", linewidth=0.8)
    axes[1].axhline(
        float(tea_results["carbon_credit_rmb_per_t_product"]),
        color="#2E8B57",
        linestyle="--",
        label="100 RMB/tCO2e carbon credit",
    )
    axes[1].axvline(threshold, color="#2E8B57", linestyle=":")
    axes[1].set_ylabel("Green premium (RMB/t)")
    axes[1].legend(frameon=False, loc="upper left")
    axes[1].grid(True, alpha=0.25)

    axes[2].plot(
        prices,
        data["calculated_mac_rmb_per_tCO2e"],
        marker="o",
        color="#7B2CBF",
    )
    axes[2].axhline(100, color="#2E8B57", linestyle="--", label="100 RMB/tCO2e")
    axes[2].axvline(threshold, color="#2E8B57", linestyle=":")
    axes[2].set_ylabel("MAC (RMB/tCO2e)")
    axes[2].set_xlabel("Electricity price (RMB/kWh)")
    axes[2].legend(frameon=False, loc="upper left")
    axes[2].grid(True, alpha=0.25)
    fig.savefig(output_dir / "tea_lcom_mac_sensitivity.png", dpi=300, bbox_inches="tight")
    fig.savefig(output_dir / "tea_lcom_mac_sensitivity.svg", bbox_inches="tight")
    plt.close(fig)


def draw_process_diagram(mfa: pd.DataFrame, output_dir: Path) -> None:
    """Draw the process and recycle loop using the selected schemdraw package."""
    output_dir.mkdir(parents=True, exist_ok=True)
    diagram = schemdraw.Drawing(show=False, dpi=300)

    def box(x: float, y: float, text: str, width: float = 2.0, height: float = 1.0):
        element = flow.Box(w=width, h=height).anchor("W").at((x, y)).label(text, fontsize=9)
        diagram.add(element)

    def line(start: tuple[float, float], end: tuple[float, float]):
        diagram.add(flow.Line().at(start).to(end))

    def arrow(start: tuple[float, float], end: tuple[float, float], label: str | None = None):
        element = flow.Arrow().at(start).to(end)
        if label:
            element.label(label, fontsize=8)
        diagram.add(element)

    fresh_co2 = stream_mass(mfa, "Fresh_CO2_Feed")
    fresh_h2 = stream_mass(mfa, "Fresh_H2_Feed")
    recycle = stream_mass(mfa, "Recycle_Gas_Loop")
    offgas = stream_mass(mfa, "Separator_Offgas")
    purge = stream_mass(mfa, "Purge_Gas")
    crude = stream_mass(mfa, "Crude_Methanol_Liquid")
    product = stream_mass(mfa, "Refined_Methanol_Product")
    water = stream_mass(mfa, "Distillation_Bottoms_Water")
    net_water = stream_mass(mfa, "Demineralized_Water_Net")
    oxygen = stream_mass(mfa, "Byproduct_Oxygen")
    recycle_pct = recycle / offgas * 100
    purge_pct = purge / offgas * 100

    box(0, 1.5, f"Captured CO2 feed\n{fresh_co2:,.0f} kg", 2.6, 1.4)
    box(3.6, 1.5, "Mixing and\npreheating", 2.6, 1.4)
    box(7.2, 1.5, "Fixed-bed reactor\nSingle-pass 25%", 2.6, 1.4)
    box(10.8, 1.5, f"Separator\nOff-gas {offgas:,.0f} kg", 2.6, 1.4)
    box(14.4, 1.5, f"Distillation\nCrude {crude:,.0f} kg", 2.6, 1.4)
    box(18, 1.5, f"Refined methanol\n{product:,.0f} kg", 2.6, 1.4)
    arrow((2.6, 1.5), (3.6, 1.5))
    arrow((6.2, 1.5), (7.2, 1.5))
    arrow((9.8, 1.5), (10.8, 1.5))
    arrow((13.4, 1.5), (14.4, 1.5))
    arrow((17, 1.5), (18, 1.5))

    box(7.2, 5, f"Recycle compressor\n{recycle:,.0f} kg ({recycle_pct:.1f}%)", 2.6, 1.2)
    arrow((12.1, 2.2), (12.1, 5))
    arrow((12.1, 5), (9.8, 5))
    line((7.2, 5), (4.9, 5))
    arrow((4.9, 5), (4.9, 2.2), "Recycle gas to mixer")

    box(14.4, -0.8, f"Purge gas\n{purge:,.0f} kg ({purge_pct:.1f}%)\nTo boiler", 2.6, 1.4)
    line((12.1, 0.8), (12.1, 0))
    line((12.1, 0), (15.7, 0))
    arrow((15.7, 0), (15.7, -0.1))

    box(
        0,
        -1.5,
        f"PEM electrolyzer\nH2 {fresh_h2:,.0f} kg\nNet water {net_water:,.0f} kg",
        2.6,
        1.4,
    )
    box(-3, -1.5, f"O2 by-product\n{oxygen:,.0f} kg", 2.2, 1.4)
    arrow((0, -1.5), (-0.8, -1.5))
    line((2.6, -1.5), (4.9, -1.5))
    arrow((4.9, -1.5), (4.9, 0.8), "fresh H2")

    line((17, 0.8), (17.6, 0.8))
    line((17.6, 0.8), (17.6, -3))
    arrow((17.6, -3), (1.3, -3), f"recovered water {water:,.0f} kg")
    arrow((1.3, -3), (1.3, -2.2))

    diagram.save(str(output_dir / "methanol_recycle_process.png"), dpi=300)
    diagram.save(str(output_dir / "methanol_recycle_process.svg"))


def print_results(
    recycle: dict[str, float],
    boundary: dict[str, object],
    reactions: dict[str, dict[str, float]],
    lca: dict[str, float],
    tea: dict[str, object],
    planning: dict[str, float],
) -> None:
    print("MFA recycle model (CO2-equivalent single-component basis)")
    print(f"  Listed gas recycle split: {recycle['recycle_fraction'] * 100:.4f}%")
    print(f"  Solver residual: {recycle['solver_residual_kg']:.3e} kg")
    print(
        "  Solved recycle CO2-equivalent flow: "
        f"{recycle['solved_recycle_co2_equivalent_kg']:.3f} kg/t"
    )
    print(f"  Solved recycle ratio: {recycle['solved_recycle_ratio']:.4f}:1")
    print(
        "  Listed total-gas recycle ratio (recycle / fresh CO2+H2): "
        f"{recycle['listed_total_gas_recycle_ratio']:.4f}:1"
    )
    print(
        "  Calculated overall CO2 utilization: "
        f"{recycle['overall_carbon_utilization_pct']:.4f}%"
    )
    print("  Handout reference values: 3.8:1 recycle ratio; 96.0% carbon utilization")
    print()

    print("Reported external-stream boundary audit (internal water recycle excluded)")
    print(
        f"  Mass in/out: {boundary['input_mass_kg']:.3f} / "
        f"{boundary['output_mass_kg']:.3f} kg; delta "
        f"{boundary['mass_delta_kg']:.3f} kg"
    )
    print("  Element | input kg | output kg | output-input kg | deviation of input")
    for element, values in boundary["elements"].items():
        print(
            f"  {element:>7} | {values['input_kg']:>8.3f} | {values['output_kg']:>9.3f} | "
            f"{values['delta_kg']:>14.3f} | {values['delta_pct_of_input']:>+8.3f}%"
        )
    print("  Required full-system tolerance: absolute element deviation < 0.01%.")
    print("  Reaction-level stoichiometric checks:")
    for reaction, checks in reactions.items():
        deviations = ", ".join(
            f"{element} {values['delta_pct']:+.6f}%"
            for element, values in checks.items()
        )
        print(f"    {reaction}: {deviations}")
    print()

    print("LCA")
    print(
        f"  Green power: {lca['green_gwp']:.2f} kg CO2e/t; "
        f"reduction vs. coal methanol {lca['green_reduction_pct']:.2f}%"
    )
    print(
        f"  Regional grid: {lca['grid_gwp']:.2f} kg CO2e/t; "
        f"increase vs. coal methanol {lca['grid_increase_pct']:.2f}%"
    )
    print(f"  Electricity use: {lca['electricity_kwh']:.1f} kWh/t")
    print()

    print("TEA")
    print(
        f"  100 RMB/tCO2e credit: {tea['carbon_credit_rmb_per_t_product']:.2f} RMB/t product"
    )
    print(
        "  Highest electricity price at break-even with that credit: "
        f"{tea['break_even_electricity_price_rmb_per_kwh']:.5f} RMB/kWh"
    )
    print(
        "  Market-parity electricity price without carbon value: "
        f"{tea['market_parity_electricity_price_rmb_per_kwh']:.5f} RMB/kWh"
    )
    print()

    print("Planning exercise")
    print(
        "  Minimum rooftop-PV share to beat the coal-methanol GWP: "
        f"{planning['solar_share_threshold'] * 100:.2f}%"
    )
    print(
        f"  Rooftop-PV-only capacity factor: "
        f"{planning['rooftop_solar_capacity_factor'] * 100:.1f}%"
    )
    print(
        "  Indicative capital-cost multiplier at 1,200 h vs. 8,000 h: "
        f"{planning['capital_cost_multiplier_at_rooftop_solar_utilization']:.2f}x"
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    mfa, lca_data, tea_data = read_case_data()
    recycle = solve_recycle_model(mfa)
    boundary = audit_reported_boundary(mfa)
    reactions = reaction_balance_checks()
    lca = analyze_lca(lca_data)
    tea = analyze_tea(tea_data, lca)
    planning = analyze_planning_case(lca)
    draw_sensitivity_plot(tea, OUTPUT_DIR)
    draw_process_diagram(mfa, OUTPUT_DIR)
    print_results(recycle, boundary, reactions, lca, tea, planning)


if __name__ == "__main__":
    main()
