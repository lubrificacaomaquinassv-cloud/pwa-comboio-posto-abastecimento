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
from etl import CORES, cruzar, kpis, load_base, load_cobertura, load_gis
from npk import calcular
from ui import css, hero, kpis as show_kpis, tabela

st.set_page_config(page_title=TITULO, page_icon="🌲", layout="wide")
css()
hero(TITULO, f"{SUBTITULO} · build {BUILD}")


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
    st = p.stat()
    return f"{st.st_size}:{int(st.st_mtime_ns)}"


@st.cache_data(show_spinner="Carregando planilhas e KML…")
def carregar(pc: str | None, pb: str | None, pk: str | None, fpc: str, fpb: str, fpk: str):
    del fpc, fpb, fpk  # chave de cache — conteúdo/timestamp dos arquivos
    return (
        load_cobertura(Path(pc) if pc else None),
        load_base(Path(pb) if pb else None),
        load_gis(Path(pk) if pk else None),
    )


def mapa(gdf):
    g = gdf.to_crs(4326).copy()
    c = g.geometry.union_all().centroid
    fmap = folium.Map(location=[c.y, c.x], zoom_start=11, tiles="CartoDB dark_matter", control_scale=True)
    geojson = json.loads(g.to_json())
    for feat, (_, row) in zip(geojson["features"], g.iterrows()):
        feat["properties"]["cor"] = row.get("cor", CORES["sem_dado"])
        feat["properties"]["tip"] = (
            f"Talhão {row.talhao} | {row.status} | "
            f"{row.area_feita:.1f} ha feito | {row.area_rest:.1f} ha restante"
        )

    folium.GeoJson(
        geojson,
        style_function=lambda f: {
            "fillColor": f["properties"].get("cor", CORES["sem_dado"]),
            "color": "#ffffff",
            "weight": 1,
            "fillOpacity": 0.72,
        },
        tooltip=folium.GeoJsonTooltip(fields=["tip"], labels=False),
    ).add_to(fmap)
    return fmap


with st.sidebar:
    st.markdown("### Dados")
    st.caption("Nuvem: envie os 3 arquivos · PC: usa caminhos D:\\ automaticamente")

    up_c = st.file_uploader("Cobertura (.xlsx)", type=["xlsx"])
    up_b = st.file_uploader("Base (.xlsx)", type=["xlsx"])
    up_k = st.file_uploader("KML", type=["kml"])

    pc = _salvar(up_c, "cobertura.xlsx") or (str(PATH_COBERTURA) if PATH_COBERTURA.exists() else None)
    pb = _salvar(up_b, "base.xlsx") or (str(PATH_BASE) if PATH_BASE.exists() else None)
    pk = _salvar(up_k, "fazenda.kml") or (str(PATH_KML) if PATH_KML.exists() else None)

    servico = st.selectbox("Serviço", ["cobertura", "base"], format_func=lambda x: "Cobertura" if x == "cobertura" else "Base/Subsolagem")

try:
    cob, base, gis = carregar(pc, pb, pk, _fp(pc), _fp(pb), _fp(pk))
    fonte = "upload" if any([up_c, up_b, up_k]) else ("PC D:\\" if PATH_KML.exists() else "demo")
    st.sidebar.success(
        f"Fonte: {fonte} · GIS: {len(gis)} talhões · "
        f"Cobertura: {cob['talhao'].nunique()} · Base: {len(base)} linhas"
    )
except Exception as e:
    st.error(f"Erro ao carregar: {e}")
    st.stop()

mapa_df = cruzar(gis, pd.concat([cob, base]), servico)
show_kpis(kpis(mapa_df))

st.caption("Mapa: região Igarapava/Delta (divisa SP/MG) — localização correta da Fazenda Santa Virgínia.")

tab1, tab2, tab3 = st.tabs(["Mapa", "Talhões", "NPK"])

with tab1:
    st.markdown("🟢 Concluído · 🔴 Pendente · ⚪ Sem registro na planilha")
    components.html(mapa(mapa_df)._repr_html_(), height=540)

with tab2:
    cols = [c for c in ["talhao", "status", "area_ha", "area_feita", "area_rest", "horto"] if c in mapa_df.columns]
    tabela(mapa_df[cols].sort_values(["status", "talhao"]), h=500)

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
