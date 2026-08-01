"""Painel Adubação Florestal 2026 — Santa Virgínia."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import folium
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from config import BUILD, PATH_BASE, PATH_COBERTURA, PATH_KML, SUBTITULO, TITULO
from etl import CORES, SERVICO_LABEL, cruzar, historico, kpis, load_base, load_cobertura, load_gis, retiros
from npk import calcular
from ui import (
    calc_npk_resultado,
    css,
    ficha_talhao,
    hero,
    kpis as show_kpis,
    legenda_mapa,
    tabela,
)

st.set_page_config(page_title=TITULO, page_icon="🌲", layout="wide")
css()
hero(TITULO, f"{SUBTITULO} · build {BUILD}")

if "talhao_sel" not in st.session_state:
    st.session_state.talhao_sel = None


def _salvar(upload, nome: str) -> str | None:
    if upload is None:
        return None
    p = Path(tempfile.gettempdir()) / f"sv_adub_{nome}"
    p.write_bytes(upload.getvalue())
    return str(p)


def _fp(path: str | None) -> str:
    if not path:
        return "none"
    p = Path(path)
    if not p.exists():
        return "missing"
    st_file = p.stat()
    return f"{st_file.st_size}:{int(st_file.st_mtime_ns)}"


@st.cache_data(show_spinner="Carregando planilhas e KML…")
def carregar(pc: str | None, pb: str | None, pk: str | None, fpc: str, fpb: str, fpk: str):
    del fpc, fpb, fpk
    return (
        load_cobertura(Path(pc) if pc else None),
        load_base(Path(pb) if pb else None),
        load_gis(Path(pk) if pk else None),
    )


def mapa(gdf: pd.DataFrame, destaque: str | None = None):
    g = gdf.to_crs(4326).copy()
    c = g.geometry.union_all().centroid
    fmap = folium.Map(location=[c.y, c.x], zoom_start=12, tiles="CartoDB dark_matter", control_scale=True)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri",
        name="Satélite",
        overlay=False,
        control=True,
    ).add_to(fmap)

    geojson = json.loads(g.to_json())
    for feat, (_, row) in zip(geojson["features"], g.iterrows()):
        sel = destaque and str(row.talhao) == str(destaque)
        feat["properties"]["cor"] = row.get("cor", CORES["sem_dado"])
        feat["properties"]["tooltip"] = row.get("tooltip", f"Talhão {row.talhao}")
        feat["properties"]["popup"] = row.get("popup", f"Talhão {row.talhao}")
        feat["properties"]["peso"] = 3 if sel else 1
        feat["properties"]["borda"] = "#ffd166" if sel else "#ffffff"

    folium.GeoJson(
        geojson,
        style_function=lambda f: {
            "fillColor": f["properties"].get("cor", CORES["sem_dado"]),
            "color": f["properties"].get("borda", "#ffffff"),
            "weight": f["properties"].get("peso", 1),
            "fillOpacity": 0.78 if f["properties"].get("peso", 1) > 1 else 0.72,
        },
        highlight_function=lambda f: {
            "weight": 3,
            "color": "#ffd166",
            "fillOpacity": 0.9,
        },
        tooltip=folium.GeoJsonTooltip(fields=["tooltip"], labels=False, sticky=True),
        popup=folium.GeoJsonPopup(fields=["popup"], labels=False, parse_html=True, max_width=320),
    ).add_to(fmap)
    folium.LayerControl(position="topright", collapsed=True).add_to(fmap)
    return fmap


def _filtrar(gdf: pd.DataFrame, retiro: str, busca: str) -> pd.DataFrame:
    f = gdf.copy()
    if retiro != "Todos":
        f = f[f["retiro"].astype(str) == retiro]
    if busca.strip():
        q = busca.strip().upper()
        f = f[f["talhao"].astype(str).str.upper().str.contains(q, na=False)]
    return f


with st.sidebar:
    st.markdown("### Dados")
    st.caption("Nuvem: envie os 3 arquivos · PC: usa caminhos D:\\ automaticamente")

    up_c = st.file_uploader("Cobertura (.xlsx)", type=["xlsx"])
    up_b = st.file_uploader("Base (.xlsx)", type=["xlsx"])
    up_k = st.file_uploader("KML", type=["kml"])

    pc = _salvar(up_c, "cobertura.xlsx") or (str(PATH_COBERTURA) if PATH_COBERTURA.exists() else None)
    pb = _salvar(up_b, "base.xlsx") or (str(PATH_BASE) if PATH_BASE.exists() else None)
    pk = _salvar(up_k, "fazenda.kml") or (str(PATH_KML) if PATH_KML.exists() else None)

    servico = st.selectbox(
        "Serviço",
        ["cobertura", "base"],
        format_func=lambda x: "Cobertura" if x == "cobertura" else "Base/Subsolagem",
    )

try:
    cob, base, gis = carregar(pc, pb, pk, _fp(pc), _fp(pb), _fp(pk))
    ops = pd.concat([cob, base], ignore_index=True)
    fonte = "upload" if any([up_c, up_b, up_k]) else ("PC D:\\" if PATH_KML.exists() else "demo")
    st.sidebar.success(
        f"Fonte: {fonte} · GIS: {len(gis)} talhões · "
        f"Cobertura: {cob['talhao'].nunique()} · Base: {len(base)} linhas"
    )
except Exception as e:
    st.error(f"Erro ao carregar: {e}")
    st.stop()

mapa_df = cruzar(gis, ops, servico)
servico_label = SERVICO_LABEL[servico]
lista_retiros = ["Todos"] + retiros(ops, servico)

with st.sidebar:
    st.markdown("---")
    st.markdown("### Consulta")
    filtro_retiro = st.selectbox("Retiro", lista_retiros)
    busca_talhao = st.text_input("Buscar talhão", placeholder="Ex.: 172, 416A")
    visiveis = _filtrar(mapa_df, filtro_retiro, busca_talhao)
    opcoes = ["— selecione —"] + sorted(visiveis["talhao"].astype(str).unique().tolist(), key=lambda x: (len(x), x))
    sel = st.selectbox("Talhão para detalhe", opcoes, index=0)
    if sel != "— selecione —":
        st.session_state.talhao_sel = sel

show_kpis(kpis(mapa_df))

tab1, tab2, tab3 = st.tabs(["🗺️ Mapa operacional", "📋 Talhões e retiros", "🧮 Calculadora NPK"])

with tab1:
    st.markdown(
        f'<div class="panel"><div class="panel-title">Mapa — {servico_label}</div>'
        f'<div class="panel-sub">Clique em qualquer talhão para abrir retiro, área, status e fertilizante aplicado. '
        f"Use camada <b>Satélite</b> no canto superior direito.</div></div>",
        unsafe_allow_html=True,
    )
    legenda_mapa()
    destaque = st.session_state.talhao_sel
    if destaque:
        row_d = mapa_df[mapa_df["talhao"].astype(str) == str(destaque)]
        if not row_d.empty:
            ficha_talhao(row_d.iloc[0], servico_label)
    components.html(mapa(visiveis if len(visiveis) else mapa_df, destaque)._repr_html_(), height=620, scrolling=False)

with tab2:
    c1, c2 = st.columns(2)
    with c1:
        ret2 = st.selectbox("Filtrar retiro", lista_retiros, key="ret_tab")
    with c2:
        bus2 = st.text_input("Buscar talhão", placeholder="Número do talhão", key="bus_tab")

    vis2 = _filtrar(mapa_df, ret2, bus2)
    tal_opcoes = sorted(vis2["talhao"].astype(str).unique().tolist(), key=lambda x: (len(x), x))
    tal_sel = st.selectbox(
        "Selecione o talhão para ver ficha e histórico",
        tal_opcoes if tal_opcoes else ["— sem talhões no filtro —"],
        disabled=not tal_opcoes,
        key="tal_tab",
    )
    if tal_opcoes:
        st.session_state.talhao_sel = tal_sel

    if tal_opcoes and tal_sel:
        row = vis2[vis2["talhao"].astype(str) == str(tal_sel)].iloc[0]
        ficha_talhao(row, servico_label)

        hist = historico(ops, str(tal_sel), servico)
        if not hist.empty:
            st.markdown(
                '<div class="panel"><div class="panel-title">Histórico na planilha</div>'
                f'<div class="panel-sub">Todos os lançamentos do talhão {tal_sel} neste serviço.</div></div>',
                unsafe_allow_html=True,
            )
            if servico == "cobertura":
                cols_hist = ["horto", "talhao", "ha_floresta", "fertilizante", "data", "dos_real", "total_kg", "operador"]
            else:
                cols_hist = ["horto", "talhao", "area_ha", "fertilizante", "dosagem", "total_kg", "prestador", "status"]
            cols_hist = [c for c in cols_hist if c in hist.columns]
            show = hist[cols_hist].copy()
            show = show.rename(columns={"horto": "Retiro", "talhao": "Talhão", "ha_floresta": "Ha floresta"})
            if "data" in show.columns:
                show["data"] = pd.to_datetime(show["data"], errors="coerce").dt.strftime("%d/%m/%Y")
            if "status" in show.columns:
                show["status"] = show["status"].map({"concluido": "Concluído", "pendente": "Pendente"}).fillna(show["status"])
            st.dataframe(show, use_container_width=True, hide_index=True, height=220)
        else:
            st.info("Este talhão não possui lançamento na planilha do serviço selecionado.")

    st.markdown(
        '<div class="panel"><div class="panel-title">Lista geral</div>'
        '<div class="panel-sub">Visão completa dos talhões filtrados — selecione um talhão acima para abrir a ficha.</div></div>',
        unsafe_allow_html=True,
    )
    cols = [c for c in ["talhao", "retiro", "status_label", "area_ha", "area_feita", "area_rest", "fertilizante", "data_fmt"] if c in vis2.columns]
    tabela(vis2[cols].sort_values(["status_label", "talhao"]), h=360, destaque=str(tal_sel) if tal_opcoes else None)

with tab3:
    st.markdown(
        """
