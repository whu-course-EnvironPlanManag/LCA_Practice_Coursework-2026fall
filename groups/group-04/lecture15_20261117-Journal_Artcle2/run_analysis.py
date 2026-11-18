from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager
import plotly.graph_objects as go
import statsmodels.api as sm
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
RESULTS = ROOT / "results"
P2O5_TO_P = 0.4364
BASE_MANURE_RATE = 0.30
TARGET_MANURE_RATE = 0.75
BASE_STRUVITE_RATE = 0.05
TARGET_STRUVITE_RATE = 0.60
LIVESTOCK_PUE = 0.23
FEED_SHARE = 0.30
FOOD_SHARE = 0.52
WASTEWATER_SHARE = 0.80
CROP_HARVEST_INDEX = 0.80
BALANCE_TOLERANCE = 1e-4
NODE_LABELS_ZH = {
    "Primary phosphate mining": "磷矿开采",
    "Other supply (trade/stock estimate)": "其他供应（贸易/库存估算）",
    "Chemical industry": "磷化工",
    "Manure pool": "粪肥资源池",
    "Wastewater": "污水处理",
    "Soil legacy": "土壤遗留磷",
    "Cropland": "农田种植",
    "Crop harvest": "作物收获",
    "Livestock": "畜禽养殖",
    "Residents": "居民消费",
    "Environmental losses": "环境损失",
    "Other crop uses": "其他作物用途",
    "Human retention": "人体留存",
}
FLOW_LABELS_ZH = {
    "Primary supply": "磷矿来源",
    "Estimated supply gap": "其他供应估算",
    "Mineral fertilizer": "矿物磷肥",
    "Recycled manure": "回收粪肥",
    "Recovered struvite": "回收鸟粪石",
    "Soil legacy release": "土壤遗留磷释放",
    "Crop harvest": "作物收获磷",
    "Field loss": "田间损失",
    "Soil accumulation": "土壤磷累积",
    "Plant food": "植物性食物",
    "Feed": "饲料",
    "Other crop uses": "其他作物用途",
    "Animal products": "动物性产品",
    "Manure generated": "畜禽粪磷",
    "Unrecovered manure": "未回收粪肥损失",
    "Human retention": "人体留存",
    "Wastewater generation": "生活污水磷",
    "Unrecovered wastewater P": "未回收污水磷",
}
CATEGORY_LABELS_ZH = {
    "A": "非食用农产品",
    "B": "水果与蔬菜",
    "C": "油脂与糖类原料",
    "D": "厨房调味品",
    "E": "谷物",
    "F": "豆类",
    "G": "动物产品",
    "H": "饼粕",
    "I": "其他",
    "J": "酒类与饮料",
    "K": "饲草",
    "M": "活体动物",
}


class ACSPModel:
    """Cropland P balance using observed harvest and explicit stock terms."""

    def __init__(
        self,
        fertilizer_p: float,
        organic_fertilizer_p: float,
        recovered_wastewater_p: float,
        crop_harvest_p: float,
        field_loss_rate: float,
    ) -> None:
        self.fertilizer_p = fertilizer_p
        self.organic_fertilizer_p = organic_fertilizer_p
        self.recovered_wastewater_p = recovered_wastewater_p
        self.crop_harvest_p = crop_harvest_p
        self.field_loss_rate = field_loss_rate

    def calculate(self) -> dict[str, float]:
        field_loss_p = self.fertilizer_p * self.field_loss_rate
        crop_uptake_p = self.crop_harvest_p / CROP_HARVEST_INDEX
        crop_residue_p = crop_uptake_p - self.crop_harvest_p
        soil_delta = (
            self.fertilizer_p + self.organic_fertilizer_p
            + self.recovered_wastewater_p - self.crop_harvest_p - field_loss_p
        )
        return {
            "crop_uptake_p": crop_uptake_p,
            "crop_residue_p": crop_residue_p,
            "field_loss_p": field_loss_p,
            "soil_legacy_release_p": max(0.0, -soil_delta),
            "soil_legacy_accumulation_p": max(0.0, soil_delta),
        }


def load_population() -> tuple[pd.DataFrame, set[int]]:
    path = RAW / "7.Global population projection data for P sustainability scenario analysis.xlsx"
    estimates = pd.read_excel(path, sheet_name="Estimates", header=16)
    medium = pd.read_excel(path, sheet_name="Medium variant", header=16)
    estimates["Year"] = pd.to_numeric(estimates["Year"], errors="coerce")
    medium["Year"] = pd.to_numeric(medium["Year"], errors="coerce")
    population_column = "Total Population, as of 1 July (thousands)"
    world_name = "Region, subregion, country or area *"
    world_estimates = estimates.loc[
        estimates["Type"].eq("World"), ["Year", population_column]
    ].dropna()
    world_medium = medium.loc[
        medium["Type"].eq("World"), ["Year", population_column]
    ].dropna()
    population = pd.concat(
        [world_estimates.assign(Variant="Estimates"), world_medium.assign(Variant="Medium")],
        ignore_index=True,
    )
    country_codes = pd.to_numeric(
        estimates.loc[estimates["Type"].eq("Country/Area"), "Location code"],
        errors="coerce",
    ).dropna()
    return population, set(country_codes.astype(int))


