# -*- coding: utf-8 -*-
"""任务3（后半）：品类交叉敏感性回归（66 组合）。

算法与作者参考代码（有交叉项.py）一致：
1. 特征 = 两个品类的国家层面纯磷量 + 均值中心化交互项 Xi·Xj−mean(Xi·Xj)；
2. 目标 = 各国全部 12 品类（A-K,M，无 L）合计纯磷；
3. train/test 70/30 划分（random_state=42），StandardScaler 标准化后 OLS；
4. 交叉敏感性系数 = 交互项标准化系数（params[3]），
   p<0.05 且系数>0 → 协同，p<0.05 且系数<0 → 拮抗，否则 → 无显著交互。

数据切片：分别用 2022 年单年与 1961-2022 全期合计两种口径尝试，
以参考表基准（E+G 组合 CoefE=1.094、CoefG=1.890、R²=0.9993）判定匹配口径。
"""
import itertools
import warnings
import pandas as pd
import numpy as np
import statsmodels.api as sm
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

warnings.filterwarnings("ignore", message=".*rank-deficient.*")

import config as C
import data_load as D

CATS = list("ABCDEFGHIJKM")  # 12 品类（L 恒为 0，剔除后恰为 66 组合）
RANDOM_STATE = 42
TEST_SIZE = 0.3


def run_pair(x1, x2, y, name1, name2):
    """单组合回归：标准化系数 + 标准化交互系数（参考代码 StandardScaler+params[3] 口径）。"""
    inter = x1 * x2
    inter = inter - inter.mean()  # 均值中心化，消除共线性
    X = np.column_stack([x1, x2, inter])
    yv = y.values.reshape(-1, 1)
    Xtr, Xte, ytr, yte = train_test_split(X, yv, test_size=TEST_SIZE,
                                          random_state=RANDOM_STATE)
    sx, sy = StandardScaler(), StandardScaler()
    Xtr_s = sm.add_constant(sx.fit_transform(Xtr))
    ytr_s = sy.fit_transform(ytr)
    model = sm.OLS(ytr_s, Xtr_s).fit()
    coef = model.params[1:]
    pval = model.pvalues[3]
    Xte_s = sm.add_constant(sx.transform(Xte))
    pred = sy.inverse_transform(model.predict(Xte_s).reshape(-1, 1))
    ss_res = ((yte.ravel() - pred.ravel()) ** 2).sum()
    ss_tot = ((yte.ravel() - yte.mean()) ** 2).sum()
    r2_te = 1 - ss_res / ss_tot
    if pval < 0.05:
        itype = "Synergistic Enhancement" if coef[2] > 0 else "Antagonistic Attenuation"
    else:
        itype = "No Significant Interaction"
    return {
        "pair": f"{name1} + {name2}",
        "coef_1": coef[0], "coef_2": coef[1],
        "p_1": model.pvalues[1], "p_2": model.pvalues[2], "p_interaction": pval,
        "cross_sensitivity": coef[2],
        "R2_train": model.rsquared, "R2_test": r2_te,
        "interaction_type": itype,
    }


def cross_sensitivity(slice_name, matrix, total):
    rows = []
    for a, b in itertools.combinations(CATS, 2):
        rows.append(run_pair(matrix[a].values.astype(float), matrix[b].values.astype(float),
                             total, a, b))
    df = pd.DataFrame(rows)
    df["slice"] = slice_name
    return df


def match_reference(df, ref=("E", "G")):
    """按参考基准（CoefE≈1.094, CoefG≈1.890, R²≈0.9993）评估切片匹配度。"""
    key = f"{ref[0]} + {ref[1]}"
    r = df[df["pair"] == key].iloc[0]
    err = abs(r["coef_1"] - 1.094) + abs(r["coef_2"] - 1.890) + abs(r["R2_test"] - 0.9993)
    return err, r


def run():
    """两种切片各跑 66 组合，返回全部结果与更贴合参考基准的切片名。"""
    results = {}
    err = {}
    # 切片1：2022 单年
    m22 = D.category_matrix(2022)
    t22 = m22.sum(axis=1)
    results["2022"] = cross_sensitivity("2022", m22, t22)
    # 切片2：1961-2022 全期合计
    df = D.wide_product_table()
    years = [c for c in df.columns if isinstance(c, int)]
    df["sum"] = df[years].sum(axis=1)
    mtot = df.pivot_table(index="Country", columns="Product", values="sum", aggfunc="sum")
    mtot = mtot.reindex(columns=CATS).fillna(0.0)
    results["fullsum"] = cross_sensitivity("fullsum", mtot, mtot.sum(axis=1))
    for k, v in results.items():
        e, row = match_reference(v)
        err[k] = e
        print(f"[{k}] E+G 基准偏差和 = {e:.4f} | CoefE={row['coef_1']:.3f} "
              f"CoefG={row['coef_2']:.3f} R2_test={row['R2_test']:.4f}")
    best = min(err, key=err.get)
    return results, best


if __name__ == "__main__":
    results, best = run()
    print("最贴合参考基准的切片:", best)
    df = results[best]
    print(df.sort_values("R2_test", ascending=False).head(10).to_string(index=False))
