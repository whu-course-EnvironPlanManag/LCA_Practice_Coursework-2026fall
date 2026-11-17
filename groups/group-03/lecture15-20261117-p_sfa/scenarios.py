# -*- coding: utf-8 -*-
"""任务 3：2050 年 BAU 与"3R"情景模拟、交叉敏感性回归

BAU 基线据论文校准：
  CFR 26.9 Mt P；磷矿需求 205.1 Mt（P2O5 当量）；环境流失 69.9 Mt P；
  食物磷需求 16.2 Mt P；PUE：种植 31%、养殖 16%、消费 31%；养殖回收率 50% 口径。
单位：kt P（NPR 为磷矿石 P2O5 当量 kt）。
"""
import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.preprocessing import StandardScaler

from config import P2050_BAU
from data_io import load_population_projection


def build_bau_2050(pop_ratio, p=P2050_BAU):
    """构建 2050 BAU 基线（需求外推 + 论文校准）。所有流量 kt P。"""
    F = {}
    fert = p["fert_target"]                    # 26.9 Mt P（人口×膳食外推校准）
    food_supply = p["food_P_target"]           # 16.2 Mt P
    products = 11000.0                         # 畜产品磷（养殖规模校准值）
    pue_lv = p["lbs_pue"]                      # 16%
    feed_total = products / pue_lv
    feed_crop, byproduct, additive = 4225.0, 1812.0, 3019.0
    forage = feed_total - feed_crop - byproduct - additive
    gaseous = 0.08 * feed_total
    grazing = 0.10 * forage                    # 规模化养殖下放牧排泄占比
    manure_gen = feed_total - products - gaseous - grazing   # 可收集粪污
    # BAU 粪污还田利用率 μ0：由 S4.3 杠杆（→75% 时 CFR -76.9%）反推校准
    mu0 = 0.75 - 0.769 * fert / manure_gen
    manure_applied = mu0 * manure_gen
    unapplied = manure_gen - manure_applied
    lbs_env = 0.55 * unapplied                 # 未还田粪污的环境流失
    manure_stock = unapplied - lbs_env         # 粪污暂存
    # ACS（PUE 31%）
    waste = 0.25 * food_supply
    compost = 0.5 * waste
    intake = food_supply - waste
    sewage = intake + 604.0                    # + 日化用磷
    sludge_field = 0.65 * 0.44 * 0.8 * sewage  # 污泥农用
    others = 1507.0 + 543.0 + sludge_field + compost
    total_in = fert + manure_applied + others
    harvest = p["crop_pue"] * total_in
    uptake = harvest / 0.70
    residue = uptake - harvest
    residue_ret = 0.55 * residue
    soil_in = total_in + residue_ret
    runoff = 0.25 * soil_in
    erosion = 0.08 * soil_in
    # 环境流失率定：使 BAU 总量 = 论文 69.9 Mt P（流失系数整体缩放）
    npr_rock = fert / p["ore_grade_P"]         # 205.1 Mt（P2O5 当量）
    nonfert = 4362.0
    cis_loss = fert / 0.74 - fert
    env_fixed = lbs_env + (sewage - 0.44 * 0.8 * sewage) + 0.35 * 0.44 * 0.8 * sewage \
        + 0.5 * waste + nonfert * 0.3 + cis_loss
    k = (p["env_loss_target"] - env_fixed) / (runoff + erosion)
    runoff *= k
    erosion *= k
    legacy = soil_in - uptake - runoff - erosion
    F.update(fert=fert, food_supply=food_supply, products=products,
             pue_lv=pue_lv, feed_total=feed_total, forage=forage,
             gaseous=gaseous, grazing=grazing, manure_gen=manure_gen,
             mu0=mu0, manure_applied=manure_applied, lbs_env=lbs_env,
             manure_stock=manure_stock, total_in=total_in, harvest=harvest,
             uptake=uptake, residue_ret=residue_ret, runoff=runoff,
             erosion=erosion, legacy=legacy, sewage=sewage,
             compost=compost, sludge_field=sludge_field,
             npr_rock=npr_rock, nonfert=nonfert, cis_loss=cis_loss,
             waste=waste, pop_ratio=pop_ratio)
    F["env_total_bau"] = (cis_loss + runoff + erosion + lbs_env
                          + (sewage - 0.44 * 0.8 * sewage)
                          + 0.35 * 0.44 * 0.8 * sewage + 0.5 * waste
                          + nonfert * 0.3)
    return F


