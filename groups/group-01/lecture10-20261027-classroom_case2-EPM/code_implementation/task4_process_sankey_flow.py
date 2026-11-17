# -*- coding: utf-8 -*-
"""
课程名称：《环境规划与管理》
案例主题：工业园区二氧化碳捕集耦合绿氢合成绿色甲醇系统
任务编号：任务 4（学生随堂实训版）
脚本名称：task4_process_sankey_flow.py
功能描述：
  读取任务 3 落盘的帕累托拐点（锚点 B）调控参数，调用任务 1 的反应-分离-循环
  联立平衡求解器，得到与锚点 B 严格咬合的吨产品物料定额，再放大至 10 万吨/年，
  绘制物质流（MFA）与能量流（EFA）全流程拓扑图。

【相对讲义原始框架的修订说明】
  1. 原框架把锚点 B 参数（f_green=1.0、r_purge=0.0216）与全部通量写死在绘图函数中，
     与任务 3 求解结果不存在程序化联系。本脚本改为从 anchor_b_params.json 读取，
     保证“第 4 章工程清单”与“第 5 章寻优结果”在数据链条上严格一致。
  2. 原框架 draw_unit() 使用 "\\n" 字面转义序列，matplotlib 不会解析为换行，
     图中会直接输出反斜杠加字母 n。本脚本改用真实换行符。
  3. 原框架循环气 46.40 万吨/年取自 φ=1.0% 的旧工况，与锚点 B 的 φ=2.16% 不匹配；
     本脚本按锚点 B 的 φ 重新求解回路，循环气与驰放气通量均为求解结果。
"""

import sys
import io
import os
import json

# 针对 Windows 控制台编码环境进行 UTF-8 容错封装
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import matplotlib.pyplot as plt
import matplotlib.patches as patches

from task1_mfa_recycle_solver import (
    solve_mfa_balance, verify_element_conservation, MW_H2, FRESH_H2_KG
)

# 统一中文字体（SimHei 缺少 U+2082 下标字符，图中化学式一律使用 mathtext）
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'PingFang SC', 'DejaVu Sans', 'Arial']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['mathtext.fontset'] = 'dejavusans'

ANNUAL_MEOH_TON = 100000.0     # 10 万吨/年
OPERATING_HOURS = 8000.0


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


def load_anchor_b():
    """读取任务 3 输出的锚点 B 参数；若缺失则回退到讲义给定基准值"""
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "anchor_b_params.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f), path
    fallback = {
        "f_green": 1.0, "r_purge": 0.0216, "eta_carbon_pct": 91.78,
        "e_total_kwh": 11247.0, "gwp_net": -1085.2,
        "base_lcom": 3945.9, "lcom_policy_adjusted": 2362.5,
        "mac_policy_adjusted": -37.3, "compliance_status": "RED_III_RFNBO_Certified"
    }
    return fallback, None


def compute_anchor_b_fluxes(anchor):
    """按锚点 B 参数重解回路平衡，并放大至 10 万吨/年工程通量"""
    eta = anchor["eta_carbon_pct"] / 100.0
    r_purge = anchor["r_purge"]

    # 锚点解的吨产品新鲜 CO2 定额：以 96.0% 总碳利用率设计点为基准反算
    fresh_co2_kg = 1423.0 * (0.960 / eta)
    fresh_h2_kg = FRESH_H2_KG * (0.960 / eta)

    res = solve_mfa_balance(purge_ratio=r_purge, fresh_co2_kg=fresh_co2_kg)

    # 单吨定额（kg/t 甲醇）
    per_ton = {
        "fresh_co2_kg": fresh_co2_kg,
        "fresh_h2_kg": fresh_h2_kg,
        "recycle_gas_kg": res["m_gas_recycle_kg"],
        "purge_gas_kg": res["m_gas_purge_kg"],
        "gen_water_kg": res["m_h2o_gen_kg"],
        "net_makeup_water_kg": (1.385 + 0.008 * (0.010 / r_purge)) * 1000.0,
        "byproduct_o2_kg": fresh_h2_kg * 8.0,     # 2H2+O2->2H2O 的氧氢质量比 8.0
        "eta_carbon": res["eta_carbon"],
        "eps_rwgs": res["eps_rwgs"],
        "recycle_ratio_molar": res["recycle_ratio_molar"],
        "recycle_ratio_mass": res["recycle_ratio_mass"],
        "residual": res["residual"],
    }

    # 电耗分项（与任务 3 的能量模型同口径）
    e_h2 = fresh_h2_kg * 52.0
    e_co2 = 255.0 * (fresh_co2_kg / 1423.0)
    e_recycle = 155.0 * ((0.010 / r_purge) ** 0.65)
    e_distill = 120.0
    e_total = e_h2 + e_co2 + e_recycle + e_distill
    per_ton.update({
        "e_h2_kwh": e_h2, "e_co2_kwh": e_co2,
        "e_recycle_kwh": e_recycle, "e_distill_kwh": e_distill,
        "e_total_kwh": e_total,
    })

    # 放大至 10 万吨/年（质量：万吨/年；电量：亿 kWh/年）
    sf = ANNUAL_MEOH_TON
    annual = {
        "fresh_co2_10kt": per_ton["fresh_co2_kg"] * sf / 1e7,
        "fresh_h2_10kt": per_ton["fresh_h2_kg"] * sf / 1e7,
        "recycle_gas_10kt": per_ton["recycle_gas_kg"] * sf / 1e7,
        "purge_gas_10kt": per_ton["purge_gas_kg"] * sf / 1e7,
        "gen_water_10kt": per_ton["gen_water_kg"] * sf / 1e7,
        "net_makeup_water_10kt": per_ton["net_makeup_water_kg"] * sf / 1e7,
        "byproduct_o2_10kt": per_ton["byproduct_o2_kg"] * sf / 1e7,
        "power_100m_kwh": per_ton["e_total_kwh"] * sf / 1e8,
        "hourly_meoh_t": sf / OPERATING_HOURS,
    }
    annual["total_water_intake_10kt"] = annual["net_makeup_water_10kt"] + annual["gen_water_10kt"]
    annual["share_h2"] = per_ton["e_h2_kwh"] / e_total * 100.0
    annual["share_co2"] = per_ton["e_co2_kwh"] / e_total * 100.0
    annual["share_recycle"] = per_ton["e_recycle_kwh"] / e_total * 100.0
    annual["share_distill"] = per_ton["e_distill_kwh"] / e_total * 100.0
    return per_ton, annual, res


