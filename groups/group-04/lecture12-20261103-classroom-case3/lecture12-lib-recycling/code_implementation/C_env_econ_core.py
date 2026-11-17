# -*- coding: utf-8 -*-
"""
C_env_econ_core.py —— C 模块“环境经济与决策”（汇报稿第 16—22 页）共用模型

【AI 辅助编程说明】
  Prompt 摘要："把汇报稿第 16—22 页的 LCA / TEA / 帕累托 / 财务 / 敏感性数值固化为可复现代码，
   20,000 t/a 进料按 4,000 t 梯次 + 16,000 t 再生分流；LCA/TEA 单吨指标按再生链核算，
   财务年度量按 20,000 t 全量口径（含梯次，按同单吨毛利简化），并保留 16,000 t 再生线口径备查；
    所有脚本共用同一套参数与函数，结果写入 data_cohort/*.json / *.csv 供 C_figures.py 绘图。
  人工校验：①拐点方案 GWP 1,140.7 kg CO₂e/t、水 8.80 m³/t、LCOR −5,726 元/t 与汇报稿一致；
  ②CAPEX 7.20 亿元按 80:20 分摊（再生线 5.76 亿元、梯次线 1.44 亿元），保证“每吨指标”不随口径漂移；
  ③财务页按 20,000 t/a 满负荷计，NPV 11.24 亿元、静态回收期 3.8 年；再生链 16,000 t 口径 NPV 9.00 亿元。

口径与边界
  · 全园进料 20,000 t/a = 4,000 t 梯次（SOH>80%）+ 16,000 t 再生（SOH<80%，80%）。
  · 功能单位：1 t 进入再生链的退役电池（LFP 60 / NMC811 35 / NCA 5）≈ 0.064 t Li₂CO₃ 当量。
  · 边界：摇篮到大门（收集运输—拆解分选—三条精炼路线—盐类／正极粉出厂）。
  · LCOR 负值 = 净收益；MAC 负值 = 减碳同时盈利；财务为税前无杠杆现金流。
"""
import json
import os
from math import inf

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
DATA = os.path.join(PROJ, "data_cohort")
FIG = os.path.join(PROJ, "figures_output")
os.makedirs(DATA, exist_ok=True)
os.makedirs(FIG, exist_ok=True)

with open(os.path.join(DATA, "ABC_parameters.json"), encoding="utf-8") as fh:
    P = json.load(fh)

FEED, PROC, LCA_T, TEA = P["feedstock"], P["process"], P["lca"], P["tea"]
SHARE, COMP, ELEM = FEED["share"], FEED["composition"], FEED["active_element_fraction"]
PRE, ROUTES = PROC["pretreatment"], PROC["routes"]

# ---------------- 产能口径（梯次 + 再生） ----------------
CAP_TOTAL = int(P["_meta"]["design_capacity_t_cells_per_year"])   # 20,000 t/a 进料
CASCADE_T = int(CAP_TOTAL * 0.20)                                  # 4,000 t/a 梯次
REGEN_T = CAP_TOTAL - CASCADE_T                                    # 16,000 t/a 再生
CAPEX_TOTAL = float(TEA["capex_yuan"])                             # 7.20 亿元
CAPEX_REGEN = CAPEX_TOTAL * REGEN_T / CAP_TOTAL                    # 5.76 亿元
CAPEX_CASCADE = CAPEX_TOTAL - CAPEX_REGEN                          # 1.44 亿元
FIXED_LABOR_ENV = (TEA["labor_yuan_per_t"] + TEA["env_cost_yuan_per_t"]) * REGEN_T
FULL_Q = CAP_TOTAL                                                    # 20,000 t/a 全量口径
FULL_CAPEX = CAPEX_TOTAL                                              # 7.20 亿元
FULL_FIXED = (TEA["labor_yuan_per_t"] + TEA["env_cost_yuan_per_t"]) * CAP_TOTAL

WACC, YEARS = TEA["wacc"], TEA["life_years"]
CRF = WACC * (1 + WACC) ** YEARS / ((1 + WACC) ** YEARS - 1)        # 0.10185
AF = ((1 + WACC) ** YEARS - 1) / (WACC * (1 + WACC) ** YEARS)       # 9.8181

