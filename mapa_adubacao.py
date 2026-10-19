"""Mapa GIS estilo painel SV: Esri, pintar por métrica, clique no talhão."""
from __future__ import annotations

import html
import json
from typing import Literal

import folium
import numpy as np
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

Camada = Literal["Satélite", "Terreno"]
PintarPor = Literal["Cobertura", "Hectares", "Valor"]

TILES_SATELITE = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    "Esri",
)
TILES_TERRENO = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
    "Esri",
)

COR_NAO_INICIADO = "#5a5a5a"
COR_PARCIAL = "#f9a825"
COR_COMPLETO = "#2e7d32"
COR_SEM_DADO = "#3d4a5c"


def _fmt_num(val, casas: int = 2) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "—"
    try:
        return f"{float(val):,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return str(val)


def _fmt_data(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "—"
    if hasattr(val, "strftime"):
        return val.strftime("%d/%m/%Y")
    return str(val)


def html_ficha_lateral(ficha: dict | None) -> str:
    if not ficha:
        return """
        <div class="sv-map-panel sv-ficha">
            <div class="sv-map-panel-title">TALHÃO</div>
            <p class="sv-ficha-hint">Clique em um polígono no mapa para ver os dados de adubação.</p>
        </div>
        """
    t = html.escape(str(ficha.get("talhao", "")))
    return f"""
    <div class="sv-map-panel sv-ficha">
        <div class="sv-map-panel-title">TALHÃO {t}</div>
        <div class="sv-ficha-grid">
            <span class="lbl">Nº talhão</span><span class="val">{t}</span>
            <span class="lbl">Total (há)</span><span class="val">{_fmt_num(ficha.get('area_total_ha'))}</span>
            <span class="lbl">Floresta (há)</span><span class="val">{_fmt_num(ficha.get('area_floresta_ha'))}</span>
            <span class="lbl">Fertilizante</span><span class="val">{html.escape(str(ficha.get('fertilizante') or '—'))}</span>
            <span class="lbl">Data</span><span class="val">{_fmt_data(ficha.get('data'))}</span>
            <span class="lbl">Previsto (kg/há)</span><span class="val">{_fmt_num(ficha.get('previsto_ha'), 0)}</span>
            <span class="lbl">Realizado (kg/há)</span><span class="val">{_fmt_num(ficha.get('realizado_ha'))}</span>
            <span class="lbl">Total gasto (kg)</span><span class="val">{_fmt_num(ficha.get('kg_total'), 0)}</span>
            <span class="lbl">Operador</span><span class="val">{html.escape(str(ficha.get('operador') or '—'))}</span>
        </div>
        <p class="sv-ficha-foot">Realizado = Total gasto ÷ Floresta (há)</p>
    </div>
    """


def css_mapa_panels() -> str:
    return """
    <style>
    .sv-map-wrap { position: relative; }
    .sv-map-panel {
        background: rgba(22, 28, 38, 0.92);
        border: 1px solid rgba(255,255,255,0.12);
        border-radius: 12px;
        padding: 14px 16px;
        color: #e8ecf1;
        font-size: 13px;
        margin-bottom: 10px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.35);
    }
    .sv-map-panel-title {
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.08em;
        color: #8b949e;
        margin-bottom: 10px;
    }
    .sv-ficha-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 6px 12px;
    }
    .sv-ficha-grid .lbl { color: #9aa4b2; font-size: 12px; }
    .sv-ficha-grid .val { color: #f0f3f6; font-weight: 600; text-align: right; }
    .sv-ficha-hint { color: #9aa4b2; margin: 0; font-size: 12px; line-height: 1.4; }
    .sv-ficha-foot { color: #6e7681; font-size: 11px; margin: 10px 0 0 0; }
    div[data-testid="stVerticalBlock"] > div:has(.sv-map-controls-anchor) {
        margin-top: -8px;
    }
    </style>
    """


def _cor_cobertura(row: pd.Series) -> str:
    kg = row.get("kg_total_map")
    pct = row.get("pct_cobertura")
    if pd.isna(kg) or kg == 0:
        return COR_NAO_INICIADO
    if pd.notna(pct) and pct >= 95:
        return COR_COMPLETO
    if pd.notna(pct) and pct > 0:
        return COR_PARCIAL
    real = row.get("realizado_ha")
    prev = row.get("dose_recomendada_ha")
    if pd.notna(real) and pd.notna(prev) and prev > 0:
        ratio = real / prev
        if ratio >= 0.95:
            return COR_COMPLETO
        if ratio > 0:
            return COR_PARCIAL
    return COR_PARCIAL if kg and kg > 0 else COR_NAO_INICIADO


def _cor_escala(valores: pd.Series, paleta: list[str]) -> pd.Series:
    s = pd.to_numeric(valores, errors="coerce").fillna(0)
    if s.max() == s.min():
        return pd.Series([paleta[0]] * len(s), index=s.index)
    q = (s - s.min()) / (s.max() - s.min())
    idx = (q * (len(paleta) - 1)).round().astype(int).clip(0, len(paleta) - 1)
    return idx.map(lambda i: paleta[i])


def _montar_cores(gdf: pd.DataFrame, pintar: PintarPor) -> pd.Series:
    if pintar == "Cobertura":
        return gdf.apply(_cor_cobertura, axis=1)
    if pintar == "Hectares":
        paleta = ["#1a237e", "#3949ab", "#5c6bc0", "#7986cb", "#9fa8da", "#c5cae9"]
        return _cor_escala(gdf["area_floresta_map"].fillna(gdf["area_ha_kml"]), paleta)
    paleta = ["#4a148c", "#6a1b9a", "#8e24aa", "#ab47bc", "#ce93d8", "#f3e5f5"]
    return _cor_escala(gdf["kg_total_map"], paleta)


@st.cache_resource(show_spinner="Montando camadas do mapa…")
def _folium_mapa(
    geojson_str: str,
    centro_lat: float,
    centro_lon: float,
    camada: Camada,
    rotulos_json: str | None,
):
    tiles = TILES_TERRENO if camada == "Terreno" else TILES_SATELITE
    mapa = folium.Map(
        location=[centro_lat, centro_lon],
        zoom_start=12,
        tiles=tiles[0],
        attr=tiles[1],
        control_scale=False,
    )

    folium.GeoJson(
        geojson_str,
        style_function=lambda feat: {
            "fillColor": feat["properties"].get("cor", COR_SEM_DADO),
            "color": "#1a1a1a",
            "weight": 1,
            "fillOpacity": 0.72,
        },
        highlight_function=lambda x: {"weight": 3, "color": "#4caf50", "fillOpacity": 0.85},
        tooltip=folium.GeoJsonTooltip(fields=["talhao"], aliases=["Talhão:"]),
    ).add_to(mapa)

    if rotulos_json:
        folium.GeoJson(
            rotulos_json,
            name="Rótulos",
            point_to_layer=lambda feat, latlng: folium.Marker(
                latlng,
                icon=folium.DivIcon(
                    icon_size=(40, 14),
                    icon_anchor=(20, 7),
                    html=f'<div style="font-size:10px;font-weight:700;color:#fff;text-shadow:1px 1px 2px #000;">{feat["properties"]["talhao"]}</div>',
                ),
            ),
        ).add_to(mapa)

    return mapa


def render_mapa_adubacao(
    gdf_mapa: pd.DataFrame,
    ficha: dict | None,
    key_suffix: str = "",
) -> str | None:
    """
    Renderiza mapa + painéis flutuantes. Retorna talhão clicado (se houver).
    gdf_mapa: GeoDataFrame com talhao, geometry, métricas mergeadas.
    """
    st.markdown(css_mapa_panels(), unsafe_allow_html=True)

    col_map, col_ui = st.columns([4, 1])
    with col_ui:
        st.markdown('<div class="sv-map-controls-anchor"></div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="sv-map-panel"><div class="sv-map-panel-title">CAMADA</div></div>',
            unsafe_allow_html=True,
        )
        camada = st.radio(
            "camada_mapa",
            ["Satélite", "Terreno"],
            horizontal=True,
            label_visibility="collapsed",
            key=f"camada_mapa{key_suffix}",
        )
        st.markdown(
            '<div class="sv-map-panel"><div class="sv-map-panel-title">PINTAR POR</div></div>',
            unsafe_allow_html=True,
        )
        pintar = st.radio(
            "pintar_por",
            ["Cobertura", "Hectares", "Valor"],
            horizontal=False,
            label_visibility="collapsed",
            key=f"pintar_por{key_suffix}",
        )
        rotulos = st.checkbox(
            "Rótulos dos talhões",
            value=True,
            key=f"rotulos_talhao{key_suffix}",
        )
        st.markdown(html_ficha_lateral(ficha), unsafe_allow_html=True)

    gdf = gdf_mapa.copy()
    gdf["cor"] = _montar_cores(gdf, pintar)  # type: ignore[arg-type]

    centro_lat = float(gdf.geometry.centroid.y.mean())
    centro_lon = float(gdf.geometry.centroid.x.mean())

    props_cols = ["talhao", "cor"]
    geojson_str = json.dumps(gdf[props_cols + ["geometry"]].__geo_interface__)

    rotulos_json = None
    if rotulos:
        pts = []
        for _, row in gdf.iterrows():
            c = row.geometry.centroid
            pts.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [c.x, c.y]}, "properties": {"talhao": str(row["talhao"])}})
        rotulos_json = json.dumps({"type": "FeatureCollection", "features": pts})

    mapa = _folium_mapa(geojson_str, centro_lat, centro_lon, camada, rotulos_json)

    with col_map:
        out = st_folium(
            mapa,
            width=None,
            height=620,
            returned_objects=["last_object_clicked"],
            key=f"mapa_adubacao{key_suffix}",
            use_container_width=True,
        )

    talhao_click = None
    if out and out.get("last_object_clicked"):
        props = out["last_object_clicked"].get("properties") or {}
        talhao_click = props.get("talhao")
    return talhao_click
