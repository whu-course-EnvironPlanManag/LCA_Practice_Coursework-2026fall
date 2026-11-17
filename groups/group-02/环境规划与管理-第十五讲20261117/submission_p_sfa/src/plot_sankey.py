"""Plotly 交互式桑基图：2022 年全系统磷物质流。"""
from __future__ import annotations

from pathlib import Path

import plotly.graph_objects as go

from .system_model import INTERNAL, SINK, SOURCE, STOCK

COLORS = {
    SOURCE: "#8c8c8c",
    SINK: "#c0392b",
    STOCK: "#b7791f",
    INTERNAL: "#2e6da4",
}

# 按“外源 → 开采 → 化工 → 农田 → 收获 → 养殖 → 消费 → 末端”的顺序排布节点，
# 让主链从左到右贯通，减少回流与交叉。
PIPE_ORDER = [
    "磷矿储量（开采）",
    "磷矿缺口（USGS未覆盖/进口）",
    "化肥进口",
    "大气沉降",
    "种子磷（FAOSTAT 官方估计）",
    "草地放牧饲料（由粪磷闭合反算）",
    "其他食物（水产品等，缺数据）",
    "PMS 磷矿开采",
    "CIS 磷化工",
    "化肥池",
    "ACS 农田",
    "作物收获",
    "LBS 畜禽养殖",
    "RCS 居民消费",
    "污水处理",
    "工业用磷",
    "废弃物与加工损失",
    "地表水",
    "土壤遗留磷",
    "化肥库存",
]

# 手工坐标：横轴按“外源 → 开采 → 化工 → 农田 → 收获 → 养殖/消费 → 末端”分列，
# 纵轴 0 在上、1 在下。Plotly 的自动布局按拓扑排布，无法体现上述主链顺序，
# 故用 fixed 模式固定节点位置，让主链从左到右贯通、汇节点集中在右缘。
NODE_POS = {
    "磷矿储量（开采）": (0.01, 0.20),
    "磷矿缺口（USGS未覆盖/进口）": (0.01, 0.34),
    "化肥进口": (0.01, 0.48),
    "大气沉降": (0.01, 0.62),
    "种子磷（FAOSTAT 官方估计）": (0.01, 0.70),
    "草地放牧饲料（由粪磷闭合反算）": (0.01, 0.84),
    "其他食物（水产品等，缺数据）": (0.01, 0.96),
    "PMS 磷矿开采": (0.15, 0.28),
    "CIS 磷化工": (0.30, 0.35),
    "化肥池": (0.45, 0.44),
    "化肥库存": (0.45, 0.04),
    "ACS 农田": (0.60, 0.58),
    "作物收获": (0.72, 0.54),
    "LBS 畜禽养殖": (0.82, 0.72),
    "RCS 居民消费": (0.88, 0.81),
    "污水处理": (0.94, 0.90),
    "工业用磷": (0.99, 0.10),
    "废弃物与加工损失": (0.99, 0.44),
    "地表水": (0.99, 0.96),
    "土壤遗留磷": (0.55, 0.94),
}


def build_figure(ledger, title: str = "2022 年全球人为磷物质流（Mt P）") -> go.Figure:
    names = [n for n in PIPE_ORDER if n in ledger.kind]
    names += [n for n in ledger.kind if n not in PIPE_ORDER]
    idx = {n: i for i, n in enumerate(names)}

    flows = [f for f in ledger.flows if f.value > 1e-9]
    source = [idx[f.source] for f in flows]
    target = [idx[f.target] for f in flows]
    value = [round(f.value, 6) for f in flows]
    link_color = []
    for f in flows:
        base = COLORS.get(ledger.kind.get(f.source, INTERNAL), "#2e6da4")
        alpha = 0.35 if ledger.kind.get(f.source) != STOCK else 0.55
        r, g, b = (int(base[i:i + 2], 16) for i in (1, 3, 5))
        link_color.append(f"rgba({r},{g},{b},{alpha})")

    node_color = [COLORS.get(ledger.kind.get(n, INTERNAL), "#2e6da4") for n in names]
    node_custom = []
    for n in names:
        inflow = sum(f.value for f in ledger.flows if f.target == n)
        outflow = sum(f.value for f in ledger.flows if f.source == n)
        node_custom.append(f"流入 {inflow:.2f} Mt P<br>流出 {outflow:.2f} Mt P")

    fig = go.Figure(go.Sankey(
        arrangement="fixed",
        node=dict(label=names, color=node_color, pad=18, thickness=16,
                  x=[NODE_POS[n][0] for n in names],
                  y=[NODE_POS[n][1] for n in names],
                  customdata=node_custom, hovertemplate="%{label}<br>%{customdata}<extra></extra>"),
        link=dict(source=source, target=target, value=value, color=link_color,
                  hovertemplate="%{source.label} → %{target.label}<br>%{value:.2f} Mt P<extra></extra>"),
    ))
    fig.update_layout(title=dict(text=title, x=0.5),
                      font=dict(size=12, family="Microsoft YaHei, Arial"),
                      height=780, margin=dict(l=20, r=20, t=70, b=20))
    return fig


def export_html(fig: go.Figure, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(path), include_plotlyjs="cdn")
    return path


def export_png(fig: go.Figure, path: Path,
               width: int = 1600, height: int = 900, scale: float = 2) -> Path:
    """导出静态 PNG，供 GitHub/PR 直接预览（HTML 不会被渲染）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_image(str(path), width=width, height=height, scale=scale)
    return path


def build_scenario_figure(df, baseline=None) -> go.Figure:
    """2050 情景对比：环境流失、磷矿需求、农田 PUE。"""
    import plotly.express as px

    fig = px.bar(
        df, x="情景", y=["环境流失(Mt P)", "磷矿需求(Mt P)"],
        barmode="group", text_auto=".2f",
        title="2050 年情景对比：环境流失与磷矿需求",
    )
    fig.update_layout(height=520, legend_title_text="",
                      font=dict(family="Microsoft YaHei, Arial"),
                      margin=dict(l=20, r=20, t=70, b=20))
    fig.update_xaxes(tickangle=-15)
    return fig
