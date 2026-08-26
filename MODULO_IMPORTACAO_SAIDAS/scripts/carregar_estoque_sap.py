#!/usr/bin/env python3
"""Carrega estoque SAP (Excel) -> estoque_sap_campo.

Uso:
  python carregar_estoque_sap.py
  python carregar_estoque_sap.py --aplicar
  python carregar_estoque_sap.py --gerar-sql
"""
from __future__ import annotations

import argparse
import re
import unicodedata
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT_SQL = ROOT / "sql" / "006_seed_estoque_sap_campo.sql"
SECRETS = ROOT.parent / "requisicao-compras" / ".streamlit" / "secrets.toml"

DEFAULT_PASTA = Path(r"c:\Users\hmauricio\Desktop\BAIXAS_SAP")
HISTORICO = "historico"


def _glob_estoque(pasta: Path, tipo: str) -> list[Path]:
    patterns = (
        f"estoque_{tipo}_*.xlsx",
        f"estoques_{tipo}_*.xlsx",
        f"estoque_{tipo}.xlsx",
        f"estoques_{tipo}.xlsx",
    )
    cands: list[Path] = []
    seen: set[str] = set()
    for pat in patterns:
        for p in pasta.glob(pat):
            key = str(p.resolve()).lower()
            if key not in seen:
                seen.add(key)
                cands.append(p)
    return cands


def achar_estoque(pasta: Path, tipo: str) -> Path | None:
    """Pega o Excel de estoque mais recente (estoque_* ou estoques_*), incluindo historico\\."""
    if not pasta.is_dir():
        return None
    aliases = {
        "nutricao_animal": ("nutricao_animal", "nutricao", "nutri"),
        "combustivel": ("combustivel",),
        "defensivos": ("defensivos", "defensivo"),
        "medicamentos": ("medicamentos", "medicamento"),
    }
    tipos = aliases.get(tipo, (tipo,))
    cands: list[Path] = []
    for t in tipos:
        cands.extend(_glob_estoque(pasta, t))
    hist = pasta / HISTORICO
    if hist.is_dir():
        for t in tipos:
            cands.extend(_glob_estoque(hist, t))
    if cands:
        # dedupe
        seen: set[str] = set()
        uniq = []
        for p in cands:
            k = str(p.resolve()).lower()
            if k not in seen:
                seen.add(k)
                uniq.append(p)
        return sorted(uniq, key=lambda p: p.stat().st_mtime, reverse=True)[0]
    return None

COL_ALIASES = {
    "codigo": ["n do item", "no do item", "codigo", "item"],
    "descricao": ["descricao do item", "descricao"],
    "qtd": ["em estoque", "estoque", "quantidade"],
    "unidade": ["unidade de medida de estoque", "unidade", "um"],
}


def norm_col(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.lower().strip())


def achar_col(df: pd.DataFrame, grupo: str) -> str:
    cols = {norm_col(c): c for c in df.columns}
    for alias in COL_ALIASES[grupo]:
        if alias in cols:
            return cols[alias]
    raise KeyError(f"Coluna {grupo} nao encontrada: {list(df.columns)}")


def fmt_codigo(raw) -> str:
    s = re.sub(r"\D", "", str(raw).strip())
    return (s.lstrip("0") or "0").zfill(5)


def norm_unidade(u: str) -> str:
    u = str(u or "UN").strip().upper()
    if u in ("LT", "LTS", "L", "LI", "LITRO", "LITROS"):
        return "LT"
    return u


def ler_estoque(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path)
    out = _ler_estoque_dataframe(df, path.name)
    return out.drop_duplicates(subset=["codigo_sap"], keep="first")


def ler_estoque_bytes(data: bytes, filename: str) -> pd.DataFrame:
    import io

    df = pd.read_excel(io.BytesIO(data))
    out = _ler_estoque_dataframe(df, filename)
    return out.drop_duplicates(subset=["codigo_sap"], keep="first")


def _ler_estoque_dataframe(df: pd.DataFrame, filename: str) -> pd.DataFrame:
    out = pd.DataFrame({
        "codigo_sap": df[achar_col(df, "codigo")].map(fmt_codigo),
        "descricao_sap": df[achar_col(df, "descricao")].astype(str).str.strip(),
        "em_estoque": pd.to_numeric(df[achar_col(df, "qtd")], errors="coerce").fillna(0),
        "unidade": df[achar_col(df, "unidade")].map(norm_unidade),
        "fonte": filename,
    })
    return out


def gerar_sql(df: pd.DataFrame) -> str:
    hoje = date.today().isoformat()
    linhas = [
        f"-- Estoque SAP campo — gerado em {hoje} ({len(df)} itens)",
        "",
        "INSERT INTO public.estoque_sap_campo (codigo_sap, em_estoque, unidade, atualizado_em)",
        "VALUES",
    ]
    vals = []
    for r in df.itertuples(index=False):
        desc = str(r.descricao_sap).replace("'", "''")
        vals.append(
            f"  ('{r.codigo_sap}', {float(r.em_estoque)}, '{r.unidade}', now())"
        )
    linhas.append(",\n".join(vals))
    linhas.append(
        "ON CONFLICT (codigo_sap) DO UPDATE SET\n"
        "  em_estoque = EXCLUDED.em_estoque,\n"
        "  unidade = EXCLUDED.unidade,\n"
        "  atualizado_em = now();"
    )
    return "\n".join(linhas) + "\n"


