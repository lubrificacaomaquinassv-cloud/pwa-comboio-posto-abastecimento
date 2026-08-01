"""
Dashboard Adubação Florestal 2026 — Santa Virgínia
Cobertura (6 hortos) + Base/Subsolagem + mapa GIS + calculadora NPK.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from config import (
    DASHBOARD_BUILD,
    PATH_BASE,
    PATH_COBERTURA,
    PATH_COBERTURA_SAMPLE,
    PATH_GIS_SAMPLE,
    PATH_KML,
)
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

st.set_page_config(
    page_title="Adubação Florestal 2026",
    page_icon="🌲",
    layout="wide",
)

st.title("Adubação Florestal 2026")
st.caption(
    f"Acompanhamento de cobertura, base/subsolagem e nutrientes — Fazenda Santa Virgínia · build {DASHBOARD_BUILD}"
)


def hex_to_rgba(hex_color: str, alpha: int = 190) -> list[int]:
    h = hex_color.lstrip("#")
    return [int(h[i : i + 2], 16) for i in (0, 2, 4)] + [alpha]


@st.cache_data(show_spinner="Carregando planilhas e GIS…")
def carregar_dados(path_cobertura: str, path_base: str, path_gis: str):
    cobertura = load_cobertura(Path(path_cobertura) if Path(path_cobertura).exists() else None)
    base = load_base(Path(path_base) if Path(path_base).exists() else None)
    gis_path = Path(path_gis) if Path(path_gis).exists() else None
    gis = load_talhoes_gis(gis_path)
    return cobertura, base, gis


with st.sidebar:
    st.header("Fontes de dados")
    path_cobertura = st.text_input("Planilha Cobertura", str(PATH_COBERTURA))
    path_base = st.text_input("Planilha Base/Subsolagem", str(PATH_BASE))
    path_gis = st.text_input("Cadastro KML / GeoJSON", str(PATH_KML))

    using_sample = not Path(path_cobertura).exists()
    if using_sample:
        st.info("Planilhas reais não encontradas — usando **dados amostra** em `data/sample/`.")

    servico = st.radio(
        "Serviço no mapa",
        options=["cobertura", "base_subsolagem"],
        format_func=lambda x: "Adubação de Cobertura" if x == "cobertura" else "Base / Subsolagem",
    )

try:
    cobertura, base, gis = carregar_dados(path_cobertura, path_base, path_gis)
except Exception as exc:
    st.error(f"Erro ao carregar dados: {exc}")
    st.stop()

hortos = ["Todos"] + listar_hortos(cobertura, base)
with st.sidebar:
    horto_filtro = st.selectbox("Filtrar por horto", hortos)

operacional = cobertura if servico == "cobertura" else base
mapa = cruzar_servico_gis(gis, operacional, servico, horto=None if horto_filtro == "Todos" else horto_filtro)
kpis = resumo_kpis(mapa)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Talhões no GIS", kpis["talhoes_gis"])
c2.metric("Concluídos", kpis["concluidos"])
c3.metric("Pendentes", kpis["pendentes"])
c4.metric("Área feita (ha)", f"{kpis['area_feita_ha']:,.1f}")
c5.metric("Área restante (ha)", f"{kpis['area_restante_ha']:,.1f}")

tab_mapa, tab_tabela, tab_npk, tab_dados = st.tabs(
    ["Mapa", "Tabela por talhão", "Calculadora NPK", "Dados brutos"]
)

with tab_mapa:
    st.subheader("Mapa por talhão")
    st.markdown("🟢 Concluído · 🔴 Pendente · ⚪ Sem registro na planilha")

    mapa_plot = mapa.to_crs("EPSG:4326").copy()
    mapa_plot["label"] = mapa_plot.apply(
        lambda r: (
            f"Talhão {r['talhao']} | {r['status']} | "
            f"Feito: {r['area_feita_ha']:.1f} ha | Restante: {r['area_restante_ha']:.1f} ha"
        ),
        axis=1,
    )
    mapa_plot["fill_rgb"] = mapa_plot["cor"].map(lambda c: hex_to_rgba(c))

    geojson = json.loads(mapa_plot.to_json())
    for feat, (_, row) in zip(geojson["features"], mapa_plot.iterrows()):
        feat["properties"]["fillColor"] = row["fill_rgb"]
        feat["properties"]["label"] = row["label"]
        feat["properties"]["pct"] = round(float(row["pct_concluido"]), 1)

    center = mapa_plot.geometry.union_all().centroid
    st.pydeck_chart(
        {
            "initialViewState": {
                "latitude": center.y,
                "longitude": center.x,
                "zoom": 11,
                "pitch": 0,
            },
            "mapStyle": "light",
            "layers": [
                {
                    "@@type": "GeoJsonLayer",
                    "data": geojson,
                    "pickable": True,
                    "stroked": True,
                    "filled": True,
                    "getFillColor": "properties.fillColor",
                    "getLineColor": [40, 40, 40, 200],
                    "lineWidthMinPixels": 1,
                    "opacity": 0.82,
                }
            ],
            "tooltip": {"text": "{label}\nProgresso: {pct}%"},
        },
        use_container_width=True,
    )

    if servico == "cobertura":
        ops_f = operacional if horto_filtro == "Todos" else operacional[operacional["horto"] == horto_filtro]
        por_horto = (
            ops_f.groupby("horto")
            .agg(talhoes=("talhao", "nunique"), ha=("ha_floresta", "sum"), kg=("total_kg", "sum"))
            .reset_index()
        )
    else:
        ops_f = operacional if horto_filtro == "Todos" else operacional[operacional["horto"] == horto_filtro]
        feito = ops_f[ops_f["status"] == "concluido"]
        pend = ops_f[ops_f["status"] == "pendente"]
        por_horto = pd.DataFrame({"horto": sorted(ops_f["horto"].dropna().unique())})
        por_horto["feito_ha"] = por_horto["horto"].map(feito.groupby("horto")["area_ha"].sum())
        por_horto["pendente_ha"] = por_horto["horto"].map(pend.groupby("horto")["area_ha"].sum())
        por_horto = por_horto.fillna(0)

    st.dataframe(por_horto, use_container_width=True, hide_index=True)

with tab_tabela:
    cols_show = [
        "talhao",
        "classe",
        "horto",
        "status",
        "area_ha",
        "area_feita_ha",
        "area_restante_ha",
        "pct_concluido",
        "fertilizante",
    ]
    tabela = mapa[[c for c in cols_show if c in mapa.columns]].sort_values(["status", "talhao"]).copy()
    tabela["pct_concluido"] = tabela["pct_concluido"].round(1)
    for col in ("area_ha", "area_feita_ha", "area_restante_ha"):
        if col in tabela.columns:
            tabela[col] = tabela[col].round(2)

    st.dataframe(tabela, use_container_width=True, hide_index=True)
    st.download_button(
        "Exportar CSV",
        tabela.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"adubacao_{servico}_2026.csv",
        mime="text/csv",
    )

with tab_npk:
    st.subheader("Calculadora de NPK")
    st.markdown(
        "Fórmula **14-14-10** = % de **N**, **P₂O₅** e **K₂O** em peso. "
        "Informe dosagem (kg/ha) e área (ha)."
    )

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        formula_in = st.text_input("Fórmula / fertilizante", "Sulfammo 10-05-18")
    with col_b:
        dosagem_in = st.number_input("Dosagem (kg/ha)", min_value=0.0, value=200.0, step=10.0)
    with col_c:
        area_in = st.number_input("Área (ha)", min_value=0.0, value=50.0, step=1.0)

    if st.button("Calcular nutrientes", type="primary"):
        try:
            parsed = parse_formula(formula_in)
            result = calcular_nutrientes(formula_in, dosagem_in, area_in)
            st.success(f"Fórmula: **N {parsed.n}% · P₂O₅ {parsed.p2o5}% · K₂O {parsed.k2o}%**")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("N (kg/ha)", f"{result.n_kg_ha:.2f}")
            m2.metric("P₂O₅ (kg/ha)", f"{result.p2o5_kg_ha:.2f}")
            m3.metric("K₂O (kg/ha)", f"{result.k2o_kg_ha:.2f}")
            m4.metric("Adubo total (kg)", f"{result.adubo_total_kg:,.0f}")
            m5, m6, m7 = st.columns(3)
            m5.metric("N total (kg)", f"{result.n_total_kg:,.1f}")
            m6.metric("P₂O₅ total (kg)", f"{result.p2o5_total_kg:,.1f}")
            m7.metric("K₂O total (kg)", f"{result.k2o_total_kg:,.1f}")
        except ValueError as err:
            st.error(str(err))

    st.divider()
    st.markdown("**Nutrientes nos talhões registrados**")
    ops_npk = enriquecer_npk(operacional if horto_filtro == "Todos" else operacional[operacional["horto"] == horto_filtro])
    cols_npk = [
        c
        for c in [
            "horto",
            "talhao",
            "fertilizante",
            "ha_floresta",
            "area_ha",
            "dosagem_realizada",
            "dosagem_kg_ha",
            "n_total_kg",
            "p2o5_total_kg",
            "k2o_total_kg",
            "total_kg",
        ]
        if c in ops_npk.columns
    ]
    st.dataframe(ops_npk[cols_npk].dropna(how="all", subset=["n_total_kg"]), use_container_width=True)

with tab_dados:
    st.subheader("Cobertura — 6 hortos")
    st.dataframe(cobertura, use_container_width=True, hide_index=True)
    st.subheader("Base / Subsolagem")
    st.dataframe(base, use_container_width=True, hide_index=True)
    st.subheader("Cadastro GIS")
    st.dataframe(gis.drop(columns="geometry"), use_container_width=True, hide_index=True)
