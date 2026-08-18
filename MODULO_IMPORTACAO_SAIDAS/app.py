#!/usr/bin/env python3
"""Painel local para inclusão manual no catálogo e estoque (painel Lovable)."""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))

from carregar_catalogo import ler_csv, upsert_catalogo  # noqa: E402
from carregar_estoque import ler_csv as ler_estoque_csv, upsert_estoque  # noqa: E402

st.set_page_config(
    page_title="Importação Catálogo / Estoque",
    page_icon="📦",
    layout="wide",
)

st.title("CONTROLE DE MOVIMENTAÇÃO E FLUXO DE ESTOQUES")
st.caption("Santa Vergínia Agropecuária e Florestal — Módulo de importação (catálogo + saldo)")

aba_cat, aba_est, aba_arq = st.tabs(["Catálogo", "Estoque", "Arquivos CSV"])

with aba_cat:
    st.subheader("Incluir / atualizar item no catálogo")
    with st.form("form_catalogo"):
        codigo = st.text_input("Código SAP", placeholder="2333")
        desc_sap = st.text_input("Descrição SAP", placeholder="GEL IRRIGAÇÃO FLOBOND A-30 SC 25 KG")
        desc_res = st.text_input("Descrição resumida", placeholder="Gel Irrigação Flobond A-30 SC 25 KG")
        unidade = st.selectbox("Unidade", ["KG", "LT", "UN", "SC", "GL"])
        categoria = st.selectbox("Categoria", ["Defensivos", "Medicamentos", "Filtros", "Outros"])
        deposito = st.text_input("Depósito SAP", value="FSV-MAN")
        obs = st.text_area("Observação", placeholder="Ex.: entrada NF-e 200 KG")
        ok = st.form_submit_button("Gravar catálogo", type="primary")
    if ok and codigo and desc_sap:
        item = {
            "codigo_sap": codigo.strip(),
            "descricao_sap": desc_sap.strip(),
            "descricao_resumida": (desc_res or desc_sap).strip(),
            "unidade_estoque": unidade,
            "categoria": categoria,
            "deposito_sap": deposito.strip() or "FSV-MAN",
            "ativo": True,
            "fonte_arquivo": "streamlit_manual",
            "observacao": obs.strip(),
        }
        ins, upd = upsert_catalogo([item])
        st.success(f"Catálogo gravado ({ins} inserido, {upd} atualizado).")

with aba_est:
    st.subheader("Atualizar saldo no painel")
    with st.form("form_estoque"):
        codigo_e = st.text_input("Código SAP ", placeholder="2333", key="cod_est")
        qtd = st.number_input("Quantidade em estoque", min_value=0.0, step=1.0, value=0.0)
        unidade_e = st.selectbox("Unidade ", ["KG", "LT", "UN", "SC", "GL"], key="uni_est")
        ok_e = st.form_submit_button("Gravar estoque", type="primary")
    if ok_e and codigo_e:
        item = {"codigo_sap": codigo_e.strip(), "em_estoque": float(qtd), "unidade": unidade_e}
        n = upsert_estoque([item])
        st.success(f"Saldo gravado para {codigo_e} ({n} registro).")

with aba_arq:
    st.subheader("Carregar CSV da pasta dados/")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Executar catalogo_inclusoes.csv"):
            path = ROOT / "dados" / "catalogo_inclusoes.csv"
            ins, upd = upsert_catalogo(ler_csv(path))
            st.success(f"Catálogo: {ins} inserido(s), {upd} atualizado(s).")
    with col2:
        if st.button("Executar estoque_inclusoes.csv"):
            path = ROOT / "dados" / "estoque_inclusoes.csv"
            n = upsert_estoque(ler_estoque_csv(path))
            st.success(f"Estoque: {n} saldo(s) gravado(s).")

st.info(
    "Painel web oficial: https://estoque-verde-ouro.lovable.app/ — "
    "após gravar catálogo + estoque, atualize a página (F5) para ver o item."
)
