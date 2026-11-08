"""从逐年物质流与守恒表生成二次锂供应趋势及代表年锂流图。"""
from collections import defaultdict
import json
import math
from matplotlib.path import Path as MplPath
from matplotlib.patches import PathPatch, Rectangle
import matplotlib.pyplot as plt
from common import DATA, RESULTS, OUTPUT, InputError, read_csv, write_csv
from plot_results import save


def summarize_lithium_flows(annual, balances, scenario):
    """按年汇总t Li，核对退役后去向；不将电池质量或LCE作为锂质量。"""
    totals = defaultdict(lambda: defaultdict(float))
    annual_fields = {"Li_retired_kg": "retired_li_t", "Li_collected_kg": "collected_li_t",
                     "Li_refining_input_kg": "refining_input_li_t", "Li_secondary_kg": "secondary_li_t"}
    balance_fields = {"recovered_product_kg": "balance_product_li_t", "refining_residue_kg": "refining_residue_li_t",
                      "outside_formal_system_kg": "outside_formal_li_t", "opening_echelon_kg": "opening_echelon_li_t",
                      "closing_echelon_kg": "closing_echelon_li_t"}
    for row in annual:
        for source, target in annual_fields.items():
            totals[int(row["year"])][target] += float(row[source])/1000
    balance_years = set()
    for row in balances:
        if row["element"] != "Li":
            continue
        year = int(row["year"])
        balance_years.add(year)
        for source, target in balance_fields.items():
            totals[year][target] += float(row[source])/1000
    if balance_years != {int(row["year"]) for row in annual}:
        raise InputError("年度物质流与Li守恒表的年份不一致")
    result = []
    for year, values in sorted(totals.items()):
        if not all(math.isfinite(v) and v >= 0 for v in values.values()):
            raise InputError("锂流汇总包含负值或非有限数值")
        close = lambda a, b: math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)
        if not close(values["secondary_li_t"], values["balance_product_li_t"]):
            raise InputError("DMFA再生Li与守恒表的再生产品不一致")
        if not close(values["refining_input_li_t"], values["secondary_li_t"]+values["refining_residue_li_t"]):
            raise InputError("精炼Li进料与产品、残余之和不一致")
        total_in = values["retired_li_t"]+values["opening_echelon_li_t"]
        total_out = values["secondary_li_t"]+values["refining_residue_li_t"]+values["outside_formal_li_t"]+values["closing_echelon_li_t"]
        if not close(total_in, total_out) or not close(values["retired_li_t"], values["collected_li_t"]+values["outside_formal_li_t"]):
            raise InputError("退役Li、正规收集与库存/产品/残余去向不闭合")
        result.append({"scenario": scenario, "year": year, **values})
    return result


