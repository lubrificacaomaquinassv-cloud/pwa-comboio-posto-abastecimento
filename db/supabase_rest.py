"""Leitura Supabase via API (URL + chave) — igual aos outros painéis."""
from __future__ import annotations

import json
from typing import Any

import geopandas as gpd
import pandas as pd
from shapely.geometry import shape

from db.secrets_helper import _get_secret


def get_supabase_client():
    try:
        from supabase import create_client
    except ImportError:
        return None

    url = _get_secret("SUPABASE_URL")
    key = (
        _get_secret("SUPABASE_SERVICE_ROLE_KEY")
        or _get_secret("SUPABASE_KEY")
        or _get_secret("SUPABASE_ANON_KEY")
    )
    if not url or not key:
        return None
    return create_client(url, key)


def _records(response: Any) -> list[dict]:
    if response is None:
        return []
    data = getattr(response, "data", None)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    return []


def _gdf_from_geojson_rows(rows: list[dict]) -> gpd.GeoDataFrame:
    registros = []
    for row in rows:
        gj = row.get("geojson")
        if not gj:
            continue
        if isinstance(gj, str):
            gj = json.loads(gj)
        geom = shape(gj)
        registros.append(
            {
                "talhao": str(row.get("talhao", "")).strip().upper(),
                "classe": row.get("classe"),
                "retiro": row.get("retiro"),
                "area_ha_kml": row.get("area_ha_kml"),
                "geometry": geom,
            }
        )
    gdf = gpd.GeoDataFrame(registros, geometry="geometry", crs="EPSG:4326")
    return gdf[gdf["talhao"].notna() & (gdf["talhao"] != "")].copy()


def carregar_talhoes_geom_rest(client) -> tuple[gpd.GeoDataFrame | None, str | None, str | None]:
    """
    Retorna (gdf, fonte, erro).
    erro = mensagem se vazio (view não criada, RLS, etc.)
    """
    ultimo_erro: str | None = None

    # 1) RPC (melhor com RLS)
    try:
        resp = client.rpc("api_talhoes_geojson", {}).execute()
        payload = resp.data
        if isinstance(payload, list) and payload:
            gdf = _gdf_from_geojson_rows(payload)
            if len(gdf):
                return gdf, "API rpc api_talhoes_geojson", None
        if isinstance(payload, str):
            payload = json.loads(payload)
        if isinstance(payload, list) and payload:
            gdf = _gdf_from_geojson_rows(payload)
            if len(gdf):
                return gdf, "API rpc api_talhoes_geojson", None
    except Exception as exc:
        ultimo_erro = f"RPC api_talhoes_geojson: {exc}"

    # 2) View
    try:
        resp = client.table("vw_dim_talhoes_geojson").select("*").limit(8000).execute()
        rows = _records(resp)
        if rows:
            gdf = _gdf_from_geojson_rows(rows)
            if len(gdf):
                return gdf, "API vw_dim_talhoes_geojson", None
        ultimo_erro = "View vw_dim_talhoes_geojson retornou 0 linhas."
    except Exception as exc:
        ultimo_erro = f"View vw_dim_talhoes_geojson: {exc}"

    return None, None, ultimo_erro or "Geometria não disponível via API."


def carregar_cobertura_rest(client) -> pd.DataFrame:
    try:
        resp = client.table("fato_adubacao_cobertura").select("*").limit(50000).execute()
        df = pd.DataFrame(_records(resp))
        if "data" in df.columns:
            df["data"] = pd.to_datetime(df["data"], errors="coerce")
        return df
    except Exception:
        return pd.DataFrame()


def carregar_base_rest(client) -> pd.DataFrame:
    try:
        resp = client.table("fato_adubacao_base").select("*").limit(50000).execute()
        return pd.DataFrame(_records(resp))
    except Exception:
        return pd.DataFrame()
