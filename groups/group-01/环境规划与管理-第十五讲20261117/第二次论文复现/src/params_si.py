# -*- coding: utf-8 -*-
"""论文 SI 系数表（Table S3 / S4 / S15）整理。

所有数值均逐条摘自 Liu et al. (2026) PNAS 补充材料文本
（提取自 groups/group-01/环境规划与管理-第十五讲20261117 的 PDF），
并注明出处，保证"数据真实"可追溯。
单位约定：质量流以吨 P 计（配合 config.T_PER_MT 折算 Mt）。
"""

# ============ PMS / CIS：磷矿-化工环节（Table S3，α 系数） ============
ALPHA = {
    "P_in_P2O5": 0.4364,            # α1 P2O5 中元素 P 含量（化学式计算）
    "PR_reserve_P": 0.28,           # α2 磷矿储量平均含磷 28%
    "PR_concentrate_P": 0.31,       # α3 选矿精矿平均含磷 31%
    "sand_waste_ratio": 1.0,        # α4 开采过程砂石废料产生系数 Mt/Mt 精矿
    "sand_P": 0.0008,               # α5 砂石废料平均含磷 0.08%
    "primary_PMS_ratio": 1.0,       # α6 开采过程初级 PMS 产生系数
    "PMS_P": 0.0388,                # α7 PMS 平均含磷 3.88%
    "tailings_ratio": 3.2,          # α8 尾矿产生系数 Mt/Mt 精矿
    "tailings_P": 0.038,            # α9 尾矿平均含磷 3.8%
    "secondary_PMS_ratio": 0.2,     # α10 次级 PMS 产生系数 Mt/Mt 原矿
    "phosphogypsum_ratio": 4.8,     # α11 磷石膏产生系数 Mt/Mt P2O5
    "phosphogypsum_P": 0.004,       # α12 磷石膏平均含磷 0.4%
    "ferroP_ratio": 0.1,            # α13 磷铁生产系数
    "ferroP_P": 0.224,              # α14 磷铁平均含磷 22.4%
    "elementalP_slag_ratio": 9.0,   # α15 黄磷渣生产系数
    "elementalP_slag_P": 0.013,     # α16 黄磷渣平均含磷 1.30%
    "thermal_PA_share": 0.55,       # α17 热法磷酸占黄磷产量比例 55%
    "detergent_share": 0.15,        # α18 非肥用途中洗涤剂占比 15%
    "food_additive_share": 0.25,    # α19 食品/饲料添加剂占比 25%
    "industrial_share": 0.50,       # α20 工业用途占比 50%
    "other_share": 0.10,            # α21 其他用途占比 10%
}

# ============ CIS：化工子系统（Table S4） ============
CIS = {
    "a1": 0.4236,        # 磷肥占化工磷产品比例（三角分布 41.48/42.36/45.84 取众数附近）
    "a2": 0.1201,        # 其他磷化工产品比例
    "b": 0.052,          # 黄磷/热法酸比例
    "feed_kappa": 0.0039,  # 饲料磷酸氢钙占产品比例 0.39%
    "Q_detergent_u": 3.264,  # 城市人均洗涤剂年用量 kg/(人·年)
    "Q_detergent_r": 4.74,   # 农村人均洗涤剂年用量 kg/(人·年)
    "kappa_detergent": 0.0011,  # 洗涤剂中 P 含量 0.11%
    "c": 0.80,           # 磷回收工艺比例
    "d": 1.00,           # 完全反应比例
    "kappa_ardealite": 0.0122,  # 磷渣中钙铝磷矿比例
}

