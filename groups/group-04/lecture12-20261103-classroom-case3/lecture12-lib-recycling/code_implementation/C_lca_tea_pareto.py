# -*- coding: utf-8 -*-
"""
C_lca_tea_pareto.py —— 水-碳耦合 LCA、平准化回收成本 TEA 与多目标帕累托寻优
方向 B：浙江衢州华友循环资源再生产业园（一期 20,000 t 退役动力电池/a，2035 扩至 60,000 t/a）

运行顺序：A_mfa_model.py → B_policy_engine.py → C_lca_tea_pareto.py → C_integrated_figures.py
输出：data_cohort/C_lca_tea_results.json、C_pareto_front.csv、C_pareto_front_by_price.csv、
      C_sensitivity.csv、C_water_carbon_curve.csv

【AI 辅助编程说明】
  Prompt 摘要："为退役动力电池再生精炼园区编写 Python 脚本：以 LFP 直接再生比例与绿电
  消纳比例为决策变量，遍历 21×21 网格 × 3 档碳酸锂价格，按工信部 2024 年本与欧盟
  2023/1542 红线剔除不可行解，用归一化理想点欧氏距离标定帕累托拐点，并输出锚点 A/B/C。"
  人工校验修正：①修正采购成本漏乘 Li2CO3/Li 换算系数；②拆分裂解直接再生锂（再生正极粉）
  与湿法碳酸锂两种产品形态，避免重复计价；③再生 LFP 粉价格改为随碳酸锂价格联动；
  ④绿电溢价改为随消纳比例凸性上升；⑤MAC 单位由 元/kg 统一为 元/t CO2e。
"""
import json
import os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data_cohort")

with open(os.path.join(DATA, "ABC_parameters.json"), encoding="utf-8") as f:
    P = json.load(f)

CAP = P["_meta"]["design_capacity_t_cells_per_year"]
SHARE, COMP, ELEM = P["feedstock"]["share"], P["feedstock"]["composition"], P["feedstock"]["active_element_fraction"]
ROUTES, PRE = P["process"]["routes"], P["process"]["pretreatment"]
LCA, TEA = P["lca"], P["tea"]
LI2CO3_PER_LI = P["process"]["li2co3_per_li"]
DIRECT_CAP = P["process"]["direct_suitability_cap"]
RC_SHARE_NMC = 0.30                     # NMC/NCA 中 30% 走还原焙烧+湿法（工程配置约束）
CRF = TEA["wacc"] * (1 + TEA["wacc"]) ** TEA["life_years"] / ((1 + TEA["wacc"]) ** TEA["life_years"] - 1)
REAGENTS = {k: LCA["reagents"][k] for k in ("H2SO4", "NaOH", "Na2CO3", "H2O2")}
REAGENT_CO2 = sum(v * LCA["reagents"]["kg_co2e_per_kg"][k] for k, v in REAGENTS.items())
TRANSPORT_CO2 = LCA["transport"]["distance_km"] * LCA["transport"]["kg_co2e_per_t_km"]
PRIMARY = LCA["primary"]
PRIMARY_COST_PER_T = 0.0861 * 65000       # 原生精炼现金成本基准：0.0861 t LCE/t 电池 × 65,000 元/t
PRICES = [TEA["li2co3_price_usd_per_t"]["low"], TEA["li2co3_price_usd_per_t"]["base"],
          TEA["li2co3_price_usd_per_t"]["high"]]


