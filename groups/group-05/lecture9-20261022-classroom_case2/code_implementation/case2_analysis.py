"""Reproduce the MFA-LCA-TEA calculations and figures for classroom case 2.

Uses only the Python standard library. Run from any directory with:
    python case2_analysis.py
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List


HERE = Path(__file__).resolve().parent
CASE_ROOT = HERE.parent
DATA_DIR = CASE_ROOT / "case_files" / "data_cohort"
MFA_FILE = DATA_DIR / "mfa_reaction_recycle_balance.csv"
LCA_FILE = DATA_DIR / "lca_grid_scenarios_lci.csv"
TEA_FILE = DATA_DIR / "tea_lcom_sensitivity_data.csv"

CO2_C_FRACTION = 12.0 / 44.01
MEOH_C_FRACTION = 12.0 / 32.04
COAL_GWP_KG_PER_T = 2600.0
GREEN_GWP_KG_PER_T = -1044.12
AVOIDED_TCO2E_PER_T_PRODUCT = (
    COAL_GWP_KG_PER_T - GREEN_GWP_KG_PER_T
) / 1000.0


def load_rows(path: Path) -> List[Dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def by_name(rows: List[Dict[str, str]], column: str, name: str) -> Dict[str, str]:
    return next(row for row in rows if row[column] == name)


def write_sensitivity_chart(rows: List[Dict[str, str]], path: Path) -> None:
    width, height = 1000, 900
    left, right = 100, 930
    plot_width = right - left
    panels = [
        ("LCOM (RMB/t product)", "lcom_rmb_per_t", 0, 8000, "#1565c0"),
        ("Green premium (RMB/t product)", "green_premium_rmb_per_t", -1000, 5500, "#2e7d32"),
        ("MAC (RMB/tCO2e)", "mac_rmb_per_tCO2e", -250, 1500, "#c62828"),
    ]
    prices = [float(row["electricity_price_rmb_per_kwh"]) for row in rows]
    panel_top = [80, 355, 630]
    panel_height = 190
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>text{font-family:Arial,sans-serif;fill:#263238}.axis{stroke:#455a64;'
        'stroke-width:1}.grid{stroke:#dfe5e8;stroke-width:1}</style>',
        '<text x="500" y="35" text-anchor="middle" font-size="22" font-weight="bold">'
        'Electricity-price sensitivity</text>',
    ]
    x_min, x_max = min(prices), max(prices)
    for index, (title, column, y_min, y_max, color) in enumerate(panels):
        top = panel_top[index]
        bottom = top + panel_height
        parts.append(
            f'<text x="{left}" y="{top - 15}" font-size="16" font-weight="bold">{title}</text>'
        )
        for tick_index in range(5):
            value = y_min + (y_max - y_min) * tick_index / 4
            y = bottom - panel_height * tick_index / 4
            parts.append(f'<line class="grid" x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}"/>')
            parts.append(
                f'<text x="{left - 10}" y="{y + 4:.1f}" text-anchor="end" font-size="12">'
                f'{value:,.0f}</text>'
            )
        parts.append(f'<line class="axis" x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}"/>')
        parts.append(f'<line class="axis" x1="{left}" y1="{top}" x2="{left}" y2="{bottom}"/>')
        coordinates = []
        for row in rows:
            price = float(row["electricity_price_rmb_per_kwh"])
            value = float(row[column])
            x = left + (price - x_min) / (x_max - x_min) * plot_width
            y = bottom - (value - y_min) / (y_max - y_min) * panel_height
            coordinates.append(f"{x:.1f},{y:.1f}")
        parts.append(
            f'<polyline points="{" ".join(coordinates)}" fill="none" stroke="{color}" '
            'stroke-width="3"/>'
        )
        for price in (0.05, 0.15, 0.35, 0.60):
            x = left + (price - x_min) / (x_max - x_min) * plot_width
            parts.append(f'<line class="axis" x1="{x:.1f}" y1="{bottom}" x2="{x:.1f}" y2="{bottom + 5}"/>')
            parts.append(
                f'<text x="{x:.1f}" y="{bottom + 20}" text-anchor="middle" font-size="12">'
                f'{price:.2f}</text>'
            )
    parts.extend(
        [
            '<text x="515" y="890" text-anchor="middle" font-size="14">'
            'Electricity price (RMB/kWh)</text>',
            "</svg>",
        ]
    )
    path.write_text("\n".join(parts), encoding="utf-8")


def write_process_diagram(path: Path) -> None:
    svg = """<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="660" viewBox="0 0 1200 660">
