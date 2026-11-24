"""2050 年 BAU 与课程 3R 情景。"""
from __future__ import annotations

import pandas as pd

from .params import coeff
from .system_model import SOURCE, SINK, PhosphorusSystemModel


def _metrics(model: PhosphorusSystemModel, ledger, label: str) -> dict:
    g = ledger.global_balance()
    sink_loss = sum(f.value for f in ledger.flows
                    if ledger.kind.get(f.target) == SINK)
    rock_demand = sum(f.value for f in ledger.flows
                      if f.target == "PMS 磷矿开采")
    # 直接环境流失：进入地表水与废弃物/加工损失，不含工业用磷
    env_loss = sum(f.value for f in ledger.flows
                   if f.target in ("地表水", "废弃物与加工损失"))
    stock = sum(ledger.stock_delta.values())
    acs = model.acs.run()
    fert = acs.fertilizer
    manure = acs.manure
    product = acs.harvest + model.b.animal_p * getattr(model, "_demand_scale", 1.0)
    ag_input = fert + manure + acs.deposition + acs.seed
    return {
        "情景": label,
        "化肥施用(Mt P)": fert,
        "粪肥还田(Mt P)": manure,
        "磷矿需求(Mt P)": rock_demand,
        "系统总输入(Mt P)": g["total_in"],
        "环境流失(Mt P)": env_loss,
        "全部汇流(Mt P)": sink_loss,
        "存量变化(Mt P)": stock,
        "农田PUE": product / (ag_input + 1e-9),
        "守恒相对误差": g["rel_err"],
    }


def run_scenarios(bundle, coefficients) -> tuple[pd.DataFrame, dict]:
    model = PhosphorusSystemModel(bundle, coefficients)
    scale = bundle.pop_2050 / bundle.population
    model._demand_scale = scale

    cases = {
        "2050 BAU": dict(demand_scale=scale),
        "2050 化肥减施20%": dict(demand_scale=scale,
                               fert_reduction=coeff(coefficients, "reduce_rate")),
        "2050 粪便堆肥利用率75%": dict(demand_scale=scale,
                                  manure_rate=coeff(coefficients, "manure_target")),
        "2050 污水鸟粪石回收60%": dict(demand_scale=scale,
                                  struvite_rate=coeff(coefficients, "recovery_target")),
        "2050 综合3R": dict(demand_scale=scale,
                          fert_reduction=coeff(coefficients, "reduce_rate"),
                          manure_rate=coeff(coefficients, "manure_target"),
                          struvite_rate=coeff(coefficients, "recovery_target")),
    }
    rows = []
    for label, kw in cases.items():
        ledger = model.build(**kw)
        rows.append(_metrics(model, ledger, label))
    df = pd.DataFrame(rows)

    # 相对 2050 BAU 的变化率
    bau = df.loc[df["情景"] == "2050 BAU"].iloc[0]
    for col in ["环境流失(Mt P)", "磷矿需求(Mt P)", "化肥施用(Mt P)"]:
        df[f"{col}相对BAU(%)"] = (df[col] / bau[col] - 1.0) * 100.0

    # 2022 基准
    model2022 = PhosphorusSystemModel(bundle, coefficients)
    model2022._demand_scale = 1.0
    base = _metrics(model2022, model2022.build(), "2022 基准")
    return df, base