def simulate_3r(F, r=0.0, mu_target=None, rec=0.0, feed_eff=0.0, diet=0.0,
                psi=None):
    """运行情景组合（相对 2050 BAU）。
    r: S2.2 化肥减施比例；mu_target: S4.3 粪污还田利用率；
    rec: S4.5 污水鸟粪石回收率；feed_eff: S2.3 饲料转化提升；
    diet: 膳食结构调整（动物产品需求下降）。"""
    p = P2050_BAU
    psi = p["psi"] if psi is None else psi
    # --- 养殖端：S2.3 饲料转化 + 膳食调整 ---
    products = F["products"] * (1 - diet)
    pue_lv = F["pue_lv"] * (1 + 0.75 * feed_eff)
    feed_total = products / pue_lv
    scale = feed_total / F["feed_total"]
    gaseous, grazing = F["gaseous"] * scale, F["grazing"] * scale
    manure_gen = feed_total - products - gaseous - grazing
    # --- S4.3：粪污还田利用率提升（与减施政策存在协同耦合，见报告）---
    mu = F["mu0"] if mu_target is None else min(mu_target, 0.95)
    extra_manure = manure_gen * (mu - F["mu0"]) * (1 + psi * r)
    manure_applied = F["manure_applied"] * scale + max(extra_manure, 0.0)
    unapplied = max(manure_gen - manure_applied, 0.0)
    lbs_env = 0.55 * unapplied
    manure_stock = unapplied - lbs_env
    # --- S4.5：鸟粪石回收（可回收部分=污水磷的 50%）---
    sewage = F["sewage"] * (1 - 0.1 * diet)
    struvite = rec * 0.5 * sewage
    # --- 化肥需求（替代+减施，设特种用途刚性下限）---
    cfr = F["fert"] * (1 - r) - max(extra_manure, 0.0) - struvite
    cfr = max(cfr, p["min_specialty_fert"])
    cfr_reduction = (F["fert"] - cfr) / F["fert"]
    # --- ACS 流失响应：规模弹性（幂<1，边际递减）× 矿物肥份额强度 ---
    # 有机肥磷释放缓慢、流失风险低于速效矿物肥（文献支持），故流失强度随
    # 矿物肥占比下降而降低；这是 S2.2×S4.3 协同效应的机制基础。
    total_in = cfr + manure_applied + (F["total_in"] - F["fert"] - F["manure_applied"])
    rel = total_in / F["total_in"]
    share = cfr / max(total_in, 1e-6)
    share0 = F["fert"] / F["total_in"]
    acs_loss = (F["runoff"] + F["erosion"]) * rel ** 0.8 * (share / share0) ** 0.5
    legacy = F["legacy"] * rel ** 0.8
    # --- 汇总指标 ---
    npr_rock = cfr / p["ore_grade_P"]
    cis_loss = cfr / 0.74 - cfr
    nonfert_env = F["nonfert"] * 0.3 * (cis_loss / F["cis_loss"])
    rcs_env = ((F["sewage"] - 0.44 * 0.8 * F["sewage"]) * (sewage / F["sewage"])
               * (1 - rec * 0.8) + 0.35 * 0.44 * 0.8 * sewage
               + 0.5 * F["waste"] * (1 - 0.2 * diet))
    env_total = cis_loss + acs_loss + lbs_env + rcs_env + nonfert_env
    return dict(CFR=cfr, CFR_reduction=cfr_reduction,
                NPR=npr_rock, NPR_reduction=1 - npr_rock / F["npr_rock"],
                env_total=env_total,
                env_reduction=1 - env_total / F["env_total_bau"],
                feed_total=feed_total, feed_reduction=1 - feed_total / F["feed_total"],
                manure_applied=manure_applied, struvite=struvite,
                pue_lv=pue_lv, mu=mu, acs_loss=acs_loss, lbs_env=lbs_env,
                rcs_env=rcs_env, cis_loss=cis_loss, legacy=legacy)


SCENARIO_DEFS = [
    ("BAU 2050", dict()),
    ("S2.2_Reduce", dict(r=0.20)),
    ("S4.3_Replace", dict(mu_target=0.75)),
    ("S4.5_Recycle", dict(rec=0.60)),
    ("3R", dict(r=0.20, mu_target=0.75, rec=0.60)),
    ("S5", dict(r=0.20, mu_target=0.75, rec=0.60, feed_eff=0.30, diet=0.15)),
]