def world_population(population: pd.DataFrame, year: int, variant: str) -> float:
    rows = population.loc[
        population["Variant"].eq(variant) & population["Year"].eq(year),
        "Total Population, as of 1 July (thousands)",
    ]
    if rows.empty:
        raise ValueError(f"World population for {year} ({variant}) is unavailable")
    return float(rows.iloc[0])


def load_crop_history() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    path = RAW / "Agricultural products_P_result_national level（1961-2022）.xlsx"
    data = pd.read_excel(path, sheet_name="product_P_result (tons)")
    year_columns = {
        int(str(column)): column for column in data.columns if str(column).isdigit()
    }
    world = data.loc[data["Country"].astype(str).str.strip().str.casefold().eq("world")]
    if world.empty:
        raise ValueError("The product-P workbook has no World aggregate rows")
    values = world.set_index("Product")[list(year_columns.values())].apply(
        pd.to_numeric, errors="coerce"
    )
    values.columns = list(year_columns)
    values = values.groupby(level=0).sum(min_count=1)
    history = values.sum(axis=0, min_count=1).rename("Crop harvest P (tons)").reset_index()
    history = history.rename(columns={"index": "Year"}).sort_values("Year")

    coefficient_path = RAW / "3.P content coefficient of products_Production.xlsx"
    coefficients = pd.read_excel(coefficient_path, sheet_name=0)
    category_map: dict[str, str] = {}
    if coefficients.shape[1] >= 6:
        category_map = {
            str(code).strip(): str(label).strip()
            for code, label in zip(coefficients.iloc[:, 4], coefficients.iloc[:, 5])
            if pd.notna(code) and pd.notna(label)
        }
    category_values = values.rename_axis("Product").reset_index().melt(
        id_vars="Product", var_name="Year", value_name="Crop harvest P (tons)"
    )
    category_values["Product category"] = category_values["Product"].astype(str).map(
        lambda code: category_map.get(code, code)
    )
    return history, category_values, coefficients


def load_fertilizer(population: pd.DataFrame, country_codes: set[int]) -> tuple[int, float]:
    path = RAW / "Nutrient phosphate P2O5 use data at the national level.csv"
    data = pd.read_csv(path, encoding="latin1", low_memory=False)
    data["Year"] = pd.to_numeric(data["Year"], errors="coerce")
    data["Area Code (M49)"] = pd.to_numeric(data["Area Code (M49)"], errors="coerce")
    data["Value"] = pd.to_numeric(data["Value"], errors="coerce")
    country_use = data.loc[
        data["Element"].eq("Agricultural Use")
        & data["Unit"].eq("t")
        & data["Area Code (M49)"].isin(country_codes)
    ]
    annual = country_use.groupby("Year")["Value"].sum(min_count=1).dropna()
    available = annual.loc[(annual.index <= 2022) & (annual.index >= 1961)]
    if available.empty:
        raise ValueError("No country-level agricultural phosphate-use data found")
    year = int(available.index.max())
    p2o5_tons = float(available.loc[year])
    return year, p2o5_tons * P2O5_TO_P / 1_000_000


def load_mining() -> tuple[int, float]:
    path = RAW / "Phosphate rock (P2O5) production data-national level (USGS,1998-2022).xlsx"
    data = pd.read_excel(path, sheet_name="P2O5 (tons)")
    year_columns = [column for column in data.columns if str(column).isdigit()]
    candidates: list[tuple[int, float, int]] = []
    for column in year_columns:
        values = pd.to_numeric(data[column], errors="coerce")
        valid = int(values.notna().sum())
        if valid >= 10:
            candidates.append((int(column), float(values.sum()), valid))
    if not candidates:
        raise ValueError("No complete phosphate-mining year could be identified")
    year, p2o5_tons, _ = max(candidates, key=lambda row: row[0])
    return year, p2o5_tons * P2O5_TO_P / 1_000_000


