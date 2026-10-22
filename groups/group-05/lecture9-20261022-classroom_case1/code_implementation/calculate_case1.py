"""Reproduce the case 1 green-electricity and yield sensitivity calculations."""

from __future__ import annotations

import csv
from html import escape
from pathlib import Path


OUTPUT_DIR = Path(__file__).resolve().parent

BASELINE_GWP = 636.0
GRID_ELECTRICITY_GWP = 0.55
GREEN_ELECTRICITY_GWP = 0.03
ELECTRICITY_USE = 850.0
VIRGIN_PET_GWP = 2250.0
BASELINE_LCOP = 6153.4
GRID_ELECTRICITY_PRICE = 0.65
GREEN_ELECTRICITY_PRICE = 0.70
BASELINE_YIELD = 0.80
LOW_YIELD = 0.70

GWP_ITEMS = [
    ("Bottle-brick transport", 150.0),
    ("Electricity", ELECTRICITY_USE * GREEN_ELECTRICITY_GWP),
    ("Steam", 130.0),
    ("Sodium hydroxide", 31.5),
    ("Fresh water", 0.95),
    ("Wastewater treatment", 6.05),
    ("HDPE avoided-burden credit", -150.0),
]

LCOP_ITEMS = [
    ("Feedstock", 5250.0, "feed-linked variable"),
    ("Electricity", 552.5, "feed-linked variable"),
    ("Steam", 170.0, "feed-linked variable"),
    ("Water and sodium hydroxide", 115.0, "feed-linked variable"),
    ("Solid-waste disposal", 20.3, "feed-linked variable"),
    ("Labor", 218.8, "fixed per tonne of product"),
    ("Maintenance", 52.5, "fixed per tonne of product"),
    ("Management, insurance and depreciation", 196.4, "fixed per tonne of product"),
    ("HDPE byproduct revenue", -422.1, "feed-linked variable"),
]


def make_results() -> list[dict[str, str]]:
    electricity_baseline = ELECTRICITY_USE * GRID_ELECTRICITY_GWP
    electricity_green = ELECTRICITY_USE * GREEN_ELECTRICITY_GWP
    green_gwp = BASELINE_GWP - electricity_baseline + electricity_green
    green_lcop = BASELINE_LCOP + ELECTRICITY_USE * (
        GREEN_ELECTRICITY_PRICE - GRID_ELECTRICITY_PRICE
    )
    yield_scale = BASELINE_YIELD / LOW_YIELD

    yield70_gwp_items = [(name, amount * yield_scale) for name, amount in GWP_ITEMS]
    yield70_gwp = sum(amount for _, amount in yield70_gwp_items)

    green_power_premium = ELECTRICITY_USE * (
        GREEN_ELECTRICITY_PRICE - GRID_ELECTRICITY_PRICE
    )
    yield70_lcop_items = []
    for name, amount, cost_type in LCOP_ITEMS:
        if name == "Electricity":
            amount += green_power_premium
        if cost_type == "feed-linked variable":
            amount *= yield_scale
        yield70_lcop_items.append((name, amount))
    yield70_lcop = sum(amount for _, amount in yield70_lcop_items)

    assert abs(sum([20, 25, 35, 5, 40, 75, 800]) - 1000) < 1e-9
    assert abs(sum(amount for _, amount in GWP_ITEMS) - green_gwp) < 1e-9
    assert abs(sum(amount for _, amount, _ in LCOP_ITEMS) - BASELINE_LCOP) < 1e-9

    rows: list[dict[str, str]] = []

    def add(name: str, value: float, unit: str, formula: str) -> None:
        rows.append(
            {
                "metric": name,
                "value": f"{value:.4f}",
                "unit": unit,
                "formula_or_assumption": formula,
            }
        )

    add("Baseline electricity emissions", electricity_baseline, "kg CO2e/t", "850 kWh/t * 0.55 kg CO2e/kWh")
    add("Green electricity emissions", electricity_green, "kg CO2e/t", "850 kWh/t * 0.03 kg CO2e/kWh")
    add("Green-scenario net GWP", green_gwp, "kg CO2e/t", "636 - 467.5 + 25.5")
    add(
        "Green-scenario reduction vs virgin PET",
        (VIRGIN_PET_GWP - green_gwp) / VIRGIN_PET_GWP * 100,
        "%",
        "(2250 - green-scenario net GWP) / 2250 * 100",
    )
    add("Green electricity cost increase", ELECTRICITY_USE * (GREEN_ELECTRICITY_PRICE - GRID_ELECTRICITY_PRICE), "CNY/t", "850 kWh/t * (0.70 - 0.65) CNY/kWh")
    add("Green-scenario LCOP", green_lcop, "CNY/t", "6153.4 + 850 * (0.70 - 0.65)")
    add("Green-scenario LCOP increase", green_lcop - BASELINE_LCOP, "CNY/t", "Green-scenario LCOP - 6153.4")
    add("Green-scenario LCOP increase rate", (green_lcop - BASELINE_LCOP) / BASELINE_LCOP * 100, "%", "(green-scenario LCOP - 6153.4) / 6153.4 * 100")
    add("Feedstock required at 80% yield", 1 / BASELINE_YIELD, "t/t product", "1 / 0.80")
    add("Feedstock required at 70% yield", 1 / LOW_YIELD, "t/t product", "1 / 0.70")
    add("Feed-linked activity scale at 70% yield", yield_scale, "ratio", "(1 / 0.70) / (1 / 0.80)")
    add("70%-yield green-scenario net GWP", yield70_gwp, "kg CO2e/t", "All listed LCA inventory items, including HDPE credit, scale by 8/7")
    add("70%-yield green-electricity LCOP sensitivity", yield70_lcop, "CNY/t", "Green electricity at 0.70 CNY/kWh; feed-linked variable items scale by 8/7; fixed per-tonne costs unchanged")
    add("70%-yield LCOP change vs green-scenario LCOP", yield70_lcop - green_lcop, "CNY/t", "70%-yield LCOP sensitivity - green-scenario LCOP")
    add("70%-yield LCOP change rate vs green-scenario LCOP", (yield70_lcop - green_lcop) / green_lcop * 100, "%", "(70%-yield LCOP sensitivity - green-scenario LCOP) / green-scenario LCOP * 100")
    for name, amount in GWP_ITEMS:
        add(f"Green-scenario GWP item: {name}", amount, "kg CO2e/t", "Case handout inventory; electricity uses green factor")
    for name, amount in yield70_gwp_items:
        add(f"70%-yield GWP item: {name}", amount, "kg CO2e/t", "Green-scenario GWP item * 8/7")
    for name, amount in yield70_lcop_items:
        assumption = (
            "Green electricity at 0.70 CNY/kWh, then scaled by 8/7"
            if name == "Electricity"
            else "Baseline item * 8/7 for feed-linked items; otherwise unchanged"
        )
        add(f"70%-yield green-electricity LCOP item: {name}", amount, "CNY/t", assumption)
    return rows


