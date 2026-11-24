# -*- coding: utf-8 -*-
"""2050 年 BAU 与 Reduce/Replace/Recycle 情景推演（单位：Mt P）。"""

from functools import lru_cache
import os

import pandas as pd
import plotly.graph_objects as go

import data_loader as dl
from mfa_model import GlobalPModel
from png_export import export_png

DEFAULT_REDUCE = 0.20
DEFAULT_REPLACE = 0.75
DEFAULT_RECYCLE = 0.60
COLLECTIBLE_MANURE_SHARE = 0.15


@lru_cache(maxsize=1)
def world_population_ratio():
    """返回 UN WPP 中位预测的 2050/2022 世界人口比。"""
    estimates = dl.load_population_projection("Estimates")
    medium = dl.load_population_projection("Medium variant")
    pop_2022 = estimates.loc[(estimates["Location"] == "World")
                             & (estimates["Year"] == 2022), "Population_thousands"].iloc[0]
    pop_2050 = medium.loc[(medium["Location"] == "World")
                          & (medium["Year"] == 2050), "Population_thousands"].iloc[0]
    return float(pop_2050 / pop_2022)


def prepare_bau(model: GlobalPModel, population_ratio=None):
    """按人口比外推 BAU，供默认情景和回归网格共同复用。"""
    if not model.flows:
        model.build_2022_flows()
    f = model.flows
    ratio = world_population_ratio() if population_ratio is None else population_ratio
    fert = f["P_fert"] * ratio
    nonfert = f["P_nonfert"] * ratio
    animal = f["P_animal_product"] * ratio
    feed = animal / model.LBS_PUE
    manure = feed - animal
    sewage = f["P_sewage"] * ratio
    leaching = f["P_leaching"] * ratio
    manure_loss = f["P_manure_loss"] * ratio
    waste = f["P_waste"] * ratio
    env_loss = nonfert + leaching + manure_loss + sewage + waste
    return {
        "population_ratio": float(ratio), "NPR": fert + nonfert, "CFR": fert,
        "env_loss": env_loss, "fert": fert, "nonfert": nonfert,
        "animal_product": animal, "feed": feed, "manure": manure,
        "manure_return": f["P_manure_return"] * ratio, "sewage": sewage,
        "leaching": leaching, "manure_loss": manure_loss, "waste": waste,
        "struvite_recovered": 0.0, "extra_manure_reused": 0.0,
        "total_p_reduction": 0.0,
    }


def run_policy_scenario(model: GlobalPModel, reduce_rate=DEFAULT_REDUCE,
                        manure_utilization=DEFAULT_REPLACE,
                        struvite_recovery=DEFAULT_RECYCLE, bau=None):
    """运行任意 3R 参数组合；Replace 为可收集粪便的目标利用率。"""
    for name, value in [("Reduce", reduce_rate), ("Replace", manure_utilization),
                        ("Recycle", struvite_recovery)]:
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{name} 参数须位于 [0, 1]，实际为 {value}")
    bau = prepare_bau(model) if bau is None else bau

    collectible_manure = bau["manure"] * COLLECTIBLE_MANURE_SHARE
    extra_manure = max(collectible_manure * manure_utilization - bau["manure_return"], 0.0)
    recovered = bau["sewage"] * struvite_recovery
    cfr = max(bau["fert"] * (1.0 - reduce_rate) - extra_manure - recovered, 0.0)

    # 非化肥需求保持 BAU 绝对量，因此 NPR 不再除以非化肥份额或重复加项。
    npr = cfr + bau["nonfert"]
    # 淋溶随三项措施后的实际矿物化肥投入变化，而非只响应 Reduce。
    leaching = bau["leaching"] * cfr / bau["fert"]
    # 75% 利用率对应基准设定中的 50% 粪便流失削减，其他水平线性插值。
    manure_loss_reduction_share = min((2.0 / 3.0) * manure_utilization, 1.0)
    manure_loss = bau["manure_loss"] * (1.0 - manure_loss_reduction_share)
    sewage = bau["sewage"] * (1.0 - struvite_recovery)
    env_loss = leaching + manure_loss + sewage + bau["waste"] + bau["nonfert"]

    result = {
        "population_ratio": bau["population_ratio"],
        "Reduce": float(reduce_rate), "Replace": float(manure_utilization),
        "Recycle": float(struvite_recovery),
        "NPR": float(npr), "CFR": float(cfr), "env_loss": float(env_loss),
        "leaching": float(leaching), "manure_loss": float(manure_loss),
        "sewage": float(sewage), "nonfert": bau["nonfert"],
        "waste": bau["waste"], "struvite_recovered": float(recovered),
        "extra_manure_reused": float(extra_manure),
        "total_p_reduction": float(bau["env_loss"] - env_loss),
    }
    for key in ["NPR", "CFR", "env_loss", "total_p_reduction"]:
        if result[key] < -1e-10:
            raise AssertionError(f"{key} 出现不合理负值：{result[key]}")
    if recovered > bau["sewage"] + 1e-10 or extra_manure > collectible_manure + 1e-10:
        raise AssertionError("回收量超过可供回收流")
    return result


