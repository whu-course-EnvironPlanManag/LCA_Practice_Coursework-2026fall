# -*- coding: utf-8 -*-
"""
课程名称：《环境规划与管理》
案例主题：工业园区二氧化碳捕集耦合绿氢合成绿色甲醇系统
任务编号：任务 1（学生实训脚本）
脚本名称：task1_mfa_recycle_solver.py
实训目标：
  1. 以反应器单程 CO2 转化率 X_sp 与驰放分流比 r_purge 作为真实输入参数，
     联立求解"新鲜进料—混合—反应—分离—分流"内循环回路的稳态物料平衡；
  2. 由模型自身算出的各物流组成（而非"输入减输出"倒算尾气）独立核验 C/H/O 元素守恒；
  3. 输出单吨产品（1,000 kg 精甲醇）与 10 万吨/年工程通量的物料、用水与电耗清单；
  4. 与 data_cohort 工程实测数据集逐流股比对，记录口径差异；
  5. 读取 task3 锚点 B 结果，按同一设计工况再输出一份 10 万吨/年通量清单，
     与报告表 2-2 逐项核对（基准工况与锚点 B 工况不混用取水口径）。

模型闭合假设（与数据集比对结果见运行输出）：
  * 净反应按 CO2 + 3H2 -> CH3OH + H2O 计，净 CO 生成量取 0；
  * 反应器入口 H2/CO2 摩尔比按化学计量 3.0 控制；
    该闭合条件可复现数据集 offgas 4,686 kg/t 与循环气 4,640 kg/t（偏差 < 0.1%）；
  * 分离器将甲醇与水全部冷凝，气相仅含未反应 CO2 与 H2；
  * 分流器按 r_purge 排放、其余回流，系统处于稳态。

注意：讲义提示的 RWGS 副产 CO（约 1.124 kmol/t）与数据集 offgas 4,686 kg/t 不自洽——
      在 1% 驰放比下循环回路会把净生成 CO 累积至 100 倍（约 112 kmol/t，即 3.1 t/t），
      使 offgas 增至约 6.9 t/t。故本模型采用"净 CO = 0"口径，详见输出中的口径差异记录。
"""

import sys
import io
import os

# 针对 Windows 控制台编码环境进行 UTF-8 容错封装
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import numpy as np
import pandas as pd

# ==============================================================================
# 1. 基础物理化学常数与分子量基准
# ==============================================================================
M_C = 12.011       # kg/kmol
M_H = 1.008        # kg/kmol
M_O = 15.999       # kg/kmol

# 分子量由元素质量统一定义，保证化学计量与元素核验口径完全一致
MW_CO2 = M_C + 2.0 * M_O        # 44.009
MW_H2 = 2.0 * M_H               # 2.016
MW_CH3OH = M_C + 4.0 * M_H + M_O  # 32.042
MW_H2O = 2.0 * M_H + M_O        # 18.015
MW_O2 = 2.0 * M_O               # 31.998

# 各组分元素组成（每 1 kmol 组分所含元素 kmol 数）
SPECIES = {
    "CO2":  {"MW": MW_CO2,   "C": 1.0, "H": 0.0, "O": 2.0},
    "H2":   {"MW": MW_H2,    "C": 0.0, "H": 2.0, "O": 0.0},
    "CH3OH": {"MW": MW_CH3OH, "C": 1.0, "H": 4.0, "O": 1.0},
    "H2O":  {"MW": MW_H2O,   "C": 0.0, "H": 2.0, "O": 1.0},
    "O2":   {"MW": MW_O2,    "C": 0.0, "H": 0.0, "O": 2.0},
}
M_ELEM = {"C": M_C, "H": M_H, "O": M_O}

# 功能单位基准：生产 1,000.0 kg 聚合级精甲醇 (纯度 >= 99.85 wt%)
PRODUCT_MEOH_KG = 1000.0

# 公用工程单耗基准（取自工程数据集与理论白皮书）
PEM_KWH_PER_KG_H2 = 52.0        # PEM 电解水制氢直流电耗
CO2_COMPRESSION_KWH = 255.0     # CO2 捕集与三级压缩（对应 1,423 kg/t 基准）
CO2_COMPRESSION_REF_KG = 1423.0
RECYCLE_COMPRESSION_KWH = 155.0  # 循环气增压与循环水泵（对应循环气 4,640 kg/t）
DISTILLATION_KWH = 120.0        # 双塔精馏与冷冻脱轻

# 工业取水：政策卡片给定的全厂新鲜除盐取水函数基准项 1.385 t/t（非园区定额 1.400 t/t，
# 亦非实测取水；未单列冷却补水、工艺损耗与产品带水分项）
COURSE_MAKEUP_WATER_TPT = 1.385  # t 水 / t 甲醇