def load_db_cfg() -> dict:
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # type: ignore
    with open(SECRETS, "rb") as f:
        return tomllib.load(f)["connections"]["supabase"]


def carregar_codigos_catalogo(conn) -> set[str]:
    cur = conn.cursor()
    cur.execute("SELECT codigo_sap FROM dim_catalogo_sap_campo WHERE ativo")
    codes = {r[0] for r in cur.fetchall()}
    cur.close()
    return codes


def aplicar_supabase_conn(conn, df: pd.DataFrame) -> tuple[int, int]:
    """Upsert estoque usando conexão existente."""
    catalogo = carregar_codigos_catalogo(conn)
    df_ok = df[df["codigo_sap"].isin(catalogo)].copy()
    df_skip = df[~df["codigo_sap"].isin(catalogo)]

    cur = conn.cursor()
    sql = """
        INSERT INTO estoque_sap_campo (codigo_sap, em_estoque, unidade, atualizado_em)
        VALUES (%s, %s, %s, now())
        ON CONFLICT (codigo_sap) DO UPDATE SET
          em_estoque = EXCLUDED.em_estoque,
          unidade = EXCLUDED.unidade,
          atualizado_em = now()
    """
    ok = 0
    for r in df_ok.itertuples(index=False):
        cur.execute(sql, (r.codigo_sap, float(r.em_estoque), r.unidade))
        ok += 1
    conn.commit()
    cur.close()
    return ok, len(df_skip)


def aplicar_supabase(df: pd.DataFrame) -> tuple[int, int]:
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # type: ignore

    import psycopg2

    cfg = load_db_cfg()
    conn = psycopg2.connect(
        host=cfg["host"], port=cfg["port"], database=cfg["database"],
        user=cfg["username"], password=cfg["password"], sslmode="require",
    )
    catalogo = carregar_codigos_catalogo(conn)
    df_skip = df[~df["codigo_sap"].isin(catalogo)]
    ok, skip = aplicar_supabase_conn(conn, df)
    conn.close()

    if not df_skip.empty:
        print(f"\nIgnorados (sem cadastro no catalogo): {skip}")
        for r in df_skip.head(10).itertuples(index=False):
            print(f"  {r.codigo_sap} {str(r.descricao_sap)[:40]}")
        if len(df_skip) > 10:
            print(f"  ... +{len(df_skip) - 10} itens")
    return ok, skip


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pasta", type=Path, default=DEFAULT_PASTA)
    ap.add_argument("--defensivos", type=Path, default=None)
    ap.add_argument("--medicamentos", type=Path, default=None)
    ap.add_argument("--combustivel", type=Path, default=None)
    ap.add_argument("--nutricao", type=Path, default=None, help="estoque_nutricao_animal_*.xlsx")
    ap.add_argument("--aplicar", action="store_true")
    ap.add_argument("--gerar-sql", action="store_true")
    args = ap.parse_args()

    path_def = args.defensivos or achar_estoque(args.pasta, "defensivos")
    path_med = args.medicamentos or achar_estoque(args.pasta, "medicamentos")
    path_comb = args.combustivel or achar_estoque(args.pasta, "combustivel")
    path_nut = args.nutricao or achar_estoque(args.pasta, "nutricao_animal")

    partes: list[tuple[str, Path, pd.DataFrame]] = []
    for label, path in (
        ("Defensivos", path_def),
        ("Medicamentos", path_med),
        ("Combustivel", path_comb),
        ("Nutricao Animal", path_nut),
    ):
        if path is None:
            print(f"AVISO: nenhum estoque_{label.lower()}_*.xlsx em {args.pasta} — pulando.")
            continue
        partes.append((label, path, ler_estoque(path)))

    if not partes:
        print(f"ERRO: nenhum Excel de estoque em {args.pasta}")
        print("Esperado: estoque_medicamentos_DD_MM_YYYY.xlsx (ou estoques_medicamentos_...)")
        print("Export SAP = posicao de ESTOQUE (nao confundir com baixas_*.xlsx)")
        raise SystemExit(1)

    df = pd.concat([p[2] for p in partes], ignore_index=True)
    for label, path, parte in partes:
        print(f"{label}: {len(parte)} <- {path.name}")
    print(f"Total: {len(df)} itens | estoque total qty: {df.em_estoque.sum():,.1f}")

    sql = gerar_sql(df)
    OUT_SQL.write_text(sql, encoding="utf-8")
    print(f"SQL: {OUT_SQL}")

    crucial = df[df.codigo_sap == "02405"]
    if not crucial.empty:
        r = crucial.iloc[0]
        print(f"Crucial 02405 (galao): {r.em_estoque} {r.unidade}")

    if args.aplicar:
        ok, skip = aplicar_supabase(df)
        print(f"OK — {ok} itens aplicados no Supabase ({skip} ignorados).")
        print("Atualize o Lovable (F5): https://estoque-verde-ouro.lovable.app/")
    elif args.gerar_sql:
        print("Cole 006_seed_estoque_sap_campo.sql no Supabase.")
    else:
        print("Use --aplicar ou CARREGAR_ESTOQUE.bat (responda S).")


if __name__ == "__main__":
    main()
