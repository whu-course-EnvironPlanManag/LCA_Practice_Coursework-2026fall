# -*- coding: utf-8 -*-
"""全局参数与路径配置（无硬编码绝对路径，全部相对本文件定位）。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]          # reproduction/
LECTURE = ROOT.parent                               # lecture15-.../
SRC_DATA = LECTURE / "source_data"
OUT_DATA = ROOT / "data_processed"
FIG = ROOT / "figures"
for d in (OUT_DATA, FIG):
    d.mkdir(parents=True, exist_ok=True)

USGS_FILE = SRC_DATA / "Origin data" / "1.Phosphate rock origin data" / \
    "Phosphate rock (P2O5) production data-national level (USGS,1998-2022).xlsx"

# 单位换算：论文口径 8,809 Mt 磷矿石 ↔ 2,643 Mt P2O5 ↔ 1,153 Mt P
GRADE_P2O5 = 2643 / 8809          # 30.0% 矿石品位
P2O5_TO_P = 1153 / 2643           # 0.4364 P2O5→P
ROCK_TO_P = GRADE_P2O5 * P2O5_TO_P  # 0.1309

# 2022 年全球磷物质流快照（Mt P/a）。数值来源见 params_2022 中的 source 字段
P_2022 = dict(
    mined=23.33,          # USGS 2021 全球矿石 178.2 Mt × 0.1309（2022 数据缺，沿用）
    ore_to_cis=22.53,     # 进入磷化工的矿石磷
    fert=20.50,           # 矿物磷肥消费（Liu et al. 2026, 正文）
    industrial=1.60,      # 工业磷酸盐
    deposition=2.00,      # 大气沉降（SI Text/Fig. S4 量级）
    seed=0.60,            # 种子
    forage=7.00,          # 牧草/天然草地输入（非耕地来源）
    ind_feed=1.20,        # 工业饲料磷
    byproduct=0.60,       # 农副产物饲料
    import_feed=1.80,     # 饲料净进口（= 工业饲料 + 副产物，保证闭合）
    manure_recycle=5.00,  # 粪肥还田
    sludge_recycle=2.50,  # 污泥回用
    straw_return=0.90,    # 秸秆还田
    harvest=9.90,         # 作物收获带出（PUE=31.4%）
    runoff=3.60,          # 农田径流流失
    food=7.40,            # 进入食物链的作物磷
    feed_crop=1.60,       # 作物饲料
    animal_products=2.40, # 动物产品磷（畜禽 PUE=23.1%）
    pasture_soil=1.20,    # 牧场土壤遗留
    field_loss=0.50,      # 粪肥田间流失
    manure_waste=1.30,    # 粪污进处理系统
    eaten=8.10,           # 居民摄入
    food_waste=1.70,      # 食物浪费
    ww=4.50,              # 生活污水进处理厂
    rural_direct=3.60,    # 农村直排
    landfill=1.00,        # 污泥填埋
    discharge=4.00,       # 处理尾水排放
    outflow=2.20,         # 河流入海
)

# 2022 参数来源标注（写入 model_parameters.json，供报告溯源）
SOURCE_2022 = {
    "mined": "USGS 1998–2022 国家级矿石产量（本文件）；2021 年 178.2 Mt × 0.1309",
    "fert": "Liu et al. (2026) 正文：2022 年矿物磷肥 20.5 Mt P",
    "harvest": "由农田 PUE≈31% 反推（正文：2050 BAU 作物 PUE 31%）",
    "animal_products": "畜禽 PUE 23%（正文历史均值 23%）",
    "food": "正文：每年施入磷中约 30% 进入食物",
    "deposition/seed/forage/ind_feed/byproduct": "SI Text S2–S4 清单口径量级",
    "manure_recycle/sludge_recycle/landfill/discharge": "工程假设（缺原始县级清单，按全球均值设定）",
    "import_feed": "平衡项，等于工业饲料 + 农副产物（贸易净输入）",
}

# 2050 BAU 与情景锚点（相对 BAU 的百分比变化，取自论文 Fig. 4A 与任务书 §5.2）
SCEN_2050 = dict(
    bau=dict(npr=26.9, cfr=26.9, loss=69.9, pue_crop=0.31, pue_livestock=0.16,
             recover_crop=0.17, recover_livestock=0.50, recover_consumption=0.09),
    s22=dict(npr=-0.096, cfr=-0.200, loss=-0.12),   # 化肥减施 20%
    s43=dict(npr=-0.2215, cfr=-0.769, loss=-0.77),  # 粪污还田 75%
    recycle=dict(npr=-0.06, loss=-0.18),            # 鸟粪石回收 60%
    s5=dict(npr=-0.97, loss=-0.65),                 # 全措施综合
    synergy=0.25,                                    # 耦合项（由 S5 反演）
)

SEED = 20261117
