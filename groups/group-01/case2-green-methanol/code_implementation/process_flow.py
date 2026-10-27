"""用 Plotly 绘制案例二工艺方框图；流量取自原始 MFA CSV。"""

import csv
from pathlib import Path

import plotly.graph_objects as go


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "case_files" / "data_cohort" / "mfa_reaction_recycle_balance.csv"


def main():
    with SOURCE.open(encoding="utf-8-sig", newline="") as file:
        mass = {r["stream_id"]: float(r["mass_flow_per_ton_product_kg"])
                for r in csv.DictReader(file)}

    fig = go.Figure()

    def box(x0, y0, x1, y1, label, color):
        fig.add_shape(type="rect", x0=x0, y0=y0, x1=x1, y1=y1,
                      line=dict(color="#254253", width=2), fillcolor=color)
        fig.add_annotation(x=(x0+x1)/2, y=(y0+y1)/2, text=label,
                           showarrow=False, align="center", font=dict(size=19, color="#183040"))

    def line(points, color="#486478"):
        for (x0, y0), (x1, y1) in zip(points[:-1], points[1:]):
            fig.add_shape(type="line", x0=x0, y0=y0, x1=x1, y1=y1,
                          line=dict(color=color, width=3))

    def arrow(start, end, color="#486478"):
        fig.add_annotation(x=end[0], y=end[1], ax=start[0], ay=start[1],
                           xref="x", yref="y", axref="x", ayref="y", text="",
                           showarrow=True, arrowhead=3, arrowsize=1.4,
                           arrowwidth=3, arrowcolor=color)

    def label(x, y, text, color="#254253"):
        fig.add_annotation(x=x, y=y, text=text, showarrow=False,
                           align="center", font=dict(size=16, color=color),
                           bgcolor="rgba(255,255,255,0.85)")

    box(0.2, 4.4, 1.9, 5.4, "CO₂ 捕集<br>与压缩", "#DDECF4")
    box(0.2, 2.3, 1.9, 3.3, "PEM 电解水<br>制氢", "#DDECF4")
    box(2.6, 4.2, 3.8, 5.2, "混合器", "#E8F1E3")
    box(4.6, 4.2, 6.3, 5.2, "甲醇合成<br>反应器", "#FCEAD3")
    box(7.1, 4.2, 8.8, 5.2, "冷凝与<br>气液分离", "#E8F1E3")
    box(9.3, 5.8, 10.6, 6.8, "气体分流", "#FCEAD3")
    box(6.2, 6.9, 7.9, 7.9, "循环压缩机", "#DDECF4")
    box(9.3, 2.6, 10.6, 3.6, "双塔精馏", "#E8F1E3")
    box(11.4, 2.6, 13.1, 3.6, "聚合级甲醇<br>1,000 kg", "#D6EBCF")
    box(11.4, 6.0, 13.1, 7.0, "驰放气<br>厂内锅炉", "#F7DFDC")

    arrow((1.9, 4.9), (2.6, 4.9))
    label(2.22, 5.4, f"新鲜 CO₂ {mass['S01']:.0f} kg")
    line([(1.05, 3.3), (1.05, 3.9), (2.3, 3.9), (2.3, 4.5)])
    arrow((2.3, 4.5), (2.6, 4.5))
    label(1.35, 3.67, f"新鲜 H₂ {mass['S02']:.0f} kg")
    arrow((3.8, 4.7), (4.6, 4.7))
    label(4.2, 5.22, f"{mass['S07']:.0f} kg")
    arrow((6.3, 4.7), (7.1, 4.7))
    label(6.7, 5.22, "单程 CO₂ 转化：讲义标称 25%")

    line([(8.8, 4.75), (9.95, 4.75), (9.95, 5.55)])
    arrow((9.95, 5.55), (9.95, 5.8))
    label(9.65, 5.27, f"分离气 {mass['S10']:.0f} kg")
    arrow((10.6, 6.3), (11.4, 6.3))
    label(11.0, 6.8, f"{mass['S11']:.0f} kg")

    line([(9.7, 6.8), (9.7, 7.4), (8.2, 7.4)])
    arrow((8.2, 7.4), (7.9, 7.4), "#207A72")
    line([(6.2, 7.4), (3.2, 7.4), (3.2, 5.5)])
    arrow((3.2, 5.5), (3.2, 5.2), "#207A72")
    label(4.8, 7.65, f"循环气 {mass['S06']:.0f} kg（回流 99.018%）", "#207A72")

    line([(7.95, 4.2), (7.95, 3.1), (9.0, 3.1)])
    arrow((9.0, 3.1), (9.3, 3.1))
    label(8.25, 3.56, f"粗甲醇/水 {mass['S09']:.0f} kg")
    arrow((10.6, 3.1), (11.4, 3.1))
    line([(9.95, 2.6), (9.95, 0.8), (1.05, 0.8), (1.05, 2.0)])
    arrow((1.05, 2.0), (1.05, 2.3), "#207A72")
    label(5.8, 1.09, f"精馏水回用 {mass['S13']:.0f} kg", "#207A72")
    arrow((-0.55, 2.8), (0.2, 2.8))
    label(-0.45, 3.33, f"外购净水<br>{mass['S03']:.0f} kg")
    line([(1.85, 2.3), (1.85, 1.75)])
    arrow((1.85, 1.75), (1.85, 1.48))
    label(2.8, 1.72, f"副产 O₂ {mass['S05']:.0f} kg 外售")

    fig.update_layout(title="绿色甲醇工艺物质流程图（kg / t 精甲醇；按 CSV 原值）",
                      width=2200, height=1300, template="plotly_white",
                      font=dict(family="Microsoft YaHei, Noto Sans CJK SC, Arial"),
                      margin=dict(l=80, r=60, t=110, b=60))
    fig.update_xaxes(range=[-1.1, 13.5], visible=False, fixedrange=True)
    fig.update_yaxes(range=[0.2, 8.35], visible=False, fixedrange=True,
                     scaleanchor="x", scaleratio=1)
    fig.write_image(HERE / "process_flow.svg")
    fig.write_image(HERE / "process_flow.png", scale=2)


if __name__ == "__main__":
    main()
