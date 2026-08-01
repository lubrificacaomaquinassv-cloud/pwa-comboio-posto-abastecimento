"""
Painel Adubação Florestal 2026 — Santa Virgínia
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import folium
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from config import APP_SUBTITLE, APP_TITLE, PAINEL_BUILD, PATH_BASE, PATH_COBERTURA, PATH_KML
from etl import (
    cruzar_servico_gis,
    enriquecer_npk,
    listar_hortos,
    load_base,
    load_cobertura,
    load_talhoes_gis,
    resumo_kpis,
)
from npk import calcular_nutrientes, parse_formula
from ui import dark_table, inject_styles, render_hero, render_kpis, render_legend, section

st.set_page_config(page_title=f"{APP_TITLE} — SV", page_icon="🌲", layout="wide")

inject_styles()
render_hero(APP_TITLE, APP_SUBTITLE, PAINEL_BUILD)


def _salvar_upload(uploaded, suffix: str) -> Path | None:
    if uploaded is None:
        return None
    tmp = Path(tempfile.gettempdir()) / f"adubacao_{uploaded.file_id}{suffix}"
    tmp.write_bytes(uploaded.getvalue())
    return tmp


@st.cache_data(show_spinner="Carregando planilhas e GIS…")
def carregar_dados(path_cobertura: str | None, path_base: str | None, path_gis: str | None, cache_key: str):
    del cache_key
    cobertura = load_cobertura(Path(path_cobertura) if path_cobertura and Path(path_cobertura).exists() else None)
    base = load_base(Path(path_base) if path_base and Path(path_base).exists() else None)
    gis_path = Path(path_gis) if path_gis and Path(path_gis).exists() else None
    gis = load_talhoes_gis(gis_path)
    return cobertura, base, gis


def _centroide(gdf):
    try:
        geom = gdf.geometry.union_all()
    except AttributeError:
        geom = gdf.geometry.unary_union
    c = geom.centroid
    return c.y, c.x


def _mapa_folium(gdf) -> folium.Map:
    lat, lon = _centroide(gdf)
    fmap = folium.Map(location=[lat, lon], zoom_start=11, tiles="CartoDB dark_matter", control_scale=True)
    for _, row in gdf.iterrows():
        if row.geometry is None or row.geometry.is_empty:
            continue
        cor = row.get("cor", "#95a5a6")

        def _style(_, c=cor):
            return {"fillColor": c, "color": "#ffffff", "weight": 1, "fillOpacity": 0.72}

        folium.GeoJson(
            row.geometry.__geo_interface__,
            style_function=_style,
            tooltip=(
                f"Talhão {row.get('talhao')} | {row.get('status')} | "
                f"Feito {row.get('area_feita_ha', 0):.1f} ha | "
                f"Restante {row.get('area_restante_ha', 0):.1f} ha"
            ),
        ).add_to(fmap)
    return fmap


with st.sidebar:
    section("Dados", sidebar=True)
    path_cobertura = st.text_input("Cobertura", str(PATH_COBERTURA), label_visibility="collapsed")
    path_base = st.text_input("Base/Subsolagem", str(PATH_BASE), label_visibility="collapsed")
    path_gis = st.text_input("KML", str(PATH_KML), label_visibility="collapsed")

    ok_c = Path(path_cobertura).exists()
    ok_b = Path(path_base).exists()
    ok_g = Path(path_gis).exists()
    if ok_c and ok_b and ok_g:
        st.success("Planilhas e KML encontrados no PC")
    else:
        st.warning("Usando dados demo — confira caminhos D:\\")

    section("Filtros", sidebar=True)
    servico = st.selectbox(
        "Serviço",
        ["cobertura", "base_subsolagem"],
        format_func=lambda x: "Adubação de Cobertura" if x == "cobertura" else "Base / Subsolagem",
    )

try:
    cache_key = f"{path_cobertura}|{path_base}|{path_gis}"
    cobertura, base, gis = carregar_dados(path_cobertura, path_base, path_gis, cache_key)
except Exception as exc:
    st.error(f"Erro ao carregar: {exc}")
    st.info("Verifique se Python, geopandas e openpyxl estão instalados (RODAR_PAINEL.bat faz isso).")
    st.stop()

hortos = ["Todos"] + listar_hortos(cobertura, base)
with st.sidebar:
    horto_filtro = st.selectbox("Horto", hortos)

operacional = cobertura if servico == "cobertura" else base
mapa = cruzar_servico_gis(gis, operacional, servico, horto=None if horto_filtro == "Todos" else horto_filtro)
render_kpis(resumo_kpis(mapa))

tab_mapa, tab_tabela, tab_npk, tab_dados = st.tabs(["Mapa", "Talhões", "NPK", "Dados"])

with tab_mapa:
    section("Mapa operacional")
    render_legend()
    mapa_plot = mapa.to_crs("EPSG:4326")
    try:
        fmap = _mapa_folium(mapa_plot)
        components.html(fmap._repr_html_(), height=520, scrolling=False)
    except Exception as exc:
        st.error(f"Erro no mapa: {exc}")

    section("Por horto")
    ops_f = operacional if horto_filtro == "Todos" else operacional[operacional["horto"] == horto_filtro]
    if servico == "cobertura":
        por_horto = ops_f.groupby("horto").agg(talhoes=("talhao", "nunique"), ha=("ha_floresta", "sum"), kg=("total_kg", "sum")).reset_index()
    else:
        feito = ops_f[ops_f["status"] == "concluido"]
        pend = ops_f[ops_f["status"] == "pendente"]
        por_horto = pd.DataFrame({"horto": sorted(ops_f["horto"].dropna().unique())})
        por_horto["feito_ha"] = por_horto["horto"].map(feito.groupby("horto")["area_ha"].sum())
        por_horto["pendente_ha"] = por_horto["horto"].map(pend.groupby("horto")["area_ha"].sum())
        por_horto = por_horto.fillna(0)
    dark_table(por_horto, height=220)

with tab_tabela:
    section("Status por talhão")
    cols = ["talhao", "classe", "horto", "status", "area_ha", "area_feita_ha", "area_restante_ha", "pct_concluido", "fertilizante"]
    tabela = mapa[[c for c in cols if c in mapa.columns]].sort_values(["status", "talhao"]).copy()
    tabela["pct_concluido"] = tabela["pct_concluido"].round(1)
    for c in ("area_ha", "area_feita_ha", "area_restante_ha"):
        if c in tabela.columns:
            tabela[c] = tabela[c].round(2)
    dark_table(tabela, height=460)
    st.download_button("Exportar CSV", tabela.to_csv(index=False).encode("utf-8-sig"), f"adubacao_{servico}.csv", "text/csv")

with tab_npk:
    section("Calculadora NPK")
    c1, c2, c3 = st.columns(3)
    formula_in = c1.text_input("Fórmula", "Sulfammo 10-05-18")
    dosagem_in = c2.number_input("kg/ha", 0.0, value=200.0, step=10.0)
    area_in = c3.number_input("Área ha", 0.0, value=50.0, step=1.0)
    if st.button("Calcular"):
        try:
            r = calcular_nutrientes(formula_in, dosagem_in, area_in)
            st.success(f"N {r.formula.n}% · P {r.formula.p2o5}% · K {r.formula.k2o}%")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("N kg/ha", f"{r.n_kg_ha:.1f}")
            m2.metric("P₂O₅ kg/ha", f"{r.p2o5_kg_ha:.1f}")
            m3.metric("K₂O kg/ha", f"{r.k2o_kg_ha:.1f}")
            m4.metric("Adubo kg", f"{r.adubo_total_kg:,.0f}")
        except ValueError as e:
            st.error(str(e))
    section("Nutrientes aplicados")
    ops = operacional if horto_filtro == "Todos" else operacional[operacional["horto"] == horto_filtro]
    npk_df = enriquecer_npk(ops)
    show = [c for c in ["horto", "talhao", "fertilizante", "n_total_kg", "p2o5_total_kg", "k2o_total_kg"] if c in npk_df.columns]
    dark_table(npk_df[show].dropna(subset=["n_total_kg"], how="all"), height=300)

with tab_dados:
    dark_table(cobertura.head(80), 240)
    dark_table(base.head(80), 240)