def simulate(direct_share_lfp):
    """给定 LFP 直再比例，返回单吨退役电池的物料、能耗、水耗与回收率"""
    li_in = sum(SHARE[k] * COMP[k]["active"] * ELEM[k]["Li"] for k in SHARE)          # t/t
    lfp_act = SHARE["LFP"] * COMP["LFP"]["active"]
    lfp_li_mass = lfp_act * ELEM["LFP"]["Li"]
    lfp_fe_mass = lfp_act * ELEM["LFP"]["Fe"]
    lfp_p_mass = lfp_act * ELEM["LFP"]["P"]
    ni_in = SHARE["NMC811"] * COMP["NMC811"]["active"] * ELEM["NMC811"]["Ni"] + \
        SHARE["NCA"] * COMP["NCA"]["active"] * ELEM["NCA"]["Ni"]
    co_in = SHARE["NMC811"] * COMP["NMC811"]["active"] * ELEM["NMC811"]["Co"] + \
        SHARE["NCA"] * COMP["NCA"]["active"] * ELEM["NCA"]["Co"]
    mn_in = SHARE["NMC811"] * COMP["NMC811"]["active"] * ELEM["NMC811"]["Mn"]
    cu_in = sum(SHARE[k] * COMP[k]["Cu"] for k in SHARE)
    al_in = sum(SHARE[k] * COMP[k]["Al"] for k in SHARE)

    hy, rc, dr = ROUTES["Hy"], ROUTES["RC_Hy"], ROUTES["Direct"]
    # 锂：LFP 分流为“直接再生（锂以再生正极粉形态留存）”与“湿法（锂以 Li2CO3 形态产出）”
    lfp_li_lce = lfp_li_mass * (1 - direct_share_lfp) * hy["Li"]
    lfp_li_powder = lfp_li_mass * direct_share_lfp * dr["Li"]
    other_li_rec = (li_in - lfp_li_mass) * ((1 - RC_SHARE_NMC) * hy["Li"] + RC_SHARE_NMC * rc["Li"])
    li_rec = lfp_li_lce + lfp_li_powder + other_li_rec
    nico_rec = (ni_in + co_in + mn_in) * ((1 - RC_SHARE_NMC) * hy["NiCoMn"] + RC_SHARE_NMC * rc["NiCoMn"])

    lce_t = (lfp_li_lce + other_li_rec) * LI2CO3_PER_LI          # 仅湿法/焙烧路线产出碳酸锂
    powder_t = lfp_act * direct_share_lfp * 0.97                  # 再生磷酸铁锂正极粉
    fe_rec = lfp_fe_mass * (1 - direct_share_lfp) * hy["FeP"]
    p_rec = lfp_p_mass * (1 - direct_share_lfp) * hy["FeP"]
    fepo4_t = fe_rec + p_rec + 16.0 / 30.97 * p_rec
    ni_rec = ni_in * ((1 - RC_SHARE_NMC) * hy["NiCoMn"] + RC_SHARE_NMC * rc["NiCoMn"])
    co_rec = co_in * ((1 - RC_SHARE_NMC) * hy["NiCoMn"] + RC_SHARE_NMC * rc["NiCoMn"])
    mn_rec = mn_in * ((1 - RC_SHARE_NMC) * hy["NiCoMn"] + RC_SHARE_NMC * rc["NiCoMn"])

    # 能耗 / 水耗：按化学体系与路线配比加权
    e_lfp = direct_share_lfp * dr["energy_GJ_per_t"] + (1 - direct_share_lfp) * hy["energy_GJ_per_t"]
    e_nmc = (1 - RC_SHARE_NMC) * hy["energy_GJ_per_t"] + RC_SHARE_NMC * rc["energy_GJ_per_t"]
    energy = SHARE["LFP"] * e_lfp + (SHARE["NMC811"] + SHARE["NCA"]) * e_nmc
    th = (SHARE["LFP"] * (direct_share_lfp * dr["thermal_share"] + (1 - direct_share_lfp) * hy["thermal_share"]) +
          (SHARE["NMC811"] + SHARE["NCA"]) * ((1 - RC_SHARE_NMC) * hy["thermal_share"] + RC_SHARE_NMC * rc["thermal_share"]))
    w = (SHARE["LFP"] * (direct_share_lfp * dr["water_m3_per_t"] + (1 - direct_share_lfp) * hy["water_m3_per_t"]) +
         (SHARE["NMC811"] + SHARE["NCA"]) * ((1 - RC_SHARE_NMC) * hy["water_m3_per_t"] + RC_SHARE_NMC * rc["water_m3_per_t"]))

    return {"li_rec_t": li_rec, "li_in_t": li_in, "nico_rec_t": nico_rec, "lce_t": lce_t, "powder_t": powder_t,
            "fepo4_t": fepo4_t, "ni_t": ni_rec, "co_t": co_rec, "mn_t": mn_rec,
            "cu_t": cu_in * PRE["copper_al_recovery"], "al_t": al_in * PRE["copper_al_recovery"],
            "energy_gj": energy, "heat_gj": energy * th,
            "electric_kwh": energy * (1 - th) / 0.0036 + PRE["electricity_kwh_per_t"],
            "water_m3": w + PRE["water_m3_per_t"],
            "li_recovery": li_rec / li_in,
            "nico_recovery": nico_rec / (ni_in + co_in + mn_in)}