def find_data_file(filename="mfa_reaction_recycle_balance.csv"):
    """跨层级自动查找工程数据集路径"""
    search_paths = [
        os.path.join("data_cohort", filename),
        os.path.join("..", "data_cohort", filename),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data_cohort", filename),
    ]
    for p in search_paths:
        if os.path.exists(p):
            return p
    return None


def load_anchor_b_purge_ratio():
    """
    读取 task3 锚点指标表中锚点 B 的驰放分流比，用于报告表 2-2（设计基准）通量核对。
    找不到结果文件时返回 None，由调用方提示先运行 task3；不在此处写死锚点数值。
    """
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "..", "results_output", "task3_anchor_metrics.csv")
    if not os.path.isfile(path):
        return None
    df = pd.read_csv(path)
    tag = df["锚点"].astype(str).str.strip().str.upper()
    sel = df[tag == "B"]
    if sel.empty:
        return None
    return float(sel.iloc[0]["驰放分流比 r_purge (%)"]) / 100.0


# ==============================================================================
# 2. 反应-循环系统物料平衡求解器
# ==============================================================================
def solve_mfa_balance(single_pass_conv=0.250, purge_ratio=0.010,
                      h2_co2_inlet_ratio=3.0):
    """
    以单程转化率与驰放分流比为输入，联立求解稳态循环回路物料平衡。

    方程（对反应器入口 CO2 摩尔流 a 进行代数联立）：
        a = n_co2_rxn / X_sp                                  （单程转化定义）
        n_co2_unrxn = a * (1 - X_sp)                          （反应器出口未反应 CO2）
        n_co2_fresh = n_co2_rxn + r_purge * n_co2_unrxn       （新鲜补料 = 消耗 + 驰放）
        n_co2_recycle = (1 - r_purge) * n_co2_unrxn           （分流器回流）
        n_co2_inlet = n_co2_fresh + n_co2_recycle = a         （混合器闭合）
    H2 通道完全对称，等效于 n_h2_rxn = 3 * n_meoh。

    参数：
      single_pass_conv  : 反应器单程 CO2 转化率 X_sp，基准 0.250 (25.0%)
      purge_ratio       : 分流器驰放分流比 r_purge，基准 0.010 (1.0% 驰放、99.0% 循环)
      h2_co2_inlet_ratio : 反应器入口 H2/CO2 摩尔比，按化学计量取 3.0（闭合条件）
    返回：
      单吨产品各物流的摩尔流 (kmol) 与质量流 (kg)，以及循环比、碳利用率等指标
    """
    if not 0.0 < single_pass_conv < 1.0:
        raise ValueError("单程转化率必须位于 (0, 1) 区间")
    if not 0.0 < purge_ratio < 1.0:
        raise ValueError("驰放分流比必须位于 (0, 1) 区间")
    if h2_co2_inlet_ratio < 3.0:
        raise ValueError("反应器入口 H2/CO2 摩尔比须不低于化学计量比 3.0")

    # ---------- 反应计量：净 CO2 + 3H2 -> CH3OH + H2O ----------
    n_meoh = PRODUCT_MEOH_KG / SPECIES["CH3OH"]["MW"]
    n_co2_rxn = n_meoh           # 净反应消耗 CO2
    n_h2_rxn = 3.0 * n_meoh      # 净反应消耗 H2

    # ---------- 单程转化率驱动反应器入口量 ----------
    n_co2_inlet = n_co2_rxn / single_pass_conv
    n_h2_inlet = h2_co2_inlet_ratio * n_co2_inlet

    # ---------- 反应器出口（未反应气） ----------
    n_co2_unrxn = n_co2_inlet - n_co2_rxn
    n_h2_outlet = n_h2_inlet - n_h2_rxn
    n_gas_offgas = n_co2_unrxn + n_h2_outlet

    # ---------- 分流器：驰放比真正决定排放与回流 ----------
    n_co2_purge = purge_ratio * n_co2_unrxn
    n_h2_purge = purge_ratio * n_h2_outlet
    n_co2_recycle = (1.0 - purge_ratio) * n_co2_unrxn
    n_h2_recycle = (1.0 - purge_ratio) * n_h2_outlet

    # ---------- 新鲜补料 = 反应消耗 + 驰放损失 ----------
    n_co2_fresh = n_co2_rxn + n_co2_purge
    n_h2_fresh = n_h2_rxn + n_h2_purge

    # ---------- 精馏与电解 ----------
    n_water = n_meoh          # 生成水与产品等摩尔
    n_oxygen = n_h2_fresh / 2.0  # 电解阳极副产 O2

    # ---------- 物流字典（单位：kmol / t 甲醇） ----------
    streams = {
        "fresh_co2":   {"CO2": n_co2_fresh},
        "fresh_h2":    {"H2": n_h2_fresh},
        "recycle":     {"CO2": n_co2_recycle, "H2": n_h2_recycle},
        "reactor_in":  {"CO2": n_co2_inlet,   "H2": n_h2_inlet},
        "reactor_out": {"CO2": n_co2_unrxn,   "H2": n_h2_outlet,
                        "CH3OH": n_meoh,      "H2O": n_water},
        "offgas":      {"CO2": n_co2_unrxn,   "H2": n_h2_outlet},
        "purge":       {"CO2": n_co2_purge,   "H2": n_h2_purge},
        "crude_meoh":  {"CH3OH": n_meoh,      "H2O": n_water},
        "product":     {"CH3OH": n_meoh},
        "water":       {"H2O": n_water},
        "oxygen":      {"O2": n_oxygen},
    }
    masses = {k: _stream_mass(v) for k, v in streams.items()}

    # ---------- 指标 ----------
    recycle_ratio_mass = masses["recycle"] / (masses["fresh_co2"] + masses["fresh_h2"])
    # 循环比统一定义为“循环气/新鲜气”；反应器总进料/新鲜进料另记为 feed_ratio_molar
    recycle_ratio_molar = (n_co2_recycle + n_h2_recycle) / (n_co2_fresh + n_h2_fresh)
    feed_ratio_molar = (n_co2_inlet + n_h2_inlet) / (n_co2_fresh + n_h2_fresh)
    eta_carbon = n_meoh / n_co2_fresh

    # ---------- 电耗 ----------
    e_h2 = PEM_KWH_PER_KG_H2 * masses["fresh_h2"]
    e_co2 = CO2_COMPRESSION_KWH * masses["fresh_co2"] / CO2_COMPRESSION_REF_KG
    e_recycle = RECYCLE_COMPRESSION_KWH * masses["recycle"] / 4640.0
    e_distill = DISTILLATION_KWH
    e_total = e_h2 + e_co2 + e_recycle + e_distill

    return {
        "single_pass_conv": single_pass_conv,
        "purge_ratio": purge_ratio,
        "h2_co2_inlet_ratio": h2_co2_inlet_ratio,
        "n_meoh_kmol": n_meoh,
        "n_co2_rxn_kmol": n_co2_rxn,
        "n_h2_rxn_kmol": n_h2_rxn,
        "n_co2_inlet_kmol": n_co2_inlet,
        "n_h2_inlet_kmol": n_h2_inlet,
        "n_co2_unrxn_kmol": n_co2_unrxn,
        "n_h2_outlet_kmol": n_h2_outlet,
        "n_co2_fresh_kmol": n_co2_fresh,
        "n_h2_fresh_kmol": n_h2_fresh,
        "n_co2_recycle_kmol": n_co2_recycle,
        "n_h2_recycle_kmol": n_h2_recycle,
        "n_co2_purge_kmol": n_co2_purge,
        "n_h2_purge_kmol": n_h2_purge,
        "m_co2_fresh_kg": masses["fresh_co2"],
        "m_h2_fresh_kg": masses["fresh_h2"],
        "m_meoh_out_kg": masses["product"],
        "m_h2o_gen_kg": masses["water"],
        "m_gas_recycle_kg": masses["recycle"],
        "m_gas_purge_kg": masses["purge"],
        "m_gas_offgas_kg": masses["offgas"],
        "m_reactor_inlet_kg": masses["reactor_in"],
        "m_crude_meoh_kg": masses["crude_meoh"],
        "m_o2_kg": masses["oxygen"],
        "eta_carbon": eta_carbon,
        "recycle_ratio_mass": recycle_ratio_mass,
        "recycle_ratio_molar": recycle_ratio_molar,
        "feed_ratio_molar": feed_ratio_molar,
        "e_h2_kwh": e_h2,
        "e_co2_kwh": e_co2,
        "e_recycle_kwh": e_recycle,
        "e_distill_kwh": e_distill,
        "e_total_kwh": e_total,
        "streams": streams,
        "stream_masses": masses,
    }


