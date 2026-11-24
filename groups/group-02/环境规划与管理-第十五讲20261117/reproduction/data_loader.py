# -*- coding: utf-8 -*-
"""
data_loader.py
==============
数据清洗与整合模块：读取 1961–2022 年农产品纯磷产出宽表、含磷率字典、
人口预测、耕地面积、磷矿与化肥等数据，统一折算为千吨磷 (kt P) 与百万公顷 (M ha)。

所有路径均通过 __file__ 相对定位，杜绝硬编码绝对路径。
"""

import os
import glob

import numpy as np
import pandas as pd

# 项目根目录：reproduction/ 的上一级 = 第十五讲课程目录
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DATA = os.path.join(_BASE, "source_data")
FIRST_REV = os.path.join(SOURCE_DATA, "Supplementary_dataset_PNAS_First_Revision")
ORIGIN = os.path.join(SOURCE_DATA, "Origin data")

# 单位换算
T_TO_KT = 1e-3          # 吨 -> 千吨
T_P2O5_TO_P = 0.4366    # P2O5 中磷元素质量分数 (2×30.97/141.94)


def _find(dirpath, pattern):
    """在目录下按通配符查找第一个匹配文件。"""
    hits = glob.glob(os.path.join(dirpath, pattern))
    if not hits:
        raise FileNotFoundError(f"未找到匹配 {pattern} 的文件于 {dirpath}")
    return hits[0]


def load_product_p():
    """
    读取农产品纯磷产出宽表，返回 tidy 长表。

    返回
    ----
    DataFrame, 列 = [Country, Category, Year, P_kt]，P_kt 为千吨磷。
    """
    path = _find(FIRST_REV,
                 "1.Country-level raw data on agricultural production and P calculations/*.xlsx")
    raw = pd.read_excel(path, sheet_name="product_P_result (tons)")
    # 规整列名：年份列转整型，其余保留
    raw.columns = [int(c) if str(c).isdigit() else c for c in raw.columns]
    year_cols = [c for c in raw.columns if isinstance(c, (int, np.integer))]
    long = raw.melt(id_vars=["Country", "Product"], value_vars=year_cols,
                    var_name="Year", value_name="P_tons")
    long = long.rename(columns={"Product": "Category"})
    long["P_kt"] = long["P_tons"] * T_TO_KT
    long = long.dropna(subset=["P_kt"])
    return long[["Country", "Category", "Year", "P_kt"]].reset_index(drop=True)


def load_category_map():
    """
    读取含磷率字典，返回类别码 -> 类别名 映射（12 类：A-M 无 L）。

    返回
    ----
    dict: {类别码: 类别英文名}
    """
    path = os.path.join(FIRST_REV, "3.P content coefficient of products_Production.xlsx")
    raw = pd.read_excel(path, sheet_name=0)
    mapping = raw[["Unnamed: 4", "Unnamed: 5"]].dropna().drop_duplicates()
    return dict(zip(mapping["Unnamed: 4"], mapping["Unnamed: 5"]))


def validate_product_p(long, category_map):
    """核验纯磷长表的年份、主键、数值和类别字典覆盖。"""
    if long.empty:
        raise ValueError("农产品纯磷长表为空")
    if long[["Country", "Category", "Year"]].duplicated().any():
        raise ValueError("Country + Category + Year 存在重复键")
    if long[["Country", "Category", "Year", "P_kt"]].isna().any().any():
        raise ValueError("农产品纯磷长表存在空值")
    if (long["P_kt"] < 0).any():
        raise ValueError("农产品纯磷长表存在负值")
    year_min, year_max = int(long["Year"].min()), int(long["Year"].max())
    if (year_min, year_max) != (1961, 2022):
        raise ValueError(f"年份范围应为 1961–2022，实际为 {year_min}–{year_max}")

    categories = set(long["Category"])
    expected = set(category_map)
    missing = expected - categories
    unexpected = categories - expected - {"L"}
    if missing or unexpected:
        raise ValueError(f"类别字典不匹配，缺失={sorted(missing)}，异常={sorted(unexpected)}")
    if not np.allclose(long.loc[long["Category"] == "L", "P_kt"], 0.0):
        raise ValueError("占位类别 L 应为全零")

    return {
        "记录数": len(long), "国家数": long["Country"].nunique(),
        "有效类别数": len(expected), "占位类别": "L（全零，不参与汇总）",
        "年份范围": f"{year_min}–{year_max}",
    }


