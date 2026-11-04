"""年鉴真实背景统计制图，独立于尚未补齐输入的预测模型。

模块说明：将已提取的湖北年鉴统计绘为可追溯的背景图；保留真实年份和
原统计口径，不推算新能源车安装量、绿电份额或电池退役量。已程序检查，
正式报告引用仍须组员人工核对。
"""
from pathlib import Path
import hashlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from common import ROOT, OUTPUT, InputError, number, source, read_csv
from plot_results import save


def render_yearbook_context(output=OUTPUT):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    rows = read_csv("hubei_yearbook_context.csv")
    plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Microsoft YaHei", "DejaVu Sans"],
                         "font.size": 11, "pdf.fonttype": 42, "svg.fonttype": "none",
                         "axes.spines.top": False, "axes.spines.right": False, "axes.unicode_minus": False})

    def finish(fig, name, selected, note):
        # 原值和单元格保留在data_cohort；图中仅将车辆单位由辆转换为万辆。
        for row in selected:
            source(row, name)
            original = ROOT / row["source"]
            if hashlib.sha256(original.read_bytes()).hexdigest() != row["source_sha256"]:
                raise InputError("年鉴原件已变化，请先重新提取: "+row["source"])
        fig.text(0.09, 0.015, note.replace("。", "。\n", 1).rstrip(), fontsize=9, color="#555555", va="bottom")
        save(fig, output, name, rect=(0, 0.11, 1, 1))

    private = sorted([r for r in rows if r["indicator"] == "私人汽车拥有量"], key=lambda r: int(r["year"]))
    if not private:
        raise InputError("缺少私人汽车统计，请先运行--extract-yearbook")
    years = [int(r["year"]) for r in private]
    if len(set(years)) != len(years) or {r["unit"] for r in private} != {"辆"}:
        raise InputError("私人汽车年份重复或单位不一致")
    fig, ax = plt.subplots(figsize=(10, 5.8))
    ax.plot(years, [number(r["value"], "私人汽车拥有量", 0)/10000 for r in private], "o-", color="#26747c", linewidth=1.6)
    ax.set(xlabel="年份（仅展示年鉴列示年份）", ylabel="私人汽车拥有量（万辆）", title="湖北省私人汽车拥有量：年鉴背景统计")
    ax.set_ylim(bottom=0)
    ax.set_xticks(years)
    ax.tick_params(axis="x", labelsize=9)
    finish(fig, "fig0a_yearbook_private_cars", private,
           "来源：湖北统计年鉴2025，表1607。含各类燃料汽车；不能作为新能源车保有量或电池装机量。")

    power = [r for r in rows if r["category"] == "electricity_statistics"]
    lookup = {(int(r["year"]), r["indicator"]): number(r["value"], "电力统计", 0) for r in power}
    if len(lookup) != len(power) or {r["unit"] for r in power} != {"亿kWh"}:
        raise InputError("电力统计键重复或单位不一致")
    years = sorted({int(r["year"]) for r in power})
    if not years:
        raise InputError("缺少电力平衡表")
    thermal = [lookup[(y, "火电生产量")] for y in years]
    other = [lookup[(y, "水电核电风电及其他生产量")] for y in years]
    consumption = [lookup[(y, "电力消费量")] for y in years]
    for y, a, b in zip(years, thermal, other):
        if not np.isclose(a+b, lookup[(y, "电力生产量")], rtol=1e-6, atol=1e-3):
            raise InputError("电力分项与总量不匹配，须先核实原表")
    fig, ax = plt.subplots(figsize=(10, 5.8))
    ax.bar(years, thermal, width=0.6, label="火电生产量", color="#a7b3b7")
    ax.bar(years, other, bottom=thermal, width=0.6, label="水电、核电、风电及其他生产量", color="#4f9996")
    ax.plot(years, consumption, "o-", label="电力消费量", color="#9a641d", linewidth=1.8)
    ax.set(xlabel="年份", ylabel="电量（亿kWh）", title="湖北省电力生产结构与消费规模：2019—2023年")
    ax.set_xticks(years)
    ax.set_ylim(0, max(a+b for a, b in zip(thermal, other))*1.32)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    finish(fig, "fig0b_yearbook_electricity", power,
           "来源：湖北统计年鉴2025，表0607（止于2023年）。生产结构不等于消费侧绿电比例或LCA电网因子。")

    cities = [r for r in rows if r["category"] == "city_electricity"]
    lookup = {(r["region"], r["indicator"]): number(r["value"], "城市用电量", 0) for r in cities}
    if not cities or len(lookup) != len(cities) or {r["unit"] for r in cities} != {"亿kWh"} or {r["year"] for r in cities} != {"2024"}:
        raise InputError("城市电量统计缺失、重复或年份/单位不一致")
    names = sorted({r["region"] for r in cities}, key=lambda city: lookup[(city, "全年用电量")], reverse=True)
    y = np.arange(len(names))
    fig, ax = plt.subplots(figsize=(10, 6.8))
    ax.barh(y-0.19, [lookup[(city, "全年用电量")] for city in names], height=0.36, label="全年用电量", color="#a7b3b7")
    ax.barh(y+0.19, [lookup[(city, "工业用电量")] for city in names], height=0.36, label="其中：工业用电量", color="#26747c")
    ax.set_yticks(y, names)
    ax.invert_yaxis()
    ax.set(xlabel="用电量（亿kWh）", title="2024年湖北12个主要城市用电规模")
    ax.legend(frameon=False, loc="lower right", fontsize=10)
    finish(fig, "fig0c_yearbook_city_electricity", cities,
           "来源：湖北统计年鉴2025，表1005。仅限原表12个城市；工业电量包含于全年电量，不是可新增用电容量。")

    print("已生成3张真实年鉴背景图（仅PNG，300 DPI），不是退役预测或寻优结果。")


if __name__ == "__main__":
    render_yearbook_context()
