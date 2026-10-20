"""Normalização do código de talhão (KML ↔ planilhas ↔ Supabase)."""
from __future__ import annotations

import re

import pandas as pd

_RX_INTEIRO_FLOAT = re.compile(r"^(\d+)\.0+$")


def normalizar_codigo_talhao(val) -> str | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    s = str(val).strip().upper()
    if s in ("", "NAN", "NONE", "NAT"):
        return None
    m = _RX_INTEIRO_FLOAT.match(s)
    if m:
        s = m.group(1)
    return s


def normalizar_coluna_talhao(df: pd.DataFrame, col: str = "talhao") -> pd.DataFrame:
    if df is None or df.empty or col not in df.columns:
        return df
    out = df.copy()
    out[col] = out[col].map(normalizar_codigo_talhao)
    return out