def lca(f, green_share, grid_ef=None):
    """摇篮到大门 LCA：电力、热能、试剂上游隐含排放与收集运输；水耗含工艺水与电力耗水"""
    base_ef = LCA["grid_ef"]["base"] if grid_ef is None else grid_ef
    ef = base_ef * (1 - green_share) + LCA["green_residual_ef"] * green_share
    base_w = LCA["grid_water_m3_per_kwh"]["base"] if grid_ef is None else \
        (LCA["grid_water_m3_per_kwh"]["low"] if grid_ef <= LCA["grid_ef"]["low"] * 1.001 else
         LCA["grid_water_m3_per_kwh"]["high"] if grid_ef >= LCA["grid_ef"]["high"] * 0.999 else
         LCA["grid_water_m3_per_kwh"]["base"])
    gw = base_w * (1 - green_share) + LCA["green_water_m3_per_kwh"] * green_share
    co2 = f["electric_kwh"] * ef + f["heat_gj"] * LCA["natural_gas_kg_co2e_per_GJ"] + REAGENT_CO2 + TRANSPORT_CO2
    water = f["water_m3"] + f["electric_kwh"] * gw
    product_mass = (f["lce_t"] + f["ni_t"] + f["co_t"] + f["mn_t"] + f["fepo4_t"] +
                    f["cu_t"] + f["al_t"] + f["powder_t"])
    lce_share = f["lce_t"] / max(product_mass, 1e-12)
    kgce_lce = (f["energy_gj"] * 1000 / 29.307) * lce_share / max(f["lce_t"], 1e-12)
    return {"gwp_kg_per_t": co2, "water_m3_per_t": water, "process_water_m3_per_t": f["water_m3"],
            "energy_gj_per_t": f["energy_gj"], "ef": ef, "kgce_per_t_lce": kgce_lce, "lce_share": lce_share}


def powder_price_yuan_per_t(price_cny):
    """再生 LFP 正极粉价格：随碳酸锂价格联动（行业锂价传导式），再生粉折价"""
    cfg = TEA["lfp_powder"]
    return (cfg["li2co3_coef"] * price_cny + cfg["base_yuan_per_t"]) * cfg["regenerated_discount"]


def electricity_unit_price(green_share):
    gp = TEA["green_premium"]
    return (TEA["electricity_price_yuan_per_kwh"] + gp["linear_yuan_per_kwh"] * green_share
            + gp["quad_yuan_per_kwh"] * green_share ** 2)


