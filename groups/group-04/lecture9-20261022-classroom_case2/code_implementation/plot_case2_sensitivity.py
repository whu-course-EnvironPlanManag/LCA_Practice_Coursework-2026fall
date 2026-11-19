#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""案例二 任务 2：电价—LCOM—绿色溢价—MAC 联动敏感性图。

读取 ../case_files/data_cohort/tea_lcom_sensitivity_data.csv，
输出 case2_sensitivity.png（300 dpi）与 case2_sensitivity.svg。
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "case_files" / "data_cohort" / "tea_lcom_sensitivity_data.csv"

FOSSIL_PRICE = 2500.0
DELTA_GHG_T = 3.64412          # t CO2e / t 甲醇，来自 LCA 情景 A
CARBON_PRICE = 100.0
COLOR = {"ink": "#1F2937", "muted": "#6B7280", "blue": "#2563EB",
         "green": "#059669", "red": "#DC2626", "amber": "#D97706", "grid": "#E5E7EB"}


def main() -> None:
    df = pd.read_csv(DATA)
    price = df["electricity_price_rmb_per_kwh"]
    lcom = df["electricity_cost_rmb_per_t"] + df["non_electricity_cost_rmb_per_t"]
    premium = lcom - FOSSIL_PRICE
    mac = premium / DELTA_GHG_T

    non_elec = float(df["non_electricity_cost_rmb_per_t"].iloc[0])
    kwh = float(df["electricity_cost_rmb_per_t"].iloc[0] / price.iloc[0])
    p_be = (FOSSIL_PRICE + CARBON_PRICE * DELTA_GHG_T - non_elec) / kwh
    p_plain = (FOSSIL_PRICE - non_elec) / kwh

    fig, axes = plt.subplots(3, 1, figsize=(8.2, 9.6), sharex=True,
                             gridspec_kw={"height_ratios": [1.15, 1.0, 1.0]})
    fig.patch.set_facecolor("white")

    # ---- 面板 1：LCOM ----
    ax = axes[0]
    ax.plot(price, lcom, color=COLOR["blue"], lw=2.4, marker="o", ms=4.5, label="LCOM")
    ax.axhline(FOSSIL_PRICE, color=COLOR["muted"], ls="--", lw=1.3, label="煤制甲醇 2 500 元/t")
    ax.axvline(p_be, color=COLOR["green"], ls=":", lw=1.4)
    ax.fill_between(price, lcom, FOSSIL_PRICE, where=(lcom < FOSSIL_PRICE),
                    color=COLOR["green"], alpha=0.10)
    ax.annotate(f"碳价 100 元/t 自平衡\n临界电价 {p_be:.3f} 元/kWh",
                xy=(p_be, FOSSIL_PRICE + CARBON_PRICE * DELTA_GHG_T),
                xytext=(p_be + 0.055, 4600), fontsize=9, color=COLOR["green"],
                arrowprops=dict(arrowstyle="->", color=COLOR["green"], lw=1.1))
    for x, label in ((0.15, "大基地 0.15"), (0.35, "沿海绿电 0.35")):
        y = float(lcom[price == x].iloc[0])
        ax.scatter([x], [y], s=55, color=COLOR["blue"], zorder=5)
        ax.annotate(f"{label}\n{y:,.0f} 元/t", xy=(x, y), xytext=(x + 0.015, y - 620),
                    fontsize=8.8, color=COLOR["blue"])
    ax.set_ylabel("平准化甲醇成本 LCOM（元/t）", fontsize=10.5)
    ax.set_title("电价对绿色甲醇成本、绿色溢价与边际减排成本的联动影响",
                 fontsize=14, weight="bold", color=COLOR["ink"], pad=12)
    ax.legend(loc="upper left", frameon=False, fontsize=9)
    ax.grid(axis="y", color=COLOR["grid"], lw=0.8)
    ax.set_axisbelow(True)

    # ---- 面板 2：绿色溢价 ----
    ax = axes[1]
    ax.plot(price, premium, color=COLOR["amber"], lw=2.4, marker="o", ms=4.5)
    ax.axhline(0, color=COLOR["muted"], lw=1.1)
    ax.fill_between(price, premium, 0, where=(premium > 0), color=COLOR["red"], alpha=0.12,
                    label="成本倒挂区")
    ax.fill_between(price, premium, 0, where=(premium <= 0), color=COLOR["green"], alpha=0.16,
                    label="商业平价区")
    ax.annotate(f"无碳收益平价点\n{p_plain:.3f} 元/kWh", xy=(p_plain, 0),
                xytext=(p_plain + 0.045, -900), fontsize=9, color=COLOR["green"],
                arrowprops=dict(arrowstyle="->", color=COLOR["green"], lw=1.1))
    ax.set_ylabel("绿色溢价（元/t）", fontsize=10.5)
    ax.legend(loc="upper left", frameon=False, fontsize=9)
    ax.grid(axis="y", color=COLOR["grid"], lw=0.8)
    ax.set_axisbelow(True)

    # ---- 面板 3：MAC ----
    ax = axes[2]
    ax.plot(price, mac, color=COLOR["red"], lw=2.4, marker="o", ms=4.5)
    ax.axhline(CARBON_PRICE, color=COLOR["green"], ls="--", lw=1.3,
               label=f"全国碳价 ≈ {CARBON_PRICE:.0f} 元/t CO2e")
    ax.axvline(p_be, color=COLOR["green"], ls=":", lw=1.4)
    ax.scatter([0.55], [float(mac[price == 0.55].iloc[0])], s=70, marker="X",
               color=COLOR["ink"], zorder=5)
    ax.annotate("0.55 元电网情景：\nGWP 为 +4 531，MAC 已失去减排意义",
                xy=(0.55, float(mac[price == 0.55].iloc[0])),
                xytext=(0.33, 1420), fontsize=8.6, color=COLOR["ink"],
                arrowprops=dict(arrowstyle="->", color=COLOR["ink"], lw=1.0))
    ax.set_xlabel("工业电价（元/kWh）", fontsize=10.5)
    ax.set_ylabel("边际减排成本 MAC\n（元/t CO2e）", fontsize=10.5)
    ax.legend(loc="upper left", frameon=False, fontsize=9)
    ax.grid(axis="y", color=COLOR["grid"], lw=0.8)
    ax.set_axisbelow(True)
    ax.set_xlim(0.03, 0.62)

    fig.text(0.012, 0.012,
             "数据：tea_lcom_sensitivity_data.csv  |  功能单位：1 t 精甲醇  |  "
             "ΔGHG = 3.644 t CO2e/t（情景 A 相对煤制甲醇）",
             fontsize=8, color=COLOR["muted"])

    fig.tight_layout(rect=(0, 0.028, 1, 1))
    for suffix, dpi in (("png", 300), ("svg", None)):
        fig.savefig(HERE / f"case2_sensitivity.{suffix}", dpi=dpi,
                    facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print("已输出 case2_sensitivity.png / case2_sensitivity.svg")


if __name__ == "__main__":
    main()