def svg_text(x: int, y: int, value: str, *, size: int = 17, weight: str = "normal") -> str:
    return (
        f'<text x="{x}" y="{y}" text-anchor="middle" font-size="{size}" '
        f'font-weight="{weight}">{escape(value)}</text>'
    )


def make_process_diagram() -> str:
    stages = [
        (210, "1. 脱包、筛选", "与干式脱标"),
        (410, "2. 湿式粉碎", "与热碱洗"),
        (610, "3. 密度浮选", "分离槽"),
        (810, "4. 光学色选", "脱水与干燥"),
        (1010, "5. 挤出造粒", "与 SSP 增粘"),
    ]
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1450" height="650" viewBox="0 0 1450 650">',
        '<defs><marker id="arrow" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto"><path d="M0,0 L10,4 L0,8 Z" fill="#334155"/></marker></defs>',
        '<rect width="1450" height="650" fill="#ffffff"/>',
        '<g font-family="Arial, Microsoft YaHei, sans-serif" fill="#14213d">',
        svg_text(725, 44, "废弃 PET 瓶砖机械物理再生物质流程（基准批次：1,000 kg）", size=25, weight="bold"),
    ]

    def box(x: int, y: int, width: int, height: int, lines: tuple[str, ...], fill: str, stroke: str = "#2563eb") -> None:
        parts.append(
            f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="12" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
        )
        for index, line in enumerate(lines):
            parts.append(svg_text(x + width // 2, y + 35 + 25 * index, line, size=16, weight="bold" if index == 0 else "normal"))

    box(20, 190, 140, 90, ("废瓶砖", "1,000 kg"), "#e0f2fe")
    for x, first, second in stages:
        box(x, 190, 160, 90, (first, second), "#eff6ff")
    box(1250, 190, 170, 90, ("瓶级 rPET", "800 kg"), "#dcfce7", "#16a34a")

    main_links = [
        (160, 190, 210, "1,000 kg"),
        (370, 190, 410, "955 kg"),
        (570, 190, 610, "920 kg"),
        (770, 190, 810, "840 kg"),
        (970, 190, 1010, "800 kg"),
        (1170, 190, 1250, "800 kg"),
    ]
    for x1, y, x2, label in main_links:
        parts.append(f'<path d="M{x1} {y + 45} H{x2 - 5}" fill="none" stroke="#334155" stroke-width="3" marker-end="url(#arrow)"/>')
        parts.append(svg_text((x1 + x2) // 2, y + 27, label, size=14, weight="bold"))

    waste_boxes = [
        (205, ("废标签膜 20 kg", "泥沙与干灰 25 kg")),
        (405, ("洗涤杂质 35 kg", "进入污水处理")),
        (605, ("HDPE 产品 75 kg", "夹带损失 5 kg")),
        (805, ("黄变片与细粉", "损失 40 kg")),
    ]
    for x, labels in waste_boxes:
        parts.append(f'<path d="M{x + 80} 280 V360" fill="none" stroke="#64748b" stroke-width="2" marker-end="url(#arrow)"/>')
        box(x, 365, 160, 76, labels, "#fff7ed", "#ea580c")

    parts.extend(
        [
            '<rect x="70" y="485" width="1310" height="98" rx="12" fill="#f8fafc" stroke="#cbd5e1"/>',
            svg_text(725, 519, "质量平衡：输入 1,000 kg = 标签 20 + 泥沙 25 + 洗涤杂质 35 + HDPE 夹带 5 + 色选损失 40 + HDPE 产品 75 + rPET 800 kg", size=15),
            svg_text(725, 550, "主产品收率 = 800 / 1,000 = 80.0%；图中物流质量按讲义 MFA 基准值标注。", size=15),
            "</g></svg>",
        ]
    )
    return "\n".join(parts)


def main() -> None:
    results_path = OUTPUT_DIR / "calculation_results.csv"
    with results_path.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=["metric", "value", "unit", "formula_or_assumption"],
        )
        writer.writeheader()
        writer.writerows(make_results())

    diagram_path = OUTPUT_DIR / "process_flow_diagram.svg"
    diagram_path.write_text(make_process_diagram(), encoding="utf-8")
    print(f"Wrote {results_path.name} and {diagram_path.name}")


if __name__ == "__main__":
    main()
