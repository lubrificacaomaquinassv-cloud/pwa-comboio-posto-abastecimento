"""Aplica arquivos SQL no Supabase."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from db_config import conectar_psycopg2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sql", nargs="?", default=str(ROOT / "sql" / "001_schema_saida_operacional.sql"))
    args = ap.parse_args()
    sql_path = Path(args.sql)
    if not sql_path.is_file():
        print(f"SQL não encontrado: {sql_path}")
        sys.exit(1)
    sql = sql_path.read_text(encoding="utf-8")
    conn = conectar_psycopg2()
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(sql)
    cur.close()
    conn.close()
    print(f"OK — {sql_path.name} aplicado no Supabase.")


if __name__ == "__main__":
    main()
