"""Painel separado: Terceiros / Drone — deploy com main file app_drone.py."""
import os
import tempfile

import streamlit as st
from sqlalchemy import create_engine, text

from db.secrets_helper import listar_db_urls
from ingestion.kml_parser import ler_talhoes_kml
from painel_terceiros import carregar_terceiros, render_aba_terceiros


def get_engine():
    for url in listar_db_urls():
        try:
            engine = create_engine(url, connect_args={"sslmode": "require"}, pool_pre_ping=True)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return engine
        except Exception:
            continue
    return None


st.set_page_config(page_title="Drone / Terceiros - SV", layout="wide")
st.title("Operações Terceiros / Drone")
st.caption("Separado do painel de **Adubação** (`app.py`).")

arq_kml = st.sidebar.file_uploader("Mapa KML", type=["kml"])
arq_terceiros = st.sidebar.file_uploader("Planilhas (xlsx)", type=["xlsx"], accept_multiple_files=True)

if not arq_kml:
    st.warning("Envie o KML para este app de drone/terceiros.")
    st.stop()

with tempfile.NamedTemporaryFile(suffix=".kml", delete=False) as tmp:
    tmp.write(arq_kml.getvalue())
    path_kml = tmp.name
gdf = ler_talhoes_kml(path_kml)
df = carregar_terceiros(arq_terceiros) if arq_terceiros else __import__("pandas").DataFrame()
render_aba_terceiros(df, gdf_talhoes=gdf, get_engine=get_engine)
