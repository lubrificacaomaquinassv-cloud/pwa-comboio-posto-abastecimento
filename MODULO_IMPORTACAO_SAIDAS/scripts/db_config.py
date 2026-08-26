"""Conexão Postgres Supabase — múltiplas fontes de secrets."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_SECRETS_CANDIDATES = (
    ROOT / ".streamlit" / "secrets.toml",
    ROOT.parent / "requisicao-compras" / ".streamlit" / "secrets.toml",
    ROOT.parent / "painel-estrategico-sv" / ".streamlit" / "secrets.toml",
)


def _load_toml() -> dict:
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # type: ignore

    merged: dict = {}
    loaded_any = False
    for path in _SECRETS_CANDIDATES:
        if path.is_file():
            with open(path, "rb") as f:
                data = tomllib.load(f)
            loaded_any = True
            for key, val in data.items():
                if isinstance(val, dict) and isinstance(merged.get(key), dict):
                    merged[key] = {**merged[key], **val}
                else:
                    merged[key] = val
    if not loaded_any:
        raise FileNotFoundError(
            "Nenhum secrets.toml encontrado. "
            f"Copie [connections.supabase] de requisicao-compras para {ROOT / '.streamlit' / 'secrets.toml'}"
        )
    return merged


def load_db_cfg() -> dict:
    data = _load_toml()
    if "connections" in data and "supabase" in data["connections"]:
        return data["connections"]["supabase"]
    raise KeyError("[connections.supabase] ausente no secrets.toml")


def conectar_psycopg2():
    import psycopg2

    cfg = load_db_cfg()
    return psycopg2.connect(
        host=cfg["host"],
        port=cfg["port"],
        database=cfg["database"],
        user=cfg["username"],
        password=cfg["password"],
        sslmode="require",
    )
