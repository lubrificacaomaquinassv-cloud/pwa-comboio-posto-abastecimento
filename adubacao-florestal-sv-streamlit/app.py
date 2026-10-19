"""
Painel de Adubacao Florestal - Fazenda Santa Vergínia
Repositorio: lubrificacaomaquinassv-cloud/adubacao-florestal-sv

Fluxo:
  1) Upload do KML (mapa) + planilhas de Cobertura e Base/Subsolagem
  2) Leitura automatica dos PDFs de retiro (pasta mapas_retiro/) para o
     de-para talhao -> retiro
  3) Parsing e calculo de NPK aplicado
  4) Cruzamento com o cadastro geoespacial de talhoes
  5) Visualizacao: mapa, KPIs, tabelas por retiro, calculadora interativa
  6) Botao opcional para gravar no Supabase (fonte oficial)
"""
import os

import numpy as np
import pandas as pd
import streamlit as st

from ingestion.kml_parser import ler_talhoes_kml, talhoes_com_codigo_ambiguo
from ingestion.excel_parser import ler_adubacao_cobertura, ler_adubacao_base
from ingestion.pdf_retiro_parser import ler_pasta_pdfs_retiro
from npk_calculator import aplicar_calculadora_no_df, calcular_npk_aplicado, dose_por_ha
from painel_terceiros import carregar_terceiros, render_aba_terceiros
from db.supabase_io import (
    carregar_base,
    carregar_cobertura,
    carregar_talhoes_geom,
    ficha_talhao_dict,
    gravar_base,
    gravar_cobertura,
    gravar_talhoes,
    ultimo_cobertura_por_talhao,
)
from mapa_adubacao import render_mapa_adubacao

PAINEL_BUILD = "2026.10.19-gis-dim-talhoes"

st.set_page_config(page_title="Adubação Florestal - Santa Vergínia", layout="wide", initial_sidebar_state="expanded")

# ===================================================================
# Tema escuro (mesmo padrao visual dos outros paineis Santa Vergínia)
# ===================================================================
st.markdown("""
<style>
    .stApp { background-color: #0b1220; color: #e8e6da; }
    section[data-testid="stSidebar"] { background-color: #0f1a2e; }
    h1, h2, h3 { color: #e8c976 !important; }
    [data-testid="stMetricValue"] { color: #e8c976; }
    [data-testid="stMetricLabel"] { color: #cfd3dc; }
    .sv-banner {
        background: linear-gradient(135deg, #0a1730 0%, #142850 100%);
        border: 1px solid #c9a227;
        border-radius: 10px;
        padding: 22px 28px;
        margin-bottom: 22px;
    }
    .sv-banner h1 {
        margin: 0; font-size: 30px; letter-spacing: 0.5px;
        color: #f2d98a !important;
    }
    .sv-banner p {
        margin: 4px 0 0 0; color: #b9c2d0; font-size: 14px;
    }
    div[data-baseweb="tab-list"] { border-bottom: 1px solid #2a3550; }
    button[data-baseweb="tab"] { color: #cfd3dc; }
    button[data-baseweb="tab"][aria-selected="true"] { color: #e8c976 !important; }
</style>
""", unsafe_allow_html=True)

# Logo da empresa (aceita assets/, raiz, ou nome com sufixo de upload duplicado)
_candidatos_logo = [
    os.path.join(os.path.dirname(__file__), "assets", "logo_santa_verginia.png"),
    os.path.join(os.path.dirname(__file__), "logo_santa_verginia.png"),
    os.path.join(os.path.dirname(__file__), "logo_santa_verginia (1).png"),
]
_logo_path = next((p for p in _candidatos_logo if os.path.exists(p)), None)
if _logo_path:
    st.sidebar.image(_logo_path, use_container_width=True)


# -----------------------------------------------------------------
# Conexao Supabase (opcional - so ativa se as credenciais existirem)
# -----------------------------------------------------------------
def get_engine():
    """Cria a conexao SQLAlchemy com o Supabase via Transaction Pooler,
    lendo as credenciais de st.secrets ou variaveis de ambiente.
    Retorna None se as credenciais nao estiverem configuradas
    (o painel continua funcionando 100% a partir dos uploads)."""
    try:
        from sqlalchemy import create_engine
        url = st.secrets.get("SUPABASE_DB_URL") or os.environ.get("SUPABASE_DB_URL")
        if not url:
            return None
        return create_engine(url)
    except Exception:
        return None