LI2CO3_PER_LI = PROC["li2co3_per_li"]        # 5.32
FEPO4_PER_LFP = 0.59                         # FePO₄／LiFePO₄ × 回收率
RC_SHARE_NMC = 0.30                          # NMC/NCA 走还原焙烧的配比
DIRECT_CAP = PROC["direct_suitability_cap"]  # 直再适用性上限 60%
REA_CO2 = sum(LCA_T["reagents"][k] * LCA_T["reagents"]["kg_co2e_per_kg"][k]
              for k in ("H2SO4", "NaOH", "Na2CO3", "H2O2"))
PRIMARY_GWP = LCA_T["primary"]["co2_kg_per_t"]
PRIMARY_WATER = LCA_T["primary"]["water_m3_per_t"]
PRIMARY_CASH = 65000 * 0.0861                # 原生精炼现金成本（元/t 电池），MAC 对照基准

KNEE_D, KNEE_G = 0.60, 0.55                  # 拐点方案：直再 60%、绿电 55%


# ---------------- 单吨再生链模型 ----------------
def simulate(direct_share_lfp=KNEE_D, rc_share=None):
    """返回 1 t 进入再生链的退役电池的物料产出、能耗、水耗与回收率"""
    rc_share = RC_SHARE_NMC if rc_share is None else rc_share
    li_in = sum(SHARE[k] * COMP[k]["active"] * ELEM[k]["Li"] for k in SHARE)
    lfp_act = SHARE["LFP"] * COMP["LFP"]["active"]
    lfp_li = lfp_act * ELEM["LFP"]["Li"]
    ni_in = (SHARE["NMC811"] * COMP["NMC811"]["active"] * ELEM["NMC811"]["Ni"] +
             SHARE["NCA"] * COMP["NCA"]["active"] * ELEM["NCA"]["Ni"])
    co_in = (SHARE["NMC811"] * COMP["NMC811"]["active"] * ELEM["NMC811"]["Co"] +
             SHARE["NCA"] * COMP["NCA"]["active"] * ELEM["NCA"]["Co"])
    mn_in = SHARE["NMC811"] * COMP["NMC811"]["active"] * ELEM["NMC811"]["Mn"]
    cu_in = sum(SHARE[k] * COMP[k]["Cu"] for k in SHARE)
    al_in = sum(SHARE[k] * COMP[k]["Al"] for k in SHARE)

    hy, rc, dr = ROUTES["Hy"], ROUTES["RC_Hy"], ROUTES["Direct"]
    lfp_lce = lfp_li * (1 - direct_share_lfp) * hy["Li"]
    lfp_pw = lfp_li * direct_share_lfp * dr["Li"]
    other = (li_in - lfp_li) * ((1 - rc_share) * hy["Li"] + rc_share * rc["Li"])
    li_rec = lfp_lce + lfp_pw + other
    nico_rec = (ni_in + co_in + mn_in) * ((1 - rc_share) * hy["NiCoMn"] + rc_share * rc["NiCoMn"])

    e_lfp = direct_share_lfp * dr["energy_GJ_per_t"] + (1 - direct_share_lfp) * hy["energy_GJ_per_t"]
    e_nmc = (1 - rc_share) * hy["energy_GJ_per_t"] + rc_share * rc["energy_GJ_per_t"]
    energy = SHARE["LFP"] * e_lfp + (SHARE["NMC811"] + SHARE["NCA"]) * e_nmc
    th = (SHARE["LFP"] * (direct_share_lfp * dr["thermal_share"] + (1 - direct_share_lfp) * hy["thermal_share"]) +
          (SHARE["NMC811"] + SHARE["NCA"]) * ((1 - rc_share) * hy["thermal_share"] + rc_share * rc["thermal_share"]))
    w = (SHARE["LFP"] * (direct_share_lfp * dr["water_m3_per_t"] + (1 - direct_share_lfp) * hy["water_m3_per_t"]) +
         (SHARE["NMC811"] + SHARE["NCA"]) * ((1 - rc_share) * hy["water_m3_per_t"] + rc_share * rc["water_m3_per_t"]))
    k = (1 - rc_share) * hy["NiCoMn"] + rc_share * rc["NiCoMn"]
    return {
        "li_in_t": li_in, "li_rec_t": li_rec, "li_recovery": li_rec / li_in,
        "nico_recovery": nico_rec / (ni_in + co_in + mn_in),
        "lce_t": (lfp_lce + other) * LI2CO3_PER_LI,
        "powder_t": lfp_act * direct_share_lfp * 0.97,
        "fepo4_t": lfp_act * (1 - direct_share_lfp) * FEPO4_PER_LFP,
        "ni_t": ni_in * k, "co_t": co_in * k, "mn_t": mn_in * k,
        "cu_t": cu_in * PRE["copper_al_recovery"], "al_t": al_in * PRE["copper_al_recovery"],
        "black_mass_t": (SHARE["LFP"] * COMP["LFP"]["active"] + (SHARE["NMC811"] * COMP["NMC811"]["active"] +
                        SHARE["NCA"] * COMP["NCA"]["active"]) + sum(SHARE[k] * COMP[k]["graphite"] for k in SHARE)),
        "energy_gj": energy, "heat_gj": energy * th,
        "electric_kwh": energy * (1 - th) / 0.0036 + PRE["electricity_kwh_per_t"],
        "water_m3": w + PRE["water_m3_per_t"],
    }


