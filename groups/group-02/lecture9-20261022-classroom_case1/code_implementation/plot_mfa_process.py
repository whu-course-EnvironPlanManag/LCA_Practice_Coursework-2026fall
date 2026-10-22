# -*- coding: utf-8 -*-
"""
案例一：废弃 PET 塑料瓶机械物理再生系统 —— MFA 物质流桑基图绘制脚本
====================================================================

基于 data_cohort/mfa_mass_balance.csv 的质量通量数据，使用 plotly.graph_objects.Sankey
绘制“1000 kg 废瓶砖 -> 800 kg rPET + 75 kg HDPE + 各工段杂质损失”的桑基图，
流线宽度与物料通量严格成正比。

输出：
  - process_flow_diagram.png   （高分辨率静态位图，scale=3 => 约 4200px 宽，满足 ≥300dpi）
  - process_flow_diagram.svg   （矢量图，无损缩放）
"""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent / "case_files" / "data_cohort"
PNG_PATH = BASE_DIR / "process_flow_diagram.png"
SVG_PATH = BASE_DIR / "process_flow_diagram.svg"


# ----------------------------------------------------------------------------
# 节点：按“原料 -> 工段 -> 产品/副产/废物”自左向右组织
# ----------------------------------------------------------------------------
LABELS = {
    "input":   "废 PET 瓶砖<br>(1000 kg)",
    "P1":      "拆包·筛分<br>干式脱标",
    "P2":      "热碱洗·漂洗",
    "P3":      "密度浮选<br>分离",
    "P4":      "光学色选<br>脱水·干燥",
    "P5":      "真空挤出<br>造粒·SSP",
    "rPET":    "瓶级 rPET 颗粒<br>(800 kg · 收率80%)",
    "label":   "废标签 PP/PVC<br>(20 kg)",
    "sand":    "泥沙尘土<br>(25 kg)",
    "cod":     "胶水/COD<br>(35 kg)",
    "hdpe":    "副产品 HDPE 瓶盖<br>(75 kg)",
    "hdpe_loss":"HDPE 夹带损失<br>(5 kg)",
    "fines":   "杂色/超细粉<br>(40 kg)",
}

# 节点顺序（即列表索引）
NODE_ORDER = [
    "input", "P1", "P2", "P3", "P4", "P5",
    "rPET", "label", "sand", "cod", "hdpe", "hdpe_loss", "fines",
]
NODE_LABELS = [LABELS[k] for k in NODE_ORDER]

# 节点配色：工段=浅灰蓝，主产品=绿，副产=蓝，废物=橙，原料=深灰
NODE_COLORS = [
    "#4a4a4a",   # input
    "#90bccd", "#90bccd", "#90bccd", "#90bccd", "#90bccd",  # P1..P5
    "#2e8b57",   # rPET 主产品
    "#e07b39", "#e07b39", "#e07b39", "#e07b39", "#e07b39", "#e07b39",  # wastes
]
# 单独把 HDPE 副产标蓝
NODE_COLORS[NODE_ORDER.index("hdpe")] = "#3b7dd8"

# ----------------------------------------------------------------------------
# 链接：source -> target -> value (kg)，保证任一工段入流 = 出流（质量守恒）
# ----------------------------------------------------------------------------
def idx(key: str) -> int:
    return NODE_ORDER.index(key)


LINKS = [
    # (source, target, mass_kg)
    ("input", "P1", 1000.0),
    ("P1", "label", 20.0),
    ("P1", "sand", 25.0),
    ("P1", "P2", 955.0),
    ("P2", "cod", 35.0),
    ("P2", "P3", 920.0),
    ("P3", "hdpe", 75.0),
    ("P3", "hdpe_loss", 5.0),
    ("P3", "P4", 840.0),
    ("P4", "fines", 40.0),
    ("P4", "P5", 800.0),
    ("P5", "rPET", 800.0),
]

sources = [idx(s) for s, _, _ in LINKS]
targets = [idx(t) for _, t, _ in LINKS]
values = [v for _, _, v in LINKS]

# 流线颜色：主产品流=绿，HDPE 副产流=蓝，废物支流=橙，主干原料流=灰
LINK_COLORS = [
    "#8a8a8a",                       # input -> P1
    "#e07b39", "#e07b39",            # P1 -> label / sand
    "#8a8a8a",                       # P1 -> P2
    "#e07b39",                       # P2 -> cod
    "#8a8a8a",                       # P2 -> P3
    "#3b7dd8", "#e07b39", "#8a8a8a", # P3 -> hdpe / hdpe_loss / P4
    "#e07b39", "#8a8a8a",            # P4 -> fines / P5
    "#2e8b57",                       # P5 -> rPET
]


def main() -> None:
    # 读取 CSV 并校验质量守恒，确保与桑基图一致
    mfa = pd.read_csv(DATA_DIR / "mfa_mass_balance.csv")
    total_in = mfa.loc[mfa["Flow_Type"] == "Raw_Material", "Mass_kg"].sum()
    assert abs(total_in - 1000.0) < 1e-6, "原料输入应为 1000 kg"

    fig = go.Figure(
        data=[
            go.Sankey(
                arrangement="snap",
                node=dict(
                    label=NODE_LABELS,
                    color=NODE_COLORS,
                    pad=18,
                    thickness=18,
                    line=dict(color="white", width=1),
                ),
                link=dict(
                    source=sources,
                    target=targets,
                    value=values,
                    color=LINK_COLORS,
                ),
            )
        ]
    )

    fig.update_layout(
        title=dict(
            text="废弃 PET 塑料瓶机械物理再生系统 · 物质流分析 (MFA) 桑基图",
            x=0.5,
            font=dict(size=20),
        ),
        font=dict(size=13, family="Microsoft YaHei, SimHei, sans-serif"),
        width=1400,
        height=760,
        margin=dict(l=20, r=20, t=80, b=20),
    )

    # 高分辨率位图（scale=3 -> 4200×2280 px，满足 ≥300 dpi 打印要求）
    fig.write_image(str(PNG_PATH), scale=3)
    # 矢量图（无损缩放）
    fig.write_image(str(SVG_PATH))

    print(f"桑基图已生成：\n  PNG -> {PNG_PATH}\n  SVG -> {SVG_PATH}")


if __name__ == "__main__":
    main()