def simulate_scenario(
    *,
    year: int,
    fertilizer_bau_mt: float,
    crop_harvest_mt: float,
    mining_share: float,
    reduce_rate: float,
    manure_rate: float,
    struvite_rate: float,
) -> tuple[dict[str, float | int | str], list[dict[str, float | str]]]:
    food_p = crop_harvest_mt * FOOD_SHARE
    feed_p = crop_harvest_mt * FEED_SHARE
    other_crop_p = crop_harvest_mt - food_p - feed_p
    animal_product_p = feed_p * LIVESTOCK_PUE
    manure_p = feed_p - animal_product_p
    resident_intake_p = food_p + animal_product_p
    wastewater_p = resident_intake_p * WASTEWATER_SHARE
    human_retention_p = resident_intake_p - wastewater_p
    manure_recovered_p = manure_p * manure_rate
    manure_loss_p = manure_p - manure_recovered_p
    struvite_recovered_p = wastewater_p * struvite_rate
    wastewater_loss_p = wastewater_p - struvite_recovered_p

    baseline_manure_p = manure_p * BASE_MANURE_RATE
    baseline_struvite_p = wastewater_p * BASE_STRUVITE_RATE
    additional_recycled_p = (
        manure_recovered_p - baseline_manure_p
        + struvite_recovered_p - baseline_struvite_p
    )
    fertilizer_p = max(
        0.0,
        fertilizer_bau_mt * (1 - reduce_rate) - additional_recycled_p,
    )

    reduce_scaled = reduce_rate / 0.20
    manure_scaled = (manure_rate - BASE_MANURE_RATE) / (
        TARGET_MANURE_RATE - BASE_MANURE_RATE
    )
    field_loss_rate = max(
        0.02,
        0.10 * (1 - 0.15 * reduce_scaled - 0.08 * manure_scaled - 0.12 * reduce_scaled * manure_scaled),
    )
    acs_flows = ACSPModel(
        fertilizer_p=fertilizer_p,
        organic_fertilizer_p=manure_recovered_p,
        recovered_wastewater_p=struvite_recovered_p,
        crop_harvest_p=crop_harvest_mt,
        field_loss_rate=field_loss_rate,
    ).calculate()
    field_loss_p = acs_flows["field_loss_p"]
    soil_release_p = acs_flows["soil_legacy_release_p"]
    soil_accumulation_p = acs_flows["soil_legacy_accumulation_p"]

    mining_p = fertilizer_p * min(1.0, max(0.0, mining_share))
    other_supply_p = fertilizer_p - mining_p
    total_environmental_loss = field_loss_p + manure_loss_p + wastewater_loss_p
    total_input = fertilizer_p + soil_release_p
    total_output = (
        field_loss_p + other_crop_p + manure_loss_p + wastewater_loss_p
        + human_retention_p + soil_accumulation_p
    )
    balance_error = abs(total_input - total_output) / (total_input + 1e-6)

    checks = [
        ("Chemical industry", mining_p + other_supply_p, fertilizer_p),
        (
            "Cropland",
            fertilizer_p + manure_recovered_p + struvite_recovered_p + soil_release_p,
            crop_harvest_mt + field_loss_p + soil_accumulation_p,
        ),
        ("Livestock", feed_p, animal_product_p + manure_p),
        ("Manure handling", manure_p, manure_recovered_p + manure_loss_p),
        ("Residents", food_p + animal_product_p, human_retention_p + wastewater_p),
        ("Wastewater", wastewater_p, struvite_recovered_p + wastewater_loss_p),
        ("Whole system", total_input, total_output),
    ]
    check_rows = []
    for subsystem, input_p, output_p in checks:
        error = abs(input_p - output_p) / (input_p + 1e-6)
        check_rows.append(
            {
                "Year": year,
                "Subsystem": subsystem,
                "Input (Mt P)": input_p,
                "Output (Mt P)": output_p,
                "Relative error": error,
                "Pass": error < BALANCE_TOLERANCE,
            }
        )
    if balance_error >= BALANCE_TOLERANCE or not all(row["Pass"] for row in check_rows):
        raise AssertionError(f"Mass balance failed for {year}: {balance_error:.6e}")

    metrics: dict[str, float | int | str] = {
        "Year": year,
        "Scenario": "",
        "Mineral fertilizer input (Mt P)": fertilizer_p,
        "Primary mining requirement (Mt P)": mining_p,
        "Other fertilizer supply (Mt P)": other_supply_p,
        "Crop harvest P (Mt P)": crop_harvest_mt,
        "Crop uptake P (Mt P; estimated)": acs_flows["crop_uptake_p"],
        "Crop residue P (Mt P; estimated)": acs_flows["crop_residue_p"],
        "Crop PUE (%)": 100 * crop_harvest_mt / (fertilizer_p + manure_recovered_p + struvite_recovered_p + soil_release_p),
        "Manure generated (Mt P)": manure_p,
        "Manure recycled (Mt P)": manure_recovered_p,
        "Struvite recovered (Mt P)": struvite_recovered_p,
        "Field loss (Mt P)": field_loss_p,
        "Manure loss (Mt P)": manure_loss_p,
        "Wastewater loss (Mt P)": wastewater_loss_p,
        "Total environmental loss (Mt P)": total_environmental_loss,
        "Soil legacy release (Mt P)": soil_release_p,
        "Soil legacy accumulation (Mt P)": soil_accumulation_p,
        "Relative mass-balance error": balance_error,
        "Reduction rate (%)": 100 * reduce_rate,
        "Manure utilization rate (%)": 100 * manure_rate,
        "Struvite recovery rate (%)": 100 * struvite_rate,
    }
    return metrics, check_rows


