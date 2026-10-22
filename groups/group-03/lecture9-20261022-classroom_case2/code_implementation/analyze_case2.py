"""Reproducible MFA-LCA-TEA analysis for the green methanol case study."""

from __future__ import annotations

import csv
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "case_files" / "data_cohort"
OUTPUT = HERE


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def value(row: dict[str, str], key: str) -> float:
    return float(row[key])


def solve_recycle_loop(fresh_feed: float, conversion: float, recycle_fraction: float) -> dict[str, float]:
    """Solve a single-reactant, perfectly separated recycle loop analytically."""
    denominator = 1.0 - recycle_fraction * (1.0 - conversion)
    reactor_feed = fresh_feed / denominator
    converted = conversion * reactor_feed
    purge = (1.0 - recycle_fraction) * (1.0 - conversion) * reactor_feed
    return {
        "reactor_feed": reactor_feed,
        "converted": converted,
        "purge": purge,
        "overall_conversion": converted / fresh_feed,
        "recycle": recycle_fraction * (1.0 - conversion) * reactor_feed,
    }


def compute_elemental_balance(streams: list[dict[str, str]]) -> dict[str, tuple[float, float]]:
    """Estimate C/H/O mass from listed stream compositions for the outer plant boundary."""
    by_id = {row["stream_id"]: row for row in streams}
    # H2 is generated from water inside the integrated plant, so do not count S02 again.
    # S04, S06-S10 and S13 are internal/intermediate streams and are not double-counted.
    inputs = [("S01", "co2_wt_pct"), ("S03", "h2o_wt_pct")]
    outputs = [
        ("S05", "o2_wt_pct"),
        ("S11", None),
        ("S12", "meoh_wt_pct"),
    ]
    # Elemental mass fractions in pure compounds; purge composition is taken from its row.
    compound_fractions = {
        "co2_wt_pct": (12.011 / 44.01, 0.0, 31.999 / 44.01),
        "h2_wt_pct": (0.0, 2.016 / 2.016, 0.0),
        "h2o_wt_pct": (0.0, 2.016 / 18.016, 15.999 / 18.016),
        "o2_wt_pct": (0.0, 0.0, 1.0),
        "meoh_wt_pct": (12.011 / 32.04, 4.032 / 32.04, 15.999 / 32.04),
    }

    def total(items: list[tuple[str, str | None]]) -> dict[str, float]:
        result = {element: 0.0 for element in ("C", "H", "O")}
        for stream_id, composition_key in items:
            row = by_id[stream_id]
            mass = value(row, "mass_flow_per_ton_product_kg")
            if composition_key is None:
                components = [
                    ("co2_wt_pct", "C"), ("h2_wt_pct", "H"),
                    ("meoh_wt_pct", "MeOH"), ("h2o_wt_pct", "H2O"),
                    ("o2_wt_pct", "O2"),
                ]
                for key, compound in components:
                    fraction = value(row, key) / 100.0
                    if compound == "MeOH":
                        fractions = compound_fractions["meoh_wt_pct"]
                    elif compound == "H2O":
                        fractions = compound_fractions["h2o_wt_pct"]
                    elif compound == "O2":
                        fractions = compound_fractions["o2_wt_pct"]
                    else:
                        fractions = compound_fractions[key]
                    for element, elemental_fraction in zip(("C", "H", "O"), fractions):
                        result[element] += mass * fraction * elemental_fraction
            else:
                fraction = value(row, composition_key) / 100.0
                fractions = compound_fractions[composition_key]
                for element, elemental_fraction in zip(("C", "H", "O"), fractions):
                    result[element] += mass * fraction * elemental_fraction
        return result

    incoming, outgoing = total(inputs), total(outputs)
    return {element: (incoming[element], outgoing[element]) for element in incoming}