def tea(f, price_usd, green_share=0.0):
    price = price_usd * TEA["fx_cny_per_usd"]          # 元/t Li2CO3
    purchase = (TEA["purchase_li_coef"] * price * f["li_in_t"] * LI2CO3_PER_LI
                + TEA["purchase_nico_coef"] * (TEA["nickel_price_yuan_per_t"] * f["ni_t"] +
                                               TEA["cobalt_price_yuan_per_t"] * f["co_t"])
                + TEA["purchase_fixed_yuan_per_t"])
    e_price = electricity_unit_price(green_share)
    electricity = f["electric_kwh"] * e_price
    heat = f["heat_gj"] * TEA["heat_price_yuan_per_GJ"]
    d_share = f["powder_t"] / 0.1746                    # 由再生粉产量反推 LFP 直再比例
    reagent = ROUTES["Hy"]["reagent_cost_yuan_per_t"] - 500 * d_share
    # 水资源费 + 废水处理费（衢江上游水环境敏感区，按未循环部分全额处理）
    water_cost = (f["water_m3"] * TEA["fresh_water_price_yuan_per_m3"] +
                  f["water_m3"] * (1 - P["process"]["wastewater_recycle"]) *
                  TEA["wastewater_treat_yuan_per_m3"])
    opex = purchase + TEA["collection_transport_yuan_per_t"] + electricity + heat + reagent + \
        water_cost + TEA["labor_yuan_per_t"] + TEA["env_cost_yuan_per_t"]
    capex_ann = TEA["capex_yuan"] * CRF / CAP
    revenue = (f["lce_t"] * price + f["ni_t"] * TEA["nickel_price_yuan_per_t"] * TEA["salt_discount"] +
               f["co_t"] * TEA["cobalt_price_yuan_per_t"] * TEA["salt_discount"] +
               f["mn_t"] * 15000 * TEA["salt_discount"] +
               f["fepo4_t"] * TEA["fepo4_price_yuan_per_t"] +
               f["powder_t"] * powder_price_yuan_per_t(price) +
               f["cu_t"] * TEA["copper_price_yuan_per_t"] + f["al_t"] * TEA["aluminum_price_yuan_per_t"])
    return {"purchase": purchase, "opex": opex + capex_ann, "revenue": revenue,
            "electricity": electricity, "heat": heat, "reagent": reagent, "water_cost": water_cost,
            "lcor_yuan_per_t": capex_ann + opex - revenue, "capex_ann": capex_ann,
            "electricity_price": e_price, "powder_price": powder_price_yuan_per_t(price),
            "price_cny": price}


def mac_of(lcor, gwp):
    """边际减排成本（元/t CO2e）：以原生精炼路径为基准"""
    return (lcor - PRIMARY_COST_PER_T) / max(PRIMARY["co2_kg_per_t"] - gwp, 1e-9) * 1000


def feasible(f, env):
    return (f["li_recovery"] >= 0.90 + 1e-9 and f["nico_recovery"] >= 0.98 - 1e-9
            and env["kgce_per_t_lce"] < P["process"]["lce_energy_ceiling_kgce_per_t"]
            and P["process"]["wastewater_recycle"] >= 0.90 - 1e-9)


GRID = np.linspace(0, 1, 21)

# ---------------- 1. 帕累托寻优（按锂价分层，逐层剔除政策不可行解） ----------------
print("=" * 96)
print("多目标帕累托寻优：决策变量 = 绿电消纳比例 × LFP 直接再生比例（21×21 网格 × 3 档锂价）")
print("=" * 96)
par = {}
for p in PRICES:
    pts = []
    for g in GRID:
        for d in GRID:
            if d > DIRECT_CAP + 1e-9:
                continue
            f = simulate(d)
            env = lca(f, g)
            eco = tea(f, p, g)
            if feasible(f, env):
                pts.append({"price_usd": float(p), "green": round(float(g), 4), "direct": round(float(d), 4),
                            "gwp": env["gwp_kg_per_t"], "lcor": eco["lcor_yuan_per_t"],
                            "water": env["water_m3_per_t"], "li_recovery": f["li_recovery"],
                            "nico_recovery": f["nico_recovery"], "kgce": env["kgce_per_t_lce"]})
    front = []
    for i, a in enumerate(pts):
        dominated = False
        for j, b in enumerate(pts):
            if i == j:
                continue
            if b["gwp"] <= a["gwp"] + 1e-9 and b["lcor"] <= a["lcor"] + 1e-9 and \
                    (b["gwp"] < a["gwp"] - 1e-9 or b["lcor"] < a["lcor"] - 1e-9):
                dominated = True
                break
        if not dominated:
            front.append(a)
    par[p] = {"candidates": pts, "front": front}
    print(f"  锂价 {p:>6.0f} USD/t：可行工况 {len(pts):>4d} 组，非支配解 {len(front):>3d} 组")

total_cand = sum(len(v["candidates"]) for v in par.values())
print(f"\n累计可行工况 {total_cand} 组（任务书要求 ≥ 500 组）")