def _stream_mass(stream):
    """物流质量 (kg)，stream 为 {组分: kmol} 字典"""
    return sum(n * SPECIES[sp]["MW"] for sp, n in stream.items())


def _stream_elements(stream):
    """物流元素质量 (kg)，返回 {'C':…, 'H':…, 'O':…}"""
    out = {el: 0.0 for el in M_ELEM}
    for sp, n in stream.items():
        for el in M_ELEM:
            out[el] += n * SPECIES[sp][el] * M_ELEM[el]
    return out


# ==============================================================================
# 3. 严格元素守恒核查 (C, H, O 质量守恒)
# ==============================================================================
def verify_element_conservation(res):
    """
    独立核验 C、H、O 元素质量守恒。

    尾气元素量由分流器按 r_purge 分流后的物流组成直接给出，不使用
    "输入 - 产品与水" 的差额倒算，故守恒检验具备独立意义。

    检验层级：
      系统边界：新鲜 CO2 + 新鲜 H2  vs  精甲醇 + 生成水 + 驰放气
      单元级  ：混合器、反应器、分离器、分流器
    """
    streams = res["streams"]

    def combine(*names):
        total = {}
        for name in names:
            for sp, n in streams[name].items():
                total[sp] = total.get(sp, 0.0) + n
        return total

    def rel_err(a, b, scale):
        return abs(a - b) / max(scale, 1e-12)

    system_in = _stream_elements(combine("fresh_co2", "fresh_h2"))
    system_out = _stream_elements(combine("product", "water", "purge"))

    system = {}
    for el in M_ELEM:
        system[el] = {
            "in": system_in[el],
            "out": system_out[el],
            "err": rel_err(system_in[el], system_out[el], system_in[el]),
        }

    # 单元级守恒检验（每个单元入口与出口的元素总量）
    units = {
        "混合器 (新鲜气+循环气 vs 反应器入口)":
            (combine("fresh_co2", "fresh_h2", "recycle"), combine("reactor_in")),
        "反应器 (入口 vs 出口)":
            (combine("reactor_in"), combine("reactor_out")),
        "分离器 (出口 vs 气相+粗甲醇)":
            (combine("reactor_out"), combine("offgas", "crude_meoh")),
        "分流器 (分离气相 vs 循环气+驰放气)":
            (combine("offgas"), combine("recycle", "purge")),
    }
    unit_results = {}
    for name, (s_in, s_out) in units.items():
        e_in = _stream_elements(s_in)
        e_out = _stream_elements(s_out)
        unit_results[name] = {
            el: rel_err(e_in[el], e_out[el], e_in[el]) for el in M_ELEM
        }

    return {
        "C_in": system["C"]["in"], "C_out": system["C"]["out"], "C_err": system["C"]["err"],
        "H_in": system["H"]["in"], "H_out": system["H"]["out"], "H_err": system["H"]["err"],
        "O_in": system["O"]["in"], "O_out": system["O"]["out"], "O_err": system["O"]["err"],
        "units": unit_results,
        "mass_in": _stream_mass(combine("fresh_co2", "fresh_h2")),
        "mass_out": _stream_mass(combine("product", "water", "purge")),
    }


