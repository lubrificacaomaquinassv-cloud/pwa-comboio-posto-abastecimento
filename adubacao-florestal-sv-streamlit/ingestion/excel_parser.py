"""
Parsers das planilhas de adubacao (formato real usado na Santa Vergínia).

1) Adubacao de Cobertura: uma pasta de trabalho com 1 aba por retiro
   (ex: "C. Campo", "Água Branca", "Taquarussu", "Eucalipto", "Reserva",
   "Poço Azul"). Cada aba tem cabecalho na linha onde a coluna B == "Talhão",
   dados logo abaixo, e termina antes do bloco de resumo "Consumo total".

2) Adubacao de Base (arquivo com aba "Subsolagem"): DUAS tabelas lado a lado
   na mesma aba -> bloco esquerdo = ja subsolado/adubado na base, bloco
   direito = ainda a subsolar. As duas tem a mesma estrutura de colunas
   (Horto, Talhão, Área Plantada, Fertilizante, Dosagem/há, Total, Prestador).
"""
import pandas as pd

from ingestion.talhao_codigo import normalizar_coluna_talhao

COLS_COBERTURA = [
    "talhao", "area_total_ha", "area_floresta_ha", "fertilizante",
    "data", "dose_recomendada_ha", "dose_realizada_ha", "kg_total", "operador",
]

COLS_BASE_BLOCO = [
    "retiro", "talhao", "area_plantada_ha", "fertilizante",
    "dose_ha", "kg_total", "prestador",
]


def _norm_header(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    s = str(val).strip().lower()
    for a, b in (("ã", "a"), ("á", "a"), ("â", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ç", "c")):
        s = s.replace(a, b)
    return s


def _localizar_cabecalho_cobertura(raw: pd.DataFrame) -> tuple[int, int] | None:
    """Linha e coluna onde aparece 'Talhão' (qualquer coluna, não só B)."""
    for idx in raw.index:
        row = raw.loc[idx]
        for col_idx, val in enumerate(row):
            if _norm_header(val) == "talhao":
                return int(idx), int(col_idx)
    return None


def ler_adubacao_cobertura(caminho_xlsx: str) -> pd.DataFrame:
    """Le todas as abas do arquivo de Adubacao de Cobertura e retorna um DataFrame unico,
    com uma coluna 'retiro' preenchida a partir do nome da aba."""
    xls = pd.ExcelFile(caminho_xlsx)
    partes = []

    for aba in xls.sheet_names:
        raw = pd.read_excel(caminho_xlsx, sheet_name=aba, header=None)

        loc = _localizar_cabecalho_cobertura(raw)
        if loc is None:
            continue
        linha_header, col_start = loc
        inicio_dados = linha_header + 3  # pula 'Recomendação/Realizado' + linha em branco

        bloco = raw.iloc[inicio_dados:, col_start : col_start + 9].copy()
        bloco.columns = COLS_COBERTURA

        # corta no primeiro talhao vazio (fim da tabela, antes do resumo "Consumo total")
        fim = bloco["talhao"].isna().idxmax() if bloco["talhao"].isna().any() else None
        if fim is not None:
            bloco = bloco.loc[:fim].iloc[:-1] if pd.isna(bloco.loc[fim, "talhao"]) else bloco

        bloco = bloco[bloco["talhao"].notna()].copy()
        bloco["retiro"] = aba
        partes.append(bloco)

    df = pd.concat(partes, ignore_index=True)

    df = normalizar_coluna_talhao(df)
    df["fertilizante"] = df["fertilizante"].astype(str).str.strip()
    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    for col in ["area_total_ha", "area_floresta_ha", "dose_recomendada_ha", "dose_realizada_ha", "kg_total"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def ler_adubacao_base(caminho_xlsx: str, aba: str = "Subsolagem") -> pd.DataFrame:
    """Le a aba de Subsolagem/Adubacao de Base, que tem 2 blocos lado a lado
    (subsolado / a subsolar), e retorna um DataFrame unico empilhado com
    uma coluna 'status' indicando qual bloco a linha veio."""
    raw = pd.read_excel(caminho_xlsx, sheet_name=aba, header=None)

    linha_header = raw.index[raw[1] == "Horto"][0]
    inicio_dados = linha_header + 1

    bloco_feito = raw.iloc[inicio_dados:, 1:8].copy()
    bloco_feito.columns = COLS_BASE_BLOCO
    bloco_feito["status"] = "Subsolado/Adubado"

    bloco_pendente = raw.iloc[inicio_dados:, 9:16].copy()
    bloco_pendente.columns = COLS_BASE_BLOCO
    bloco_pendente["status"] = "A subsolar"

    df = pd.concat([bloco_feito, bloco_pendente], ignore_index=True)
    df = df[df["talhao"].notna()].copy()

    df = normalizar_coluna_talhao(df)
    df["retiro"] = df["retiro"].astype(str).str.strip()
    df["fertilizante"] = df["fertilizante"].astype(str).str.strip()
    for col in ["area_plantada_ha", "dose_ha", "kg_total"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


if __name__ == "__main__":
    import sys
    cob = ler_adubacao_cobertura(sys.argv[1])
    print("=== Cobertura ===")
    print(f"{len(cob)} registros | retiros: {cob['retiro'].unique().tolist()}")
    print(cob.head())

    base = ler_adubacao_base(sys.argv[2])
    print("\n=== Base / Subsolagem ===")
    print(f"{len(base)} registros | status: {base['status'].value_counts().to_dict()}")
    print(base.head())
