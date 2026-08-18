"""Cliente Supabase compartilhado pelos scripts de importação."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECRETS_LOCAL = ROOT / ".streamlit" / "secrets.toml"


def load_secrets() -> dict:
    if SECRETS_LOCAL.is_file():
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # type: ignore
        with SECRETS_LOCAL.open("rb") as fh:
            return tomllib.load(fh)
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_KEY", "").strip()
    if url and key:
        return {"SUPABASE_URL": url, "SUPABASE_KEY": key}
    raise FileNotFoundError(
        "Configure .streamlit/secrets.toml (copie de secrets.toml.example) "
        "ou defina SUPABASE_URL e SUPABASE_KEY no ambiente."
    )


def get_client():
    from supabase import create_client

    cfg = load_secrets()
    url = str(cfg.get("SUPABASE_URL", "")).strip()
    key = str(cfg.get("SUPABASE_KEY", "")).strip()
    if not url or not key:
        raise ValueError("SUPABASE_URL e SUPABASE_KEY são obrigatórios.")
    return create_client(url, key)