# -----------------------------------------------------------------
# Sidebar - fonte (Supabase ou planilhas)
# -----------------------------------------------------------------
_engine = get_engine()
_opcoes_fonte = ["☁️ Supabase (oficial)", "📂 Planilhas (Excel)"]
_idx_fonte = 0 if _engine else 1
st.sidebar.title("📂 Fontes de dados")
fonte_dados = st.sidebar.radio(
    "Origem dos lançamentos",
    _opcoes_fonte,
    index=_idx_fonte,
    help="Produção: dados lidos do Supabase. Desenvolvimento: upload das planilhas.",
)
_usa_supabase = fonte_dados.startswith("☁️")

if _usa_supabase and _engine is None:
    st.error(
        "Modo Supabase selecionado, mas `SUPABASE_DB_URL` não está configurado "
        "(Secrets do Streamlit Cloud ou `.streamlit/secrets.toml`)."
    )
    st.stop()

arq_kml = st.sidebar.file_uploader("Mapa da fazenda (KML)", type=["kml"])
arq_cobertura = None
arq_base = None
if not _usa_supabase:
    arq_cobertura = st.sidebar.file_uploader("Adubação de Cobertura (xlsx)", type=["xlsx"])
    arq_base = st.sidebar.file_uploader("Adubação de Base / Subsolagem (xlsx)", type=["xlsx"])
else:
    st.sidebar.caption(
        "Cobertura e base vêm do Supabase. O **mapa GIS** usa `public.dim_talhoes` "
        "(Apontamento) ou `dim_talhao_florestal` — **KML não é obrigatório** se já houver polígonos no banco."
    )

st.sidebar.markdown("---")
st.sidebar.subheader("Operações Terceiros / Drone")
arq_terceiros = st.sidebar.file_uploader(
    "Planilhas COSER / F-ORION / EcoAero (xlsx, múltiplos)",
    type=["xlsx"],
    accept_multiple_files=True,
)
_pasta_terceiros_default = os.path.join(
    os.path.dirname(__file__), "dados_terceiros"
)
_usar_pasta_local = st.sidebar.checkbox(
    "Carregar planilhas terceiros (COSER / F-ORION / EcoAero)",
    value=os.path.isdir(_pasta_terceiros_default),
    help="Já vem com as planilhas da pasta dados_terceiros/ no servidor.",
)
_kml_default = os.path.join(os.path.dirname(__file__), "dados", "fazenda_santa_virginia_completo.kml")
_tem_kml = bool(arq_kml) or os.path.isfile(_kml_default)

st.sidebar.markdown("---")
st.sidebar.caption(
    "**Modo Terceiros/Drone:** abre direto (KML + planilhas já no servidor).\n\n"
    "**Modo NPK completo:** suba também Cobertura + Base (xlsx)."
)

# -----------------------------------------------------------------
# Ingestao (cache para nao reprocessar a cada interacao do usuario)
# -----------------------------------------------------------------
@st.cache_data(show_spinner="Lendo o mapa (KML)...")
def _carregar_kml(bytes_kml):
    caminho_tmp = "/tmp/_mapa_fazenda.kml"
    with open(caminho_tmp, "wb") as f:
        f.write(bytes_kml)
    return ler_talhoes_kml(caminho_tmp)


@st.cache_data(show_spinner="Lendo a planilha de Cobertura...")
def _carregar_cobertura(bytes_xlsx):
    caminho_tmp = "/tmp/_cobertura.xlsx"
    with open(caminho_tmp, "wb") as f:
        f.write(bytes_xlsx)
    return ler_adubacao_cobertura(caminho_tmp)


@st.cache_data(show_spinner="Lendo a planilha de Base/Subsolagem...")
def _carregar_base(bytes_xlsx):
    caminho_tmp = "/tmp/_base.xlsx"
    with open(caminho_tmp, "wb") as f:
        f.write(bytes_xlsx)
    return ler_adubacao_base(caminho_tmp)


