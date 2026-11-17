# -*- coding: utf-8 -*-
"""数据加载与清洗模块。

所有数值均来自 source_data 下的原始文件，加载逻辑注明数据口径；
无法直接获得的量（如 2022 年化肥施用量）采用线性外推并在报告中如实说明。
"""
from functools import lru_cache
import pandas as pd
import numpy as np

import config as C

# 宽表中的 13 个产品类别（L 类在数据中恒为 0，回归变量不含 L）
CATEGORIES = list("ABCDEFGHIJKM")

# FAOSTAT QCL 中按"千头"报告的品种（World 存量数值级差 1000 倍）
_THOUSAND_HEAD_ITEMS = {"Chickens", "Ducks", "Geese", "Turkeys", "Rabbits and hares"}


def read_any(path, **kw):
    """csv 编码兼容读取：优先 utf-8，失败回退 latin-1（部分 FAOSTAT 导出含非 UTF-8 字节）。"""
    try:
        return pd.read_csv(path, encoding="utf-8", **kw)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="latin-1", **kw)


# ---------------------------------------------------------------- 农产品纯磷宽表
@lru_cache(maxsize=1)
def wide_product_table():
    """国家×品类×年份纯磷产出宽表（吨 P）。列：Country, Product, 1961..2022。"""
    df = pd.read_excel(C.WIDE_PROD_TABLE, sheet_name=C.WIDE_PROD_SHEET)
    df.columns = [int(c) if str(c).isdigit() else c for c in df.columns]
    return df


@lru_cache(maxsize=1)
def global_category_yearly():
    """全球分品类年度纯磷产出（Mt P），索引为 (年份, 品类)。"""
    df = wide_product_table()
    years = [c for c in df.columns if isinstance(c, int)]
    long = df.melt(id_vars=["Country", "Product"], value_vars=years,
                   var_name="Year", value_name="P_t")
    g = long.groupby(["Year", "Product"])["P_t"].sum().unstack() / C.T_PER_MT
    return g


def category_matrix(year):
    """指定年份的国家×品类矩阵（行=国家，列=品类，值=吨 P）。"""
    df = wide_product_table()
    m = df.pivot_table(index="Country", columns="Product", values=year, aggfunc="sum")
    m = m.reindex(columns=CATEGORIES).fillna(0.0)
    return m


# ---------------------------------------------------------------- 化肥施用量
@lru_cache(maxsize=1)
def fertilizer_p_series():
    """矿物磷肥施用量序列（吨 P/年，1961-2021 实测；2022 线性外推）。

    来源：FAOSTAT Nutrient 'Agricultural Use'，P(t)=P2O5×0.4364。
    2022 年无实测值，按 2020→2021 增量线性外推，报告中注明。
    """
    df = read_any(C.FERT_USE_CSV, usecols=["Area", "Element", "Item", "Unit", "Year", "Value"])
    sel = df[(df["Element"] == "Agricultural Use") & (df["Unit"] == "t")
             & (df["Item"] == "Nutrient phosphate P2O5 (total)")].copy()
    # 该表无 World 汇总行，P(t) 列也仅对生产/贸易行填充，故按国家求和并换算 P2O5→P
    sel["P_t"] = sel["Value"].astype(float) * C.P_IN_P2O5
    s = sel.groupby("Year")["P_t"].sum().astype(float)
    if 2022 not in s.index and 2021 in s.index and 2020 in s.index:
        s.loc[2022] = s.loc[2021] + (s.loc[2021] - s.loc[2020])
    return s.rename("fert_P_t")


# ---------------------------------------------------------------- 耕地面积
@lru_cache(maxsize=1)
def cropland_area_ha():
    """全球耕地面积（ha/年）。FAOSTAT RL World Cropland Area，单位 1000 ha。"""
    df = read_any(C.CROPLAND_CSV)
    sel = df[(df["Area"] == "World") & (df["Element"] == "Area") & (df["Item"] == "Cropland")]
    s = sel.groupby("Year")["Value"].sum().astype(float) * 1e3
    return s.rename("cropland_ha")


# ---------------------------------------------------------------- 畜禽存栏
@lru_cache(maxsize=1)
def livestock_world_stocks():
    """全球畜禽存栏（头）年度矩阵：行=年份，列=品种。"""
    import glob
    frames = []
    for f in sorted(glob.glob(str(C.LIVESTOCK_DIR / "*.csv"))):
        d = read_any(f)
        st = d[(d["Element"] == "Stocks") & (d["Area"] == "World")]
        if st.empty:
            continue
        item = st["Item"].iloc[0]
        v = st.groupby("Year")["Value"].sum().astype(float)
        if item in _THOUSAND_HEAD_ITEMS:
            v = v * 1e3
        frames.append(v.rename(item))
    return pd.concat(frames, axis=1).sort_index()


