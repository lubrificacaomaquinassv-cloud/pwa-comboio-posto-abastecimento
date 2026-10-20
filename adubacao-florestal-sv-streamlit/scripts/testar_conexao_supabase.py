"""Testa SUPABASE_DB_URL (secrets.toml ou env) sem abrir o painel."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import text

from db.supabase_url import create_supabase_engine, ler_supabase_db_url, normalizar_db_url


def main() -> int:
    raw = ler_supabase_db_url()
    if not raw:
        print("ERRO: SUPABASE_DB_URL nao encontrada (.streamlit/secrets.toml ou env).", file=sys.stderr)
        return 1
    norm = normalizar_db_url(raw)
    if not norm:
        print("ERRO: URL invalida (use postgresql+psycopg:// pooler).", file=sys.stderr)
        return 1
    if "postgres." not in norm.split("@")[0]:
        print("AVISO: usuario deveria ser postgres.SEU_REF (nao apenas postgres).", file=sys.stderr)
    engine = create_supabase_engine()
    if engine is None:
        print("ERRO: nao foi possivel criar engine.", file=sys.stderr)
        return 1
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        print(f"ERRO DE CONEXAO: {e}", file=sys.stderr)
        return 1
    print("CONEXAO OK — pode abrir o painel (PARAR_E_ABRIR_PAINEL.bat).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