@st.cache_data(show_spinner="Lendo os mapas de retiro (PDF)...")
def _carregar_de_para_pdf():
    pasta_mapas = os.path.join(os.path.dirname(__file__), "mapas_retiro")
    if not os.path.isdir(pasta_mapas):
        return pd.DataFrame(columns=["talhao", "retiro", "arquivo_origem"])
    return ler_pasta_pdfs_retiro(pasta_mapas)


def _bytes_kml() -> bytes | None:
    if arq_kml:
        return arq_kml.getvalue()
    if os.path.isfile(_kml_default):
        with open(_kml_default, "rb") as f:
            return f.read()
    return None


def _carregar_df_terceiros() -> pd.DataFrame:
    if arq_terceiros:
        return carregar_terceiros(arq_terceiros)
    if _usar_pasta_local and os.path.isdir(_pasta_terceiros_default):
        return carregar_terceiros(_pasta_terceiros_default)
    return pd.DataFrame()


# -----------------------------------------------------------------
# Carregar cobertura/base (Supabase ou upload)
# -----------------------------------------------------------------
df_cobertura = pd.DataFrame()
df_base = pd.DataFrame()
gdf_talhoes = None
_fonte_gis = None

def _preferencia_gis() -> str | None:
    try:
        return st.secrets.get("SUPABASE_GIS_TABLE") or os.environ.get("SUPABASE_GIS_TABLE")
    except Exception:
        return os.environ.get("SUPABASE_GIS_TABLE")


if _usa_supabase:
    try:
        df_cobertura = carregar_cobertura(_engine)
        df_base = carregar_base(_engine)
        gdf_db, _fonte_gis = carregar_talhoes_geom(_engine, preferir_tabela=_preferencia_gis())
        if gdf_db is not None and len(gdf_db):
            gdf_talhoes = gdf_db
            st.sidebar.success(f"🗺️ GIS Supabase: **{_fonte_gis}** ({len(gdf_db)} polígonos)")
        elif _bytes_kml():
            gdf_talhoes = _carregar_kml(_bytes_kml())
            _fonte_gis = "KML enviado na sessão"
        df_cobertura = aplicar_calculadora_no_df(df_cobertura, "fertilizante", "kg_total", "area_total_ha")
        if not df_base.empty:
            df_base = aplicar_calculadora_no_df(df_base, "fertilizante", "kg_total", "area_plantada_ha")
    except Exception as e:
        st.error(f"Erro ao ler Supabase: {e}")
        st.exception(e)
        st.stop()
    if df_cobertura.empty:
        st.warning(
            "Nenhum registro em `fato_adubacao_cobertura`. "
            "Execute `sql/003_schema_adubacao_florestal.sql` e rode "
            "`python scripts/sync_excel_to_supabase.py` com suas planilhas (DADOS_PAINEL)."
        )
        st.stop()
    if gdf_talhoes is None:
        st.error("Nenhuma geometria encontrada no Supabase.")
        st.markdown(
            """
Verifique no **Table Editor** se existe **`public.dim_talhoes`** com coluna de geometria (PostGIS)
ou a tabela **`dim_talhao_florestal`**. O painel lê automaticamente o GIS do Apontamento de Campo.

Opcional: envie o KML na barra lateral **uma vez** e use a aba **Supabase → Sincronizar** para gravar.
            """
        )
        st.stop()

_modo_completo = _usa_supabase or bool(arq_kml and arq_cobertura and arq_base)