# ==============================================================================
# 4. 园区级工程规模放大核算 (10 万吨/年)
# ==============================================================================
def scale_up_park_level(res, annual_meoh_ton=100000.0, plant_water_tpt=None):
    """
    据单吨定额放大至 10 万吨/年工业园区级工程通量。
    用水（四类分项，不把全厂模型取水全部计入电解槽）：
      ① 全厂模型取水：默认取课程基础参数 1.385 t/t（政策取水函数 W = 1.385 + 0.008×(0.010/r)
         的基准项；政策卡片同时给出园区定额 1.400 t/t 与刚性红线 1.425 t/t，三者不可混称）。
         锚点 B 的全厂模型取水量为 1.40154 t/t，由政策取水函数在 r_purge = 0.4837% 处计算，
         调用时通过 plant_water_tpt 显式传入，避免与基准工况混用。
      ② 电解化学计量需水 = 8.94 kg H2O / kg H2（按新鲜氢量计），即电解槽总进水；
      ③ 精馏副产回用水取模型计算值，回用于电解槽；
      ④ 电解净补水 = 电解化学计量需水 − 回用水；未分配差额 = 全厂模型取水 − 电解净补水。
    说明：数据底座与政策卡片均未单列冷却补水、工艺损耗与产品带水的实测分项，故"未分配差额"
          仅为代数差额（历史字段名 cooling_water / cooling_water_tpt 保留以兼容调用），
          其物理去向待实测，不构成全厂水平衡已闭合的证据，也不倒算配平。
    """
    k = annual_meoh_ton

    recycled_water_tpt = res["m_h2o_gen_kg"] / 1000.0
    plant_water_tpt = COURSE_MAKEUP_WATER_TPT if plant_water_tpt is None else float(plant_water_tpt)
    # 电解化学计量耗水 = 8.94 kg H2O / kg H2（按新鲜氢量计）
    stoich_water_tpt = (MW_H2O / MW_H2) * res["m_h2_fresh_kg"] / 1000.0
    electrolyzer_makeup_tpt = stoich_water_tpt - recycled_water_tpt
    # 历史字段名 cooling_water_tpt 保留以兼容调用；其真实含义为"未分配差额"
    # （全厂模型取水 − 电解净补水），不认定为冷却补水或工艺损耗，物理去向待实测。
    cooling_water_tpt = plant_water_tpt - electrolyzer_makeup_tpt

    return {
        "annual_meoh_capacity_ton": k,
        "annual_co2_ton": res["m_co2_fresh_kg"] * k / 1000.0,
        "annual_green_h2_ton": res["m_h2_fresh_kg"] * k / 1000.0,
        "annual_crude_water_ton": res["m_h2o_gen_kg"] * k / 1000.0,
        "annual_plant_water_ton": plant_water_tpt * k,
        "annual_makeup_water_ton": electrolyzer_makeup_tpt * k,
        "annual_cooling_water_ton": cooling_water_tpt * k,   # 历史字段名：实为未分配差额年通量
        "annual_recycled_water_ton": recycled_water_tpt * k,
        "annual_electrolyzer_feed_ton": stoich_water_tpt * k,
        "annual_stoich_water_ton": stoich_water_tpt * k,
        "annual_oxygen_ton": res["m_o2_kg"] * k / 1000.0,
        "annual_purge_gas_ton": res["m_gas_purge_kg"] * k / 1000.0,
        "annual_recycle_gas_ton": res["m_gas_recycle_kg"] * k / 1000.0,
        "annual_crude_meoh_ton": res["m_crude_meoh_kg"] * k / 1000.0,
        "annual_power_b_kwh": res["e_total_kwh"] * k / 1e8,   # 亿 kWh/年
        "tpt": {
            "co2": res["m_co2_fresh_kg"],
            "h2": res["m_h2_fresh_kg"],
            "plant_water": plant_water_tpt,
            "recycled_water": recycled_water_tpt,
            "makeup_water": electrolyzer_makeup_tpt,
            "cooling_water": cooling_water_tpt,   # 历史字段名：实为未分配差额（物理去向待实测）
            "electrolyzer_feed": stoich_water_tpt,
            "stoich_water": stoich_water_tpt,
            "water_reuse_pct": recycled_water_tpt / stoich_water_tpt * 100.0,
            "oxygen": res["m_o2_kg"],
            "purge": res["m_gas_purge_kg"],
            "recycle": res["m_gas_recycle_kg"],
            "power": res["e_total_kwh"],
        },
    }


