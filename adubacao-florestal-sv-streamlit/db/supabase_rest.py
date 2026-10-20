"""Leitura Supabase via PostgREST (SUPABASE_URL + SUPABASE_KEY) — sem postgres no Streamlit."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

import pandas as pd


def credenciais_rest() -> tuple[str, str] | None:
    """URL do projeto + chave (service_role recomendado para leitura de fatos)."""
    url = os.environ.get("SUPABASE_URL")
    key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_KEY")
    )
    try:
        import streamlit as st

        url = st.secrets.get("SUPABASE_URL") or url
        key = (
            st.secrets.get("SUPABASE_SERVICE_ROLE_KEY")
            or st.secrets.get("SUPABASE_KEY")
            or key
        )
    except Exception:
        pass
    if url and key:
        return url.rstrip("/"), key.strip()
    return None


def rest_disponivel() -> bool:
    return credenciais_rest() is not None


def _fetch_paginado(tabela: str, *, order: str = "id") -> list[dict[str, Any]]:
    creds = credenciais_rest()
    if not creds:
        return []
    base_url, key = creds
    rows: list[dict[str, Any]] = []
    offset = 0
    page = 1000
    while True:
        end = offset + page - 1
        req = urllib.request.Request(
            f"{base_url}/rest/v1/{tabela}?select=*&order={order}",
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Range": f"{offset}-{end}",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                chunk = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 416:
                break
            if e.code == 404:
                return []
            raise
        if not chunk:
            break
        rows.extend(chunk)
        if len(chunk) < page:
            break
        offset += page
    return rows


def _df_tabela(tabela: str, order: str) -> pd.DataFrame:
    data = _fetch_paginado(tabela, order=order)
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    drop = [c for c in ("id", "updated_at") if c in df.columns]
    return df.drop(columns=drop, errors="ignore")


def carregar_cobertura_rest() -> pd.DataFrame:
    from db.supabase_io import _padronizar_df_cobertura

    df = _df_tabela("fato_adubacao_cobertura", order="talhao,data")
    return _padronizar_df_cobertura(_renomear_npk(df))


def carregar_base_rest() -> pd.DataFrame:
    from ingestion.talhao_codigo import normalizar_coluna_talhao

    return normalizar_coluna_talhao(_df_tabela("fato_adubacao_base", order="talhao"))


def _renomear_npk(df: pd.DataFrame) -> pd.DataFrame:
    """Postgres grava n_kg; calculadora usa N_kg."""
    m = {"n_kg": "N_kg", "p2o5_kg": "P2O5_kg", "k2o_kg": "K2O_kg"}
    ren = {k: v for k, v in m.items() if k in df.columns and v not in df.columns}
    if ren:
        df = df.rename(columns=ren)
    return df