# -----------------------------------------------------------------
# Modo Terceiros/Drone — KML + planilhas já embutidos (sem upload)
# -----------------------------------------------------------------
if not _modo_completo:
    if not _tem_kml:
        st.markdown(
            '<div class="sv-banner"><h1>🌳 Painel de Adubação Florestal</h1>'
            '<p>Fazenda Santa Vergínia — Terceiros/Drone · Cobertura · Base · NPK</p></div>',
            unsafe_allow_html=True,
        )
        st.error("Mapa KML não encontrado no servidor.")
        if _engine is None:
            st.warning(
                "**Versão antiga ou Secrets ausentes:** este deploy ainda não tem `SUPABASE_DB_URL` "
                f"(build esperado: **{PAINEL_BUILD}**). Veja `COMO_ATUALIZAR_PAINEL_ONLINE.md`."
            )
        st.markdown(
            f"""
**Para o painel oficial (Supabase + mapa Esri):**

1. Publicar no GitHub o código com build **`{PAINEL_BUILD}`** (repo `adubacao-florestal-sv` ou pasta `adubacao-florestal-sv-streamlit` no PWA).
2. Streamlit Cloud → **Secrets** → `SUPABASE_DB_URL` → **Redeploy**.
3. Supabase → executar `sql/003_schema_adubacao_florestal.sql`.
4. No PC → `powershell -File scripts\\CARGA_DADOS_PAINEL.ps1` (pasta `Desktop\\DADOS_PAINEL`).

**Enquanto isso (modo manual):** envie o KML **`fazenda_santa_virginia_completo.kml`** na barra lateral
(e planilhas Cobertura + Base se quiser o painel completo).
            """
        )
        st.stop()

    try:
        gdf_talhoes = _carregar_kml(_bytes_kml())
        gdf_validos = gdf_talhoes[gdf_talhoes["talhao"].notna()].copy()
        df_terceiros = _carregar_df_terceiros()
    except Exception as e:
        st.error(f"Erro ao processar KML / terceiros: {e}")
        st.exception(e)
        st.stop()

    st.markdown(
        '<div class="sv-banner"><h1>🚁 Operações Terceiros / Drone</h1>'
        '<p>Fazenda Santa Vergínia — COSER · F-ORION · EcoAero</p></div>',
        unsafe_allow_html=True,
    )
    st.success("Mapa KML e planilhas de terceiros carregados automaticamente.")
    st.info(
        "Para ver também **Cobertura**, **Base/Subsolagem** e **Calculadora NPK**, "
        "suba na barra lateral as planilhas de Adubação de Cobertura e Base (xlsx)."
    )
    render_aba_terceiros(df_terceiros, gdf_talhoes=gdf_validos, get_engine=get_engine)
    st.stop()

if not _usa_supabase:
    try:
        gdf_talhoes = _carregar_kml(arq_kml.getvalue())
        df_cobertura = _carregar_cobertura(arq_cobertura.getvalue())
        df_base = _carregar_base(arq_base.getvalue())
    except Exception as e:
        st.error(f"Erro ao processar os arquivos: {e}")
        st.exception(e)
        st.stop()
    df_cobertura = aplicar_calculadora_no_df(df_cobertura, "fertilizante", "kg_total", "area_total_ha")
    df_base = aplicar_calculadora_no_df(df_base, "fertilizante", "kg_total", "area_plantada_ha")

try:
    de_para_pdf = _carregar_de_para_pdf()
except Exception as e:
    st.error(f"Erro ao ler PDFs de retiro: {e}")
    st.stop()

# -----------------------------------------------------------------
# Cruzamento: talhao (KML) x retiro (PDF/planilha) x cobertura x base
# -----------------------------------------------------------------
gdf_validos = gdf_talhoes[gdf_talhoes["talhao"].notna()].copy()

de_para_planilhas = pd.concat([
    df_cobertura[["talhao", "retiro"]],
    df_base[["talhao", "retiro"]],
]).drop_duplicates(subset="talhao", keep="first")

de_para_retiro = pd.concat([
    de_para_pdf[["talhao", "retiro"]] if len(de_para_pdf) else pd.DataFrame(columns=["talhao", "retiro"]),
    de_para_planilhas,
]).drop_duplicates(subset="talhao", keep="first")

gdf_validos = gdf_validos.merge(de_para_retiro, on="talhao", how="left")

area_cobertura_talhao = df_cobertura.groupby("talhao").agg(
    area_adubada_cobertura_ha=("area_total_ha", "sum"),
    kg_total_cobertura=("kg_total", "sum"),
    n_kg_cobertura=("N_kg", "sum"),
    p2o5_kg_cobertura=("P2O5_kg", "sum"),
    k2o_kg_cobertura=("K2O_kg", "sum"),
).reset_index()

area_base_feito = df_base[df_base["status"] == "Subsolado/Adubado"].groupby("talhao").agg(
    area_subsolada_ha=("area_plantada_ha", "sum"),
    kg_total_base=("kg_total", "sum"),
).reset_index()

painel = gdf_validos.merge(area_cobertura_talhao, on="talhao", how="left")
painel = painel.merge(area_base_feito, on="talhao", how="left")

