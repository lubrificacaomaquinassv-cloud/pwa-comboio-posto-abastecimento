"""Calculadora de nutrientes a partir da fórmula NPK do adubo."""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class FormulaNPK:
    n: float
    p2o5: float
    k2o: float
    rotulo: str


@dataclass(frozen=True)
class NutrientesAplicados:
    formula: FormulaNPK
    dosagem_kg_ha: float
    area_ha: float
    n_kg_ha: float
    p2o5_kg_ha: float
    k2o_kg_ha: float
    n_total_kg: float
    p2o5_total_kg: float
    k2o_total_kg: float
    adubo_total_kg: float


_FORMULA_RE = re.compile(
    r"(?P<n>\d{1,2})\s*[-–]\s*(?P<p>\d{1,2})\s*[-–]\s*(?P<k>\d{1,2})"
)


def parse_formula(texto: str) -> FormulaNPK:
    if not texto or not str(texto).strip():
        raise ValueError("Informe a fórmula ou nome do fertilizante com N-P-K.")

    raw = str(texto).strip()
    match = _FORMULA_RE.search(raw)
    if not match:
        raise ValueError(
            f"Não encontrei padrão N-P-K em '{raw}'. Ex.: 14-14-10 ou Sulfammo 10-05-18."
        )

    return FormulaNPK(
        n=float(match.group("n")),
        p2o5=float(match.group("p")),
        k2o=float(match.group("k")),
        rotulo=raw,
    )


def calcular_nutrientes(
    formula_texto: str,
    dosagem_kg_ha: float,
    area_ha: float,
) -> NutrientesAplicados:
    if dosagem_kg_ha < 0 or area_ha < 0:
        raise ValueError("Dosagem e área devem ser >= 0.")

    formula = parse_formula(formula_texto)
    n_kg_ha = dosagem_kg_ha * formula.n / 100.0
    p_kg_ha = dosagem_kg_ha * formula.p2o5 / 100.0
    k_kg_ha = dosagem_kg_ha * formula.k2o / 100.0

    return NutrientesAplicados(
        formula=formula,
        dosagem_kg_ha=dosagem_kg_ha,
        area_ha=area_ha,
        n_kg_ha=n_kg_ha,
        p2o5_kg_ha=p_kg_ha,
        k2o_kg_ha=k_kg_ha,
        n_total_kg=n_kg_ha * area_ha,
        p2o5_total_kg=p_kg_ha * area_ha,
        k2o_total_kg=k_kg_ha * area_ha,
        adubo_total_kg=dosagem_kg_ha * area_ha,
    )