# 基准锂价前沿的拐点（归一化理想点欧氏距离最小化）
BP = float(TEA["li2co3_price_usd_per_t"]["base"])
base_front = par[BP]["front"]
gw = np.array([x["gwp"] for x in base_front])
lc = np.array([x["lcor"] for x in base_front])
gn = (gw - gw.min()) / (gw.max() - gw.min() + 1e-12)
ln = (lc - lc.min()) / (lc.max() - lc.min() + 1e-12)
knee = base_front[int(np.argmin(np.sqrt(gn ** 2 + ln ** 2)))]
A = min(par[BP]["candidates"], key=lambda x: x["lcor"])
C = min(par[BP]["candidates"], key=lambda x: x["gwp"])
print(f"\n锚点 A（成本最优）：绿电 {A['green']*100:.0f}%  直再 {A['direct']*100:.0f}%  "
      f"LCOR {A['lcor']:.0f} 元/t  碳足迹 {A['gwp']:.0f} kg CO2e/t  水 {A['water']:.2f} m3/t")
print(f"锚点 B（拐点）：  绿电 {knee['green']*100:.0f}%  直再 {knee['direct']*100:.0f}%  "
      f"LCOR {knee['lcor']:.0f} 元/t  碳足迹 {knee['gwp']:.0f} kg CO2e/t  水 {knee['water']:.2f} m3/t")
print(f"锚点 C（碳最优）：绿电 {C['green']*100:.0f}%  直再 {C['direct']*100:.0f}%  "
      f"LCOR {C['lcor']:.0f} 元/t  碳足迹 {C['gwp']:.0f} kg CO2e/t  水 {C['water']:.2f} m3/t")

# ---------------- 2. 情景评估（base / green / knee） ----------------
SCEN = {"base":  {"green_share": 0.0, "direct_share_lfp": 0.20},
        "green": {"green_share": 1.0, "direct_share_lfp": DIRECT_CAP},
        "knee":  {"green_share": knee["green"], "direct_share_lfp": knee["direct"]}}
print("\n" + "=" * 96)
print("LCA / TEA 情景评估（功能单位：1 t 退役动力电池；锂价 22,000 USD/t）")
print("=" * 96)
out = {"crf": CRF, "primary": PRIMARY, "primary_cost_yuan_per_t_cells": PRIMARY_COST_PER_T,
       "direct_suitability_cap": DIRECT_CAP, "scenarios": {}}
for name, sc in SCEN.items():
    f = simulate(sc["direct_share_lfp"])
    env = lca(f, sc["green_share"])
    eco = tea(f, BP, sc["green_share"])
    rec = {"green_share": sc["green_share"], "direct_share_lfp": sc["direct_share_lfp"],
           "gwp_kg_per_t": env["gwp_kg_per_t"], "water_m3_per_t": env["water_m3_per_t"],
           "process_water_m3_per_t": env["process_water_m3_per_t"],
           "energy_gj_per_t": env["energy_gj_per_t"], "ef": env["ef"],
           "lcor_yuan_per_t": eco["lcor_yuan_per_t"], "profit_yuan_per_t": -eco["lcor_yuan_per_t"],
           "mac_yuan_per_t_co2e": mac_of(eco["lcor_yuan_per_t"], env["gwp_kg_per_t"]),
           "lce_t": f["lce_t"], "powder_t": f["powder_t"], "fepo4_t": f["fepo4_t"],
           "ni_t": f["ni_t"], "co_t": f["co_t"], "mn_t": f["mn_t"],
           "li_recovery": f["li_recovery"], "nico_recovery": f["nico_recovery"],
           "kgce_per_t_lce": env["kgce_per_t_lce"],
           "co2_saving_vs_primary": 1 - env["gwp_kg_per_t"] / PRIMARY["co2_kg_per_t"],
           "water_saving_vs_primary": 1 - env["water_m3_per_t"] / PRIMARY["water_m3_per_t"],
           "electric_kwh_per_t": f["electric_kwh"], "heat_gj_per_t": f["heat_gj"],
           "cost_detail": eco}
    out["scenarios"][name] = rec
    print(f"[{name:<5}] 绿电 {sc['green_share']*100:>3.0f}%  直再 {sc['direct_share_lfp']*100:>3.0f}%  "
          f"→ 碳足迹 {env['gwp_kg_per_t']:>6.0f} kg CO2e/t（降 {rec['co2_saving_vs_primary']*100:4.1f}%）  "
          f"水 {env['water_m3_per_t']:>5.2f} m3/t（降 {rec['water_saving_vs_primary']*100:4.1f}%）  "
          f"LCOR {eco['lcor_yuan_per_t']:>8.0f} 元/t  MAC {rec['mac_yuan_per_t_co2e']:>8.0f} 元/t CO2e")

