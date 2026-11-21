# -*- coding: utf-8 -*-
"""
课程名称：《环境规划与管理》
案例主题：工业园区二氧化碳捕集耦合绿氢合成绿色甲醇系统
任务编号：任务 4（学生随堂实训版）
脚本名称：task4_process_sankey_flow.py
功能描述：
  直接读取任务 3 结果文件 results_output/task3_pareto_frontier.csv 中标记为锚点 B 的
  帕累托拐点行，按 10 万吨/年产能线性放大，绘制工业园区绿色甲醇系统物质流（MFA）与
  能量流（EFA）全流程拓扑图（figures_output/fig1_mfa_process_flow.png，300 DPI）。

  图中全部通量、电耗、循环比、驰放比、碳利用率均由锚点 B 行计算得出，脚本内不保留
  任何写死的物料/能耗基准值（仅保留年运行小时数 8,000 h 与 10 万吨/年产能这两项课程
  给定的规模参数）。

  图中包含：
    1. 碳捕集、绿电制氢、催化合成、循环分流、双塔精馏各工段物料通量（万 t/a）；
    2. 未反应气闭环内循环流与精馏釜水回用流（含循环比与驰放比）；
    3. 各工段综合电耗分布（亿 kWh/a 及占比）；
    4. 取水四类分项与箭头口径：进入电解槽的新鲜水箭头为"电解净补水"，
       精馏回水箭头为回用水，二者合计为电解槽总进水；全厂模型取水与未分配差额
       只用说明框列示，不画成进入电解槽的物流，也不画成已确认的冷却水或损耗；
    5. 输出前的自校验：电耗分项闭合、碳元素闭合、反应器进出质量闭合、循环比质量=摩尔、
       水量分项代数核验（不作全厂水平衡闭合结论），并与结果文件中的锚点 B 指标逐项核对（GWP、LCOM）。
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

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# 分子量口径与任务 1 完全一致（唯一来源）
try:
    from task1_mfa_recycle_solver import M_C, MW_CO2, MW_CH3OH, MW_H2O, MW_H2
except ImportError:                                            # 兼容包内导入方式
    from code_implementation.task1_mfa_recycle_solver import M_C, MW_CO2, MW_CH3OH, MW_H2O, MW_H2

# 统一中文字体
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'PingFang SC', 'DejaVu Sans', 'Arial']
plt.rcParams['axes.unicode_minus'] = False

# ==============================================================================
# 规模换算基准（课程给定，非物料基准值）
# ==============================================================================
ANNUAL_HOURS = 8000.0          # 固定床反应器年设计满负荷运行小时数（课程给定）
PLANT_CAPACITY_T_A = 100000.0  # 示范线精甲醇设计产能 10 万吨/年
KG_PER_WAN_T = 1.0e7           # 1 万吨 = 1e7 kg
KWH_PER_YI_KWH = 1.0e8         # 1 亿 kWh = 1e8 kWh
OUTPUT_DPI = 300               # 输出分辨率下限（不低于 300 DPI）


def get_figures_output_dir():
    """跨层级定位 figures_output 目录，确保脚本从任意工作路径均能正确定位"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(current_dir, "..", "figures_output"),
        os.path.join("figures_output"),
        os.path.join("..", "figures_output")
    ]
    for d in candidates:
        try:
            os.makedirs(d, exist_ok=True)
            return d
        except Exception:
            continue
    return "."