def plot_dmfa_supply(baseline, recommended, planning_start, decision_year, figures):
    """趋势展示全部规划年份；流带宽度只表示代表年的年度锂流量。"""
    base = {r["year"]: r for r in baseline if r["year"] >= planning_start}
    rec = {r["year"]: r for r in recommended if r["year"] >= planning_start}
    if not base or base.keys() != rec.keys() or decision_year not in rec:
        raise InputError("DMFA图缺少一致的规划年份或代表年")
    for year in base:
        if not math.isclose(base[year]["retired_li_t"], rec[year]["retired_li_t"], rel_tol=1e-9, abs_tol=1e-9):
            raise InputError("收集情景不应改变首次退役锂量")
    flow = rec[decision_year]
    if flow["opening_echelon_li_t"] > 1e-9 or flow["closing_echelon_li_t"] > 1e-9:
        raise InputError("本图的代表年流向适用于零梯次库存情景；非零库存须另绘入库与释放流")
    total = flow["retired_li_t"]
    if total <= 0:
        raise InputError("代表年退役锂为零，不能绘制比例流带")
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.6))
    years = sorted(base)
    axes[0].plot(years, [base[y]["retired_li_t"] for y in years], color="#6c7478", label="首次退役锂")
    axes[0].plot(years, [base[y]["secondary_li_t"] for y in years], color="#42788b", linestyle="--", label="基准：再生产品锂")
    axes[0].plot(years, [rec[y]["secondary_li_t"] for y in years], color="#b17a26", label="B收集率情景：再生产品锂")
    axes[0].set(xlabel="年份", ylabel="年度锂流量（t Li/年）", title="(a) 退役锂与二次锂供应")
    axes[0].legend(frameon=False, fontsize=9, loc="upper left")
    axes[0].set_ylim(bottom=0)
    ax = axes[1]
    ax.set(xlim=(0, 1.18), ylim=(0, 1), title=f"(b) {decision_year}年推荐B锂流向（t Li/年）")
    ax.set_axis_off()
    scale = 0.62/total
    collected = flow["collected_li_t"]*scale
    product = flow["secondary_li_t"]*scale
    residue = flow["refining_residue_li_t"]*scale
    outside = flow["outside_formal_li_t"]*scale

    def ribbon(xa, ya, xb, yb, height, color):
        if height <= 0:
            return
        mid = (xa+xb)/2
        vertices = [(xa, ya), (mid, ya), (mid, yb), (xb, yb), (xb, yb+height),
                    (mid, yb+height), (mid, ya+height), (xa, ya+height), (xa, ya)]
        codes = [MplPath.MOVETO, MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4, MplPath.LINETO,
                 MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4, MplPath.CLOSEPOLY]
        ax.add_patch(PathPatch(MplPath(vertices, codes), facecolor=color, edgecolor="none"))

    product_y, residue_y, outside_y = .08, .16+product, .24+product+residue
    ribbon(.058, .14, .43, .14, collected, "#9ac8bf")
    ribbon(.058, .14+collected, .88, outside_y, outside, "#c7ced1")
    ribbon(.448, .14, .88, product_y, product, "#9ac8bf")
    ribbon(.448, .14+product, .88, residue_y, residue, "#e5c795")
    for x, y, height in ((.04, .14, .62), (.43, .14, collected), (.88, product_y, product),
                         (.88, residue_y, residue), (.88, outside_y, outside)):
        if height > 0:
            ax.add_patch(Rectangle((x, y), .018, height, facecolor="#46726e", edgecolor="none"))
    ax.text(.04, .035, f"首次退役锂\n{total:,.2f} t Li", ha="left", va="center", fontsize=9)
    ax.text(.43, .035, f"正规收集\n{flow['collected_li_t']:,.2f} t Li", ha="center", va="center", fontsize=9)
    ax.text(.92, outside_y+outside/2, f"正规系统外流出\n{flow['outside_formal_li_t']:,.2f} t Li", ha="left", va="center", fontsize=9)
    ax.text(.92, product_y+product/2, f"再生产品\n{flow['secondary_li_t']:,.2f} t Li", ha="left", va="center", fontsize=9)
    ax.text(.92, residue_y+residue/2, f"精炼残余\n{flow['refining_residue_li_t']:,.2f} t Li", ha="left", va="center", fontsize=9)
    fig.suptitle("动态物质流：退役资源量、二次锂供应与回收去向", fontsize=12)
    fig.text(.5, .025, "条件情景；远期供应为未施加扩容约束的物质流潜力。代表年流带按锂质量成比例绘制，梯次库存为0。",
             ha="center", fontsize=9)
    save(fig, figures, "fig11_dmfa_lithium_flows", rect=(0, .07, 1, .94))


def build_dmfa_outputs():
    baseline = summarize_lithium_flows(read_csv("dmfa_annual.csv", directory=RESULTS),
                                     read_csv("element_balance.csv", directory=RESULTS), "baseline")
    recommended = summarize_lithium_flows(read_csv("recommended_dmfa_brine.csv", directory=RESULTS),
                                        read_csv("recommended_balance_brine.csv", directory=RESULTS), "B")
    write_csv(RESULTS/"dmfa_lithium_flow_summary.csv", baseline+recommended)
    cfg = json.loads((DATA/"model_config.json").read_text("utf-8"))
    plot_dmfa_supply(baseline, recommended, cfg["planning_start_year"], cfg["decision_year"], OUTPUT)
    return baseline, recommended