for col in ["area_adubada_cobertura_ha", "kg_total_cobertura", "n_kg_cobertura",
            "p2o5_kg_cobertura", "k2o_kg_cobertura", "area_subsolada_ha", "kg_total_base"]:
    painel[col] = painel[col].fillna(0)

painel["pct_cobertura"] = (painel["area_adubada_cobertura_ha"] / painel["area_ha_kml"] * 100).round(1)
painel["pct_base"] = (painel["area_subsolada_ha"] / painel["area_ha_kml"] * 100).round(1)

# divisao segura (evita divisao por zero sem usar pd.NA, que quebra .round())
painel["n_kg_ha_cobertura"] = painel["n_kg_cobertura"] / painel["area_adubada_cobertura_ha"].replace(0, np.nan)
painel["n_kg_ha_cobertura"] = painel["n_kg_ha_cobertura"].round(2)


def status_execucao(pct):
    if pd.isna(pct) or pct == 0:
        return "Não iniciado"
    if pct >= 99:
        return "Completo"
    return "Parcial"


painel["status_cobertura"] = painel["pct_cobertura"].apply(status_execucao)
painel["status_base"] = painel["pct_base"].apply(status_execucao)
painel["alerta_sequencia"] = (painel["pct_cobertura"] > 0) & (painel["pct_base"] == 0)

# -----------------------------------------------------------------
# Sidebar - filtros
# -----------------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.title("🔍 Filtros")
retiros_disponiveis = sorted([r for r in painel["retiro"].dropna().unique()])
filtro_retiro = st.sidebar.multiselect("Retiro", options=retiros_disponiveis, default=retiros_disponiveis)
filtro_classe = st.sidebar.multiselect(
    "Classe", options=sorted(painel["classe"].dropna().unique()),
    default=sorted(painel["classe"].dropna().unique())
)

painel_f = painel[painel["retiro"].isin(filtro_retiro) & painel["classe"].isin(filtro_classe)]

# -----------------------------------------------------------------
# Corpo principal
# -----------------------------------------------------------------
st.markdown(
    '<div class="sv-banner"><h1>🌳 Painel de Adubação Florestal</h1>'
    '<p>Fazenda Santa Vergínia — Cobertura · Base/Subsolagem · Calculadora NPK</p></div>',
    unsafe_allow_html=True,
)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Área mapeada (filtro)", f"{painel_f['area_ha_kml'].sum():,.0f} ha")
if painel_f["area_ha_kml"].sum() > 0:
    col2.metric("% Cobertura aplicada", f"{(painel_f['area_adubada_cobertura_ha'].sum() / painel_f['area_ha_kml'].sum() * 100):.1f}%")
    col3.metric("% Base/Subsolagem", f"{(painel_f['area_subsolada_ha'].sum() / painel_f['area_ha_kml'].sum() * 100):.1f}%")
else:
    col2.metric("% Cobertura aplicada", "—")
    col3.metric("% Base/Subsolagem", "—")
col4.metric("Talhões com alerta de sequência", int(painel_f["alerta_sequencia"].sum()))

aba_mapa, aba_cobertura, aba_base, aba_calc, aba_terceiros, aba_supabase = st.tabs(
    ["🗺️ Mapa", "🌾 Cobertura", "🚜 Base/Subsolagem", "🧮 Calculadora NPK",
     "🚁 Terceiros / Drone", "☁️ Supabase"]
)

