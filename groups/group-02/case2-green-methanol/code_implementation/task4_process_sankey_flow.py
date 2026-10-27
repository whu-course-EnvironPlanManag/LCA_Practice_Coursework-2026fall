# -*- coding: utf-8 -*-
"""
《环境规划与管理》第十讲实训任务
作者：帕娜尔·阿克木 (Group 02)
任务：工艺流程物质流与能量流拓扑图绘制

功能说明：
  基于任务 3 帕累托拐点 (锚点 B: f_green=100%, r_purge=2.16%) 的工程通量数据，
  绘制工业园区 10 万吨/年绿色甲醇系统的 MFA-EFA 全流程拓扑图。

设计特色：
  - 竖向卡片式布局，主工艺链自上而下
  - 蓝绿主题配色，区分输入/循环/输出物流
  - 底部工程指标汇总看板
"""

import sys
import io
import os

# Windows 环境 UTF-8 编码处理
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# 中文字体配置
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'PingFang SC', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


def ensure_output_directory():
    """确保图表输出目录存在"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(script_dir, "..", "figures_output"),
        os.path.join("figures_output"),
        os.path.join("..", "figures_output")
    ]
    for d in candidates:
        try:
            os.makedirs(d, exist_ok=True)
            return d
        except:
            continue
    return "."


# =============================================================================
# 配色方案 (蓝绿主题 - 现代卡片风格)
# =============================================================================
THEME = {
    "bg": "#FFFFFF",
    "card_fill": "#F0F4F8",
    "card_edge": "#2B6CB0",
    "title_text": "#1A365D",
    "body_text": "#2D3748",
    "sub_text": "#718096",

    "co2_stream": "#C05621",
    "h2_stream": "#2F855A",
    "meoh_stream": "#6B46C1",
    "recycle_stream": "#0987A0",
    "water_stream": "#2B6CB0",
    "waste_stream": "#C53030",
    "main_stream": "#1A365D",

    "energy_badge": "#DD6B20",
    "highlight_box": "#EBF8FF",
    "summary_fill": "#F7FAFC",
    "summary_edge": "#CBD5E0",
}


# =============================================================================
# 辅助绘图函数
# =============================================================================
def draw_card(ax, x, y, w, h, title, detail="", energy=""):
    """绘制工艺单元卡片（带左侧色条）"""
    # 卡片主体
    card = mpatches.FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.3,rounding_size=0.8",
        facecolor=THEME["card_fill"],
        edgecolor=THEME["card_edge"],
        linewidth=1.4,
        zorder=2
    )
    ax.add_patch(card)

    # 左侧色条
    bar = mpatches.FancyBboxPatch(
        (x, y), 0.6, h,
        boxstyle="round,pad=0.1,rounding_size=0.4",
        facecolor=THEME["card_edge"],
        edgecolor="none",
        zorder=3
    )
    ax.add_patch(bar)

    # 标题文字
    title_y = y + h * 0.68
    ax.text(x + w / 2 + 0.3, title_y, title,
            fontsize=9.8, fontweight="bold", ha="center", va="center",
            color=THEME["title_text"], zorder=4)

    # 详情文字
    if detail:
        detail_y = y + h * 0.38
        ax.text(x + w / 2 + 0.3, detail_y, detail,
                fontsize=7.8, ha="center", va="center",
                color=THEME["sub_text"], zorder=4)

    # 能耗标签
    if energy:
        energy_y = y + h * 0.12
        ax.text(x + w / 2 + 0.3, energy_y, energy,
                fontsize=7.2, fontweight="bold", ha="center", va="center",
                color=THEME["energy_badge"],
                bbox=dict(boxstyle="round,pad=0.15", facecolor="#FFFAF0",
                          edgecolor=THEME["energy_badge"], linewidth=0.6, alpha=0.9),
                zorder=4)


def draw_flow(ax, x1, y1, x2, y2, label="", color="#333", width=1.8, curve=0.0,
              label_pos=0.5, label_offset=(0, 1.8)):
    """绘制物流箭头与标注"""
    style = f"Simple,tail_width={width},head_width={width * 3.0},head_length={width * 2.5}"
    arrow_kwargs = dict(arrowstyle=style, color=color, zorder=4)

    if curve != 0.0:
        arrow = mpatches.FancyArrowPatch(
            (x1, y1), (x2, y2),
            connectionstyle=f"arc3,rad={curve}",
            **arrow_kwargs
        )
    else:
        arrow = mpatches.FancyArrowPatch((x1, y1), (x2, y2), **arrow_kwargs)

    ax.add_patch(arrow)

    if label:
        lx = x1 + (x2 - x1) * label_pos + label_offset[0]
        ly = y1 + (y2 - y1) * label_pos + label_offset[1]
        ax.text(lx, ly, label,
                fontsize=7.6, fontweight="bold", ha="center", va="center",
                bbox=dict(boxstyle="round,pad=0.15", facecolor="white",
                          edgecolor="none", alpha=0.88),
                color=color, zorder=5)


# =============================================================================
# 主绘图函数
# =============================================================================
def draw_process_flow_diagram(output_filename="fig1_mfa_process_flow.png"):
    """
    绘制 10 万吨/年绿色甲醇系统物质流与能量流拓扑图
    采用竖向卡片式布局，主工艺链自上而下
    """
    out_dir = ensure_output_directory()
    output_path = os.path.join(out_dir, output_filename)

    fig, ax = plt.subplots(figsize=(14, 16), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    fig.patch.set_facecolor(THEME["bg"])

    # ---- 标题区 ----
    ax.text(50, 97.5,
            "工业园区 10 万吨/年 CO2 加氢制绿色甲醇系统",
            fontsize=16, fontweight="bold", ha="center", va="center",
            color=THEME["title_text"])
    ax.text(50, 95.5,
            "物质流-能量流拓扑图 (MFA-EFA)  |  年运行 8000h  |  碳利用率 96.0%  |  综合电耗 10.826 亿 kWh/a",
            fontsize=9.5, ha="center", va="center", color=THEME["sub_text"])

    # ---- 六大工艺单元卡片布局 (自上而下) ----
    # 第一行：碳捕集 + 电解制氢 (并列)
    draw_card(ax, 5, 78, 28, 11,
              "CO2 捕集压缩单元",
              "MEA 化学吸收 + 三级压缩 (5.0 MPa)",
              "电耗: 0.255 亿kWh/a (2.36%)")

    draw_card(ax, 67, 78, 28, 11,
              "130 MW PEM 电解水制氢站",
              "质子交换膜电解槽阵列 (3.0 MPa)",
              "电耗: 10.296 亿kWh/a (95.10%)")

    # 第二行：混合预热 + 合成反应器 (并列)
    draw_card(ax, 5, 56, 28, 11,
              "反应进料混合预热器",
              "新进料 + 循环气深度混合, 230 C, 5.0 MPa",
              "")

    draw_card(ax, 67, 56, 28, 11,
              "固定床甲醇合成反应器",
              "Cu/ZnO/Al2O3 催化剂, 250 C, 单程转化率 25%",
              "副产中压蒸汽回供再沸器")

    # 第三行：冷凝分离 + 双塔精馏 (并列)
    draw_card(ax, 5, 34, 28, 11,
              "冷凝分离与循环分流器",
              "气液闪蒸冷凝分离器, 循环比 3.8:1",
              "循环压缩电耗: 0.155 亿kWh/a")

    draw_card(ax, 67, 34, 28, 11,
              "双塔精馏分离系统",
              "常压脱轻塔 + 加压脱水精馏塔",
              "脱水精馏电耗: 0.120 亿kWh/a")

    # ---- 外部输入物流 ----
    # 烟气 CO2 原料输入
    draw_flow(ax, 0, 83.5, 5, 83.5,
              "原料烟气 CO2\n14.23 万吨/a",
              THEME["co2_stream"], width=2.2, label_offset=(0, 2.8))

    # 新鲜除盐水输入
    draw_flow(ax, 0, 61.5, 5, 61.5,
              "新鲜脱盐纯水\n13.85 万吨/a (70.7%)",
              THEME["water_stream"], width=2.0, label_offset=(0, 2.8))

    # ---- 单元间主物流连接 ----
    # CO2 捕集 -> 混合预热器
    draw_flow(ax, 19, 78, 19, 67,
              "高纯 CO2: 14.23 万吨/a",
              THEME["co2_stream"], width=2.0, label_offset=(-6.5, 0))

    # 电解制氢 -> 混合预热器 (横向跨越)
    draw_flow(ax, 67, 83.5, 33, 61.5,
              "电解绿氢: 1.98 万吨/a",
              THEME["h2_stream"], width=2.0, curve=0.25, label_offset=(0, 4.0))

    # 混合预热器 -> 合成反应器
    draw_flow(ax, 33, 61.5, 67, 61.5,
              "反应器入口混合气: 62.61 万吨/a",
              THEME["main_stream"], width=2.8, label_offset=(0, 2.5))

    # 合成反应器 -> 冷凝分离器
    draw_flow(ax, 81, 56, 81, 45,
              "反应出口生成物: 62.61 万吨/a",
              THEME["main_stream"], width=2.8, label_offset=(6.5, 0))

    # 冷凝分离器 -> 精馏塔 (纵向连接)
    draw_flow(ax, 19, 34, 19, 22,
              "粗甲醇液体: 15.75 万吨/a",
              THEME["meoh_stream"], width=2.2, label_offset=(-7.0, 0))

    # ---- 循环与副产物流 ----
    # 未反应气闭环内循环 (从分离器回到混合器)
    draw_flow(ax, 5, 39.5, 5, 56,
              "未反应气循环流 (99.0% 回流)\n46.40 万吨/a, 循环比 3.8:1",
              THEME["recycle_stream"], width=2.6, curve=-0.35, label_offset=(-3.5, 0))

    # 驰放废气排放
    draw_flow(ax, 33, 42, 48, 42,
              "驰放废气 (1.0%)\n0.46 万吨/a, 送锅炉掺烧",
              THEME["waste_stream"], width=1.3, label_offset=(0, 2.5))

    # 精馏塔 -> 产品输出
    draw_flow(ax, 67, 39.5, 50, 22,
              "产品: 聚合级精甲醇\n10.00 万吨/a (纯度>=99.85%)",
              THEME["meoh_stream"], width=2.8, curve=0.2, label_offset=(0, -3.5))

    # 电解副产 O2 外售
    draw_flow(ax, 81, 78, 81, 67,
              "阳极副产高纯 O2 (外售)\n15.84 万吨/a",
              THEME["h2_stream"], width=1.8, label_offset=(6.5, 0))

    # 精馏副产水回用 (从精馏塔回到电解制氢站)
    draw_flow(ax, 81, 34, 81, 22,
              "精馏釜副产生成水 (闭环回用)\n5.75 万吨/a, 削减新鲜水耗 29.3%",
              THEME["water_stream"], width=1.8, curve=-0.3, label_offset=(6.5, 0))

    # 回用水连接到电解制氢站进水标注
    ax.text(81, 18,
            "PEM 电解槽总进水: 19.60 万吨/a\n[净补水 70.7% + 回用水 29.3%]",
            fontsize=7.5, fontweight="bold", ha="center", va="center",
            bbox=dict(boxstyle="round,pad=0.25", facecolor=THEME["highlight_box"],
                      edgecolor=THEME["water_stream"], linewidth=0.9),
            color=THEME["water_stream"], zorder=6)

    # ---- 底部工程指标汇总看板 ----
    summary_y = 2
    summary_h = 10
    summary_box = mpatches.FancyBboxPatch(
        (3, summary_y), 94, summary_h,
        boxstyle="round,pad=0.4,rounding_size=0.6",
        facecolor=THEME["summary_fill"],
        edgecolor=THEME["summary_edge"],
        linewidth=1.1,
        zorder=2
    )
    ax.add_patch(summary_box)

    ax.text(5, summary_y + summary_h - 1.5,
            "关键工程指标汇总 (10 万吨/年规模, 锚点 B 工况: f=100%, r=2.16%)",
            fontsize=9.2, fontweight="bold", color=THEME["title_text"], zorder=3)

    col_data = [
        "原料捕集: CO2 14.23 万吨/a (1.423 t/t)\n绿氢需求: H2 1.98 万吨/a (0.198 t/t)",
        "水循环率: 精馏回用 5.75 万吨/a (29.3%)\n净除盐水: 13.85 万吨/a (1.385 t/t)",
        "碳利用率: 96.0% (驰放碳损耗 4.0%)\n副产纯氧: 外售 15.84 万吨/a (1.584 t/t)",
        "全厂电耗: 10.826 亿kWh/a (制氢占95.1%)\n热集成: 反应副产蒸汽回用碳捕集再沸器"
    ]
    col_x = [6, 29, 53, 77]
    for cx, cd in zip(col_x, col_data):
        ax.text(cx, summary_y + 3.5, cd,
                fontsize=7.6, va="center", color=THEME["body_text"], zorder=3)

    # ---- 保存输出 ----
    plt.tight_layout()
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    plt.savefig(output_path, dpi=300)
    plt.close(fig)

    print(f"[完成] 工艺物质流-能量流拓扑图已保存: {output_path}")


# =============================================================================
# 主程序入口
# =============================================================================
if __name__ == "__main__":
    print("=" * 80)
    print("《环境规划与管理》任务 4: 工艺流程 MFA-EFA 拓扑图绘制")
    print("学生: 帕娜尔·阿克木 | Group 02")
    print("=" * 80)
    draw_process_flow_diagram()