def build_flow_ledger(metrics: dict[str, float | int | str]) -> pd.DataFrame:
    flow_values = [
        ("Primary phosphate mining", "Chemical industry", "Primary supply", metrics["Primary mining requirement (Mt P)"]),
        ("Other supply (trade/stock estimate)", "Chemical industry", "Estimated supply gap", metrics["Other fertilizer supply (Mt P)"]),
        ("Chemical industry", "Cropland", "Mineral fertilizer", metrics["Mineral fertilizer input (Mt P)"]),
        ("Manure pool", "Cropland", "Recycled manure", metrics["Manure recycled (Mt P)"]),
        ("Wastewater", "Cropland", "Recovered struvite", metrics["Struvite recovered (Mt P)"]),
        ("Soil legacy", "Cropland", "Soil legacy release", metrics["Soil legacy release (Mt P)"]),
        ("Cropland", "Crop harvest", "Crop harvest", metrics["Crop harvest P (Mt P)"]),
        ("Cropland", "Environmental losses", "Field loss", metrics["Field loss (Mt P)"]),
        ("Cropland", "Soil legacy", "Soil accumulation", metrics["Soil legacy accumulation (Mt P)"]),
        ("Crop harvest", "Residents", "Plant food", metrics["Crop harvest P (Mt P)"] * FOOD_SHARE),
        ("Crop harvest", "Livestock", "Feed", metrics["Crop harvest P (Mt P)"] * FEED_SHARE),
        (
            "Crop harvest",
            "Other crop uses",
            "Other crop uses",
            metrics["Crop harvest P (Mt P)"] * (1 - FOOD_SHARE - FEED_SHARE),
        ),
        ("Livestock", "Residents", "Animal products", metrics["Manure generated (Mt P)"] * LIVESTOCK_PUE / (1 - LIVESTOCK_PUE)),
        ("Livestock", "Manure pool", "Manure generated", metrics["Manure generated (Mt P)"]),
        ("Manure pool", "Environmental losses", "Unrecovered manure", metrics["Manure generated (Mt P)"] - metrics["Manure recycled (Mt P)"]),
    ]
    resident_intake = metrics["Crop harvest P (Mt P)"] * FOOD_SHARE + metrics["Manure generated (Mt P)"] * LIVESTOCK_PUE / (1 - LIVESTOCK_PUE)
    wastewater = resident_intake * WASTEWATER_SHARE
    flow_values.extend(
        [
            ("Residents", "Human retention", "Human retention", resident_intake - wastewater),
            ("Residents", "Wastewater", "Wastewater generation", wastewater),
            ("Wastewater", "Environmental losses", "Unrecovered wastewater P", wastewater - metrics["Struvite recovered (Mt P)"]),
        ]
    )
    ledger = pd.DataFrame(
        flow_values,
        columns=["Source", "Target", "Flow", "Value (Mt P)"],
    )
    ledger["Value (Mt P)"] = pd.to_numeric(ledger["Value (Mt P)"], errors="coerce")
    return ledger.loc[ledger["Value (Mt P)"].gt(1e-12)].reset_index(drop=True)


def write_sankey(ledger: pd.DataFrame, output_path: Path) -> None:
    labels = ledger["Source"].tolist() + ledger["Target"].tolist()
    nodes = list(dict.fromkeys(labels))
    node_index = {name: index for index, name in enumerate(nodes)}
    display_nodes = [NODE_LABELS_ZH.get(name, name) for name in nodes]
    colors = [
        "#315C4B" if "loss" in name.lower() or "environment" in name.lower()
        else "#C17B3A" if name in {"Primary phosphate mining", "Other supply (trade/stock estimate)"}
        else "#537A9A" if name in {"Chemical industry", "Cropland", "Livestock", "Residents"}
        else "#7F9E67"
        for name in nodes
    ]
    figure = go.Figure(
        go.Sankey(
            arrangement="snap",
            node={"label": display_nodes, "pad": 18, "thickness": 18, "color": colors},
            link={
                "source": ledger["Source"].map(node_index),
                "target": ledger["Target"].map(node_index),
                "value": ledger["Value (Mt P)"],
                "label": ledger["Flow"].map(lambda value: FLOW_LABELS_ZH.get(value, value)),
                "customdata": ledger["Flow"].map(lambda value: FLOW_LABELS_ZH.get(value, value)),
                "hovertemplate": "%{customdata}<br>%{value:.3f} Mt P<extra></extra>",
                "color": "rgba(83,122,154,0.38)",
            },
        )
    )
    figure.update_layout(
        title="2022 年全球人为磷流（单位：Mt P，估算）",
        font={"family": "Microsoft YaHei, sans-serif", "size": 13},
        margin={"l": 20, "r": 20, "t": 60, "b": 20},
    )
    figure.write_html(output_path, include_plotlyjs=True, full_html=True)


def configure_plot_fonts() -> None:
    candidates = ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Arial Unicode MS"]
    available = {font.name for font in font_manager.fontManager.ttflist}
    selected = next((name for name in candidates if name in available), "DejaVu Sans")
    plt.rcParams["font.family"] = selected
    plt.rcParams["axes.unicode_minus"] = False


