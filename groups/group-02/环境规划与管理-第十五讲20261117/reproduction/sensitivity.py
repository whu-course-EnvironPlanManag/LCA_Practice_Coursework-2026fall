# -*- coding: utf-8 -*-
"""2050 年 3R 政策情景的交叉敏感性回归。"""

import itertools

import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.preprocessing import StandardScaler

from mfa_model import GlobalPModel
from scenario_2050 import (DEFAULT_RECYCLE, DEFAULT_REDUCE, DEFAULT_REPLACE,
                           prepare_bau, run_policy_scenario)

POLICY_VARIABLES = ["Reduce", "Replace", "Recycle"]
INTERACTIONS = [("Reduce", "Replace"), ("Reduce", "Recycle"), ("Replace", "Recycle")]
TARGET = "total_p_reduction"


def build_policy_dataset(model: GlobalPModel, grid_size=5):
    """生成确定性 3R 规则网格，包含 BAU、单措施和默认 3R 点。"""
    if grid_size < 2:
        raise ValueError("grid_size 至少为 2")
    grids = {
        "Reduce": np.linspace(0.0, DEFAULT_REDUCE, grid_size),
        "Replace": np.linspace(0.0, DEFAULT_REPLACE, grid_size),
        "Recycle": np.linspace(0.0, DEFAULT_RECYCLE, grid_size),
    }
    bau = prepare_bau(model)
    rows = []
    for reduce_rate, replace_rate, recycle_rate in itertools.product(
            grids["Reduce"], grids["Replace"], grids["Recycle"]):
        rows.append(run_policy_scenario(
            model, reduce_rate=reduce_rate, manure_utilization=replace_rate,
            struvite_recovery=recycle_rate, bau=bau))
    data = pd.DataFrame(rows)
    expected = len(data)
    if data[POLICY_VARIABLES].drop_duplicates().shape[0] != expected:
        raise AssertionError("3R 参数网格存在重复组合")
    if not np.isfinite(data[POLICY_VARIABLES + [TARGET]].to_numpy()).all():
        raise AssertionError("3R 情景样本存在非有限值")
    return data


def run_policy_regression(data):
    """均值中心化构造交互项，再标准化并拟合完整多元 OLS。"""
    modeled = data.copy()
    for variable in POLICY_VARIABLES:
        modeled[f"{variable}_c"] = modeled[variable] - modeled[variable].mean()
    interaction_names = []
    for var1, var2 in INTERACTIONS:
        name = f"{var1}×{var2}"
        modeled[name] = modeled[f"{var1}_c"] * modeled[f"{var2}_c"]
        interaction_names.append(name)

    features = POLICY_VARIABLES + interaction_names
    scaler_x = StandardScaler()
    scaler_y = StandardScaler()
    x_std = scaler_x.fit_transform(modeled[features])
    y_std = scaler_y.fit_transform(modeled[[TARGET]]).ravel()
    x_const = sm.add_constant(x_std, has_constant="add")
    fitted = sm.OLS(y_std, x_const).fit()
    confidence = fitted.conf_int(alpha=0.05)

    rows = []
    for index, variable in enumerate(["const"] + features):
        p_value = float(fitted.pvalues[index])
        coefficient = float(fitted.params[index])
        if variable in interaction_names:
            if p_value < 0.05:
                effect = "协同增强" if coefficient > 0 else "拮抗削弱"
            else:
                effect = "无显著交互"
        else:
            effect = "—"
        rows.append({
            "变量": variable, "标准化系数": coefficient,
            "标准误": float(fitted.bse[index]), "t值": float(fitted.tvalues[index]),
            "p值": p_value, "95%CI下限": float(confidence[index][0]),
            "95%CI上限": float(confidence[index][1]),
            "显著_p<0.05": p_value < 0.05, "交互效应类型": effect,
        })
    coefficients = pd.DataFrame(rows)
    summary = pd.DataFrame([
        ("样本量", int(fitted.nobs)), ("R²", float(fitted.rsquared)),
        ("调整R²", float(fitted.rsquared_adj)),
        ("RMSE_标准化", float(np.sqrt(np.mean(fitted.resid ** 2)))),
        ("F检验p值", float(fitted.f_pvalue)),
        ("因变量", TARGET), ("中心化", "主变量均值中心化后构造交互项"),
        ("标准化", "自变量与因变量 Z-score；全样本推断，无训练/测试划分"),
    ], columns=["统计项", "值"])
    return coefficients, summary


def key_interaction_result(coefficients, summary):
    """单独提取 S2.2×S4.3 的代理交互 Reduce×Replace。"""
    row = coefficients.loc[coefficients["变量"] == "Reduce×Replace"].iloc[0]
    r2 = float(summary.loc[summary["统计项"] == "R²", "值"].iloc[0])
    return pd.DataFrame([{
        "论文情景代理": "S2.2 节肥 × S4.3 粪污还田",
        "回归交互项": "Reduce×Replace", "因变量": "2050 BAU环境损失−情景环境损失 (Mt P)",
        "标准化交互系数": row["标准化系数"], "p值": row["p值"],
        "交互效应类型": row["交互效应类型"], "全模型R²": r2,
        "解释边界": "确定性简化情景的模型响应分析，不是观测数据上的因果证明",
    }])


if __name__ == "__main__":
    model = GlobalPModel()
    model.build_2022_flows()
    dataset = build_policy_dataset(model)
    coefficients, summary = run_policy_regression(dataset)
    print(f"政策情景样本：{dataset.shape}")
    print(coefficients.to_string(index=False))
    print(summary.to_string(index=False))
    print(key_interaction_result(coefficients, summary).to_string(index=False))
