"""Indicative process split using the A-data chemistry mix and cited LFP margins."""

from __future__ import annotations

import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = PROJECT_ROOT / "data_cohort" / "B_process_allocation.csv"

TOTAL_INTAKE_T = 20_000.0
CASCADE_SHARE = 0.20
LFP_SHARE = 0.60
NMC_SHARE = 0.40
BASELINE_DIRECT_SHARE_OF_LFP = 0.50
DIRECT_NET_USD_PER_KG = (1.30, 1.32)
HYDRO_NET_USD_PER_KG = (-2.05, -2.00)


def lfp_value_usd(direct_t: float, hydro_t: float) -> tuple[float, float]:
    direct_kg = direct_t * 1000
    hydro_kg = hydro_t * 1000
    low = direct_kg * DIRECT_NET_USD_PER_KG[0] + hydro_kg * HYDRO_NET_USD_PER_KG[0]
    high = direct_kg * DIRECT_NET_USD_PER_KG[1] + hydro_kg * HYDRO_NET_USD_PER_KG[1]
    return low, high


def main() -> None:
    recycling_t = TOTAL_INTAKE_T * (1 - CASCADE_SHARE)
    lfp_t = recycling_t * LFP_SHARE
    nmc_t = recycling_t * NMC_SHARE

    baseline_direct_t = lfp_t * BASELINE_DIRECT_SHARE_OF_LFP
    baseline_hydro_t = lfp_t - baseline_direct_t
    optimized_direct_t = lfp_t
    optimized_hydro_t = 0.0

    baseline_low, baseline_high = lfp_value_usd(baseline_direct_t, baseline_hydro_t)
    optimized_low, optimized_high = lfp_value_usd(optimized_direct_t, optimized_hydro_t)
    gain_low = optimized_low - baseline_high
    gain_high = optimized_high - baseline_low

    rows = [
        {
            "scenario": "A_baseline_50_50_LFP_split",
            "nmc_pyro_hydro_share_of_recycling_feed_percent": 100 * nmc_t / recycling_t,
            "lfp_direct_share_of_recycling_feed_percent": 100 * baseline_direct_t / recycling_t,
            "lfp_hydromet_share_of_recycling_feed_percent": 100 * baseline_hydro_t / recycling_t,
            "nmc_battery_equivalent_t_per_year": nmc_t,
            "lfp_direct_battery_equivalent_t_per_year": baseline_direct_t,
            "lfp_hydromet_battery_equivalent_t_per_year": baseline_hydro_t,
            "lfp_net_value_low_usd_per_year": baseline_low,
            "lfp_net_value_high_usd_per_year": baseline_high,
            "increment_vs_baseline_low_usd_per_year": 0.0,
            "increment_vs_baseline_high_usd_per_year": 0.0,
        },
        {
            "scenario": "economic_only_all_LFP_direct",
            "nmc_pyro_hydro_share_of_recycling_feed_percent": 100 * nmc_t / recycling_t,
            "lfp_direct_share_of_recycling_feed_percent": 100 * optimized_direct_t / recycling_t,
            "lfp_hydromet_share_of_recycling_feed_percent": 100 * optimized_hydro_t / recycling_t,
            "nmc_battery_equivalent_t_per_year": nmc_t,
            "lfp_direct_battery_equivalent_t_per_year": optimized_direct_t,
            "lfp_hydromet_battery_equivalent_t_per_year": optimized_hydro_t,
            "lfp_net_value_low_usd_per_year": optimized_low,
            "lfp_net_value_high_usd_per_year": optimized_high,
            "increment_vs_baseline_low_usd_per_year": gain_low,
            "increment_vs_baseline_high_usd_per_year": gain_high,
        },
    ]

    with OUTPUT.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"Recycling feed: {recycling_t:,.0f} t/a")
    print(f"NMC battery-equivalent feed: {nmc_t:,.0f} t/a")
    print(f"LFP battery-equivalent feed: {lfp_t:,.0f} t/a")
    print(f"Economic-only route split: 40:60:0 (NMC pyro-hydro:LFP direct:LFP hydromet)")
    print(f"Baseline LFP value: ${baseline_low:,.0f} to ${baseline_high:,.0f} per year")
    print(f"All-direct LFP value: ${optimized_low:,.0f} to ${optimized_high:,.0f} per year")
    print(f"Indicative gain vs baseline: ${gain_low:,.0f} to ${gain_high:,.0f} per year")
    print(f"CSV: {OUTPUT}")


if __name__ == "__main__":
    main()