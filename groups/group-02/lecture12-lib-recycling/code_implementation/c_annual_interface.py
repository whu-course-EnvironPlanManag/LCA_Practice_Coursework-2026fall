# -*- coding: utf-8 -*-
"""成员 C 年度接口 v2 接入层（替换旧条件演示 LCOR 接入）。

依据 `给B_年度接口v2/README_先读.md`：
  - 读取 `给B_年度接口v2/C_to_B_existing_case_status_v2.json`，其中保留 B 原 3267 个
    case_id 与五项情景参数（process_mix/green_ratio/grid_ef/lithium_price_usd/
    energy_efficiency），按 case_id 逐条连接并同时校验五项参数；
  - 正式 LCOR 为空（null），不导入为 0、不进入正式可行前沿；
  - 未知结果一律列未就绪/缺项（NOT_READY_ANNUAL_V2 / UNKNOWN），不重启合成值或阈值填充。
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd

_BASE = os.path.dirname(os.path.abspath(__file__))
_C_DIR = Path(_BASE).parent / "data_cohort" / "给B_年度接口v2"
_MAP_FILE = _C_DIR / "C_to_B_existing_case_status_v2.json"

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
    """把 C 年度接口 v2 的逐工况状态按 case_id 并入 B 的 DataFrame（新增列，不覆盖既有列）。"""
    m = load_map()
    annual_case_id = []
    tea_status = []
    policy_status = []
    lcor = []
    formal = []
    reason = []
    for _, row in df.iterrows():
        e = m.get(str(int(row["case_id"])))
        if e and _params_match(row, e):
            annual_case_id.append(e.get("annual_case_id"))
            tea_status.append(e.get("c_tea_status", "UNKNOWN"))
            policy_status.append(e.get("c_policy_status", "UNKNOWN"))
            lcor.append(e.get("lcor_rmb_per_t_LCE"))          # 正式 LCOR，可能为 None
            formal.append(bool(e.get("formal_result_eligible", False)))
            reason.append(e.get("reason", ""))
        else:
            annual_case_id.append(None)
            tea_status.append("UNMAPPED")
            policy_status.append("UNKNOWN")
            lcor.append(None)
            formal.append(False)
            reason.append("not_in_annual_v2_map_or_mismatch")
    out = df.copy()
    out["annual_case_id"] = annual_case_id
    out["c_annual_tea_status"] = tea_status
    out["c_annual_policy_status"] = policy_status
    out["c_annual_lcor_rmb_per_t_LCE"] = lcor
    out["c_annual_formal_result_eligible"] = formal
    out["c_annual_reason"] = reason
    return out


if __name__ == "__main__":
    csv_path = Path(_BASE).parent / "data_cohort" / "scenario_results.csv"
    df = pd.read_csv(csv_path, encoding="utf-8")
    df = join(df)
    print(f"年度接口v2 接入：总 {len(df)} 工况")
    print(f"  c_annual_tea_status 分布：{df['c_annual_tea_status'].value_counts().to_dict()}")
    print(f"  c_annual_policy_status 分布：{df['c_annual_policy_status'].value_counts().to_dict()}")
    print(f"  c_annual_lcor_rmb_per_t_LCE 非空：{int(df['c_annual_lcor_rmb_per_t_LCE'].notna().sum())}")
    print(f"  c_annual_formal_result_eligible=True：{int(df['c_annual_formal_result_eligible'].sum())}")