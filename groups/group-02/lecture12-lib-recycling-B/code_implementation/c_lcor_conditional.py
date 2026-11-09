# -*- coding: utf-8 -*-
"""成员 C 条件演示 LCOR（partial_lcor_conditional）接入层。

依据 `C发给B_LCOR接口包_20261103/README_先给B看.md`：
  - 仅用于「条件演示、纯湿法、LCE3000吨、只计锂盐回款、报价现金预算」的单独演示图；
  - 不覆盖正式 LCOR 字段（lcor_rmb_per_t），不标注政策可行，不与全路线帕累托混画；
  - 按 case_id + 五项情景参数逐条校验，禁止按文件行号拼接。
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd

_BASE = os.path.dirname(os.path.abspath(__file__))
_C_DIR = Path(_BASE).parent / "C发给B_LCOR接口包_20261103"
_MAP_FILE = _C_DIR / "C_to_B_conditional_by_B_case_id.json"

# 需与 C 逐条校验的五项情景参数（scale 一致后用 float 比较）
_VERIFY_KEYS = ("process_mix", "green_ratio", "grid_ef", "lithium_price_usd", "energy_efficiency")


def load_map() -> dict:
    """返回 {case_id(str): 条目}，用于按 case_id 精确关联（不依赖文件行号）。"""
    if not _MAP_FILE.exists():
        return {}
    data = json.loads(_MAP_FILE.read_text(encoding="utf-8"))
    return {str(e["case_id"]): e for e in data}


def _params_match(row, entry) -> bool:
    for k in _VERIFY_KEYS:
        try:
            if abs(float(row[k]) - float(entry[k])) > 1e-6:
                return False
        except (TypeError, ValueError, KeyError):
            return False
    return True


def join(df: pd.DataFrame) -> pd.DataFrame:
    """把条件部分 LCOR 按 case_id 并入 B 的 DataFrame（新增列，不覆盖既有列）。"""
    m = load_map()
    partial = []
    scope = []
    status = []
    for _, row in df.iterrows():
        e = m.get(str(int(row["case_id"])))
        if e and _params_match(row, e) and e.get("partial_lcor_conditional_CNY_t_LCE") is not None:
            partial.append(float(e["partial_lcor_conditional_CNY_t_LCE"]))
            scope.append(e.get("scope", ""))
            status.append(e.get("status", "UNKNOWN"))
        else:
            partial.append(None)
            scope.append("not_in_conditional_map_or_mismatch")
            status.append("UNKNOWN")
    out = df.copy()
    out["partial_lcor_conditional_CNY_t_LCE"] = partial
    out["c_conditional_lcor_scope"] = scope
    out["c_conditional_lcor_status"] = status
    return out


if __name__ == "__main__":
    csv_path = Path(_BASE).parent / "data_cohort" / "scenario_results.csv"
    df = pd.read_csv(csv_path, encoding="utf-8")
    df = join(df)
    sub = df[df["partial_lcor_conditional_CNY_t_LCE"].notna()]
    print(f"条件接入：总 {len(df)} 工况，条件部分 LCOR 非空 {len(sub)}（应=297 纯湿法）")
    if len(sub):
        lo, hi = sub["partial_lcor_conditional_CNY_t_LCE"].min(), sub["partial_lcor_conditional_CNY_t_LCE"].max()
        print(f"partial_lcor_conditional  [{lo:,.0f}, {hi:,.0f}] 元/t LCE")