"""Localização automática dos arquivos da pasta DADOS_PAINEL (KML + planilhas)."""
from __future__ import annotations

import os
import re
from pathlib import Path


def descobrir_arquivos_dados_painel(pasta: str | os.PathLike) -> dict[str, Path | None]:
    """
    Encontra KML, cobertura e base na pasta (mesma lógica do CARGA_DADOS_PAINEL.ps1).

    Retorna chaves: kml, cobertura, base (base pode ser None).
    Levanta FileNotFoundError se a pasta, KML ou cobertura não existirem.
    """
    root = Path(pasta).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Pasta de dados não encontrada: {root}")

    kmls = sorted(root.glob("*.kml"), key=lambda p: p.stat().st_size, reverse=True)
    if not kmls:
        raise FileNotFoundError(f"Nenhum .kml em {root}")
    kml = kmls[0]

    xlsx = list(root.glob("*.xlsx"))
    cobertura = _primeiro_match(xlsx, r"cobertura", case_insensitive=True)
    if cobertura is None:
        xlsx_sorted = sorted(xlsx, key=lambda p: p.stat().st_mtime, reverse=True)
        if not xlsx_sorted:
            raise FileNotFoundError(f"Nenhum .xlsx (cobertura) em {root}")
        cobertura = xlsx_sorted[0]

    base = _primeiro_match(xlsx, r"base|subsol", case_insensitive=True)

    return {"kml": kml, "cobertura": cobertura, "base": base}


def _primeiro_match(files: list[Path], pattern: str, *, case_insensitive: bool) -> Path | None:
    flags = re.IGNORECASE if case_insensitive else 0
    rx = re.compile(pattern, flags)
    for p in files:
        if rx.search(p.name):
            return p
    return None
