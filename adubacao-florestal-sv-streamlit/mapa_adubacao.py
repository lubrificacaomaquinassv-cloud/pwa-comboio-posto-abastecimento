"""Mapa GIS estilo painel SV: Esri, pintar por métrica, clique no talhão."""
from __future__ import annotations

import html
import re
from typing import Literal

import folium
import geopandas as gpd
import numpy as np
import pandas as pd
import streamlit as st
from shapely.geometry import Point
from streamlit_folium import st_folium

from ingestion.talhao_codigo import normalizar_codigo_talhao

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


def _gdf_para_mapa(gdf_mapa: pd.DataFrame) -> gpd.GeoDataFrame:
    """Garante GeoDataFrame com coluna ativa `geometry` (PostGIS pode vir como geom/geometria)."""
    if isinstance(gdf_mapa, gpd.GeoDataFrame):
        g = gdf_mapa.copy()
        if g.geometry.name != "geometry":
            g = g.rename_geometry("geometry")
        if g.crs is None:
            g = g.set_crs(4326)
        return g
    g = gdf_mapa.copy()
    for col in ("geometry", "geom", "geometria"):
        if col in g.columns:
            out = gpd.GeoDataFrame(g, geometry=col, crs="EPSG:4326")
            if out.geometry.name != "geometry":
                out = out.rename_geometry("geometry")
            return out
    raise KeyError(
        "Nenhuma coluna de geometria (geometry/geom/geometria). "
        "Verifique se o mapa veio do Supabase ou KML."
    )


def _fmt_num(val, casas: int = 2) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "—"
    try:
        return f"{float(val):,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return str(val)


def _fmt_data(val) -> str:
    if val is None or pd.isna(val):
        return "—"
    if hasattr(val, "strftime"):
        try:
            return val.strftime("%d/%m/%Y")
        except (ValueError, TypeError):
            return "—"
    return str(val)


def painel_ficha_talhao_streamlit(ficha: dict | None) -> None:
    """Ficha do talhão (Streamlit nativo — sempre visível abaixo do mapa)."""
    st.markdown("---")
    st.subheader("📋 Ficha do talhão")
    if not ficha:
        st.info(
            "Use **Ver talhão** na barra lateral (esquerda) ou **Buscar talhão** à direita do mapa. "
            "Também pode clicar **dentro da área colorida** do polígono."
        )
        return
    t = ficha.get("talhao", "—")
    st.markdown(f"**Talhão {t}** · Retiro: **{ficha.get('retiro') or '—'}** · Classe: **{ficha.get('classe') or '—'}**")
    if not ficha.get("tem_lancamento_cobertura", True):
        st.warning(
            "Este talhão está no mapa (KML), mas **não há lançamento de cobertura** "
            "no Supabase/planilha para este código."
        )
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Área total (ha)", _fmt_num(ficha.get("area_total_ha")))
    c2.metric("Floresta (ha)", _fmt_num(ficha.get("area_floresta_ha")))
    c3.metric("Status cobertura", str(ficha.get("status_cobertura") or "—"))
    pct = ficha.get("pct_cobertura")
    c4.metric(
        "% cobertura",
        "—" if pct is None or (isinstance(pct, float) and np.isnan(pct)) else f"{float(pct):.1f}%",
    )
    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Fertilizante", str(ficha.get("fertilizante") or "—"))
    c6.metric("Data", _fmt_data(ficha.get("data")))
    c7.metric("Previsto (kg/ha)", _fmt_num(ficha.get("previsto_ha"), 0))
    c8.metric("Realizado (kg/ha)", _fmt_num(ficha.get("realizado_ha")))
    c9, c10 = st.columns(2)
    c9.metric("Total gasto (kg)", _fmt_num(ficha.get("kg_total"), 0))
    c10.metric("Operador", str(ficha.get("operador") or "—"))


