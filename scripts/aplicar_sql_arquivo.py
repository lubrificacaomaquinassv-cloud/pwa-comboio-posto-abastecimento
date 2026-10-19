#!/usr/bin/env python3
"""Executa um .sql no Supabase (usa SUPABASE_DB_URL)."""
from __future__ import annotations

import os
import sys


def _db_url() -> str:
    url = os.environ.get("SUPABASE_DB_URL", "")
    if not url:
        print("Defina SUPABASE_DB_URL", file=sys.stderr)
        sys.exit(1)
    return url.replace("postgresql+psycopg://", "postgresql://").replace(
        "postgresql+psycopg2://", "postgresql://"
    )


def main() -> None:
    if len(sys.argv) < 2:
        print("Uso: python scripts/aplicar_sql_arquivo.py sql/005_api_mapa_talhoes.sql", file=sys.stderr)
        sys.exit(1)
    path = sys.argv[1]
    sql = open(path, encoding="utf-8").read()

    import psycopg

    with psycopg.connect(_db_url(), autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
    print(f"OK: {path}")


if __name__ == "__main__":
    main()
