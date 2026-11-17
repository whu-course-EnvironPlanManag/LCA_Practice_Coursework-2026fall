"""
00_config.py — 全局参数与路径配置（唯一硬编码处）
【AI 辅助编程提示词记录】
Prompt: "编写 Python 全局配置模块，包含路径、功能单位、Weibull 参数、汇率、WACC、中文字体。"
是否经人工校验：是
"""
import os
import matplotlib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data_cohort")
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results_output")
FIGURES_DIR = os.path.join(PROJECT_ROOT, "figures_output")
REPORT_DIR = os.path.join(PROJECT_ROOT, "report")
for d in [RESULTS_DIR, FIGURES_DIR]:
    os.makedirs(d, exist_ok=True)

FUNCTIONAL_UNIT = "1 kWh 电池全寿命周期交付电量"
WEIBULL_ETA_YEARS = 8.0
WEIBULL_BETA = 3.2
USD_TO_CNY = 7.0
WACC = 0.08
PLANT_LIFE_YEARS = 15
DISCOUNT_RATE = 0.08
LI2CO3_PRICES_CNY = {"low": 70000, "baseline": 154000, "high": 350000}
SOH_LSV_LOWER = 0.85
SOH_ESS_LOWER = 0.80
SOH_CBS_LOWER = 0.70
GRID_CARBON_FACTOR = 0.581
GREEN_CARBON_FACTOR = 0.020

matplotlib.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False
FIG_DPI = 300

def capital_recovery_factor(rate=WACC, years=PLANT_LIFE_YEARS):
    return rate * (1 + rate) ** years / ((1 + rate) ** years - 1)
