#!/usr/bin/env python3
"""Aplica 021 + 022 no Supabase (movimento_baixa_sap + views almox)."""
from __future__ import annotations

import tomllib
from pathlib import Path

import psycopg2

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    ROOT / "sql" / "021_movimento_baixa_sap.sql",
    ROOT / "sql" / "022_views_painel_almox_contabil.sql",
]
SECRETS = ROOT.parent / "requisicao-compras" / ".streamlit" / "secrets.toml"


def run_sql(cur, path: Path) -> None:
    sql = path.read_text(encoding="utf-8")
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
                print("OK:", path.name, "—", stmt.replace("\n", " ")[:90])
            buf = []
    if buf:
        stmt = "\n".join(buf).strip().rstrip(";")
        if stmt:
            cur.execute(stmt)
            print("OK:", path.name, "—", stmt.replace("\n", " ")[:90])


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
    for f in FILES:
        if not f.is_file():
            print("Ausente:", f)
            continue
        print(f"\n=== {f.name} ===")
        run_sql(cur, f)

    for v in (
        "vw_almox_dashboard",
        "vw_almox_movimentacao_contabil",
        "vw_almox_estoque_atual",
        "vw_almox_integridade_geral",
    ):
        cur.execute(
            "SELECT 1 FROM information_schema.views WHERE table_schema='public' AND table_name=%s",
            (v,),
        )
        print(v, "OK" if cur.fetchone() else "FALTA")

    conn.close()
    print("\nConcluido. Proximo: CONCILIAR_BAIXA_SAP.bat --aplicar")


if __name__ == "__main__":
    main()
