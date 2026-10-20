"""Leitura e normalização de SUPABASE_DB_URL (sem importar Streamlit app)."""
from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import quote_plus, unquote

ROOT = Path(__file__).resolve().parents[1]
SECRETS_PATH = ROOT / ".streamlit" / "secrets.toml"


def ler_supabase_db_url() -> str | None:
    env = os.environ.get("SUPABASE_DB_URL")
    if env and str(env).strip():
        return str(env).strip()
    if SECRETS_PATH.is_file():
        try:
            text = SECRETS_PATH.read_text(encoding="utf-8-sig")
            for pattern in (
                r'SUPABASE_DB_URL\s*=\s*"([^"]+)"',
                r"SUPABASE_DB_URL\s*=\s*'([^']+)'",
            ):
                m = re.search(pattern, text)
                if m and m.group(1).strip():
                    return m.group(1).strip()
        except OSError:
            pass
    return None


def normalizar_db_url(url: str) -> str | None:
    url = str(url).strip()
    if url.startswith("https://") or url.startswith("http://"):
        return None
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    if not url.startswith("postgresql+"):
        return None
    try:
        scheme, rest = url.split("://", 1)
        if "@" in rest:
            userinfo, hostpart = rest.rsplit("@", 1)
            if ":" in userinfo:
                user, pwd = userinfo.split(":", 1)
                user = quote_plus(unquote(user), safe=".")
                pwd = quote_plus(unquote(pwd), safe="")
                url = f"{scheme}://{user}:{pwd}@{hostpart}"
    except ValueError:
        pass
    return url


def create_supabase_engine():
    from sqlalchemy import create_engine

    raw = ler_supabase_db_url()
    if not raw:
        return None
    url = normalizar_db_url(raw)
    if not url:
        return None
    if not os.environ.get("SUPABASE_DB_URL"):
        os.environ["SUPABASE_DB_URL"] = url
    return create_engine(url)