def grid_factor(g, grid_ef=None, grid_water=None):
    """绿电比例 g 下的等效电网排放因子与耗水强度（绿电残余因子另计）"""
    ef_g = LCA_T["grid_ef"]["base"] if grid_ef is None else grid_ef
    gw_g = LCA_T["grid_water_m3_per_kwh"]["base"] if grid_water is None else grid_water
    ef = g * LCA_T["green_residual_ef"] + (1 - g) * ef_g
    gw = g * LCA_T["green_water_m3_per_kwh"] + (1 - g) * gw_g
    return ef, gw


def lca(f, g=KNEE_G, grid_ef=None, grid_water=None):
    """摇篮到大门：电力 + 天然气 + 试剂上游 + 收集运输；水耗含电力耗水"""
    ef, gw = grid_factor(g, grid_ef, grid_water)
    electric = f["electric_kwh"] * ef
    heat = f["heat_gj"] * LCA_T["natural_gas_kg_co2e_per_GJ"]
    reagent = REA_CO2
    transport = LCA_T["transport"]["distance_km"] * LCA_T["transport"]["kg_co2e_per_t_km"]
    gwp = electric + heat + reagent + transport
    water = f["water_m3"] + f["electric_kwh"] * gw
    return {"gwp_kg_per_t": gwp, "water_m3_per_t": water, "ef": ef, "grid_water": gw,
            "breakdown": {"electricity": electric, "heat": heat, "reagent": reagent, "transport": transport}}


# ---------------- 技术经济模型 ----------------
def eprice(g, t=None):
    t = TEA if t is None else t
    pr = t["green_premium"]
    return t["electricity_price_yuan_per_kwh"] + pr["linear_yuan_per_kwh"] * g + pr["quad_yuan_per_kwh"] * g ** 2


def pw_price(price_usd, t=None):
    """再生 LFP 正极粉价格：0.24×P(Li₂CO₃)+8,500，再按 88% 折价"""
    t = TEA if t is None else t
    lp = t["lfp_powder"]
    return (lp["li2co3_coef"] * price_usd * t["fx_cny_per_usd"] + lp["base_yuan_per_t"]) * lp["regenerated_discount"]