def create_sensitivity_plot(tea_rows: list[dict[str, str]]) -> None:
    prices = [value(row, "electricity_price_rmb_per_kwh") for row in tea_rows]
    lcom = [value(row, "lcom_rmb_per_t") for row in tea_rows]
    premium = [value(row, "green_premium_rmb_per_t") for row in tea_rows]
    mac = [value(row, "mac_rmb_per_tCO2e") for row in tea_rows]

    plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), constrained_layout=True)
    axes[0].plot(prices, lcom, color="#147D73", marker="o", linewidth=2.4, label="LCOM")
    axes[0].plot(prices, premium, color="#D67C32", marker="s", linewidth=2, label="Green premium")
    axes[0].axhline(2500, color="#4B5563", linestyle="--", linewidth=1.2, label="Fossil methanol price")
    axes[0].set(xlabel="Electricity price (RMB/kWh)", ylabel="Cost (RMB/t methanol)", title="Cost and green premium")
    axes[0].grid(axis="y", alpha=0.22)
    axes[0].legend(frameon=False)
    axes[1].plot(prices, mac, color="#B94B4B", marker="o", linewidth=2.4, label="MAC")
    axes[1].axhline(100, color="#4B5563", linestyle="--", linewidth=1.2, label="Carbon price reference: 100 RMB/tCO2e")
    axes[1].axhline(0, color="#9CA3AF", linewidth=0.8)
    axes[1].set(xlabel="Electricity price (RMB/kWh)", ylabel="MAC (RMB/tCO2e)", title="Marginal abatement cost")
    axes[1].grid(axis="y", alpha=0.22)
    axes[1].legend(frameon=False)
    fig.suptitle("Power-to-methanol: electricity-price sensitivity", fontsize=14, fontweight="bold")
    fig.savefig(OUTPUT / "lcom_mac_sensitivity.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def create_process_flow() -> None:
    fig, ax = plt.subplots(figsize=(12, 6.5))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7)
    ax.axis("off")

    boxes = {
        "feed": (0.5, 3.35, 2.0, 1.25, "Fresh feeds\nCO2 1,423 kg | H2 198 kg", "#DCEFEA"),
        "reactor": (3.3, 3.35, 2.0, 1.25, "Methanol reactor\n25% single-pass conversion", "#FCE8D5"),
        "separator": (6.1, 3.35, 2.0, 1.25, "Cooler / separator\nGas 4,686 kg", "#E5E9F5"),
        "distill": (9.0, 3.35, 2.0, 1.25, "Distillation\nCrude methanol 1,575 kg", "#F3E5EF"),
        "product": (9.0, 0.65, 2.0, 1.0, "Product\n1,000 kg methanol", "#DCEFEA"),
        "purge": (6.1, 0.65, 2.0, 1.0, "Purge\n46 kg", "#F7DFDF"),
        "recycle": (3.3, 0.65, 2.0, 1.0, "Recycle gas\n4,640 kg", "#E8F0D9"),
    }
    for x, y, width, height, label, color in boxes.values():
        patch = FancyBboxPatch((x, y), width, height, boxstyle="round,pad=0.06,rounding_size=0.08", facecolor=color, edgecolor="#344054", linewidth=1.2)
        ax.add_patch(patch)
        ax.text(x + width / 2, y + height / 2, label, ha="center", va="center", fontsize=9.5)

    def arrow(start: tuple[float, float], end: tuple[float, float], label: str = "", curve: float = 0.0) -> None:
        patch = FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=13, linewidth=1.5, color="#475467", connectionstyle=f"arc3,rad={curve}")
        ax.add_patch(patch)
        if label:
            midpoint = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2 + (0.22 if curve >= 0 else -0.22))
            ax.text(*midpoint, label, ha="center", va="center", fontsize=8.5, color="#344054", bbox={"facecolor": "white", "edgecolor": "none", "pad": 1.5})

    arrow((2.5, 3.98), (3.3, 3.98), "fresh feed")
    arrow((5.3, 3.98), (6.1, 3.98), "reactor outlet")
    arrow((8.1, 3.98), (9.0, 3.98), "liquid 1,575 kg")
    arrow((10.0, 3.35), (10.0, 1.65), "refined methanol", curve=0.0)
    arrow((7.1, 3.35), (7.1, 1.65), "1% purge", curve=0.0)
    arrow((6.1, 3.55), (5.25, 1.3), "99% recycle", curve=-0.12)
    arrow((4.3, 1.65), (4.3, 3.35), "return to reactor", curve=-0.32)
    ax.text(6, 6.15, "Green methanol process flow and recycle loop", ha="center", fontsize=15, fontweight="bold")
    ax.text(6, 5.65, "Flow rates are per tonne of methanol; source data describe a 99:1 gas split.", ha="center", fontsize=9, color="#475467")
    ax.text(6, 0.15, "Source: case data_cohort/mfa_reaction_recycle_balance.csv", ha="center", fontsize=8, color="#667085")
    fig.savefig(OUTPUT / "process_flow.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    streams = read_csv(DATA / "mfa_reaction_recycle_balance.csv")
    lca_rows = read_csv(DATA / "lca_grid_scenarios_lci.csv")
    tea_rows = read_csv(DATA / "tea_lcom_sensitivity_data.csv")
    stream_by_id = {row["stream_id"]: row for row in streams}

    recycle = value(stream_by_id["S06"], "mass_flow_per_ton_product_kg")
    fresh_co2 = value(stream_by_id["S01"], "mass_flow_per_ton_product_kg")
    fresh_h2 = value(stream_by_id["S02"], "mass_flow_per_ton_product_kg")
    purge = value(stream_by_id["S11"], "mass_flow_per_ton_product_kg")
    offgas = value(stream_by_id["S10"], "mass_flow_per_ton_product_kg")
    recycle_fraction = recycle / (recycle + purge)
    loop = solve_recycle_loop(fresh_co2, 0.25, recycle_fraction)
    product_meoh = value(stream_by_id["S12"], "mass_flow_per_ton_product_kg")
    product_co2_equivalent = product_meoh * 44.01 / 32.04

    print("MFA: recycle-loop diagnostic")
    print(f"  CSV recycle split: {recycle_fraction:.4%} recycle / {1 - recycle_fraction:.4%} purge")
    print(f"  Recycle / (fresh CO2 + fresh H2), mass basis: {recycle / (fresh_co2 + fresh_h2):.4f} (claimed 3.8)")
    print(f"  Recycle / fresh CO2, mass basis: {recycle / fresh_co2:.4f}")
    print(f"  Ideal single-reactant loop overall conversion at 25% pass conversion: {loop['overall_conversion']:.4%}")
    print(f"  Product carbon expressed as CO2 / fresh CO2: {product_co2_equivalent / fresh_co2:.4%} (claimed 96.0%)")
    print(f"  Separator offgas / recycle / purge: {offgas:.1f} / {recycle:.1f} / {purge:.1f} kg per t product")

    balances = compute_elemental_balance(streams)
    print("Elemental balance from external-boundary stream compositions (kg element/t product):")
    for element, (incoming, outgoing) in balances.items():
        delta = outgoing - incoming
        relative = abs(delta) / incoming * 100 if incoming else math.nan
        print(f"  {element}: input={incoming:.3f}, output={outgoing:.3f}, delta={delta:+.3f} ({relative:.3f}% of input)")

    lca_total = {row["lci_inventory_item"]: row for row in lca_rows}
    green_gwp = value(lca_total["Net_Life_Cycle_GWP_Total"], "gwp_scenario_a_kgCO2e")
    grid_gwp = value(lca_total["Net_Life_Cycle_GWP_Total"], "gwp_scenario_b_kgCO2e")
    fossil_gwp = value(lca_total["Fossil_Benchmark_CtM"], "gwp_scenario_a_kgCO2e")
    reduction = fossil_gwp - green_gwp
    print("LCA (kg CO2e/t methanol):")
    print(f"  Renewable electricity: {green_gwp:.2f}; regional grid: {grid_gwp:.2f}; fossil benchmark: {fossil_gwp:.2f}")

    non_electric = value(tea_rows[0], "non_electricity_cost_rmb_per_t")
    electricity_use = sum(
        value(row, "flow_per_ton_product")
        for row in lca_rows
        if row["lci_inventory_item"].startswith("Electricity_")
    )
    carbon_price = 100.0
    break_even_price = (value(tea_rows[0], "fossil_methanol_price_rmb_per_t") + carbon_price * reduction / 1000 - non_electric) / electricity_use
    grid_parity = (
        value(tea_rows[0], "fossil_methanol_price_rmb_per_t") - non_electric
    ) / electricity_use
    print("TEA:")
    print(f"  Non-electric LCOM: {non_electric:.2f} RMB/t; electricity use: {electricity_use:.0f} kWh/t")
    print(f"  Max power price at MAC <= {carbon_price:.0f} RMB/tCO2e: {break_even_price:.4f} RMB/kWh")
    print(f"  Max power price for unsubsidized cost parity (MAC <= 0): {grid_parity:.4f} RMB/kWh")

    create_sensitivity_plot(tea_rows)
    create_process_flow()
    print(f"Charts written to: {OUTPUT}")


if __name__ == "__main__":
    main()