"""案例二：读取原始 CSV，核算循环、元素、LCA 与电价敏感性。"""

import csv
from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots


HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "case_files" / "data_cohort"


def rows(name):
    with (DATA / name).open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def main():
    streams = {r["stream_id"]: r for r in rows("mfa_reaction_recycle_balance.csv")}
    mass = lambda key: float(streams[key]["mass_flow_per_ton_product_kg"])
    pct = lambda key, column: float(streams[key][column]) / 100

    fresh = mass("S01") + mass("S02")
    recycle = mass("S06")
    offgas = mass("S10")
    purge = mass("S11")
    print("=== MFA：CSV 物流，kg/t 甲醇 ===")
    for name, left, right in (
        ("混合器", fresh + recycle, mass("S07")),
        ("反应器", mass("S07"), mass("S08")),
        ("分离器", mass("S08"), mass("S09") + offgas),
        ("分流器", offgas, recycle + purge),
        ("精馏塔", mass("S09"), mass("S12") + mass("S13")),
        ("合成边界", fresh, mass("S12") + mass("S13") + purge),
    ):
        print(f"{name}: 入 {left:.3f}; 出 {right:.3f}; 差 {left-right:+.3f}")
    print(f"实际循环比 R/F={recycle/fresh:.6f}; 回流分率={recycle/offgas:.6%}")

    # 以原表纯物质名义流量计算；原表组分含未知惰性物，不能由其确定 C/H/O。
    c, h, o = 12.01, 1.008, 16.00
    mw_co2, mw_h2, mw_meoh, mw_water, mw_co = c + 2 * o, 2 * h, c + 4 * h + o, 2 * h + o, c + o
    n_co2 = mass("S01") / mw_co2
    n_h2 = mass("S02") / mw_h2
    n_meoh = mass("S12") / mw_meoh
    n_water = mass("S13") / mw_water
    carbon_util = n_meoh / n_co2
    print(f"产品碳利用率={carbon_util:.6%} (名义纯 CO2/甲醇；非 96.0%)")
    purity_util = (mass("S12")*pct("S12", "meoh_wt_pct")/mw_meoh
                   / (mass("S01")*pct("S01", "co2_wt_pct")/mw_co2))
    print(f"按 CSV 纯度修正的已知 CO2→甲醇碳利用率={purity_util:.6%}")

    # 若用三种已知气体 CO2、CO、H2 恰好补齐元素，求得的是反推组成，并非实测。
    implied_co2 = (2*n_co2 - n_meoh - n_water) - (n_co2 - n_meoh)
    implied_co = 2*(n_co2 - n_meoh) - (2*n_co2 - n_meoh - n_water)
    implied_h2 = n_h2 - 2*n_meoh - n_water
    implied_mass = (implied_co2*mw_co2, implied_co*mw_co, implied_h2*mw_h2)
    print("元素闭合所需驰放气 CO2/CO/H2 (反推，不代表 CSV 观测): "
          + ", ".join(f"{x:.6f}" for x in implied_mass))

    # 按 CSV 的质量分数逐股审计；other_inerts 的元素组成未知。
    atomic = {
        "co2_wt_pct": (c/mw_co2, 0, 2*o/mw_co2),
        "h2_wt_pct": (0, 1, 0),
        "meoh_wt_pct": (c/mw_meoh, 4*h/mw_meoh, o/mw_meoh),
        "h2o_wt_pct": (0, 2*h/mw_water, o/mw_water),
        "o2_wt_pct": (0, 0, 1),
    }
    def known_elements(keys):
        return [sum(mass(k)*pct(k, col)*parts[i]
                    for k in keys for col, parts in atomic.items()) for i in range(3)]
    incoming_elements = known_elements(("S01", "S02"))
    outgoing_elements = known_elements(("S11", "S12", "S13"))
    unknown_in = sum(mass(k)*pct(k, "other_inerts_wt_pct") for k in ("S01", "S02"))
    unknown_out = sum(mass(k)*pct(k, "other_inerts_wt_pct") for k in ("S11", "S12", "S13"))
    print(f"CSV 未定组成: 输入={unknown_in:.3f} kg; 输出={unknown_out:.3f} kg")
    for symbol, incoming, known_outgoing in zip("CHO", incoming_elements, outgoing_elements):
        gap = incoming - known_outgoing
        print(f"{symbol}: 输入={incoming:.6f}; 已知输出={known_outgoing:.6f}; "
              f"待解释={gap:+.6f} kg ({abs(gap)/incoming:.4%} 输入)")

    # 理想 CO2-only 回路：反应掉的 CO2 全部离开气相，未反应 CO2 全在气相。
    x_sp, q = 0.25, 0.99
    ideal_recycle_co2 = q*(1-x_sp)*mass("S01")/(1-q*(1-x_sp))
    ideal_purge_co2 = (1-q)*(1-x_sp)*(mass("S01")+ideal_recycle_co2)
    print(f"理想 CO2-only 回路: 循环 CO2={ideal_recycle_co2:.3f}, "
          f"驰放 CO2={ideal_purge_co2:.3f} kg; 总 CO2 转化率="
          f"{(1-ideal_purge_co2/mass('S01')):.6%}")
    co2_in = mass("S07")*pct("S07", "co2_wt_pct")
    co2_out = mass("S08")*pct("S08", "co2_wt_pct")
    print(f"CSV 反应器 CO2 表观单程转化率={(1-co2_out/co2_in):.6%}")

    lci = {r["lci_inventory_item"]: r for r in rows("lca_grid_scenarios_lci.csv")}
    electricity = sum(float(lci[k]["flow_per_ton_product"]) for k in lci if k.startswith("Electricity_"))
    fixed = (float(lci["Direct_Fugitive_Emissions"]["gwp_scenario_a_kgCO2e"])
             + float(lci["Infrastructure_and_Catalyst"]["gwp_scenario_a_kgCO2e"])
             + float(lci["CO2_Capture_Credit"]["gwp_scenario_a_kgCO2e"])
             + float(lci["Byproduct_Oxygen_Credit"]["gwp_scenario_a_kgCO2e"]))
    green_ef = float(lci["Electricity_PEM_Electrolysis"]["ef_scenario_a_green_power"])
    grid_ef = float(lci["Electricity_PEM_Electrolysis"]["ef_scenario_b_regional_grid"])
    benchmark = float(lci["Fossil_Benchmark_CtM"]["gwp_scenario_a_kgCO2e"])
    green_gwp = electricity*green_ef + fixed
    grid_gwp = electricity*grid_ef + fixed
    avoided_t = (benchmark-green_gwp)/1000
    print("=== LCA / TEA ===")
    print(f"用电={electricity:.3f} kWh/t; 非电净项={fixed:.3f} kgCO2e/t")
    print(f"绿电 GWP={green_gwp:.3f}; 网电 GWP={grid_gwp:.3f}; "
          f"绿电避免排放={avoided_t:.6f} tCO2e/t")

    tea = rows("tea_lcom_sensitivity_data.csv")
    non_electric = float(tea[0]["non_electricity_cost_rmb_per_t"])
    fossil_price = float(tea[0]["fossil_methanol_price_rmb_per_t"])
    carbon_price = 100.0  # 讲义任务指定的假设值，非实时行情
    threshold = (fossil_price + carbon_price*avoided_t - non_electric)/electricity
    parity = (fossil_price-non_electric)/electricity
    print(f"非电成本={non_electric:.2f} 元/t; 无碳价平价电价={parity:.6f} 元/kWh")
    print(f"100 元/tCO2e 碳价下最高电价={threshold:.6f} 元/kWh")
    for row in tea:
        p = float(row["electricity_price_rmb_per_kwh"])
        lcom = electricity*p + non_electric
        premium = lcom-fossil_price
        mac = premium/avoided_t
        assert abs(lcom-float(row["lcom_rmb_per_t"])) < 0.011
        assert abs(mac-float(row["mac_rmb_per_tCO2e"])) < 0.02
        if p in (0.15, 0.35, 0.55):
            print(f"电价={p:.2f}: LCOM={lcom:.2f}; 溢价={premium:.2f}; "
                  f"绿电 MAC={mac:.2f} 元/tCO2e")

    prices = [0.05 + i*0.001 for i in range(551)]
    lcom_values = [electricity*p+non_electric for p in prices]
    premium_values = [v-fossil_price for v in lcom_values]
    mac_values = [v/avoided_t for v in premium_values]
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=prices, y=lcom_values, name="LCOM", line=dict(color="#146C94", width=3)), secondary_y=False)
    fig.add_trace(go.Scatter(x=prices, y=premium_values, name="绿色溢价", line=dict(color="#E28413", width=3)), secondary_y=False)
    fig.add_trace(go.Scatter(x=prices, y=mac_values, name="MAC（绿电）", line=dict(color="#568B3C", width=3)), secondary_y=True)
    fig.add_hline(y=carbon_price, line_dash="dot", line_color="#568B3C", secondary_y=True,
                  annotation_text="碳价假设 100 元/tCO₂e")
    fig.add_vline(x=threshold, line_dash="dash", line_color="#A23B72",
                  annotation_text=f"临界电价 {threshold:.4f} 元/kWh")
    fig.update_layout(title="电价对绿色甲醇 LCOM、溢价和 MAC 的影响（100% 绿电）",
                      width=1500, height=850, template="plotly_white",
                      font=dict(family="Microsoft YaHei, Noto Sans CJK SC, Arial", size=18),
                      legend=dict(orientation="h", y=1.08, x=0))
    fig.update_xaxes(title_text="电价（元/kWh）", range=[0.05, 0.60])
    fig.update_yaxes(title_text="LCOM / 绿色溢价（元/t 甲醇）", secondary_y=False)
    fig.update_yaxes(title_text="MAC（元/t CO₂e）", secondary_y=True)
    fig.write_image(HERE / "electricity_sensitivity.svg")
    fig.write_image(HERE / "electricity_sensitivity.png", scale=2)


if __name__ == "__main__":
    main()