def html_ficha_lateral(ficha: dict | None) -> str:
    if not ficha:
        return """
        <div class="sv-map-panel sv-ficha">
            <div class="sv-map-panel-title">FICHA DO TALHÃO</div>
            <p class="sv-ficha-hint-strong">
                <b>Clique dentro do polígono colorido</b> no mapa. O talhão ficará com
                <span style="color:#00e676">borda verde</span> e os dados aparecem aqui.
            </p>
            <p class="sv-ficha-hint">A busca por número abaixo é opcional.</p>
        </div>
        """
    t = html.escape(str(ficha.get("talhao", "")))
    retiro = html.escape(str(ficha.get("retiro") or "—"))
    classe = html.escape(str(ficha.get("classe") or "—"))
    status = html.escape(str(ficha.get("status_cobertura") or "—"))
    pct = ficha.get("pct_cobertura")
    pct_txt = "—" if pct is None or (isinstance(pct, float) and np.isnan(pct)) else f"{float(pct):.1f}%"
    sem_lanc = not ficha.get("tem_lancamento_cobertura", True)
    aviso = (
        '<p class="sv-ficha-hint">Sem lançamento de cobertura no painel/Supabase — '
        "cadastro do mapa (KML). Carregue a planilha ou sincronize para ver fertilizante e doses.</p>"
        if sem_lanc
        else ""
    )
    return f"""
    <div class="sv-map-panel sv-ficha sv-ficha-ativa">
        <div class="sv-map-panel-title">TALHÃO {t} · SELECIONADO</div>
        <div class="sv-ficha-grid">
            <span class="lbl">Nº talhão</span><span class="val">{t}</span>
            <span class="lbl">Retiro</span><span class="val">{retiro}</span>
            <span class="lbl">Classe</span><span class="val">{classe}</span>
            <span class="lbl">Total (há)</span><span class="val">{_fmt_num(ficha.get('area_total_ha'))}</span>
            <span class="lbl">Floresta (há)</span><span class="val">{_fmt_num(ficha.get('area_floresta_ha'))}</span>
            <span class="lbl">Status cobertura</span><span class="val">{status}</span>
            <span class="lbl">% cobertura</span><span class="val">{pct_txt}</span>
            <span class="lbl">Fertilizante</span><span class="val">{html.escape(str(ficha.get('fertilizante') or '—'))}</span>
            <span class="lbl">Data</span><span class="val">{_fmt_data(ficha.get('data'))}</span>
            <span class="lbl">Previsto (kg/há)</span><span class="val">{_fmt_num(ficha.get('previsto_ha'), 0)}</span>
            <span class="lbl">Realizado (kg/há)</span><span class="val">{_fmt_num(ficha.get('realizado_ha'))}</span>
            <span class="lbl">Total gasto (kg)</span><span class="val">{_fmt_num(ficha.get('kg_total'), 0)}</span>
            <span class="lbl">Operador</span><span class="val">{html.escape(str(ficha.get('operador') or '—'))}</span>
        </div>
        {aviso}
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
    .sv-ficha.sv-ficha-ativa {
        border: 2px solid #00e676;
        box-shadow: 0 0 0 1px rgba(0, 230, 118, 0.35);
    }
    .sv-ficha-hint-strong {
        color: #c9d1d9;
        font-size: 12px;
        margin: 0 0 8px 0;
        line-height: 1.45;
    }
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


def _coords_folium(geom) -> list:
    """Converte geometria shapely em lista de anéis [[lat, lon], ...] para folium.Polygon."""
    if geom is None or geom.is_empty:
        return []
    gtype = geom.geom_type
    if gtype == "Polygon":
        ext = [[float(y), float(x)] for x, y in geom.exterior.coords]
        return [ext]
    if gtype == "MultiPolygon":
        rings: list = []
        for poly in geom.geoms:
            if poly.is_empty:
                continue
            ext = [[float(y), float(x)] for x, y in poly.exterior.coords]
            rings.append(ext)
        return rings
    return []


def _html_popup_talhao(talhao: str, ficha: dict | None) -> str:
    if not ficha:
        return f"<b>Talhão {html.escape(talhao)}</b><br>Clique para selecionar."
    t = html.escape(str(ficha.get("talhao", talhao)))
    fert = html.escape(str(ficha.get("fertilizante") or "—"))
    status = html.escape(str(ficha.get("status_cobertura") or "—"))
    pct = ficha.get("pct_cobertura")
    pct_txt = "—" if pct is None or (isinstance(pct, float) and np.isnan(pct)) else f"{float(pct):.1f}%"
    return (
        f"<div style='min-width:180px;font-size:12px;line-height:1.5'>"
        f"<b>Talhão {t}</b><br>"
        f"Retiro: {html.escape(str(ficha.get('retiro') or '—'))}<br>"
        f"Status: {status} · {pct_txt}<br>"
        f"Fertilizante: {fert}<br>"
        f"Realizado: {_fmt_num(ficha.get('realizado_ha'))} kg/ha"
        f"</div>"
    )


def _adicionar_poligono_talhao(
    mapa: folium.Map,
    geom,
    cor: str,
    talhao: str,
    *,
    selecionado: bool = False,
    outro_selecionado_no_mapa: bool = False,
    ficha_popup: dict | None = None,
) -> None:
    """Camadas folium sem lambdas — compatível com st_folium (JSON serializável)."""
    rings = _coords_folium(geom)
    if not rings:
        return
    tip = f"Talhão: {talhao}"
    pop = folium.Popup(_html_popup_talhao(talhao, ficha_popup), max_width=280)
    if selecionado:
        borda, peso, opacidade = "#00e676", 4, 0.88
    elif outro_selecionado_no_mapa:
        borda, peso, opacidade = "#333333", 1, 0.38
    else:
        borda, peso, opacidade = "#1a1a1a", 1, 0.72
    opts = dict(
        color=borda,
        weight=peso,
        fill=True,
        fill_color=cor or COR_SEM_DADO,
        fill_opacity=opacidade,
        tooltip=tip,
        popup=pop,
    )
    if len(rings) == 1:
        folium.Polygon(locations=rings[0], **opts).add_to(mapa)
    else:
        for ring in rings:
            folium.Polygon(locations=ring, **opts).add_to(mapa)


def _folium_mapa(
    gdf: gpd.GeoDataFrame,
    centro_lat: float,
    centro_lon: float,
    camada: Camada,
    mostrar_rotulos: bool,
    talhao_selecionado: str | None = None,
    fichas_por_talhao: dict[str, dict] | None = None,
) -> folium.Map:
    tiles = TILES_TERRENO if camada == "Terreno" else TILES_SATELITE
    mapa = folium.Map(
        location=[centro_lat, centro_lon],
        zoom_start=12,
        tiles=tiles[0],
        attr=tiles[1],
        control_scale=False,
    )

    sel = (str(talhao_selecionado).strip().upper() if talhao_selecionado else None)
    fichas = fichas_por_talhao or {}
    bounds_sel = None

    for _, row in gdf.iterrows():
        tal = str(row.get("talhao", ""))
        tal_norm = normalizar_codigo_talhao(tal) or tal
        cor = str(row.get("cor") or COR_SEM_DADO)
        is_sel = sel is not None and tal_norm == sel
        ficha_pop = fichas.get(tal_norm) or fichas.get(tal)
        _adicionar_poligono_talhao(
            mapa,
            row.geometry,
            cor,
            tal,
            selecionado=is_sel,
            outro_selecionado_no_mapa=bool(sel and not is_sel),
            ficha_popup=ficha_pop if is_sel else None,
        )
        if is_sel and row.geometry is not None and not row.geometry.is_empty:
            bounds_sel = row.geometry.bounds
        if mostrar_rotulos and row.geometry is not None and not row.geometry.is_empty:
            c = row.geometry.centroid
            folium.Marker(
                location=[float(c.y), float(c.x)],
                icon=folium.DivIcon(
                    icon_size=(40, 14),
                    icon_anchor=(20, 7),
                    html=(
                        f'<div style="font-size:10px;font-weight:700;color:#fff;'
                        f'text-shadow:1px 1px 2px #000;">{html.escape(tal)}</div>'
                    ),
                ),
            ).add_to(mapa)

    if bounds_sel is not None:
        minx, miny, maxx, maxy = bounds_sel
        mapa.fit_bounds([[miny, minx], [maxy, maxx]], padding=(40, 40))

    return mapa


_RX_TALHAO_TEXTO = re.compile(
    r"(?:talh[aã]o|talhao)\s*:?\s*([0-9]+[A-Z0-9\-]*)",
    re.IGNORECASE,
)


def _talhao_de_texto(val) -> str | None:
    if val is None:
        return None
    if isinstance(val, dict):
        for v in val.values():
            t = _talhao_de_texto(v)
            if t:
                return t
        return None
    if isinstance(val, (list, tuple)):
        for item in val:
            t = _talhao_de_texto(item)
            if t:
                return t
        return None
    s = str(val).strip()
    if not s:
        return None
    m = _RX_TALHAO_TEXTO.search(s)
    if m:
        return normalizar_codigo_talhao(m.group(1))
    if re.fullmatch(r"[0-9]+[A-Z0-9\-]*", s, re.I):
        return normalizar_codigo_talhao(s)
    return None


def _talhao_por_ponto(gdf: pd.DataFrame, lat: float, lng: float) -> str | None:
    if gdf is None or gdf.empty or "geometry" not in gdf.columns:
        return None
    geo = gdf
    if isinstance(geo, gpd.GeoDataFrame):
        if geo.crs is None:
            geo = geo.set_crs(4326)
        elif geo.crs.to_epsg() != 4326:
            geo = geo.to_crs(4326)
    pt = gpd.GeoDataFrame(geometry=[Point(float(lng), float(lat))], crs="EPSG:4326")
    try:
        hits = gpd.sjoin(geo, pt, predicate="contains", how="inner")
    except Exception:
        pt_sh = Point(float(lng), float(lat))
        mask = geo.geometry.contains(pt_sh)
        if not mask.any():
            mask = geo.geometry.intersects(pt_sh)
        if not mask.any():
            return None
        hits = geo.loc[mask]
    if hits.empty:
        return None
    if len(hits) > 1:
        hits = hits.assign(_area=hits.geometry.area).sort_values("_area")
    return normalizar_codigo_talhao(hits.iloc[0]["talhao"])


def _talhao_do_clique(out: dict | None, gdf: pd.DataFrame) -> str | None:
    """Resolve talhão: tooltip/popup do GeoJSON, properties ou ponto no polígono."""
    if not out:
        return None

    for key in ("last_object_clicked_tooltip", "last_object_clicked_popup"):
        t = _talhao_de_texto(out.get(key))
        if t:
            return t

    obj = out.get("last_object_clicked")
    if isinstance(obj, dict):
        props = obj.get("properties") or {}
        tal = props.get("talhao")
        if tal:
            return normalizar_codigo_talhao(tal)
        lat = obj.get("lat")
        lng = obj.get("lng")
        if lat is not None and lng is not None:
            t = _talhao_por_ponto(gdf, float(lat), float(lng))
            if t:
                return t

    click = out.get("last_clicked") or out.get("last_object_clicked")
    if isinstance(click, dict):
        lat = click.get("lat")
        lng = click.get("lng")
        if lat is not None and lng is not None:
            return _talhao_por_ponto(gdf, float(lat), float(lng))
    return None


def render_mapa_adubacao(
    gdf_mapa: pd.DataFrame,
    ficha: dict | None,
    key_suffix: str = "",
    talhoes_lista: list[str] | None = None,
    talhao_selecionado: str | None = None,
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
            "Mostrar números no mapa",
            value=False,
            help="Desligado por padrão — mapa mais limpo; clique no polígono para escolher o talhão.",
            key=f"rotulos_talhao{key_suffix}",
        )
        ficha_slot = st.empty()
        if ficha:
            ficha_slot.markdown(html_ficha_lateral(ficha), unsafe_allow_html=True)
        else:
            ficha_slot.markdown(html_ficha_lateral(None), unsafe_allow_html=True)

    gdf = _gdf_para_mapa(gdf_mapa)
    gdf["cor"] = _montar_cores(gdf, pintar)  # type: ignore[arg-type]

    centro_lat = float(gdf.geometry.centroid.y.mean())
    centro_lon = float(gdf.geometry.centroid.x.mean())

    sel = talhao_selecionado or st.session_state.get("talhao_selecionado")
    mapa = _folium_mapa(
        gdf,
        centro_lat,
        centro_lon,
        camada,
        rotulos,
        talhao_selecionado=sel,
        fichas_por_talhao={str(ficha["talhao"]): ficha} if ficha and ficha.get("talhao") else None,
    )

    with col_map:
        out = st_folium(
            mapa,
            width=None,
            height=620,
            returned_objects=[
                "last_object_clicked",
                "last_clicked",
                "last_object_clicked_tooltip",
                "last_object_clicked_popup",
                "last_object_clicked_count",
            ],
            key=f"mapa_adubacao{key_suffix}",
            use_container_width=True,
        )

    clicado = _talhao_do_clique(out, gdf)

    with col_ui:
        lista = talhoes_lista or sorted(
            gdf["talhao"].dropna().astype(str).unique().tolist(),
            key=lambda x: (len(x), x),
        )
        _placeholder = "— escolha —"
        opcoes = [_placeholder] + lista
        atual = st.session_state.get("talhao_selecionado")
        key_buscar = f"buscar_talhao{key_suffix}"
        if atual in opcoes:
            st.session_state[key_buscar] = atual
        elif key_buscar not in st.session_state:
            st.session_state[key_buscar] = _placeholder

        def _on_buscar_talhao() -> None:
            sel = st.session_state.get(key_buscar)
            if sel == _placeholder:
                st.session_state.talhao_selecionado = None
            else:
                st.session_state.talhao_selecionado = normalizar_codigo_talhao(sel)

        with st.expander("Buscar por número (opcional)", expanded=False):
            st.selectbox(
                "Buscar talhão",
                opcoes,
                label_visibility="collapsed",
                key=key_buscar,
                on_change=_on_buscar_talhao,
            )

    return clicado
