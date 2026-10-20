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
import re
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from ingestion.kml_parser import ler_talhoes_kml, talhoes_com_codigo_ambiguo
from ingestion.excel_parser import ler_adubacao_cobertura, ler_adubacao_base
from ingestion.pdf_retiro_parser import ler_pasta_pdfs_retiro
from npk_calculator import aplicar_calculadora_no_df, calcular_npk_aplicado, dose_por_ha
from painel_terceiros import carregar_terceiros, render_aba_terceiros
from db.carga_supabase import sync_pasta_dados_painel
from db.supabase_io import (
    carregar_base,
    carregar_cobertura,
    carregar_talhoes_geom,
    ficha_talhao_merged,
    gravar_base,
    gravar_cobertura,
    gravar_talhoes,
    ultimo_cobertura_por_talhao,
)
from db.supabase_rest import (
    carregar_base_rest,
    carregar_cobertura_rest,
    rest_disponivel,
)
from ingestion.dados_painel import descobrir_arquivos_dados_painel
from ingestion.talhao_codigo import normalizar_coluna_talhao
from mapa_adubacao import painel_ficha_talhao_streamlit, render_mapa_adubacao

PAINEL_BUILD = "2026.10.20-mapa-ficha-v3"

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
    try:
        st.sidebar.image(_logo_path, use_container_width=True)
    except TypeError:
        st.sidebar.image(_logo_path, use_column_width=True)


# -----------------------------------------------------------------
# Conexao Supabase (opcional - so ativa se as credenciais existirem)
# -----------------------------------------------------------------
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
_SECRETS_PATH = os.path.join(_APP_DIR, ".streamlit", "secrets.toml")


def _ler_supabase_db_url() -> str | None:
    """Lê URL do pooler: env, secrets.toml ao lado do app.py, depois st.secrets."""
    env = os.environ.get("SUPABASE_DB_URL")
    if env and str(env).strip():
        return str(env).strip()
    if os.path.isfile(_SECRETS_PATH):
        try:
            text = Path(_SECRETS_PATH).read_text(encoding="utf-8-sig")
            for pattern in (
                r'SUPABASE_DB_URL\s*=\s*"([^"]+)"',
                r"SUPABASE_DB_URL\s*=\s*'([^']+)'",
            ):
                m = re.search(pattern, text)
                if m and m.group(1).strip():
                    return m.group(1).strip()
        except OSError:
            pass
    try:
        v = st.secrets.get("SUPABASE_DB_URL")
        if v:
            return str(v).strip()
    except Exception:
        pass
    return None


def _normalizar_db_url(url: str) -> str | None:
    url = str(url).strip()
    if url.startswith("https://") or url.startswith("http://"):
        return None
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    if not url.startswith("postgresql+"):
        return None
    return url


def get_engine():
    """Cria a conexao SQLAlchemy com o Supabase via Transaction Pooler."""
    try:
        from sqlalchemy import create_engine

        raw = _ler_supabase_db_url()
        if not raw:
            return None
        url = _normalizar_db_url(raw)
        if not url:
            return None
        if not os.environ.get("SUPABASE_DB_URL"):
            os.environ["SUPABASE_DB_URL"] = url
        return create_engine(url)
    except Exception:
        return None


# -----------------------------------------------------------------
# Sidebar - fonte (Supabase ou planilhas)
# -----------------------------------------------------------------
_engine = get_engine()
_rest_ok = rest_disponivel()
_supabase_ok = _engine is not None or _rest_ok
_opcoes_fonte = ["☁️ Supabase (oficial)", "📂 Planilhas (Excel)"]
_idx_fonte = 0 if _supabase_ok else 1
st.sidebar.title("📂 Fontes de dados")
fonte_dados = st.sidebar.radio(
    "Origem dos lançamentos",
    _opcoes_fonte,
    index=_idx_fonte,
    help="Produção: Supabase (Postgres ou API). Planilhas: upload ou pasta dados/ no servidor.",
)
_usa_supabase = fonte_dados.startswith("☁️")

_tem_secrets_arquivo = os.path.isfile(_SECRETS_PATH)
_url_lida = _ler_supabase_db_url()

