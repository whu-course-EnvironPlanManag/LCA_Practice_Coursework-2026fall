# -*- coding: utf-8 -*-
"""全局路径与常量配置。

所有路径均相对本仓库根目录解析，禁止出现任何写死的绝对盘符路径，
以保证在他人机器上 `python run_all.py` 可直接运行（评分扣分项）。
"""
from pathlib import Path

# 本文件位于 <第十五讲目录>/第二次论文复现/src/config.py
THIS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = THIS_DIR.parent                      # 第二次论文复现

# 第十五讲课程资料目录（含 source_data），即本项目目录的上一级
LECTURE_DIR = PROJECT_DIR.parent
DATA_DIR = LECTURE_DIR / "source_data"

# ---- 关键数据文件（相对 source_data 的固定子路径）----
FR_DIR = DATA_DIR / "Supplementary_dataset_PNAS_First_Revision"
SR_DIR = DATA_DIR / "Supplementary Data_PNAS Second Revision"
ORIGIN_DIR = DATA_DIR / "Origin data"

# 任务1/回归：国家×品类纯磷产出宽表（1961-2022）
WIDE_PROD_TABLE = (FR_DIR / "1.Country-level raw data on agricultural production and P calculations"
                   / "Agricultural products_P_result_national level（1961-2022）.xlsx")
WIDE_PROD_SHEET = "product_P_result (tons)"

# 含磷率字典（产品级）
COEF_PROD = FR_DIR / "3.P content coefficient of products_Production.xlsx"
COEF_TRADE = FR_DIR / "4.P content coefficient of products_Trade.xlsx"

# 敏感性系数（验证目标）
SENS_PROD = FR_DIR / "5.Sensitivity Analysis Results_Production.xlsx"
SENS_TRADE = FR_DIR / "6.Sensitivity Analysis Results_Trade.xlsx"

# 人口预测（UN WPP 2019 中方案，含 SSP 路径）
POP_PROJ = FR_DIR / "7.Global population projection data for P sustainability scenario analysis.xlsx"

# 农田种植系统参考类
ACSP_REF_CODE = FR_DIR / "8.Code implementation of P_SFA modeling_cropping system case.py"

# 交叉敏感性回归：第二返修基准输出
CROSSSENS_PROD_REF = SR_DIR / "Results_CrossSensitivity_All Combinations_Production.xlsx"
CROSSSENS_TRADE_REF = SR_DIR / "Results_CrossSensitivity_All Combinations_Trade.xlsx"

# 回归算法参考代码
REG_CODE_DIR = SR_DIR / "PNAS Second Revision – Cross-Sensitivity Analysis Code"

# 化肥施用量（FAOSTAT Nutrient，P2O5 吨，国家级×年）
FERT_USE_CSV = ORIGIN_DIR / "7.Global and national level CPF application and trade data" / "Nutrient phosphate P2O5 use data at the national level.csv"

# 磷矿生产（USGS P2O5，国家级 1998-2022）
PR_PROD_XLSX = ORIGIN_DIR / "1.Phosphate rock origin data" / "Phosphate rock (P2O5) production data-national level (USGS,1998-2022).xlsx"

# 全球土地利用（耕地/草地面积）
CROPLAND_CSV = ORIGIN_DIR / "8.Global land use data" / "Global level cropland area.csv"
AGRI_LAND_CSV = ORIGIN_DIR / "8.Global land use data" / "Global level agricultural land area.csv"

# 人口与食物磷供给
POP_CSV = ORIGIN_DIR / "9.Other datasets" / "Global country-level population data.csv"
FOOD_P_CSV = ORIGIN_DIR / "9.Other datasets" / "Global national level food phosphorus supply data.csv"

# 贸易纯磷（国家级进出口，1961-2022）
TRADE_EXP_XLSX = (FR_DIR / "2.Country-level origin data on agricultural trade and P calculations"
                  / "Calculated data on P in agricultural exports at the national level.xlsx")
TRADE_IMP_XLSX = (FR_DIR / "2.Country-level origin data on agricultural trade and P calculations"
                  / "Calculated data on P in agricultural imports at the national level.xlsx")

# 畜禽存栏（LBS 粪便计算的活动数据）
LIVESTOCK_DIR = ORIGIN_DIR / "5.Original data on live animal products (national-level production and trade)" / "Production and stock"

# 原始 FAOSTAT 生产逐年 csv（交叉验证：产量×含磷率 vs 宽表）
RAW_PROD_DIR = (FR_DIR / "1.Country-level raw data on agricultural production and P calculations"
                / "Raw data on agricultural production（1961-2022）")

# ---- 输出目录 ----
OUTPUT_DIR = PROJECT_DIR / "output"
FIG_DIR = OUTPUT_DIR / "figures"
CSV_DIR = OUTPUT_DIR / "csv"
HTML_DIR = OUTPUT_DIR / "html"

for _d in (OUTPUT_DIR, FIG_DIR, CSV_DIR, HTML_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ---- 单位换算 ----
T_PER_MT = 1e6      # 吨 -> 百万吨 Mt
T_PER_KT = 1e3      # 吨 -> 千吨 kt
P_IN_P2O5 = 0.4364  # P2O5 中 P 的质量分数（SI Table S3, α1）

YEARS = list(range(1961, 2023))
