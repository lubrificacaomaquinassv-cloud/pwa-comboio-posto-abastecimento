#!/usr/bin/env python3
"""Carrega cadastro SAP (Excel) -> dim_catalogo_sap_campo.

Uso:
  python carregar_catalogo_sap.py --dry-run
  python carregar_catalogo_sap.py --aplicar
  python carregar_catalogo_sap.py --nutricao --aplicar
  python carregar_catalogo_sap.py --nutricao "c:\\...\\estoque_nutricao_animal_24_08_2026.xlsx" --aplicar
"""
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SQL_SCHEMA = ROOT / "sql" / "002_catalogo_sap_insumos.sql"
OUT_SQL = ROOT / "sql" / "003_seed_catalogo_sap_campo.sql"
SECRETS = ROOT.parent / "requisicao-compras" / ".streamlit" / "secrets.toml"

DEFAULT_MEDICAMENTOS = Path(r"c:\Users\hmauricio\Desktop\BAIXAS_SAP\cadastro_sap_medicamentos.xlsx")
DEFAULT_DEFENSIVOS = Path(r"c:\Users\hmauricio\Desktop\BAIXAS_SAP\cadastro_sap_defensivos.xlsx")
DEFAULT_NUTRICAO = Path(r"c:\Users\hmauricio\Desktop\BAIXAS_SAP\estoque_nutricao_animal_24_08_2026.xlsx")

# Aliases iniciais (campo/WhatsApp)
ALIASES_INICIAIS: list[tuple[str, str]] = [
    ("fordor", "02156"),
    ("crucial", "02405"),
    ("zapp", "02556"),
    ("agefix", "02023"),
    ("blitz", "02088"),
    ("engeo", "01995"),
    ("roundup", "01954"),
    ("glifos", "01954"),
]

COL_ALIASES = {
    "codigo": ["n do item", "no do item", "numero do item", "codigo", "item"],
    "descricao": ["descricao do item", "descricao", "nome"],
    "unidade": ["unidade de medida de estoque", "unidade", "um"],
}


def norm_col(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.lower().strip())


def achar_col(df: pd.DataFrame, grupo: str) -> str:
    cols_norm = {norm_col(c): c for c in df.columns}
    for alias in COL_ALIASES[grupo]:
        if alias in cols_norm:
            return cols_norm[alias]
    raise KeyError(f"Coluna '{grupo}' não encontrada em {list(df.columns)}")


def fmt_codigo(raw) -> str:
    s = re.sub(r"\D", "", str(raw).strip())
    return (s.lstrip("0") or "0").zfill(5)


def norm_unidade(u: str) -> str:
    u = str(u or "UN").strip().upper()
    if u in ("LT", "LTS", "LITRO", "LITROS"):
        return "LT"
    if u in ("L",):
        return "LT"
    return u


def resumida(desc: str) -> str:
    d = str(desc).strip()
    for prefix in (
        "ADUBO FERT ", "ADUBO ", "VACINA ", "OLEO LUBRIFICANTE ", "SERINGA DESC ",
        "AGULHA DESC. ", "AGULHA DESC ", "AGULHA ",
    ):
        if d.upper().startswith(prefix):
            d = d[len(prefix):]
            break
    words = re.split(r"\s+", d)
    stop = {"DE", "DO", "DA", "PARA", "COM", "EM", "P/", "PC", "SC", "FR", "ML", "LT", "LTS", "KG", "BB"}
    out = []
    for w in words:
        if w.upper() in stop and len(out) >= 1:
            break
        out.append(w)
        if len(out) >= 3:
            break
    return " ".join(out).title()[:100] if out else d[:60].title()


def esc(s: str) -> str:
    return str(s or "").replace("'", "''")


