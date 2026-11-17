# -*- coding: utf-8 -*-
"""数据清洗与整合模块：任务 1 第 1 步
读取农产品纯磷产出宽表、含磷率字典、人口预测与食物磷供给数据，
完成跨表连接与时间序列构建。
"""
import pandas as pd
import numpy as np
from config import (F_PROD, F_COEF, F_POP, F_FOODP, F_ANIMAL_DIR,
                    CROP_CATEGORIES, ANIMAL_CATEGORIES, CATEGORY_MAP)


def load_product_P_series():
    """读取农产品纯磷产出表，规整年份列为整型，返回长表与全球年度序列。"""
    df = pd.read_excel(F_PROD, sheet_name="product_P_result (tons)")
    df.columns = [int(c) if str(c).strip().isdigit() else str(c).strip()
                  for c in df.columns]
    df = df.dropna(subset=["Country", "Product"])
    year_cols = [c for c in df.columns if isinstance(c, int)]
    df[year_cols] = df[year_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    # 全球年度总产出（含 A–M 全部类别）
    global_series = df[year_cols].sum()
    # 按类别分组（作物 / 动物）
    by_cat = df.groupby("Product")[year_cols].sum()
    crop_series = by_cat.loc[[c for c in CROP_CATEGORIES if c in by_cat.index]].sum()
    animal_series = by_cat.loc[[c for c in ANIMAL_CATEGORIES if c in by_cat.index]].sum()
    return df, global_series, crop_series, animal_series


def load_P_coefficients():
    """读取含磷率字典（g P / kg 实物量），并与产品类别图例合并。"""
    d = pd.read_excel(F_COEF, sheet_name="Sheet1")
    d = d[["Product", "Category", "Coefficient"]].dropna(subset=["Product"])
    d["Coefficient"] = pd.to_numeric(d["Coefficient"], errors="coerce")
    d = d.dropna(subset=["Coefficient"])
    d["Category_Name"] = d["Category"].map(CATEGORY_MAP)
    return d


def build_task1_dataset():
    """跨表连接：宽表(类别字母) × 字典(类别含义) → 类别级含磷产出时间序列。"""
    df, g, crop_s, animal_s = load_product_P_series()
    coef = load_P_coefficients()
    cat_map = (coef[["Category", "Category_Name"]]
               .dropna().drop_duplicates().set_index("Category")["Category_Name"])
    summary = pd.DataFrame({
        "类别": sorted(df["Product"].unique()),
        "食品组": [cat_map.get(c, "—") for c in sorted(df["Product"].unique())],
    })
    return df, coef, summary, g, crop_s, animal_s


def load_population_projection():
    """读取 UN WPP 人口预测：返回 2022 年（Estimates）与 2050 年（Medium）世界人口。"""
    est = pd.read_excel(F_POP, sheet_name="Estimates", header=16)
    med = pd.read_excel(F_POP, sheet_name="Medium variant", header=16)
    popcol = "Total Population, as of 1 January (thousands)"
    est = est[(est["Variant"] == "Estimates") & (est["Region, subregion, country or area *"] == "World")]
    med = med[(med["Variant"] == "Medium") & (med["Region, subregion, country or area *"] == "World")]
    p2022 = float(est.loc[est["Year"] == 2022, popcol].iloc[0]) * 1000.0  # 人
    p2050 = float(med.loc[med["Year"] == 2050, popcol].iloc[0]) * 1000.0
    return p2022, p2050


def load_food_P_supply_2021():
    """读取食物磷供给数据（mg/cap/d），汇总各食品组得到人均日摄入，返回全球年均食物磷供给（kt P）。"""
    d = pd.read_csv(F_FOODP)
    d = d[d["Indicator"] == "Phosphorus supply"]
    d["Value"] = pd.to_numeric(d["Value"], errors="coerce")
    per_cap = d.groupby(["Area", "Year"])["Value"].sum().reset_index()
    latest = int(per_cap["Year"].max())
    per_cap = per_cap[per_cap["Year"] == latest]
    mg_cap_day = per_cap["Value"].mean()          # 各国简单平均
    kt_yr = mg_cap_day * 1e-6 * 8000.0 * 365.0    # 按 80 亿人折算 kt P/yr
    return latest, mg_cap_day, kt_yr


if __name__ == "__main__":
    df, coef, summary, g, crop_s, animal_s = build_task1_dataset()
    print("=== 任务1 数据清洗结果 ===")
    print(summary.to_string(index=False))
    print(f"\n全球农产品纯磷产出: 1961 {g[1961]/1e6:.2f} Mt P, 2022 {g[2022]/1e6:.2f} Mt P")
    print(f"  其中植物性产品 2022: {crop_s[2022]/1e6:.2f} Mt P; 动物性产品 2022: {animal_s[2022]/1e6:.2f} Mt P")
    print(f"含磷率字典: {len(coef)} 条产品系数记录")
    p22, p50 = load_population_projection()
    print(f"世界人口: 2022 {p22/1e9:.3f} 十亿; 2050(Medium) {p50/1e9:.3f} 十亿; 增长比 {p50/p22:.4f}")
    yr, mg, kt = load_food_P_supply_2021()
    print(f"食物磷供给({yr}): 人均 {mg:.0f} mg/cap/d → 全球约 {kt:.0f} kt P/yr")
