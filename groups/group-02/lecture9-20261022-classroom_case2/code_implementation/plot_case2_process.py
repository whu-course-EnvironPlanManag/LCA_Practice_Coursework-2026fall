# -*- coding: utf-8 -*-
"""
案例二（任务 3）：CO2 加氢合成绿色甲醇系统 —— 循环回路工艺流程图 (BFD)
========================================================================
使用 schemdraw（纯 Python）绘制带「未反应气循环回路」的方框工艺流程图，
展示原料输入、关键工艺单元、主产品、副产品与驰放气分支。
输出 300 dpi 高清 PNG（白底、深色线条、浅色单元填充，保证在深色/浅色主题下均清晰）。
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

import schemdraw
import schemdraw.elements as elm

OUT_PNG = Path(__file__).resolve().parent / "case2_process_flow.png"

# 单元配色：边框深色 + 填充浅色，区分不同工艺功能
LINE = "#1f3a5f"          # 深蓝灰线条/边框
text_fill = "#eaf3fb"     # 原料
mix_fill = "#dbeafe"      # 混合
rxn_fill = "#fde9d9"      # 反应
sep_fill = "#e6f4ea"      # 分离
spl_fill = "#f3e8ff"      # 分流
dis_fill = "#fff3cd"      # 精馏
prod_fill = "#cfe8d8"     # 主产品
wat_fill = "#d4e6f1"      # 生成水
pur_fill = "#f6dfdf"      # 驰放气


def main() -> None:
    with schemdraw.Drawing(show=False) as d:
        d.config(fontsize=12, font="Microsoft YaHei", lw=2.2, color=LINE)

        # ---------- 节点 ----------
        mixer = elm.RBox(w=2.4, h=1.0).at((2.0, 2.0)).fill(mix_fill).label("气体混合器\n与预热器")
        reactor = elm.RBox(w=3.2, h=1.3).at((6.2, 2.0)).fill(rxn_fill).label(
            "固定床合成反应器\n250℃ · 5.0 MPa\n单程转化率 25%")
        sep = elm.RBox(w=3.0, h=1.3).at((10.6, 2.0)).fill(sep_fill).label("冷凝高压\n气液分离器")
        split = elm.RBox(w=2.8, h=1.0).at((15.0, 2.0)).fill(spl_fill).label("循环气分流器\n99% / 1%")
        dist = elm.RBox(w=2.6, h=1.0).at((10.6, -0.4)).fill(dis_fill).label("双塔精馏提纯")
        product = elm.RBox(w=2.6, h=1.0).at((15.0, -0.4)).fill(prod_fill).label(
            "聚合级精甲醇\n1000 kg (主产品)")
        water = elm.RBox(w=2.9, h=0.9).at((10.6, -2.6)).fill(wat_fill).label(
            "生成水 575 kg\n(微滤后回流电解槽)")
        purge = elm.RBox(w=2.2, h=0.9).at((18.2, 3.4)).fill(pur_fill).label("驰放气 46 kg\n(送锅炉)")
        co2 = elm.RBox(w=2.0, h=0.9).at((-0.4, 3.2)).fill(text_fill).label("新鲜 CO2\n1423 kg")
        h2 = elm.RBox(w=2.0, h=0.9).at((-0.4, 0.8)).fill(text_fill).label("新鲜 H2\n198 kg")

        # ---------- 箭头 ----------
        # 原料进料 -> 混合器
        elm.Arrow().at((-0.4, 2.75)).to((0.8, 2.3))
        elm.Arrow().at((-0.4, 1.25)).to((0.8, 1.7))
        # 混合器 -> 反应器
        elm.Arrow().at((3.2, 2.0)).to((4.6, 2.0))
        # 反应器 -> 分离器
        elm.Arrow().at((7.8, 2.0)).to((9.1, 2.0))
        # 分离器(液) -> 精馏
        elm.Arrow().at((10.6, 1.35)).to((10.6, 0.1))
        # 分离器(气) -> 分流器
        elm.Arrow().at((12.1, 2.0)).to((13.6, 2.0))
        # 精馏 -> 产品
        elm.Arrow().at((11.9, -0.4)).to((13.7, -0.4))
        # 精馏 -> 生成水
        elm.Arrow().at((10.6, -0.9)).to((10.6, -2.15))
        # 分流器 -> 驰放气
        elm.Arrow().at((16.4, 2.35)).to((18.2, 3.09))

        # ---------- 循环回路（分流器 -> 混合器） ----------
        elm.Arrow().at((15.0, 2.5)).to((15.0, 5.0))
        elm.Line().at((15.0, 5.0)).to((2.0, 5.0)).label(
            "未反应循环气 4640 kg (循环比≈3.8:1)", loc="top", ofst=0.12)
        elm.Arrow().at((2.0, 5.0)).to((2.0, 2.5))

        # 分离器液相/气相流量标注
        elm.Label().at((11.9, 0.75)).label("粗甲醇\n1575 kg", fontsize=11)
        elm.Label().at((13.55, 2.45)).label("4686 kg", fontsize=11)

    # 白底（非透明），保证在深色 IDE 主题下也能看清
    d.save(str(OUT_PNG), dpi=300, transparent=False)
    print(f"工艺流程图已保存：{OUT_PNG}")


if __name__ == "__main__":
    main()