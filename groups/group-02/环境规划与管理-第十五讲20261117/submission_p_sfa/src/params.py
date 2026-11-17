"""系数表读取。"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import config


def load_coefficients(path: Path | None = None) -> pd.DataFrame:
    path = path or (config.PARAMS_DIR / "coefficients.csv")
    df = pd.read_csv(path)
    df["symbol"] = df["symbol"].astype(str).str.strip()
    return df.set_index("symbol")


def coeff(df: pd.DataFrame, symbol: str) -> float:
    if symbol not in df.index:
        raise KeyError(f"系数表中缺少 {symbol}")
    return float(df.loc[symbol, "value"])
