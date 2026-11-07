#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lecture12 案例三（锂离子电池回收）成员 A 中期建模：图表生成。

产出：
    fig1_mfa_process_flow.png    工序物质流骨架图（含闸门状态与未定义 Li 流量标注）
    fig2_zone_layout.png         园区功能分区示意图
两张图均为 300 DPI，由本目录脚本与 data_cohort 输出驱动，图中不出现未解锁的流量数值。

AI 辅助说明：
    提示词摘要：“以 STAGE_DEFINITION 的 5 段工序与 FUNCTIONAL_ZONES 的 8 个分区绘制两张
    示意图，标注阻断输入编号与‘数值待解锁’，不得在图上出现未解锁的流量数值”。
    人工复核：需成员 A 检查分区衔接与主导风向逻辑。

运行：python code_implementation/plot_figures.py
"""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))

from engineering_plan import FUNCTIONAL_ZONES  # noqa: E402
from mfa_model import (  # noqa: E402
    STAGE_DEFINITION,
    WORKDIR,
    load_handoff,
    module_readiness,
)

FIG_DIR = WORKDIR / "figures_output"
DPI = 300

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

COLOR_ARROW = "#3d4a5c"
COLOR_WARN = "#b3261e"
COLOR_HEADER = "#8c96a1"
COLOR_ZONE = "#e8f1f8"
COLOR_BODY = "#f4f6f8"


def _ready_map(raw: dict) -> dict[str, bool]:
    return {r["module"]: r["ready"] for r in module_readiness(raw)}


def draw_process_flow(raw: dict) -> Path:
    ready = _ready_map(raw)
    fig, ax = plt.subplots(figsize=(16, 8.6))
    ax.set_xlim(0, 16)
    ax.set_ylim(1.4, 8.45)
    ax.axis("off")

    ax.text(0.45, 8.05, "工序物质流骨架图（成员 A 中期成果）", fontsize=19, fontweight="bold", color="#1f2d3d")
    ax.text(0.45, 7.62,
            "规划来料 8 万 t/a 退役整包（团体口径）｜Li 元素流量：未定义（M02/M03/M05）｜"
            f"全流程模型就绪标记 full_process_model_ready = {raw['dataset']['full_process_model_ready']}",
            fontsize=10.5, color="#4a5568")

    xs = [0.35 + i * 3.25 for i in range(5)]
    y, w, h = 4.5, 2.9, 2.6
    for stage_id, name, inflow, outflow, blockers in STAGE_DEFINITION:
        i = int(stage_id[1]) - 1
        ax.add_patch(FancyBboxPatch((xs[i], y), w, h, boxstyle="round,pad=0.04,rounding_size=0.1",
                                    linewidth=1.5, edgecolor="#c9d3dd", facecolor=COLOR_BODY))
        ax.add_patch(FancyBboxPatch((xs[i], y + h - 0.45), w, 0.45, boxstyle="round,pad=0.04,rounding_size=0.1",
                                    linewidth=0, facecolor=COLOR_HEADER))
        ax.text(xs[i] + 0.14, y + h - 0.31, f"{stage_id}  {name}", fontsize=11.5, color="white",
                fontweight="bold", va="center")
        ax.text(xs[i] + 0.14, y + h - 0.76, "入：" + textwrap.fill(inflow, 13), fontsize=7.8,
                color="#243244", va="top", linespacing=1.45)
        ax.text(xs[i] + 0.14, y + 1.42, "出：" + textwrap.fill(outflow, 13), fontsize=7.8,
                color="#243244", va="top", linespacing=1.45)
        ax.text(xs[i] + 0.14, y + 0.66, "Li 元素流量：未定义", fontsize=8.4, color="#6b7684")
        ax.text(xs[i] + 0.14, y + 0.3, f"状态：未解锁（{','.join(blockers)}）", fontsize=8.4, color=COLOR_WARN)

    links = ((0, 1, "整包"), (1, 2, "电芯"), (2, 3, "黑粉"), (3, 4, "浸出液"))
    for left, right, label in links:
        x0, x1 = xs[left] + w + 0.03, xs[right] - 0.03
        ax.add_patch(FancyArrowPatch((x0, y + h / 2), (x1, y + h / 2), arrowstyle="-|>",
                                     mutation_scale=15, linewidth=1.7, color=COLOR_ARROW))
        ax.text((x0 + x1) / 2, y + h / 2 + 0.16, label, fontsize=7.6, color=COLOR_ARROW, ha="center")

    ax.add_patch(FancyBboxPatch((0.35, 1.5), 15.55, 2.05, boxstyle="round,pad=0.04,rounding_size=0.1",
                                linewidth=1, edgecolor="#c9d3dd", facecolor="#fbfcfd"))
    ax.text(0.55, 3.28, "副产物与治理出口（随主工艺路线与 M06/M07 解锁后才能定量）", fontsize=10.5,
            fontweight="bold", color="#1f2d3d")
    side = ("铜箔、铝箔、隔膜（S2）", "电解液与 VOC（S2 尾气）", "浸出渣、除杂渣（S3）",
            "硫酸盐副产品（S4）", "废水、尾气、危废（S5）")
    for k, text in enumerate(side):
        ax.text(0.6 + k * 3.02, 2.9, f"• {text}", fontsize=8.8, color="#3f4c5a")
    ax.text(0.55, 2.5, "说明：箭头只表示工艺衔接，不表示已核定的质量通量；Li 守恒核验"
                       "（相对误差严格 < 5e-4，零输入判 undefined）由 mfa_model.li_balance_check 在数据解锁后执行。",
            fontsize=8.2, color="#6b7684")
    ax.text(0.55, 2.12, "闸门：" + "　".join(
        f"{m}={'READY' if v else 'BLOCKED'}"
        for m, v in ready.items() if m in ("recycling_feed_allocation", "recycling_flow_mfa", "full_plant_li_mfa")),
        fontsize=8.2, color="#6b7684")
    ax.text(0.55, 1.76, "数据来源：A前期数据_IDE交接包_20261103 / a_phase1_ide_handoff.json（只读）；"
                        "组成代理 JR23_LFP_PACK/CELL、JR23_NMC_PACK/CELL", fontsize=7.8, color="#8a96a3")

    fig.tight_layout()
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    out = FIG_DIR / "fig1_mfa_process_flow.png"
    fig.savefig(out, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out


def draw_zone_layout() -> Path:
    fig, ax = plt.subplots(figsize=(14, 9))
    ax.set_xlim(0, 13.2)
    ax.set_ylim(1.0, 8.5)
    ax.axis("off")

    ax.text(0.45, 8.1, "园区功能分区示意图（成员 A 中期成果）", fontsize=19, fontweight="bold", color="#1f2d3d")
    ax.text(0.45, 7.7,
            "边界：仅回收园区，不含邦普时代正极材料与邦普宜化配套原料；面积与规模待 M01/M02/M09 解除后核定",
            fontsize=9.6, color="#4a5568")
    ax.add_patch(FancyArrowPatch((4.0, 7.12), (6.3, 7.12), arrowstyle="-|>", mutation_scale=14,
                                 linewidth=1.5, color="#2f7d4f"))
    ax.text(4.05, 7.22, "主导风向（西北 → 东南）：办公与公用工程置于上风向", fontsize=8.4, color="#2f7d4f")

    boxes = {
        "Z8": (0.45, 6.55, 3.0, 0.85),
        "Z1": (0.45, 4.55, 2.6, 1.8),
        "Z2": (3.55, 4.55, 2.6, 1.8),
        "Z3": (6.65, 4.55, 2.6, 1.8),
        "Z4": (9.75, 4.55, 2.6, 1.8),
        "Z7": (3.7, 1.9, 2.5, 1.75),
        "Z5": (6.8, 1.9, 2.5, 1.75),
        "Z6": (9.9, 1.9, 2.5, 1.75),
    }
    zones = {z["zone_id"]: z for z in FUNCTIONAL_ZONES}
    for zid, (x, y, w, h) in boxes.items():
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04,rounding_size=0.1",
                                    linewidth=1.4, edgecolor="#5b7f9e", facecolor=COLOR_ZONE))
        ax.text(x + 0.12, y + h - 0.24, f"{zid} {zones[zid]['name']}", fontsize=9.6,
                fontweight="bold", color="#1f3b52", va="top")
        if zid == "Z8":
            ax.text(x + 0.12, y + 0.14, "上风向｜面积与规模未定义", fontsize=7.6, color="#8a96a3")
            continue
        wrapped = textwrap.fill(zones[zid]["function"], 15)
        ax.text(x + 0.12, y + h - 0.62, wrapped, fontsize=7.4, color="#3f4c5a",
                va="top", linespacing=1.45)
        ax.text(x + 0.12, y + 0.12, "面积 / 规模：未定义（数值待解锁）", fontsize=7.2, color="#8a96a3")

    flows = (
        ((3.05, 5.45), (3.55, 5.45), None, 0.0, 0.0),
        ((6.15, 5.45), (6.65, 5.45), None, 0.0, 0.0),
        ((9.25, 5.45), (9.75, 5.45), None, 0.0, 0.0),
        ((4.95, 4.55), (4.95, 3.65), "固废 / 危废", 0.60, 0.05),
        ((11.05, 4.55), (11.15, 3.65), "废液", 0.55, 0.05),
        ((10.1, 4.55), (9.2, 3.65), "产品", -1.15, -0.12),
    )
    for (x0, y0), (x1, y1), label, dx, dy in flows:
        ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=13,
                                     linewidth=1.3, color=COLOR_ARROW))
        if label:
            ax.text((x0 + x1) / 2 + dx, (y0 + y1) / 2 + dy, label, fontsize=7.6,
                    color=COLOR_ARROW, ha="left")

    ax.add_patch(Rectangle((0.3, 4.4), 12.15, 2.05, linewidth=1.2, linestyle=(0, (5, 4)),
                           edgecolor=COLOR_WARN, facecolor="none"))
    ax.text(0.45, 1.62, "红色虚线 = 安全缓冲区：防火分区、防爆间距与卫生防护距离按现行规范及环评 / 安评核定，本阶段不填数值",
            fontsize=8.2, color=COLOR_WARN)
    ax.text(0.45, 1.33, "箭头表示物料衔接方向（横向为工序衔接，纵向为产物、废液与固废去向）；Z6 紧邻 Z4 以便废液自流收集，"
                        "Z7 独立设于生产区外侧便于危废车辆转运。分区面积、层高与间距均为待解锁项，不以 0 代替。",
            fontsize=7.6, color="#5b6b7b")

    fig.tight_layout()
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    out = FIG_DIR / "fig2_zone_layout.png"
    fig.savefig(out, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out


def main() -> int:
    raw = load_handoff()
    print("生成图表（DPI=%d）：" % DPI)
    for path in (draw_process_flow(raw), draw_zone_layout()):
        print(f"    {path.relative_to(WORKDIR)}  {path.stat().st_size / 1024:,.0f} KB  {DPI} DPI")
    print("完成：两张图来自脚本与交接包数据，图中不出现未解锁的流量数值。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
