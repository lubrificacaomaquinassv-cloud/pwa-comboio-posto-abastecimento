"""Painel Streamlit — controle orçamentário doméstico (SQLite local)."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import List, Optional

import pandas as pd
import streamlit as st

import database as db
from fatura import (
    chave_fatura,
    ciclo_vigente,
    data_pagamento_fatura,
    pagamento_parcela,
    periodo_fechamento_para_pagamento,
)

st.set_page_config(page_title="Orçamento Doméstico", page_icon="🏠", layout="wide")


def aplicar_tema() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background: linear-gradient(165deg, #0c0f14 0%, #121820 45%, #0f1318 100%);
            color: #e8eef7;
        }
        [data-testid="stSidebar"] {
            background-color: #0a0d12;
            border-right: 1px solid #2a3548;
        }
        [data-testid="stSidebar"] * {
            color: #dce4f0 !important;
        }
        h1, h2, h3, label, p, span, .stMarkdown {
            color: #e8eef7;
        }
        div[data-testid="stMetric"] {
            background: #151b26;
            border: 1px solid #2a3548;
            border-radius: 10px;
            padding: 12px 16px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.25);
        }
        div[data-testid="stMetric"] label {
            color: #9fb0c8 !important;
        }
        div[data-testid="stMetric"] [data-testid="stMetricValue"] {
            color: #f0f6ff !important;
        }
        div[data-testid="stMetric"] [data-testid="stMetricDelta"] {
            color: #6ee7b7 !important;
        }
        .stAlert {
            background-color: #151b26;
            border: 1px solid #2a3548;
            color: #e8eef7;
        }
        div[data-baseweb="select"] > div,
        div[data-baseweb="input"] > div,
        .stTextInput input, .stNumberInput input, .stDateInput input {
            background-color: #1a2230 !important;
            color: #f0f6ff !important;
            border-color: #3d4f6a !important;
        }
        .stButton > button[kind="primary"] {
            background: linear-gradient(90deg, #059669, #10b981);
            color: #041008;
            border: none;
            font-weight: 600;
        }
        .stButton > button[kind="secondary"] {
            background: #1a2230;
            color: #e8eef7;
            border: 1px solid #3d4f6a;
        }
        [data-testid="stDataFrame"] {
            border: 1px solid #2a3548;
            border-radius: 8px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def brl(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def parse_mes(mes: str) -> date:
    y, m = mes.split("-")
    return date(int(y), int(m), 1)


def meses_disponiveis() -> List[str]:
    rows = db.list_lancamentos()
    meses = {r["mes_competencia"] for r in rows}
    hoje = date.today()
    meses.add(f"{hoje.year:04d}-{hoje.month:02d}")
    return sorted(meses, reverse=True)


def faturas_disponiveis() -> List[str]:
    rows = db.list_lancamentos()
    faturas = {r["fatura_pagamento"] for r in rows if r.get("fatura_pagamento")}
    cfg = db.get_config()
    ciclo = ciclo_vigente(date.today(), cfg["dia_fechamento"], cfg["dia_pagamento"])
    faturas.add(chave_fatura(ciclo["vencimento"]))
    faturas.add(chave_fatura(ciclo["proximo_vencimento"]))
    return sorted(f for f in faturas if f)


def salvar_parcelado(
    data_compra: date,
    descricao: str,
    categoria: str,
    valor_total: float,
    parcelas: int,
    forma: str,
    forcar_proximo: bool,
    confirmado: bool,
) -> None:
    cfg = db.get_config()
    grupo = str(uuid.uuid4())
    valor_parcela = round(valor_total / parcelas, 2)
    ajuste = round(valor_total - valor_parcela * parcelas, 2)
    for n in range(1, parcelas + 1):
        valor = valor_parcela + (ajuste if n == parcelas else 0)
        fat = pagamento_parcela(
            data_compra,
            n,
            cfg["dia_fechamento"],
            cfg["dia_pagamento"],
            forcar_proximo_ciclo=forcar_proximo,
        )
        db.insert_lancamento(
            {
                "data_compra": data_compra.isoformat(),
                "descricao": descricao,
                "categoria": categoria,
                "tipo": "variavel",
                "forma_pagamento": forma,
                "valor": valor,
                "parcela_num": n,
                "parcelas_total": parcelas,
                "grupo_parcelamento": grupo if parcelas > 1 else None,
                "fatura_pagamento": chave_fatura(fat),
                "mes_competencia": db.mes_competencia_de(data_compra),
                "confirmado": confirmado,
                "proximo_ciclo_forcado": forcar_proximo and n == 1,
            }
        )


def banner_ciclo() -> None:
    cfg = db.get_config()
    info = ciclo_vigente(date.today(), cfg["dia_fechamento"], cfg["dia_pagamento"])
    col1, col2, col3 = st.columns(3)
    col1.metric(
        "Fechamento da fatura atual",
        info["fechamento"].strftime("%d/%m/%Y"),
        "Já fechou" if info["ja_fechou"] else "Em aberto",
    )
    col2.metric("Vencimento desta fatura", info["vencimento"].strftime("%d/%m/%Y"))
    col3.metric("Próximo fechamento", info["proximo_fechamento"].strftime("%d/%m/%Y"))
    st.caption(
        f"Compras de {info['inicio_compras'].strftime('%d/%m/%Y')} até "
        f"{info['fechamento'].strftime('%d/%m/%Y')} entram nesta fatura "
        f"(paga em {info['vencimento'].strftime('%d/%m/%Y')}). "
        "Use **Próximo ciclo** ao lançar se a despesa deve ir para a fatura seguinte."
    )


def pagina_painel() -> None:
    cfg = db.get_config()
    hoje = date.today()
    ciclo = ciclo_vigente(hoje, cfg["dia_fechamento"], cfg["dia_pagamento"])

    faturas = faturas_disponiveis()
    default_fat = chave_fatura(ciclo["vencimento"])
    idx = faturas.index(default_fat) if default_fat in faturas else 0
    fatura_sel = st.selectbox(
        "Fatura de referência (data de pagamento)",
        faturas,
        index=idx,
        format_func=lambda s: datetime.strptime(s, "%Y-%m-%d").strftime("%d/%m/%Y"),
    )
    fat_date = datetime.strptime(fatura_sel, "%Y-%m-%d").date()
    prox_fat = chave_fatura(
        date(
            fat_date.year + (1 if fat_date.month == 12 else 0),
            1 if fat_date.month == 12 else fat_date.month + 1,
            fat_date.day,
        )
    )

    mes_ref = f"{fat_date.year:04d}-{fat_date.month:02d}"
    renda = db.get_renda_mes(mes_ref, cfg["renda_padrao"])
    fixas = db.sum_fixas_mes(mes_ref)
    supermercado = db.sum_supermercado_fatura(fatura_sel)
    parcelado = db.total_parcelado_na_fatura(fatura_sel)
    encerra = db.parcelas_encerrando(fatura_sel)
    encerra_prox = db.parcelas_encerrando(prox_fat)
    valor_encerra = sum(float(x["valor"]) for x in encerra)
    valor_encerra_prox = sum(float(x["valor"]) for x in encerra_prox)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Renda", brl(renda))
    c2.metric("Despesas fixas (mês)", brl(fixas))
    c3.metric("Supermercado (esta fatura)", brl(supermercado))
    c4.metric("Total parcelado (fatura)", brl(parcelado))

    c5, c6, c7 = st.columns(3)
    c5.metric("Parcelas que encerram nesta fatura", f"{len(encerra)}", brl(valor_encerra))
    c6.metric("Parcelas que encerram na próxima", f"{len(encerra_prox)}", brl(valor_encerra_prox))
    saldo = renda - fixas - supermercado - parcelado
    c7.metric("Indicativo (renda − fixas − mercado − parcelado)", brl(saldo))

    inicio, fim = periodo_fechamento_para_pagamento(
        fat_date, cfg["dia_fechamento"], cfg["dia_pagamento"]
    )
    st.info(
        f"Período de compras desta fatura: {inicio.strftime('%d/%m/%Y')} a "
        f"{fim.strftime('%d/%m/%Y')} · Pagamento em {fat_date.strftime('%d/%m/%Y')}"
    )

    if encerra:
        with st.expander("Detalhe — últimas parcelas nesta fatura"):
            st.dataframe(
                pd.DataFrame(encerra)[
                    ["descricao", "categoria", "parcela_num", "parcelas_total", "valor"]
                ],
                use_container_width=True,
                hide_index=True,
            )

    st.divider()
    st.subheader("Lançamentos por mês")
    mes_tab = st.selectbox("Mês", meses_disponiveis())
    lanc = db.list_lancamentos(mes_competencia=mes_tab, apenas_confirmados=True)
    if not lanc:
        st.write("Nenhum lançamento confirmado neste mês.")
        return
    df = pd.DataFrame(lanc)
    df["data_compra"] = pd.to_datetime(df["data_compra"]).dt.strftime("%d/%m/%Y")
    df["valor"] = df["valor"].map(brl)
    df["parcelas"] = df.apply(
        lambda r: f"{r['parcela_num']}/{r['parcelas_total']}" if r["parcelas_total"] > 1 else "—",
        axis=1,
    )
    df["prox_ciclo"] = df["proximo_ciclo_forcado"].map({1: "Sim", 0: "—"})
    st.dataframe(
        df[
            [
                "data_compra",
                "descricao",
                "categoria",
                "tipo",
                "forma_pagamento",
                "valor",
                "parcelas",
                "fatura_pagamento",
                "prox_ciclo",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )


def form_proximo_ciclo(data_compra: date, key: str) -> bool:
    cfg = db.get_config()
    info = ciclo_vigente(data_compra, cfg["dia_fechamento"], cfg["dia_pagamento"])
    fat_normal = data_pagamento_fatura(
        data_compra, cfg["dia_fechamento"], cfg["dia_pagamento"], False
    )
    forcar = st.checkbox(
        "Lançar no **próximo ciclo** (depois do fechamento / fatura seguinte)",
        key=key,
        help="Marque quando a compra ainda está no período aberto, mas você quer que caia na próxima fatura.",
    )
    if forcar:
        fat_forcada = data_pagamento_fatura(
            data_compra, cfg["dia_fechamento"], cfg["dia_pagamento"], True
        )
        st.success(
            f"Vencimento previsto: **{fat_forcada.strftime('%d/%m/%Y')}** "
            f"(sem marcar seria {fat_normal.strftime('%d/%m/%Y')})."
        )
    elif info["ja_fechou"] and data_compra <= info["fechamento"]:
        st.warning("Esta data já passou do fechamento; novas compras entram no próximo ciclo automaticamente.")
    else:
        st.caption(f"Vencimento automático: {fat_normal.strftime('%d/%m/%Y')}")
    return forcar


def pagina_lancamentos() -> None:
    tab_fixa, tab_var, tab_renda = st.tabs(["Despesas fixas", "Cartão / variáveis", "Renda do mês"])

    with tab_renda:
        mes = st.text_input("Mês (AAAA-MM)", value=f"{date.today().year:04d}-{date.today().month:02d}")
        cfg = db.get_config()
        valor = st.number_input("Renda", min_value=0.0, step=100.0, value=float(cfg["renda_padrao"]))
        if st.button("Salvar renda", key="save_renda"):
            db.set_renda_mes(mes, valor)
            st.success("Renda registrada.")

    with tab_fixa:
        with st.form("form_fixa"):
            data_compra = st.date_input("Data", value=date.today())
            categoria = st.selectbox("Categoria", db.CATEGORIAS_FIXAS)
            descricao = st.text_input("Descrição", value=categoria)
            valor = st.number_input("Valor (R$)", min_value=0.01, step=0.01, format="%.2f")
            forma = st.selectbox("Forma", ["pix", "débito", "dinheiro", "boleto", "cartão"])
            submitted = st.form_submit_button("Validar")
        if submitted:
            st.session_state["preview_fixa"] = {
                "data_compra": data_compra,
                "categoria": categoria,
                "descricao": descricao or categoria,
                "valor": valor,
                "forma": forma,
            }
        prev = st.session_state.get("preview_fixa")
        if prev:
            st.subheader("Confirmação")
            st.write(prev)
            if st.button("Confirmar despesa fixa", type="primary"):
                db.insert_lancamento(
                    {
                        "data_compra": prev["data_compra"].isoformat(),
                        "descricao": prev["descricao"],
                        "categoria": prev["categoria"],
                        "tipo": "fixa",
                        "forma_pagamento": prev["forma"],
                        "valor": prev["valor"],
                        "parcela_num": 1,
                        "parcelas_total": 1,
                        "fatura_pagamento": None,
                        "mes_competencia": db.mes_competencia_de(prev["data_compra"]),
                        "confirmado": True,
                    }
                )
                del st.session_state["preview_fixa"]
                st.success("Despesa fixa confirmada.")
                st.rerun()

    with tab_var:
        cfg = db.get_config()
        with st.form("form_var"):
            data_compra = st.date_input("Data da compra", value=date.today(), key="dt_var")
            categoria = st.selectbox("Categoria", db.CATEGORIAS_VARIAVEIS)
            descricao = st.text_input("Descrição")
            valor_total = st.number_input("Valor total (R$)", min_value=0.01, step=0.01, format="%.2f")
            modo_parcelas = st.radio("Parcelas", ["Selecionar", "Digitar quantidade"], horizontal=True)
            if modo_parcelas == "Selecionar":
                parcelas = st.selectbox("Quantidade", list(range(1, 25)), index=0)
            else:
                parcelas = st.number_input("Qtd. parcelas (1–24)", min_value=1, max_value=24, value=1)
            forma = st.selectbox("Forma", ["cartão", "pix", "débito"], key="forma_var")
            submitted = st.form_submit_button("Validar")
        if submitted:
            st.session_state["preview_var"] = {
                "data_compra": data_compra,
                "categoria": categoria,
                "descricao": descricao or categoria,
                "valor_total": valor_total,
                "parcelas": int(parcelas),
                "forma": forma,
            }
        prev = st.session_state.get("preview_var")
        if prev:
            st.subheader("Confirmação — cartão / variável")
            forcar = form_proximo_ciclo(prev["data_compra"], key="prox_var")
            cfg = db.get_config()
            fat = data_pagamento_fatura(
                prev["data_compra"],
                cfg["dia_fechamento"],
                cfg["dia_pagamento"],
                forcar_proximo_ciclo=forcar,
            )
            st.write(
                {
                    **prev,
                    "valor_parcela": round(prev["valor_total"] / prev["parcelas"], 2),
                    "1ª fatura (pagamento)": fat.strftime("%d/%m/%Y"),
                }
            )
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("Confirmar lançamento", type="primary"):
                    salvar_parcelado(
                        prev["data_compra"],
                        prev["descricao"],
                        prev["categoria"],
                        prev["valor_total"],
                        prev["parcelas"],
                        prev["forma"],
                        forcar,
                        True,
                    )
                    del st.session_state["preview_var"]
                    st.success("Lançamento confirmado.")
                    st.rerun()
            with col_b:
                if st.button("Descartar"):
                    del st.session_state["preview_var"]
                    st.rerun()

        st.divider()
        st.subheader("Antecipar lançamento — próximo ciclo")
        st.caption(
            "Use quando a fatura acabou de fechar e você já quer registrar compras "
            "(ex.: mercado) que entrarão na **próxima** fatura."
        )
        with st.form("form_proximo_mes"):
            data_futura = st.date_input(
                "Data estimada da compra",
                value=ciclo_vigente(date.today(), cfg["dia_fechamento"], cfg["dia_pagamento"])[
                    "proximo_fechamento"
                ],
            )
            cat2 = st.selectbox("Categoria ", ["Supermercado (cartão)"] + db.CATEGORIAS_VARIAVEIS)
            desc2 = st.text_input("Descrição ")
            val2 = st.number_input("Valor (R$) ", min_value=0.01, step=0.01, format="%.2f")
            go = st.form_submit_button("Validar pré-lançamento")
        if go:
            st.session_state["preview_pre"] = {
                "data_compra": data_futura,
                "categoria": cat2,
                "descricao": desc2 or cat2,
                "valor_total": val2,
                "parcelas": 1,
                "forma": "cartão",
                "forcar": True,
            }
        pre = st.session_state.get("preview_pre")
        if pre:
            fat = data_pagamento_fatura(
                pre["data_compra"],
                cfg["dia_fechamento"],
                cfg["dia_pagamento"],
                forcar_proximo_ciclo=True,
            )
            st.write({**pre, "fatura": fat.strftime("%d/%m/%Y")})
            if st.button("Confirmar pré-lançamento (próximo ciclo)", type="primary"):
                salvar_parcelado(
                    pre["data_compra"],
                    pre["descricao"],
                    pre["categoria"],
                    pre["valor_total"],
                    1,
                    pre["forma"],
                    True,
                    True,
                )
                del st.session_state["preview_pre"]
                st.success("Pré-lançamento salvo na próxima fatura.")
                st.rerun()


def pagina_config() -> None:
    cfg = db.get_config()
    with st.form("cfg"):
        dia_fech = st.number_input("Dia de fechamento da fatura", 1, 28, int(cfg["dia_fechamento"]))
        dia_pag = st.number_input("Dia de pagamento", 1, 28, int(cfg["dia_pagamento"]))
        renda = st.number_input("Renda padrão (R$)", min_value=0.0, step=100.0, value=float(cfg["renda_padrao"]))
        if st.form_submit_button("Salvar configuração"):
            db.update_config(int(dia_fech), int(dia_pag), renda)
            st.success("Configuração atualizada.")
    st.markdown(
        """
        **SQLite local:** os dados ficam em `data/orcamento.db` neste computador — não vão para Supabase nem nuvem.
        Faça backup copiando essa pasta.
        """
    )


def main() -> None:
    aplicar_tema()
    st.title("Controle orçamentário doméstico")
    banner_ciclo()
    pagina = st.sidebar.radio("Menu", ["Painel", "Lançamentos", "Configuração"])
    if pagina == "Painel":
        pagina_painel()
    elif pagina == "Lançamentos":
        pagina_lancamentos()
    else:
        pagina_config()


if __name__ == "__main__":
    main()
