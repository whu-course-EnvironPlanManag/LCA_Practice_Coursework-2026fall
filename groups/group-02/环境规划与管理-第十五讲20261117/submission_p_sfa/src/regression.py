"""参数网格 + 均值中心化交互项回归。

样本由模型自身在政策参数空间上运行生成（不是论文结果表）：
  化肥减施比例 × 粪便堆肥利用率 × 污水鸟粪石回收率，
  另加拉丁超立方抽样补充连续取值。
因变量取 2050 年情景下的“总环境流失”与“农田 PUE”。
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.preprocessing import StandardScaler

from .system_model import PhosphorusSystemModel


def build_sample(bundle, coefficients, n_lhs: int = 200, seed: int = 42) -> pd.DataFrame:
    model = PhosphorusSystemModel(bundle, coefficients)
    scale = bundle.pop_2050 / bundle.population

    grid_reduce = np.round(np.arange(0.0, 0.401, 0.05), 3)
    grid_manure = np.round(np.arange(0.30, 0.901, 0.10), 3)
    grid_recover = np.round(np.arange(0.0, 0.801, 0.10), 3)

    combos = [(r, m, v) for r in grid_reduce for m in grid_manure for v in grid_recover]

    rng = np.random.default_rng(seed)
    lhs = rng.random((n_lhs, 3))
    lhs[:, 0] = lhs[:, 0] * 0.40
    lhs[:, 1] = 0.30 + lhs[:, 1] * 0.60
    lhs[:, 2] = lhs[:, 2] * 0.80
    combos += [tuple(row) for row in np.round(lhs, 4)]

    rows = []
    for red, man, rec in combos:
        ledger = model.build(fert_reduction=red, manure_rate=man,
                             struvite_rate=rec, demand_scale=scale)
        env_loss = sum(f.value for f in ledger.flows
                       if f.target in ("地表水", "废弃物与加工损失"))
        acs = model.acs.run()
        product = acs.harvest + bundle.animal_p * scale
        pue = product / (acs.fertilizer + acs.manure + acs.deposition + 1e-9)
        rock = sum(f.value for f in ledger.flows if f.target == "PMS 磷矿开采")
        rows.append({"化肥减施比例": red, "粪便堆肥利用率": man,
                     "鸟粪石回收率": rec, "总环境流失": env_loss,
                     "农田PUE": pue, "磷矿需求": rock})
    return pd.DataFrame(rows)


def fit_interaction(df: pd.DataFrame, target: str = "总环境流失") -> dict:
    """均值中心化 + 交互项 + Z-score 标准化 OLS。"""
    vars_ = ["化肥减施比例", "粪便堆肥利用率", "鸟粪石回收率"]
    x = df[vars_].astype(float)
    y = df[target].astype(float)

    xc = x - x.mean()
    xc.columns = [f"{v}_c" for v in vars_]
    pairs = [(0, 1), (0, 2), (1, 2)]
    for i, j in pairs:
        xc[f"交互_{vars_[i][:2]}x{vars_[j][:2]}"] = xc.iloc[:, i] * xc.iloc[:, j]

    scaler = StandardScaler()
    xs = pd.DataFrame(scaler.fit_transform(xc), columns=xc.columns, index=xc.index)
    ys = (y - y.mean()) / y.std(ddof=0)

    model = sm.OLS(ys, sm.add_constant(xs)).fit()
    resid_std = float(np.std(model.resid, ddof=1)) if len(df) > 8 else 0.0
    degenerate = resid_std < 1e-6     # 近似恒等线性，p 值不可用于判定交互
    out = {
        "target": target,
        "n": int(len(df)),
        "r2": float(model.rsquared),
        "r2_adj": float(model.rsquared_adj),
        "f_pvalue": float(model.f_pvalue),
        "resid_std": resid_std,
        "degenerate": bool(degenerate),
        "coef": {k: float(v) for k, v in model.params.items()},
        "pvalue": {k: float(v) for k, v in model.pvalues.items()},
    }

    # 方向感知的协同/拮抗判定
    direction = -1.0 if target == "总环境流失" else 1.0
    effects = {}
    for i, j in pairs:
        name = f"交互_{vars_[i][:2]}x{vars_[j][:2]}"
        beta = out["coef"][name]
        p = out["pvalue"][name]
        if degenerate:
            tag = "不可检验（拟合近似恒等）"
        elif p >= 0.05:
            tag = "无显著交互"
        elif beta * direction > 0:
            tag = "协同增强"
        else:
            tag = "拮抗削弱"
        effects[name] = {"beta": beta, "p": p, "type": tag}
    out["interactions"] = effects
    return out


def pairwise_table(df: pd.DataFrame, target: str = "总环境流失") -> pd.DataFrame:
    """逐对变量回归（参考 有交叉项.py 的组合遍历思路）。

    与参考脚本一致：先均值中心化再构造乘积项，最后对自变量与因变量
    同时做标准化，使交互系数可与主效应直接比较。
    对每一对变量，把剩余的第三个政策变量作为主效应控制项，
    避免遗漏变量造成的交互系数偏误（三因子设计下必须控制第三因子）。
    """
    vars_ = ["化肥减施比例", "粪便堆肥利用率", "鸟粪石回收率"]
    direction = -1.0 if target == "总环境流失" else 1.0
    rows = []
    for a in range(len(vars_)):
        for b in range(a + 1, len(vars_)):
            k = 3 - a - b
            sub = df[[vars_[a], vars_[b], vars_[k], target]].astype(float).copy()
            xa = sub[vars_[a]] - sub[vars_[a]].mean()
            xb = sub[vars_[b]] - sub[vars_[b]].mean()
            xk = sub[vars_[k]] - sub[vars_[k]].mean()
            inter = f"{vars_[a]}×{vars_[b]}"
            X = pd.DataFrame({
                "x1": xa / xa.std(ddof=0),
                "x2": xb / xb.std(ddof=0),
                "x3": xk / xk.std(ddof=0),
                "交互": (xa * xb) / (xa * xb).std(ddof=0),
            })
            y = sub[target]
            ys = (y - y.mean()) / y.std(ddof=0)
            m = sm.OLS(ys, sm.add_constant(X)).fit()
            beta = float(m.params["交互"])
            p = float(m.pvalues["交互"])
            resid_std = float(np.std(m.resid, ddof=1))
            if resid_std < 1e-6:
                tag = "不可检验（拟合近似恒等）"
            elif p >= 0.05:
                tag = "无显著交互"
            else:
                tag = "协同增强" if beta * direction > 0 else "拮抗削弱"
            rows.append({"变量组合": inter, "控制变量": vars_[k],
                         "交互项系数": beta, "p值": p,
                         "R²": float(m.rsquared), "R²_adj": float(m.rsquared_adj),
                         "残差标准差": resid_std, "交互类型": tag})
    return pd.DataFrame(rows)