# ============ ACS：农田种植子系统（Table S3/S4） ============
# 作物总磷吸收系数 κ_u,i（kg P/t 产量，Table S3）
UPTAKE_KG_T = {
    "rice": 4.1, "wheat": 5.1, "maize": 4.0, "barley": 5.1, "sorghum": 4.8,
    "millet": 4.5, "rye": 5.2, "oat": 6.0, "potato": 0.8, "sweet potato": 1.0,
    "cassava": 0.2, "soybean": 0.2, "rapeseed": 7.0, "olive": 0.7,
    "sugar beet": 0.7, "sugarcane": 0.3, "seed cotton": 16.0,
    "vegetable and melon": 0.7, "fruit": 0.8,
}
# 作物收获物含磷系数 κ_h,i（kg P/t 产量，Table S3）
HARVEST_KG_T = {
    "rice": 2.9, "wheat": 3.7, "maize": 2.7, "barley": 3.6, "sorghum": 3.4,
    "millet": 3.5, "rye": 3.6, "oat": 3.8, "potato": 0.7, "sweet potato": 1.0,
    "cassava": 0.1, "soybean": 0.2, "rapeseed": 7.0, "olive": 0.2,
    "sugar beet": 0.5, "sugarcane": 0.3, "seed cotton": 12.2,
    "vegetable and melon": 0.2, "fruit": 0.4,
}
ACS = {
    "beta1_residue_fertilizer": 0.40,  # β1 作物秸秆还田作有机肥比例 40%
    "beta2_residue_feed": 0.25,        # β2 秸秆作饲料比例 25%
    "s_deposition_kg_km2a": 25.0,      # s 大气沉降 25 kg P/(km²·a)（Table S4）
    "kappa_drainage_kg_ha_a": 2.1,     # κ_drainage 农田排水流失 2.1 kg P/(ha·a)
    "kappa_leaching_kg_ha_a": 0.2,     # κ_leaching 农田淋溶 0.2 kg P/(ha·a)
    "h": 0.30,                         # h 其他磷输入（SD）系数 30%
    # λ 系数（Table S3，交叉验证用）：kg P/ha/yr
    "lambda1_depo_arable": 0.4,
    "lambda2_depo_grass": 0.4,
    "lambda3_runoff_arable": 1.8,
    "lambda4_runoff_grass": 0.6,
    "lambda5_leaching_arable": 0.34,
    "lambda6_leaching_grass": 0.34,
    "runoff_waste_coeff": 0.05,        # 工业/开采废弃物入水体径流系数 5%（SI Text）
}

# ============ LBS：畜禽养殖子系统 ============
LBS = {
    # κ_excretion,i 粪便磷排放 kg P/(头·年)（Table S4 均值）
    "excretion_kg_head_yr": {
        "pig": 1.14, "cow": 5.1, "sheep": 1.6, "poultry": 0.18, "rabbit": 0.18,
    },
    # kDC 系列（Table S3，头数口径的另一组系数，用于交叉验证）
    "kDC_kg_head_yr": {
        "buffalo": 15.2, "cattle": 5.6, "goat_sheep": 0.1, "horse": 6.8,
        "pig": 2.4, "chicken_per_1000": 135.0, "duck_per_1000": 384.0,
    },
    # 粪污还田比例 return rate（Table S4）
    "manure_return_rate": {
        "pig": 0.65, "cow": 0.70, "sheep": 0.40, "poultry": 0.55, "rabbit": 0.55,
    },
    "beta3_manure_fertilizer": 0.67,   # β3 畜禽粪便用作有机肥比例 67%
    "beta4_feed_additive": 0.005,      # β4 饲料添加剂 P 占比 0.5%
    # κ_AP 动物产品含磷率（kg P/kg 产品，Table S4）
    "product_P_frac": {
        "pork": 0.13, "beef": 0.168, "mutton": 0.146, "poultry_meat": 0.139,
        "aquatic": 0.185, "egg": 0.162, "milk": 0.073, "sugar": 0.003, "honey": 0.162,
    },
    # 食品级 P 含量 mg/100g（Table S3 ka 系列，供食物供给口径）
    "ka_mg_100g": {
        "beef_buffalo": 165, "mutton": 337, "pork": 202, "poultry_meat": 203,
        "other_meat": 214, "egg": 204, "milk": 110,
    },
    "epsilon_processing_loss": 0.12,   # ε 屠宰/加工损失比例 12%
    "lambda_processing_loss": 0.10,    # λ 加工损失比例 10%
}