def tea(f, price_usd=22000, g=KNEE_G, t=None, capex_yuan=None, q_t=None):
    """单吨再生链成本、收入与 LCOR（负值=净收益）"""
    t = TEA if t is None else t
    q_t = REGEN_T if q_t is None else q_t
    capex = CAPEX_REGEN if capex_yuan is None else capex_yuan
    price_cny = price_usd * t["fx_cny_per_usd"]
    purchase_li = f["li_in_t"] * LI2CO3_PER_LI * price_cny * t["purchase_li_coef"]
    purchase_nico = (f["ni_t"] * t["nickel_price_yuan_per_t"] +
                     f["co_t"] * t["cobalt_price_yuan_per_t"]) * t["purchase_nico_coef"]
    purchase = purchase_li + purchase_nico + t["purchase_fixed_yuan_per_t"]
    electricity = f["electric_kwh"] * eprice(g, t)
    heat = f["heat_gj"] * t["heat_price_yuan_per_GJ"]
    reagent = 900.0
    water_cost = (f["water_m3"] * t["fresh_water_price_yuan_per_m3"] +
                  f["water_m3"] * (1 - PROC["wastewater_recycle"]) * t["wastewater_treat_yuan_per_m3"])
    opex_cash = (purchase + t["collection_transport_yuan_per_t"] + electricity + heat + reagent +
                 water_cost + t["labor_yuan_per_t"] + t["env_cost_yuan_per_t"])
    capex_ann = capex * CRF / q_t
    pw = pw_price(price_usd, t)
    revenue = (f["lce_t"] * price_cny + f["powder_t"] * pw +
               (f["ni_t"] * t["nickel_price_yuan_per_t"] + f["co_t"] * t["cobalt_price_yuan_per_t"] +
                f["mn_t"] * t["manganese_price_yuan_per_t"]) * t["salt_discount"] +
               f["fepo4_t"] * t["fepo4_price_yuan_per_t"] +
               f["cu_t"] * t["copper_price_yuan_per_t"] + f["al_t"] * t["aluminum_price_yuan_per_t"])
    return {
        "purchase": purchase, "purchase_li": purchase_li, "purchase_nico": purchase_nico,
        "purchase_fixed": t["purchase_fixed_yuan_per_t"],
        "capex_ann": capex_ann, "electricity": electricity, "heat": heat, "reagent": reagent,
        "collection": t["collection_transport_yuan_per_t"], "labor": t["labor_yuan_per_t"],
        "env": t["env_cost_yuan_per_t"], "water_cost": water_cost,
        "opex_cash": opex_cash, "opex": opex_cash + capex_ann,
        "revenue": revenue, "lcor_yuan_per_t": capex_ann + opex_cash - revenue,
        "eprice": eprice(g, t), "powder_price": pw,
        "revenue_items": {
            "lithium_carbonate": f["lce_t"] * price_cny,
            "regen_powder": f["powder_t"] * pw,
            "nicomn_salts": (f["ni_t"] * t["nickel_price_yuan_per_t"] +
                             f["co_t"] * t["cobalt_price_yuan_per_t"] +
                             f["mn_t"] * t["manganese_price_yuan_per_t"]) * t["salt_discount"],
            "fepo4_cu_al": (f["fepo4_t"] * t["fepo4_price_yuan_per_t"] +
                            f["cu_t"] * t["copper_price_yuan_per_t"] +
                            f["al_t"] * t["aluminum_price_yuan_per_t"]),
        },
    }


def marginal_cost(lcor, gwp):
    """相对原生精炼的边际减排成本（元/t CO₂e；负值=减碳同时降本）"""
    return (lcor - PRIMARY_CASH) / (PRIMARY_GWP - gwp) * 1000


def annual_flux(f, q=REGEN_T):
    """按再生链年处理量折算年通量（P14 / P23 用）"""
    keys = ("lce_t", "powder_t", "ni_t", "co_t", "mn_t", "fepo4_t", "cu_t", "al_t", "black_mass_t")
    return {"q_t": q, **{k: f[k] * q for k in keys}}


# ---------------- 财务 ----------------
def irr_of(cf, capex, years=YEARS):
    """等额年现金流的 IRR（二分法）"""
    if cf <= 0:
        return float("nan")

    def npv(r):
        return -capex + sum(cf / (1 + r) ** y for y in range(1, years + 1))

    lo, hi = -0.99, 1.0
    if npv(lo) * npv(hi) < 0:
        for _ in range(200):
            mid = (lo + hi) / 2
            if npv(lo) * npv(mid) <= 0:
                hi = mid
            else:
                lo = mid
        return (lo + hi) / 2
    return float("nan")


def financial(util, price_usd=22000, d=KNEE_D, g=KNEE_G, capex=CAPEX_REGEN, q_cap=REGEN_T,
              fixed=FIXED_LABOR_ENV):
    """财务：利用率 → LCOR / 年现金流 / NPV / 回收期 / IRR；默认再生链 16,000 t 口径"""
    f = simulate(d)
    ec = tea(f, price_usd, g)
    var = ec["purchase"] + ec["collection"] + ec["electricity"] + ec["heat"] + ec["reagent"] + ec["water_cost"]
    q = q_cap * util
    cf = (ec["revenue"] - var) * q - fixed
    npv = -capex + cf * AF
    payback = capex / cf if cf > 0 else inf
    lcor = (capex * CRF + fixed) / q + var - ec["revenue"]
    return {"util": util, "q_t": q, "lcor": lcor, "cashflow_yi": cf / 1e8,
            "npv_yi": npv / 1e8, "payback_a": payback, "irr": irr_of(cf, capex)}


