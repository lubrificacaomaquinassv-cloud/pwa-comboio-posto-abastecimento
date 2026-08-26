"""Leitura de Excel de baixa SAP e importação para movimento_baixa_sap."""
from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import date
from pathlib import Path

import pandas as pd

DEFAULT_PASTA = Path(r"c:\Users\hmauricio\Desktop\BAIXAS_SAP")
HISTORICO = "historico"


def norm_col(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.lower().strip())


def fmt_codigo(raw) -> str:
    s = re.sub(r"\D", "", str(raw).strip())
    return (s.lstrip("0") or "0").zfill(5)


def infer_categoria(nome_arquivo: str) -> str | None:
    n = nome_arquivo.lower()
    if "medicamento" in n:
        return "Medicamentos"
    if "defensivo" in n:
        return "Defensivos"
    if "combustivel" in n or "combustível" in n:
        return "Combustivel"
    if "nutricao" in n or "nutri" in n or "tip" in n:
        return "Nutricao Animal"
    if "lubrific" in n or "lub" in n:
        return "Lubrificantes"
    return None


def infer_data_baixa(path: Path) -> date:
    m = re.search(r"(\d{2})[_-](\d{2})[_-](\d{4})", path.stem)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return date(y, mo, d)
        except ValueError:
            pass
    return date.fromtimestamp(path.stat().st_mtime)


def arquivo_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _pick_col(cols: dict[str, str], *patterns: str) -> str | None:
    for pat in patterns:
        for k, orig in cols.items():
            if pat in k:
                return orig
    return None


def ler_baixa_excel(path: Path) -> pd.DataFrame:
    """Lê baixa SAP com conta, destino e valor (colunas SAP export)."""
    return _ler_baixa_dataframe(pd.read_excel(path), path.name, path)


def ler_baixa_bytes(data: bytes, filename: str) -> pd.DataFrame:
    """Lê baixa SAP a partir de upload Streamlit (bytes + nome do arquivo)."""
    import io

    pseudo = Path(filename)
    df = _ler_baixa_dataframe(pd.read_excel(io.BytesIO(data)), filename, pseudo)
    df["arquivo_hash"] = arquivo_hash_bytes(data)
    return df


def _ler_baixa_dataframe(df: pd.DataFrame, filename: str, path: Path) -> pd.DataFrame:
    """Parse comum — path usado para data inferida."""
    cols = {norm_col(c): c for c in df.columns}
    c_cod = _pick_col(cols, "n do item", "no do item", "codigo")
    c_qtd = _pick_col(cols, "quant")
    c_desc = _pick_col(cols, "descri")
    c_total = _pick_col(cols, "total")
    c_custo = _pick_col(cols, "custo do item", "info pre")
    c_conta = _pick_col(cols, "codigo da conta", "conta")
    c_cc = _pick_col(cols, "centro de custo", "centro custo")
    c_dep = _pick_col(cols, "deposito", "depósito")

    if not c_cod or not c_qtd:
        raise KeyError(f"Colunas obrigatórias ausentes em {filename}: {list(df.columns)}")

    out = pd.DataFrame({
        "codigo_sap": df[c_cod].map(fmt_codigo),
        "descricao": df[c_desc].astype(str).str.strip() if c_desc else "",
        "quantidade": pd.to_numeric(df[c_qtd], errors="coerce"),
        "valor_total": pd.to_numeric(df[c_total], errors="coerce") if c_total else None,
        "valor_unitario": pd.to_numeric(df[c_custo], errors="coerce") if c_custo else None,
        "conta_contabil": df[c_conta].astype(str).str.strip() if c_conta else None,
        "centro_custo_sap": df[c_cc].astype(str).str.strip() if c_cc else None,
        "deposito_sap": df[c_dep].astype(str).str.strip() if c_dep else None,
        "linha_excel": df.index + 2,
    })
    out = out.dropna(subset=["quantidade"])
    out["fonte"] = filename
    out["categoria"] = infer_categoria(filename)
    out["data_baixa"] = infer_data_baixa(path)
    if path.is_file():
        out["arquivo_hash"] = arquivo_hash(path)
    return out


def arquivo_hash_bytes(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


def _dirs_baixas(pasta: Path, incluir_historico: bool) -> list[Path]:
    dirs = [pasta]
    hist = pasta / HISTORICO
    if incluir_historico and hist.is_dir():
        dirs.append(hist)
    return dirs


def _match_baixa_arquivo(nome: str, categorias: set[str] | None) -> bool:
    n = nome.lower()
    if n.startswith(("cadastro_", "estoque_", "estoques_")):
        return False
    if "baixa" not in n:
        return False
    cat = infer_categoria(nome)
    if categorias is None:
        return cat is not None or any(
            k in n for k in ("medicamento", "defensivo", "combustivel", "combustível", "nutricao", "nutri")
        )
    return cat in categorias if cat else False


def listar_excel_baixas(
    pasta: Path,
    incluir_historico: bool = True,
    categorias: set[str] | None = None,
) -> list[Path]:
    """Excel de baixa SAP por categoria (Medicamentos, Defensivos, Combustivel, …)."""
    out: list[Path] = []
    for d in _dirs_baixas(pasta, incluir_historico):
        if not d.is_dir():
            continue
        for f in d.iterdir():
            if not f.is_file() or f.suffix.lower() != ".xlsx":
                continue
            if _match_baixa_arquivo(f.name, categorias):
                out.append(f)
    return sorted(out, key=lambda p: p.stat().st_mtime, reverse=True)


def importar_movimentos(conn, df: pd.DataFrame, dry_run: bool = True) -> tuple[int, int]:
    """Upsert em movimento_baixa_sap. Retorna (inseridos, ignorados)."""
    if df.empty:
        return 0, 0
    cur = conn.cursor()
    sql = """
        INSERT INTO movimento_baixa_sap (
          codigo_sap, descricao, quantidade, valor_total, valor_unitario,
          conta_contabil, centro_custo_sap, deposito_sap, categoria,
          data_baixa, arquivo_fonte, arquivo_hash, linha_excel
        ) VALUES (
          %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (arquivo_hash, linha_excel) DO UPDATE SET
          quantidade = EXCLUDED.quantidade,
          valor_total = EXCLUDED.valor_total,
          valor_unitario = EXCLUDED.valor_unitario,
          conta_contabil = EXCLUDED.conta_contabil,
          centro_custo_sap = EXCLUDED.centro_custo_sap,
          deposito_sap = EXCLUDED.deposito_sap,
          categoria = EXCLUDED.categoria,
          data_baixa = EXCLUDED.data_baixa,
          arquivo_fonte = EXCLUDED.arquivo_fonte
    """
    ins, skip = 0, 0
    for r in df.itertuples(index=False):
        if dry_run:
            ins += 1
            continue
        try:
            cur.execute(
                sql,
                (
                    r.codigo_sap,
                    r.descricao or None,
                    float(r.quantidade),
                    float(r.valor_total) if pd.notna(r.valor_total) else None,
                    float(r.valor_unitario) if pd.notna(r.valor_unitario) else None,
                    r.conta_contabil if r.conta_contabil and r.conta_contabil != "nan" else None,
                    r.centro_custo_sap if r.centro_custo_sap and r.centro_custo_sap != "nan" else None,
                    r.deposito_sap if r.deposito_sap and r.deposito_sap != "nan" else None,
                    r.categoria,
                    r.data_baixa,
                    r.fonte,
                    r.arquivo_hash,
                    int(r.linha_excel),
                ),
            )
            ins += 1
        except Exception:
            skip += 1
    if not dry_run:
        conn.commit()
    cur.close()
    return ins, skip
