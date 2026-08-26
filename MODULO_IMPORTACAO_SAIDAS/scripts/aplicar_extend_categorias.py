#!/usr/bin/env python3
"""Aplica sql/010_extend_categorias.sql (Nutricao Animal + Combustivel no catálogo)."""
from __future__ import annotations

import tomllib
from pathlib import Path

import psycopg2

ROOT = Path(__file__).resolve().parents[1]
SQL_FILE = ROOT / "sql" / "010_extend_categorias.sql"
SECRETS = ROOT.parent / "requisicao-compras" / ".streamlit" / "secrets.toml"


def run_sql(cur, sql: str) -> None:
    buf: list[str] = []
    in_dollar = False
    for line in sql.splitlines():
        s = line.strip()
        if not in_dollar and (not s or s.startswith("--")):
            continue
        if "$$" in line:
            n = line.count("$$")
            if not in_dollar:
                in_dollar = True
                if n >= 2:
                    in_dollar = False
            else:
                in_dollar = False
        buf.append(line)
        if not in_dollar and ";" in line:
            stmt = "\n".join(buf).strip().rstrip(";")
            if stmt:
                cur.execute(stmt)
            buf = []
    if buf:
        stmt = "\n".join(buf).strip().rstrip(";")
        if stmt:
            cur.execute(stmt)


def main() -> None:
    cfg = tomllib.load(open(SECRETS, "rb"))["connections"]["supabase"]
    conn = psycopg2.connect(
        host=cfg["host"],
        port=cfg["port"],
        database=cfg["database"],
        user=cfg["username"],
        password=cfg["password"],
        sslmode="require",
    )
    conn.autocommit = True
    cur = conn.cursor()
    run_sql(cur, SQL_FILE.read_text(encoding="utf-8"))
    cur.execute(
        "SELECT conname FROM pg_constraint WHERE conname = 'dim_catalogo_sap_campo_categoria_check'"
    )
    print("OK — 010_extend_categorias aplicado (Nutricao Animal liberada no catalogo).")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
