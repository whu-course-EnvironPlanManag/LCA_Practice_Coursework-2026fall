"""路径、单位与类别配置。

所有路径均由本文件推导，禁止写死本机绝对路径；外部数据目录可通过
命令行参数 --data-dir 覆盖（见 run_all.py）。
"""
from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------- 目录
BASE_DIR = Path(__file__).resolve().parent.parent          # submission_p_sfa/
PROJECT_DIR = BASE_DIR.parent                              # 第十五讲课程包
DEFAULT_DATA_DIR = PROJECT_DIR / "source_data"
# 补充数据（codex 交付，不修改原始课程材料）
DEFAULT_EXTRA_DIR = BASE_DIR / "data_extra"

PARAMS_DIR = BASE_DIR / "params"
RESULTS_DIR = BASE_DIR / "results"
FIGURES_DIR = BASE_DIR / "figures"
REPORT_DIR = BASE_DIR / "report"

# ---------------------------------------------------------------- 数据相对路径
REL = {
    "product_p": (
        "Supplementary_dataset_PNAS_First_Revision/"
        "1.Country-level raw data on agricultural production and P calculations/"
        "Agricultural products_P_result_national level（1961-2022）.xlsx"
    ),
    "p_coefficient": (
        "Supplementary_dataset_PNAS_First_Revision/"
        "3.P content coefficient of products_Production.xlsx"
    ),
    # 分年度原始产量（FAOSTAT 长表），仅用于字典加权交叉校验
    "raw_production": (
        "Supplementary_dataset_PNAS_First_Revision/"
        "1.Country-level raw data on agricultural production and P calculations/"
        "Raw data on agricultural production（1961-2022）"
    ),
    "population": (
        "Supplementary_dataset_PNAS_First_Revision/"
        "7.Global population projection data for P sustainability scenario analysis.xlsx"
    ),
    "fertilizer": (
        "Origin data/7.Global and national level CPF application and trade data/"
        "Nutrient phosphate P2O5 use data at the national level.csv"
    ),
    "phosphate_rock": (
        "Origin data/1.Phosphate rock origin data/"
        "Phosphate rock (P2O5) production data-national level (USGS,1998-2022).xlsx"
    ),
    "cropland": "Origin data/8.Global land use data/Global level cropland area.csv",
    "food_supply": "Origin data/9.Other datasets/Global national level food phosphorus supply data.csv",
    "exports": (
        "Supplementary_dataset_PNAS_First_Revision/"
        "2.Country-level origin data on agricultural trade and P calculations/"
        "Calculated data on P in agricultural exports at the national level.xlsx"
    ),
    "imports": (
        "Supplementary_dataset_PNAS_First_Revision/"
        "2.Country-level origin data on agricultural trade and P calculations/"
        "Calculated data on P in agricultural imports at the national level.xlsx"
    ),
}

# ---------------------------------------------------------------- 补充数据文件名
# 由 codex 数据交付说明中的 7 个 CSV 块落盘，口径见各文件 source/status 列。
EXTRA = {
    "seed_p": "seed_p_1961_2022.csv",                       # ESB_2025，Mt P
    "livestock": "livestock_heads_1961_2022.csv",            # QCL_2025 存栏 + 粪磷
    "grassland": "grassland_area_1961_2022.csv",             # RL_2026 永久草地面积
    "grass_proxy": "grassland_uptake_proxy.csv",             # Sattari 2016 区间代理
    "fert_trade_rfn": "fertilizer_trade_rfn_1961_2022.csv",  # RFN_2026 养分贸易 proxy
    "rock_ds140": "phosphate_rock_ds140.csv",                # USGS DS140 实物量
    "rock_myb": "phosphate_rock_myb.csv",                    # USGS MYB 成套 P2O5
}

# ---------------------------------------------------------------- 类别口径
# A 非食用农产品 / B 果蔬 / C 油糖原料 / D 调味 / E 谷物 / F 豆类
# G 动物产品 / H 饼粕 / I 其他 / J 酒饮 / K 饲草 / L(空列) / M 活体动物
CROP_CATEGORIES = ["A", "B", "C", "D", "E", "F", "H", "I", "J", "K"]
ANIMAL_CATEGORY = "G"
LIVE_ANIMAL_CATEGORY = "M"      # 与 G 口径重叠，仅用于核对，不计入流量
UNUSED_CATEGORIES = ["L"]

# 生产表中混入的区域聚合行，国家尺度分析必须剔除
AGGREGATE_COUNTRIES = {
    "World", "Asia", "Americas", "Europe", "Africa", "Oceania",
    "Africa (FAO)", "Asia (FAO)", "Europe (FAO)", "Oceania (FAO)",
    "Americas (FAO)", "World (FAO)",
}

# ---------------------------------------------------------------- 单位
# 全系统统一使用 Mt P（百万吨纯磷）
T_PER_MT = 1e6
# P2O5 -> P 的化学计量系数（SI Table S3, alpha1）
P2O5_TO_P = 0.4364
# 面积：1000 ha -> ha
KHA_TO_HA = 1e3
# 人口：千人 -> 人
KILO_PERSON = 1e3


def ensure_output_dirs() -> None:
    for d in (PARAMS_DIR, RESULTS_DIR, FIGURES_DIR, REPORT_DIR):
        d.mkdir(parents=True, exist_ok=True)