# --- Mapa ---
with aba_mapa:
    if painel_f.empty:
        st.warning("Nenhum talhão corresponde aos filtros selecionados.")
    else:
        ambiguos = talhoes_com_codigo_ambiguo(gdf_talhoes)
        if len(ambiguos) > 0:
            with st.expander(
                f"⚠️ {ambiguos['talhao'].nunique()} códigos de talhão aparecem em mais de uma classe (verificar com o coordenador)"
            ):
                st.caption(
                    "O cruzamento abaixo usa apenas o número do talhão. Para estes códigos, "
                    "existe mais de um polígono no KML com o mesmo número em classes diferentes "
                    "(ex: Silvicultura e Silvipastoril) — o valor de área/adubação pode estar "
                    "sendo atribuído à classe errada até isso ser confirmado."
                )
                st.dataframe(ambiguos, use_container_width=True)

        ult_cob = ultimo_cobertura_por_talhao(df_cobertura)
        gdf_mapa = painel_f.merge(
            ult_cob[
                [
                    "talhao",
                    "kg_total",
                    "area_floresta_ha",
                    "dose_recomendada_ha",
                    "realizado_ha",
                    "fertilizante",
                    "data",
                    "operador",
                    "area_total_ha",
                ]
            ].rename(
                columns={
                    "kg_total": "kg_total_map",
                    "area_floresta_ha": "area_floresta_map",
                }
            ),
            on="talhao",
            how="left",
        )
        gdf_mapa["kg_total_map"] = gdf_mapa["kg_total_map"].fillna(0)

        if "talhao_selecionado" not in st.session_state:
            st.session_state.talhao_selecionado = None

        ficha = ficha_talhao_dict(ult_cob, st.session_state.talhao_selecionado)
        try:
            clicado = render_mapa_adubacao(gdf_mapa, ficha, key_suffix="_prod")
            if clicado and clicado != st.session_state.talhao_selecionado:
                st.session_state.talhao_selecionado = str(clicado).strip().upper()
                st.rerun()
        except Exception as e:
            st.error(f"Erro ao renderizar o mapa: {e}")
            st.exception(e)

# --- Cobertura ---
with aba_cobertura:
    resumo_retiro_cob = painel_f.groupby("retiro").agg(
        area_total_ha=("area_ha_kml", "sum"),
        area_adubada_ha=("area_adubada_cobertura_ha", "sum"),
        talhoes_nao_iniciados=("status_cobertura", lambda s: (s == "Não iniciado").sum()),
    ).reset_index()
    resumo_retiro_cob["pct_execucao"] = (resumo_retiro_cob["area_adubada_ha"] / resumo_retiro_cob["area_total_ha"] * 100).round(1)
    resumo_retiro_cob = resumo_retiro_cob.sort_values("pct_execucao")

    st.subheader("Execução por retiro (Cobertura)")
    st.dataframe(resumo_retiro_cob, use_container_width=True)

    st.subheader("Detalhe por talhão")
    st.dataframe(
        painel_f[["talhao", "retiro", "classe", "area_ha_kml", "area_adubada_cobertura_ha",
                  "pct_cobertura", "status_cobertura", "n_kg_ha_cobertura"]].sort_values("pct_cobertura"),
        use_container_width=True,
    )

    st.subheader("Lançamentos brutos (planilha de Cobertura)")
    st.dataframe(df_cobertura, use_container_width=True)

# --- Base/Subsolagem ---
with aba_base:
    resumo_retiro_base = painel_f.groupby("retiro").agg(
        area_total_ha=("area_ha_kml", "sum"),
        area_subsolada_ha=("area_subsolada_ha", "sum"),
    ).reset_index()
    resumo_retiro_base["pct_execucao"] = (resumo_retiro_base["area_subsolada_ha"] / resumo_retiro_base["area_total_ha"] * 100).round(1)
    resumo_retiro_base = resumo_retiro_base.sort_values("pct_execucao")

    st.subheader("Execução por retiro (Base/Subsolagem)")
    st.dataframe(resumo_retiro_base, use_container_width=True)

    st.subheader("Pendências (\"A subsolar\")")
    st.dataframe(df_base[df_base["status"] == "A subsolar"], use_container_width=True)

    st.subheader("Já subsolado/adubado")
    st.dataframe(df_base[df_base["status"] == "Subsolado/Adubado"], use_container_width=True)

