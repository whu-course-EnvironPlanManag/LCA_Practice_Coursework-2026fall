"""容量约束的收集中心—梯次中心/精炼基地混合整数选址。

AI提示词：使用scipy.optimize.milp，以有出处的道路距离、容量、固定费用求解
多商品物流。不得用直线距离冒充道路距离，不把梯次入库当作当年再生供给。
自动测试：容量约束、不可行域与流量核查；尚待团队人工核定候选地适宜性。
"""
import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix
from common import InputError, number, source
from lca_tea import capital_recovery_factor


def solve_network(nodes, edges, supplies, radius_km=None, time_limit=30):
    lookup = {}
    for row in nodes:
        source(row, "network nodes")
        key = row["node_id"]
        if key in lookup:
            raise InputError("网络节点ID重复")
        if row["role"] not in {"origin", "collection", "echelon", "refining"}:
            raise InputError("网络节点role错误")
        if row["role"] != "origin" and str(row["eligible"]).lower() not in {"true", "false"}:
            raise InputError("候选地eligible须明确为true/false，未知不能当已审查通过")
        lookup[key] = row
    demand = {}
    for row in supplies:
        key = (row["node_id"], row["commodity"])
        if key in demand:
            raise InputError("城市/物流类别供给重复")
        if row["node_id"] not in lookup or lookup[row["node_id"]]["role"] != "origin":
            raise InputError("供给必须来自origin节点")
        if row["commodity"] not in {"recycling", "echelon"}:
            raise InputError("commodity须为recycling或echelon")
        demand[key] = number(row["supply_t"], "网络供给t", 0)
    if not demand or sum(demand.values()) <= 0:
        raise InputError("网络无正供给")
    candidates = [key for key in lookup if lookup[key]["role"] != "origin"]
    valid = []
    seen = set()
    for row in edges:
        source(row, "road distance")
        start, end, commodity = row["from_node"], row["to_node"], row["commodity"]
        if start not in lookup or end not in lookup:
            raise InputError("运输边引用不存在节点")
        pair = (lookup[start]["role"], lookup[end]["role"], commodity)
        if pair not in {("origin", "collection", "recycling"), ("origin", "collection", "echelon"),
                        ("collection", "refining", "recycling"), ("collection", "echelon", "echelon")}:
            raise InputError(f"不允许的网络边{pair}；梯次返厂量须来自dMFA独立延迟库存")
        key = (start, end, commodity)
        if key in seen:
            raise InputError("运输边重复")
        seen.add(key)
        distance = number(row["road_distance_km"], "道路距离", 0)
        if radius_km is None or distance <= radius_km:
            valid.append({**row, "distance": distance})
    ne, nn = len(valid), len(candidates)
    if not ne:
        return {"status": "Network_Infeasible", "reason": "运输半径内没有有效道路边"}
    n = ne+nn
    objective = np.zeros(n)
    for i, row in enumerate(valid):
        handling = number(lookup[row["to_node"]]["variable_handling_cny_t"], "节点单吨运行费", 0)
        objective[i] = row["distance"]*number(row["transport_cny_tkm"], "运输单价", 0)+handling
    upper = np.full(n, np.inf)
    for j, key in enumerate(candidates):
        node = lookup[key]
        objective[ne+j] = number(node["capex_cny"], "节点CAPEX", 0)*capital_recovery_factor(node["wacc"], node["life_years"])+number(node["fixed_opex_cny_y"], "节点固定OPEX", 0)
        upper[ne+j] = 1 if str(lookup[key]["eligible"]).lower() == "true" else 0
    matrix, lower, high = [], [], []
    # 每个起点、每个商品独立守恒。未提供供给的起点相应流量约束为0。
    for key, node in lookup.items():
        if node["role"] not in {"origin", "collection"}:
            continue
        for commodity in ("recycling", "echelon"):
            coefficients = {}
            for i, edge in enumerate(valid):
                if edge["commodity"] != commodity:
                    continue
                if edge["from_node"] == key:
                    coefficients[i] = coefficients.get(i, 0)+1
                if edge["to_node"] == key:
                    coefficients[i] = coefficients.get(i, 0)-1
            matrix.append(coefficients)
            q = demand.get((key, commodity), 0)
            lower.append(q)
            high.append(q)
    for j, key in enumerate(candidates):
        coefficients = {i: 1 for i, edge in enumerate(valid) if edge["to_node"] == key}
        coefficients[ne+j] = -number(lookup[key]["capacity_t_y"], "节点处理能力", 0)
        matrix.append(coefficients)
        lower.append(-np.inf)
        high.append(0)
    ri, ci, values = [], [], []
    for r, coefficients in enumerate(matrix):
        for c, v in coefficients.items():
            ri.append(r); ci.append(c); values.append(v)
    sparse = coo_matrix((values, (ri, ci)), shape=(len(matrix), n)).tocsc()
    result = milp(objective, integrality=np.r_[np.zeros(ne), np.ones(nn)],
                  bounds=Bounds(np.zeros(n), upper), constraints=LinearConstraint(sparse, lower, high),
                  options={"time_limit": time_limit, "mip_rel_gap": 0.0})
    if result.status != 0:
        return {"status": "Network_Infeasible" if result.status == 2 else "Network_Not_Proven_Optimal", "reason": result.message}
    flows = []
    for i, edge in enumerate(valid):
        if result.x[i] <= 1e-8:
            continue
        tonne_km = result.x[i]*edge["distance"]
        flows.append({"from_node": edge["from_node"], "to_node": edge["to_node"], "commodity": edge["commodity"],
                      "flow_t": float(result.x[i]), "road_distance_km": edge["distance"], "tonne_km": tonne_km,
                      "transport_gwp_kg": tonne_km*number(edge["transport_gwp_kg_tkm"], "运输碳因子", 0),
                      "transport_water_l": tonne_km*number(edge["transport_water_l_tkm"], "运输耗水因子", 0)})
    terminal = sum(row["flow_t"] for row in flows if lookup[row["to_node"]]["role"] in {"refining", "echelon"})
    if abs(terminal-sum(demand.values())) > max(1, terminal)*1e-7:
        raise ArithmeticError("网络流量守恒失败")
    opened = [key for j, key in enumerate(candidates) if result.x[ne+j] > 0.5]
    return {"status": "Optimal", "annual_cost_cny": float(result.fun),
            "capex_cny": sum(float(lookup[key]["capex_cny"]) for key in opened),
            "annual_capital_cny": sum(float(lookup[key]["capex_cny"])*capital_recovery_factor(lookup[key]["wacc"], lookup[key]["life_years"]) for key in opened),
            "opened_nodes": opened,
            "flows": flows, "transport_gwp_kg": sum(r["transport_gwp_kg"] for r in flows),
            "transport_water_l": sum(r["transport_water_l"] for r in flows),
            "total_supply_t": sum(demand.values()), "terminal_received_t": terminal}