if _usa_supabase and not _supabase_ok:
    if _tem_secrets_arquivo and _url_lida:
        st.error(
            "O arquivo **secrets.toml** foi encontrado, mas a conexão Postgres falhou. "
            "Instale dependências (`pip install psycopg sqlalchemy`) e rode **PARAR_E_ABRIR_PAINEL.bat** "
            "dentro da pasta `adubacao-florestal-sv-streamlit`."
        )
    elif _tem_secrets_arquivo:
        st.error(
            "Existe `.streamlit/secrets.toml`, mas **SUPABASE_DB_URL** não foi lido. "
            "Rode **CONFIGURAR_PAINEL_LOCAL.ps1** de novo."
        )
    else:
        st.error(
            "Modo Supabase selecionado, mas faltam credenciais. Rode **CONFIGURAR_PAINEL_LOCAL.ps1** "
            "ou crie `.streamlit/secrets.toml` com `SUPABASE_DB_URL` (Transaction pooler)."
        )
    st.stop()

if _tem_secrets_arquivo and _engine is None and not _rest_ok:
    st.sidebar.error(
        "Arquivo `secrets.toml` encontrado, mas o painel **nao conectou**. "
        "Feche o localhost e rode **PARAR_E_ABRIR_PAINEL.bat**. "
        "Se persistir, rode **CONFIGURAR_PAINEL_LOCAL.ps1** de novo (URL postgresql+psycopg)."
    )
elif _engine is not None:
    st.sidebar.success("Supabase Postgres (pooler) configurado.")
elif not _tem_secrets_arquivo:
    st.sidebar.warning("Sem `.streamlit/secrets.toml` — rode CONFIGURAR_PAINEL_LOCAL.ps1")
elif not _usa_supabase and _tem_secrets_arquivo:
    st.sidebar.warning(
        "Você está em **Planilhas (Excel)**. Para mapa + adubação do banco, "
        "marque **☁️ Supabase (oficial)** acima."
    )

_dados_dir = os.path.join(os.path.dirname(__file__), "dados")
_kml_default = os.path.join(_dados_dir, "fazenda_santa_virginia_completo.kml")
_tem_dados_servidor = os.path.isdir(_dados_dir) and any(
    f.endswith((".xlsx", ".kml")) for f in os.listdir(_dados_dir)
)

arq_kml = None
arq_cobertura = None
arq_base = None
if _usa_supabase:
    st.sidebar.caption(
        "**Produção:** lançamentos e mapa vêm do **Supabase** (sem upload a cada login). "
        "Atualize os dados com `CARGA_DADOS_PAINEL.ps1`, GitHub Actions ou aba **Supabase**."
    )
    if _tem_dados_servidor:
        st.sidebar.info("Pasta `dados/` no servidor com planilhas/KML (sync → Supabase na aba ☁️).")
else:
    arq_kml = st.sidebar.file_uploader("Mapa da fazenda (KML)", type=["kml"])
    arq_cobertura = st.sidebar.file_uploader("Adubação de Cobertura (xlsx)", type=["xlsx"])
    arq_base = st.sidebar.file_uploader("Adubação de Base / Subsolagem (xlsx)", type=["xlsx"])

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


@st.cache_data(show_spinner="Lendo Cobertura (arquivo no servidor)...")
def _carregar_cobertura_arquivo(caminho: str):
    return ler_adubacao_cobertura(caminho)


@st.cache_data(show_spinner="Lendo a planilha de Base/Subsolagem...")
def _carregar_base(bytes_xlsx):
    caminho_tmp = "/tmp/_base.xlsx"
    with open(caminho_tmp, "wb") as f:
        f.write(bytes_xlsx)
    return ler_adubacao_base(caminho_tmp)


@st.cache_data(show_spinner="Lendo Base (arquivo no servidor)...")
def _carregar_base_arquivo(caminho: str):
    return ler_adubacao_base(caminho)


def _carregar_planilhas_pasta_dados() -> tuple[pd.DataFrame, pd.DataFrame, str | None]:
    """Lê cobertura/base da pasta dados/ (deploy), sem upload."""
    try:
        paths = descobrir_arquivos_dados_painel(_dados_dir)
    except FileNotFoundError:
        return pd.DataFrame(), pd.DataFrame(), None
    df_c = _carregar_cobertura_arquivo(str(paths["cobertura"]))
    df_b = pd.DataFrame()
    if paths["base"]:
        df_b = _carregar_base_arquivo(str(paths["base"]))
    return df_c, df_b, str(paths["cobertura"])


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