# ============ RCS：居民消费子系统 ============
RCS = {
    "beta5_human_excretion_kg_capita_yr": 0.47,  # β5 人均年排磷 0.47 kg P
    "beta6_rural_excreta_reuse": 0.44,           # β6 农村人粪尿直接还田比例 44%
    "beta7_urban_excreta_reuse": 0.22,           # β7 城市人粪尿还田比例 22%
    # 人均食物磷摄入/浪费（kg P/(人·年)，Table S4）
    "Pu_mean": 0.59, "Pu_waste": 1.26,   # 城市 摄入/浪费
    "Pr_mean": 0.59, "Pr_waste": 0.84,   # 农村 摄入/浪费
    # φ 系列（Table S4）：消费端路径分配比例
    "phi1": 0.568, "phi2": 0.271, "phi3": 0.056, "phi4": 0.893, "phi5": 0.957,
    "phi6": 0.10, "phi7": 0.70, "phi8": 0.307, "phi9": 0.657, "phi10": 0.506,
    "kappa_domestic_water": 0.00082,     # 生活污水中 P 比例
    "kitchen_refuse_frac": 0.05,          # 厨余占生活垃圾比例
    "Q_waste_u_kg_person_day": 0.525,     # 城市人均生活垃圾 kg/(人·日)
    "Q_waste_r_kg_person_day": 0.96,      # 农村人均生活垃圾 kg/(人·日)
    "treatment_rate_range": (0.0611, 0.975),  # 污水处理率（国家差异 6.11%-97.5%）
    "struvite_recovery_default": 0.30,    # 现状污水磷回收（鸟粪石）比例假设（基准情景）
}

# ============ 情景参数（任务3：3R + Table S15） ============
SCENARIOS = {
    # 任务书指定的 3R 参数（优先级高于 Table S15 的 30%/100%）
    "R_fertilizer_reduction": 0.20,       # Reduce：化肥减施 20%（S2.2）
    "R_manure_compost_rate": 0.75,        # Replace：粪便堆肥还田率提升至 75%（S4.3）
    "R_struvite_recovery": 0.60,          # Recycle：污水鸟粪石回收率提升至 60%
    # Table S15 其他情景（供扩展）
    "S2.3_feed_conversion_gain": 0.314,   # 饲料转化率提升 31.4%
    "S2.4_aquaculture_gain": 0.50,        # 综合养殖提升 50%
    "S4.1_PG_tailings_recovery": 0.60,    # 磷石膏/尾矿回收提至 60%
    "S3.2_food_loss_reduction": 0.80,     # 食物损失削减 80%
}

# ============ PUE / PRR 定义（SI Text S4） ============
# PUE_{c/a} = P_product / P_input
#   c=种植、a=养殖；P_input 含饲料、添加剂与进口的畜禽产品磷
# PRR_{c/a/u/r} = REC / W
#   秸秆/粪污/城市废物/农村废物的回收量 W 与其再回用 REC 之比
# 生命周期磷消费 PC_{a→c} = (P_newinput + P_food_output) / P_food_output
#   new input = 化肥 + 种子 + 大气沉降 + 进口饲料磷

# ============ 论文关键基准（任务书第五节，用于对照核验） ============
BENCHMARKS = {
    "cumulative_PR_P_1961_2022_Mt": 1153.0,     # 累计磷矿进入社会系统纯磷
    "fert_P_1961_Mt": 4.9,                      # 矿物磷肥施用量 1961
    "fert_P_2022_Mt": 20.5,                     # 矿物磷肥施用量 2022
    "ACS_fertilizer_share_min": 0.64,           # 2022 化肥占 ACS 磷输入 >64%
    "ACS_PUE_mean": 0.31,                       # 种植业 PUE ≈31%
    "LBS_PUE_mean": 0.23,                       # 养殖业 PUE ≈23%
    "S4.3_NPR_cut": -0.2215, "S4.3_CFR_cut": -0.769, "S4.3_loss_cut": -0.77,
    "S2.3_IFD_cut": -0.26, "S2.3_FGD_cut": -0.35, "S2.3_NPR_cut": -0.17,
    "S2.3_crop_PUE_gain": 0.18, "S2.3_livestock_PUE_gain": 0.36,
    "S5_NPR_cut": -0.97, "S5_loss_cut_range": (-0.33, -0.98),
    "regression_R2_min": 0.85,
    "PUE_targets": {"basic": 0.50, "medium": 0.60, "high": 0.70},
}