# ==============================================================================
# 5. 与工程数据集逐流股比对
# ==============================================================================
def compare_with_dataset(res, csv_file):
    """将模型结果与数据集实测流股质量流量比对，返回偏差表"""
    df = pd.read_csv(csv_file)
    ref = dict(zip(df["stream_id"], df["mass_flow_per_ton_product_kg"]))

    mapping = [
        ("S01", "新鲜 CO2 进料", res["m_co2_fresh_kg"]),
        ("S02", "新鲜 H2 进料", res["m_h2_fresh_kg"]),
        ("S06", "未反应气循环流", res["m_gas_recycle_kg"]),
        ("S07", "反应器入口混合气", res["m_reactor_inlet_kg"]),
        ("S09", "粗甲醇液相", res["m_crude_meoh_kg"]),
        ("S10", "分离器气相总流", res["m_gas_offgas_kg"]),
        ("S11", "驰放废气", res["m_gas_purge_kg"]),
        ("S13", "精馏生成水", res["m_h2o_gen_kg"]),
    ]
    rows = []
    for sid, name, model_val in mapping:
        ref_val = float(ref[sid])
        dev = (model_val - ref_val) / ref_val * 100.0
        rows.append((sid, name, ref_val, model_val, dev))
    return rows


# ==============================================================================
# 6. 主程序与自检核验
# ==============================================================================
if __name__ == "__main__":
    print("=" * 88)
    print("《环境规划与管理》任务 1：MFA 循环流求解与元素质量守恒验证")
    print("=" * 88)

    csv_file = find_data_file()
    if csv_file:
        df = pd.read_csv(csv_file)
        print(f"[数据源] 成功加载实操工程数据集: {csv_file} (共 {len(df)} 个节点)")
    else:
        print("[提示] 未找到数据集，使用内建化学计量参数。")

    X_SP = 0.250
    R_PURGE = 0.010
    res = solve_mfa_balance(single_pass_conv=X_SP, purge_ratio=R_PURGE)

    print(f"\n【输入参数】单程 CO2 转化率 X_sp = {X_SP:.1%} ｜ 驰放分流比 r_purge = {R_PURGE:.1%}")

    print("\n【单吨产品 (1,000 kg 精甲醇) 物流清单（单位：kg/t）】")
    flow_rows = [
        ("S01 新鲜 CO2 进料", res["m_co2_fresh_kg"]),
        ("S02 新鲜 H2 进料", res["m_h2_fresh_kg"]),
        ("S06 未反应气循环流", res["m_gas_recycle_kg"]),
        ("S07 反应器入口混合气", res["m_reactor_inlet_kg"]),
        ("S08 反应器出口物料", res["m_reactor_inlet_kg"]),
        ("S09 粗甲醇液相 (甲醇+水)", res["m_crude_meoh_kg"]),
        ("S10 分离器气相总流", res["m_gas_offgas_kg"]),
        ("S11 驰放废气", res["m_gas_purge_kg"]),
        ("S12 聚合级精甲醇产品", res["m_meoh_out_kg"]),
        ("S13 精馏生成水", res["m_h2o_gen_kg"]),
        ("副产高纯氧气", res["m_o2_kg"]),
    ]
    for name, val in flow_rows:
        print(f"  {name:<26s} : {val:10.2f} kg/t")

    print("\n【回路与转化指标（由 X_sp 与 r_purge 推导）】")
    print(f"  反应器入口 CO2 / H2   : {res['n_co2_inlet_kmol']:.2f} / "
          f"{res['n_h2_inlet_kmol']:.2f} kmol/t  (H2/CO2 = {res['h2_co2_inlet_ratio']:.2f})")
    print(f"  反应器出口未反应 CO2  : {res['n_co2_unrxn_kmol']:.2f} kmol/t "
          f"（单程转化率校验 {res['n_co2_rxn_kmol'] / res['n_co2_inlet_kmol']:.2%}）")
    print(f"  循环比（质量，循环气/新鲜气）  : {res['recycle_ratio_mass']:.2f} : 1")
    print(f"  循环比（摩尔，循环气/新鲜气）  : {res['recycle_ratio_molar']:.2f} : 1"
          f"（与质量比同值：循环气与新鲜气同为 H2/CO2 = 3 配比）")
    print(f"  反应器总进料/新鲜进料（摩尔）   : {res['feed_ratio_molar']:.2f} : 1"
          f"（含循环气，属总进料放大倍数，非循环比）")
    print(f"  总碳转化利用率 η_carbon         : {res['eta_carbon']:.2%}")

    # ---------- 元素守恒 ----------
    cons = verify_element_conservation(res)
    print("\n【C, H, O 三元素质量守恒（系统边界）】")
    print(f"  碳 C: 输入 {cons['C_in']:9.4f} kg | 输出 {cons['C_out']:9.4f} kg | "
          f"相对误差 {cons['C_err']:.3e}")
    print(f"  氢 H: 输入 {cons['H_in']:9.4f} kg | 输出 {cons['H_out']:9.4f} kg | "
          f"相对误差 {cons['H_err']:.3e}")
    print(f"  氧 O: 输入 {cons['O_in']:9.4f} kg | 输出 {cons['O_out']:9.4f} kg | "
          f"相对误差 {cons['O_err']:.3e}")
    print(f"  总质量: 输入 {cons['mass_in']:.4f} kg | 输出 {cons['mass_out']:.4f} kg")

    print("\n【单元级元素守恒（相对误差）】")
    for name, errs in cons["units"].items():
        print(f"  {name:<34s} C {errs['C']:.2e}  H {errs['H']:.2e}  O {errs['O']:.2e}")

    assert cons["C_err"] < 1e-4, "碳守恒误差超出阈值"
    assert cons["H_err"] < 1e-4, "氢守恒误差超出阈值"
    assert cons["O_err"] < 1e-4, "氧守恒误差超出阈值"
    assert abs(cons["mass_in"] - cons["mass_out"]) < 1e-6, "系统总质量不闭合"
    for name, errs in cons["units"].items():
        assert max(errs.values()) < 1e-9, f"{name} 元素不闭合"
    print("  -> 结论：三元素与总质量在所有单元和系统边界均闭合，误差 < 0.01%。")

    # ---------- 工程放大 ----------
    park = scale_up_park_level(res, annual_meoh_ton=100000.0)
    print("\n【工业园区 10 万吨/年工程通量清单（报告第 2 章）】")
    print(f"  绿色精甲醇设计产能       : {park['annual_meoh_capacity_ton']:>13,.0f} t/a")
    print(f"  工业点源 CO2 年需捕集量   : {park['annual_co2_ton']:>13,.0f} t/a "
          f"({park['annual_co2_ton']/1e4:.2f} 万 t/a)")
    print(f"  电解水绿氢年需求总量     : {park['annual_green_h2_ton']:>13,.0f} t/a "
          f"({park['annual_green_h2_ton']/1e4:.2f} 万 t/a)")
    print(f"  精馏副产生成水回用量     : {park['annual_recycled_water_ton']:>13,.0f} t/a "
          f"({park['annual_recycled_water_ton']/1e4:.2f} 万 t/a)")
    print(f"  全厂新鲜除盐取水量       : {park['annual_plant_water_ton']:>13,.0f} t/a "
          f"({park['annual_plant_water_ton']/1e4:.2f} 万 t/a)")
    print(f"  其中 电解净补水量       : {park['annual_makeup_water_ton']:>13,.0f} t/a "
          f"({park['annual_makeup_water_ton']/1e4:.2f} 万 t/a, "
          f"{park['tpt']['makeup_water']:.3f} t/t)")
    print(f"  其中 未分配差额          : {park['annual_cooling_water_ton']:>13,.0f} t/a "
          f"({park['annual_cooling_water_ton']/1e4:.2f} 万 t/a, "
          f"{park['tpt']['cooling_water']*1000:.2f} kg/t；历史字段名 cooling_water，"
          f"物理去向待实测，非冷却水或工艺损耗)")
    print(f"  电解槽总进水量(=化学计量): {park['annual_electrolyzer_feed_ton']:>13,.0f} t/a "
          f"({park['annual_electrolyzer_feed_ton']/1e4:.2f} 万 t/a, "
          f"= 净补水 + 回水 {park['tpt']['recycled_water']:.3f} t/t，"
          f"回用占 {park['tpt']['water_reuse_pct']:.2f}%)")
    print(f"  副产高纯工业纯氧总量     : {park['annual_oxygen_ton']:>13,.0f} t/a "
          f"({park['annual_oxygen_ton']/1e4:.2f} 万 t/a)")
    print(f"  未反应气循环气总量       : {park['annual_recycle_gas_ton']:>13,.0f} t/a "
          f"({park['annual_recycle_gas_ton']/1e4:.2f} 万 t/a)")
    print(f"  系统驰放废气总量         : {park['annual_purge_gas_ton']:>13,.0f} t/a")
    print(f"  全厂年综合用电负荷       : {park['annual_power_b_kwh']:>13.3f} 亿 kWh/a")

    # ---------- 报告表 2-2 设计基准（锚点 B）通量核对 ----------
    print("\n【报告表 2-2 设计基准（锚点 B）10 万吨/年通量核对】")
    r_b = load_anchor_b_purge_ratio()
    if r_b is None:
        print("  未找到 results_output/task3_anchor_metrics.csv，跳过锚点 B 核对（请先运行 task3）。")
    else:
        w_b = COURSE_MAKEUP_WATER_TPT + 0.008 * 0.010 / r_b   # 卡片3 取水函数
        res_b = solve_mfa_balance(single_pass_conv=X_SP, purge_ratio=r_b)
        park_b = scale_up_park_level(res_b, annual_meoh_ton=100000.0, plant_water_tpt=w_b)
        t = park_b["tpt"]
        print(f"  设计工况：r_purge = {r_b*100:.4f}%，全厂模型取水 = {w_b:.5f} t/t"
              f"（政策函数值，非 1.385 基准参数、非 1.400 定额）")
        print(f"  新鲜 CO2               : {park_b['annual_co2_ton']/1e4:>8.2f} 万 t/a ({t['co2']:.2f} kg/t)")
        print(f"  电解绿氢               : {park_b['annual_green_h2_ton']/1e4:>8.2f} 万 t/a ({t['h2']:.2f} kg/t)")
        print(f"  副产纯氧               : {park_b['annual_oxygen_ton']/1e4:>8.2f} 万 t/a ({t['oxygen']:.2f} kg/t)")
        print(f"  循环气                 : {park_b['annual_recycle_gas_ton']/1e4:>8.2f} 万 t/a ({t['recycle']:.2f} kg/t)")
        print(f"  驰放气                 : {park_b['annual_purge_gas_ton']:>11,.0f} t/a ({t['purge']:.2f} kg/t)")
        print(f"  全厂模型取水           : {park_b['annual_plant_water_ton']/1e4:>8.2f} 万 t/a ({t['plant_water']:.5f} t/t)")
        print(f"  其中 电解净补水        : {park_b['annual_makeup_water_ton']/1e4:>8.2f} 万 t/a ({t['makeup_water']*1000:.2f} kg/t)")
        print(f"  其中 未分配差额        : {park_b['annual_cooling_water_ton']/1e4:>8.2f} 万 t/a ({t['cooling_water']*1000:.2f} kg/t；物理去向待实测)")
        print(f"  电解槽总进水           : {park_b['annual_electrolyzer_feed_ton']/1e4:>8.2f} 万 t/a ({t['stoich_water']*1000:.2f} kg/t)")
        print(f"  其中 精馏回用水        : {park_b['annual_recycled_water_ton']/1e4:>8.2f} 万 t/a ({t['recycled_water']*1000:.2f} kg/t)")
        print(f"  综合电耗               : {park_b['annual_power_b_kwh']:>8.3f} 亿 kWh/a ({t['power']:.2f} kWh/t)")
        print("  -> 以上数值即报告表 2-2 的锚点 B 数据来源（同一模型、同一设计工况）。")

    print("\n【单吨电耗分解 (kWh/t 甲醇)】")
    print(f"  PEM 电解制氢 (52 kWh/kg)  : {res['e_h2_kwh']:>9.1f}  ({res['e_h2_kwh']/res['e_total_kwh']:.1%})")
    print(f"  CO2 捕集与三级压缩        : {res['e_co2_kwh']:>9.1f}  ({res['e_co2_kwh']/res['e_total_kwh']:.1%})")
    print(f"  循环气增压与循环水泵      : {res['e_recycle_kwh']:>9.1f}  ({res['e_recycle_kwh']/res['e_total_kwh']:.1%})")
    print(f"  双塔精馏与冷冻脱轻        : {res['e_distill_kwh']:>9.1f}  ({res['e_distill_kwh']/res['e_total_kwh']:.1%})")
    print(f"  合计                      : {res['e_total_kwh']:>9.1f} kWh/t")

    # ---------- 数据集比对 ----------
    if csv_file:
        print("\n【与工程数据集逐流股比对（kg/t）】")
        print(f"  {'流股':<6s}{'名称':<22s}{'数据集':>10s}{'模型':>10s}{'偏差':>9s}")
        for sid, name, ref_val, model_val, dev in compare_with_dataset(res, csv_file):
            print(f"  {sid:<6s}{name:<22s}{ref_val:>10.1f}{model_val:>10.2f}{dev:>8.2f}%")

    # ---------- 口径差异记录 ----------
    r_for_96 = X_SP * (1.0 - 0.96) / (0.96 * (1.0 - X_SP))
    x_for_96 = None
    for x in np.linspace(0.05, 0.95, 9001):
        if x / (x + R_PURGE * (1.0 - x)) >= 0.96:
            x_for_96 = x
            break
    print("\n【口径差异记录（不强行配平，供报告说明）】")
    print(f"  1) 总碳利用率：模型 {res['eta_carbon']:.2%}（X_sp={X_SP:.0%}、r_purge={R_PURGE:.1%}）")
    print(f"     讲义标称 96.0% 需 r_purge ≈ {r_for_96:.2%} 或 X_sp ≈ {x_for_96:.2%}；"
          f"数据集 96.5% 对应 r_purge ≈ 1.21%")
    print(f"  2) 生成水：模型 {res['m_h2o_gen_kg']:.1f} kg/t vs 数据集 575.0 kg/t "
          f"（{(res['m_h2o_gen_kg'] - 575.0) / 575.0 * 100:+.2f}%），"
          f"差异源于净 CO 口径与取整")
    print(f"  3) 新鲜 CO2 / H2：模型 {res['m_co2_fresh_kg']:.1f} / {res['m_h2_fresh_kg']:.1f} kg/t "
          f"vs 数据集 1423.0 / 198.0 kg/t")
    print(f"  4) 综合电耗：模型 {res['e_total_kwh']:.0f} kWh/t vs 讲义 10826 kWh/t "
          f"（{(res['e_total_kwh'] - 10826.0) / 10826.0 * 100:+.2f}%），"
          f"差异主要来自新鲜氢量与电耗强度取整")
    print(f"  5) 取水口径：本脚本基准工况的全厂模型取水取课程基础参数 {park['tpt']['plant_water']:.3f} t/t"
          f"（政策取水函数的基准项，非园区定额 1.400 t/t、亦非实测取水）；"
          f"电解化学计量需水 {park['tpt']['stoich_water']:.3f} t/t，扣除回用 "
          f"{park['tpt']['recycled_water']:.3f} t/t 后电解净补水 {park['tpt']['makeup_water']:.3f} t/t；"
          f"两者之差 {park['tpt']['cooling_water']*1000:.2f} kg/t 为未分配差额"
          f"（历史字段名 cooling_water；物理去向待实测，属代数差额，不构成水平衡闭合）")
    print(f"     锚点 B 的全厂模型取水量由政策函数得 1.40154 t/t（非 1.385），"
          f"同口径未分配差额为 252.60 kg/t；两工况不可混用'定额''实际取水''模型估算值'")
    print(f"  6) RWGS 副产 CO：讲义约 1.124 kmol/t 与数据集 offgas 4686 kg/t 不自洽，"
          f"本模型取净 CO = 0")
    print("=" * 88)
