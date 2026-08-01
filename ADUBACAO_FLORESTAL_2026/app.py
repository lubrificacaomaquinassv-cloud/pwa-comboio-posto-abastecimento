"""
Painel Adubação Florestal 2026 — Santa Virgínia
Cobertura · Base/Subsolagem · Mapa GIS · NPK
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

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

st.set_page_config(
    page_title=f"{APP_TITLE} — SV",
    page_icon="🌲",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_styles()
render_hero(APP_TITLE, APP_SUBTITLE, PAINEL_BUILD)


def hex_to_rgba(hex_color: str, alpha: int = 190) -> list[int]:
    h = hex_color.lstrip("#")
    return [int(h[i : i + 2], 16) for i in (0, 2, 4)] + [alpha]


def _salvar_upload(uploaded, suffix: str) -> Path | None:
    if uploaded is None:
        return None
    tmp = Path(tempfile.gettempdir()) / f"adubacao_{uploaded.file_id}{suffix}"
    tmp.write_bytes(uploaded.getvalue())
    return tmp


@st.cache_data(show_spinner="Carregando planilhas e cadastro GIS…")
def carregar_dados(
    path_cobertura: str | None,
    path_base: str | None,
    path_gis: str | None,
    cache_key: str,
):
    del cache_key
    cobertura = load_cobertura(Path(path_cobertura) if path_cobertura and Path(path_cobertura).exists() else None)
    base = load_base(Path(path_base) if path_base and Path(path_base).exists() else None)
    gis_path = Path(path_gis) if path_gis and Path(path_gis).exists() else None
    gis = load_talhoes_gis(gis_path)
    return cobertura, base, gis


with st.sidebar:
    section("Fontes de dados")
    modo = st.radio(
        "Origem",
        ["PC — caminhos locais", "Nuvem — upload"],
        label_visibility="collapsed",
    )

    path_cobertura = path_base = path_gis = None
    cache_key = "default"

    if modo.startswith("PC"):
        path_cobertura = st.text_input("Cobertura (.xlsx)", str(PATH_COBERTURA))
        path_base = st.text_input("Base / Subsolagem (.xlsx)", str(PATH_BASE))
        path_gis = st.text_input("Cadastro GIS (.kml)", str(PATH_KML))
        cache_key = f"{path_cobertura}|{path_base}|{path_gis}"
        if not Path(path_cobertura).exists():
            st.caption("Arquivos locais não encontrados — carregando amostra demo.")
    else:
        st.caption("Envie os arquivos e clique em Recarregar.")
        up_cobertura = st.file_uploader("Cobertura", type=["xlsx"], label_visibility="collapsed")
        up_base = st.file_uploader("Base / Subsolagem", type=["xlsx"], label_visibility="collapsed")
        up_gis = st.file_uploader("GIS (.kml / .geojson)", type=["kml", "geojson"], label_visibility="collapsed")
        if st.button("Recarregar dados", use_container_width=True):
            st.cache_data.clear()
        path_cobertura = str(_salvar_upload(up_cobertura, ".xlsx")) if up_cobertura else None
        path_base = str(_salvar_upload(up_base, ".xlsx")) if up_base else None
        if up_gis:
            ext = Path(up_gis.name).suffix.lower() or ".kml"
            path_gis = str(_salvar_upload(up_gis, ext))
        cache_key = "|".join(f"{u.name}:{u.size}" if u else "-" for u in (up_cobertura, up_base, up_gis))

    section("Operação")
    servico = st.selectbox(
        "Serviço",
        options=["cobertura", "base_subsolagem"],
        format_func=lambda x: "Adubação de Cobertura" if x == "cobertura" else "Base / Subsolagem",
    )

try:
    cobertura, base, gis = carregar_dados(path_cobertura, path_base, path_gis, cache_key)
except Exception as exc:
    st.error(f"Erro ao carregar dados: {exc}")
    st.stop()

hortos = ["Todos"] + listar_hortos(cobertura, base)
with st.sidebar:
    horto_filtro = st.selectbox("Horto / retiro", hortos)

operacional = cobertura if servico == "cobertura" else base
mapa = cruzar_servico_gis(
    gis, operacional, servico, horto=None if horto_filtro == "Todos" else horto_filtro
)
kpis = resumo_kpis(mapa)
render_kpis(kpis)

tab_mapa, tab_tabela, tab_npk, tab_dados = st.tabs(
    ["Mapa operacional", "Talhões", "Calculadora NPK", "Dados brutos"]
)

with tab_mapa:
    section("Mapa por talhão")
    render_legend()

    mapa_plot = mapa.to_crs("EPSG:4326").copy()
    mapa_plot["label"] = mapa_plot.apply(
        lambda r: (
            f"Talhão {r['talhao']} | {r['status']} | "
            f"Feito: {r['area_feita_ha']:.1f} ha | Restante: {r['area_restante_ha']:.1f} ha"
        ),
        axis=1,
    )
    mapa_plot["fill_rgb"] = mapa_plot["cor"].map(hex_to_rgba)

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
            "mapStyle": "dark",
            "layers": [
                {
                    "@@type": "GeoJsonLayer",
                    "data": geojson,
                    "pickable": True,
                    "stroked": True,
                    "filled": True,
                    "getFillColor": "properties.fillColor",
                    "getLineColor": [120, 160, 110, 180],
                    "lineWidthMinPixels": 1,
                    "opacity": 0.85,
                }
            ],
            "tooltip": {"text": "{label}\nProgresso: {pct}%"},
        },
        use_container_width=True,
    )

    section("Resumo por horto")
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
    dark_table(por_horto, height=260)

with tab_tabela:
    section("Status por talhão")
    cols_show = [
        "talhao", "classe", "horto", "status", "area_ha",
        "area_feita_ha", "area_restante_ha", "pct_concluido", "fertilizante",
    ]
    tabela = mapa[[c for c in cols_show if c in mapa.columns]].sort_values(["status", "talhao"]).copy()
    tabela["pct_concluido"] = tabela["pct_concluido"].round(1)
    for col in ("area_ha", "area_feita_ha", "area_restante_ha"):
        if col in tabela.columns:
            tabela[col] = tabela[col].round(2)
    dark_table(tabela, height=480)
    st.download_button(
        "Exportar CSV",
        tabela.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"adubacao_{servico}_2026.csv",
        mime="text/csv",
        use_container_width=True,
    )

with tab_npk:
    section("Calculadora de nutrientes")
    st.caption("Fórmula 14-14-10 = % de N, P₂O₅ e K₂O em peso · dosagem em kg/ha · área em ha")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        formula_in = st.text_input("Fertilizante / fórmula", "Sulfammo 10-05-18")
    with col_b:
        dosagem_in = st.number_input("Dosagem (kg/ha)", min_value=0.0, value=200.0, step=10.0)
    with col_c:
        area_in = st.number_input("Área (ha)", min_value=0.0, value=50.0, step=1.0)

    if st.button("Calcular NPK", use_container_width=False):
        try:
            parsed = parse_formula(formula_in)
            result = calcular_nutrientes(formula_in, dosagem_in, area_in)
            st.success(f"N {parsed.n}% · P₂O₅ {parsed.p2o5}% · K₂O {parsed.k2o}%")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("N (kg/ha)", f"{result.n_kg_ha:.2f}")
            m2.metric("P₂O₅ (kg/ha)", f"{result.p2o5_kg_ha:.2f}")
            m3.metric("K₂O (kg/ha)", f"{result.k2o_kg_ha:.2f}")
            m4.metric("Adubo total (kg)", f"{result.adubo_total_kg:,.0f}")
        except ValueError as err:
            st.error(str(err))

    section("Nutrientes aplicados — planilha")
    ops_npk = enriquecer_npk(
        operacional if horto_filtro == "Todos" else operacional[operacional["horto"] == horto_filtro]
    )
    cols_npk = [
        c for c in [
            "horto", "talhao", "fertilizante", "ha_floresta", "area_ha",
            "dosagem_realizada", "dosagem_kg_ha", "n_total_kg", "p2o5_total_kg", "k2o_total_kg", "total_kg",
        ] if c in ops_npk.columns
    ]
    dark_table(ops_npk[cols_npk].dropna(how="all", subset=["n_total_kg"]), height=320)

with tab_dados:
    section("Cobertura — 6 hortos")
    dark_table(cobertura.head(100), height=280)
    section("Base / Subsolagem")
    dark_table(base.head(100), height=280)
    section("Cadastro GIS")
    dark_table(gis.drop(columns="geometry").head(100), height=280)