def ler_arquivo(path: Path, categoria: str, deposito: str) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(path)
    df = pd.read_excel(path)
    c_cod = achar_col(df, "codigo")
    c_desc = achar_col(df, "descricao")
    c_un = achar_col(df, "unidade")
    out = pd.DataFrame({
        "codigo_sap": df[c_cod].map(fmt_codigo),
        "descricao_sap": df[c_desc].astype(str).str.strip(),
        "unidade_estoque": df[c_un].map(norm_unidade),
        "categoria": categoria,
        "deposito_sap": deposito,
        "fonte_arquivo": path.name,
    })
    out["descricao_resumida"] = out["descricao_sap"].map(resumida)
    out = out.drop_duplicates(subset=["codigo_sap"], keep="first")
    return out


def gerar_sql(df: pd.DataFrame) -> str:
    hoje = date.today().isoformat()
    linhas = [
        f"-- Seed dim_catalogo_sap_campo — gerado em {hoje}",
        f"-- {len(df)} itens ({df['categoria'].value_counts().to_dict()})",
        "",
        "INSERT INTO public.dim_catalogo_sap_campo",
        "  (codigo_sap, descricao_sap, descricao_resumida, unidade_estoque, categoria, deposito_sap, fonte_arquivo, ativo)",
        "VALUES",
    ]
    vals = []
    for _, r in df.iterrows():
        vals.append(
            f"  ('{esc(r['codigo_sap'])}', '{esc(r['descricao_sap'])}', '{esc(r['descricao_resumida'])}', "
            f"'{esc(r['unidade_estoque'])}', '{esc(r['categoria'])}', '{esc(r['deposito_sap'])}', "
            f"'{esc(r['fonte_arquivo'])}', true)"
        )
    linhas.append(",\n".join(vals))
    linhas.append(
        "ON CONFLICT (codigo_sap) DO UPDATE SET\n"
        "  descricao_sap = EXCLUDED.descricao_sap,\n"
        "  descricao_resumida = EXCLUDED.descricao_resumida,\n"
        "  unidade_estoque = EXCLUDED.unidade_estoque,\n"
        "  categoria = EXCLUDED.categoria,\n"
        "  deposito_sap = EXCLUDED.deposito_sap,\n"
        "  fonte_arquivo = EXCLUDED.fonte_arquivo,\n"
        "  ativo = true,\n"
        "  updated_at = now();"
    )
    linhas.append("")
    linhas.append("-- Aliases iniciais")
    for alias, cod in ALIASES_INICIAIS:
        cod5 = fmt_codigo(cod)
        linhas.append(
            f"INSERT INTO public.dim_catalogo_sap_alias (alias, codigo_sap, observacao) "
            f"VALUES ('{esc(alias)}', '{cod5}', 'alias campo') "
            f"ON CONFLICT (alias) DO UPDATE SET codigo_sap = EXCLUDED.codigo_sap, ativo = true;"
        )
    return "\n".join(linhas) + "\n"


