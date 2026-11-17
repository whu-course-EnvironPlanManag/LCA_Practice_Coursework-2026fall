# -*- coding: utf-8 -*-
"""任务2（可视化）：2022 年全球磷全链条物质流桑基图（Plotly 交互式 HTML）。

节点：PMS 磷矿 → CIS 磷化工 → ACS 种植 → LBS 养殖 → RCS 居民 → 环境汇。
流量全部取自 mfa_model 的 2022 年计算结果；LBS 的草地/工业饲料输入
为平衡闭合估算（口径见 mfa_model 文档字符串）。
"""
import plotly.graph_objects as go

import config as C
import data_load as D
from mfa_model import GlobalPModel


def build_sankey():
    m = GlobalPModel(2022)
    f = m.acs.flows()
    Mt = 1e6

    pr = m.pr_p_input() / Mt
    fert = m.fert / Mt
    cis_waste = max(pr - fert, 0.0)          # CIS 平衡残差（磷石膏/非肥产品等）
    feed = f["P_Feed_to_LBS"] / Mt
    harvest_food = max(f["P_Harvest"] / Mt - feed, 0.0)
    manure = m.manure / Mt
    manure_return = f["P_ManureReturn"] / Mt
    manure_waste = max(manure - manure_return, 0.0)
    lbs_loss = m.lbs_processing_loss_p() / Mt
    lbs_products = m.lbs_product_output_p() / Mt
    lbs_other_input = max(lbs_products + manure + lbs_loss - feed, 0.0)  # 草地/工业饲料闭合项
    excreta = m.rcs_excreta_p() / Mt
    excreta_return = m.rcs_excreta_return_p() / Mt
    excreta_env = max(excreta - excreta_return, 0.0)
    food_waste = m.rcs_food_waste_p() / Mt
    rcs_in = harvest_food + lbs_products
    rcs_residual = max(rcs_in - excreta - food_waste, 0.0)               # 供应链残余/体内滞留
    dep = f["P_Deposition"] / Mt
    sd = f["P_SD"] / Mt
    residue_return = f["P_ResidueReturn"] / Mt
    straw_waste = f["P_Straw_Waste"] / Mt
    water = f["P_Drainage_Leaching"] / Mt
    legacy = f["Soil_Legacy_P_delta"] / Mt

    nodes = ["PMS 磷矿开采", "CIS 磷化工", "ACS 农田种植", "LBS 畜禽养殖", "RCS 居民消费",
             "大气沉降", "土壤再分配(SD)", "非耕地饲料(草地/工业,闭合估算)",
             "水体流失", "土壤遗留磷", "废物/流失"]
    idx = {n: i for i, n in enumerate(nodes)}

    # 内部环流处理：秸秆还田(residue_return)为 ACS 内部循环，不画环流。
    # 模型中 legacy = 总输入(含 SD) − 总输出，故已包含 SD 与秸秆还田的累积；
    # 图中 SD 单独作为输入节点，秸秆还田不画，因此遗留输出侧只需扣除 residue_return。
    legacy_drawn = legacy - residue_return

    links = [
        (idx["PMS 磷矿开采"], idx["CIS 磷化工"], pr, "磷矿折纯磷"),
        (idx["CIS 磷化工"], idx["ACS 农田种植"], fert, "矿物磷肥"),
        (idx["CIS 磷化工"], idx["废物/流失"], cis_waste, "化工废物/非肥产品"),
        (idx["大气沉降"], idx["ACS 农田种植"], dep, "大气沉降"),
        (idx["土壤再分配(SD)"], idx["ACS 农田种植"], sd, "SD 沉积输入"),
        (idx["LBS 畜禽养殖"], idx["ACS 农田种植"], manure_return, "粪肥还田"),
        (idx["RCS 居民消费"], idx["ACS 农田种植"], excreta_return, "人粪尿还田"),
    ]
    links = [l for l in links if l[2] > 0]
    links += [
        (idx["ACS 农田种植"], idx["LBS 畜禽养殖"], feed, "饲料粮"),
        (idx["非耕地饲料(草地/工业,闭合估算)"], idx["LBS 畜禽养殖"], lbs_other_input, "牧草与工业饲料"),
        (idx["LBS 畜禽养殖"], idx["RCS 居民消费"], lbs_products, "动物产品"),
        (idx["LBS 畜禽养殖"], idx["废物/流失"], manure_waste, "未管理粪便"),
        (idx["LBS 畜禽养殖"], idx["废物/流失"], lbs_loss, "屠宰加工损失"),
        (idx["ACS 农田种植"], idx["RCS 居民消费"], harvest_food, "作物食物"),
        (idx["RCS 居民消费"], idx["废物/流失"], excreta_env, "污水排泄磷"),
        (idx["RCS 居民消费"], idx["废物/流失"], food_waste, "食物浪费"),
        (idx["RCS 居民消费"], idx["废物/流失"], rcs_residual, "供应链残余"),
        (idx["ACS 农田种植"], idx["水体流失"], water, "排水与淋溶"),
        (idx["ACS 农田种植"], idx["土壤遗留磷"], legacy_drawn, "土壤累积"),
        (idx["ACS 农田种植"], idx["废物/流失"], straw_waste, "秸秆废弃"),
    ]

    fig = go.Figure(go.Sankey(
        node=dict(label=nodes, pad=18, thickness=20,
                  color=["#8c6d3f", "#5b8c85", "#7cb342", "#ef6c00", "#d81b60",
                         "#90a4ae", "#a1887f", "#1e88e5", "#0288d1", "#6d4c41", "#9e9e9e"]),
        link=dict(source=[l[0] for l in links],
                  target=[l[1] for l in links],
                  value=[l[2] for l in links],
                  label=[l[3] for l in links],
                  color="rgba(150,150,150,0.35)"),
    ))
    fig.update_layout(
        title="2022 年全球磷全链条物质流桑基图（Mt P，复现自 Liu et al. 2026 PNAS）",
        font_size=12, width=1200, height=720, margin=dict(l=40, r=40, t=60, b=40))
    out = C.HTML_DIR / "sankey_2022.html"
    fig.write_html(str(out))
    print(f"桑基图已输出: {out}")
    return out


if __name__ == "__main__":
    build_sankey()
