"""Monta SUPABASE_DB_URL a partir de secrets simples (Streamlit)."""
from __future__ import annotations

import os
import re
from urllib.parse import quote_plus

POOLER_HOSTS_DEFAULT = (
    "aws-1-sa-east-1.pooler.supabase.com",
    "aws-0-sa-east-1.pooler.supabase.com",
)


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


def _build_url(ref: str, senha: str, host: str, user: str | None = None) -> str:
    u = user or f"postgres.{ref}"
    senha_q = quote_plus(senha)
    return f"postgresql+psycopg://{u}:{senha_q}@{host}:6543/postgres"


def listar_db_urls() -> list[str]:
    """Todas as URLs a tentar (URI direta + poolers)."""
    urls: list[str] = []
    direta = _get_secret("SUPABASE_DB_URL")
    if direta:
        urls.append(direta)

    base = _get_secret("SUPABASE_URL")
    senha = _get_secret("SUPABASE_DB_PASSWORD") or _get_secret("DATABASE_PASSWORD")
    if not base or not senha:
        return urls

    m = re.search(r"https?://([^.]+)\.supabase\.co", base)
    if not m:
        return urls
    ref = m.group(1)
    user = _get_secret("SUPABASE_DB_USER") or f"postgres.{ref}"

    host_custom = _get_secret("SUPABASE_POOLER_HOST")
    hosts = [host_custom] if host_custom else list(POOLER_HOSTS_DEFAULT)
    for host in hosts:
        if host:
            urls.append(_build_url(ref, senha, host, user))
    return urls


def resolver_db_url() -> str | None:
    candidatos = listar_db_urls()
    return candidatos[0] if candidatos else None