# ---------------- 3. 敏感性：电网排放因子 × 碳酸锂价格（5×5 双因素网格） ----------------
ef_grid = np.linspace(LCA["grid_ef"]["low"], LCA["grid_ef"]["high"], 5)
price_grid = np.linspace(PRICES[0], PRICES[-1], 5)
sens = []
for ef in ef_grid:
    for p in price_grid:
        f = simulate(knee["direct"])
        env = lca(f, knee["green"], grid_ef=float(ef))
        eco = tea(f, float(p), knee["green"])
        sens.append({"grid_ef": round(float(ef), 4), "price_usd": round(float(p), 1),
                     "gwp_kg_per_t": env["gwp_kg_per_t"], "water_m3_per_t": env["water_m3_per_t"],
                     "lcor_yuan_per_t": eco["lcor_yuan_per_t"]})

# ---------------- 4. 水-碳权衡曲线（不同电网结构 × 绿电比例） ----------------
wcc = []
for ef in [LCA["grid_ef"]["low"], LCA["grid_ef"]["base"], LCA["grid_ef"]["high"]]:
    for g in GRID:
        f = simulate(knee["direct"])
        env = lca(f, g, grid_ef=ef)
        wcc.append({"grid_ef": ef, "green_share": round(float(g), 4),
                    "gwp_kg_per_t": env["gwp_kg_per_t"], "water_m3_per_t": env["water_m3_per_t"]})

# ---------------- 5. 远期扩容（2035，60,000 t/a，绿电 100%） ----------------
fut = simulate(knee["direct"])
fut_env = lca(fut, 1.0)
long_term = {"capacity_t_per_year": 60000, "green_share": 1.0, "direct_share_lfp": knee["direct"],
             "gwp_kg_per_t": fut_env["gwp_kg_per_t"], "water_m3_per_t": fut_env["water_m3_per_t"],
             "annual_co2_saving_t": (PRIMARY["co2_kg_per_t"] - fut_env["gwp_kg_per_t"]) * 60000 / 1000,
             "annual_water_saving_m3": (PRIMARY["water_m3_per_t"] - fut_env["water_m3_per_t"]) * 60000,
             "annual_lce_t": fut["lce_t"] * 60000, "annual_powder_t": fut["powder_t"] * 60000}

out["pareto"] = {"n_candidates_total": total_cand, "n_front_base": len(base_front),
                 "knee": knee, "anchor_cost": A, "anchor_carbon": C,
                 "front_base": base_front,
                 "by_price": {str(k): {"n_candidates": len(v["candidates"]), "n_front": len(v["front"]),
                                       "front": v["front"]} for k, v in par.items()}}
out["sensitivity"] = sens
out["water_carbon_curve"] = wcc
out["long_term_2035"] = long_term
out["annual_base"] = {"capacity_t_per_year": CAP,
                      "lce_t": out["scenarios"]["knee"]["lce_t"] * CAP,
                      "powder_t": out["scenarios"]["knee"]["powder_t"] * CAP,
                      "fepo4_t": out["scenarios"]["knee"]["fepo4_t"] * CAP,
                      "gwp_t_co2e": out["scenarios"]["knee"]["gwp_kg_per_t"] * CAP / 1000,
                      "co2_saving_t": (PRIMARY["co2_kg_per_t"] - out["scenarios"]["knee"]["gwp_kg_per_t"]) * CAP / 1000,
                      "water_m3": out["scenarios"]["knee"]["water_m3_per_t"] * CAP,
                      "water_saving_m3": (PRIMARY["water_m3_per_t"] - out["scenarios"]["knee"]["water_m3_per_t"]) * CAP}

# ---------------- 6. C 模块交付：项目级现金流/NPV、锂价—工艺经济性排序、单因素敏感性 ----------------
annuity = (1 - (1 + TEA["wacc"]) ** -TEA["life_years"]) / TEA["wacc"]
CONF = {"hy_only": (0.0, 0.0), "base": (0.0, 0.20), "knee": (knee["green"], knee["direct"]),
        "green": (1.0, DIRECT_CAP)}

