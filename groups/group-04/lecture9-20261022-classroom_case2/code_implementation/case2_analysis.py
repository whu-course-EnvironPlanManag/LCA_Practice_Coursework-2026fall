from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager
from scipy.optimize import fsolve


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent / "case_files" / "data_cohort"
MFA_FILE = DATA_DIR / "mfa_reaction_recycle_balance.csv"
LCA_FILE = DATA_DIR / "lca_grid_scenarios_lci.csv"
TEA_FILE = DATA_DIR / "tea_lcom_sensitivity_data.csv"

SINGLE_PASS_CONVERSION = 0.25
RECYCLE_SPLIT = 0.99
CARBON_PRICE_RMB_PER_T = 100.0
FOSSIL_METHANOL_PRICE_RMB_PER_T = 2500.0
ELEMENT_BALANCE_TOLERANCE_PCT = 0.01
OUTPUT_DPI = 301


def read_csv(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Required case data file not found: {path}")
    return pd.read_csv(path)


def unique_row(frame: pd.DataFrame, column: str, value: str) -> pd.Series:
    rows = frame.loc[frame[column].eq(value)]
    if len(rows) != 1:
        raise ValueError(f"Expected exactly one row for {value!r} in {column}, found {len(rows)}")
    return rows.iloc[0]


def mass_of(row: pd.Series) -> float:
    mass = float(row["mass_flow_per_ton_product_kg"])
    if not np.isfinite(mass) or mass < 0:
        raise ValueError(f"Invalid mass flow for {row.get('stream_name', 'unknown stream')}: {mass}")
    return mass


def component_fraction(row: pd.Series, component: str) -> float:
    fraction = float(row[f"{component}_wt_pct"]) / 100.0
    if not np.isfinite(fraction) or not 0 <= fraction <= 1:
        raise ValueError(f"Invalid {component} mass fraction in stream {row['stream_name']}")
    return fraction


def component_mass(row: pd.Series, component: str) -> float:
    return mass_of(row) * component_fraction(row, component)


def element_mass(row: pd.Series, element: str) -> float:
    """Estimate elemental mass from listed species mass fractions and formulas."""
    co2 = component_mass(row, "co2") * (12.0 / 44.0)
    hydrogen = (
        component_mass(row, "h2")
        + component_mass(row, "meoh") * (4.0 / 32.0)
        + component_mass(row, "h2o") * (2.0 / 18.0)
    )
    oxygen = (
        component_mass(row, "co2") * (32.0 / 44.0)
        + component_mass(row, "meoh") * (16.0 / 32.0)
        + component_mass(row, "h2o") * (16.0 / 18.0)
        + component_mass(row, "o2")
    )
    return {"C": co2 + component_mass(row, "meoh") * (12.0 / 32.0),
            "H": hydrogen,
            "O": oxygen}[element]


def solve_recycle(mfa: pd.DataFrame) -> dict[str, float]:
    fresh_co2 = mass_of(unique_row(mfa, "stream_name", "Fresh_CO2_Feed"))
    fresh_h2 = mass_of(unique_row(mfa, "stream_name", "Fresh_H2_Feed"))
    fresh_gas = fresh_co2 + fresh_h2

    def recycle_balance(values: np.ndarray) -> np.ndarray:
        recycle_mass = float(values[0])
        unreacted_outlet = (1.0 - SINGLE_PASS_CONVERSION) * (fresh_gas + recycle_mass)
        return np.array([recycle_mass - RECYCLE_SPLIT * unreacted_outlet])

    solution, info, ier, message = fsolve(
        recycle_balance, np.array([fresh_gas]), full_output=True
    )
    if ier != 1:
        raise RuntimeError(f"Recycle balance solver did not converge: {message}")
    recycle_mass = float(solution[0])
    residual = float(abs(recycle_balance(solution)[0]))
    if residual > 1e-8:
        raise RuntimeError(f"Recycle balance residual is too large: {residual:g} kg")

    overall_gas_conversion_proxy = (
        SINGLE_PASS_CONVERSION * (fresh_gas + recycle_mass) / fresh_gas
    )
    listed_recycle = mass_of(unique_row(mfa, "stream_name", "Recycle_Gas_Loop"))
    listed_offgas = mass_of(unique_row(mfa, "stream_name", "Separator_Offgas"))
    listed_purge = mass_of(unique_row(mfa, "stream_name", "Purge_Gas"))
    listed_mix = mass_of(unique_row(mfa, "stream_name", "Reactor_Inlet_Mix"))

    fresh_carbon = element_mass(unique_row(mfa, "stream_name", "Fresh_CO2_Feed"), "C")
    product_carbon = element_mass(
        unique_row(mfa, "stream_name", "Refined_Methanol_Product"), "C"
    )
    data_carbon_utilization = product_carbon / fresh_carbon

    return {
        "fresh_gas_kg": fresh_gas,
        "solved_recycle_kg": recycle_mass,
        "solved_recycle_to_fresh_gas_ratio": recycle_mass / fresh_gas,
        "solved_single_pass_conversion_pct": SINGLE_PASS_CONVERSION * 100,
        "solved_overall_gas_conversion_proxy_pct": overall_gas_conversion_proxy * 100,
        "solver_residual_kg": residual,
        "listed_recycle_kg": listed_recycle,
        "listed_recycle_ratio": listed_recycle / (fresh_co2 + fresh_h2),
        "listed_recycle_split_pct": listed_recycle / listed_offgas * 100,
        "listed_purge_split_pct": listed_purge / listed_offgas * 100,
        "listed_mixer_closure_kg": listed_mix - listed_recycle - fresh_co2 - fresh_h2,
        "data_carbon_utilization_pct": data_carbon_utilization * 100,
    }


def calculate_element_balances(mfa: pd.DataFrame) -> dict[str, dict[str, float]]:
    external_inputs = [
        "Fresh_CO2_Feed",
        "Fresh_H2_Feed",
        "Demineralized_Water_Net",
    ]
    external_outputs = [
        "Byproduct_Oxygen",
        "Purge_Gas",
        "Refined_Methanol_Product",
    ]
    rows = mfa.set_index("stream_name")
    results: dict[str, dict[str, float]] = {}

    for element in ("C", "H", "O"):
        input_mass = sum(element_mass(rows.loc[name], element) for name in external_inputs)
        output_mass = sum(element_mass(rows.loc[name], element) for name in external_outputs)
        difference = output_mass - input_mass
        difference_pct = abs(difference) / input_mass * 100 if input_mass else float("inf")
        results[element] = {
            "input_kg": input_mass,
            "output_kg": output_mass,
            "difference_kg": difference,
            "difference_pct": difference_pct,
        }
    return results


def load_lca_results(lca: pd.DataFrame) -> dict[str, float]:
    total = unique_row(lca, "lci_inventory_item", "Net_Life_Cycle_GWP_Total")
    fossil = unique_row(lca, "lci_inventory_item", "Fossil_Benchmark_CtM")
    green_gwp = float(total["gwp_scenario_a_kgCO2e"])
    grid_gwp = float(total["gwp_scenario_b_kgCO2e"])
    fossil_gwp = float(fossil["gwp_scenario_a_kgCO2e"])
    return {
        "green_gwp_kgco2e_per_t": green_gwp,
        "grid_gwp_kgco2e_per_t": grid_gwp,
        "fossil_gwp_kgco2e_per_t": fossil_gwp,
        "green_abatement_tco2e_per_t": (fossil_gwp - green_gwp) / 1000.0,
    }


def load_tea_curves(tea: pd.DataFrame, lca_results: dict[str, float]) -> pd.DataFrame:
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
        raise ValueError(f"TEA data is missing required columns: {', '.join(sorted(missing))}")

    curves = tea.copy()
    for column in required:
        curves[column] = pd.to_numeric(curves[column], errors="raise")
    curves = curves.sort_values("electricity_price_rmb_per_kwh").reset_index(drop=True)
    prices = curves["electricity_price_rmb_per_kwh"].to_numpy()
    if len(prices) < 2 or np.any(np.diff(prices) <= 0):
        raise ValueError("TEA electricity prices must be unique and strictly increasing")

    abatement = lca_results["green_abatement_tco2e_per_t"]
    if abatement <= 0:
        raise ValueError("Green methanol must have positive abatement versus fossil methanol")
    curves["mac_recalculated_rmb_per_tCO2e"] = (
        curves["green_premium_rmb_per_t"] / abatement
    )
    return curves


def find_break_even_price(
    curves: pd.DataFrame, lca_results: dict[str, float]
) -> dict[str, float]:
    electricity_use = (
        curves["electricity_cost_rmb_per_t"]
        / curves["electricity_price_rmb_per_kwh"]
    )
    electricity_use_value = float(electricity_use.median())
    if not np.allclose(electricity_use, electricity_use_value, rtol=1e-6, atol=1e-6):
        raise ValueError("TEA dataset does not support a constant electricity use per tonne")

    non_electric_cost = float(curves["non_electricity_cost_rmb_per_t"].iloc[0])
    if not np.allclose(curves["non_electricity_cost_rmb_per_t"], non_electric_cost):
        raise ValueError("TEA non-electricity cost varies; cannot use linear threshold formula")
    fossil_price = float(curves["fossil_methanol_price_rmb_per_t"].iloc[0])
    if not np.allclose(curves["fossil_methanol_price_rmb_per_t"], fossil_price):
        raise ValueError("Fossil methanol benchmark varies across TEA scenarios")

    carbon_credit = (
        CARBON_PRICE_RMB_PER_T * lca_results["green_abatement_tco2e_per_t"]
    )
    threshold = (
        fossil_price + carbon_credit - non_electric_cost
    ) / electricity_use_value
    return {
        "carbon_price_rmb_per_tco2e": CARBON_PRICE_RMB_PER_T,
        "carbon_credit_rmb_per_t_product": carbon_credit,
        "break_even_electricity_price_rmb_per_kwh": threshold,
        "electricity_use_kwh_per_t": electricity_use_value,
    }


def plot_economic_sensitivity(curves: pd.DataFrame, path: Path) -> None:
    plt.rcParams["font.family"] = font_manager.FontProperties(
        fname=font_manager.findfont("Microsoft YaHei")
    ).get_name()
    plt.rcParams["axes.unicode_minus"] = False

    price = np.linspace(0.05, 0.60, 111)
    electricity_use = float(
        (
            curves["electricity_cost_rmb_per_t"]
            / curves["electricity_price_rmb_per_kwh"]
        ).median()
    )
    non_electric_cost = float(curves["non_electricity_cost_rmb_per_t"].iloc[0])
    fossil_price = float(curves["fossil_methanol_price_rmb_per_t"].iloc[0])
    lcom = electricity_use * price + non_electric_cost
    premium = lcom - fossil_price
    avoided_emissions = float(
        curves["green_premium_rmb_per_t"].iloc[0]
        / curves["mac_recalculated_rmb_per_tCO2e"].iloc[0]
    )
    mac = premium / avoided_emissions

    fig, ax = plt.subplots(figsize=(11, 6.5), dpi=300)
    ax.plot(price, lcom, color="#2563eb", linewidth=2.2, label="LCOM")
    ax.plot(price, premium, color="#ea580c", linewidth=2.2, label="绿色溢价")
    ax.axhline(fossil_price, color="#64748b", linestyle=":", linewidth=1.2, label="化石甲醇基准价")
    ax.set_xlabel("电价 (元/kWh)")
    ax.set_ylabel("LCOM / 绿色溢价 (元/t 甲醇)")
    ax.set_xlim(0.05, 0.60)
    ax.grid(True, alpha=0.25)

    ax_mac = ax.twinx()
    ax_mac.plot(price, mac, color="#15803d", linewidth=2.0, label="MAC")
    ax_mac.axhline(
        CARBON_PRICE_RMB_PER_T,
        color="#15803d",
        linestyle="--",
        linewidth=1.2,
        label="碳价 100 元/t CO2e",
    )
    ax_mac.set_ylabel("MAC (元/t CO2e)")

    handles, labels = [], []
    for axis in (ax, ax_mac):
        axis_handles, axis_labels = axis.get_legend_handles_labels()
        labels.extend(axis_labels)
        handles.extend(axis_handles)
    ax.legend(handles, labels, loc="upper left", frameon=True)
    ax.set_title("绿色甲醇电价敏感性：LCOM、绿色溢价与 MAC")
    fig.tight_layout()
    fig.savefig(path, dpi=OUTPUT_DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def plot_process_flow(mfa: pd.DataFrame, path: Path) -> None:
    plt.rcParams["font.family"] = font_manager.FontProperties(
        fname=font_manager.findfont("Microsoft YaHei")
    ).get_name()
    plt.rcParams["axes.unicode_minus"] = False
    def stream_mass(name: str) -> float:
        return mass_of(unique_row(mfa, "stream_name", name))

    recycle_fraction = (
        stream_mass("Recycle_Gas_Loop") / stream_mass("Separator_Offgas")
    )
    purge_fraction = stream_mass("Purge_Gas") / stream_mass("Separator_Offgas")
    fig, ax = plt.subplots(figsize=(15, 8), dpi=300)
    ax.set_xlim(0, 15.2)
    ax.set_ylim(0.7, 9)
    ax.axis("off")
    ax.set_title("CO2 捕集耦合绿氢合成绿色甲醇工艺流程图", fontsize=17, pad=18)

    boxes = {
        "co2": (0.25, 6.85, 1.8, 0.95, f"新鲜 CO2\n{stream_mass('Fresh_CO2_Feed'):,.0f} kg"),
        "h2": (0.25, 5.05, 1.8, 0.95, f"绿氢 H2\n{stream_mass('Fresh_H2_Feed'):,.0f} kg"),
        "mix": (2.75, 5.75, 1.65, 1.15, "混合 / 预热"),
        "reactor": (5.0, 5.75, 1.9, 1.15, "固定床反应器\n单程转化率 25%"),
        "separator": (7.55, 5.75, 1.9, 1.15, "冷凝与气液分离"),
        "split": (
            10.05, 5.75, 1.75, 1.15,
            f"循环气分流\n{recycle_fraction:.0%} / {purge_fraction:.0%}",
        ),
        "compressor": (7.55, 2.7, 2.0, 1.0, "循环压缩机"),
        "distill": (11.4, 3.65, 1.8, 1.0, "双塔精馏"),
        "product": (13.7, 3.65, 1.35, 1.0, f"精甲醇\n{stream_mass('Refined_Methanol_Product'):,.0f} kg"),
        "water": (11.4, 1.75, 1.8, 0.85, f"回流水\n{stream_mass('Distillation_Bottoms_Water'):,.0f} kg"),
        "purge": (10.05, 8.0, 1.75, 0.8, f"驰放气\n{stream_mass('Purge_Gas'):,.0f} kg"),
        "oxygen": (5.0, 2.7, 1.9, 1.0, f"副产氧气\n{stream_mass('Byproduct_Oxygen'):,.0f} kg"),
        "electrolyzer": (2.75, 2.7, 1.65, 1.0, "PEM 电解槽"),
        "water_feed": (0.25, 2.7, 1.8, 1.0, f"净补水\n{stream_mass('Demineralized_Water_Net'):,.0f} kg"),
    }
    for x, y, width, height, label in boxes.values():
        ax.add_patch(
            plt.Rectangle(
                (x, y), width, height, facecolor="#e8f1ff",
                edgecolor="#334155", linewidth=1.4,
            )
        )
        ax.text(x + width / 2, y + height / 2, label, ha="center", va="center", fontsize=9)
    for key in ("product", "oxygen", "purge"):
        x, y, width, height, label = boxes[key]
        ax.add_patch(
            plt.Rectangle(
                (x, y), width, height, facecolor="#e7f5e8",
                edgecolor="#334155", linewidth=1.4,
            )
        )
        ax.text(x + width / 2, y + height / 2, label, ha="center", va="center", fontsize=9)

    def center(key: str) -> tuple[float, float]:
        x, y, width, height, _ = boxes[key]
        return (x + width / 2, y + height / 2)

    def connect(
        source: str,
        target: str,
        label: str = "",
        *,
        source_anchor: str = "right",
        target_anchor: str = "left",
        color: str = "#334155",
        rad: float = 0.0,
    ) -> None:
        sx, sy = center(source)
        tx, ty = center(target)
        source_box, target_box = boxes[source], boxes[target]
        starts = {
            "right": (source_box[0] + source_box[2], sy),
            "left": (source_box[0], sy),
            "top": (sx, source_box[1] + source_box[3]),
            "bottom": (sx, source_box[1]),
        }
        ends = {
            "right": (target_box[0] + target_box[2], ty),
            "left": (target_box[0], ty),
            "top": (tx, target_box[1] + target_box[3]),
            "bottom": (tx, target_box[1]),
        }
        ax.annotate(
            "", xy=ends[target_anchor], xytext=starts[source_anchor],
            arrowprops=dict(
                arrowstyle="-|>", color=color, lw=1.5,
                connectionstyle=f"arc3,rad={rad}",
            ),
        )
        if label:
            ax.text((sx + tx) / 2, (sy + ty) / 2 + 0.16, label,
                    ha="center", va="center", fontsize=8, color=color)

    connect("co2", "mix", "CO2", source_anchor="right", target_anchor="top")
    connect("h2", "mix", "H2")
    connect("mix", "reactor")
    connect("reactor", "separator")
    connect("separator", "split")
    connect("split", "purge", source_anchor="top", target_anchor="bottom")
    connect("split", "compressor", source_anchor="bottom", target_anchor="top")
    compressor_box = boxes["compressor"]
    mix_box = boxes["mix"]
    recycle_start = (compressor_box[0], compressor_box[1] + compressor_box[3] / 2)
    mix_bottom = (mix_box[0] + mix_box[2] / 2, mix_box[1])
    recycle_route_y = 4.35
    ax.plot(
        [recycle_start[0], recycle_start[0] - 0.35, mix_bottom[0], mix_bottom[0]],
        [recycle_start[1], recycle_route_y, recycle_route_y, mix_bottom[1]],
        color="#334155",
        linewidth=1.5,
    )
    ax.annotate(
        "",
        xy=mix_bottom,
        xytext=(mix_bottom[0], recycle_route_y),
        arrowprops=dict(arrowstyle="-|>", color="#334155", lw=1.5),
    )
    ax.text(5.55, 4.55, "Recycle loop", ha="center", fontsize=8, color="#334155")
    connect("separator", "distill", source_anchor="bottom", target_anchor="top")
    connect("distill", "product")
    connect("distill", "water", source_anchor="bottom", target_anchor="top")
    connect("water_feed", "electrolyzer")
    connect("electrolyzer", "h2", "H2", source_anchor="top", target_anchor="bottom", rad=-0.2)
    connect("electrolyzer", "oxygen", "O2 副产品")
    water_box = boxes["water"]
    electrolyzer_box = boxes["electrolyzer"]
    water_start = (water_box[0] + water_box[2] / 2, water_box[1])
    loop_y = 1.15
    ax.plot(
        [water_start[0], water_start[0], electrolyzer_box[0] + electrolyzer_box[2] / 2],
        [water_start[1], loop_y, loop_y],
        color="#15803d",
        linewidth=1.5,
    )
    ax.annotate(
        "",
        xy=(electrolyzer_box[0] + electrolyzer_box[2] / 2, electrolyzer_box[1]),
        xytext=(electrolyzer_box[0] + electrolyzer_box[2] / 2, loop_y),
        arrowprops=dict(arrowstyle="-|>", color="#15803d", lw=1.5),
    )
    ax.text(7.7, 1.3, "575 kg 回用至电解槽", ha="center", fontsize=8, color="#15803d")
    ax.text(
        9.8, 7.05,
        f"未反应气 {stream_mass('Separator_Offgas'):,.0f} kg",
        ha="center", fontsize=8, color="#334155",
    )
    ax.text(
        11.6, 5.0,
        f"粗甲醇液相 {stream_mass('Crude_Methanol_Liquid'):,.0f} kg",
        ha="center", fontsize=8, color="#334155",
    )
    ax.text(
        11.25, 7.0, f"{purge_fraction:.0%} 驰放",
        ha="center", fontsize=8, color="#334155",
    )
    ax.text(
        10.35, 4.85, f"{recycle_fraction:.0%} 回流",
        ha="center", fontsize=8, color="#334155",
    )

    ax.text(
        7.5, 0.65,
        "流程及标注质量来自 mfa_reaction_recycle_balance.csv；回流水为系统内部流，不重复计入外部进料。",
        ha="center", va="center", fontsize=9, color="#475569",
    )
    fig.tight_layout()
    fig.savefig(path, dpi=OUTPUT_DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def write_results(
    path: Path,
    recycle: dict[str, float],
    balances: dict[str, dict[str, float]],
    lca: dict[str, float],
    break_even: dict[str, float],
    curves: pd.DataFrame,
) -> None:
    carbon_price_mac = (
        float(
            np.interp(
                break_even["break_even_electricity_price_rmb_per_kwh"],
                curves["electricity_price_rmb_per_kwh"],
                curves["mac_recalculated_rmb_per_tCO2e"],
            )
        )
    )
    lines = [
        "=== Case 2: CO2-to-methanol MFA-LCA-TEA results ===",
        "",
        "[Task 1: recycle loop]",
        f"Single-pass conversion (model input): {recycle['solved_single_pass_conversion_pct']:.2f}%",
        f"Recycle / fresh CO2+H2 mass ratio (fsolve): "
        f"{recycle['solved_recycle_to_fresh_gas_ratio']:.4f}",
        "Overall gas-conversion proxy (fsolve; not carbon utilization): "
        f"{recycle['solved_overall_gas_conversion_proxy_pct']:.4f}%",
        f"fsolve equation residual: {recycle['solver_residual_kg']:.3e} kg per normalized basis",
        f"CSV recycle flow / fresh CO2+H2 feed: {recycle['listed_recycle_ratio']:.4f}",
        f"CSV recycle / offgas split: {recycle['listed_recycle_split_pct']:.4f}% recycle; "
        f"{recycle['listed_purge_split_pct']:.4f}% purge",
        f"CSV reactor-mixer mass closure (listed mix - fresh - recycle): "
        f"{recycle['listed_mixer_closure_kg']:.2f} kg",
        f"CSV-based carbon utilization (product carbon / fresh CO2 carbon): "
        f"{recycle['data_carbon_utilization_pct']:.4f}%",
        "Data check: the solved 99% recycle / 25% single-pass gas model does not equal "
        "the documentation's 3.8 recycle ratio or 96.0% carbon utilization.",
        "Recycle ratio basis: total recycle gas mass divided by fresh CO2+H2 feed mass; "
        "CSV ratio is calculated directly from its listed streams.",
        "",
        "External elemental balance (net demineralized water is an input; recovered water is internal):",
    ]
    for element, result in balances.items():
        status = "PASS" if result["difference_pct"] < ELEMENT_BALANCE_TOLERANCE_PCT else "FAIL"
        lines.append(
            f"{element}: input={result['input_kg']:.3f} kg; "
            f"output={result['output_kg']:.3f} kg; "
            f"output-input={result['difference_kg']:+.3f} kg; "
            f"relative difference={result['difference_pct']:.4f}% [{status}]"
        )
    lines.extend(
        [
            "The supplied stream table does not close elemental balances to the required "
            "0.01%; see these differences as source-data inconsistencies, not solver error.",
            "",
            "[Task 2: LCA and TEA]",
            f"Green-power GWP: {lca['green_gwp_kgco2e_per_t']:.2f} kg CO2e/t methanol",
            f"Regional-grid GWP: {lca['grid_gwp_kgco2e_per_t']:.2f} kg CO2e/t methanol",
            f"Fossil methanol benchmark: {lca['fossil_gwp_kgco2e_per_t']:.2f} kg CO2e/t",
            f"Green scenario abatement vs fossil: {lca['green_abatement_tco2e_per_t']:.5f} t CO2e/t",
            f"Electricity-price break-even with carbon price "
            f"{break_even['carbon_price_rmb_per_tco2e']:.2f} RMB/tCO2e: "
            f"{break_even['break_even_electricity_price_rmb_per_kwh']:.5f} RMB/kWh",
            f"Interpolated MAC at break-even price: {carbon_price_mac:.2f} RMB/tCO2e",
            f"Electricity use implied by TEA data: "
            f"{break_even['electricity_use_kwh_per_t']:.1f} kWh/t methanol",
            f"At 0.15 RMB/kWh: LCOM={float(np.interp(0.15, curves['electricity_price_rmb_per_kwh'], curves['lcom_rmb_per_t'])):.2f} RMB/t; "
            f"MAC={float(np.interp(0.15, curves['electricity_price_rmb_per_kwh'], curves['mac_recalculated_rmb_per_tCO2e'])):.2f} RMB/tCO2e",
            f"At 0.35 RMB/kWh: LCOM={float(np.interp(0.35, curves['electricity_price_rmb_per_kwh'], curves['lcom_rmb_per_t'])):.2f} RMB/t; "
            f"MAC={float(np.interp(0.35, curves['electricity_price_rmb_per_kwh'], curves['mac_recalculated_rmb_per_tCO2e'])):.2f} RMB/tCO2e",
            "",
            "Outputs: case2_economic_sensitivity.png, case2_process_flow.png",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    mfa = read_csv(MFA_FILE)
    lca_data = read_csv(LCA_FILE)
    tea_data = read_csv(TEA_FILE)

    recycle = solve_recycle(mfa)
    balances = calculate_element_balances(mfa)
    lca_results = load_lca_results(lca_data)
    curves = load_tea_curves(tea_data, lca_results)
    break_even = find_break_even_price(curves, lca_results)

    sensitivity_path = BASE_DIR / "case2_economic_sensitivity.png"
    flow_path = BASE_DIR / "case2_process_flow.png"
    results_path = BASE_DIR / "case2_analysis_results.txt"
    plot_economic_sensitivity(curves, sensitivity_path)
    plot_process_flow(mfa, flow_path)
    write_results(results_path, recycle, balances, lca_results, break_even, curves)

    print("=== Case 2 MFA-LCA-TEA analysis ===")
    print(
        "Recycle / fresh CO2+H2 mass ratio (fsolve): "
        f"{recycle['solved_recycle_to_fresh_gas_ratio']:.4f}"
    )
    print(
        "Overall gas-conversion proxy (fsolve; not carbon utilization): "
        f"{recycle['solved_overall_gas_conversion_proxy_pct']:.4f}%"
    )
    print(f"CSV-based carbon utilization: {recycle['data_carbon_utilization_pct']:.4f}%")
    print("Elemental balances (the supplied data are reported as-is):")
    for element, result in balances.items():
        status = "PASS" if result["difference_pct"] < ELEMENT_BALANCE_TOLERANCE_PCT else "FAIL"
        print(
            f"  {element}: input {result['input_kg']:.3f} kg, output "
            f"{result['output_kg']:.3f} kg, difference {result['difference_pct']:.4f}% [{status}]"
        )
    print(
        "Break-even electricity price at 100 RMB/tCO2e carbon price: "
        f"{break_even['break_even_electricity_price_rmb_per_kwh']:.5f} RMB/kWh"
    )
    print(f"Saved results: {results_path}")
    print(f"Saved sensitivity plot: {sensitivity_path}")
    print(f"Saved process diagram: {flow_path}")


if __name__ == "__main__":
    main()
