# -*- coding: utf-8 -*-
"""
课程名称：《环境规划与管理》
案例主题：工业园区二氧化碳捕集耦合绿氢合成绿色甲醇系统
任务编号：任务 4（学生完成版）
脚本名称：task4_process_sankey_flow.py
功能描述：
  基于任务 3 求解出的帕累托拐点（锚点 B）工程通量基准数据，绘制工业园区
  10 万吨/年绿色甲醇系统物质流（MFA）与能量流（EFA）拓扑图。
  版式规范：
    1. 流程主线严格自左向右；循环气回流采用就近短回流（冷凝分离 → 混合预热）；
    2. 图例区分 CO2 流 / 氢气流 / 循环气 / 甲醇流 / 水流 / 驰放气六类物质流；
    3. 工艺单元框统一框高并对齐水平网格线；
    4. 文字分五个层级（标题 / 总参数 / 单元信息 / 流量标注 / 指标表），字号递减；
    5. 流量标注统一置于流线侧边空白处，不压线；
    6. 能量流（EFA）数据不在流线上标注，统一置于单元框内橙色备注与底部指标表。
  输出：figures_output/fig1_mfa_process_flow.png（300 DPI）
"""

import sys
import io
import os

if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches

plt.rcParams['font.sans-serif'] = ['Songti SC', 'STHeiti', 'PingFang SC', 'SimHei',
                                   'Microsoft YaHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

def get_figures_output_dir():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    for d in [os.path.join(current_dir, "..", "figures_output"),
              os.path.join("figures_output"), os.path.join("..", "figures_output")]:
        try:
            os.makedirs(d, exist_ok=True)
            return d
        except Exception:
            continue
    return "."

# ==============================================================================
# 物质与能量流向拓扑图（帕累托拐点锚点 B 通量基准）
# ==============================================================================
def draw_mfa_process_flow(output_filename="fig1_mfa_process_flow.png"):
    out_dir = get_figures_output_dir()
    output_path = os.path.join(out_dir, output_filename)

    fig, ax = plt.subplots(figsize=(18.0, 10.2), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    # ---- 物质流配色（图例一致） ----
    C = {"co2": "#e67e22", "h2": "#27ae60", "recycle": "#16a085",
         "meoh": "#8e44ad", "water": "#2980b9", "purge": "#c0392b"}
    EDGE = "#2c3e50"

    # ================= 文字层级 1/2：标题与总参数 =================
    ax.text(50, 96.5, "工业园区 10 万吨/年二氧化碳加氢制绿色甲醇系统物质与能量流向拓扑图（MFA-EFA）",
            fontsize=16.5, fontweight="bold", ha="center", va="center", color="#1a252f")
    ax.text(50, 92.8, "年运行 8,000 h ｜ 精甲醇产能 100,000 t/a ｜ 全厂综合电耗 10.826 亿 kWh/a ｜ 总碳转化利用率 96.5%",
            fontsize=10.5, ha="center", va="center", color="#555555")

    # ---- 对齐网格参考线（极浅，展示单元框水平对齐关系） ----
    for y in (56.0, 69.0, 26.0, 39.0):
        ax.plot([2, 98], [y, y], linestyle=":", linewidth=0.7, color="#95a5a6", alpha=0.25, zorder=1)

    # ---- 文字层级 4 辅助函数：流股标注（置于流线侧边，不压线） ----
    def slabel(x, y, text, color, ha="center", fontsize=8.0):
        ax.text(x, y, text, fontsize=fontsize, fontweight="bold", color=color,
                ha=ha, va="center", zorder=6, linespacing=1.35,
                bbox=dict(boxstyle="round,pad=0.22", facecolor="white",
                          edgecolor=color, linewidth=0.7, alpha=0.97))

    # ---- 文字层级 3：单元框（统一框高 13，标题/说明/电耗三分区） ----
    def unit(x, w, title, lines, elec=""):
        y, h = 56.0, 13.0
        ax.add_patch(patches.FancyBboxPatch((x, y), w, h,
                     boxstyle="round,pad=0.4,rounding_size=0.9",
                     facecolor="#f7f9fa", edgecolor=EDGE, linewidth=1.6, zorder=2))
        ax.text(x + w/2, y + h - 2.6, title, fontsize=10, fontweight="bold",
                ha="center", va="center", color=EDGE, zorder=3, linespacing=1.25)
        ax.text(x + w/2, y + h*0.42, lines, fontsize=7.6,
                ha="center", va="center", color="#475569", zorder=3, linespacing=1.4)
        if elec:
            ax.text(x + w/2, y + 1.7, elec, fontsize=7.8, fontweight="bold",
                    ha="center", va="center", color="#d35400", zorder=3)

    # ---- 物质流箭头（全部实线） ----
    def arrow(p0, p1, color, width=2.2, rad=0.0):
        kw = dict(arrowstyle=f"Simple,tail_width={width},head_width={width*3},head_length={width*2.6}",
                  color=color, zorder=4)
        cs = f"arc3,rad={rad}" if rad else "arc3,rad=0"
        ax.add_patch(patches.FancyArrowPatch(p0, p1, connectionstyle=cs, **kw))

    # =====================================================================
    # 主线单元（统一 y=56..69，自左向右）
    # =====================================================================
    unit(6, 13, "烟气 CO2 捕集\n与压缩单元", "MEA 化学吸收\n三级压缩至 5.0 MPa", "电耗 0.255 亿 kWh/a")
    unit(24, 12, "反应进料\n混合预热器", "新鲜气与循环气混合\n230 ℃，5.0 MPa")
    unit(40, 14, "固定床甲醇\n合成反应器", "Cu/ZnO/Al2O3，250 ℃\n单程转化率 25%", "副产中压蒸汽回供再沸器")
    unit(58, 14, "冷凝分离与\n循环分流器", "气液闪蒸，45 ℃，4.8 MPa\n驰放分流 1.0%", "循环压缩电耗 0.155 亿 kWh/a")
    unit(78, 14, "双塔精馏\n分离系统", "脱轻塔 + 加压脱水塔\n纯度 ≥ 99.85 wt%", "精馏电耗 0.120 亿 kWh/a")

    # 下层单元：电解制氢（统一框高 13，y=26..39，与混合预热器上下对齐）
    ax.add_patch(patches.FancyBboxPatch((24, 26.0), 12, 13.0,
                 boxstyle="round,pad=0.4,rounding_size=0.9",
                 facecolor="#f7f9fa", edgecolor=EDGE, linewidth=1.6, zorder=2))
    ax.text(30, 36.4, "130 MW PEM\n电解水制氢站", fontsize=10, fontweight="bold",
            ha="center", va="center", color=EDGE, zorder=3, linespacing=1.25)
    ax.text(30, 31.5, "ALK/PEM 混联，3.0 MPa\n总进水 19.60 万吨/a", fontsize=7.6,
            ha="center", va="center", color="#475569", zorder=3, linespacing=1.4)
    ax.text(30, 27.7, "电耗 10.296 亿 kWh/a（95.1%）", fontsize=7.8, fontweight="bold",
            ha="center", va="center", color="#d35400", zorder=3)

    # =====================================================================
    # 主线物质流（自左向右）与侧边标注
    # =====================================================================
    # 输入：烟气 CO2（斜向进入，标注置于起点上方空白）
    arrow((1.5, 73.0), (7.5, 65.5), C["co2"], width=2.4, rad=-0.12)
    slabel(4.0, 77.0, "烟气 CO2\n14.23 万吨/a", C["co2"])

    # 捕集 → 混合预热器
    arrow((19, 63.0), (24, 63.0), C["co2"], width=2.4)
    slabel(21.5, 73.2, "高纯 CO2\n14.23 万吨/a", C["co2"])

    # 混合预热器 → 合成反应器
    arrow((36, 63.0), (40, 63.0), EDGE, width=2.8)
    slabel(38.0, 73.6, "混合气\n62.61 万吨/a", EDGE)

    # 合成反应器 → 冷凝分离器
    arrow((54, 63.0), (58, 63.0), EDGE, width=2.8)
    slabel(56.0, 73.6, "反应出口\n62.61 万吨/a", EDGE)

    # 冷凝分离 → 双塔精馏（粗甲醇液相）
    arrow((72, 63.0), (78, 63.0), C["meoh"], width=2.6)
    slabel(75.0, 73.6, "粗甲醇液相\n15.75 万吨/a", C["meoh"])

    # 精馏 → 产品
    arrow((92, 63.0), (98.5, 63.0), C["meoh"], width=3.0)
    slabel(98.0, 73.6, "聚合级精甲醇 10.00 万吨/a", C["meoh"], ha="right")

    # =====================================================================
    # 就近短回流：未反应气内循环（分离器底部 → 混合预热器底部）
    # =====================================================================
    ry = 48.0
    ax.plot([65, 65, 27], [56, ry, ry], color=C["recycle"], linewidth=2.6, zorder=4, solid_capstyle="round")
    arrow((27, ry), (27, 56), C["recycle"], width=2.6)
    slabel(47, ry - 2.8, "未反应气内循环流 46.40 万吨/a（循环比 3.8:1，99.0% 回流）", C["recycle"])

    # 驰放废气（分离器顶部向上，标注置于流线右侧空白）
    arrow((65, 69.0), (65, 79.5), C["purge"], width=1.5)
    slabel(67.5, 77.0, "驰放废气 0.46 万吨/a 送锅炉掺烧\n（全流程碳损耗 4.0%）", C["purge"], ha="left")

    # =====================================================================
    # 电解制氢支线（绿氢上行进混合器）与输入输出流
    # =====================================================================
    arrow((33, 39.0), (33, 56.0), C["h2"], width=2.6)
    slabel(31.0, 42.5, "电解绿氢 1.98 万吨/a", C["h2"], ha="right")

    # 输入：新鲜除盐纯水（标注置于起点下方空白）
    arrow((16.5, 22.0), (24, 30.0), C["water"], width=2.2, rad=0.10)
    slabel(14.5, 18.2, "新鲜除盐纯水\n13.85 万吨/a", C["water"])

    # 输出：副产纯氧外售（垂直向下，标注置于流线右侧空白）
    arrow((30, 26.0), (30, 19.5), C["h2"], width=2.2)
    slabel(32.0, 22.2, "副产高纯氧气外售 15.84 万吨/a", "#16a085", ha="left")

    # 闭环回用：精馏生成水（精馏塔底 → 电解进水池，沿下方走行，标注置于线下空白）
    wy = 19.0
    ax.plot([85, 85, 26], [56, wy, wy], color=C["water"], linewidth=2.2, zorder=4, solid_capstyle="round")
    arrow((26, wy), (26, 26.0), C["water"], width=2.2)
    slabel(56, wy - 2.4, "精馏副产生成水 5.75 万吨/a 100% 闭环回流至制氢进水池（削减新鲜水消耗 29.3%）", C["water"])

    # =====================================================================
    # 图例（物质流分类，置于左上空白区）
    # =====================================================================
    ax.add_patch(patches.FancyBboxPatch((2, 83.0), 40, 7.6,
                 boxstyle="round,pad=0.4,rounding_size=0.8",
                 facecolor="#ffffff", edgecolor="#95a5a6", linewidth=1.0, zorder=2))
    legend_items = [
        (4.0, 88.8, "co2", "CO2 流"), (16.0, 88.8, "h2", "氢气流"), (28.0, 88.8, "recycle", "循环气"),
        (4.0, 85.4, "meoh", "甲醇流"), (16.0, 85.4, "water", "水流"), (28.0, 85.4, "purge", "驰放气"),
    ]
    for lx, ly, key, name in legend_items:
        ax.plot([lx, lx + 3.4], [ly, ly], color=C[key], linewidth=3.0, zorder=3, solid_capstyle="round")
        ax.text(lx + 4.2, ly, name, fontsize=8.2, ha="left", va="center", color=EDGE, zorder=3)
    ax.text(22, 83.8, "实线＝物质流（MFA）；电耗（EFA）标注于单元框内与底部指标表",
            fontsize=7.2, ha="center", va="center", color="#7f8c8d", zorder=3)

    # =====================================================================
    # 文字层级 5：底部指标表（三列表格）
    # =====================================================================
    tx, ty, tw, th = 2.0, 1.2, 96.0, 12.4
    ax.add_patch(patches.FancyBboxPatch((tx, ty), tw, th,
                 boxstyle="round,pad=0.3,rounding_size=0.6",
                 facecolor="#ffffff", edgecolor="#95a5a6", linewidth=1.2, zorder=2))
    c1, c2 = tx + tw/3, tx + tw*2/3
    ax.plot([c1, c1], [ty + 0.8, ty + th - 0.8], color="#bdc3c7", linewidth=1.0, zorder=3)
    ax.plot([c2, c2], [ty + 0.8, ty + th - 0.8], color="#bdc3c7", linewidth=1.0, zorder=3)
    headers = [(tx + tw/6, "物料平衡指标"), (tx + tw/2, "能量流（EFA）指标"), (tx + tw*5/6, "资源与环境指标")]
    for hx, ht in headers:
        ax.text(hx, ty + th - 2.0, ht, fontsize=9.0, fontweight="bold",
                ha="center", va="center", color=EDGE, zorder=3)
    ax.plot([tx + 1, tx + tw - 1], [ty + th - 3.4, ty + th - 3.4], color="#bdc3c7",
            linewidth=0.8, zorder=3)
    table_rows = [
        ("CO2 捕集：14.23 万吨/年（1.423 t/t）", "综合电耗：10.826 亿 kWh/年", "净除盐水：13.85 万吨/年（1.385 t/t）"),
        ("绿氢需求：1.98 万吨/年（0.198 t/t）", "电解制氢 10.296（95.1%）｜捕集压缩 0.255", "生成水回用：5.75 万吨/年（节水 29.3%）"),
        ("精甲醇产品：10.00 万吨/年（≥99.85%）", "循环压缩 0.155｜精馏 0.120（亿 kWh/年）", "总碳利用率 96.5%｜驰放 4,600 t/a｜纯氧 15.84 万吨/a"),
    ]
    row_ys = [ty + th - 5.4, ty + th - 7.6, ty + th - 9.8]
    for row_y, row in zip(row_ys, table_rows):
        for col_x, cell in zip([tx + tw/6, tx + tw/2, tx + tw*5/6], row):
            ax.text(col_x, row_y, cell, fontsize=7.6,
                    ha="center", va="center", color="#34495e", zorder=3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close(fig)
    print(f"[成功] 工艺物质能量流向拓扑图已保存至: {output_path}")

if __name__ == "__main__":
    draw_mfa_process_flow()