def write_statistical_charts(
    history: pd.DataFrame,
    category_2022: pd.DataFrame,
    scenario_table: pd.DataFrame,
    sensitivity_results: pd.DataFrame,
    output_dir: Path,
) -> list[Path]:
    configure_plot_fonts()
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = []

    figure, axis = plt.subplots(figsize=(11, 6))
    years = pd.to_numeric(history["Year"], errors="coerce")
    harvest_mt = pd.to_numeric(history["Crop harvest P (tons)"], errors="coerce") / 1_000_000
    axis.plot(years, harvest_mt, color="#287D78", linewidth=2.2)
    axis.fill_between(years, harvest_mt, color="#287D78", alpha=0.12)
    axis.scatter([2022], [harvest_mt.loc[years.eq(2022)].iloc[0]], color="#D17B3F", zorder=3)
    axis.set(title="全球作物收获纯磷变化（1961—2022）", xlabel="年份", ylabel="作物收获磷（Mt P）")
    axis.grid(axis="y", alpha=0.25)
    axis.annotate(
        f"2022 年：{harvest_mt.loc[years.eq(2022)].iloc[0]:.2f} Mt P",
        xy=(2022, harvest_mt.loc[years.eq(2022)].iloc[0]),
        xytext=(-115, 18),
        textcoords="offset points",
        arrowprops={"arrowstyle": "->", "color": "#555555"},
    )
    figure.tight_layout()
    path = output_dir / "全球作物磷历史趋势.png"
    figure.savefig(path, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(figure)
    outputs.append(path)

    categories = category_2022.copy()
    categories["类别中文"] = categories["Product"].astype(str).map(
        lambda value: CATEGORY_LABELS_ZH.get(value, value)
    )
    categories["作物磷（Mt P）"] = pd.to_numeric(
        categories["Crop harvest P (tons)"], errors="coerce"
    ) / 1_000_000
    categories = categories.loc[categories["作物磷（Mt P）"].gt(0)].sort_values("作物磷（Mt P）")
    figure, axis = plt.subplots(figsize=(10, 7))
    bars = axis.barh(categories["类别中文"], categories["作物磷（Mt P）"], color="#6A9C78")
    axis.set(title="2022 年全球作物收获磷分类", xlabel="作物收获磷（Mt P）", ylabel="产品类别")
    axis.grid(axis="x", alpha=0.25)
    axis.bar_label(bars, fmt="%.2f", padding=3, fontsize=8)
    figure.tight_layout()
    path = output_dir / "2022作物磷分类.png"
    figure.savefig(path, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(figure)
    outputs.append(path)

    scenario_labels = {"2022 estimate": "2022 年估算", "2050 BAU": "2050 年常规情景", "2050 3R": "2050 年 3R 情景"}
    scenarios = scenario_table.copy()
    scenarios["情景"] = scenarios["Scenario"].map(scenario_labels)
    positions = np.arange(len(scenarios))
    width = 0.36
    figure, axis = plt.subplots(figsize=(10, 6))
    fertilizer_bars = axis.bar(
        positions - width / 2,
        scenarios["Mineral fertilizer input (Mt P)"],
        width,
        label="矿物磷肥投入",
        color="#4E79A7",
    )
    loss_bars = axis.bar(
        positions + width / 2,
        scenarios["Total environmental loss (Mt P)"],
        width,
        label="环境损失",
        color="#C66B4E",
    )
    axis.set(
        title="2022 估算与 2050 情景对比",
        ylabel="磷流量（Mt P）",
        xticks=positions,
        xticklabels=scenarios["情景"],
    )
    axis.grid(axis="y", alpha=0.25)
    axis.legend(frameon=False)
    axis.bar_label(fertilizer_bars, fmt="%.1f", padding=2, fontsize=8)
    axis.bar_label(loss_bars, fmt="%.1f", padding=2, fontsize=8)
    figure.tight_layout()
    path = output_dir / "2050情景对比.png"
    figure.savefig(path, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(figure)
    outputs.append(path)

    term_labels = {
        "Reduce": "减量（主效应）",
        "Replace": "替代（主效应）",
        "Recycle": "回收（主效应）",
        "Reduce × Replace": "减量 × 替代",
        "Reduce × Recycle": "减量 × 回收",
        "Replace × Recycle": "替代 × 回收",
    }
    regression = sensitivity_results.copy()
    regression["中文项"] = regression["Term"].map(term_labels)
    regression = regression.sort_values("Standardized coefficient")
    colors = [
        "#C66B4E" if coefficient < 0 else "#287D78"
        for coefficient in regression["Standardized coefficient"]
    ]
    figure, axis = plt.subplots(figsize=(10, 6))
    bars = axis.barh(
        regression["中文项"],
        regression["Standardized coefficient"],
        color=colors,
    )
    axis.axvline(0, color="#444444", linewidth=0.8)
    axis.set(title="3R 措施对环境损失削减率的标准化回归系数", xlabel="标准化回归系数（p 值见回归结果表）", ylabel="政策变量")
    axis.grid(axis="x", alpha=0.25)
    for bar, coefficient in zip(bars, regression["Standardized coefficient"]):
        value = bar.get_width()
        axis.text(
            value + (0.008 if value >= 0 else -0.008),
            bar.get_y() + bar.get_height() / 2,
            f"{coefficient:+.3f}",
            ha="left" if value >= 0 else "right",
            va="center",
            fontsize=8,
        )
    figure.tight_layout()
    path = output_dir / "3R敏感性回归系数.png"
    figure.savefig(path, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(figure)
    outputs.append(path)
    return outputs


def run_sensitivity(
    fertilizer_2050: float,
    harvest_2050: float,
    mining_share: float,
    bau_loss: float,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    samples = []
    for reduce_rate in np.linspace(0.0, 0.20, 7):
        for manure_rate in np.linspace(BASE_MANURE_RATE, TARGET_MANURE_RATE, 7):
            for struvite_rate in np.linspace(BASE_STRUVITE_RATE, TARGET_STRUVITE_RATE, 7):
                metrics, _ = simulate_scenario(
                    year=2050,
                    fertilizer_bau_mt=fertilizer_2050,
                    crop_harvest_mt=harvest_2050,
                    mining_share=mining_share,
                    reduce_rate=float(reduce_rate),
                    manure_rate=float(manure_rate),
                    struvite_rate=float(struvite_rate),
                )
                samples.append(
                    {
                        "Reduce": reduce_rate,
                        "Replace": manure_rate,
                        "Recycle": struvite_rate,
                        "Total environmental loss (Mt P)": metrics["Total environmental loss (Mt P)"],
                        "Environmental loss reduction (%)": 100 * (bau_loss - metrics["Total environmental loss (Mt P)"]) / bau_loss,
                    }
                )
    scenarios = pd.DataFrame(samples)
    centered = pd.DataFrame(
        {
            name: scenarios[name] - scenarios[name].mean()
            for name in ["Reduce", "Replace", "Recycle"]
        }
    )
    features = centered.copy()
    features["Reduce × Replace"] = centered["Reduce"] * centered["Replace"]
    features["Reduce × Recycle"] = centered["Reduce"] * centered["Recycle"]
    features["Replace × Recycle"] = centered["Replace"] * centered["Recycle"]
    scaler_x = StandardScaler()
    scaler_y = StandardScaler()
    x_standardized = pd.DataFrame(
        scaler_x.fit_transform(features), columns=features.columns, index=features.index
    )
    y_standardized = scaler_y.fit_transform(
        scenarios[["Environmental loss reduction (%)"]]
    ).ravel()
    model = sm.OLS(y_standardized, sm.add_constant(x_standardized)).fit()
    rows = []
    for term in features.columns:
        coefficient = float(model.params[term])
        p_value = float(model.pvalues[term])
        if "×" not in term:
            effect = "主效应"
        elif p_value >= 0.05:
            effect = "无显著交互"
        elif coefficient > 0:
            effect = "协同增强"
        else:
            effect = "拮抗削弱"
        rows.append(
            {
                "Term": term,
                "Standardized coefficient": coefficient,
                "p-value": p_value,
                "Effect type": effect,
                "R-squared": float(model.rsquared),
                "Sample count": len(scenarios),
            }
        )
    return scenarios, pd.DataFrame(rows)


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    population, country_codes = load_population()
    history, category_history, coefficients = load_crop_history()
    fertilizer_year, fertilizer_p_mt = load_fertilizer(population, country_codes)
    mining_year, mining_p_mt = load_mining()

    population_2021 = world_population(population, fertilizer_year, "Estimates")
    population_2022 = world_population(population, 2022, "Estimates")
    population_2050 = world_population(population, 2050, "Medium")
    population_mining_year = world_population(population, mining_year, "Estimates")
    fertilizer_2022 = fertilizer_p_mt * population_2022 / population_2021
    fertilizer_2050 = fertilizer_p_mt * population_2050 / population_2021
    mining_2022_estimate = mining_p_mt * population_2022 / population_mining_year
    mining_share = min(1.0, mining_2022_estimate / fertilizer_2022)

    crop_2022_row = history.loc[history["Year"].eq(2022), "Crop harvest P (tons)"]
    if crop_2022_row.empty:
        raise ValueError("Global 2022 crop P is missing")
    crop_2022_mt = float(crop_2022_row.iloc[0]) / 1_000_000
    population_scale_2050 = population_2050 / population_2022
    crop_2050_mt = crop_2022_mt * population_scale_2050

    current, current_checks = simulate_scenario(
        year=2022,
        fertilizer_bau_mt=fertilizer_2022,
        crop_harvest_mt=crop_2022_mt,
        mining_share=mining_share,
        reduce_rate=0.0,
        manure_rate=BASE_MANURE_RATE,
        struvite_rate=BASE_STRUVITE_RATE,
    )
    current["Scenario"] = "2022 estimate"
    bau_2050, bau_checks = simulate_scenario(
        year=2050,
        fertilizer_bau_mt=fertilizer_2050,
        crop_harvest_mt=crop_2050_mt,
        mining_share=mining_share,
        reduce_rate=0.0,
        manure_rate=BASE_MANURE_RATE,
        struvite_rate=BASE_STRUVITE_RATE,
    )
    bau_2050["Scenario"] = "2050 BAU"
    three_r, three_r_checks = simulate_scenario(
        year=2050,
        fertilizer_bau_mt=fertilizer_2050,
        crop_harvest_mt=crop_2050_mt,
        mining_share=mining_share,
        reduce_rate=0.20,
        manure_rate=TARGET_MANURE_RATE,
        struvite_rate=TARGET_STRUVITE_RATE,
    )
    three_r["Scenario"] = "2050 3R"
    three_r["Environmental loss reduction vs BAU (%)"] = 100 * (
        bau_2050["Total environmental loss (Mt P)"]
        - three_r["Total environmental loss (Mt P)"]
    ) / bau_2050["Total environmental loss (Mt P)"]
    bau_2050["Environmental loss reduction vs BAU (%)"] = 0.0
    current["Environmental loss reduction vs BAU (%)"] = np.nan

    scenario_rows = [current, bau_2050, three_r]
    checks = current_checks + bau_checks + three_r_checks
    scenario_table = pd.DataFrame(scenario_rows)
    check_table = pd.DataFrame(checks)
    flow_ledger = build_flow_ledger(current)
    sensitivity_samples, sensitivity_results = run_sensitivity(
        fertilizer_2050,
        crop_2050_mt,
        mining_share,
        float(bau_2050["Total environmental loss (Mt P)"]),
    )

    category_2022 = category_history.loc[category_history["Year"].eq(2022)].copy()
    chart_paths = write_statistical_charts(
        history, category_2022, scenario_table, sensitivity_results, RESULTS
    )
    assumptions = pd.DataFrame(
        [
            ("Unit", "Mt P unless noted", "Conversion from tons to million metric tons"),
            ("P2O5 conversion", P2O5_TO_P, "Mass fraction P in P2O5; applied to fertilizer and mining records"),
            ("Fertilizer observation year", fertilizer_year, "Latest country-level FAOSTAT Agricultural Use year"),
            ("Mining observation year", mining_year, "Latest year with at least 10 reported countries; incomplete trailing column excluded"),
            ("2022 fertilizer estimate", fertilizer_2022, "2021 per-capita use scaled by 2022 world population"),
            ("2022 mining estimate", mining_2022_estimate, "Latest complete per-capita mining scaled by 2022 world population"),
            ("2050 population path", "Medium variant", "United Nations World Population Prospects 2024"),
            ("Crop allocation: food", FOOD_SHARE, "Assumption; source data does not provide complete food/feed allocation"),
            ("Crop allocation: feed", FEED_SHARE, "Assumption; source data does not provide complete food/feed allocation"),
            ("Crop harvest index", CROP_HARVEST_INDEX, "Assumption used to estimate crop uptake and internally returned residue"),
            ("Livestock PUE", LIVESTOCK_PUE, "Assignment reference value (23%)"),
            ("Baseline manure use", BASE_MANURE_RATE, "Assumption; assignment only specifies the 75% target"),
            ("Baseline struvite recovery", BASE_STRUVITE_RATE, "Assumption; assignment only specifies the 60% target"),
            ("Wastewater share", WASTEWATER_SHARE, "Assumption for resident P routed to wastewater"),
            ("Field-loss rate", 0.10, "Illustrative base coefficient; no measured global coefficient in provided inputs"),
            ("Cross-benefit coefficients", "0.15, 0.08, 0.12", "Illustrative reduce/manure effects on field-loss rate; sensitivity is model-based"),
            ("Material balance", BALANCE_TOLERANCE, "Relative error threshold"),
        ],
        columns=["Parameter", "Value", "Basis"],
    )

    history.to_csv(RESULTS / "global_harvest_p_1961_2022.csv", index=False, encoding="utf-8-sig")
    category_history.to_csv(RESULTS / "global_crop_categories_1961_2022.csv", index=False, encoding="utf-8-sig")
    category_2022.to_csv(RESULTS / "global_crop_categories_2022.csv", index=False, encoding="utf-8-sig")
    flow_ledger.to_csv(RESULTS / "flows_2022_estimate.csv", index=False, encoding="utf-8-sig")
    check_table.to_csv(RESULTS / "mass_balance_checks.csv", index=False, encoding="utf-8-sig")
    scenario_table.to_csv(RESULTS / "scenarios_2050.csv", index=False, encoding="utf-8-sig")
    sensitivity_results.to_csv(RESULTS / "cross_sensitivity_regression.csv", index=False, encoding="utf-8-sig")
    sensitivity_samples.to_csv(RESULTS / "cross_sensitivity_samples.csv", index=False, encoding="utf-8-sig")
    assumptions.to_csv(RESULTS / "model_assumptions.csv", index=False, encoding="utf-8-sig")
    write_sankey(flow_ledger, RESULTS / "sankey_2022_estimate.html")

    with pd.ExcelWriter(RESULTS / "lecture15_results.xlsx", engine="openpyxl") as writer:
        history.to_excel(writer, sheet_name="历史作物磷", index=False)
        category_2022.to_excel(writer, sheet_name="2022作物类别", index=False)
        flow_ledger.to_excel(writer, sheet_name="2022流量账本", index=False)
        check_table.to_excel(writer, sheet_name="守恒核验", index=False)
        scenario_table.to_excel(writer, sheet_name="2050情景", index=False)
        sensitivity_results.to_excel(writer, sheet_name="交叉敏感性", index=False)
        assumptions.to_excel(writer, sheet_name="模型假设", index=False)

    reduction = float(three_r["Environmental loss reduction vs BAU (%)"])
    report = f"""# 第十五讲磷循环物质流分析结果

## 主要结果

- 2022 年全球作物收获纯磷：{crop_2022_mt:.3f} Mt P，取自工作簿中的 `World` 汇总行。
- 2022 年矿物磷肥纯磷量：{fertilizer_2022:.3f} Mt P；依据 {fertilizer_year} 年各国人均施用量和世界人口估算。
- 2050 年常规情景化肥磷需求：{fertilizer_2050:.3f} Mt P，采用联合国人口中位情景并假设人均施用量不变。
- 2050 年 3R 情景环境损失较常规情景降低：{reduction:.2f}%。
- 最大物质流相对误差：{check_table['Relative error'].max():.3e}；全部检查均满足阈值 {BALANCE_TOLERANCE:g}。

## 数据口径与结果解释

化肥施用源数据截至 {fertilizer_year} 年。磷矿工作簿末尾年份列不完整，因此采用最近完整年份（{mining_year} 年）并按人口比例估算 2022 年供应。作物磷采用论文预先核算的纯磷表；含磷系数表仅用于类别说明和数据溯源，不再重复乘入纯磷值。

现有资料没有完整的全球五子系统年度流量矩阵、作物食用/饲料比例、粪肥及污水基准回收率或实测田间损失系数。因此桑基图和情景结果是透明的课堂核算模型，不代表对论文全部图件的精确复现。参数假设见 `model_assumptions.csv`。回归使用确定性的 343 组情景网格，其显著性和拟合优度描述模型响应面，不构成基于实测样本的因果推断。

## 结果文件

- `lecture15_results.xlsx`：各项分析结果汇总表。
- `sankey_2022_estimate.html`：中文交互式桑基图。
- `全球作物磷历史趋势.png`、`2022作物磷分类.png`、`2050情景对比.png`、`3R敏感性回归系数.png`：中文统计图件。
- `mass_balance_checks.csv`：子系统及全系统守恒核验。
- `cross_sensitivity_samples.csv`、`cross_sensitivity_regression.csv`：情景网格和标准化交互回归结果。
"""
    (RESULTS / "analysis_report.md").write_text(report, encoding="utf-8")

    print(f"2022 年作物收获纯磷：{crop_2022_mt:.3f} Mt")
    print(f"2050 年常规情景化肥磷需求：{fertilizer_2050:.3f} Mt")
    print(f"2050 年 3R 情景环境损失降幅：{reduction:.2f}%")
    print(f"最大物质流相对误差：{check_table['Relative error'].max():.3e}")
    scenario_console = scenario_table[
        [
            "Scenario",
            "Mineral fertilizer input (Mt P)",
            "Total environmental loss (Mt P)",
            "Crop PUE (%)",
            "Environmental loss reduction vs BAU (%)",
        ]
    ].copy()
    scenario_console["Scenario"] = scenario_console["Scenario"].map(
        {"2022 estimate": "2022 年估算", "2050 BAU": "2050 年常规情景", "2050 3R": "2050 年 3R 情景"}
    )
    scenario_console = scenario_console.rename(
        columns={
            "Scenario": "情景",
            "Mineral fertilizer input (Mt P)": "矿物磷肥投入（Mt P）",
            "Total environmental loss (Mt P)": "环境损失（Mt P）",
            "Crop PUE (%)": "作物磷利用率（%）",
            "Environmental loss reduction vs BAU (%)": "损失降幅（%）",
        }
    )
    for column in scenario_console.columns[1:]:
        scenario_console[column] = scenario_console[column].map(
            lambda value: "--" if pd.isna(value) else f"{value:.3f}"
        )
    print("\n【情景结果对比】")
    print(scenario_console.to_string(index=False))

    term_labels = {
        "Reduce": "减量（主效应）",
        "Replace": "替代（主效应）",
        "Recycle": "回收（主效应）",
        "Reduce × Replace": "减量 × 替代",
        "Reduce × Recycle": "减量 × 回收",
        "Replace × Recycle": "替代 × 回收",
    }
    regression_console = sensitivity_results[
        ["Term", "Standardized coefficient", "p-value", "Effect type", "R-squared", "Sample count"]
    ].copy()
    regression_console["Term"] = regression_console["Term"].map(term_labels)
    regression_console = regression_console.rename(
        columns={
            "Term": "回归项",
            "Standardized coefficient": "标准化系数",
            "p-value": "p 值",
            "Effect type": "效应判定",
            "R-squared": "R²",
            "Sample count": "样本数",
        }
    )
    regression_console["标准化系数"] = regression_console["标准化系数"].map(lambda value: f"{value:+.6f}")
    regression_console["p 值"] = regression_console["p 值"].map(
        lambda value: "<1e-300" if value == 0 else f"{value:.3e}"
    )
    regression_console["R²"] = regression_console["R²"].map(lambda value: f"{value:.6f}")
    print("\n【交叉敏感性回归统计表】")
    print(regression_console.to_string(index=False))
    print(f"已生成 PNG 统计图：{len(chart_paths)} 张")
    print("汇总工作簿：lecture15_results.xlsx；详细说明：analysis_report.md")
    print(f"结果目录：{RESULTS}")


if __name__ == "__main__":
    main()