# -*- coding: utf-8 -*-
"""全局配置：数据路径与模型参数（所有路径均为相对路径，可通过环境变量覆盖）"""
import os
from pathlib import Path

# 数据目录：优先环境变量 P_SFA_DATA_DIR，否则使用项目内 source_data（相对路径）
DATA_DIR = Path(os.environ.get("P_SFA_DATA_DIR",
                Path(__file__).resolve().parent / "source_data"))
OUT_DIR = Path(__file__).resolve().parent / "output"
OUT_DIR.mkdir(exist_ok=True)

# ---------- 数据文件相对路径 ----------
F_PROD = DATA_DIR / "Supplementary_dataset_PNAS_First_Revision" / \
    "1.Country-level raw data on agricultural production and P calculations" / \
    "Agricultural products_P_result_national level（1961-2022）.xlsx"
F_COEF = DATA_DIR / "Supplementary_dataset_PNAS_First_Revision" / \
    "3.P content coefficient of products_Production.xlsx"
F_POP = DATA_DIR / "Supplementary_dataset_PNAS_First_Revision" / \
    "7.Global population projection data for P sustainability scenario analysis.xlsx"
F_ANIMAL_DIR = DATA_DIR / "Origin data" / \
    "5.Original data on live animal products (national-level production and trade)" / \
    "Production and stock"
F_FOODP = DATA_DIR / "Origin data" / "9.Other datasets" / \
    "Global national level food phosphorus supply data.csv"

# 类别 → 食品组 映射（据含磷率字典 Sheet1 图例列）
CATEGORY_MAP = {
    "A": "Non-food agricultural products", "B": "Fruits and vegetables",
    "C": "Raw materials for oils, fats and sugars", "D": "Kitchen condiments",
    "E": "Cereals", "F": "Pulses", "G": "Animal products", "H": "Cakes",
    "I": "Other", "J": "Alcohol and beverages", "K": "Forage",
    "L": "Uncategorized", "M": "Live animals",
}
CROP_CATEGORIES = ["A", "B", "C", "D", "E", "F", "H", "I", "J", "K"]  # 植物性产品
ANIMAL_CATEGORIES = ["G", "M"]                                        # 动物性产品

# ---------- 2022 年基准模型参数（单位：kt P）----------
# 文献校准锚点：Liu et al. (2026) PNAS 及公开文献
P2022 = dict(
    # PMS / CIS
    fert_2022=20500.0,        # 矿物磷肥施用（任务书基准 20.5 Mt P）
    nonfert_share=0.12,       # 磷矿非肥料用途（饲料添加剂等）占比
    ore_grade_P=0.30 * 0.4364,  # 磷矿品位：30% P2O5 折纯磷
    # ACS
    deposition=1250.0,        # 大气沉降（S×s，文献系数）
    seed=450.0,               # 种子携带磷
    sludge_to_field=1100.0,   # 污泥农用有机输入
    compost_to_field=900.0,   # 厨余堆肥农用
    residue_return_ratio=0.55,  # 秸秆（地上部残留）还田比例
    harvest_ratio=0.70,       # 吸收量中收获部分比例
    runoff_coef=0.150,        # 地表径流+淋溶系数（占土壤输入）
    erosion_coef=0.045,       # 侵蚀系数
    # LBS
    animal_product_P=5000.0,  # 畜产品产出纯磷（肉奶蛋，文献校准）
    lbs_pue=0.23,             # 养殖系统 PUE（任务书基准 23%）
    gaseous_ratio=0.10,       # 养殖气态损失占饲料比例
    manure_env_ratio=0.26,    # 未还田粪污进入环境比例，余为暂存
    # LBS 饲料结构
    feed_from_crop=3500.0,    # 饲料粮（ACS→LBS）
    feed_from_byproduct=2500.0,  # 加工副产物与进口饲料
    # RCS
    food_waste_ratio=0.25,    # 家庭食物浪费比例
    detergent_P=500.0,        # 日化等非食品磷
    sewage_treated=0.55,      # 污水处理率
    p_removal=0.80,           # 处理过程除磷率
    sludge_to_field_ratio=0.65,  # 污泥农用比例
    kitchen_to_feed=0.50,     # 厨余转为饲料/堆肥比例
    # 汇总校准
    legacy_target=None,       # 由守恒平衡项自动得出
)

# 2050 BAU 情景参数（据论文：CFR 26.9、磷矿 205.1、PUE 31%/16%/31%、环境流失 69.9）
P2050_BAU = dict(
    pop_growth=None,          # 由人口预测数据读取（Medium variant 2050/2022）
    diet_factor=1.0,          # 人均膳食结构因子（校准至 CFR=26.9）
    fert_target=26900.0,      # 论文 BAU 2050 化肥需求（kt P）
    rock_target=205100.0,     # 论文 BAU 2050 磷矿需求（kt，品位<30%）
    ore_grade_P=0.30 * 0.4364,
    lbs_pue=0.16,             # 论文 BAU 2050 养殖 PUE 16%
    crop_pue=0.31,            # 论文 BAU 2050 种植 PUE 31%
    cons_pue=0.31,            # 消费系统 PUE 31%
    manure_util_bau=0.335,    # BAU 粪污还田利用率（校准 S4.3 杠杆）
    manure_util_target=0.75,  # 3R 情景目标利用率（任务书 75%）
    env_loss_target=69900.0,  # 论文 BAU 2050 环境流失总量（kt P）
    food_P_target=16200.0,    # 论文 BAU 2050 满足基本需求食物磷（kt P）
    # 环境流失分摊（据论文 36.3/19.5/14.1）
    load_cropland=36300.0, load_noncropland=19500.0, load_water=14100.0,
    # 政策协同耦合系数：化肥减施提升粪肥还田积极性（见报告讨论）
    psi=0.5,
    struvite_target=0.60,     # 鸟粪石回收率（任务书 60%）
    min_specialty_fert=800.0, # 特种用途化肥刚性需求下限（对应 S5 NPR -97%）
)

# 3R 情景定义（相对 2050 BAU）
SCENARIOS = {
    "BAU":  dict(r=0.0, mu=0.335, rec=0.0),
    "S2.2_Reduce":   dict(r=0.20, mu=0.335, rec=0.0),
    "S4.3_Replace":  dict(r=0.0, mu=0.75, rec=0.0),
    "S4.5_Recycle":  dict(r=0.0, mu=0.335, rec=0.60),
    "3R":   dict(r=0.20, mu=0.75, rec=0.60),
    "S5":   dict(r=0.20, mu=0.75, rec=0.60, extra=dict(feed_eff=0.30, diet=0.15)),
}