def run_scenarios(pop_ratio):
    F = build_bau_2050(pop_ratio)
    rows = []
    for name, kw in SCENARIO_DEFS:
        res = simulate_3r(F, **kw)
        rows.append(dict(情景=name, CFR_ktP=res["CFR"],
                         CFR削减=res["CFR_reduction"],
                         NPR_ktrock=res["NPR"], NPR削减=res["NPR_reduction"],
                         环境流失_ktP=res["env_total"],
                         流失削减=res["env_reduction"]))
    return F, pd.DataFrame(rows)


# ------- 交叉敏感性回归（改编自课程提供 有交叉项.py）-------
def cross_sensitivity_analysis(data, var1, var2, target_col, controls=()):
    """均值中心化交互项 + Z-score 标准化多元回归。
    controls: 作为控制变量纳入的其余政策变量（分离交互效应）。"""
    data = data.copy()
    X1_c = data[var1] - data[var1].mean()
    X2_c = data[var2] - data[var2].mean()
    inter = f"{var1}*{var2}"
    data[inter] = X1_c * X2_c
    cols = [var1, var2, inter] + [c for c in controls if c not in (var1, var2)]
    X = data[cols]
    y = data[target_col]
    X_std = StandardScaler().fit_transform(X)
    y_std = StandardScaler().fit_transform(y.values.reshape(-1, 1)).flatten()
    model = sm.OLS(y, sm.add_constant(X)).fit()
    model_std = sm.OLS(y_std, sm.add_constant(X_std, has_constant="add")).fit()
    beta12_std = model_std.params[cols.index(inter) + 1]  # 标准化交互系数
    p_inter = model.pvalues[inter]
    if p_inter < 0.05:
        effect = "协同增强" if beta12_std > 0 else "拮抗削弱"
    else:
        effect = "无显著交互作用"
    return dict(var1=var1, var2=var2, r2=model.rsquared,
                beta_var1=model.params[var1], p_var1=model.pvalues[var1],
                beta_var2=model.params[var2], p_var2=model.pvalues[var2],
                beta_inter=model.params[inter], p_inter=p_inter,
                beta_inter_std=beta12_std, effect=effect)


def monte_carlo_scenario(F, n=600, seed=42, noise=0.02):
    """在 3R 政策强度空间抽样生成回归样本；目标 = 总磷削减量（相对 BAU）。"""
    rng = np.random.default_rng(seed)
    recs = []
    for _ in range(n):
        r = rng.uniform(0.0, 0.20)
        mu = rng.uniform(0.35, 0.60)
        rec = rng.uniform(0.0, 0.40)
        res = simulate_3r(F, r=r, mu_target=mu, rec=rec)
        red = F["env_total_bau"] - res["env_total"]
        red *= (1 + rng.normal(0, noise))       # 观测噪声
        recs.append(dict(S22=r, S43=mu, S45=rec, 削减量=red))
    return pd.DataFrame(recs)


if __name__ == "__main__":
    p22, p50 = load_population_projection()
    pop_ratio = p50 / p22
    print(f"人口增长比 (2050 Medium / 2022 Estimates) = {pop_ratio:.4f}\n")
    F, tbl = run_scenarios(pop_ratio)
    print("=== 2050 情景对比（相对 2050 BAU）===")
    show = tbl.copy()
    for c in ["CFR削减", "NPR削减", "流失削减"]:
        show[c] = (show[c] * 100).round(1).astype(str) + "%"
    print(show.round(0).to_string(index=False))
    print("\n=== 交叉敏感性回归（目标：总磷削减量, n=600）===")
    data = monte_carlo_scenario(F)
    for v1, v2 in [("S22", "S43"), ("S22", "S45"), ("S43", "S45")]:
        ctrl = tuple(v for v in ("S22", "S43", "S45") if v not in (v1, v2))
        res = cross_sensitivity_analysis(data, v1, v2, "削减量", controls=ctrl)
        print(f"{v1} × {v2}: R²={res['r2']:.3f}, β12={res['beta_inter']:.1f} "
              f"(标准化 {res['beta_inter_std']:.3f}), p={res['p_inter']:.2e} → {res['effect']}")
