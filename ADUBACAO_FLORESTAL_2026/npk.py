"""Calculadora NPK — fórmula indica % de N, P₂O₅ e K₂O em peso."""
from __future__ import annotations

import re
from dataclasses import dataclass

_RE = re.compile(r"(?P<n>\d{1,2})\s*[-–]\s*(?P<p>\d{1,2})\s*[-–]\s*(?P<k>\d{1,2})")


@dataclass(frozen=True)
class ResultadoNPK:
    n_pct: float
    p_pct: float
    k_pct: float
    n_kg_ha: float
    p_kg_ha: float
    k_kg_ha: float
    n_total: float
    p_total: float
    k_total: float
    adubo_total: float


def calcular(formula: str, kg_ha: float, area_ha: float) -> ResultadoNPK:
    m = _RE.search(formula or "")
    if not m:
        raise ValueError("Use fórmula tipo 10-05-18 ou Sulfammo 10-05-18")
    n, p, k = float(m["n"]), float(m["p"]), float(m["k"])
    n_ha, p_ha, k_ha = kg_ha * n / 100, kg_ha * p / 100, kg_ha * k / 100
    return ResultadoNPK(n, p, k, n_ha, p_ha, k_ha, n_ha * area_ha, p_ha * area_ha, k_ha * area_ha, kg_ha * area_ha)
