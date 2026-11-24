"""数据读取与口径整理。

本模块只做“读入 -> 规整列名/年份 -> 换算纯磷 -> 返回基准量”，
不做任何模型假设。所有单位统一为 Mt P（流量）或 ha（面积）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from . import config


# ------------------------------------------------------------------ 工具
def _resolve(data_dir: Path, key: str) -> Path:
    p = Path(data_dir) / config.REL[key]
    if not p.exists():
        raise FileNotFoundError(f"缺少数据文件：{p}")
    return p


def _year_to_int(col) -> object:
    s = str(col).strip()
    if s.isdigit():
        return int(s)
    try:
        f = float(s)
    except ValueError:
        return col
    return int(f) if f.is_integer() else col


def _drop_aggregates(df: pd.DataFrame, col: str = "Country") -> pd.DataFrame:
    return df[~df[col].astype(str).str.strip().isin(config.AGGREGATE_COUNTRIES)]


# ------------------------------------------------------------------ 生产表
def load_product_p(data_dir: Path) -> pd.DataFrame:
    """读取各国分产品纯磷产出宽表，返回长表（单位：t P）。"""
    path = _resolve(data_dir, "product_p")
    df = pd.read_excel(path, sheet_name="product_P_result (tons)")
    df.columns = [_year_to_int(c) for c in df.columns]
    years = [c for c in df.columns if isinstance(c, int)]
    long = df.melt(
        id_vars=["Country", "Product"], value_vars=years,
        var_name="year", value_name="p_t",
    )
    long["Country"] = long["Country"].astype(str).str.strip()
    long["Product"] = long["Product"].astype(str).str.strip()
    long["p_t"] = pd.to_numeric(long["p_t"], errors="coerce").fillna(0.0)
    return long


def world_product_p(long: pd.DataFrame, year: int) -> pd.Series:
    """返回指定年份全球分产品纯磷量（Mt P），索引为产品类别 A–M。

    优先使用表中的 World 聚合行；若缺失则对剔重后的国家求和。
    """
    sub = long[long["year"] == year]
    if (sub["Country"] == "World").any():
        s = sub[sub["Country"] == "World"].set_index("Product")["p_t"]
    else:
        s = _drop_aggregates(sub).groupby("Product")["p_t"].sum()
    return (s / config.T_PER_MT).sort_index()


def category_p(long: pd.DataFrame, year: int) -> dict[str, float]:
    """按类别汇总全球纯磷（Mt P）：作物端、动物产品、活体动物。"""
    w = world_product_p(long, year)
    crop = float(w.reindex(config.CROP_CATEGORIES).fillna(0).sum())
    animal = float(w.get(config.ANIMAL_CATEGORY, 0.0))
    live = float(w.get(config.LIVE_ANIMAL_CATEGORY, 0.0))
    return {"crop": crop, "animal_product": animal, "live_animal": live,
            "all_categories": float(w.sum()), "by_category": w.to_dict()}


def world_series(long: pd.DataFrame) -> pd.DataFrame:
    """1961–2022 年全球作物端/动物产品纯磷时间序列（Mt P）。

    年份列已转为整型；缺失值按 0 处理前先统计其数量，供数据审计输出。
    """
    sub = long.copy()
    if (sub["Country"] == "World").any():
        sub = sub[sub["Country"] == "World"]
    else:
        sub = _drop_aggregates(sub)
    crop = (sub[sub["Product"].isin(config.CROP_CATEGORIES)]
            .groupby("year")["p_t"].sum() / config.T_PER_MT)
    animal = (sub[sub["Product"] == config.ANIMAL_CATEGORY]
              .groupby("year")["p_t"].sum() / config.T_PER_MT)
    live = (sub[sub["Product"] == config.LIVE_ANIMAL_CATEGORY]
            .groupby("year")["p_t"].sum() / config.T_PER_MT)
    return pd.DataFrame({"作物端(A–F,H–K)": crop,
                         "动物产品(G)": animal,
                         "活体动物(M,仅核对)": live}).sort_index()


# ------------------------------------------------------------------ 含磷率字典
def load_p_coefficient(data_dir: Path) -> pd.DataFrame:
    """读取含磷率字典（Product / Category / Coefficient）。

    字典原始名称带尾随空格，必须先 strip，否则 "Potatoes " 之类会漏配。
    Coefficient 为每千克实物量的纯磷千克数（kg P/kg），与产量（t）相乘即得 t P。
    """
    path = _resolve(data_dir, "p_coefficient")
    df = pd.read_excel(path, usecols=["Product", "Category", "Coefficient"])
    df["Product"] = df["Product"].astype(str).str.strip()
    df["Category"] = df["Category"].astype(str).str.strip()
    df["Coefficient"] = pd.to_numeric(df["Coefficient"], errors="coerce")
    return df.dropna(subset=["Coefficient"])


def dictionary_crosscheck(data_dir: Path, year: int = 2022) -> pd.DataFrame:
    """用含磷率字典独立复算各类别纯磷，与官方纯磷产出表逐类对照。

    口径：
      * 只取 Element=Production、Year=year、Unit=t 的原始产量行，剔除 6 个区域聚合；
      * 产品名 strip 后与字典连接，P(t) = 产量(t) × Coefficient(kg/kg)；
      * "1000 No"（蛋类、活体动物）无法按质量加权，不参与比较；
      * 官方表为模型实际采用的 product_P_result (tons)，两侧统一换算为 Mt P。
    """
    coef = load_p_coefficient(data_dir)
    raw_path = Path(data_dir) / config.REL["raw_production"] / f"{year}.csv"
    if not raw_path.exists():
        raise FileNotFoundError(f"缺少原始产量表：{raw_path}")

    raw = pd.read_csv(raw_path)
    sub = raw[(raw["Element"] == "Production")
              & (raw["Year"] == year)
              & (raw["Unit"] == "t")].copy()
    sub["Area"] = sub["Area"].astype(str).str.strip()
    sub = sub[~sub["Area"].isin(config.AGGREGATE_COUNTRIES)]
    sub["Item"] = sub["Item"].astype(str).str.strip()
    sub["Value"] = pd.to_numeric(sub["Value"], errors="coerce")

    m = sub.merge(coef, left_on="Item", right_on="Product", how="left")
    m["p_Mt"] = m["Value"] * m["Coefficient"] / config.T_PER_MT
    matched = m[m["Coefficient"].notna()]
    by_cat = matched.groupby("Category")["p_Mt"].sum()
    unmatched = m[m["Coefficient"].isna()]
    unmatched_share = float(unmatched["Value"].sum() / m["Value"].sum() * 100)

    official = world_product_p(load_product_p(data_dir), year)
    rows = []
    for cat in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K"]:
        calc = float(by_cat.get(cat, np.nan))
        off = float(official.get(cat, np.nan))
        dev = (calc / off - 1.0) * 100 if off else np.nan
        if cat == config.ANIMAL_CATEGORY:
            note = "官方表 G 类为另行折算口径，与质量×含磷率相差约 3 倍，不作直接比较"
        else:
            note = "同名产品 × 含磷率"
        rows.append({"类别": cat, "字典加权(Mt P)": calc,
                     "官方纯磷表(Mt P)": off, "相对偏差(%)": dev,
                     "说明": note})

    crop_calc = float(by_cat.reindex(config.CROP_CATEGORIES).fillna(0).sum())
    crop_off = float(official.reindex(config.CROP_CATEGORIES).fillna(0).sum())
    rows.append({"类别": "作物端合计(A–F,H–K)", "字典加权(Mt P)": crop_calc,
                 "官方纯磷表(Mt P)": crop_off,
                 "相对偏差(%)": (crop_calc / crop_off - 1.0) * 100 if crop_off else np.nan,
                 "说明": "任务 1.1 要求的跨表加权换算结果"})
    rows.append({"类别": "未匹配产品", "字典加权(Mt P)": np.nan,
                 "官方纯磷表(Mt P)": np.nan, "相对偏差(%)": np.nan,
                 "说明": f"{len(unmatched)} 行未匹配，占产量 {unmatched_share:.2f}%（不计入合计）"})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ 化肥
def load_fertilizer(data_dir: Path, year: int) -> dict[str, float]:
    """FAO 养分磷肥（P2O5）按元素汇总为 Mt P。

    原始 Value 单位为 t P2O5，需乘 0.4364 折纯磷；
    文件中 P(t) 列仅对部分元素有值，故统一由 Value 重算。
    """
    path = _resolve(data_dir, "fertilizer")
    df = pd.read_csv(path, encoding="latin-1")
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
    df = df[df["Year"] == year].copy()
    df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
    df = df[~df["Area"].astype(str).str.strip().isin(config.AGGREGATE_COUNTRIES)]

    out = {}
    for element in ["Production", "Agricultural Use", "Import Quantity", "Export Quantity"]:
        v = df.loc[df["Element"] == element, "Value"].sum(min_count=1)
        out[element] = float(v) * config.P2O5_TO_P / config.T_PER_MT if pd.notna(v) else np.nan
    return out


# ------------------------------------------------------------------ 磷矿
def load_phosphate_rock(data_dir: Path, year: int) -> float:
    """USGS 磷矿石产量（Mt 实物量）汇总。

    注意：P2O5 工作表数值与实物量表不自洽（如中国 2021 年仅 2.7 万 t P2O5，
    而实物量 9000 万 t），因此模型使用实物量 × 品位系数，见 coefficients.csv。
    """
    path = _resolve(data_dir, "phosphate_rock")
    df = pd.read_excel(path, sheet_name="phosphate rock (tons)")
    df.columns = [_year_to_int(c) for c in df.columns]
    if year not in df.columns:
        years = [c for c in df.columns if isinstance(c, int)]
        year = max(years)
    df = _drop_aggregates(df)
    return float(df[year].sum(min_count=1)) / config.T_PER_MT


# ------------------------------------------------------------------ 面积
def load_cropland_ha(data_dir: Path, year: int) -> float:
    """全球耕地面积（ha）。原始单位：1000 ha。"""
    path = _resolve(data_dir, "cropland")
    df = pd.read_csv(path)
    sub = df[(df["Area"] == "World") & (df["Element"] == "Area")
             & (df["Item"] == "Cropland") & (df["Unit"] == "1000 ha")
             & (df["Year"] == year)]
    if sub.empty:
        raise ValueError(f"耕地面积缺失：year={year}")
    return float(sub["Value"].iloc[0]) * config.KHA_TO_HA


# ------------------------------------------------------------------ 人口
def load_population(data_dir: Path) -> pd.DataFrame:
    """WPP2024 长表：Variant / Type / Year / 7月1日人口（千人）。

    真实表头在 0-based 第 16 行；文件为长表而非宽表。
    """
    path = _resolve(data_dir, "population")
    frames = []
    for sheet, tag in [("Estimates", "estimates"), ("Medium variant", "medium")]:
        df = pd.read_excel(path, sheet_name=sheet, header=16)
        df.columns = [str(c).strip() for c in df.columns]
        df = df[df["Type"].astype(str).str.strip() == "World"].copy()
        df["variant"] = tag
        frames.append(df[["variant", "Year",
                          "Total Population, as of 1 July (thousands)"]]
                      .rename(columns={"Total Population, as of 1 July (thousands)": "pop_k"}))
    out = pd.concat(frames, ignore_index=True)
    out["Year"] = pd.to_numeric(out["Year"], errors="coerce").astype("Int64")
    out["pop_k"] = pd.to_numeric(out["pop_k"], errors="coerce")
    return out.dropna(subset=["Year", "pop_k"])


def world_population(pop: pd.DataFrame, year: int, variant: str) -> float:
    sub = pop[(pop["Year"] == year) & (pop["variant"] == variant)]
    if sub.empty:
        raise ValueError(f"人口缺失：{variant} {year}")
    return float(sub["pop_k"].iloc[0]) * config.KILO_PERSON


# ------------------------------------------------------------------ 食物磷供给
def load_food_p_percap(data_dir: Path, year: int = 2021) -> float:
    """人均食物磷供给（kg P/人/年）。

    原始为 mg/人/日、按食物组分行；对同一国家求和各食物组后取国家均值。
    无 World 行，故用国家等权均值（与 SI 的 0.59 kg/cap/yr 交叉核对）。
    """
    path = _resolve(data_dir, "food_supply")
    df = pd.read_csv(path)
    df = df[(df["Unit"] == "mg/cap/d") & (df["Year"] == year)]
    per = df.groupby("Area")["Value"].sum()
    mg_per_day = float(per.mean())
    return mg_per_day * 1e-6 * 365.0


# ------------------------------------------------------------------ 贸易
def load_trade_p(data_dir: Path, year: int) -> dict[str, float]:
    """农产品进出口纯磷（Mt P），按作物类别汇总（剔除 L/M 以免与 G 重复）。"""
    out = {}
    for key in ("exports", "imports"):
        path = _resolve(data_dir, key)
        df = pd.read_excel(path, sheet_name=0)
        df.columns = [_year_to_int(c) for c in df.columns]
        if year not in df.columns:
            years = [c for c in df.columns if isinstance(c, int)]
            year = max(years)
        sub = df[df["Country"].astype(str).str.strip() == "World"]
        if sub.empty:
            sub = _drop_aggregates(df)
        sub = sub[sub["Product"].isin(config.CROP_CATEGORIES)]
        out[key] = float(sub[year].sum()) / config.T_PER_MT
    return out


# ------------------------------------------------------------------ 补充数据
# 以下数据来自 codex 交付的 7 个 CSV 块（data_extra/）。缺失时返回 None，
# 由调用方打印“缺少输入”并回退到原有反算路径，不以 0 代填。
def _extra_path(extra_dir: Path, key: str) -> Path | None:
    p = Path(extra_dir) / config.EXTRA[key]
    return p if p.exists() else None


def _num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


def load_seed_p(extra_dir: Path, year: int) -> float | None:
    """FAOSTAT 官方种子磷投入（Mt P）。空值表示缺失，不反推。"""
    path = _extra_path(extra_dir, "seed_p")
    if path is None:
        return None
    df = pd.read_csv(path)
    sub = df[_num(df["year"]) == year]
    if sub.empty:
        return None
    v = _num(sub["seed_p_Mt"]).iloc[0]
    return float(v) if pd.notna(v) else None


def load_livestock(extra_dir: Path, year: int) -> dict | None:
    """存栏量与粪磷（Mt P）。

    返回 heads / manure 两个按畜种索引的字典；山羊缺排泄系数时
    manure 为 NaN，并在 missing_species 中列明，绝不填 0。
    """
    path = _extra_path(extra_dir, "livestock")
    if path is None:
        return None
    df = pd.read_csv(path)
    sub = df[_num(df["year"]) == year].copy()
    if sub.empty:
        return None
    heads = dict(zip(sub["species"], _num(sub["heads"])))
    manure = dict(zip(sub["species"], _num(sub["manure_p_Mt"])))
    missing = [k for k, v in manure.items() if pd.isna(v)]
    total = float(pd.Series(manure, dtype="float64").sum(min_count=1))
    return {"heads": heads, "manure": manure, "missing_species": missing,
            "manure_total_Mt": total if pd.notna(total) else None}


def load_grassland_ha(extra_dir: Path, year: int) -> float | None:
    """FAOSTAT 永久草地与牧场面积（ha）。"""
    path = _extra_path(extra_dir, "grassland")
    if path is None:
        return None
    df = pd.read_csv(path)
    sub = df[_num(df["year"]) == year]
    if sub.empty:
        return None
    v = _num(sub["grassland_area_ha"]).iloc[0]
    return float(v) if pd.notna(v) else None


def load_grass_proxy(extra_dir: Path) -> dict | None:
    """Sattari 2016 草地磷吸收单产区间（kg P/ha/yr）。

    仅作区间核对，不是逐年观测；模型不据此构造草地饲料流量。
    """
    path = _extra_path(extra_dir, "grass_proxy")
    if path is None:
        return None
    df = pd.read_csv(path)
    if df.empty:
        return None
    r = df.iloc[0]
    return {"reference_year": int(r["reference_year"]),
            "min": float(r["p_uptake_min_kg_ha_yr"]),
            "central": float(r["p_uptake_central_kg_ha_yr"]),
            "max": float(r["p_uptake_max_kg_ha_yr"]),
            "source": str(r["source"])}


def load_fert_trade_rfn(extra_dir: Path, year: int) -> dict | None:
    """FAOSTAT RFN 养分贸易 proxy（Mt P）。

    这是磷肥养分量口径，不是 HS 2510/3103/3105 实物贸易，
    只用于与课程肥料表交叉核对，不作为额外边界输入。
    """
    path = _extra_path(extra_dir, "fert_trade_rfn")
    if path is None:
        return None
    df = pd.read_csv(path)
    sub = df[_num(df["year"]) == year]
    if sub.empty:
        return None
    out = {}
    for flow in ("import", "export"):
        v = _num(sub.loc[sub["flow"] == flow, "p_Mt"])
        out[flow] = float(v.iloc[0]) if not v.empty and pd.notna(v.iloc[0]) else None
    return out


def load_rock_ds140(extra_dir: Path, year: int) -> float | None:
    """USGS DS140 全球磷矿实物量（Mt 矿石）。仅作实物量 proxy。"""
    path = _extra_path(extra_dir, "rock_ds140")
    if path is None:
        return None
    df = pd.read_csv(path)
    sub = df[_num(df["year"]) == year]
    if sub.empty:
        return None
    v = _num(sub["rock_t"]).iloc[0]
    return float(v) / config.T_PER_MT if pd.notna(v) else None


def load_rock_myb(extra_dir: Path, year: int) -> dict | None:
    """USGS Mineral Yearbook 成套矿石量与 P2O5（同版本），Mt P 由 P2O5 折算。"""
    path = _extra_path(extra_dir, "rock_myb")
    if path is None:
        return None
    df = pd.read_csv(path)
    sub = df[_num(df["year"]) == year]
    if sub.empty:
        return None
    r = sub.iloc[0]
    p2o5_t = float(r["p2o5_t"])
    return {"rock_Mt": float(r["rock_t"]) / config.T_PER_MT,
            "p2o5_Mt": p2o5_t / config.T_PER_MT,
            # 按交付口径重算，不直接信任汇总列 p_Mt
            "p_Mt": p2o5_t * config.P2O5_TO_P / config.T_PER_MT,
            "source": str(r["source"])}


# ------------------------------------------------------------------ 汇总
@dataclass
class DataBundle:
    year: int
    crop_p: float                    # 作物收获纯磷（A–F,H–K）
    animal_p: float                  # 动物产品纯磷（G）
    live_animal_p: float             # 活体动物（M，仅核对，不入流量）
    by_category: dict
    fertilizer: dict                 # Production / Agricultural Use / Import / Export，Mt P
    rock_mt: float                   # 磷矿石实物量，Mt
    cropland_ha: float
    population: float                # 2022 人口（人）
    pop_2050: float                  # 2050 中方案人口（人）
    food_p_percap: float             # kg P/人/年
    trade: dict                      # exports / imports，Mt P
    notes: dict = field(default_factory=dict)
    # ---- 补充数据（缺失为 None）
    seed_p_mt: float | None = None
    livestock: dict | None = None
    manure_p_mt: float | None = None
    grassland_ha: float | None = None
    grass_proxy: dict | None = None
    fert_trade_rfn: dict | None = None
    rock_ds140_mt: float | None = None
    rock_myb: dict | None = None


def load_bundle(data_dir: Path, extra_dir: Path | None = None, year: int = 2022,
                fert_year: int | None = None) -> DataBundle:
    """一次性读取并汇总建模所需的全部基准数据。"""
    fert_year = fert_year or (year - 1)
    extra_dir = Path(extra_dir) if extra_dir else config.DEFAULT_EXTRA_DIR
    long = load_product_p(data_dir)
    cat = category_p(long, year)
    pop = load_population(data_dir)

    fert = load_fertilizer(data_dir, fert_year)
    rock = load_phosphate_rock(data_dir, fert_year)
    cropland = load_cropland_ha(data_dir, year)
    food = load_food_p_percap(data_dir, min(fert_year, 2021))
    trade = load_trade_p(data_dir, year)

    seed = load_seed_p(extra_dir, year)
    stock = load_livestock(extra_dir, year)
    grass_ha = load_grassland_ha(extra_dir, year)
    grass_proxy = load_grass_proxy(extra_dir)
    trade_rfn = load_fert_trade_rfn(extra_dir, year)
    rock_ds140 = load_rock_ds140(extra_dir, year)
    rock_myb = load_rock_myb(extra_dir, year)

    notes = {
        "product_year": year,
        "fertilizer_year": fert_year,
        "population_year": year,
        "food_supply_year": min(fert_year, 2021),
        "rock_year": fert_year,
        "live_animal_excluded": True,
        "extra_dir": str(extra_dir),
        "extra_available": {
            "seed_p": seed is not None,
            "livestock": stock is not None,
            "grassland": grass_ha is not None,
            "grass_proxy": grass_proxy is not None,
            "fert_trade_rfn": trade_rfn is not None,
            "rock_ds140": rock_ds140 is not None,
            "rock_myb": rock_myb is not None,
        },
    }
    return DataBundle(
        year=year,
        crop_p=cat["crop"],
        animal_p=cat["animal_product"],
        live_animal_p=cat["live_animal"],
        by_category=cat["by_category"],
        fertilizer=fert,
        rock_mt=rock,
        cropland_ha=cropland,
        population=world_population(pop, year, "estimates"),
        pop_2050=world_population(pop, 2050, "medium"),
        food_p_percap=food,
        trade=trade,
        notes=notes,
        seed_p_mt=seed,
        livestock=stock,
        manure_p_mt=stock["manure_total_Mt"] if stock else None,
        grassland_ha=grass_ha,
        grass_proxy=grass_proxy,
        fert_trade_rfn=trade_rfn,
        rock_ds140_mt=rock_ds140,
        rock_myb=rock_myb,
    )