def get_results_output_dir():
    """跨层级定位 results_output 目录（任务 3 结果落盘处）"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(current_dir, "..", "results_output"),
        os.path.join("results_output"),
        os.path.join("..", "results_output")
    ]
    for d in candidates:
        try:
            os.makedirs(d, exist_ok=True)
            return d
        except Exception:
            continue
    return "."


# ==============================================================================
# 模块一：读取任务 3 锚点 B 结果（唯一数据来源，无写死基准）
# ==============================================================================
def load_anchor_b_row():
    """
    读取 results_output/task3_pareto_frontier.csv，返回 anchor_tag == 'B' 的帕累托拐点行。

    兼容说明：
      * 若结果文件缺失，提示先运行 task3_pareto_frontier_decision.py，不自行造数；
      * 若锚点指标表 task3_anchor_metrics.csv 存在，则顺带取出该表中的 B 行用于交叉核对。
    返回：
      (row_dict, pareto_path, metrics_row_or_None, metrics_path_or_None)
    """
    res_dir = get_results_output_dir()
    pareto_path = os.path.join(res_dir, "task3_pareto_frontier.csv")
    if not os.path.isfile(pareto_path):
        raise FileNotFoundError(
            f"未找到任务 3 结果文件：{pareto_path}\n"
            f"请先在 code_implementation 目录运行 task3_pareto_frontier_decision.py 生成帕累托前沿。")

    front = pd.read_csv(pareto_path)
    tag = front["anchor_tag"].astype(str).str.strip().str.upper()
    sel = front[tag == "B"]
    if sel.empty:
        raise ValueError(f"结果文件 {pareto_path} 中未找到 anchor_tag == 'B' 的帕累托拐点行")
    row = sel.iloc[0].to_dict()

    metrics_path = os.path.join(res_dir, "task3_anchor_metrics.csv")
    metrics_row = None
    if os.path.isfile(metrics_path):
        metrics = pd.read_csv(metrics_path)
        hit = metrics[metrics["锚点"].astype(str).str.strip().str.upper() == "B"]
        metrics_row = hit.iloc[0].to_dict() if not hit.empty else None
    return row, pareto_path, metrics_row, (metrics_path if metrics_row is not None else None)


def build_flow_set(row):
    """
    由锚点 B 单吨指标换算 10 万吨/年工程通量（万 t/a）与分项电耗（亿 kWh/a）。

    单位换算：
      万 t/a = kg/t × 设计产能 / 1e7 ；亿 kWh/a = kWh/t × 设计产能 / 1e8
    """
    def to_wan_t(v_kg_per_t):
        return v_kg_per_t * PLANT_CAPACITY_T_A / KG_PER_WAN_T

    def to_yi_kwh(v_kwh_per_t):
        return v_kwh_per_t * PLANT_CAPACITY_T_A / KWH_PER_YI_KWH

    def to_mw(v_kwh_per_t):
        return v_kwh_per_t * PLANT_CAPACITY_T_A / ANNUAL_HOURS / 1000.0

    r_purge = float(row["r_purge"])
    fresh_co2 = float(row["fresh_co2_kg_t"])
    fresh_h2 = float(row["fresh_h2_kg_t"])
    recycle = float(row["recycle_gas_kg_t"])
    purge = float(row["purge_gas_kg_t"])

    # 循环气/新鲜气摩尔数与质量数（循环气与新鲜气同为 H2/CO2 = 3 的化学计量配比）
    recycle_kmol = recycle / ((MW_CO2 + 3.0 * 2.016) / 4.0)
    fresh_kmol = fresh_co2 / MW_CO2 + fresh_h2 / 2.016

    # ---------- 水量四类分项（不把政策取水函数的全部水量送入电解槽） ----------
    # ① 全厂模型取水：政策取水函数值；
    # ② 精馏回水：精馏副产生成水，模型按全部回用于电解槽计；
    # ③ 电解化学计量需水 = 8.94 kg H2O/kg H2 × 新鲜氢量，即电解槽总进水；
    # ④ 电解净补水 = 电解化学计量需水 − 精馏回水；未分配差额 = 全厂模型取水 − 电解净补水
    #    （仅为模型取水量与电解净补水之差，不认定为冷却水或工艺损耗，物理去向待实测）。
    plant_water = float(row["water_total_tpt"]) * 1000.0
    gen_water = float(row["gen_water_kg_t"])
    stoich_water = (MW_H2O / MW_H2) * fresh_h2
    el_makeup = stoich_water - gen_water
    cool_makeup = plant_water - el_makeup

    flows = {
        "f_co2": to_wan_t(fresh_co2),
        "f_h2": to_wan_t(fresh_h2),
        "f_o2": to_wan_t(float(row["o2_byproduct_kg_t"])),
        "f_recycle": to_wan_t(recycle),
        "f_purge": to_wan_t(purge),
        "f_water_gen": to_wan_t(gen_water),
        "f_water_plant": to_wan_t(plant_water),
        "f_water_el_makeup": to_wan_t(el_makeup),
        "f_water_cool": to_wan_t(cool_makeup),
        "f_water_el_feed": to_wan_t(stoich_water),
        "tt_water_plant": plant_water / 1000.0,
        "tt_water_el_makeup": el_makeup / 1000.0,
        "tt_water_cool": cool_makeup / 1000.0,
        "tt_water_el_feed": stoich_water / 1000.0,
        "tt_water_gen": gen_water / 1000.0,
        "f_product": PLANT_CAPACITY_T_A * 1000.0 / KG_PER_WAN_T,               # 10.00 万 t/a
        # 循环比统一定义为“循环气/新鲜气”；总进料/新鲜进料另记为 f_feed_ratio_molar
        "f_recycle_ratio_mass": recycle / (fresh_co2 + fresh_h2),
        "f_recycle_ratio_molar": recycle_kmol / fresh_kmol,
        "f_feed_ratio_molar": (recycle_kmol + fresh_kmol) / fresh_kmol,
        "e_h2": to_yi_kwh(float(row["e_h2_kwh"])),
        "e_co2": to_yi_kwh(float(row["e_co2_kwh"])),
        "e_recycle": to_yi_kwh(float(row["e_recycle_kwh"])),
        "e_distill": to_yi_kwh(float(row["e_distill_kwh"])),
        "e_total": to_yi_kwh(float(row["e_total_kwh"])),
        "mw_h2": to_mw(float(row["e_h2_kwh"])),
        "mw_total": to_mw(float(row["e_total_kwh"])),
        "r_purge_pct": r_purge * 100.0,
        "f_green_pct": float(row["f_green"]) * 100.0,
        "eta_carbon_pct": float(row["eta_carbon_pct"]),
        "gwp_net": float(row["gwp_net"]),
        "lcom": float(row["lcom_policy_adjusted"]),
        "mac": float(row["mac_policy_adjusted"]),
        "status": str(row["compliance_status"]),
    }
    flows["tt_co2"] = flows["f_co2"] / flows["f_product"]
    flows["tt_h2"] = flows["f_h2"] / flows["f_product"]
    flows["tt_o2"] = flows["f_o2"] / flows["f_product"]
    flows["f_reactor_in"] = flows["f_co2"] + flows["f_h2"] + flows["f_recycle"]
    flows["f_offgas"] = flows["f_recycle"] / (1.0 - r_purge)
    flows["f_crude"] = flows["f_product"] + flows["f_water_gen"]
    flows["share_h2"] = flows["e_h2"] / flows["e_total"] * 100.0
    flows["share_co2"] = flows["e_co2"] / flows["e_total"] * 100.0
    flows["share_recycle"] = flows["e_recycle"] / flows["e_total"] * 100.0
    flows["share_distill"] = flows["e_distill"] / flows["e_total"] * 100.0
    # 回用量分别相对电解槽总进水与全厂模型取水，两种口径分别列示
    flows["water_reuse_pct"] = gen_water / stoich_water * 100.0
    flows["water_reuse_of_plant_pct"] = gen_water / plant_water * 100.0
    flows["water_cool_pct"] = cool_makeup / plant_water * 100.0
    flows["carbon_loss_pct"] = float(row["purge_co2_kg_t"]) / fresh_co2 * 100.0
    return flows


def verify_against_anchor_b(row, flows, metrics_row=None):
    """
    输出前的数据一致性自校验：
      1. 电耗分项合计 vs 综合电耗；
      2. 碳元素闭合：新鲜 CO2 碳 = 产品固碳 + 驰放 CO2 碳；
      3. 分离器分流闭合：循环气 + 驰放气 = 分离器气相（= 循环气 / (1 − r_purge)）；
      4. 驰放气占比 = 驰放分流比 r_purge（按质量口径独立校核）；
      5. 反应器质量闭合：新鲜进料 + 循环气 = 产品 + 生成水 + 分离器气相；
      6. 循环比口径：质量循环比 = 摩尔循环比（循环气/新鲜气，两股气配比相同）；
      7. 水量四类分项代数核验：全厂模型取水 = 电解净补水 + 未分配差额（不作水平衡闭合认定），电解槽总进水 = 电解净补水 + 精馏回水；
      8. 与 task3_anchor_metrics.csv 的 B 行 GWP / LCOM 复核。
    返回：
      (校验项列表, 是否全部通过)
    """
    checks = []

    e_sum = float(row["e_h2_kwh"]) + float(row["e_co2_kwh"]) + float(row["e_recycle_kwh"]) + float(row["e_distill_kwh"])
    checks.append(("电耗分项合计", e_sum, float(row["e_total_kwh"]), "kWh/t"))

    c_fresh = float(row["fresh_co2_kg_t"]) * M_C / MW_CO2
    c_prod = 1000.0 * M_C / MW_CH3OH
    c_purge = float(row["purge_co2_kg_t"]) * M_C / MW_CO2
    checks.append(("碳元素闭合(新鲜)", c_fresh, c_prod + c_purge, "kg C/t"))

    # 分离器气液分流：分离器气相按 r_purge 分成驰放气与循环气，二者之和须回到气相总量
    offgas = float(row["recycle_gas_kg_t"]) / (1.0 - float(row["r_purge"]))
    checks.append(("循环气+驰放气=气相",
                   float(row["recycle_gas_kg_t"]) + float(row["purge_gas_kg_t"]), offgas, "kg/t"))
    checks.append(("驰放气占比=分流比(%)",
                   float(row["purge_gas_kg_t"]) / offgas * 100.0,
                   float(row["r_purge"]) * 100.0, "%"))

    m_in = float(row["fresh_co2_kg_t"]) + float(row["fresh_h2_kg_t"]) + float(row["recycle_gas_kg_t"])
    m_out = 1000.0 + float(row["gen_water_kg_t"]) + offgas
    checks.append(("反应器质量闭合", m_in, m_out, "kg/t"))

    # 循环比定义统一为“循环气/新鲜气”：质量比与摩尔比须同值（两股气 H2/CO2 均为 3）
    checks.append(("循环比 质量=摩尔",
                   flows["f_recycle_ratio_mass"], flows["f_recycle_ratio_molar"], ":1"))

    # 水量四类分项（全厂模型取水 / 电解净补水 / 未分配差额 / 精馏回水）
    plant_w = flows["tt_water_plant"] * 1000.0
    el_makeup_w = flows["tt_water_el_makeup"] * 1000.0
    cool_w = flows["tt_water_cool"] * 1000.0
    gen_w = flows["tt_water_gen"] * 1000.0
    el_feed_w = flows["tt_water_el_feed"] * 1000.0
    checks.append(("全厂模型取水=电解净补水+未分配差额", plant_w, el_makeup_w + cool_w, "kg/t"))
    checks.append(("电解槽总进水=电解净补水+回水", el_feed_w, el_makeup_w + gen_w, "kg/t"))

    ok = True
    print("\n" + "=" * 92)
    print("【数据一致性自校验（图内全部数值均取自锚点 B 行）】")
    print("=" * 92)
    for name, lhs, rhs, unit in checks:
        rel = (lhs - rhs) / rhs * 100.0 if rhs else 0.0
        passed = abs(rel) < 0.05
        ok = ok and passed
        print(f"  {name:<20}: {lhs:>12.4f} vs {rhs:>12.4f} {unit:<8}  相对偏差 {rel:+.5f}%  "
              f"{'PASS' if passed else 'CHECK'}")
    print(f"  {'水量分配明细':<20}: 全厂模型取水 {plant_w:.2f} = 电解净补水 {el_makeup_w:.2f} + 未分配差额 {cool_w:.2f}；"
          f"电解槽总进水 {el_feed_w:.2f} = 电解净补水 {el_makeup_w:.2f} + 精馏回水 {gen_w:.2f} kg/t")
    print(f"  {'未分配差额':<20}: {cool_w:.2f} kg/t 为全厂模型取水量减电解净补水后的未分配差额，"
          f"不认定为冷却水或损耗，物理去向待实测；"
          f"回用占电解槽总进水 {flows['water_reuse_pct']:.2f}%、占全厂模型取水 {flows['water_reuse_of_plant_pct']:.2f}%")

    if metrics_row is not None:
        gwp_ref = float(metrics_row["GWP_net (kg CO2e/t)"])
        lcom_ref = float(metrics_row["调整后 LCOM (元/t)"])
        d_gwp = abs(flows["gwp_net"] - gwp_ref)
        d_lcom = abs(flows["lcom"] - lcom_ref)
        passed = (d_gwp <= 0.01) and (d_lcom <= 0.01)
        ok = ok and passed
        print(f"  {'锚点指标复核':<16}: GWP {flows['gwp_net']:.2f} vs 指标表 {gwp_ref:.2f} kg CO2e/t；"
              f"LCOM {flows['lcom']:.2f} vs {lcom_ref:.2f} 元/t  {'PASS' if passed else 'CHECK'}")
    return checks, ok


# ==============================================================================
# 模块二：拓扑图绘制（全部数值来自锚点 B，无写死基准）
# ==============================================================================
def draw_mfa_process_flow(output_filename="fig1_mfa_process_flow.png"):
    """
    绘制园区级 10 万吨/年绿色甲醇工程物质与能量流动拓扑图。

    参数：
        output_filename (str): 图表输出文件名
    """
    row, pareto_path, metrics_row, metrics_path = load_anchor_b_row()
    flows = build_flow_set(row)
    verify_against_anchor_b(row, flows, metrics_row)

    print(f"\n[数据来源] {pareto_path}（锚点 B 行）" + (f"；交叉核对表 {metrics_path}" if metrics_path else ""))
    print(f"[锚点 B ] f_green = {flows['f_green_pct']:.2f}%，r_purge = {flows['r_purge_pct']:.4f}%，"
          f"总碳利用率 = {flows['eta_carbon_pct']:.2f}%，合规状态 = {flows['status']}")
    print(f"[工程通量] 新鲜 CO2 {flows['f_co2']:.2f} 万 t/a；绿氢 {flows['f_h2']:.2f} 万 t/a；"
          f"副产 O2 {flows['f_o2']:.2f} 万 t/a；循环气 {flows['f_recycle']:.2f} 万 t/a；"
          f"驰放气 {flows['f_purge']:.3f} 万 t/a")
    print(f"[循环比  ] {flows['f_recycle_ratio_mass']:.2f}:1（循环气/新鲜气，质量口径）；"
          f"{flows['f_recycle_ratio_molar']:.2f}:1（循环气/新鲜气，摩尔口径，与质量同值）；"
          f"反应器总进料/新鲜进料 {flows['f_feed_ratio_molar']:.2f}:1（非循环比）")
    print(f"[水系统  ] 全厂模型取水 {flows['f_water_plant']:.2f} 万 t/a = 电解净补水 {flows['f_water_el_makeup']:.2f} + "
          f"未分配差额 {flows['f_water_cool']:.2f} 万 t/a（{flows['tt_water_cool'] * 1000.0:.2f} kg/t，"
          f"代数差额，物理去向待实测，非冷却水或损耗认定）")
    print(f"           电解槽总进水 {flows['f_water_el_feed']:.2f} 万 t/a = 电解净补水 {flows['f_water_el_makeup']:.2f} + "
          f"精馏回水 {flows['f_water_gen']:.2f} 万 t/a（回用占电解槽总进水 {flows['water_reuse_pct']:.2f}%、"
          f"占全厂模型取水 {flows['water_reuse_of_plant_pct']:.2f}%）")
    print(f"[能  耗  ] 综合电耗 {flows['e_total']:.3f} 亿 kWh/a"
          f"（制氢 {flows['share_h2']:.1f}%、捕集 {flows['share_co2']:.2f}%、"
          f"循环增压 {flows['share_recycle']:.2f}%、精馏 {flows['share_distill']:.2f}%）")

    out_dir = get_figures_output_dir()
    output_path = os.path.join(out_dir, output_filename)

    fig, ax = plt.subplots(figsize=(16.0, 9.6))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    # --------------------------------------------------------------------------
    # 颜色配置规范（科学客观工程配色）
    # --------------------------------------------------------------------------
    c_bg_box   = "#f7f9fa"
    c_border   = "#2c3e50"
    c_co2      = "#c05621"   # 碳源
    c_h2       = "#1e8449"   # 绿氢
    c_water    = "#1f618d"   # 水系统
    c_meoh     = "#6c3483"   # 甲醇
    c_loop     = "#117a65"   # 未反应气循环
    c_purge    = "#a93226"   # 驰放废气
    c_energy   = "#b9770e"   # 电耗标注
    c_text     = "#2c3e50"
    c_sub      = "#4a5568"

    # --------------------------------------------------------------------------
    # 标题与元数据
    # --------------------------------------------------------------------------
    ax.text(50, 97.4, "工业园区 10 万吨/年二氧化碳加氢制绿色甲醇系统物质与能量流向拓扑图",
            fontsize=15.0, fontweight="bold", ha="center", va="center", color="#17202a")
    ax.text(50, 93.9,
            f"锚点 B 基准 | 精甲醇 {flows['f_product']:.2f} 万 t/a | 年运行 {ANNUAL_HOURS:,.0f} h | "
            f"综合电耗 {flows['e_total']:.3f} 亿 kWh/a | 总碳利用率 {flows['eta_carbon_pct']:.2f}%",
            fontsize=10.2, ha="center", va="center", color="#4d5656")
    ax.text(50, 91.0,
            f"数据源：task3_pareto_frontier.csv 锚点 B 行（f$_{{green}}$ = {flows['f_green_pct']:.1f}%，"
            f"r$_{{purge}}$ = {flows['r_purge_pct']:.4f}%），通量由 kg/t 指标按 10 万 t/a 线性放大",
            fontsize=8.6, ha="center", va="center", color="#707b7c", style="italic")

    # --------------------------------------------------------------------------
    # 辅助绘图函数
    # --------------------------------------------------------------------------
    def draw_unit(x, y, w, h, title, subtitle_lines=(), elec_str=""):
        ax.add_patch(patches.FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.5,rounding_size=1.0",
            facecolor=c_bg_box, edgecolor=c_border, linewidth=1.5, zorder=2))
        ax.text(x + w / 2, y + h - 2.4, title, fontsize=10.2, fontweight="bold",
                ha="center", va="center", color=c_text, zorder=3)
        for i, line in enumerate(subtitle_lines):
            ax.text(x + w / 2, y + h - 5.0 - i * 2.0, line, fontsize=7.9,
                    ha="center", va="center", color=c_sub, zorder=3)
        if elec_str:
            ax.text(x + w / 2, y + 1.7, elec_str, fontsize=7.9, fontweight="bold",
                    ha="center", va="center", color=c_energy, zorder=3)

    def draw_stream_arrow(x_start, y_start, x_end, y_end, color="#333333", width=2.0, rad=0.0):
        style = f"Simple,tail_width={width},head_width={width * 3.0},head_length={width * 2.6}"
        kw = dict(arrowstyle=style, color=color, zorder=4)
        if rad != 0.0:
            arrow = patches.FancyArrowPatch((x_start, y_start), (x_end, y_end),
                                            connectionstyle=f"arc3,rad={rad}", **kw)
        else:
            arrow = patches.FancyArrowPatch((x_start, y_start), (x_end, y_end), **kw)
        ax.add_patch(arrow)

    def draw_label(x, y, text, color, fontsize=8.0, pad=0.28):
        ax.text(x, y, text, fontsize=fontsize, fontweight="bold", ha="center", va="center",
                color=color, zorder=6,
                bbox=dict(boxstyle=f"round,pad={pad}", facecolor="white",
                          edgecolor="none", alpha=0.92))

    # --------------------------------------------------------------------------
    # 核心单元布局
    # --------------------------------------------------------------------------
    draw_unit(7, 70, 18, 16, "烟气 CO2 捕集与压缩单元",
              ["MEA 化学吸收 + 三级压缩 (5.0 MPa)",
               f"捕集量 {flows['f_co2']:.2f} 万 t/a"],
              f"电耗 {flows['e_co2']:.3f} 亿 kWh/a（{flows['share_co2']:.2f}%）")

    draw_unit(7, 34, 18, 16, f"{flows['mw_h2']:.1f} MW 电解水制氢站",
              ["ALK 90 + PEM 40 MW 混联",
               "（未建模备选配置）",
               f"装机 130 MW，产氢 {flows['f_h2']:.2f} 万 t/a",
               f"总进水 {flows['f_water_el_feed']:.2f} 万 t/a"],
              f"电耗 {flows['e_h2']:.3f} 亿 kWh/a（{flows['share_h2']:.1f}%）")

    draw_unit(31, 62, 14, 16, "反应进料混合预热器",
              ["新料与循环气深度混合",
               "230 ℃，5.0 MPa",
               f"入口通量 {flows['f_reactor_in']:.2f} 万 t/a"])

    draw_unit(49, 62, 16, 16, "固定床甲醇合成反应器",
              ["Cu/ZnO/Al2O3 催化剂",
               "250 ℃，5.0 MPa，单程转化率 25.0%",
               f"出口通量 {flows['f_reactor_in']:.2f} 万 t/a"],
              "副产中压蒸汽回供精馏再沸器")

    draw_unit(69, 62, 16, 16, "冷凝分离与循环气分流器",
              ["闪蒸冷凝分离 + 循环分流",
               f"循环 {100.0 - flows['r_purge_pct']:.4f}% / 驰放 {flows['r_purge_pct']:.4f}%",
               f"循环比 {flows['f_recycle_ratio_molar']:.2f}:1（循环气/新鲜气）",
               f"总进料/新鲜进料 {flows['f_feed_ratio_molar']:.2f}:1"],
              f"循环压缩电耗 {flows['e_recycle']:.3f} 亿 kWh/a（{flows['share_recycle']:.2f}%）")

    draw_unit(69, 16, 16, 16, "双塔精馏分离系统",
              ["常压脱轻塔 + 加压脱水精馏塔",
               "甲醇纯度 ≥ 99.85 wt%",
               f"处理粗甲醇 {flows['f_crude']:.2f} 万 t/a"],
              f"精馏电耗 {flows['e_distill']:.3f} 亿 kWh/a（{flows['share_distill']:.2f}%）")

    # --------------------------------------------------------------------------
    # 物质流连线与通量标注
    # --------------------------------------------------------------------------
    # 输入：烟气 CO2
    draw_stream_arrow(0.8, 78.0, 6.8, 78.0, c_co2, width=2.4)
    draw_label(3.6, 82.6, f"原料烟气 CO2\n{flows['f_co2']:.2f} 万 t/a", c_co2)

    # 输入：进入电解槽的新鲜除盐补水（电解净补水；全厂模型取水与未分配差额改由说明框列示）
    draw_stream_arrow(0.8, 42.0, 6.8, 42.0, c_water, width=2.2)
    draw_label(3.6, 46.4, f"电解净补水\n{flows['f_water_el_makeup']:.2f} 万 t/a", c_water)

    # 捕集 CO2 → 混合器 / 电解绿氢 → 混合器（通量已在单元内标注，避免文字堆叠）
    draw_stream_arrow(25.0, 80.0, 30.8, 71.5, c_co2, width=2.2)
    draw_stream_arrow(25.0, 46.5, 30.8, 66.0, c_h2, width=2.2)

    # 制氢站副产纯氧外售
    draw_stream_arrow(16.0, 34.0, 16.0, 20.5, c_loop, width=2.2)
    draw_label(16.0, 17.0, f"副产纯氧外售\n{flows['f_o2']:.2f} 万 t/a", c_loop)

    # 混合器 → 反应器 → 分离器
    draw_stream_arrow(45.0, 70.0, 48.8, 70.0, c_border, width=3.0)
    draw_stream_arrow(65.0, 70.0, 68.8, 70.0, c_border, width=3.0)

    # 未反应气闭环内循环流（自分离器顶部返回混合器，弧线向画面上方绕行以避开单元框）
    draw_stream_arrow(82.0, 78.0, 38.0, 78.0, c_loop, width=2.8, rad=0.22)
    draw_label(60.0, 86.6,
               f"分离器气相 {flows['f_offgas']:.2f} 万 t/a = 闭环回流 {flows['f_recycle']:.2f} + "
               f"驰放气 {flows['f_purge']:.3f}\n"
               f"回流占气相 {100.0 - flows['r_purge_pct']:.4f}%，驰放占 {flows['r_purge_pct']:.4f}%"
               f"（循环比 {flows['f_recycle_ratio_molar']:.2f}:1，循环气/新鲜气）", c_loop,
               fontsize=7.8)

    # 分离器顶部驰放废气
    draw_stream_arrow(85.0, 74.0, 96.8, 79.5, c_purge, width=1.6)
    draw_label(90.8, 82.4,
               f"驰放废气 {flows['r_purge_pct']:.4f}%（送供热锅炉）\n"
               f"{flows['f_purge']:.3f} 万 t/a（碳损耗 {flows['carbon_loss_pct']:.2f}%）", c_purge,
               fontsize=7.6)

    # 分离器底部粗甲醇液相 → 精馏塔
    draw_stream_arrow(77.0, 61.8, 77.0, 32.2, c_meoh, width=2.6)
    draw_label(82.8, 45.0, f"粗甲醇液相\n{flows['f_crude']:.2f} 万 t/a", c_meoh)

    # 精馏塔产品输出
    draw_stream_arrow(85.0, 24.0, 98.2, 24.0, c_meoh, width=2.8)
    draw_label(92.4, 19.6, f"聚合级精甲醇\n{flows['f_product']:.2f} 万 t/a（≥ 99.85 wt%）", c_meoh,
               fontsize=7.8)

    # 精馏釜水回用（闭环至制氢进水）
    draw_stream_arrow(68.8, 20.0, 26.2, 42.0, c_water, width=2.0, rad=0.18)
    draw_label(47.5, 31.6,
               f"精馏釜生成水闭环回用至电解槽\n{flows['f_water_gen']:.2f} 万 t/a"
               f"（占电解槽总进水 {flows['water_reuse_pct']:.1f}%）", c_water,
               fontsize=7.6)

    # 水量分项说明框（全厂模型取水 / 电解净补水 / 未分配差额 / 精馏回水）：
    # 全厂模型取水不画成进入电解槽的物流，未分配差额仅作说明，不画成已确认的冷却水或损耗。
    ax.text(16.0, 58.8,
            f"全厂模型取水 {flows['f_water_plant']:.2f} 万 t/a（{flows['tt_water_plant']:.3f} t/t）\n"
            f"= 电解净补水 {flows['f_water_el_makeup']:.2f} + 未分配差额 "
            f"{flows['f_water_cool']:.2f}（{flows['tt_water_cool'] * 1000.0:.2f} kg/t）\n"
            f"未分配差额：代数差额，物理去向待实测\n"
            f"（不认定为冷却水或损耗，不构成水平衡闭合）\n"
            f"电解槽总进水 {flows['f_water_el_feed']:.2f} 万 t/a\n"
            f"= 电解净补水 {flows['f_water_el_makeup']:.2f} + 回用水 {flows['f_water_gen']:.2f}"
            f"（{flows['water_reuse_pct']:.1f}%）",
            fontsize=7.0, fontweight="bold", ha="center", va="center", color=c_water, zorder=6,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#eaf2f8", edgecolor=c_water,
                      linewidth=0.9, alpha=0.95))

    # --------------------------------------------------------------------------
    # 底部工程指标看板（数值全部由锚点 B 计算）
    # --------------------------------------------------------------------------
    ax.add_patch(patches.FancyBboxPatch((3, 1.0), 94, 11.4, boxstyle="round,pad=0.5,rounding_size=1.0",
                                        facecolor="#ffffff", edgecolor="#aeb6bf", linewidth=1.1, zorder=2))
    ax.text(4.6, 10.7, "【关键规划工程指标对齐汇总（10 万吨/年规模，全部取自任务 3 锚点 B）】",
            fontsize=9.2, fontweight="bold", color=c_text, zorder=3)

    board_rows = [
        (4.8, 8.0, f"● 原料：捕集 CO2 {flows['f_co2']:.2f} 万 t/a（{flows['tt_co2']:.3f} t/t）；"
                   f"电解绿氢 {flows['f_h2']:.2f} 万 t/a（{flows['tt_h2']:.3f} t/t）"),
        (51.5, 8.0, f"● 产品：精甲醇 {flows['f_product']:.2f} 万 t/a；副产纯氧外售 {flows['f_o2']:.2f} 万 t/a"
                    f"（{flows['tt_o2']:.3f} t/t）"),
        (4.8, 5.4, f"● 水系统：全厂模型取水 {flows['f_water_plant']:.2f} 万 t/a"
                   f"= 电解净补水 {flows['f_water_el_makeup']:.2f} + 未分配差额 {flows['f_water_cool']:.2f}"
                   f"（{flows['tt_water_cool'] * 1000.0:.2f} kg/t，待实测）；"
                   f"电解槽总进水 {flows['f_water_el_feed']:.2f} 万 t/a（回水 {flows['f_water_gen']:.2f}），"
                   f"占电解进水 {flows['water_reuse_pct']:.1f}%"),
        (51.5, 5.4, f"● 电耗：{flows['e_total']:.3f} 亿 kWh/a"
                    f"（制氢 {flows['share_h2']:.1f}%、捕集 {flows['share_co2']:.2f}%、"
                    f"循环增压 {flows['share_recycle']:.2f}%、精馏 {flows['share_distill']:.2f}%）"),
        (4.8, 2.8, f"● 碳平衡：新鲜 CO2 含碳 {flows['tt_co2'] * 1000.0 * M_C / MW_CO2:.1f} kg C/t "
                   f"= 产品固碳 {1000.0 * M_C / MW_CH3OH:.1f} + 驰放 {float(row['purge_co2_kg_t']) * M_C / MW_CO2:.1f}"
                   f"（闭合率 100.000%）"),
        (51.5, 2.8, f"● 碳利用率 {flows['eta_carbon_pct']:.2f}%；驰放比 {flows['r_purge_pct']:.4f}%；"
                    f"GWP {flows['gwp_net']:.2f} kg CO2e/t；调整后 LCOM {flows['lcom']:.2f} 元/t"),
    ]
    for x, y, line in board_rows:
        ax.text(x, y, line, fontsize=7.7, va="center", ha="left", color="#34495e", zorder=3)

    # --------------------------------------------------------------------------
    # 输出
    # --------------------------------------------------------------------------
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    plt.subplots_adjust(left=0.005, right=0.995, top=0.995, bottom=0.005)
    plt.savefig(output_path, dpi=OUTPUT_DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"[成功] 工艺物质能量流向拓扑图（{OUTPUT_DPI} DPI）已保存至: {output_path}")
    return output_path


if __name__ == "__main__":
    draw_mfa_process_flow()
