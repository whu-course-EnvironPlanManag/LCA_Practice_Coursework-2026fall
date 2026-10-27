# -*- coding: utf-8 -*-
"""
案例二（任务 2）：LCA 绿电悖论 + TEA 平准化甲醇成本（LCOM）多情景敏感性分析
==============================================================================
读取 lca_grid_scenarios_lci.csv 与 tea_lcom_sensitivity_data.csv，
核算情景 A（100% 绿电）与情景 B（区域电网）的净碳足迹，
并在电价 0.05~0.60 元/kWh 区间内绘制 LCOM、绿色溢价与边际减排成本（MAC）的联动折线图，
输出全国碳市场（100 元/吨）背景下实现商业自平衡的最高临界电价。
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "case_files" / "data_cohort"
LCA_CSV = DATA_DIR / "lca_grid_scenarios_lci.csv"
TEA_CSV = DATA_DIR / "tea_lcom_sensitivity_data.csv"
OUT_PNG = Path(__file__).resolve().parent / "lcom_mac_sensitivity.png"

# 中文字体（Windows）
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

FOSSIL_GWP = 2600.0          # 煤制甲醇基准 (kg CO2e/t)
FOSSIL_PRICE = 2500.0        # 煤制甲醇售价 (元/t)
CARBON_PRICE = 100.0         # 全国碳市场碳价 (元/t CO2e)


def lca_summary() -> dict:
    lci = pd.read_csv(LCA_CSV)
    net = lci.loc[lci["lci_inventory_item"] == "Net_Life_Cycle_GWP_Total"].iloc[0]
    gwp_a = float(net["gwp_scenario_a_kgCO2e"])
    gwp_b = float(net["gwp_scenario_b_kgCO2e"])
    return {
        "gwp_a": gwp_a, "gwp_b": gwp_b,
        "reduction_a": (FOSSIL_GWP - gwp_a) / FOSSIL_GWP * 100,
        "reduction_b": (FOSSIL_GWP - gwp_b) / FOSSIL_GWP * 100,
        "delta_ghg": (FOSSIL_GWP - gwp_a) / 1000.0,   # = 3.644 t CO2e/t（kg -> t 换算）
    }


def tea_model() -> dict:
    """拟合 LCOM 线性模型：LCOM = 电耗强度 x 电价 + 非电成本。"""
    tea = pd.read_csv(TEA_CSV)
    p = tea["electricity_price_rmb_per_kwh"].to_numpy()
    lcom = tea["lcom_rmb_per_t"].to_numpy()
    non_elec = float(tea["non_electricity_cost_rmb_per_t"].iloc[0])

    # 由 CSV 反推电耗强度（应为 10826 kWh/t）
    elec_cost = tea["electricity_cost_rmb_per_t"].to_numpy()
    slope = float(elec_cost[0] / p[0])

    # 最小二乘校验
    k, b = np.polyfit(p, lcom, 1)
    return {"slope": slope, "non_elec": non_elec, "fit_k": k, "fit_b": b, "price": p, "lcom": lcom}


def critical_price(delta_ghg: float) -> float:
    """MAC = (LCOM - 2500)/ΔGHG = CARBON_PRICE 时的临界电价。"""
    tea = pd.read_csv(TEA_CSV)
    k = float(tea["electricity_cost_rmb_per_t"].iloc[0] / tea["electricity_price_rmb_per_kwh"].iloc[0])
    b = float(tea["non_electricity_cost_rmb_per_t"].iloc[0])
    # k*p + b - 2500 = mac_target * delta_ghg
    return (CARBON_PRICE * delta_ghg - b + FOSSIL_PRICE) / k


def plot_sensitivity(delta_ghg: float, k: float, b: float) -> None:
    p = np.linspace(0.05, 0.60, 200)
    lcom = k * p + b
    premium = lcom - FOSSIL_PRICE
    mac = premium / delta_ghg
    p_star = critical_price(delta_ghg)
    lcom_star = k * p_star + b

    fig, ax1 = plt.subplots(figsize=(11, 6.5), dpi=120)

    ax1.plot(p, lcom, color="#c0392b", lw=2.2, label="LCOM 平准化甲醇成本")
    ax1.axhline(FOSSIL_PRICE, color="#7f8c8d", ls="--", lw=1.2,
                label=f"煤制甲醇基准价 {FOSSIL_PRICE:.0f} 元/t")
    ax1.fill_between(p, FOSSIL_PRICE, lcom, where=(lcom > FOSSIL_PRICE),
                     color="#c0392b", alpha=0.08, label="绿色溢价区间")
    ax1.set_xlabel("电价（元/kWh）")
    ax1.set_ylabel("成本 / 溢价（元/t）", color="#c0392b")
    ax1.tick_params(axis="y", labelcolor="#c0392b")
    ax1.grid(alpha=0.25)

    ax2 = ax1.twinx()
    ax2.plot(p, mac, color="#2471a3", lw=2.2, label="MAC 边际减排成本")
    ax2.axhline(CARBON_PRICE, color="#1e8449", ls="--", lw=1.2,
                label=f"全国碳市场碳价 {CARBON_PRICE:.0f} 元/t CO2e")
    ax2.axvline(p_star, color="#1e8449", ls=":", lw=1.4)
    ax2.set_ylabel("MAC（元/t CO2e 避免）", color="#2471a3")
    ax2.tick_params(axis="y", labelcolor="#2471a3")

    ax1.scatter([p_star], [lcom_star], color="#1e8449", zorder=5, s=60)
    ax1.annotate(f"临界电价 ≈ {p_star:.2f} 元/kWh\n(LCOM={lcom_star:.0f} 元/t)",
                 xy=(p_star, lcom_star), xytext=(p_star + 0.12, lcom_star + 800),
                 fontsize=10, color="#1e8449",
                 arrowprops=dict(arrowstyle="->", color="#1e8449"))

    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=9, framealpha=0.9)

    ax1.set_title("绿色甲醇 LCOM / 绿色溢价 / MAC 对电价的联动响应", fontsize=14)
    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=300)
    plt.close(fig)


def main() -> None:
    lca = lca_summary()
    tm = tea_model()
    delta_ghg = lca["delta_ghg"]
    p_star = critical_price(delta_ghg)
    plot_sensitivity(delta_ghg, tm["slope"], tm["non_elec"])

    print("=" * 64)
    print("案例二 任务2：LCA 绿电悖论 + TEA 电价敏感性")
    print("=" * 64)
    print("\n【1】绿电悖论（情景 A vs B 净碳足迹）")
    print(f"  情景A 100%绿电  GWP = {lca['gwp_a']:+.1f} kgCO2e/t  (减排 {lca['reduction_a']:.1f}%)")
    print(f"  情景B 区域电网  GWP = {lca['gwp_b']:+.1f} kgCO2e/t  (增排 {abs(lca['reduction_b']):.1f}%)")
    print(f"  煤制甲醇基准 = {FOSSIL_GWP:.0f} kgCO2e/t；ΔGHG(绿电) = {delta_ghg:.3f} t CO2e/t")

    print("\n【2】LCOM 线性模型校验")
    print(f"  电耗强度 k = {tm['slope']:.1f} kWh/t（应≈10826）")
    print(f"  非电成本 b = {tm['non_elec']:.2f} 元/t")
    print(f"  最小二乘: LCOM = {tm['fit_k']:.2f}·p + {tm['fit_b']:.2f}")

    print("\n【3】关键电价对照")
    for pr in (0.15, 0.35, 0.55):
        L = tm["slope"] * pr + tm["non_elec"]
        mac = (L - FOSSIL_PRICE) / delta_ghg
        print(f"  电价 {pr:.2f}: LCOM={L:8.1f} 元/t, 绿色溢价={L-FOSSIL_PRICE:8.1f} 元/t, MAC={mac:7.1f} 元/tCO2e")

    print("\n【4】商业自平衡临界电价（MAC=100 元/t CO2e）")
    print(f"  p* = {p_star:.4f} 元/kWh  (对应 LCOM = {tm['slope']*p_star + tm['non_elec']:.1f} 元/t)")
    print(f"  结论：仅当电价降至约 {p_star:.2f} 元/度的大基地消纳场景，绿色甲醇才能依托国内碳市场实现自平衡。")
    print("-" * 64)
    print(f"折线图已保存：{OUT_PNG}")


if __name__ == "__main__":
    main()