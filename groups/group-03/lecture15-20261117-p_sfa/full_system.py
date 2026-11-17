# -*- coding: utf-8 -*-
"""任务 2：全系统磷物质流模型（PMS/CIS/ACS/LBS/RCS）与守恒自检、桑基图
覆盖磷矿开采、磷化工、农田种植、畜禽养殖、居民消费五个子系统，
所有流量单位 kt P，统一由 build_system() 生成，保证内部一致性。
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from config import P2022

# 节点定义（索引即 Plotly source/target 编号）
NODES = [
    "Phosphate_Mining (PMS)", "Chemical_Industry (CIS)",
    "NonFert_Products", "Grassland", "Cropland (ACS)",
    "Livestock (LBS)", "Crop_Harvest", "Crop_Residue", "Food_Supply",
    "Resident_Consumption (RCS)", "Waste_Treatment (WTS)",
    "Surface_Water (SWS)", "Noncropland_Soil", "Soil_Legacy_P",
    "Grassland_Soil_Stock", "Manure_Storage", "Atmosphere", "Landfill",
    "Trade_and_Other_Losses",
]
N = {name: i for i, name in enumerate(NODES)}
# 边界节点：环境汇与外部源
SINKS = {"Surface_Water (SWS)", "Noncropland_Soil", "Landfill",
         "Trade_and_Other_Losses"}
SOURCES = {"Phosphate_Mining (PMS)"}
STOCKS = {"Soil_Legacy_P", "Grassland_Soil_Stock", "Manure_Storage",
          "Atmosphere"}


def build_system(params=P2022, fert=None, food_supply=4579.0, year=2022,
                 m_ratio=1.36, scenario=None):
    """构建指定年份全系统磷流网络。

    参数
    ----
    params : 2022 基准参数
    fert : 矿物化肥施用量 (kt P)，默认 2022 基准值
    food_supply : 食物磷供给 (kt P/yr，数据驱动)
    m_ratio : 磷矿/化肥比（由 1961-2022 累计开采 1153 Mt 校准）
    scenario : 2050 情景参数字典（由 scenarios.py 传入），None 表示 2022 现状
    """
    if scenario is not None:
        return _build_scenario_system(scenario)
    return _build_2022_system(params, fert, food_supply, m_ratio)


def _build_2022_system(p, fert, food_supply, m_ratio, year=2022):
    F = {}
    fert = p["fert_2022"] if fert is None else fert
    # ---- PMS / CIS ----
    mine = fert * m_ratio
    nonfert = p["nonfert_share"] * mine
    cis_loss = mine - fert - nonfert
    F["mine_total"] = mine
    F["nonfert"] = nonfert
    F["cis_loss"] = cis_loss

    # ---- RCS（先算，供 ACS 有机输入量使用）----
    waste = food_supply * p["food_waste_ratio"]
    intake = food_supply - waste
    sewage = intake + p["detergent_P"]
    water = sewage * ((1 - p["sewage_treated"]) + p["sewage_treated"] * (1 - p["p_removal"]))
    sludge = sewage - water
    sludge_field = sludge * p["sludge_to_field_ratio"]
    landfill = sludge - sludge_field
    compost = waste * p["kitchen_to_feed"]
    waste_loss = waste - compost
    F.update(waste=waste, intake=intake, sewage=sewage, water=water,
             sludge=sludge, sludge_field=sludge_field, landfill=landfill,
             compost=compost, waste_loss=waste_loss)
    # ---- ACS（化肥占比 64% 校准：有机肥反推）----
    others = p["deposition"] + p["seed"] + sludge_field + compost
    manure_applied = fert * (1 - 0.64) / 0.64 - others
    total_in = fert + manure_applied + p["deposition"] + p["seed"] \
        + sludge_field + compost
    harvest = 0.42 * total_in
    uptake = harvest / 0.70
    residue = uptake - harvest
    residue_ret = residue * p["residue_return_ratio"]
    soil_in = total_in + residue_ret
    runoff = p["runoff_coef"] * soil_in
    erosion = p["erosion_coef"] * soil_in
    legacy = soil_in - uptake - runoff - erosion
    food = harvest * 0.45
    feed_crop = p["feed_from_crop"]
    other_uses = harvest - food - feed_crop
    seed_use = p["seed"]
    F.update(fert=fert, manure_applied=manure_applied, total_in_acs=total_in,
             harvest=harvest, uptake=uptake, residue_ret=residue_ret,
             runoff=runoff, erosion=erosion, legacy=legacy, food=food,
             feed_crop=feed_crop, other_uses=other_uses)
    # ---- LBS ----
    products = p["animal_product_P"]
    feed_total = products / p["lbs_pue"]                    # PUE=23% 校准
    byproduct = 1500.0
    additive = 2500.0
    forage = feed_total - feed_crop - byproduct - additive
    gaseous = p["gaseous_ratio"] * feed_total
    grazing_return = 0.30 * forage          # 放牧直接排泄还草（不经收集）
    manure_gen = feed_total - products - gaseous - grazing_return  # 可收集粪污
    unapplied = manure_gen - manure_applied
    lbs_env = p["manure_env_ratio"] * unapplied
    manure_stock = unapplied - lbs_env
    F.update(products=products, feed_total=feed_total, byproduct=byproduct,
             additive=additive, forage=forage, gaseous=gaseous,
             manure_gen=manure_gen, lbs_env=lbs_env, manure_stock=manure_stock)
    # ---- Food 链与秸秆 ----
    food_node_in = food + products
    food_other = food_node_in - food_supply - byproduct
    residue_removed = residue - residue_ret
    F["food_other"] = food_other
    F["food_supply"] = food_supply
    F["residue_removed"] = residue_removed
    # ---- Grassland ----
    dep_pasture = 600.0
    grass_stock = dep_pasture + grazing_return - forage   # 草地土壤磷净消耗
    F.update(dep_pasture=dep_pasture, grass_stock=grass_stock)
    # ---- 生成流列表 (source, target, value, label) ----
    flows = [
        (N["Phosphate_Mining (PMS)"], N["Chemical_Industry (CIS)"], mine, "磷矿供给"),
        (N["Chemical_Industry (CIS)"], N["Cropland (ACS)"], fert, "矿物化肥"),
        (N["Chemical_Industry (CIS)"], N["NonFert_Products"], nonfert, "非肥产品"),
        (N["Chemical_Industry (CIS)"], N["Noncropland_Soil"], cis_loss, "采选加工损失"),
        (N["NonFert_Products"], N["Livestock (LBS)"], additive, "饲料添加剂"),
        (N["NonFert_Products"], N["Resident_Consumption (RCS)"], 500.0, "日化用磷"),
        (N["NonFert_Products"], N["Trade_and_Other_Losses"], nonfert - 3000.0, "其他非肥用途"),
        (N["Atmosphere"], N["Cropland (ACS)"], p["deposition"], "大气沉降(农田)"),
        (N["Atmosphere"], N["Grassland"], 600.0, "大气沉降(草地)"),
        (N["Grassland"], N["Livestock (LBS)"], forage, "牧草饲料"),
        (N["Livestock (LBS)"], N["Cropland (ACS)"], manure_applied, "粪肥还田"),
        (N["Livestock (LBS)"], N["Food_Supply"], products, "畜产品"),
        (N["Livestock (LBS)"], N["Manure_Storage"], manure_stock, "粪污暂存"),
        (N["Livestock (LBS)"], N["Surface_Water (SWS)"], lbs_env * 0.6, "养殖流失(水)"),
        (N["Livestock (LBS)"], N["Noncropland_Soil"], lbs_env * 0.4, "养殖流失(土)"),
        (N["Livestock (LBS)"], N["Atmosphere"], gaseous, "气态损失"),
        (N["Cropland (ACS)"], N["Crop_Harvest"], harvest, "作物收获"),
        (N["Crop_Harvest"], N["Cropland (ACS)"], seed_use, "留种"),
        (N["Crop_Harvest"], N["Food_Supply"], food, "食物原料"),
        (N["Crop_Harvest"], N["Livestock (LBS)"], feed_crop, "饲料粮"),
        (N["Crop_Harvest"], N["Trade_and_Other_Losses"], other_uses - seed_use, "工业及其他用途"),
        (N["Cropland (ACS)"], N["Crop_Residue"], residue, "秸秆残留"),
        (N["Crop_Residue"], N["Cropland (ACS)"], residue_ret, "秸秆还田"),
        (N["Crop_Residue"], N["Trade_and_Other_Losses"], residue_removed, "秸秆离田"),
        (N["Food_Supply"], N["Resident_Consumption (RCS)"], food_supply, "食物供给"),
        (N["Food_Supply"], N["Livestock (LBS)"], byproduct, "加工副产物饲料"),
        (N["Food_Supply"], N["Trade_and_Other_Losses"], food_other, "加工损耗与净出口"),
        (N["Resident_Consumption (RCS)"], N["Waste_Treatment (WTS)"], sewage, "生活污水"),
        (N["Resident_Consumption (RCS)"], N["Cropland (ACS)"], compost, "厨余堆肥还田"),
        (N["Resident_Consumption (RCS)"], N["Trade_and_Other_Losses"], waste_loss, "厨余损耗"),
        (N["Waste_Treatment (WTS)"], N["Surface_Water (SWS)"], water, "污水排放"),
        (N["Waste_Treatment (WTS)"], N["Cropland (ACS)"], sludge_field, "污泥农用"),
        (N["Waste_Treatment (WTS)"], N["Landfill"], landfill, "污泥填埋"),
        (N["Cropland (ACS)"], N["Surface_Water (SWS)"], runoff, "径流淋溶"),
        (N["Cropland (ACS)"], N["Noncropland_Soil"], erosion, "侵蚀"),
        (N["Cropland (ACS)"], N["Soil_Legacy_P"], legacy, "土壤legacy累积"),
        (N["Grassland_Soil_Stock"], N["Grassland"], -grass_stock, "草地土壤磷释放"),
        (N["Livestock (LBS)"], N["Grassland"], grazing_return, "放牧排泄还草"),
    ]
    return flows, F


def _build_scenario_system(s):
    """2050 情景系统（参数由 scenarios.simulate() 提供），结构同 2022。"""
    F = dict(s["F"])
    flows = _build_2022_system(P2022, s["F"]["fert"], s["F"]["food_supply"], s["F"]["m_ratio"])[0]
    return flows, F


def subsystem_balance_table(flows):
    """按子系统聚合输入/输出/存量变化，输出守恒核算表。"""
    sys_in, sys_out = {}, {}
    for s, t, v, lab in flows:
        if s == t:      # 内部循环流（秸秆还田）不计入子系统平衡
            continue
        sn, tn = NODES[s], NODES[t]
        if sn not in SINKS:
            sys_in[sn] = sys_in.get(sn, 0.0) + v
        if tn not in SINKS:
            sys_out[tn] = sys_out.get(tn, 0.0) + v
    # 边界流归属：源节点流入、汇节点流出
    rows = []
    total_stock = 0.0
    for node in NODES:
        if node in SINKS or node in ("Phosphate_Mining (PMS)", "Atmosphere"):
            continue
        if node in STOCKS:
            continue
        rows.append({"子系统": node, "输入": sys_in.get(node, 0.0),
                     "输出": sys_out.get(node, 0.0)})
    df = pd.DataFrame(rows)
    return df


def verify_system_balance(flows, tolerance=1e-4):
    """全系统守恒自检：
    边界输入 − 边界输出 − Σ存量变化 = 0（相对误差 < 1e-4）
    每个库存节点的净流入即其存量变化。"""
    boundary_in = sum(v for s, t, v, l in flows if NODES[s] in SOURCES and NODES[s] != "Atmosphere")
    # Atmosphere 是内部节点（沉降与气态循环），不作为边界输入
    boundary_out = sum(v for s, t, v, l in flows
                       if NODES[t] in SINKS and NODES[t] != "Atmosphere")
    stock_delta = {}
    for s, t, v, l in flows:
        if NODES[t] in STOCKS:
            stock_delta[NODES[t]] = stock_delta.get(NODES[t], 0.0) + v
        if NODES[s] in STOCKS and NODES[t] != NODES[s]:
            stock_delta[NODES[s]] = stock_delta.get(NODES[s], 0.0) - v
    total_stock = sum(stock_delta.values())
    rel = abs(boundary_in - boundary_out - total_stock) / (boundary_in + 1e-6)
    detail = {"边界输入": boundary_in, "边界输出": boundary_out,
              "存量变化合计": total_stock, "相对误差": rel,
              "stock_detail": stock_delta}
    assert rel < tolerance, f"全系统质量守恒未通过，相对误差: {rel:.3e}\n{detail}"
    return detail


# ============ 桑基图（全节点、列内堆叠、按源头配色） ============
# 全部 19 节点保留；节点横向按流程阶段分 7 列，纵向按通量在列内
# 自动堆叠铺满，避免标签重叠；流带按源头节点配色（半透明）。

SANKEY_COLUMNS = {  # 节点 -> (列x, 列内排序号)
    "Phosphate_Mining (PMS)":      (0.015, 0),
    "Grassland":                   (0.015, 1),
    "Chemical_Industry (CIS)":     (0.16,  0),
    "NonFert_Products":            (0.30,  0),
    "Cropland (ACS)":              (0.30,  1),
    "Livestock (LBS)":             (0.46,  0),
    "Crop_Harvest":                (0.46,  1),
    "Crop_Residue":                (0.46,  2),
    "Food_Supply":                 (0.60,  0),
    "Resident_Consumption (RCS)":  (0.72,  0),
    "Waste_Treatment (WTS)":       (0.84,  0),
    "Atmosphere":                  (0.84,  1),
    "Surface_Water (SWS)":         (0.965, 0),
    "Noncropland_Soil":            (0.965, 1),
    "Soil_Legacy_P":               (0.965, 2),
    "Grassland_Soil_Stock":        (0.965, 3),
    "Manure_Storage":              (0.965, 4),
    "Landfill":                    (0.965, 5),
    "Trade_and_Other_Losses":      (0.965, 6),
}

SANKEY_PALETTE = {  # 柔和的多色系（仿能源流图风格）
    "Phosphate_Mining (PMS)": "#c8a165",
    "Grassland": "#a3c9a8",
    "Chemical_Industry (CIS)": "#7295c9",
    "NonFert_Products": "#9b8bb4",
    "Cropland (ACS)": "#6aa9a4",
    "Livestock (LBS)": "#d9a06b",
    "Crop_Harvest": "#8fbc8f",
    "Crop_Residue": "#c9b458",
    "Food_Supply": "#c98b8b",
    "Resident_Consumption (RCS)": "#b48ead",
    "Waste_Treatment (WTS)": "#7fb3d5",
    "Atmosphere": "#cccccc",
    "Surface_Water (SWS)": "#5b8db8",
    "Noncropland_Soil": "#b86b6b",
    "Soil_Legacy_P": "#8a8a8a",
    "Grassland_Soil_Stock": "#a8a29a",
    "Manure_Storage": "#c49a6c",
    "Landfill": "#9aa5b1",
    "Trade_and_Other_Losses": "#ad6a6a",
}


def make_sankey(flows=None, title="2022 年全球人为磷循环物质流（kt P）",
                outfile=None, F=None, height=880):
    """生成交互式桑基图：全节点保留，列内按通量堆叠铺满，流按源头配色。"""
    # 1) 规范化流清单（负值流方向翻转）
    norm = []
    for s, t, v, l in flows:
        if abs(v) <= 1e-6 or s == t:
            continue
        if v < 0:
            norm.append((t, s, -v, l))
        else:
            norm.append((s, t, v, l))

    # 2) 计算各节点吞吐量（取入/出的较大者）
    thru_in, thru_out = {}, {}
    for s, t, v, l in norm:
        thru_in[t] = thru_in.get(t, 0.0) + v
        thru_out[s] = thru_out.get(s, 0.0) + v
    thru = {n: max(thru_in.get(n, 0.0), thru_out.get(n, 0.0))
            for n in NODES}

    # 3) 分列堆叠：每列节点高度 ∝ 吞吐量，纵向铺满 [0,1]
    cols = {}
    for n, (x, order) in SANKEY_COLUMNS.items():
        cols.setdefault(x, []).append((order, n))
    node_x, node_y = {}, {}
    for x, items in cols.items():
        items.sort()
        total = sum(thru[n] for _, n in items) or 1.0
        cum = 0.0
        for _, n in items:
            frac = thru[n] / total
            node_y[n] = cum + frac / 2      # 节点中心
            node_x[n] = x
            cum += frac

    # 4) 流带颜色 = 源头节点色（半透明）
    def hex2rgba(hx, alpha=0.45):
        hx = hx.lstrip("#")
        r, g, b = int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16)
        return f"rgba({r},{g},{b},{alpha})"

    fig = go.Figure(go.Sankey(
        arrangement="fixed",
        node=dict(
            label=NODES,
            pad=10, thickness=22,
            x=[node_x[n] for n in NODES],
            y=[node_y[n] for n in NODES],
            color=[SANKEY_PALETTE.get(n, "#7295c9") for n in NODES],
            line=dict(color="#4d4d4d", width=0.5),
        ),
        link=dict(
            source=[s for s, t, v, l in norm],
            target=[t for s, t, v, l in norm],
            value=[v for s, t, v, l in norm],
            label=[l for s, t, v, l in norm],
            color=[hex2rgba(SANKEY_PALETTE.get(NODES[s], "#7295c9"))
                   for s, t, v, l in norm],
        ),
    ))
    fig.update_layout(title_text=title, font_size=14, width=1500,
                      height=height, margin=dict(l=10, r=10, t=60, b=20))
    if outfile:
        fig.write_html(outfile, include_plotlyjs="cdn")
    return fig


if __name__ == "__main__":
    from data_io import build_task1_dataset, load_food_P_supply_2021, \
        load_population_projection
    from acs_model import calibrate_fert_history
    from config import OUT_DIR

    df, coef, summary, g, crop_s, animal_s = build_task1_dataset()
    fert_hist, alpha = calibrate_fert_history(crop_s)
    m_ratio = 1153000.0 / fert_hist.sum()          # 累计磷矿 1153 Mt 校准
    print(f"化肥历史标定指数 α = {alpha:.3f}；磷矿/化肥比 m_ratio = {m_ratio:.3f}")
    yr, mg, kt = load_food_P_supply_2021()
    flows, F = build_system(food_supply=kt, m_ratio=m_ratio)
    detail = verify_system_balance(flows)
    print("\n=== 全系统质量守恒自检 ===")
    for k, v in detail.items():
        if k != "stock_detail":
            print(f"  {k}: {v:,.1f}" if isinstance(v, float) else f"  {k}: {v}")
    print("  库存变化明细:", {k: round(v, 1) for k, v in detail["stock_detail"].items()})
    print("✅ 全系统守恒断言通过（相对误差 < 1e-4）")
    html = OUT_DIR / "sankey_2022.html"
    make_sankey(flows=flows, outfile=html)
    print(f"\n✅ 桑基图已导出: {html}")
    tbl = subsystem_balance_table(flows)
    print("\n=== 子系统输入/输出核算 (kt P) ===")
    print(tbl.round(0).to_string(index=False))