# 粪便排泄系数（Table S4）对应的 FAOSTAT 品种归并
EXCRETION_GROUPS = {
    "cow": ["Cattle", "Buffalo"],
    "pig": ["Swine / pigs"],
    "sheep": ["Sheep", "Goats"],
    "poultry": ["Chickens", "Ducks", "Geese", "Turkeys"],
    "rabbit": ["Rabbits and hares"],
}


def manure_excretion_p(stocks=None):
    """全球畜禽粪便 P 排泄量（吨 P/年）= Σ 头数 × κ_excretion（kg/头/年）。"""
    import params_si as P
    if stocks is None:
        stocks = livestock_world_stocks()
    out = pd.Series(0.0, index=stocks.index)
    for key, items in EXCRETION_GROUPS.items():
        coef = P.LBS["excretion_kg_head_yr"][key]
        for it in items:
            if it in stocks.columns:
                out = out + stocks[it].fillna(0) * coef
    return (out / 1e3).rename("manure_P_t")  # kg/年 → t P/年


# ---------------------------------------------------------------- 人口
@lru_cache(maxsize=1)
def population_world():
    """全球人口（人/年，1961-2022）。

    1961-2021 取 FAOSTAT OA 'Total Population - Both sexes' World 行；
    FAOSTAT 无 2022 值，用 UN WPP 2024 Estimates 表 2022 年世界人口补齐。
    """
    df = read_any(C.POP_CSV)
    sel = df[(df["Area"] == "World") & (df["Element"] == "Total Population - Both sexes")]
    s = sel.groupby("Year")["Value"].sum().astype(float) * 1e3
    if 2022 not in s.index:
        p2022, _ = population_projection_2050()
        s.loc[2022] = p2022
    return s.rename("population")


# ---------------------------------------------------------------- 磷矿生产
@lru_cache(maxsize=1)
def phosphate_rock_p_series():
    """全球磷矿产量折纯磷（吨 P/年，1998-2021 实测）。P = P2O5 × 0.4364。"""
    df = pd.read_excel(C.PR_PROD_XLSX, sheet_name="P2O5 (tons)")
    years = [c for c in df.columns if isinstance(c, int)]
    s = df[years].sum() * C.P_IN_P2O5
    s.index = [int(i) for i in s.index]
    return s.rename("pr_P_t")


# ---------------------------------------------------------------- 贸易
@lru_cache(maxsize=1)
def trade_world_yearly(which="export"):
    """全球农产品贸易纯磷年度总量（吨 P）。which: export / import。"""
    path = C.TRADE_EXP_XLSX if which == "export" else C.TRADE_IMP_XLSX
    sheet = "products_P_export_result （tons）" if which == "export" else list(pd.ExcelFile(path).sheet_names)[0]
    df = pd.read_excel(path, sheet_name=sheet)
    df.columns = [int(c) if str(c).isdigit() else c for c in df.columns]
    years = [c for c in df.columns if isinstance(c, int)]
    s = df[years].sum()
    s.index = [int(i) for i in s.index]
    return s.rename(f"trade_{which}_P_t")


# ---------------------------------------------------------------- 人口预测（2050 情景）
_POPCOL = "Total Population, as of 1 July (thousands)"
_REGCOL = "Region, subregion, country or area *"


@lru_cache(maxsize=1)
def population_projection_2050():
    """UN WPP 2024 中方案：2022（Estimates 表）与 2050（Medium variant 表）全球人口（人）。"""
    est = pd.read_excel(C.POP_PROJ, sheet_name="Estimates", header=16)
    med = pd.read_excel(C.POP_PROJ, sheet_name="Medium variant", header=16)
    p2022 = est.loc[est[_REGCOL] == "World", ["Year", _POPCOL]]
    p2022 = p2022[p2022["Year"] == 2022][_POPCOL].iloc[0] * 1e3
    p2050 = med.loc[med[_REGCOL] == "World", ["Year", _POPCOL]]
    p2050 = p2050[p2050["Year"] == 2050][_POPCOL].iloc[0] * 1e3
    return float(p2022), float(p2050)


# ---------------------------------------------------------------- 作物产量（ACS 任务1）
# 19 类作物 → FAOSTAT QCL Item 精确名（17 类）；蔬菜/瓜果与水果为关键词聚合近似
CROP_ITEMS = {
    "rice": "Rice", "wheat": "Wheat", "maize": "Maize (corn)", "barley": "Barley",
    "sorghum": "Sorghum", "millet": "Millet", "rye": "Rye", "oat": "Oats",
    "potato": "Potatoes", "sweet potato": "Sweet potatoes", "cassava": "Cassava, fresh",
    "soybean": "Soya beans", "rapeseed": "Rape or colza seed", "olive": "Olives",
    "sugar beet": "Sugar beet", "sugarcane": "Sugar cane", "seed cotton": "Seed cotton, unginned",
}
VEG_KEYWORDS = ["tomato", "onion", "shallot", "cabbage", "cucumber", "gherkin", "eggplant",
                "aubergine", "lettuce", "chicory", "garlic", "okra", "mushroom", "celery",
                "spinach", "cauliflower", "broccoli", "capsicum", "asparagus", "artichoke",
                "leek", "carrot", "turnip", "radish", "parsnip", "pumpkin", "squash",
                "watermelon", "cantaloupe", "other melon", "green bean", "beans, green",
                "peas, green", "pea, green", "chick pea, green", "lentil, green"]
