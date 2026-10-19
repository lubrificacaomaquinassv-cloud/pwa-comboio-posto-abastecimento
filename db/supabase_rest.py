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
    return data if isinstance(data, list) else []


def carregar_talhoes_geom_rest(client) -> tuple[gpd.GeoDataFrame | None, str | None]:
    for fonte, tabela in (
        ("API vw_dim_talhoes_geojson", "vw_dim_talhoes_geojson"),
        ("API dim_talhoes (sem geo)", "dim_talhoes"),
    ):
        try:
            resp = client.table(tabela).select("*").limit(8000).execute()
            rows = _records(resp)
            if not rows:
                continue
            if tabela == "vw_dim_talhoes_geojson" and "geojson" in rows[0]:
                return _gdf_from_geojson_rows(rows), fonte
        except Exception:
            continue
    return None, None


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
