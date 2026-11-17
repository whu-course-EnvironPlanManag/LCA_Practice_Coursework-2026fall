# -*- coding: utf-8 -*-
"""
任务1：农田种植子系统 ACS 磷收支（生产口径 P_result 版）
数据源：Agricultural products_P_result_national level（1961-2022）.xlsx
  - 宽表：Country × Product(A-M 编码) × 年份(1961..2022)
  - 数值已是纯磷量，单位：吨 P（无需再配含磷系数表相乘）
路径策略：
  - 以脚本所在目录(__file__)为锚点拼相对子目录，不受运行目录(cwd)影响；
  - 自动在数据目录里找文件名含 result 的 .xlsx，避免全角/半角括号、空格不一致导致找不到；
  - 不写死 C 盘绝对路径，满足 GitHub 跨设备复现要求。
"""
import os
import glob
import pandas as pd

# ============ 数据目录（相对脚本所在目录） ============
DATA_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "source_data", "Origin data",
    "2.Country-level raw data on agricultural production and P calculations",
)

# ============ 农田磷输入参数（单位：吨P；按讲义/课程数据调整） ============
FERT_P = 20_500_000.0      # 化肥输入（文档基准：2022 约 20.5 Mt P）
MANURE_P = 6_000_000.0     # 有机肥还田 P（按讲义填）
DEPO_P = 600_000.0         # 大气沉降 P（按讲义填）
LOSS_RATE = 0.25           # 流失系数（占总输入比例）
TARGET_YEAR = 2022


def locate_result_file():
    """在数据目录 / 脚本同目录自动定位 P_result 的 xlsx。"""
    search_dirs = [DATA_DIR, os.path.dirname(os.path.abspath(__file__))]
    for d in search_dirs:
        if os.path.isdir(d):
            xlsxs = glob.glob(os.path.join(d, "*.xlsx"))
            # 优先文件名含 result 的文件
            xlsxs.sort(key=lambda p: (0 if "result" in os.path.basename(p).lower() else 1, p))
            if xlsxs:
                return xlsxs[0]
    # 找不到时，把目录内容列出来辅助排查
    listing = ""
    if os.path.isdir(DATA_DIR):
        listing = "\n目录内文件:\n" + "\n".join(os.listdir(DATA_DIR))
    raise FileNotFoundError(
        f"未找到 P_result 的 .xlsx。请核对目录:\n{DATA_DIR}{listing}"
    )


class ACSPModel:
    """农田种植子系统：输入磷 → 作物吸收 / 流失 / 土壤库存变化。"""

    def __init__(self, fert_p, manure_p, depo_p, loss_rate, harvest_p):
        self.fert_p = fert_p
        self.manure_p = manure_p
        self.depo_p = depo_p
        self.loss_rate = loss_rate
        self.harvest_p = harvest_p
        self.total_input = fert_p + manure_p + depo_p
        self.p_loss = 0.0
        self.p_stock = 0.0

    def run(self):
        self.p_loss = self.total_input * self.loss_rate
        self.p_stock = self.total_input - self.harvest_p - self.p_loss
        return {
            "total_input": self.total_input,
            "crop_uptake": self.harvest_p,
            "p_loss": self.p_loss,
            "stock_change": self.p_stock,
        }


def load_world_harvest(path):
    """读取 P_result 表，返回 (原始df, World行df, 各年份全球作物携出磷时序 Series)。"""
    df = pd.read_excel(path, engine="openpyxl")
    world = df[df["Country"].astype(str).str.strip().str.lower() == "world"].copy()
    years = [c for c in df.columns if isinstance(c, int)]
    # 每个年份：World 下各产品编码磷量求和 = 当年全球作物携出磷
    ts = world[years].sum(axis=0)
    return df, world, ts


if __name__ == "__main__":
    print("脚本所在目录:", os.path.dirname(os.path.abspath(__file__)))
    result_path = locate_result_file()
    print("已定位数据文件:", result_path)

    df_raw, df_world, ts = load_world_harvest(result_path)

    # 1961-2022 纯磷产出时序（任务1要求）
    print("\n===== 1961-2022 全球作物携出磷时序（吨P） =====")
    print(f"起始 1961: {ts[1961]:,.2f}")
    print(f"目标 {TARGET_YEAR}: {ts[TARGET_YEAR]:,.2f}")
    print(f"时序峰值: {ts.idxmax()} 年, {ts.max():,.2f}")

    # 2022 作物携出磷（World 各编码合计）
    harvest_2022 = float(ts[TARGET_YEAR])

    acs = ACSPModel(FERT_P, MANURE_P, DEPO_P, LOSS_RATE, harvest_2022)
    res = acs.run()

    print("\n===== 【任务1】2022 ACS 农田子系统磷收支（单位：吨P） =====")
    print(f"总磷输入:     {res['total_input']:,.3f}")
    print(f"作物吸收带走: {res['crop_uptake']:,.3f}")
    print(f"磷流失量:     {res['p_loss']:,.3f}")
    print(f"土壤库存变化: {res['stock_change']:,.3f}")

    # 附：2022 World 各产品编码磷量（A-M），需要编码对照表才能还原作物名
    print("\n===== 2022 World 各产品编码磷量（吨P） =====")
    print(df_world[["Product", TARGET_YEAR]].to_string(index=False))
