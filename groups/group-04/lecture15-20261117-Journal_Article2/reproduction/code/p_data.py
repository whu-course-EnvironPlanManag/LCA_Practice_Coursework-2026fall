# -*- coding: utf-8 -*-
"""Task 1 真实数据读取：作物纯磷产出、含磷率字典、化肥施用、人口预测。

数据源（均来自 `source_data/` 原始数据包，不做任何改数）：
1. `Supplementary_dataset_PNAS_First_Revision/1.*/Agricultural products_P_result_national level（1961-2022）.xlsx`
   —— 工作表 `product_P_result (tons)`，216 个国家/地区 × 13 类产品（A—M）× 1961—2022 年纯磷产出（t）。
   其中 World/Africa/Asia/Europe/Americas/Oceania 为汇总行，求全球值只用 `World` 行，避免重复计数。
2. `Supplementary_dataset_PNAS_First_Revision/3.P content coefficient of products_Production.xlsx`
   —— 279 种具体农产品 → A—M 类别的含磷率字典（g P / kg）。
3. `Origin data/7.Global and national level CPF application and trade data/Nutrient phosphate P2O5 use data at the national level.csv`
   —— FAOSTAT RFN 数据，`Element = Agricultural Use`、`Unit = t` 的 P2O5 施用量，按国家求和后 × 0.4364 折合纯磷。
4. `Supplementary_dataset_PNAS_First_Revision/7.Global population projection data ...xlsx`
   —— UN WPP 2024，`Estimates`（历史）与 `Medium variant`（中方案预测）。
"""
from __future__ import annotations

from functools import lru_cache

import pandas as pd

from p_config import LECTURE, OUT_DATA, P2O5_TO_P, SRC_DATA

SUPP = SRC_DATA / "Supplementary_dataset_PNAS_First_Revision"
AG_FILE = next(SUPP.glob("1.*/*.xlsx"))
COEF_FILE = next(SUPP.glob("3.P content coefficient of products_Production.xlsx"))
POP_FILE = next(SUPP.glob("7.Global population projection data*.xlsx"))
FERT_FILE = (SRC_DATA / "Origin data" / "7.Global and national level CPF application and trade data"
             / "Nutrient phosphate P2O5 use data at the national level.csv")

AGGREGATES = {"World", "Africa", "Asia", "Europe", "Americas", "Oceania"}


def _year_cols(df: pd.DataFrame) -> list[int]:
    return sorted(int(c) for c in df.columns if str(c).strip().isdigit())


@lru_cache(maxsize=1)
def load_crop_p() -> pd.DataFrame:
    """全球作物纯磷产出（Mt P/a），1961—2022，来自 World 汇总行。"""
    raw = pd.read_excel(AG_FILE, sheet_name="product_P_result (tons)")
    years = _year_cols(raw)
    world = raw[raw["Country"].astype(str).str.strip() == "World"].copy()
    if world.empty:  # 退化方案：剔除汇总行后按国家求和
        world = raw[~raw["Country"].isin(AGGREGATES)].copy()
    for y in years:
        world[y] = pd.to_numeric(world[y], errors="coerce")
    series = world[years].sum() / 1e6
    out = pd.DataFrame(dict(year=years, crop_p_Mt=series.to_numpy()))
    out.to_csv(OUT_DATA / "crop_p_production_1961_2022.csv", index=False)
    return out


@lru_cache(maxsize=1)
def load_crop_p_by_category() -> pd.DataFrame:
    """2022 年 13 类产品的纯磷产出与类别含磷率（跨表连接结果）。"""
    raw = pd.read_excel(AG_FILE, sheet_name="product_P_result (tons)")
    years = _year_cols(raw)
    world = raw[raw["Country"].astype(str).str.strip() == "World"].set_index("Product")
    coef = pd.read_excel(COEF_FILE)
    coef = coef.rename(columns={coef.columns[2]: "coefficient_g_per_kg"})
    coef["coefficient_g_per_kg"] = pd.to_numeric(coef["coefficient_g_per_kg"],
                                                 errors="coerce") * 1000  # 原表为 g P/g 实物量
    cat = (coef.groupby("Category")
           .agg(products=("Product", "size"),
                coef_mean_g_per_kg=("coefficient_g_per_kg", "mean"),
                coef_min=("coefficient_g_per_kg", "min"),
                coef_max=("coefficient_g_per_kg", "max")).reset_index()
           .rename(columns={"Category": "Product"}))
    p2022 = (pd.to_numeric(world[2022], errors="coerce") / 1e6).rename("p_2022_Mt").reset_index()
    out = cat.merge(p2022, on="Product", how="left").sort_values("p_2022_Mt", ascending=False)
    out.to_csv(OUT_DATA / "crop_p_category_2022.csv", index=False)
    return out


@lru_cache(maxsize=1)
def load_fertilizer_p() -> pd.DataFrame:
    """全球化肥磷施用量（Mt P/a），1961—2021，FAOSTAT Agricultural Use。"""
    d = pd.read_csv(FERT_FILE, encoding="latin-1",
                    usecols=["Area", "Element", "Year", "Unit", "Value"])
    d = d[(d["Element"] == "Agricultural Use") & (d["Unit"] == "t")]
    d["Year"] = pd.to_numeric(d["Year"], errors="coerce")
    d["Value"] = pd.to_numeric(d["Value"], errors="coerce")
    g = d.groupby("Year")["Value"].sum() * P2O5_TO_P / 1e6
    out = g.rename("fert_p_Mt").reset_index().rename(columns={"Year": "year"}).dropna()
    out["year"] = out["year"].astype(int)
    out.to_csv(OUT_DATA / "fertilizer_p_1961_2021.csv", index=False)
    return out


@lru_cache(maxsize=1)
def load_population() -> dict[str, float]:
    """UN WPP 2024 世界人口（十亿）：2022 历史值、2050 中方案。"""
    def world_series(sheet: str) -> pd.Series:
        d = pd.read_excel(POP_FILE, sheet_name=sheet, header=16)
        rc = next(c for c in d.columns if str(c).startswith("Region, subregion"))
        pc = next(c for c in d.columns if str(c).startswith("Total Population, as of 1 July"))
        w = d[d[rc].astype(str).str.strip() == "World"][["Year", pc]].dropna()
        w["Year"] = pd.to_numeric(w["Year"], errors="coerce")
        return (w.drop_duplicates("Year").set_index("Year")[pc].astype(float) / 1e6)  # 百万

    est = world_series("Estimates")
    med = world_series("Medium variant")
    base_year = int(max(y for y in est.index if y <= 2022))
    pop = dict(base_year=base_year, pop_2022=float(est.loc[base_year]),
               pop_2050=float(med.loc[2050]), source="UN WPP 2024 (Medium variant)")
    pd.Series(pop).to_csv(OUT_DATA / "population_projection.csv", header=False)
    return pop


def summarize() -> dict:
    crop = load_crop_p()
    fert = load_fertilizer_p()
    pop = load_population()
    return dict(
        crop_years=[int(crop["year"].min()), int(crop["year"].max())],
        crop_p_start=float(crop["crop_p_Mt"].iloc[0]),
        crop_p_end=float(crop["crop_p_Mt"].iloc[-1]),
        crop_growth=float(crop["crop_p_Mt"].iloc[-1] / crop["crop_p_Mt"].iloc[0]),
        fert_years=[int(fert["year"].min()), int(fert["year"].max())],
        fert_p_start=float(fert["fert_p_Mt"].iloc[0]),
        fert_p_end=float(fert["fert_p_Mt"].iloc[-1]),
        population=pop,
    )
