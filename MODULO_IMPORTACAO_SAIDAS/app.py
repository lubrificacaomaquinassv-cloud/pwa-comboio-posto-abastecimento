"""Almoxarifado SIGCF — validador Python unificado (WhatsApp opcional + SAP Excel)."""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))

from interpretar_mensagem import SaidaInterpretada, interpretar_mensagem
from motor_almox import (
    CATEGORIAS_BAIXA,
    CATEGORIAS_ESTOQUE,
    ResultadoValidacao,
    executar_registro,
    heatmap_conta_mes,
    ler_uploads_baixas,
    ler_uploads_estoque,
    metricas_baixas,
    preview_conciliacao,
    timeline_df,
)
from importar_nfe_campo import (
    MATCH_MIN,
    aplicar_supabase,
    itens_para_dataframe,
    processar_uploads_nfe,
)
from db_config import conectar_psycopg2
from sigcf_auth import exigir_acesso, logo_html

st.set_page_config(
    page_title="Almox SIGCF — Validador",
    layout="wide",
    page_icon="📦",
    initial_sidebar_state="collapsed",
)

exigir_acesso("Importação de Saídas Operacionais")

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700&display=swap');
[data-testid="stAppViewContainer"]{background:#0a1409;}
[data-testid="stHeader"]{background:#0a1409;}
h1,h2,h3,p,span,label{color:#e8edd0;}
h1{font-family:'Barlow Condensed',sans-serif;letter-spacing:1px;}
.stCaption,[data-testid="stCaptionContainer"] p{color:#8aab80!important;}
.logo-frame{background:linear-gradient(145deg,#0a1628,#0d2040);border:2px solid #c9a227;
 border-radius:12px;padding:5px;display:inline-block;box-shadow:0 4px 18px rgba(0,0,0,.45);}
.logo-frame img{display:block;border-radius:8px;}
.step{font-family:'Barlow Condensed',sans-serif;font-size:13px;font-weight:700;letter-spacing:2px;
 text-transform:uppercase;color:#c9a227;margin:8px 0 4px;}
.step.done{color:#6fcf60;}
.step.active{color:#ffd966;border-left:4px solid #4a9e3f;padding-left:8px;}
.sec{font-family:'Barlow Condensed',sans-serif;font-size:12px;font-weight:700;
 letter-spacing:2px;text-transform:uppercase;color:#8aab80;
 border-left:4px solid #4a9e3f;padding-left:10px;margin:16px 0 10px;}
.ok{color:#6fcf60;font-weight:700;}
.warn{color:#ffb347;font-weight:700;}
.bad{color:#ff6b6b;font-weight:700;}
.stTextArea textarea,.stTextInput input,[data-testid="stDateInput"] input{
 background:#dce6d2!important;color:#1a2818!important;border:2px solid #c9a227!important;border-radius:8px!important;}
div[data-baseweb="select"] > div{background:#dce6d2!important;border:2px solid #c9a227!important;
 color:#1a2818!important;border-radius:8px!important;}
.stButton button{background:#4a9e3f!important;color:#fff!important;
 border:1px solid #6fcf60!important;font-family:'Barlow Condensed',sans-serif;font-weight:700;
 letter-spacing:1px;text-transform:uppercase;border-radius:8px;}
[data-testid="stFileUploader"] section{background:#dce6d2!important;border:2px dashed #c9a227!important;border-radius:8px;}
"""
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

ETAPAS = ["① Importar", "② Interpretar", "③ Conferir", "④ Conciliar", "⑤ Registrar"]
SS = "almox_sessao"


def init_state():
    if SS not in st.session_state:
        st.session_state[SS] = {
            "etapa": 1,
            "data_ref": date.today(),
            "usar_whatsapp": False,
            "texto_whatsapp": "",
            "interpretado": None,
            "form_itens": None,
            "baixas_df": None,
            "estoque_df": None,
            "validacao_baixas": None,
            "validacao_estoque": None,
            "preview_conc": None,
            "conciliar_whatsapp": False,
            "registro_ok": False,
            "resultado": None,
            "modo_somente_estoque": False,
        }


def reset_fluxo():
    st.session_state[SS] = {
        "etapa": 1,
        "data_ref": date.today(),
        "usar_whatsapp": False,
        "texto_whatsapp": "",
        "interpretado": None,
        "form_itens": None,
        "baixas_df": None,
        "estoque_df": None,
        "validacao_baixas": None,
        "validacao_estoque": None,
        "preview_conc": None,
        "conciliar_whatsapp": False,
        "registro_ok": False,
        "resultado": None,
        "modo_somente_estoque": False,
    }


@st.cache_resource
def sb():
    from sigcf_auth import conectar_supabase
    return conectar_supabase()


@st.cache_data(ttl=300)
def carregar_catalogo() -> list[dict]:
    try:
        res = sb().table("dim_catalogo_sap_campo").select("*").eq("ativo", True).execute()
        return res.data or []
    except Exception:
        res = sb().table("dim_produtos").select("*").eq("ativo", True).execute()
        return res.data or []


@st.cache_data(ttl=300)
def carregar_locais() -> list[dict]:
    res = sb().table("dim_locais").select("id,nome,tipo,tipo_operacional,ativo").eq("ativo", True).execute()
    return res.data or []


@st.cache_data(ttl=300)
def carregar_talhoes() -> list[dict]:
    res = sb().table("dim_talhoes").select("id,codigo,nome,id_local,ativo").eq("ativo", True).execute()
    return res.data or []


def render_passos(etapa_atual: int):
    cols = st.columns(5)
    for i, (col, nome) in enumerate(zip(cols, ETAPAS), start=1):
        cls = "step active" if i == etapa_atual else ("step done" if i < etapa_atual else "step")
        col.markdown(f'<div class="{cls}">{nome}</div>', unsafe_allow_html=True)


def interpretado_para_form(s: SaidaInterpretada) -> dict:
    catalogo = carregar_catalogo()
    prod_opts = {
        f"{p.get('codigo_sap')} — {p.get('descricao_resumida') or p.get('descricao_sap')}": p
        for p in catalogo
    }
    locais = carregar_locais()
    talhoes = carregar_talhoes()
    itens = []
    for it in s.itens:
        cod = (it.produto_match.valor or {}).get("codigo_sap") if it.produto_match.valor else None
        label = next((k for k, v in prod_opts.items() if v.get("codigo_sap") == cod), "")
        itens.append({
            "ordem": it.ordem,
            "texto_linha": it.texto_linha,
            "produto_texto": it.produto_texto,
            "quantidade": float(it.quantidade),
            "unidade": it.unidade,
            "produto_label": label,
            "confianca": it.produto_match.confianca,
        })
    local_id = s.local.valor.get("id") if isinstance(s.local.valor, dict) else None
    talhao_id = None
    if isinstance(s.talhao.valor, dict):
        talhao_id = s.talhao.valor.get("id")
        if not talhao_id and s.talhao.valor.get("codigo"):
            cod_t = str(s.talhao.valor["codigo"]).strip()
            for t in talhoes:
                if str(t.get("codigo") or "").strip() == cod_t:
                    talhao_id = t["id"]
                    break
    return {
        "responsavel": s.responsavel.valor or "",
        "destino_texto": s.destino_texto or "",
        "data_referencia": date.today(),
        "local_id": local_id,
        "talhao_id": talhao_id,
        "itens": itens,
        "prod_opts": prod_opts,
        "locais": locais,
        "talhoes": talhoes,
    }


def plot_timeline(baixas: pd.DataFrame):
    tl = timeline_df(baixas)
    if tl.empty:
        return
    fig, ax = plt.subplots(figsize=(10, 3.5), facecolor="#0a1409")
    ax.set_facecolor("#0a1409")
    for cat, grp in tl.groupby("categoria"):
        ax.plot(grp["data_baixa"], grp["valor"], marker="o", label=str(cat))
    ax.set_title("Linha do tempo — valor baixas SAP", color="#e8edd0")
    ax.tick_params(colors="#8aab80")
    ax.legend(facecolor="#1a2818", labelcolor="#e8edd0")
    ax.grid(alpha=0.2)
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)


def plot_heatmap(baixas: pd.DataFrame):
    pivot = heatmap_conta_mes(baixas)
    if pivot.empty or pivot.shape[1] == 0:
        return
    fig, ax = plt.subplots(figsize=(10, max(3, len(pivot) * 0.35)), facecolor="#0a1409")
    im = ax.imshow(pivot.values, aspect="auto", cmap="YlGn")
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels([str(x)[:28] for x in pivot.index], color="#e8edd0", fontsize=8)
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(list(pivot.columns), color="#8aab80", rotation=45, ha="right")
    ax.set_title("Heatmap — conta contábil × mês (R$)", color="#e8edd0")
    fig.colorbar(im, ax=ax)
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)


def coletar_uploads_baixas() -> dict[str, tuple[bytes, str]]:
    out: dict[str, tuple[bytes, str]] = {}
    st.markdown('<div class="sec">Excel baixas SAP (conta, destino, valor)</div>', unsafe_allow_html=True)
    cols = st.columns(2)
    for i, (slug, _cat, label) in enumerate(CATEGORIAS_BAIXA):
        with cols[i % 2]:
            f = st.file_uploader(label, type=["xlsx"], key=f"up_baixa_{slug}")
            if f is not None:
                out[slug] = (f.getvalue(), f.name)
    return out


def coletar_uploads_estoque() -> dict[str, tuple[bytes, str]]:
    out: dict[str, tuple[bytes, str]] = {}
    st.markdown('<div class="sec">Excel estoque SAP (pós-baixa)</div>', unsafe_allow_html=True)
    cols = st.columns(2)
    for i, (slug, _cat, label) in enumerate(CATEGORIAS_ESTOQUE):
        with cols[i % 2]:
            f = st.file_uploader(label, type=["xlsx"], key=f"up_est_{slug}")
            if f is not None:
                out[slug] = (f.getvalue(), f.name)
    return out


init_state()
state = st.session_state[SS]

_, btn_col, _ = st.columns([4, 1, 4])
with btn_col:
    if st.button("＋ Nova importação", key="nova_topo"):
        reset_fluxo()
        st.rerun()

col_logo, col_t = st.columns([1, 5])
with col_logo:
    st.markdown(logo_html(100), unsafe_allow_html=True)
with col_t:
    st.title("Importação de Saídas Operacionais")
    st.caption(
        "SAP Excel → validação → conciliação → Supabase API → "
        "[alma-control-center](https://alma-control-center.lovable.app/movimentacao)"
    )

render_passos(state["etapa"])

# ── ① IMPORTAR ───────────────────────────────────────────────────────────────
if state["etapa"] == 1:
    tab_sap, tab_nfe = st.tabs(["Excel SAP (saídas)", "NF-e XML (entradas)"])

    with tab_sap:
        state["data_ref"] = st.date_input("Data de referência", value=state["data_ref"], key="data_ref_sap")

        state["usar_whatsapp"] = st.checkbox(
            "Incluir mensagem WhatsApp (opcional — medicamentos/defensivos)",
            value=state["usar_whatsapp"],
        )
        if state["usar_whatsapp"]:
            st.markdown('<div class="sec">Colar mensagem do WhatsApp</div>', unsafe_allow_html=True)
            exemplo = "Anderson Correia\n20L Agefix\n120L ZAPP\nHorto Sede - Pasto 430"
            state["texto_whatsapp"] = st.text_area(
                "Texto da mensagem",
                value=state["texto_whatsapp"] or "",
                height=160,
                placeholder=exemplo,
            )

        uploads_b = coletar_uploads_baixas()
        uploads_e = coletar_uploads_estoque()

        st.info(
            "Envie **baixas SAP** e/ou **estoque SAP** (pós-baixa). "
            "Qualquer nome de arquivo .xlsx serve — use o campo da categoria. "
            "Pode enviar só estoque para atualizar saldo — sem baixas."
        )

        c1, _ = st.columns([1, 4])
        with c1:
            tem_entrada = bool(uploads_b) or bool(uploads_e)
            if st.button("Interpretar →", type="primary", disabled=not tem_entrada, key="btn_interp_sap"):
                vb = ler_uploads_baixas(uploads_b) if uploads_b else ResultadoValidacao()
                ve = ler_uploads_estoque(uploads_e) if uploads_e else ResultadoValidacao()
                state["validacao_baixas"] = vb
                state["validacao_estoque"] = ve
                state["baixas_df"] = vb.baixas if not vb.baixas.empty else pd.DataFrame()
                state["estoque_df"] = ve.estoque if not ve.estoque.empty else pd.DataFrame()
                state["modo_somente_estoque"] = bool(uploads_e) and not uploads_b

                if vb.erros or ve.erros:
                    for e in vb.erros + ve.erros:
                        st.error(e)
                    st.stop()

                if ve.estoque.empty and vb.baixas.empty:
                    st.error("Nenhum dado válido nos arquivos enviados.")
                    st.stop()

                if state["usar_whatsapp"] and state["texto_whatsapp"].strip():
                    state["interpretado"] = interpretar_mensagem(
                        state["texto_whatsapp"],
                        carregar_catalogo(),
                        carregar_locais(),
                        carregar_talhoes(),
                    )
                    state["form_itens"] = interpretado_para_form(state["interpretado"])
                else:
                    state["interpretado"] = None
                    state["form_itens"] = None

                state["etapa"] = 2
                st.rerun()

    with tab_nfe:
        st.markdown(
            '<div class="sec">Entradas de estoque — NF-e de compra</div>',
            unsafe_allow_html=True,
        )
        st.caption(
            "NF-e de **medicamentos, defensivos ou combustível** (Diesel S-500 / S-10). "
            "Grava preço unitário em `preco_compra_campo` e atualiza valor no estoque."
        )

        xml_files = st.file_uploader(
            "Arquivo(s) XML da NF-e",
            type=["xml"],
            accept_multiple_files=True,
            key="up_nfe_entrada",
        )

        if xml_files:
            catalogo = carregar_catalogo()
            if not catalogo:
                st.error("Catálogo SAP vazio — rode CARREGAR_CATALOGO.bat antes.")
            else:
                arquivos = [(f.name, f.getvalue()) for f in xml_files]
                proc = processar_uploads_nfe(arquivos, catalogo, min_score=MATCH_MIN)
                state["nfe_proc"] = proc

                for err in proc.get("erros") or []:
                    st.error(err)

                matched = proc.get("matched") or []
                sem_match = proc.get("sem_match") or []
                todos = proc.get("itens") or []

                m1, m2, m3 = st.columns(3)
                m1.metric("Itens lidos", len(todos))
                m2.metric("Match OK", len(matched))
                m3.metric("Revisar", len(sem_match))

                if todos:
                    st.markdown("#### Pré-visualização")
                    st.dataframe(
                        itens_para_dataframe(todos),
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Qtd": st.column_config.NumberColumn(format="%.3f"),
                            "R$/un": st.column_config.NumberColumn(format="%.4f"),
                        },
                    )

                if sem_match:
                    st.warning(
                        f"{len(sem_match)} item(ns) sem match automático (confiança < {MATCH_MIN:.0%}). "
                        "Revise o catálogo SAP ou o nome na NF-e antes de gravar."
                    )

                if matched:
                    st.success(f"{len(matched)} item(ns) prontos para gravar no Supabase.")
                    if st.button("✅ Gravar entradas NF-e", type="primary", key="btn_gravar_nfe"):
                        with st.spinner("Gravando preco_compra_campo…"):
                            ok, ignorados = aplicar_supabase(matched)
                        try:
                            from db_config import conectar_psycopg2
                            from motor_almox import refresh_api_alma
                            conn = conectar_psycopg2()
                            refresh_api_alma(conn)
                            conn.close()
                        except Exception:
                            pass
                        st.success(
                            f"✅ {ok} entrada(s) registrada(s). API alma-control-center atualizada."
                        )
                        if ignorados:
                            st.caption(f"{ignorados} item(ns) ignorados.")
                        st.cache_data.clear()
                        st.balloons()
                elif todos and not matched:
                    st.error("Nenhum item com match suficiente para gravar.")
        else:
            st.info(
                "Selecione `.xml` da NF-e (medicamentos, defensivos, **combustível S-500 / S-10**)."
            )

# ── ② INTERPRETAR ──────────────────────────────────────────────────────────
elif state["etapa"] == 2:
    vb = state["validacao_baixas"]
    ve = state["validacao_estoque"]
    baixas = state["baixas_df"]
    estoque = state["estoque_df"]

    st.markdown('<div class="sec">Resultado da interpretação SAP</div>', unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Linhas baixa SAP", len(baixas) if baixas is not None else 0)
    m2.metric("Itens estoque", len(estoque) if estoque is not None and not estoque.empty else 0)
    met = metricas_baixas(baixas) if baixas is not None else {}
    m3.metric("Valor baixas", f"R$ {met.get('valor_total', 0):,.2f}")
    m4.metric("Arquivos", len(vb.arquivos_baixa) + len(ve.arquivos_estoque))

    for av in (vb.avisos or []) + (ve.avisos or []):
        st.warning(av)

    tab_b, tab_e, tab_w = st.tabs(["Baixas SAP", "Estoque SAP", "WhatsApp"])
    with tab_b:
        if baixas is not None and not baixas.empty:
            cols = ["codigo_sap", "quantidade", "conta_contabil", "centro_custo_sap", "categoria", "valor_total", "fonte"]
            cols = [c for c in cols if c in baixas.columns]
            st.dataframe(baixas[cols].head(100), use_container_width=True, hide_index=True)
        else:
            st.caption("Sem baixas neste envio — modo **somente estoque**." if state.get("modo_somente_estoque") else "Sem baixas.")
    with tab_e:
        if estoque is not None and not estoque.empty:
            st.dataframe(estoque.head(50), use_container_width=True, hide_index=True)
        else:
            st.caption("Nenhum estoque enviado — painel usará snapshot anterior.")
    with tab_w:
        if state["interpretado"]:
            s: SaidaInterpretada = state["interpretado"]
            st.write(f"Responsável: **{s.responsavel.valor or '—'}** | Destino: **{s.destino_texto or '—'}**")
            if s.itens:
                rows = [{
                    "Linha": it.texto_linha, "Produto": it.produto_texto,
                    "Qtd": it.quantidade, "SAP": (it.produto_match.valor or {}).get("codigo_sap", "—"),
                } for it in s.itens]
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.caption("Modo somente SAP — WhatsApp não informado.")

    if baixas is not None and not baixas.empty:
        st.markdown('<div class="sec">Análise Python</div>', unsafe_allow_html=True)
        plot_timeline(baixas)
        plot_heatmap(baixas)

    c1, c2, _ = st.columns([1, 1, 3])
    with c1:
        if st.button("← Voltar"):
            state["etapa"] = 1
            st.rerun()
    with c2:
        if st.button("Conferir →", type="primary"):
            state["etapa"] = 3
            st.rerun()

# ── ③ CONFERIR ─────────────────────────────────────────────────────────────
elif state["etapa"] == 3:
    st.markdown('<div class="sec">Conferência — corrija se necessário</div>', unsafe_allow_html=True)

    if state["usar_whatsapp"] and state["form_itens"]:
        form = state["form_itens"]
        form["responsavel"] = st.text_input("Responsável", value=form.get("responsavel", ""))
        form["destino_texto"] = st.text_input("Destino", value=form.get("destino_texto", ""))
        form["data_referencia"] = st.date_input("Data saída", value=form.get("data_referencia", date.today()))
        locais = form.get("locais") or carregar_locais()
        loc_opts = {f"{l['id']} — {l['nome']}": l["id"] for l in locais}
        loc_labels = list(loc_opts.keys())
        loc_def = next((k for k in loc_labels if loc_opts[k] == form.get("local_id")), loc_labels[0] if loc_labels else "")
        sel = st.selectbox("Local", options=loc_labels or ["—"], index=loc_labels.index(loc_def) if loc_def in loc_labels else 0)
        form["local_id"] = loc_opts.get(sel)
        prod_labels = list((form.get("prod_opts") or {}).keys())
        novos = []
        for i, it in enumerate(form.get("itens") or []):
            c1, c2, c3 = st.columns([3, 1, 1])
            idx = prod_labels.index(it["produto_label"]) if it.get("produto_label") in prod_labels else 0
            sel_p = c1.selectbox(f"Produto {i+1}", prod_labels or ["—"], index=idx, key=f"cp_{i}")
            qtd = c2.number_input("Qtd", value=float(it.get("quantidade", 1)), key=f"cq_{i}")
            un = c3.text_input("Un", value=it.get("unidade", "L"), key=f"cu_{i}")
            novos.append({**it, "produto_label": sel_p, "quantidade": qtd, "unidade": un})
        form["itens"] = novos
        state["form_itens"] = form
        state["conciliar_whatsapp"] = st.checkbox(
            "Conciliar WhatsApp × SAP (medicamentos/defensivos)",
            value=True,
        )
    else:
        state["conciliar_whatsapp"] = False
        if state.get("modo_somente_estoque"):
            st.success("Modo **somente estoque** — atualiza saldo no painel Lovable.")
        else:
            st.success("Modo **somente SAP** — movimento contábil + estoque.")

    c1, c2, _ = st.columns([1, 1, 3])
    with c1:
        if st.button("← Voltar"):
            state["etapa"] = 2
            st.rerun()
    with c2:
        if st.button("Conciliar →", type="primary"):
            state["etapa"] = 4
            st.rerun()

# ── ④ CONCILIAR ─────────────────────────────────────────────────────────────
elif state["etapa"] == 4:
    st.markdown('<div class="sec">Prévia conciliação</div>', unsafe_allow_html=True)
    baixas = state["baixas_df"]

    if state["conciliar_whatsapp"] and baixas is not None and not baixas.empty:
        try:
            conn = conectar_psycopg2()
            prev = preview_conciliacao(baixas, conn)
            conn.close()
            state["preview_conc"] = prev
            c1, c2, c3 = st.columns(3)
            c1.metric("Match OK", len(prev.matches))
            c2.metric("Sem baixa SAP", len(prev.sem_baixa_sap))
            c3.metric("Extra SAP", len(prev.extra_sap))
            if prev.matches:
                st.dataframe(pd.DataFrame(prev.matches), use_container_width=True, hide_index=True)
            if prev.sem_baixa_sap:
                st.warning("Pendências WhatsApp sem baixa SAP:")
                st.dataframe(pd.DataFrame(prev.sem_baixa_sap), use_container_width=True, hide_index=True)
            if prev.extra_sap:
                st.info("Linhas SAP sem WhatsApp (normal para combustível/nutrição ou atraso de mensagem):")
                st.dataframe(pd.DataFrame(prev.extra_sap), use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"Erro conciliação: {e}")
    else:
        st.info("Conciliação WhatsApp desativada — importação direta movimento contábil + estoque.")

    c1, c2, _ = st.columns([1, 1, 3])
    with c1:
        if st.button("← Voltar"):
            state["etapa"] = 3
            st.rerun()
    with c2:
        if st.button("Registrar →", type="primary"):
            state["etapa"] = 5
            st.rerun()

# ── ⑤ REGISTRAR ─────────────────────────────────────────────────────────────
elif state["etapa"] == 5:
    if state.get("registro_ok") and state.get("resultado"):
        res = state["resultado"]
        st.success("Registro concluído — API alma-control-center atualizada.")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Movimentos SAP", res.movimentos_importados)
        c2.metric("Estoque campo", res.estoque_ok)
        c3.metric("Estoque lub", res.estoque_lub_ok)
        c4.metric("Lotes conciliados", res.lotes_conciliados)
        if res.estoque_skip or res.consumo_lub_marcados:
            st.caption(
                f"Ignorados catálogo campo: {res.estoque_skip} · "
                f"Consumo lub PWA marcado: {res.consumo_lub_marcados}"
            )
        if res.lote_whatsapp_id:
            st.caption(f"Lote WhatsApp: `{res.lote_whatsapp_id[:8]}…`")
        if res.api_refresh:
            st.json(res.api_refresh)
        if res.erros:
            for e in res.erros:
                st.error(e)
        st.markdown(
            "[Abrir painel alma-control-center ↗](https://alma-control-center.lovable.app/movimentacao)"
        )
        if state["baixas_df"] is not None and not state["baixas_df"].empty:
            plot_timeline(state["baixas_df"])
        if st.button("＋ Nova importação", type="primary"):
            reset_fluxo()
            st.rerun()
        st.stop()

    st.markdown('<div class="sec">Confirmar registro no Supabase</div>', unsafe_allow_html=True)
    baixas = state["baixas_df"]
    estoque = state["estoque_df"] if state["estoque_df"] is not None else pd.DataFrame()

    st.write(f"**Baixas:** {len(baixas)} linhas | **Estoque:** {len(estoque)} itens")
    st.write(f"Conciliar WhatsApp: **{'Sim' if state['conciliar_whatsapp'] else 'Não'}**")

    c1, c2, _ = st.columns([1, 1, 3])
    with c1:
        if st.button("← Voltar"):
            state["etapa"] = 4
            st.rerun()
    with c2:
        if st.button("Confirmar registro", type="primary"):
            with st.spinner("Gravando movimentos, estoque e refresh API…"):
                res = executar_registro(
                    baixas,
                    estoque,
                    conciliar_whatsapp=state["conciliar_whatsapp"],
                    whatsapp_form=state.get("form_itens"),
                    texto_whatsapp=state.get("texto_whatsapp") or "",
                    data_referencia=state.get("data_ref"),
                )
                state["resultado"] = res
                state["registro_ok"] = True
                if res.erros and not res.movimentos_importados and not res.estoque_ok:
                    st.error("; ".join(res.erros))
                else:
                    st.rerun()

with st.sidebar:
    st.markdown("### Motor Python")
    st.markdown(
        """
**Fluxo unificado**
1. **Entradas:** aba NF-e XML (compras)
2. **Saídas:** Excel SAP (baixas + estoque)
3. WhatsApp opcional
4. Validação + conciliação
5. Supabase + `api_alma_*`

**API Lovable**
- `api_alma_dashboard`
- `api_alma_movimentacao`
- `api_alma_estoque`
- `api_alma_timeline`
- `api_alma_conta_mes`
        """
    )
    if st.button("Reiniciar", key="sb_reset"):
        reset_fluxo()
        st.rerun()
    st.caption("Setup SQL: `sql/023_api_painel_alma.sql`")