def load_cropland_area():
    """
    读取全球耕地面积（World, Area 元素, Cropland 条目）。

    返回
    ----
    Series: 索引 = 年份(int)，值 = 千公顷 (1000 ha)。
    """
    path = os.path.join(ORIGIN, "8.Global land use data", "Global level cropland area.csv")
    raw = pd.read_csv(path)
    sub = raw[(raw["Area"] == "World") & (raw["Element"] == "Area")
              & (raw["Item"] == "Cropland")]
    s = sub.set_index("Year")["Value"].sort_index()
    s.index = s.index.astype(int)
    return s


def load_population():
    """
    读取全球人口（World, Total Population - Both sexes, 千人为单位）。

    返回
    ----
    Series: 索引 = 年份(int)，值 = 千人 (1000 persons)。
    """
    path = os.path.join(ORIGIN, "9.Other datasets", "Global country-level population data.csv")
    raw = pd.read_csv(path)
    sub = raw[(raw["Area"] == "World") & (raw["Element"] == "Total Population - Both sexes")]
    s = sub.set_index("Year")["Value"].sort_index()
    s.index = s.index.astype(int)
    return s


def load_population_projection(variant="Medium variant"):
    """
    读取 UN WPP 人口预测数据（长表格式，含 Year 列）。

    使用 openpyxl 只读模式流式提取（避开 pandas.read_excel 读取 24MB 大表
    时偶发的段错误），仅保留 World 行。

    参数
    ----
    variant : str, 'Estimates'（历史）或 'Medium variant'（中位预测）。

    返回
    ----
    DataFrame: 含列 [Location, Year, Population_thousands]。
    """
    import openpyxl
    path = os.path.join(FIRST_REV,
                        "7.Global population projection data for P sustainability scenario analysis.xlsx")
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[variant]

    header = None
    loc_idx = year_idx = pop_idx = None
    rows = []
    for row in ws.iter_rows(values_only=True):
        if header is None:
            # 定位表头行（含 'Variant' 与 'country or area'）
            if row and any("Variant" in str(c) for c in row) \
                    and any("country or area" in str(c) for c in row):
                header = row
                loc_idx = next(i for i, c in enumerate(header)
                               if "country or area" in str(c))
                year_idx = next(i for i, c in enumerate(header) if str(c).strip() == "Year")
                pop_idx = next(i for i, c in enumerate(header)
                               if "1 July" in str(c) and "Total Population" in str(c))
            continue
        if row and loc_idx is not None and str(row[loc_idx]) == "World":
            year = row[year_idx]
            pop = row[pop_idx]
            if isinstance(year, (int, float)) and pop is not None:
                rows.append({"Location": "World", "Year": int(year),
                             "Population_thousands": float(pop)})
    wb.close()
    return pd.DataFrame(rows)


def load_rock_p2o5():
    """
    读取磷酸盐岩 P2O5 产量（USGS, 1998–2021），返回全球总量时间序列。

    返回
    ----
    Series: 索引 = 年份(int)，值 = P2O5 吨 (t P2O5)。
    """
    path = _find(ORIGIN, "1.Phosphate rock origin data/*production data-national level*.xlsx")
    raw = pd.read_excel(path, sheet_name="P2O5 (tons)")
    raw = raw.rename(columns={"Unnamed: 25": 2022})
    year_cols = [c for c in raw.columns if isinstance(c, (int, np.integer))]
    s = raw[year_cols].sum(axis=0)
    s.index = s.index.astype(int)
    return s.sort_index()


def load_fertilizer_intensity():
    """
    读取各国化肥施用强度（kg P/ha 与 kg P/km2）。

    返回
    ----
    DataFrame: [Country, kg_per_ha, kg_per_km2]。
    """
    path = _find(ORIGIN, "7.Global and national level CPF application and trade data/*per hectare*.xlsx")
    return pd.read_excel(path, sheet_name=0)


if __name__ == "__main__":
    # 自检：打印各数据概览
    prod = load_product_p()
    print("农产品纯磷长表:", prod.shape, "| 2022 全球总产出 (Mt P) =",
          prod[prod["Year"] == 2022]["P_kt"].sum() / 1e3)
    print("类别映射:", load_category_map())
    print("耕地面积 2022 (M ha):", load_cropland_area().get(2022) / 1e3)
    print("人口 2022 (十亿):", load_population().get(2022) / 1e6)
    print("磷矿 P2O5 2021 (Mt):", load_rock_p2o5().get(2021) / 1e6)
    proj = load_population_projection()
    print("人口预测长表:", proj.shape, "| 年范围:", proj["Year"].min(), "-", proj["Year"].max())