# --- Calculadora NPK ---
with aba_calc:
    st.subheader("Calculadora de NPK aplicado")
    c1, c2, c3, c4 = st.columns(4)
    kg_input = c1.number_input("Quantidade de adubo (kg)", min_value=0.0, value=239.0, step=10.0)
    n_input = c2.number_input("% N", min_value=0, max_value=100, value=14)
    p_input = c3.number_input("% P₂O₅", min_value=0, max_value=100, value=14)
    k_input = c4.number_input("% K₂O", min_value=0, max_value=100, value=10)
    area_input = st.number_input("Área aplicada (ha) — opcional, para calcular dose/ha", min_value=0.0, value=0.0, step=1.0)

    if st.button("Calcular"):
        resultado = calcular_npk_aplicado(kg_input, n_input, p_input, k_input)
        st.success(
            f"N: {resultado['N_kg']} kg  |  P₂O₅: {resultado['P2O5_kg']} kg  |  K₂O: {resultado['K2O_kg']} kg"
        )
        if area_input > 0:
            dose = dose_por_ha(kg_input, area_input, n_input, p_input, k_input)
            st.info(
                f"Dose por hectare — N: {dose['N_kg_ha']} kg/ha | "
                f"P₂O₅: {dose['P2O5_kg_ha']} kg/ha | K₂O: {dose['K2O_kg_ha']} kg/ha"
            )

    st.markdown("---")
    st.subheader("NPK calculado automaticamente — todos os lançamentos de Cobertura")
    st.dataframe(
        df_cobertura[["talhao", "retiro", "fertilizante", "formula_npk", "kg_total",
                      "N_kg", "P2O5_kg", "K2O_kg", "N_kg_ha", "P2O5_kg_ha", "K2O_kg_ha"]],
        use_container_width=True,
    )

    nao_identificados = df_cobertura[df_cobertura["formula_npk"] == "não identificada"]["fertilizante"].unique()
    if len(nao_identificados) > 0:
        st.warning(f"Fertilizantes sem fórmula reconhecida (cadastrar em FORMULAS_ADUBO): {list(nao_identificados)}")

# --- Terceiros / Drone ---
with aba_terceiros:
    try:
        df_terceiros = _carregar_df_terceiros()
    except Exception as e:
        st.error(f"Erro ao ler planilhas de terceiros: {e}")
        st.exception(e)
        df_terceiros = pd.DataFrame()
    render_aba_terceiros(df_terceiros, gdf_talhoes=gdf_validos, get_engine=get_engine)

# --- Supabase ---
with aba_supabase:
    st.subheader("Gravar no Supabase")
    engine = get_engine()
    if engine is None:
        st.warning(
            "Conexão com Supabase não configurada. Defina `SUPABASE_DB_URL` em `.streamlit/secrets.toml` "
            "(local) ou nos Secrets do Streamlit Cloud (produção) para habilitar a gravação."
        )
        st.code(
            'SUPABASE_DB_URL = "postgresql+psycopg://postgres.<ref>:<senha>@'
            'aws-1-sa-east-1.pooler.supabase.com:6543/postgres"',
            language="toml",
        )
    else:
        st.success("Conexão com Supabase disponível.")
        st.caption("Execute `sql/003_schema_adubacao_florestal.sql` no Supabase antes da primeira carga.")
        if st.button("Sincronizar talhões + cobertura + base (upsert)"):
            try:
                n_t = gravar_talhoes(engine, gdf_validos)
                n_c = gravar_cobertura(engine, df_cobertura, arquivo_origem="painel_streamlit")
                n_b = gravar_base(engine, df_base) if not df_base.empty else 0
                st.success(f"Supabase atualizado: {n_t} talhões, {n_c} lanç. cobertura, {n_b} base.")
            except Exception as e:
                st.error(f"Erro ao gravar: {e}")
                st.info(
                    "Se a tabela ainda não existe, rode o script SQL `sql/003_schema_adubacao_florestal.sql` "
                    "ou use `python scripts/sync_excel_to_supabase.py` no PC com a pasta DADOS_PAINEL."
                )

st.sidebar.markdown("---")
st.sidebar.caption(
    f"Build **{PAINEL_BUILD}** · Supabase: {'sim' if _engine else 'não'}"
    + (f" · GIS: {_fonte_gis}" if _fonte_gis else "")
)
st.sidebar.caption(
    f"Talhões no mapa: {len(gdf_talhoes)} | Com número válido: {gdf_validos['talhao'].nunique()}\n\n"
    f"Retiro via PDF: {gdf_validos['talhao'].isin(de_para_pdf['talhao']).sum() if len(de_para_pdf) else 0} | "
    f"via planilha: {(~gdf_validos['talhao'].isin(de_para_pdf['talhao']) & gdf_validos['retiro'].notna()).sum() if len(de_para_pdf) else gdf_validos['retiro'].notna().sum()} | "
    f"sem retiro: {gdf_validos['retiro'].isna().sum()}"
)