def run_scenarios(model: GlobalPModel):
    """运行默认 BAU/3R，返回结果字典与中文对比表。"""
    bau = prepare_bau(model)
    policy = run_policy_scenario(model, bau=bau)
    bau_summary = {key: bau[key] for key in
                   ["NPR", "CFR", "env_loss", "animal_product", "manure"]}
    results = {"population_ratio": bau["population_ratio"], "BAU": bau_summary, "3R": policy}
    table = pd.DataFrame({
        "指标": ["原生磷矿需求 NPR (Mt P)", "化学磷肥需求 CFR (Mt P)", "系统环境损失 (Mt P)"],
        "2050 BAU": [bau["NPR"], bau["CFR"], bau["env_loss"]],
        "2050 3R": [policy["NPR"], policy["CFR"], policy["env_loss"]],
    })
    table["削减幅度_%"] = (1.0 - table["2050 3R"] / table["2050 BAU"]) * 100
    return results, table


def export_scenario_figure(table, out_path=None, png_path=None):
    """生成 NPR、CFR、环境损失的 BAU/3R 分组对比图。"""
    out_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = out_path or os.path.join(out_dir, "scenario_2050.html")
    png_path = png_path or os.path.join(out_dir, "scenario_2050.png")
    labels = ["NPR", "CFR", "环境损失"]
    bau = table["2050 BAU"].tolist()
    policy = table["2050 3R"].tolist()
    reductions = table["削减幅度_%"].tolist()
    fig = go.Figure([
        go.Bar(name="2050 BAU", x=labels, y=bau, marker_color="#9e9e9e",
               text=[f"{v:.2f}" for v in bau], textposition="outside"),
        go.Bar(name="2050 3R", x=labels, y=policy, marker_color="#2b8cbe",
               text=[f"{v:.2f}" for v in policy], textposition="outside"),
    ])
    for index, reduction in enumerate(reductions):
        fig.add_annotation(x=index, y=max(bau[index], policy[index]) * 1.13,
                           text=f"削减 {reduction:.1f}%", showarrow=False,
                           font=dict(color="#0868ac", size=14))
    fig.update_layout(
        title="2050 年 BAU 与 3R 情景对比",
        yaxis_title="磷流量 (Mt P)", barmode="group",
        font=dict(size=14, family="Microsoft YaHei, Arial"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        width=1100, height=650, margin=dict(l=70, r=40, t=110, b=70),
    )
    fig.update_yaxes(rangemode="tozero")
    fig.write_html(out_path, include_plotlyjs=True, full_html=True)
    if export_png(out_path, png_path, 1100, 780):
        print(f"[OK] 静态 PNG 已导出：{png_path}")
    else:
        print("[提示] 静态 PNG 导出失败，已保留交互式 HTML。")
    return out_path


if __name__ == "__main__":
    model = GlobalPModel()
    model.build_2022_flows()
    results, table = run_scenarios(model)
    print(f"2050/2022 人口比 = {results['population_ratio']:.4f}")
    print(table.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    print(results["3R"])