_fonte_planilhas = "Supabase"
_modo_servidor_local = False
if _usa_supabase:
    try:
        if _engine is not None:
            df_cobertura = carregar_cobertura(_engine)
            df_base = carregar_base(_engine)
            st.sidebar.caption("Conexão: Postgres (pooler)")
        else:
            df_cobertura = carregar_cobertura_rest()
            df_base = carregar_base_rest()
            st.sidebar.success("Conexão: Supabase API (REST)")
        gdf_db, _fonte_gis = (None, None)
        if _engine is not None:
            gdf_db, _fonte_gis = carregar_talhoes_geom(_engine, preferir_tabela=_preferencia_gis())
        if gdf_db is not None and len(gdf_db):
            gdf_talhoes = gdf_db
            st.sidebar.success(f"🗺️ GIS Supabase: **{_fonte_gis}** ({len(gdf_db)} polígonos)")
        elif _bytes_kml():
            gdf_talhoes = _carregar_kml(_bytes_kml())
            _fonte_gis = "KML em dados/ ou sessão"
        if df_cobertura.empty:
            df_disk, df_base_disk, _arq = _carregar_planilhas_pasta_dados()
            if not df_disk.empty:
                df_cobertura, df_base = df_disk, df_base_disk
                _fonte_planilhas = f"arquivos em dados/ (ainda não no Supabase)"
                st.sidebar.warning(
                    "Cobertura vazia no Supabase — lendo planilhas de **`dados/`**. "
                    "Use aba **☁️ Supabase** → *Sincronizar pasta dados/* ou rode `CARGA_DADOS_PAINEL.ps1`."
                )
        df_cobertura = aplicar_calculadora_no_df(df_cobertura, "fertilizante", "kg_total", "area_total_ha")
        if not df_base.empty:
            df_base = aplicar_calculadora_no_df(df_base, "fertilizante", "kg_total", "area_plantada_ha")
    except Exception as e:
        st.error(f"Erro ao ler Supabase: {e}")
        st.exception(e)
        st.stop()
    if df_cobertura.empty:
        st.error("Nenhum dado de cobertura no Supabase nem em `dados/` no servidor.")
        st.markdown(
            """
**Carga profissional (uma vez — o painel não perde os dados):**

1. **No seu PC** (pasta `Desktop\\DADOS_PAINEL`):
   ```powershell
   cd adubacao-florestal-sv-streamlit
   $env:SUPABASE_DB_URL = "postgresql+psycopg://postgres.SEU_REF:SUA_SENHA@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"
   powershell -ExecutionPolicy Bypass -File scripts\\CARGA_DADOS_PAINEL.ps1
   ```
2. **Ou via GitHub:** copie os xlsx/kml para `adubacao-florestal-sv-streamlit/dados/`, configure o secret **`SUPABASE_DB_URL`** em *Settings → Secrets → Actions* e rode o workflow **Sync DADOS_PAINEL → Supabase**.

Streamlit Cloud: secret **`SUPABASE_DB_URL`** + origem **☁️ Supabase (oficial)** — sem upload por sessão.
            """
        )
        st.stop()
    if gdf_talhoes is None:
        if _bytes_kml():
            gdf_talhoes = _carregar_kml(_bytes_kml())
            _fonte_gis = "KML em dados/"
        else:
            st.error("Nenhuma geometria no Supabase nem KML em `dados/`.")
            st.stop()
    st.sidebar.caption(f"Planilhas: {_fonte_planilhas}")

# Modo servidor: planilhas + KML em adubacao-florestal-sv-streamlit/dados/ (sem Supabase, sem upload)
if not _usa_supabase and df_cobertura.empty and _tem_dados_servidor:
    try:
        df_disk, df_base_disk, _ = _carregar_planilhas_pasta_dados()
        if not df_disk.empty and _bytes_kml():
            df_cobertura = aplicar_calculadora_no_df(
                df_disk, "fertilizante", "kg_total", "area_total_ha"
            )
            df_base = df_base_disk
            if not df_base.empty:
                df_base = aplicar_calculadora_no_df(
                    df_base, "fertilizante", "kg_total", "area_plantada_ha"
                )
            gdf_talhoes = _carregar_kml(_bytes_kml())
            _fonte_gis = "KML em dados/"
            _fonte_planilhas = "dados/ (servidor)"
            _modo_servidor_local = True
            st.sidebar.success("📁 Cobertura/Base/KML lidos de **`dados/`** (persistente no deploy).")
    except Exception as e:
        st.sidebar.warning(f"Não foi possível ler `dados/`: {e}")

