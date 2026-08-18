"""Normalização de código SAP (formato painel / importação SAP)."""
from __future__ import annotations


def normalizar_codigo_sap(valor: str) -> str:
    """
    Converte código para o formato usado no catálogo SAP campo.
    Códigos numéricos viram 5 dígitos com zero à esquerda (ex.: 2333 → 02333).
    """
    txt = str(valor).strip()
    if txt.endswith(".0") and txt[:-2].isdigit():
        txt = txt[:-2]
    if txt.isdigit():
        return txt.zfill(5)
    return txt
