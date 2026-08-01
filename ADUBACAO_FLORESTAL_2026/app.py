"""Painel Adubação Florestal 2026 — Santa Virgínia."""
from __future__ import annotations

import tempfile
from pathlib import Path

import folium
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from config import BUILD, PATH_BASE, PATH_COBERTURA, PATH_KML, SUBTITULO, TITULO
from etl import CORES, cruzar, kpis, load_base, load_cobertura, load_gis
from npk import calcular
from ui import css, hero, kpis as show_kpis, tabela

st.set_page_config(page_title=TITULO, page_icon="🌲", layout="wide")
css()
hero(TITULO, f"{SUBTITULO} · build {BUILD}")


@st.cache_data
def dados():
    return load_cobertura(), load_base(), load_gis()


def mapa(gdf):
    g = gdf.to_crs(4326)
    c = g.geometry.union_all().centroid
    m = folium.Map(location=[c.y, c.x], zoom_start=11, tiles="CartoDB dark_matter")
    for _, r in g.iterrows():
        cor = r.get("cor", CORES["sem_dado"])

        def estilo(_, col=cor):
            return {"fillColor": col, "color": "#fff", "weight": 1, "fillOpacity": 0.75}

        folium.GeoJson(r.geometry.__geo_interface__, style_function=estilo,
                       tooltip=f"Talhão {r.talhao} | {r.status} | {r.area_feita:.1f}/{r.area_ha:.1f} ha").add_to(m)
    return m


with st.sidebar:
    st.markdown("### Dados")
    st.caption("PC: caminhos D:\\ · Nuvem: upload abaixo")
    up_c = st.file_uploader("Cobertura (.xlsx)", type=["xlsx"])
    up_b = st.file_uploader("Base (.xlsx)", type=["xlsx"])
    up_k = st.file_uploader("KML", type=["kml"])
    if up_c or up_b or up_k:
        tmp = Path(tempfile.gettempdir())
        if up_c:
            p = tmp / "cobertura.xlsx"; p.write_bytes(up_c.getvalue()); import config; config.PATH_COBERTURA = p
        if up_b:
            p = tmp / "base.xlsx"; p.write_bytes(up_b.getvalue()); import config; config.PATH_BASE = p
        if up_k:
            p = tmp / "fazenda.kml"; p.write_bytes(up_k.getvalue()); import config; config.PATH_KML = p
        st.cache_data.clear()

    servico = st.selectbox("Serviço", ["cobertura", "base"], format_func=lambda x: "Cobertura" if x == "cobertura" else "Base/Subsolagem")

try:
    cob, base, gis = dados()
except Exception as e:
    st.error(f"Erro ao carregar: {e}")
    st.stop()

ops = cob if servico == "cobertura" else base
mapa_df = cruzar(gis, pd.concat([cob, base]), servico)
show_kpis(kpis(mapa_df))

tab1, tab2, tab3 = st.tabs(["Mapa", "Talhões", "NPK"])

with tab1:
    components.html(mapa(mapa_df)._repr_html_(), height=520)

with tab2:
    cols = ["talhao", "status", "area_ha", "area_feita", "area_rest", "horto", "fertilizante"]
    cols = [c for c in cols if c in mapa_df.columns]
    tabela(mapa_df[cols].sort_values("talhao"))

with tab3:
    c1, c2, c3 = st.columns(3)
    f = c1.text_input("Fórmula", "Sulfammo 10-05-18")
    d = c2.number_input("kg/ha", value=200.0)
    a = c3.number_input("Área ha", value=50.0)
    if st.button("Calcular"):
        try:
            r = calcular(f, d, a)
            st.success(f"N {r.n_pct}% · P {r.p_pct}% · K {r.k_pct}%")
            m1, m2, m3 = st.columns(3)
            m1.metric("N total kg", f"{r.n_total:.0f}")
            m2.metric("P₂O₅ total kg", f"{r.p_total:.0f}")
            m3.metric("K₂O total kg", f"{r.k_total:.0f}")
        except ValueError as err:
            st.error(str(err))
