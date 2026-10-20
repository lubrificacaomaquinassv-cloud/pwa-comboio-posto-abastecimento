"""Inventário e classificação de todos os .xlsx em DADOS_PAINEL."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from ingestion.excel_parser import ler_adubacao_base, ler_adubacao_cobertura


@dataclass
class PlanilhaInventario:
    caminho: Path
    nome: str
    tipo: str  # cobertura_sv | base_subsolagem_sv | vazio | erro | desconhecido
    abas: list[str] = field(default_factory=list)
    linhas_lidas: int = 0
    talhoes: int = 0
    detalhe: str = ""


def _detectar_tipo_bruto(caminho: Path) -> tuple[str, list[str], str]:
    xls = pd.ExcelFile(caminho)
    abas = list(xls.sheet_names)
    for aba in abas:
        try:
            raw = pd.read_excel(caminho, sheet_name=aba, header=None, nrows=40)
        except Exception as e:
            return "erro", abas, str(e)
        if raw.shape[1] < 2:
            continue
        col_b = raw[1].astype(str)
        if col_b.str.contains("Talhão", na=False).any():
            return "cobertura_sv", abas, f"aba '{aba}' formato Cobertura SV"
        if col_b.str.contains("Horto", na=False).any():
            return "base_subsolagem_sv", abas, f"aba '{aba}' formato Base/Subsolagem SV"
    return "desconhecido", abas, "nenhuma aba com cabeçalho Talhão ou Horto (coluna B)"


def inventariar_pasta(pasta: str | Path) -> list[PlanilhaInventario]:
    root = Path(pasta).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Pasta não encontrada: {root}")

    itens: list[PlanilhaInventario] = []
    xlsx_files = sorted(root.glob("*.xlsx"), key=lambda p: p.name.lower())

    for path in xlsx_files:
        tipo, abas, det = _detectar_tipo_bruto(path)
        inv = PlanilhaInventario(caminho=path, nome=path.name, tipo=tipo, abas=abas, detalhe=det)
        try:
            if tipo == "cobertura_sv":
                df = ler_adubacao_cobertura(str(path))
                inv.linhas_lidas = len(df)
                inv.talhoes = int(df["talhao"].nunique()) if len(df) else 0
                if inv.linhas_lidas == 0:
                    inv.tipo = "vazio"
                    inv.detalhe = "formato reconhecido mas 0 linhas de dados"
            elif tipo == "base_subsolagem_sv":
                df = ler_adubacao_base(str(path))
                inv.linhas_lidas = len(df)
                inv.talhoes = int(df["talhao"].nunique()) if len(df) else 0
                if inv.linhas_lidas == 0:
                    inv.tipo = "vazio"
        except Exception as e:
            inv.tipo = "erro"
            inv.detalhe = str(e)
        itens.append(inv)
    return itens


def resumo_inventario(itens: list[PlanilhaInventario]) -> dict:
    cob = [i for i in itens if i.tipo == "cobertura_sv"]
    base = [i for i in itens if i.tipo == "base_subsolagem_sv"]
    return {
        "total_xlsx": len(itens),
        "cobertura": [{"arquivo": i.nome, "linhas": i.linhas_lidas, "talhoes": i.talhoes} for i in cob],
        "base_subsolagem": [{"arquivo": i.nome, "linhas": i.linhas_lidas, "talhoes": i.talhoes} for i in base],
        "ignorados": [{"arquivo": i.nome, "tipo": i.tipo, "detalhe": i.detalhe} for i in itens if i.tipo not in (
            "cobertura_sv",
            "base_subsolagem_sv",
        )],
    }


def carregar_todas_coberturas(itens: list[PlanilhaInventario]) -> pd.DataFrame:
    import pandas as pd

    partes = []
    for inv in itens:
        if inv.tipo != "cobertura_sv" or inv.linhas_lidas == 0:
            continue
        df = ler_adubacao_cobertura(str(inv.caminho))
        df["arquivo_origem_planilha"] = inv.nome
        partes.append(df)
    if not partes:
        return pd.DataFrame()
    return pd.concat(partes, ignore_index=True)


def carregar_todas_bases(itens: list[PlanilhaInventario]) -> pd.DataFrame:
    import pandas as pd

    partes = []
    for inv in itens:
        if inv.tipo != "base_subsolagem_sv" or inv.linhas_lidas == 0:
            continue
        df = ler_adubacao_base(str(inv.caminho))
        df["arquivo_origem_planilha"] = inv.nome
        partes.append(df)
    if not partes:
        return pd.DataFrame()
    return pd.concat(partes, ignore_index=True)