# ==============================================================================
# 绘图
# ==============================================================================
def draw_mfa_process_flow(output_filename="fig1_mfa_process_flow.png"):
    """绘制园区级 10 万吨/年绿色甲醇工程物质与能量流动拓扑图"""
    out_dir = get_figures_output_dir()
    output_path = os.path.join(out_dir, output_filename)

    anchor, anchor_path = load_anchor_b()
    per_ton, annual, res = compute_anchor_b_fluxes(anchor)

    print("=" * 88)
    print("《环境规划与管理》任务 4：锚点 B 工况物质流与能量流拓扑图绘制")
    print("=" * 88)
    if anchor_path:
        print(f"[参数来源] 已读取任务 3 锚点 B 参数: {anchor_path}")
    else:
        print("[参数来源] 未找到 anchor_b_params.json，回退至讲义基准参数（请先运行任务 3）")
    print(f"[回路求解] 锚点 B 工况 fsolve 最大残差 = {per_ton['residual']:.3e}")
    print(f"  绿电比例 {anchor['f_green']*100:.1f}% | 驰放比 {anchor['r_purge']*100:.2f}% "
          f"| 严谨碳利用率 {per_ton['eta_carbon']*100:.2f}% | RWGS 选择性 {per_ton['eps_rwgs']*100:.2f}%")
    chk = verify_element_conservation(res)
    print(f"  C/H/O 相对误差 = {chk['C_err']:.2e} / {chk['H_err']:.2e} / {chk['O_err']:.2e}")
    print(f"  循环气 {annual['recycle_gas_10kt']:.2f} 万吨/年 | 驰放气 {annual['purge_gas_10kt']:.2f} 万吨/年 "
          f"| 生成水 {annual['gen_water_10kt']:.2f} 万吨/年")

    fig, ax = plt.subplots(figsize=(16, 10), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    c_bg_box   = "#f7f9fa"
    c_edge_box = "#2c3e50"
    c_co2      = "#c0651a"
    c_h2       = "#1e8449"
    c_water    = "#21618c"
    c_meoh     = "#6c3483"
    c_loop     = "#117a65"
    c_purge    = "#a93226"
    c_o2       = "#148f77"
    c_energy   = "#ca6f1e"

    # 标题
    ax.text(50, 97.5, "工业园区 10 万吨/年二氧化碳加氢制绿色甲醇系统物质流与能量流拓扑图",
            fontsize=16, fontweight="bold", ha="center", va="center", color="#1a252f")
    ax.text(50, 94.0,
            f"规划基准：帕累托拐点（锚点 B） | 绿电比例 {anchor['f_green']*100:.0f}% "
            f"| 驰放分流比 {anchor['r_purge']*100:.2f}% | 年运行 8,000 h "
            f"| 产能 10.00 万吨/年 | 全厂电耗 {annual['power_100m_kwh']:.3f} 亿 kWh/年",
            fontsize=10.0, ha="center", va="center", color="#566573")

    def draw_unit(x, y, w, h, title, lines, elec_str="", subtitle_color="#475569"):
        rect = patches.FancyBboxPatch((x, y), w, h,
                                      boxstyle="round,pad=0.6,rounding_size=1.0",
                                      facecolor=c_bg_box, edgecolor=c_edge_box,
                                      linewidth=1.6, zorder=3)
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h - 2.0, title, fontsize=10.5, fontweight="bold",
                ha="center", va="center", color="#1b2631", zorder=4)
        n = len(lines) + (1 if elec_str else 0)
        y_start = y + h - 5.0
        step = min(3.0, (h - 6.0) / max(n, 1))
        for i, ln in enumerate(lines):
            ax.text(x + w / 2, y_start - i * step, ln, fontsize=8.2,
                    ha="center", va="center", color=subtitle_color, zorder=4)
        if elec_str:
            ax.text(x + w / 2, y_start - len(lines) * step, elec_str, fontsize=8.4,
                    fontweight="bold", ha="center", va="center", color=c_energy, zorder=4)

    def poly_arrow(points, color, width=2.2, ls="-"):
        """正交折线箭头：逐段绘制，末段带箭头"""
        for i in range(len(points) - 1):
            x1, y1 = points[i]
            x2, y2 = points[i + 1]
            if i == len(points) - 2:
                style = f"Simple,tail_width={width},head_width={width*3.0},head_length={width*2.6}"
                ax.add_patch(patches.FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style,
                                                     color=color, linewidth=0, zorder=5,
                                                     linestyle=ls))
            else:
                ax.plot([x1, x2], [y1, y2], color=color, linewidth=width * 0.55,
                        solid_capstyle="butt", zorder=5, linestyle=ls)

    def stream_label(x, y, text, color, ha="center", va="center", fs=8.6):
        ax.text(x, y, text, fontsize=fs, fontweight="bold", ha=ha, va=va, color=color,
                bbox=dict(boxstyle="round,pad=0.25", facecolor="white",
                          edgecolor=color, linewidth=0.7, alpha=0.95), zorder=7)

    # ---------------- 工艺单元 ----------------
    draw_unit(6, 66, 16, 14, "烟气 CO$_2$ 捕集与压缩", [
        "MEA 化学吸收 + 再生",
        "三级压缩至 5.0 MPa",
    ], f"电耗 {annual['share_co2']:.2f}%")

    draw_unit(6, 26, 16, 16, "电解水制氢站", [
        "100 MW ALK + 30 MW PEM",
        "产氢 3.0 MPa / 纯度 99.999%",
    ], f"电耗 {annual['share_h2']:.2f}%")

    draw_unit(30, 54, 14, 13, "进料混合与预热", [
        "新进料与循环气深度混合",
        "230 ℃ / 5.0 MPa",
    ])

    draw_unit(52, 54, 15, 13, "固定床合成反应器", [
        "Cu/ZnO/Al$_2$O$_3$ 催化剂",
        "250 ℃ / 5.0 MPa / 单程 25%",
    ], "副产中压蒸汽回供再沸器")

    draw_unit(75, 54, 15, 14, "冷凝分离与循环分流", [
        "气液闪蒸 + 循环压缩机",
        f"循环比 {per_ton['recycle_ratio_mass']:.2f}:1 / 驰放 {anchor['r_purge']*100:.2f}%",
    ], f"循环压缩电耗 {annual['share_recycle']:.2f}%")

    draw_unit(75, 24, 15, 14, "双塔精馏提纯", [
        "常压脱轻塔 + 加压脱水塔",
        "甲醇纯度 ≥ 99.85 wt%",
    ], f"精馏电耗 {annual['share_distill']:.2f}%")

    # ---------------- 物料流 ----------------
    # 新鲜 CO2
    poly_arrow([(0.5, 73), (6, 73)], c_co2, 3.2)
    stream_label(14, 82.8, f"新鲜捕集高纯 CO$_2$\n{annual['fresh_co2_10kt']:.2f} 万吨/年 "
                           f"({per_ton['fresh_co2_kg']:.1f} kg/t)", c_co2)
    # CO2 -> 混合器
    poly_arrow([(22, 73), (28, 73), (28, 62.5), (30, 62.5)], c_co2, 2.6)
    stream_label(25.0, 68.2, "高纯 CO$_2$", c_co2, fs=8.0)

    # 新鲜绿氢 B -> 混合器
    poly_arrow([(22, 31), (28, 31), (28, 58.0), (30, 58.0)], c_h2, 2.6)
    stream_label(23.6, 47.0, f"电解绿氢\n{annual['fresh_h2_10kt']:.2f} 万吨/年", c_h2, fs=8.0)

    # 新鲜水补水
    poly_arrow([(0.5, 35), (6, 35)], c_water, 2.4)
    stream_label(1.0, 22.8, f"外购除盐纯水\n{annual['net_makeup_water_10kt']:.2f} 万吨/年",
                 c_water, ha="left")

    # 副产纯氧外售
    poly_arrow([(20, 26), (20, 21.8)], c_o2, 2.2)
    stream_label(21.2, 21.5, f"副产纯 O$_2$ {annual['byproduct_o2_10kt']:.2f} 万吨/年（外售）",
                 c_o2, ha="left", fs=8.2)

    # 生成水闭环 F -> B
    poly_arrow([(78, 24), (78, 17), (8, 17), (8, 26)], c_water, 2.0)
    stream_label(48, 19.2, f"精馏塔釜生成水 100% 闭环回用  {annual['gen_water_10kt']:.2f} 万吨/年"
                           f"（占电解总进水 {annual['gen_water_10kt']/annual['total_water_intake_10kt']*100:.1f}%）",
                 c_water, fs=8.0)

    # 混合器 -> 反应器
    poly_arrow([(44, 60.5), (52, 60.5)], "#34495e", 3.4)
    stream_label(48, 63.2, "反应器入口混合气", "#34495e", fs=8.4)

    # 反应器 -> 分离器
    poly_arrow([(67, 60.5), (75, 60.5)], "#34495e", 3.4)
    stream_label(71, 63.2, "反应出口气液", "#34495e", fs=8.4)

    # 未反应气循环（顶部）
    poly_arrow([(82.5, 68), (82.5, 87), (37, 87), (37, 67)], c_loop, 2.8)
    stream_label(59, 89.2, f"未反应气内循环流（{100-anchor['r_purge']*100:.1f}% 回流）  "
                           f"{annual['recycle_gas_10kt']:.2f} 万吨/年  |  循环比 "
                           f"{per_ton['recycle_ratio_mass']:.2f}:1", c_loop, fs=8.6)

    # 驰放气
    poly_arrow([(90, 64), (97, 64)], c_purge, 1.6)
    stream_label(93.5, 67.0, f"驰放废气\n{annual['purge_gas_10kt']:.2f} 万吨/年", c_purge, fs=8.0)

    # 分离器 -> 精馏塔
    poly_arrow([(82.5, 54), (82.5, 38)], c_meoh, 2.8)
    stream_label(86.6, 46.0, f"粗甲醇液相\n{(annual['gen_water_10kt']+10.0):.2f} 万吨/年",
                 c_meoh, fs=8.2)

    # 精甲醇产品
    poly_arrow([(90, 31), (96, 31)], c_meoh, 3.2)
    stream_label(92.8, 34.0, "聚合级精甲醇\n10.00 万吨/年", c_meoh, fs=8.0)

    # ---------------- 底部指标看板 ----------------
    board = patches.FancyBboxPatch((2, 1.5), 96, 10.0,
                                   boxstyle="round,pad=0.4,rounding_size=0.8",
                                   facecolor="#ffffff", edgecolor="#aab7b8",
                                   linewidth=1.0, zorder=2)
    ax.add_patch(board)
    ax.text(3.0, 10.0, f"【锚点 B 工程指标汇总】（GWP$_{{net}}$ = {anchor['gwp_net']:.1f} kg CO$_2$e/t，"
                       f"净 LCOM = {anchor['lcom_policy_adjusted']:.1f} 元/t，"
                       f"MAC = {anchor['mac_policy_adjusted']:.1f} 元/t CO$_2$e，"
                       f"{anchor['compliance_status']}）",
            fontsize=8.6, fontweight="bold", color="#1b2631", zorder=4)

    cols = [
        (3.5, f"- 新鲜 CO$_2$：{annual['fresh_co2_10kt']:.2f} 万吨/年\n"
              f"- 新鲜绿氢：{annual['fresh_h2_10kt']:.2f} 万吨/年"),
        (27.0, f"- 总碳利用率：{per_ton['eta_carbon']*100:.2f}%\n"
               f"- 驰放碳损耗：{(1-per_ton['eta_carbon'])*100:.2f}%"),
        (51.0, f"- 净取水：{annual['net_makeup_water_10kt']:.2f} 万吨/年\n"
               f"- 电解总进水：{annual['total_water_intake_10kt']:.2f} 万吨/年（回用 "
               f"{annual['gen_water_10kt']/annual['total_water_intake_10kt']*100:.1f}%）"),
        (75.0, f"- 全厂电耗：{annual['power_100m_kwh']:.3f} 亿 kWh/年\n"
               f"- 制氢电耗占比：{annual['share_h2']:.2f}%"),
    ]
    for x, txt in cols:
        ax.text(x, 5.4, txt, fontsize=8.2, va="center", color="#2e4053", zorder=4)

    plt.tight_layout()
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"[图表输出] 物质流与能量流拓扑图已保存至: {output_path}")
    print("=" * 88)
    return per_ton, annual


if __name__ == "__main__":
    draw_mfa_process_flow()