def project_finance(f, g, p):
    """项目级财务：年现金流 = (收入 − 现金成本) × 产能；NPV = −CAPEX + 年现金流 × 年金现值系数"""
    eco = tea(f, p, g)
    annual_cf = (eco["capex_ann"] - eco["lcor_yuan_per_t"]) * CAP
    npv = -TEA["capex_yuan"] + annual_cf * annuity
    payback = TEA["capex_yuan"] / annual_cf if annual_cf > 0 else float("inf")
    return eco, annual_cf, npv, payback

finance = {}
for name, (g, d) in CONF.items():
    f = simulate(d)
    eco, cf, npv, pb = project_finance(f, g, BP)
    finance[name] = {"green_share": g, "direct_share_lfp": d, "lcor": eco["lcor_yuan_per_t"],
                     "annual_cash_flow_yuan": cf, "npv_yuan": npv, "payback_years": pb,
                     "irr_note": "无杠杆税前口径，未计所得税与折旧抵税"}

cashflow = {name: [] for name in CONF}
for name, (g, d) in CONF.items():
    f = simulate(d)
    eco = tea(f, BP, g)
    cf0 = -TEA["capex_yuan"]
    cum = cf0
    series = [{"year": 0, "cash_flow": cf0, "cumulative": cum}]
    for t in range(1, TEA["life_years"] + 1):
        cf = (eco["capex_ann"] - eco["lcor_yuan_per_t"]) * CAP
        cum += cf / (1 + TEA["wacc"]) ** t
        series.append({"year": t, "cash_flow": cf, "cumulative": cum})
    cashflow[name] = series

price_curve = []
for p in np.linspace(PRICES[0], PRICES[-1], 17):
    row = {"price_usd": round(float(p), 1)}
    for name, (g, d) in CONF.items():
        f = simulate(d)
        eco = tea(f, float(p), g)
        row[name] = round(float(eco["lcor_yuan_per_t"]), 1)
    price_curve.append(row)

def breakeven(curve, key):
    """线性插值求 LCOR = 0 的碳酸锂价格"""
    for a, b in zip(curve[:-1], curve[1:]):
        if a[key] < 0 <= b[key] or b[key] < 0 <= a[key]:
            return round(a["price_usd"] + (b["price_usd"] - a["price_usd"]) *
                         (0 - a[key]) / (b[key] - a[key]), 0)
    return None

# 单因素敏感性（拐点方案，偏离 ±Δ 后重算 LCOR，用于龙卷风图）
def lcor_with(**mods):
    backup = {k: TEA.get(k) for k in mods}
    try:
        for k, v in mods.items():
            TEA[k] = v
        return tea(simulate(knee["direct"]), BP, knee["green"])["lcor_yuan_per_t"]
    finally:
        for k, v in backup.items():
            if v is None:
                TEA.pop(k, None)
            else:
                TEA[k] = v

base_lcor = tea(simulate(knee["direct"]), BP, knee["green"])["lcor_yuan_per_t"]
tornado = []

def add_factor(name, lo, hi):
    tornado.append({"factor": name, "low": lo, "high": hi, "base": base_lcor})

# 1) 碳酸锂价格 ±30%
add_factor("碳酸锂价格 ±30%",
           tea(simulate(knee["direct"]), BP * 0.7, knee["green"])["lcor_yuan_per_t"],
           tea(simulate(knee["direct"]), BP * 1.3, knee["green"])["lcor_yuan_per_t"])
# 2) CAPEX ±30%
add_factor("CAPEX ±30%", lcor_with(capex_yuan=TEA["capex_yuan"] * 0.7),
           lcor_with(capex_yuan=TEA["capex_yuan"] * 1.3))
# 3) 采购锂系数 ±15%
add_factor("采购锂系数 ±15%", lcor_with(purchase_li_coef=TEA["purchase_li_coef"] * 0.85),
           lcor_with(purchase_li_coef=TEA["purchase_li_coef"] * 1.15))
