# -*- coding: utf-8 -*-
"""由统一 MFA 流量台账生成 2022 年交互桑基图和高清静态图。"""

import os

import numpy as np
import plotly.graph_objects as go

from mfa_model import GlobalPModel
from png_export import export_png

_OUT_DIR = os.path.dirname(os.path.abspath(__file__))


def build_sankey_figure(model: GlobalPModel):
    """校验流量和内部节点平衡后构建 Plotly Sankey。"""
    nodes, sources, targets, values = model.sankey_data()
    if not all(isinstance(i, (int, np.integer)) and 0 <= i < len(nodes)
               for i in sources + targets):
        raise ValueError("桑基 source/target 必须为合法的非负整数索引")
    if not np.isfinite(values).all() or any(value < 0 for value in values):
        raise ValueError("桑基连接值必须为有限非负数")
    balances = model.sankey_node_balances()
    failed = balances[balances["相对误差"] >= 1e-4]
    if not failed.empty:
        raise ValueError("桑基内部节点未闭合：\n" + failed.to_string(index=False))

    color_map = {
        "Other_Feed_Sources": "#c7e9c0", "Atmosphere": "#b3cde3",
        "Soil_Legacy_P": "#8a6d3b", "Phosphate_Rock": "#8c6d31",
        "Chemical_Industry": "#e0b84a", "Cropland": "#7bc96f",
        "Crop_Harvest": "#a1d99b", "Livestock": "#f4a582",
        "Consumption": "#c994c7", "Waterbody": "#4292c6",
        "Pasture": "#74c476", "Landfill": "#999999",
        "Live_Animal_Use": "#d8b365", "Consumer_Unallocated": "#bdbdbd",
    }
    fig = go.Figure(data=[go.Sankey(
        arrangement="snap",
        node=dict(pad=15, thickness=22, line=dict(color="black", width=0.5),
                  label=nodes, color=[color_map.get(n, "#cccccc") for n in nodes]),
        link=dict(source=sources, target=targets, value=values,
                  color="rgba(120,120,120,0.35)"),
    )])
    fig.update_layout(
        title="2022 年全球人为磷循环物质流桑基图 (Mt P)<br><sup>负土壤存量变化以 Soil_Legacy_P → Cropland 反向表示</sup>",
        font=dict(size=13, family="Microsoft YaHei, Arial"),
        width=1400, height=800, margin=dict(l=30, r=30, t=90, b=30),
    )
    return fig


def export_sankey(model: GlobalPModel, out_path=None, png_path=None):
    """导出离线 HTML 与高清 PNG，返回 HTML 路径。"""
    fig = build_sankey_figure(model)
    out_path = out_path or os.path.join(_OUT_DIR, "sankey_2022.html")
    png_path = png_path or os.path.splitext(out_path)[0] + ".png"
    fig.write_html(out_path, include_plotlyjs=True, full_html=True)
    if export_png(out_path, png_path, 1400, 920):
        print(f"[OK] 静态 PNG 已导出：{png_path}")
    else:
        print("[提示] 静态 PNG 导出失败，已保留交互式 HTML。")
    return out_path


if __name__ == "__main__":
    model = GlobalPModel()
    model.build_2022_flows()
    model.verify_mass_balance()
    path = export_sankey(model)
    print(f"桑基图已导出：{path}")
    print(f"静态图已导出：{os.path.splitext(path)[0] + '.png'}")