def carregar_supabase(df: pd.DataFrame) -> None:
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # type: ignore

    import psycopg2
    from psycopg2.extras import execute_batch

    if not SECRETS.is_file():
        raise FileNotFoundError(SECRETS)
    with open(SECRETS, "rb") as f:
        cfg = tomllib.load(f)["connections"]["supabase"]
    conn = psycopg2.connect(
        host=cfg["host"], port=cfg["port"], database=cfg["database"],
        user=cfg["username"], password=cfg["password"], sslmode="require",
    )
    conn.autocommit = True
    cur = conn.cursor()
    if SQL_SCHEMA.is_file():
        cur.execute(SQL_SCHEMA.read_text(encoding="utf-8"))

    upsert = """
        INSERT INTO public.dim_catalogo_sap_campo
          (codigo_sap, descricao_sap, descricao_resumida, unidade_estoque,
           categoria, deposito_sap, fonte_arquivo, ativo)
        VALUES (%s, %s, %s, %s, %s, %s, %s, true)
        ON CONFLICT (codigo_sap) DO UPDATE SET
          descricao_sap = EXCLUDED.descricao_sap,
          descricao_resumida = EXCLUDED.descricao_resumida,
          unidade_estoque = EXCLUDED.unidade_estoque,
          categoria = EXCLUDED.categoria,
          deposito_sap = EXCLUDED.deposito_sap,
          fonte_arquivo = EXCLUDED.fonte_arquivo,
          ativo = true,
          updated_at = now()
    """
    rows = [
        (r.codigo_sap, r.descricao_sap, r.descricao_resumida, r.unidade_estoque,
         r.categoria, r.deposito_sap, r.fonte_arquivo)
        for r in df.itertuples(index=False)
    ]
    execute_batch(cur, upsert, rows, page_size=100)

    alias_sql = """
        INSERT INTO public.dim_catalogo_sap_alias (alias, codigo_sap, observacao)
        VALUES (%s, %s, 'alias campo')
        ON CONFLICT (alias) DO UPDATE SET codigo_sap = EXCLUDED.codigo_sap, ativo = true
    """
    codigos = set(df["codigo_sap"])
    alias_rows = [(a, fmt_codigo(c)) for a, c in ALIASES_INICIAIS if fmt_codigo(c) in codigos]
    if alias_rows:
        execute_batch(cur, alias_sql, alias_rows)

    cur.close()
    conn.close()


def main():
    ap = argparse.ArgumentParser(description="Carrega catálogo SAP -> dim_catalogo_sap_campo")
    ap.add_argument("--defensivos", type=Path, default=DEFAULT_DEFENSIVOS)
    ap.add_argument("--medicamentos", type=Path, default=DEFAULT_MEDICAMENTOS)
    ap.add_argument(
        "--nutricao",
        nargs="?",
        const=str(DEFAULT_NUTRICAO),
        default=None,
        help="Carrega só nutrição (pode usar estoque_nutricao_animal_*.xlsx como cadastro)",
    )
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--gerar-sql", action="store_true")
    ap.add_argument("--aplicar", action="store_true", help="Upsert direto no Supabase")
    args = ap.parse_args()

    partes: list[pd.DataFrame] = []
    if args.nutricao is not None:
        path_nut = Path(args.nutricao)
        df_nut = ler_arquivo(path_nut, "Nutricao Animal", "FSV-PEC")
        print(f"Nutricao Animal (FSV-PEC): {len(df_nut)} itens <- {path_nut.name}")
        partes.append(df_nut)
    else:
        df_def = ler_arquivo(args.defensivos, "Defensivos", "FSV-MAN")
        df_med = ler_arquivo(args.medicamentos, "Medicamentos", "FSV-PEC")
        print(f"Defensivos (FSV-MAN): {len(df_def)} itens <- {args.defensivos.name}")
        print(f"Medicamentos (FSV-PEC): {len(df_med)} itens <- {args.medicamentos.name}")
        partes.extend([df_def, df_med])

    df = pd.concat(partes, ignore_index=True)
    print(f"Total: {len(df)} itens")
    print(df.groupby(["categoria", "unidade_estoque"]).size().to_string())
    print()
    print(df[["codigo_sap", "descricao_resumida", "unidade_estoque", "categoria"]].head(8).to_string(index=False))

    sql = gerar_sql(df)
    OUT_SQL.write_text(sql, encoding="utf-8")
    print(f"\nSQL gerado: {OUT_SQL}")

    if args.dry_run:
        return

    if args.gerar_sql:
        print("Use 002 + 003 no Supabase SQL Editor.")
        return

    if args.aplicar:
        carregar_supabase(df)
        print("OK — catálogo aplicado no Supabase.")
        return

    print("\nPróximo passo:")
    print("  1) Cole sql/002_catalogo_sap_insumos.sql no Supabase")
    print("  2) Cole sql/003_seed_catalogo_sap_campo.sql no Supabase")
    print("  ou: python carregar_catalogo_sap.py --aplicar")


if __name__ == "__main__":
    main()