# 4) 电价 ±20%（含绿电溢价整体平移）
p0 = TEA["electricity_price_yuan_per_kwh"]
TEA["electricity_price_yuan_per_kwh"] = p0 * 0.8
lo_e = tea(simulate(knee["direct"]), BP, knee["green"])["lcor_yuan_per_t"]
TEA["electricity_price_yuan_per_kwh"] = p0 * 1.2
hi_e = tea(simulate(knee["direct"]), BP, knee["green"])["lcor_yuan_per_t"]
TEA["electricity_price_yuan_per_kwh"] = p0
add_factor("电价 ±20%", lo_e, hi_e)
# 5) 再生粉折价率 ±10 个百分点（88% → 78%/98%）
d0 = TEA["lfp_powder"]["regenerated_discount"]
TEA["lfp_powder"]["regenerated_discount"] = d0 - 0.10
lo_d = tea(simulate(knee["direct"]), BP, knee["green"])["lcor_yuan_per_t"]
TEA["lfp_powder"]["regenerated_discount"] = d0 + 0.10
hi_d = tea(simulate(knee["direct"]), BP, knee["green"])["lcor_yuan_per_t"]
TEA["lfp_powder"]["regenerated_discount"] = d0
add_factor("再生粉折价 ±10 pct", lo_d, hi_d)

out["economics"] = {"annuity_factor": annuity, "finance": finance, "cashflow": cashflow,
                    "price_curve": price_curve,
                    "breakeven_price_usd": {k: breakeven(price_curve, k) for k in CONF},
                    "tornado": tornado}

with open(os.path.join(DATA, "C_lca_tea_results.json"), "w", encoding="utf-8") as fp:
    json.dump(out, fp, ensure_ascii=False, indent=2)

with open(os.path.join(DATA, "C_pareto_front.csv"), "w", encoding="utf-8-sig") as fp:
    fp.write("price_usd,green_share,direct_share,gwp_kg_per_t,lcor_yuan_per_t,water_m3_per_t\n")
    for r in base_front:
        fp.write(f"{r['price_usd']},{r['green']},{r['direct']},{r['gwp']:.1f},{r['lcor']:.1f},{r['water']:.3f}\n")

with open(os.path.join(DATA, "C_pareto_front_by_price.csv"), "w", encoding="utf-8-sig") as fp:
    fp.write("price_usd,green_share,direct_share,gwp_kg_per_t,lcor_yuan_per_t,water_m3_per_t\n")
    for p in PRICES:
        for r in par[p]["front"]:
            fp.write(f"{r['price_usd']},{r['green']},{r['direct']},{r['gwp']:.1f},{r['lcor']:.1f},{r['water']:.3f}\n")

with open(os.path.join(DATA, "C_sensitivity.csv"), "w", encoding="utf-8-sig") as fp:
    fp.write("grid_ef,price_usd,gwp_kg_per_t,water_m3_per_t,lcor_yuan_per_t\n")
    for r in sens:
        fp.write(f"{r['grid_ef']},{r['price_usd']},{r['gwp_kg_per_t']:.1f},"
                 f"{r['water_m3_per_t']:.3f},{r['lcor_yuan_per_t']:.1f}\n")

with open(os.path.join(DATA, "C_water_carbon_curve.csv"), "w", encoding="utf-8-sig") as fp:
    fp.write("grid_ef,green_share,gwp_kg_per_t,water_m3_per_t\n")
    for r in wcc:
        fp.write(f"{r['grid_ef']},{r['green_share']},{r['gwp_kg_per_t']:.1f},{r['water_m3_per_t']:.3f}\n")

print(f"\n年通量（拐点，{CAP} t/a）：Li2CO3 {out['annual_base']['lce_t']:.0f} t/a；再生正极粉 "
      f"{out['annual_base']['powder_t']:.0f} t/a；年减碳 {out['annual_base']['co2_saving_t']:.0f} t CO2e")
print(f"远期 2035（60,000 t/a、绿电 100%）：碳足迹 {long_term['gwp_kg_per_t']:.0f} kg CO2e/t；"
      f"年减碳 {long_term['annual_co2_saving_t']:.0f} t CO2e")
print("\n已写出 C_lca_tea_results.json / C_pareto_front.csv / C_pareto_front_by_price.csv / "
      "C_sensitivity.csv / C_water_carbon_curve.csv")