FRUIT_KEYWORDS = ["banana", "plantain", "apple", "orange", "grape", "mango", "guava",
                  "mangosteen", "mandarin", "clementine", "pineapple", "pears", "pear,",
                  "peach", "nectarine", "papaya", "avocado", "kiwi", "coconut",
                  "citrus fruit", "pome fruits", "stone fruits", "berries", "cherry",
                  "persimmon", "pomegranate", "quince", "figs", "dates", "plums",
                  "apricots", "lychees", "durians", "jackfruit", "passion fruit",
                  "strawberry", "cranberries", "blueberries", "raspberries", "currants",
                  "gooseberries", "other fruits, n.e.c.", "other berries"]
_EXCLUDE_TOKENS = ["oil", "wine", "juice", "dried", "flour", "canned", "preserved",
                   "seed", "meal", "sugar", "starch", "fiber", "fibre", "tree", "nut of"]


def _match_agg(items, values, keywords):
    """按关键词聚合 FAOSTAT Item 产量（吨），排除加工副产品，避免重复计数。"""
    total = 0.0
    matched = []
    for name, v in zip(items, values):
        low = name.lower()
        if any(x in low for x in _EXCLUDE_TOKENS):
            continue
        if any(k in low for k in keywords):
            total += v
            matched.append(name)
    return total, matched


@lru_cache(maxsize=1)
def crop_world_production_2022():
    """2022 年全球 19 类作物产量（吨，鲜重）。

    17 类为 FAOSTAT 精确 Item 对应；'vegetable and melon'、'fruit' 两类
    无单一聚合 Item，采用关键词聚合近似（覆盖主要鲜食果蔬），报告中注明。
    """
    df = read_any(C.RAW_PROD_DIR / "2022.csv")
    pro = df[(df["Element"] == "Production") & (df["Area"] == "World") & (df["Unit"] == "t")]
    items = pro["Item"].tolist()
    values = pro["Value"].astype(float).tolist()
    lookup = dict(zip(items, values))
    out = {}
    for crop, item in CROP_ITEMS.items():
        out[crop] = float(lookup.get(item, 0.0))
    veg, veg_names = _match_agg(items, values, VEG_KEYWORDS)
    fruit, fruit_names = _match_agg(items, values, FRUIT_KEYWORDS)
    out["vegetable and melon"] = veg
    out["fruit"] = fruit
    return out, {"vegetable and melon": veg_names, "fruit": fruit_names}


@lru_cache(maxsize=None)
def _crop_production_year(year):
    path = C.RAW_PROD_DIR / f"{year}.csv"
    if not path.exists():
        return None
    df = read_any(path)
    pro = df[(df["Element"] == "Production") & (df["Area"] == "World") & (df["Unit"] == "t")]
    items = pro["Item"].tolist()
    values = pro["Value"].astype(float).tolist()
    lookup = dict(zip(items, values))
    out = {crop: float(lookup.get(item, 0.0)) for crop, item in CROP_ITEMS.items()}
    out["vegetable and melon"] = _match_agg(items, values, VEG_KEYWORDS)[0]
    out["fruit"] = _match_agg(items, values, FRUIT_KEYWORDS)[0]
    return out


def crop_production_series():
    """19 类作物全球产量（吨）年度矩阵，行=年份。1961-2022 逐年读取。"""
    frames = []
    for y in C.YEARS:
        q = _crop_production_year(y)
        if q is not None:
            frames.append(pd.Series(q, name=y))
    return pd.DataFrame(frames).sort_index()


if __name__ == "__main__":
    g = global_category_yearly()
    print("品类年度合计（Mt P）1961/2022：", g.loc[1961].sum(), g.loc[2022].sum())
    print("化肥 P(t) 1961/2021/2022(外推) Mt：",
          fertilizer_p_series().loc[1961] / 1e6,
          fertilizer_p_series().loc[2021] / 1e6,
          fertilizer_p_series().loc[2022] / 1e6)
    print("耕地 2022（Mha）：", cropland_area_ha().loc[2022] / 1e6)
    print("粪便 P 2022（Mt）：", manure_excretion_p().loc[2022] / 1e6)
    print("人口 2022：", population_world().loc[2022] / 1e9, "B")
    print("磷矿 P 2021（Mt）：", phosphate_rock_p_series().loc[2021] / 1e6)
    print("贸易出口 P 2022（Mt）：", trade_world_yearly("export").loc[2022] / 1e6)
    print("人口预测 2022/2050：", population_projection_2050())
    q, names = crop_world_production_2022()
    print("作物产量 2022（Mt）：", {k: round(v / 1e6, 1) for k, v in q.items()})
    print("蔬菜匹配条目数：", len(names["vegetable and melon"]), "水果：", len(names["fruit"]))
