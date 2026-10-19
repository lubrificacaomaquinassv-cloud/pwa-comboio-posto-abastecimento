"""Monta SUPABASE_DB_URL a partir de secrets simples (Streamlit)."""
from __future__ import annotations

import os
import re
from urllib.parse import quote_plus


def _get_secret(key: str) -> str | None:
    try:
        import streamlit as st

        val = st.secrets.get(key)
        if val:
            return str(val).strip()
    except Exception:
        pass
    val = os.environ.get(key)
    return str(val).strip() if val else None


def resolver_db_url() -> str | None:
    """
    Aceita:
      1) SUPABASE_DB_URL (URI completa psycopg)
      2) SUPABASE_URL + SUPABASE_DB_PASSWORD (+ opcional SUPABASE_POOLER_HOST)
    """
    direta = _get_secret("SUPABASE_DB_URL")
    if direta:
        return direta

    base = _get_secret("SUPABASE_URL")
    senha = _get_secret("SUPABASE_DB_PASSWORD") or _get_secret("DATABASE_PASSWORD")
    if not base or not senha:
        return None

    m = re.search(r"https?://([^.]+)\.supabase\.co", base)
    if not m:
        return None
    ref = m.group(1)
    host = _get_secret("SUPABASE_POOLER_HOST") or "aws-1-sa-east-1.pooler.supabase.com"
    user = _get_secret("SUPABASE_DB_USER") or f"postgres.{ref}"
    senha_q = quote_plus(senha)
    return f"postgresql+psycopg://{user}:{senha_q}@{host}:6543/postgres"