<defs><marker id="arrow" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto">
<path d="M0,0 L10,4 L0,8 Z" fill="#37474f"/></marker></defs>
<rect width="100%" height="100%" fill="white"/>
<style>
text{font-family:Arial,sans-serif;fill:#18313b}.box{fill:#e8f1f5;stroke:#35616f;stroke-width:2}
.unit{font-size:16px;font-weight:bold}.flow{fill:none;stroke:#37474f;stroke-width:2.5;marker-end:url(#arrow)}
.recycle{fill:none;stroke:#1565c0;stroke-width:3;marker-end:url(#arrow)}
.purge{fill:none;stroke:#c62828;stroke-width:2.5;marker-end:url(#arrow)}
.label{font-size:14px}.title{font-size:23px;font-weight:bold}
</style>
<text x="600" y="36" text-anchor="middle" class="title">Power-to-Methanol process and recycle loop (per tonne product)</text>
<rect class="box" x="55" y="150" width="190" height="100" rx="8"/>
<text x="150" y="185" text-anchor="middle" class="unit">Fresh feed</text>
<text x="150" y="211" text-anchor="middle" class="label">CO2 1,423 kg + H2 198 kg</text>
<rect class="box" x="340" y="150" width="190" height="100" rx="8"/>
<text x="435" y="185" text-anchor="middle" class="unit">Mixer / heater</text>
<text x="435" y="211" text-anchor="middle" class="label">Reactor inlet 6,261 kg</text>
<rect class="box" x="625" y="150" width="190" height="100" rx="8"/>
<text x="720" y="185" text-anchor="middle" class="unit">Reactor</text>
<text x="720" y="211" text-anchor="middle" class="label">Single-pass conversion 25%</text>
<rect class="box" x="905" y="150" width="220" height="100" rx="8"/>
<text x="1015" y="185" text-anchor="middle" class="unit">Cooler / separator</text>
<text x="1015" y="211" text-anchor="middle" class="label">Off-gas 4,686 kg</text>
<path class="flow" d="M245 200 H340"/><path class="flow" d="M530 200 H625"/>
<path class="flow" d="M815 200 H905"/>
<path class="flow" d="M1015 250 V360 H905"/>
<rect class="box" x="700" y="320" width="205" height="90" rx="8"/>
<text x="802" y="353" text-anchor="middle" class="unit">Distillation</text>
<text x="802" y="380" text-anchor="middle" class="label">Crude liquid 1,575 kg</text>
<path class="flow" d="M905 365 H700"/>
<path class="flow" d="M700 390 H560 V485"/>
<rect class="box" x="420" y="485" width="280" height="90" rx="8"/>
<text x="560" y="520" text-anchor="middle" class="unit">Products / coproducts</text>
<text x="560" y="547" text-anchor="middle" class="label">Methanol 1,000 kg; water 575 kg recycled</text>
<rect class="box" x="305" y="320" width="180" height="90" rx="8"/>
<text x="395" y="353" text-anchor="middle" class="unit">Gas splitter</text>
<text x="395" y="380" text-anchor="middle" class="label">99% recycle / 1% purge*</text>
<path class="flow" d="M1015 250 V290 H395 V320"/>
<path class="recycle" d="M305 365 H270 V90 H435 V150"/>
<text x="350" y="78" text-anchor="middle" class="label" fill="#1565c0">Recycle gas 4,640 kg</text>
<path class="purge" d="M395 410 V485"/>
<text x="305" y="458" text-anchor="middle" class="label" fill="#c62828">Purge 46 kg</text>
<text x="58" y="625" class="label">* CSV flow values imply 46 / 4,686 = 0.98% purge. The source documentation's 3.8:1 recycle ratio is not consistent with these stream totals.</text>
</svg>"""
    path.write_text(svg, encoding="utf-8")


def create_report(
    mfa_rows: List[Dict[str, str]],
    lca_rows: List[Dict[str, str]],
    tea_rows: List[Dict[str, str]],
) -> str:
    streams = {row["stream_id"]: row for row in mfa_rows}
    co2_kg = float(streams["S01"]["mass_flow_per_ton_product_kg"])
    h2_kg = float(streams["S02"]["mass_flow_per_ton_product_kg"])
    recycle_kg = float(streams["S06"]["mass_flow_per_ton_product_kg"])
    offgas_kg = float(streams["S10"]["mass_flow_per_ton_product_kg"])
    purge_kg = float(streams["S11"]["mass_flow_per_ton_product_kg"])
    meoh_kg = float(streams["S12"]["mass_flow_per_ton_product_kg"])

    single_pass = 0.25
    recycle_fraction = 0.99
    purge_fraction = 1.0 - recycle_fraction
    denominator = 1.0 - recycle_fraction * (1.0 - single_pass)
    ideal_overall = single_pass / denominator
    ideal_recycle_ratio = recycle_fraction * (1.0 - single_pass) / denominator
    observed_recycle_ratio = recycle_kg / (co2_kg + h2_kg)
    observed_purge_fraction = purge_kg / offgas_kg
    feed_carbon = co2_kg * CO2_C_FRACTION
    product_carbon = meoh_kg * MEOH_C_FRACTION
    carbon_utilization = product_carbon / feed_carbon
    purge_co2_carbon = purge_kg * 0.754 * CO2_C_FRACTION
    carbon_residual = feed_carbon - product_carbon - purge_co2_carbon

    lca_green = float(
        by_name(lca_rows, "lci_inventory_item", "Net_Life_Cycle_GWP_Total")[
            "gwp_scenario_a_kgCO2e"
        ]
    )
    lca_grid = float(
        by_name(lca_rows, "lci_inventory_item", "Net_Life_Cycle_GWP_Total")[
            "gwp_scenario_b_kgCO2e"
        ]
    )
    grid_reduction = (COAL_GWP_KG_PER_T - lca_grid) / COAL_GWP_KG_PER_T * 100
    pv_threshold = (10826.0 * 0.75 - 1423.0 - COAL_GWP_KG_PER_T) / (
        10826.0 * (0.75 - 0.04)
    )

    price_015 = by_name(tea_rows, "electricity_price_rmb_per_kwh", "0.15")
    price_035 = by_name(tea_rows, "electricity_price_rmb_per_kwh", "0.35")
    max_lcom = 2500.0 + AVOIDED_TCO2E_PER_T_PRODUCT * 100.0
    non_electric_cost = float(price_015["non_electricity_cost_rmb_per_t"])
    max_power_price = (max_lcom - non_electric_cost) / 10826.0
    pv_capacity_factor = 1200.0 / 8000.0

    return rf"""# 案例二 MFA-LCA-TEA 解答

> 计算依据：同目录 `case_files/data_cohort/` 中的 CSV。脚本会重算本报告与两张 SVG。功能单位为 1 t 聚合级甲醇。

## 结论速览

- **MFA：**基于理想完全混合循环方程，单程转化率 25%、未反应气回流率 99% 时，理想全系统转化率为 **{ideal_overall * 100:.2f}%**，循环量/新鲜 CO₂+H₂ 质量比为 **{ideal_recycle_ratio:.2f}:1**。但 CSV 观测质量流量对应比值仅 **{observed_recycle_ratio:.2f}:1**，与讲义声称的 3.8:1 不符；CSV 中甲醇碳利用率约 **{carbon_utilization * 100:.2f}%**，不能据此验证“严格 96.0%”。
- **LCA：**数据集报告绿电净足迹 **{lca_green:,.2f} kg CO₂e/t**，区域电网净足迹 **{lca_grid:,.2f} kg CO₂e/t**，后者较煤制甲醇基准低 **{grid_reduction:.1f}%**（为负值即反向增排）。课堂混供题给定 EF=0.04/0.75 时，绿电占比至少为 **{pv_threshold * 100:.2f}%** 才能不高于 2,600 kg CO₂e/t。
- **TEA：**0.35 元/kWh 时 LCOM **{float(price_035["lcom_rmb_per_t"]):,.2f} 元/t**、MAC **{float(price_035["mac_rmb_per_tCO2e"]):,.2f} 元/tCO₂e**；0.15 元/kWh 时 LCOM **{float(price_015["lcom_rmb_per_t"]):,.2f} 元/t**、MAC **{float(price_015["mac_rmb_per_tCO2e"]):,.2f} 元/tCO₂e**。按 100 元/tCO₂e 碳价，理论最高电价约 **{max_power_price:.4f} 元/kWh**。

## 一、MFA：循环回路、碳利用率与数据核验

### 1. 理想稳态循环计算

令反应器入口 CO₂ 为 \(R\)，新鲜 CO₂ 为 \(F\)，单程反应率 \(X=0.25\)，未反应气回流率 \(r=0.99\)。稳态关系为：

\\[
R=F+r(1-X)R,\\qquad R/F=1/[1-r(1-X)].
\\]

所以总体转化率（最终反应的 CO₂ / 新鲜 CO₂）为：

\\[
X_{{overall}}=X/[1-r(1-X)]={ideal_overall:.6f}={ideal_overall * 100:.2f}\\%.
\\]

回流量/新鲜 CO₂ 比为 \(r(1-X)/[1-r(1-X)]={ideal_recycle_ratio:.4f}:1\)。这说明“单程 25%”经循环可显著提高总体利用，但给定 99% 回流时理论值不是 96% 或 3.8:1。

### 2. 按 CSV 流量复算

| 指标 | CSV 复算 | 讲义/目标值 | 结论 |
|---|---:|---:|---|
| 循环气质量流量 / 新鲜 CO₂+H₂质量流量 | {recycle_kg:,.0f}/{co2_kg + h2_kg:,.0f} = **{observed_recycle_ratio:.2f}:1** | 3.8:1 | 不一致 |
| 驰放分率 | {purge_kg:,.0f}/{offgas_kg:,.0f} = **{observed_purge_fraction * 100:.3f}%** | 1.0% | 约一致（舍入） |
| 甲醇产品碳 / 新鲜 CO₂ 碳 | {product_carbon:.2f}/{feed_carbon:.2f} = **{carbon_utilization * 100:.2f}%** | 96.0% | CSV 得到约 96.55% |

按 CSV 所列驰放气 CO₂ 质量分数 75.4% 估算，进料碳减去产品碳及驰放气中已标注 CO₂ 碳后尚差 **{carbon_residual:.2f} kg C/t 产品**（约占进料碳 {carbon_residual / feed_carbon * 100:.2f}%）。CSV 未给出驰放气中 CO、烃类的完整组分，也没有足够的组分级进出口反应数据，因此无法证明 C/H/O 三元素误差小于 0.01%；不应把未闭合的结果伪装为严格守恒。数据需补齐/修订后才能完成该项作业验证。

## 二、LCA：绿电悖论与光伏临界占比

| 情景 | 净碳足迹 (kg CO₂e/t) | 相对煤制甲醇 2,600 kg CO₂e/t |
|---|---:|---:|
| 100% 绿电 | {lca_green:,.2f} | 减排 {((COAL_GWP_KG_PER_T - lca_green) / COAL_GWP_KG_PER_T * 100):.1f}% |
| 区域电网 | {lca_grid:,.2f} | {'增排' if lca_grid > COAL_GWP_KG_PER_T else '减排'} {abs((lca_grid - COAL_GWP_KG_PER_T) / COAL_GWP_KG_PER_T * 100):.1f}% |

讲义课堂混供题另给定光伏 EF=0.04、燃煤自备电 EF=0.75 kg CO₂e/kWh，并采用：

\\[
GWP(x)=10,826(0.75-0.71x)-1,423.
\\]

令 \(GWP(x)\\le2,600\)，解得 \(x\\ge{pv_threshold:.6f}\)，即光伏绿电占比至少 **{pv_threshold * 100:.2f}%**。该混供临界值采用课堂题的排放因子，不应与 LCI 表情景 A/B 的 0.035/0.550 kg CO₂e/kWh 混为同一组参数。

屋顶光伏年满发 1,200 h，而化工装置设计年运行 8,000 h，时间覆盖率只有 **{pv_capacity_factor * 100:.1f}%**。若不配储能、备用电源或扩建并网，无法满足连续工艺负荷；按固定设计产能要求折算，设备利用率降低将导致单位产量资本摊销约放大 \(8000/1200=6.67\) 倍。实际 CAPEX 影响还取决于储能、备用和扩容方案。

## 三、TEA：LCOM、绿色溢价、MAC 与碳价阈值

成本模型为 `LCOM = 电价 × 10,826 kWh/t + 1,238.37 元/t`。其中非电成本包含资本摊销、CO₂、耗材运维，并已扣除副产氧抵扣。

| 电价 (元/kWh) | LCOM (元/t) | 绿色溢价 (元/t) | MAC (元/tCO₂e) |
|---:|---:|---:|---:|
| 0.15 | {float(price_015["lcom_rmb_per_t"]):,.2f} | {float(price_015["green_premium_rmb_per_t"]):,.2f} | {float(price_015["mac_rmb_per_tCO2e"]):,.2f} |
| 0.35 | {float(price_035["lcom_rmb_per_t"]):,.2f} | {float(price_035["green_premium_rmb_per_t"]):,.2f} | {float(price_035["mac_rmb_per_tCO2e"]):,.2f} |

绿电情景相对煤制甲醇的减排量为 **{AVOIDED_TCO2E_PER_T_PRODUCT:.5f} tCO₂e/t 产品**。在 100 元/tCO₂e 的碳价下，可覆盖绿色溢价上限为 **{AVOIDED_TCO2E_PER_T_PRODUCT * 100:,.2f} 元/t**，对应 LCOM 上限 **{max_lcom:,.2f} 元/t**，所以最高电价为：

\\[
p_{{max}}=({max_lcom:,.2f}-1,238.37)/10,826={max_power_price:.5f}\\text{{ 元/kWh}}.
\\]

即约 **0.150 元/kWh**；此处采用碳价恰好覆盖全部溢价的收支平衡定义，不含融资、税收、碳信用额外性及价格波动。

## 四、规划建议与作业结论

1. 优先考虑可提供低碳、低价且稳定电力的区域/专线与储能组合；不能只凭年发电量判断能否支撑连续化装置。
2. 常规高碳电网下，电解制氢的用电排放可抵消 CO₂ 固定信用，使 CCU 甲醇出现“绿电悖论”；应先核实项目电力的小时级来源及生命周期排放因子。
3. 以给定经济和碳足迹参数计算，电价约 0.15 元/kWh 是 100 元/tCO₂e 碳价下的经济临界值，不代表所有项目都可直接投资。
4. 课程数据中的“3.8:1 回流比”“96.0% 碳利用率”和组分流量不能完全互相验证。建议先修订流股组分、反应计量和回流/驰放定义，再提交元素级严格守恒结论。

## 生成文件

- `tea_lcom_sensitivity.svg`：基于 TEA CSV 的 LCOM、绿色溢价、MAC 电价敏感性曲线。
- `process_flow.svg`：标示循环回路、驰放及精馏产品的工艺流程图。
"""


def main() -> None:
    mfa_rows = load_rows(MFA_FILE)
    lca_rows = load_rows(LCA_FILE)
    tea_rows = load_rows(TEA_FILE)
    write_sensitivity_chart(tea_rows, HERE / "tea_lcom_sensitivity.svg")
    write_process_diagram(HERE / "process_flow.svg")
    report = create_report(mfa_rows, lca_rows, tea_rows)
    (HERE / "case2_mfa_lca_tea_results.md").write_text(report, encoding="utf-8")
    print("Generated:")
    print(f"  {HERE / 'case2_mfa_lca_tea_results.md'}")
    print(f"  {HERE / 'tea_lcom_sensitivity.svg'}")
    print(f"  {HERE / 'process_flow.svg'}")


if __name__ == "__main__":
    main()