<div class="npk-hero">
  <h2>Calculadora NPK</h2>
  <p>Estime quantidades de Nitrogênio, Fósforo (P₂O₅) e Potássio (K₂O) a partir da fórmula comercial,
  dose kg/ha e área do talhão. Use para planejar compra e conferir aplicação.</p>
</div>""",
        unsafe_allow_html=True,
    )

    presets = {
        "Sulfammo 10-05-18": "Sulfammo 10-05-18",
        "Sulfammo 10-05-22": "Sulfammo 10-05-22",
        "Basifos 06-34-05": "Basifos 06-34-05",
        "Fórmula 14-14-10": "14-14-10",
    }
    p1, p2 = st.columns([2, 1])
    with p1:
        preset = st.selectbox("Fórmulas frequentes na fazenda", list(presets.keys()))
    with p2:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if st.button("Usar fórmula selecionada", use_container_width=True):
            st.session_state.formula_npk = presets[preset]

    area_ref = 50.0
    if st.session_state.talhao_sel:
        rr = mapa_df[mapa_df["talhao"].astype(str) == str(st.session_state.talhao_sel)]
        if not rr.empty:
            area_ref = float(rr.iloc[0]["area_ha"])

    c1, c2, c3, c4 = st.columns([3, 1.2, 1.2, 1.2])
    formula = c1.text_input(
        "Fórmula do fertilizante",
        value=st.session_state.get("formula_npk", presets[preset]),
        placeholder="Ex.: Sulfammo 10-05-18 ou 14-14-10",
        key="formula_npk",
    )
    kg_ha = c2.number_input("Dose (kg/ha)", min_value=0.0, value=200.0, step=10.0)
    area_ha = c3.number_input("Área (ha)", min_value=0.0, value=area_ref, step=1.0)
    calcular_btn = c4.button("Calcular NPK", type="primary", use_container_width=True)

    if st.session_state.talhao_sel:
        st.caption(f"Área sugerida do talhão **{st.session_state.talhao_sel}** selecionado na aba Talhões.")

    if calcular_btn:
        try:
            r = calcular(formula, kg_ha, area_ha)
            calc_npk_resultado(r, formula, kg_ha, area_ha)
        except ValueError as err:
            st.error(str(err))