_modo_completo = (
    (_usa_supabase and not df_cobertura.empty and gdf_talhoes is not None)
    or _modo_servidor_local
    or bool(arq_kml and arq_cobertura and arq_base)
)

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
        st.error("Mapa e dados oficiais não carregaram.")
        if _engine is None and not _rest_ok:
            st.warning(
                f"**Falta conectar ao Supabase** (build **{PAINEL_BUILD}**). "
                "No PC, rode **CONFIGURAR_PAINEL_LOCAL.ps1** ou crie `.streamlit/secrets.toml` "
                "com `SUPABASE_DB_URL` (mesma URL usada na carga DADOS_PAINEL)."
            )
            st.markdown(
                """
**No Windows (PowerShell), uma vez:**

```powershell
cd $env:USERPROFILE\\Desktop\\pwa-comboio-posto-abastecimento\\adubacao-florestal-sv-streamlit
powershell -ExecutionPolicy Bypass -File CONFIGURAR_PAINEL_LOCAL.ps1
```

Depois duplo clique em **RODAR_PAINEL_LOCAL.bat**.

Na barra lateral escolha **Supabase (oficial)** — o mapa vem do banco (`dim_talhoes`), não precisa KML no PC.
                """
            )
        elif _engine is None:
            st.warning(
                "Há chave REST, mas **falta `SUPABASE_DB_URL`** para o mapa GIS. "
                "Use **CONFIGURAR_PAINEL_LOCAL.ps1** com a URL do pooler Postgres."
            )
        else:
            st.warning(
                f"Build **{PAINEL_BUILD}**. Coloque o KML em `dados/` ou use Supabase com GIS."
            )
        st.markdown(
            "**Modo manual:** barra lateral → **Planilhas (Excel)** → envie KML + planilhas."
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
gdf_validos = normalizar_coluna_talhao(
    gdf_talhoes[gdf_talhoes["talhao"].notna()].copy()
)
df_cobertura = normalizar_coluna_talhao(df_cobertura)
df_base = normalizar_coluna_talhao(df_base)

_partes_depara = [df_cobertura[["talhao", "retiro"]]]
if not df_base.empty and "retiro" in df_base.columns:
    _partes_depara.append(df_base[["talhao", "retiro"]])
de_para_planilhas = pd.concat(_partes_depara).drop_duplicates(subset="talhao", keep="first")

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

if not df_base.empty and "status" in df_base.columns:
    area_base_feito = df_base[df_base["status"] == "Subsolado/Adubado"].groupby("talhao").agg(
        area_subsolada_ha=("area_plantada_ha", "sum"),
        kg_total_base=("kg_total", "sum"),
    ).reset_index()
else:
    area_base_feito = pd.DataFrame(columns=["talhao", "area_subsolada_ha", "kg_total_base"])

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

if "talhao_selecionado" not in st.session_state:
    st.session_state.talhao_selecionado = None

# -----------------------------------------------------------------
# Sidebar — escolher talhão (funciona mesmo se o clique no mapa falhar)
# -----------------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.subheader("📍 Ver talhão")
_lista_talhoes_sidebar = sorted(
    painel_f["talhao"].dropna().astype(str).unique().tolist(),
    key=lambda x: (len(x), x),
) if not painel_f.empty else []
_op_sidebar = ["(nenhum)"] + _lista_talhoes_sidebar
_atual_sidebar = st.session_state.get("talhao_selecionado")
_idx_sidebar = _op_sidebar.index(_atual_sidebar) if _atual_sidebar in _op_sidebar else 0
_esc_sidebar = st.sidebar.selectbox(
    "Número do talhão",
    _op_sidebar,
    index=_idx_sidebar,
    key="sidebar_ver_talhao",
)
if _esc_sidebar == "(nenhum)":
    if st.session_state.talhao_selecionado is not None:
        st.session_state.talhao_selecionado = None
        st.rerun()
elif _esc_sidebar != st.session_state.talhao_selecionado:
    st.session_state.talhao_selecionado = str(_esc_sidebar).strip().upper()
    st.rerun()

st.sidebar.caption(f"Versão do painel: **{PAINEL_BUILD}**")

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

_cob_talhoes = set(df_cobertura["talhao"].dropna().unique()) if not df_cobertura.empty else set()
_map_talhoes = set(painel_f["talhao"].dropna().unique()) if not painel_f.empty else set()
_cruzados = len(_cob_talhoes & _map_talhoes)
if df_cobertura.empty:
    st.error(
        "Nenhum lançamento de adubação carregado. Rode **CARGA_DADOS_PAINEL.ps1** (Desktop\\DADOS_PAINEL) "
        "ou coloque os xlsx em **`dados/`** e sincronize (aba ☁️ Supabase / GitHub Actions)."
    )
elif _cruzados == 0:
    st.warning(
        f"Planilha com **{len(_cob_talhoes)}** talhões, mapa com **{len(_map_talhoes)}** — "
        "**nenhum código coincide**. Verifique se a planilha de Cobertura é da mesma safra/fazenda "
        "ou se os códigos no Excel batem com o KML."
    )
else:
    st.caption(
        f"Dados de cobertura: **{len(df_cobertura)}** lançamentos · "
        f"**{_cruzados}** talhões cruzados com o mapa · fonte: {_fonte_planilhas}"
    )

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

        ficha = ficha_talhao_merged(ult_cob, painel_f, st.session_state.talhao_selecionado)
        try:
            clicado = render_mapa_adubacao(
                gdf_mapa,
                ficha,
                key_suffix="_prod",
                talhoes_lista=sorted(
                    gdf_mapa["talhao"].dropna().astype(str).unique().tolist(),
                    key=lambda x: (len(x), x),
                ),
            )
            if clicado and clicado != st.session_state.talhao_selecionado:
                st.session_state.talhao_selecionado = clicado
                st.rerun()
            ficha = ficha_talhao_merged(ult_cob, painel_f, st.session_state.talhao_selecionado)
            painel_ficha_talhao_streamlit(ficha)
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
    st.subheader("Fonte oficial — Supabase")
    engine = get_engine()
    if engine is None:
        st.warning(
            "Defina `SUPABASE_DB_URL` nos Secrets do Streamlit Cloud (e no GitHub Actions para sync automático)."
        )
        st.code(
            'SUPABASE_DB_URL = "postgresql+psycopg://postgres.<ref>:<senha>@'
            'aws-1-sa-east-1.pooler.supabase.com:6543/postgres"',
            language="toml",
        )
    else:
        st.success("Conexão com Supabase disponível. O painel **não** depende de upload por sessão.")
        st.caption("Schema: `sql/003_schema_adubacao_florestal.sql` (uma vez no SQL Editor).")

        st.markdown("#### 1) Sincronizar pasta `dados/` do servidor → Supabase")
        if os.path.isdir(_dados_dir):
            try:
                _paths_prev = descobrir_arquivos_dados_painel(_dados_dir)
                st.write(
                    f"KML: `{_paths_prev['kml'].name}` · Cobertura: `{_paths_prev['cobertura'].name}`"
                    + (f" · Base: `{_paths_prev['base'].name}`" if _paths_prev["base"] else "")
                )
            except FileNotFoundError as e:
                st.warning(str(e))
            if st.button("Executar sync dados/ → Supabase", type="primary"):
                with st.spinner("Gravando planilhas no banco…"):
                    try:
                        stats = sync_pasta_dados_painel(engine, _dados_dir)
                        st.success(
                            f"OK — talhões: {stats['talhoes']} · cobertura: {stats['cobertura']} · base: {stats['base']}"
                        )
                        st.info("Recarregue a página (R) para ler tudo do Supabase.")
                    except Exception as e:
                        st.error(f"Erro na carga: {e}")
        else:
            st.info("Copie os arquivos de `Desktop\\DADOS_PAINEL` para `dados/` no repositório ou use o PC (passo 2).")

        st.markdown("#### 2) No PC (pasta DADOS_PAINEL, sem commitar planilhas)")
        st.code(
            "powershell -ExecutionPolicy Bypass -File scripts\\CARGA_DADOS_PAINEL.ps1",
            language="powershell",
        )

        st.markdown("#### 3) GitHub Actions (push em `dados/` + secret `SUPABASE_DB_URL`)")
        st.caption("Workflow: `.github/workflows/sync-adubacao-supabase.yml` — disparo automático ou manual em Actions.")

        st.markdown("---")
        st.markdown("#### Regravar apenas o que já está na memória do painel")
        if st.button("Upsert talhões + cobertura + base (sessão atual)"):
            try:
                n_t = gravar_talhoes(engine, gdf_validos)
                n_c = gravar_cobertura(engine, df_cobertura, arquivo_origem="painel_streamlit")
                n_b = gravar_base(engine, df_base) if not df_base.empty else 0
                st.success(f"Supabase atualizado: {n_t} talhões, {n_c} lanç. cobertura, {n_b} base.")
            except Exception as e:
                st.error(f"Erro ao gravar: {e}")

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