def after_tax_financial(util, price_usd=22000, capex=CAPEX_REGEN, q_cap=REGEN_T, fixed=FIXED_LABOR_ENV):
    """计入 25% 所得税（直线折旧）后的财务表现"""
    f = simulate(KNEE_D)
    ec = tea(f, price_usd, KNEE_G)
    var = ec["purchase"] + ec["collection"] + ec["electricity"] + ec["heat"] + ec["reagent"] + ec["water_cost"]
    ebitda = (ec["revenue"] - var) * (q_cap * util) - fixed
    dep = capex / YEARS
    cf = ebitda - 0.25 * (ebitda - dep)
    npv = -capex + cf * AF
    return {"cashflow_yi": cf / 1e8, "npv_yi": npv / 1e8,
            "payback_a": capex / cf if cf > 0 else inf, "irr": irr_of(cf, capex)}


def break_even_util(capex=CAPEX_REGEN, q_cap=REGEN_T, fixed=FIXED_LABOR_ENV):
    """LCOR = 0（NPV = 0）时的利用率"""
    f = simulate(KNEE_D)
    ec = tea(f, 22000, KNEE_G)
    var = ec["purchase"] + ec["collection"] + ec["electricity"] + ec["heat"] + ec["reagent"] + ec["water_cost"]
    return (capex * CRF + fixed) / ((ec["revenue"] - var) * q_cap)


# ---------------- 蒙特卡洛 ----------------
def monte_carlo(n=5000, seed=20261108):
    """电网结构 × 锂价 × 直再比例 × 绿电比例 × 绿电溢价 五维不确定性；同时输出满负荷 NPV 与回收期"""
    rng = np.random.default_rng(seed)
    gwp, lcor, npv, pb = np.empty(n), np.empty(n), np.empty(n), np.empty(n)
    for i in range(n):
        x = rng.random()                                   # 0=煤电主导，1=水核主导
        ef = LCA_T["grid_ef"]["high"] - x * (LCA_T["grid_ef"]["high"] - LCA_T["grid_ef"]["low"])
        gw = LCA_T["grid_water_m3_per_kwh"]["high"] - x * (
            LCA_T["grid_water_m3_per_kwh"]["high"] - LCA_T["grid_water_m3_per_kwh"]["low"])
        price = rng.uniform(10000, 50000)
        d = rng.uniform(0.45, DIRECT_CAP)
        g = rng.uniform(0.45, 0.70)
        t = json.loads(json.dumps(TEA))
        t["green_premium"]["linear_yuan_per_kwh"] = rng.uniform(0.03, 0.07)
        t["green_premium"]["quad_yuan_per_kwh"] = rng.uniform(0.08, 0.16)
        f = simulate(d)
        gwp[i] = lca(f, g, grid_ef=ef, grid_water=gw)["gwp_kg_per_t"]
        ec = tea(f, price, g, t=t, capex_yuan=FULL_CAPEX, q_t=FULL_Q)
        var = (ec["purchase"] + ec["collection"] + ec["electricity"] + ec["heat"] +
               ec["reagent"] + ec["water_cost"])
        lcor[i] = ec["lcor_yuan_per_t"]
        fixed = (t["labor_yuan_per_t"] + t["env_cost_yuan_per_t"]) * FULL_Q
        cf = (ec["revenue"] - var) * FULL_Q - fixed
        npv[i] = (-FULL_CAPEX + cf * AF) / 1e8
        pb[i] = FULL_CAPEX / cf if cf > 0 else inf
    return gwp, lcor, npv, pb


# ---------------- 输出 ----------------
def save_json(name, obj):
    path = os.path.join(DATA, name)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2)
    print(f"  → {name}")
    return path


def save_csv(name, header, rows):
    path = os.path.join(DATA, name)
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        fh.write(",".join(header) + "\n")
        for r in rows:
            fh.write(",".join(f"{x:.4f}" if isinstance(x, float) else str(x) for x in r) + "\n")
    print(f"  → {name}")
    return path


def cascade_note():
    return {
        "total_feed_t_per_year": CAP_TOTAL,
        "cascade_t_per_year": CASCADE_T,
        "recycling_t_per_year": REGEN_T,
        "capex_total_yi": CAPEX_TOTAL / 1e8,
        "capex_recycling_yi": CAPEX_REGEN / 1e8,
        "capex_cascade_yi": CAPEX_CASCADE / 1e8,
        "fixed_labor_env_yuan_per_year": FIXED_LABOR_ENV,
        "full_feed_basis": "财务年度量按 20,000 t/a 全量（含 4,000 t 梯次，按同单吨毛利简化）",
        "note": "LCA/TEA 单吨指标按再生链 16,000 t/a 核算；财务另给 20,000 t/a 全量口径，CAPEX 按 80:20 分摊",
    }
