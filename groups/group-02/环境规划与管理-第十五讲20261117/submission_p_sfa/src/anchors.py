"""补充数据接入核对（锚点表）与年度序列导出。

数据来源：codex 交付的 7 个 CSV 块（config.EXTRA）。
本模块只做“读回 -> 与模型采用值对照 -> 标注状态”，不改变原始数值；
空字段一律保留缺失，不以 0 代填。
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import config
from .params import coeff


def _read(extra_dir: Path, key: str) -> pd.DataFrame | None:
    p = Path(extra_dir) / config.EXTRA[key]
    return pd.read_csv(p) if p.exists() else None


def cumulative_rock_p(extra_dir: Path, coefficients,
                      year_min: int = 1961, year_max: int = 2022) -> dict:
    """DS140 覆盖年份的累计磷矿含磷量（Mt P）。

    DS140 仅提供 1961–1998、2021–2022，缺 1999–2020，故只能给出
    覆盖年份合计；另用可用年份实物量的最小/最大值夹逼缺口，给出区间，
    两条都标注为“未完整覆盖”，不作为 1961–2022 完整累计。
    """
    df = _read(extra_dir, "rock_ds140")
    if df is None:
        return {}
    df = df.copy()
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["rock_t"] = pd.to_numeric(df["rock_t"], errors="coerce")
    df = df[(df["year"] >= year_min) & (df["year"] <= year_max)].dropna(
        subset=["rock_t"])
    factor = coeff(coefficients, "alpha3") * coeff(coefficients, "alpha1") / 1e6
    have = set(df["year"].astype(int))
    missing = sorted(set(range(year_min, year_max + 1)) - have)
    total = float(df["rock_t"].sum() * factor)
    out = {"covered_years": len(have), "missing_years": missing,
           "partial_Mt_P": total}
    if missing:
        mass = df["rock_t"]
        out["bracket_low_Mt_P"] = total + float(mass.min()) * len(missing) * factor
        out["bracket_high_Mt_P"] = total + float(mass.max()) * len(missing) * factor
    return out


def build_anchor_table(bundle, model_notes: dict, extra_dir: Path,
                       coefficients) -> pd.DataFrame:
    """按交付文档第 6 节的锚点逐项核对，返回对照表。"""
    from .data_io import (load_fert_trade_rfn, load_grassland_ha,
                          load_livestock, load_rock_ds140, load_rock_myb,
                          load_seed_p)

    seed_1961 = load_seed_p(extra_dir, 1961)
    stock_1961 = load_livestock(extra_dir, 1961)
    grass_1961 = load_grassland_ha(extra_dir, 1961)
    trade_1961 = load_fert_trade_rfn(extra_dir, 1961)
    rock_1961 = load_rock_ds140(extra_dir, 1961)
    rock_2022 = load_rock_ds140(extra_dir, 2022)
    myb_2022 = load_rock_myb(extra_dir, 2022)

    stock = bundle.livestock or {}
    heads = stock.get("heads", {})
    manure = stock.get("manure", {})
    missing_species = stock.get("missing_species", [])

    grade = coeff(coefficients, "alpha3") * coeff(coefficients, "alpha1")
    rock_grade_2022 = (rock_2022 * grade) if rock_2022 else None
    rock_grade_1961 = (rock_1961 * grade) if rock_1961 else None

    # 2021 年 RFN 与课程肥料表（同一 FAOSTAT 域，不同发布版本）交叉核对
    rfn_2021 = load_fert_trade_rfn(extra_dir, 2021) or {}
    fert = bundle.fertilizer
    imp_course = fert["Import Quantity"]
    exp_course = fert["Export Quantity"]

    def dev(model, ref):
        if model in (None, 0) or ref in (None, 0):
            return None
        return (model / ref - 1.0) * 100.0

    proxy = bundle.grass_proxy or {}
    implied = model_notes.get("grass_uptake_kg_ha")
    if implied is None or not proxy:
        grass_check = "无隐含单产或 proxy"
    elif proxy["min"] <= implied <= proxy["max"]:
        grass_check = "模型隐含单产落在 proxy 区间内"
    else:
        grass_check = "模型隐含单产超出 proxy 区间，需复核饲料口径"

    rows = [
        {"项目": "种子磷", "单位": "Mt P",
         "1961值": seed_1961, "2022值": bundle.seed_p_mt,
         "来源": "ESB_2025", "状态": "已接入 ACS",
         "说明": "FAOSTAT 官方估计；播种面积/播种率原表为空，未反推"},
        {"项目": "猪存栏", "单位": "头",
         "1961值": stock_1961["heads"].get("pig") if stock_1961 else None,
         "2022值": heads.get("pig"), "来源": "QCL_2025", "状态": "已接入 LBS",
         "说明": "Stocks 口径（非出栏）"},
        {"项目": "牛存栏", "单位": "头",
         "1961值": stock_1961["heads"].get("cattle") if stock_1961 else None,
         "2022值": heads.get("cattle"), "来源": "QCL_2025", "状态": "已接入 LBS",
         "说明": "不含水牛"},
        {"项目": "绵羊存栏", "单位": "头",
         "1961值": stock_1961["heads"].get("sheep") if stock_1961 else None,
         "2022值": heads.get("sheep"), "来源": "QCL_2025", "状态": "已接入 LBS",
         "说明": "Stocks 口径"},
        {"项目": "山羊存栏", "单位": "头",
         "1961值": stock_1961["heads"].get("goat") if stock_1961 else None,
         "2022值": heads.get("goat"), "来源": "QCL_2025",
         "状态": "存栏已接入；粪磷缺失",
         "说明": "未指定排泄系数，粪磷留空，未套用绵羊系数"},
        {"项目": "家禽存栏", "单位": "只",
         "1961值": stock_1961["heads"].get("poultry") if stock_1961 else None,
         "2022值": heads.get("poultry"), "来源": "QCL_2025", "状态": "已接入 LBS",
         "说明": "Poultry Birds 合计，原单位千只已转只"},
        {"项目": "粪磷合计（四畜种）", "单位": "Mt P",
         "1961值": stock_1961["manure_total_Mt"] if stock_1961 else None,
         "2022值": bundle.manure_p_mt, "来源": "QCL_2025×排泄系数",
         "状态": "已接入 LBS",
         "说明": f"未含山羊（{', '.join(missing_species) or '无缺失'}），"
                 "饲料需求由该值闭合反推"},
        {"项目": "永久草地面积", "单位": "ha",
         "1961值": grass_1961, "2022值": bundle.grassland_ha,
         "来源": "RL_2026", "状态": "已接入（兑现核对）",
         "说明": "仅用于草地单产隐含值核对，不构造流量"},
        {"项目": "草地磷吸收单产", "单位": "kg P/ha/yr",
         "1961值": None, "2022值": implied,
         "来源": "Sattari_2016_Table_1（proxy）", "状态": "仅区间核对",
         "说明": f"proxy 区间 {proxy.get('min')}–{proxy.get('max')}，"
                 f"central {proxy.get('central')}；{grass_check}"},
        {"项目": "磷肥进口（养分 proxy）", "单位": "Mt P",
         "1961值": trade_1961.get("import") if trade_1961 else None,
         "2022值": (bundle.fert_trade_rfn or {}).get("import"),
         "来源": "RFN_2026", "状态": "核对用（不计入边界）",
         "说明": f"2021 RFN {rfn_2021.get('import'):.3f} vs 课程表 {imp_course:.3f}"
                 f"（偏差 {dev(rfn_2021.get('import'), imp_course):+.1f}%）"
                 if rfn_2021.get("import") and imp_course else ""},
        {"项目": "磷肥出口（养分 proxy）", "单位": "Mt P",
         "1961值": trade_1961.get("export") if trade_1961 else None,
         "2022值": (bundle.fert_trade_rfn or {}).get("export"),
         "来源": "RFN_2026", "状态": "核对用（不计入边界）",
         "说明": f"2021 RFN {rfn_2021.get('export'):.3f} vs 课程表 {exp_course:.3f}"
                 f"（偏差 {dev(rfn_2021.get('export'), exp_course):+.1f}%）；"
                 "国家求和含转口，仅作量级核对"
                 if rfn_2021.get("export") and exp_course else ""},
        {"项目": "磷矿实物量", "单位": "Mt 矿石",
         "1961值": rock_1961, "2022值": rock_2022,
         "来源": "USGS_DS140_2022", "状态": "已接入（交叉核对）",
         "说明": "实物量 proxy，不能直接当纯磷"},
        {"项目": "磷矿含磷（品位法）", "单位": "Mt P",
         "1961值": rock_grade_1961, "2022值": rock_grade_2022,
         "来源": "DS140×31%×0.4364", "状态": "已接入（回退口径）",
         "说明": "品位系数来自 SI Table S3 alpha3"},
        {"项目": "磷矿含磷（同版本 P2O5）", "单位": "Mt P",
         "1961值": None, "2022值": (myb_2022 or {}).get("p_Mt"),
         "来源": "USGS_MYB2022_T10", "状态": "已接入 PMS（优先口径）",
         "说明": (f"与品位法偏差 {dev(myb_2022['p_Mt'], rock_grade_2022):+.1f}%；"
                 "矿石量与 P2O5 同表，未跨版本拼接")
                 if myb_2022 and rock_grade_2022 else ""},
        {"项目": "模型采用磷矿观测输入", "单位": "Mt P",
         "1961值": None, "2022值": model_notes.get("rock_obs_Mt"),
         "来源": model_notes.get("rock_basis", ""), "状态": "进入 PMS",
         "说明": f"缺口残差 {model_notes.get('rock_gap_Mt', 0):.3f} Mt P"},
    ]

    cum = cumulative_rock_p(extra_dir, coefficients)
    if cum:
        rows.append({
            "项目": "1961–2022 累计磷矿开采（覆盖年份）", "单位": "Mt P",
            "1961值": None, "2022值": cum["partial_Mt_P"],
            "来源": "USGS_DS140_2022",
            "状态": f"部分覆盖 {cum['covered_years']}/62 年",
            "说明": f"缺 {len(cum['missing_years'])} 年（1999–2020）；"
                    f"按可用年份实物量最小/最大值夹逼的上下界 "
                    f"{cum.get('bracket_low_Mt_P', float('nan')):.0f}–"
                    f"{cum.get('bracket_high_Mt_P', float('nan')):.0f} Mt P；"
                    "未与论文 1153 Mt P 直接比较",
        })

    df = pd.DataFrame(rows)

    def clean(v):
        if isinstance(v, (int, float)) and pd.notna(v):
            v = float(v)
            if abs(v) >= 1000:
                return str(int(round(v)))
            return f"{v:.4f}".rstrip("0").rstrip(".")
        return v

    for col in ("1961值", "2022值"):
        df[col] = df[col].map(clean).astype(object).where(df[col].notna(), "—")
    return df


def build_series(extra_dir: Path) -> pd.DataFrame:
    """把补充数据按年份拼成一张审计序列（缺失保持空值）。"""
    seed = _read(extra_dir, "seed_p")
    stock = _read(extra_dir, "livestock")
    grass = _read(extra_dir, "grassland")
    trade = _read(extra_dir, "fert_trade_rfn")
    rock = _read(extra_dir, "rock_ds140")
    myb = _read(extra_dir, "rock_myb")
    if seed is None:
        return pd.DataFrame()

    out = seed[["year", "seed_p_Mt"]].copy()
    out["year"] = pd.to_numeric(out["year"], errors="coerce")
    out = out.rename(columns={"seed_p_Mt": "种子磷(Mt P)"}).set_index("year")

    if stock is not None:
        s = stock.copy()
        s["year"] = pd.to_numeric(s["year"], errors="coerce")
        s["manure_p_Mt"] = pd.to_numeric(s["manure_p_Mt"], errors="coerce")
        piv = s.pivot_table(index="year", columns="species",
                            values="manure_p_Mt", aggfunc="first")
        out["粪磷合计(四畜种,Mt P)"] = piv.sum(axis=1, min_count=1)
        out["山羊粪磷(Mt P)"] = piv.get("goat")

    if grass is not None:
        g = grass[["year", "grassland_area_ha"]].copy()
        g["year"] = pd.to_numeric(g["year"], errors="coerce")
        out["永久草地面积(ha)"] = g.set_index("year")["grassland_area_ha"]

    if trade is not None:
        t = trade.copy()
        t["year"] = pd.to_numeric(t["year"], errors="coerce")
        t["p_Mt"] = pd.to_numeric(t["p_Mt"], errors="coerce")
        piv = t.pivot_table(index="year", columns="flow", values="p_Mt",
                            aggfunc="first")
        out["磷肥进口proxy(Mt P)"] = piv.get("import")
        out["磷肥出口proxy(Mt P)"] = piv.get("export")

    if rock is not None:
        r = rock[["year", "rock_t"]].copy()
        r["year"] = pd.to_numeric(r["year"], errors="coerce")
        out["磷矿实物量(Mt)"] = r.set_index("year")["rock_t"] / 1e6

    if myb is not None:
        m = myb[["year", "p_Mt"]].copy()
        m["year"] = pd.to_numeric(m["year"], errors="coerce")
        out["MYB磷矿含磷(Mt P)"] = m.set_index("year")["p_Mt"]

    return out.sort_index()
