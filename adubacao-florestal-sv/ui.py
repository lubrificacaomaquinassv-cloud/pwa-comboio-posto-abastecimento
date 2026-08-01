"""Visual Santa Virgínia — painéis operacionais."""
from __future__ import annotations

import html
from typing import Any

import pandas as pd
import streamlit as st

BG = "https://media.bio.site/sites/32a25c2c-d6fa-4dfc-bdc2-27e4d35d7ea2/AhS9mKiQxFRXAyMBdXDzEG.jpg"
VERDE = "#3d8b40"
VERDE_CLARO = "#8aab80"
CREME = "#e8edd0"
FUNDO = "rgba(17,28,16,.94)"


def css() -> None:
    st.markdown(
        f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow:wght@400;500;600;700&family=Barlow+Condensed:wght@600;700&display=swap');
.stApp {{
  background: linear-gradient(rgba(10,20,9,.9), rgba(10,20,9,.96)),
    url('{BG}') center/cover fixed !important;
  font-family: 'Barlow', sans-serif;
}}
[data-testid="stSidebar"] {{ background: rgba(12,22,11,.97) !important; border-right: 1px solid #2d5a30; }}
[data-testid="stSidebar"] .stMarkdown h3 {{ color: {CREME}; font-family: 'Barlow Condensed', sans-serif; }}
.block-container {{ padding-top: 1.2rem; max-width: 1400px; }}

.hero {{
  background: {FUNDO}; border: 1px solid #2d5a30; border-radius: 16px;
  padding: 22px 28px; margin-bottom: 14px;
  box-shadow: 0 8px 32px rgba(0,0,0,.35);
}}
.hero h1 {{
  font-family: 'Barlow Condensed', sans-serif; color: {CREME};
  font-size: 2.5rem; margin: 0; letter-spacing: .5px;
}}
.hero p {{ color: {VERDE_CLARO}; margin: 6px 0 0; font-size: 1rem; }}

.kpis {{
  display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 14px;
}}
.card {{
  background: {FUNDO}; border: 1px solid #1e2e1c; border-radius: 12px;
  padding: 14px 16px; position: relative; overflow: hidden;
}}
.card::before {{
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
  background: linear-gradient(90deg, {VERDE}, #6ab04c);
}}
.card small {{
  color: {VERDE_CLARO}; text-transform: uppercase; letter-spacing: 1.2px; font-size: 10px;
}}
.card strong {{
  display: block; font-family: 'Barlow Condensed', sans-serif;
  font-size: 1.9rem; color: {CREME}; margin-top: 4px;
}}

.panel {{
  background: {FUNDO}; border: 1px solid #243824; border-radius: 14px;
  padding: 18px 20px; margin-bottom: 14px;
}}
.panel-title {{
  font-family: 'Barlow Condensed', sans-serif; color: {CREME};
  font-size: 1.35rem; margin: 0 0 4px; letter-spacing: .3px;
}}
.panel-sub {{ color: {VERDE_CLARO}; font-size: .92rem; margin: 0 0 14px; }}

.legenda {{
  display: flex; gap: 18px; flex-wrap: wrap; margin-bottom: 10px;
}}
.legenda span {{
  display: inline-flex; align-items: center; gap: 7px;
  color: {CREME}; font-size: .9rem;
}}
.dot {{
  width: 12px; height: 12px; border-radius: 3px; display: inline-block;
  border: 1px solid rgba(255,255,255,.35);
}}

.badge {{
  display: inline-block; padding: 4px 10px; border-radius: 999px;
  font-size: 12px; font-weight: 600; letter-spacing: .3px;
}}
.badge-ok {{ background: rgba(46,204,113,.18); color: #6ee08a; border: 1px solid #2ecc71; }}
.badge-pend {{ background: rgba(231,76,60,.15); color: #ff8a7a; border: 1px solid #e74c3c; }}
.badge-neutro {{ background: rgba(127,140,141,.15); color: #b8c4c4; border: 1px solid #7f8c8d; }}

.ficha-grid {{
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 12px;
}}
.ficha-item {{
  background: rgba(8,14,7,.65); border: 1px solid #1e2e1c; border-radius: 10px; padding: 12px;
}}
.ficha-item small {{ color: {VERDE_CLARO}; font-size: 10px; text-transform: uppercase; letter-spacing: 1px; }}
.ficha-item strong {{ display: block; color: {CREME}; font-size: 1.05rem; margin-top: 4px; }}

.npk-hero {{
  background: linear-gradient(135deg, rgba(26,61,28,.95), rgba(17,40,18,.98));
  border: 1px solid #3d8b40; border-radius: 16px; padding: 24px 28px; margin-bottom: 18px;
  box-shadow: 0 12px 40px rgba(0,0,0,.4);
}}
.npk-hero h2 {{
  font-family: 'Barlow Condensed', sans-serif; color: {CREME};
  font-size: 2rem; margin: 0 0 6px;
}}
.npk-hero p {{ color: {VERDE_CLARO}; margin: 0; }}

.npk-result {{
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 16px;
}}
.npk-box {{
  background: rgba(8,14,7,.7); border: 1px solid #2d5a30; border-radius: 12px;
  padding: 16px; text-align: center;
}}
.npk-box small {{ color: {VERDE_CLARO}; text-transform: uppercase; letter-spacing: 1px; font-size: 10px; }}
.npk-box strong {{
  display: block; font-family: 'Barlow Condensed', sans-serif;
  font-size: 2rem; color: {CREME}; margin-top: 6px;
}}
.npk-box span {{ color: #9bc49a; font-size: .85rem; }}

div[data-testid="stTabs"] button[data-baseweb="tab"] {{
  font-family: 'Barlow Condensed', sans-serif; font-size: 1.05rem;
  color: {VERDE_CLARO} !important; padding: 10px 18px;
}}
div[data-testid="stTabs"] button[aria-selected="true"] {{
  color: {CREME} !important; border-bottom-color: {VERDE} !important;
}}

@media (max-width: 900px) {{
  .kpis {{ grid-template-columns: repeat(2, 1fr); }}
  .ficha-grid {{ grid-template-columns: repeat(2, 1fr); }}
  .npk-result {{ grid-template-columns: 1fr; }}
}}
</style>""",
        unsafe_allow_html=True,
    )


def hero(t: str, s: str) -> None:
    st.markdown(f'<div class="hero"><h1>{html.escape(t)}</h1><p>{html.escape(s)}</p></div>', unsafe_allow_html=True)


def kpis(d: dict) -> None:
    items = [
        ("Talhões", d["talhoes"]),
        ("Concluídos", d["ok"]),
        ("Pendentes", d["pend"]),
        ("Ha feita", f'{d["ha_feita"]:,.0f}'.replace(",", ".")),
        ("Ha restante", f'{d["ha_rest"]:,.0f}'.replace(",", ".")),
    ]
    bloco = "".join(f'<div class="card"><small>{a}</small><strong>{b}</strong></div>' for a, b in items)
    st.markdown(f'<div class="kpis">{bloco}</div>', unsafe_allow_html=True)


def legenda_mapa() -> None:
    st.markdown(
        """
<div class="legenda">
  <span><i class="dot" style="background:#2ecc71"></i> Concluído — clique no talhão para ver detalhes</span>
  <span><i class="dot" style="background:#e74c3c"></i> Pendente</span>
  <span><i class="dot" style="background:#7f8c8d"></i> Sem registro na planilha</span>
</div>""",
        unsafe_allow_html=True,
    )


def badge_status(status: str) -> str:
    cls = {"concluido": "badge-ok", "pendente": "badge-pend"}.get(status, "badge-neutro")
    label = {"concluido": "Concluído", "pendente": "Pendente", "sem_dado": "Sem registro"}.get(status, status)
    return f'<span class="badge {cls}">{html.escape(label)}</span>'


def ficha_talhao(row: pd.Series, servico_label: str) -> None:
    pct = 0.0
    if row.get("area_ha"):
        pct = min(100.0, 100.0 * float(row.get("area_feita", 0)) / float(row["area_ha"]))
    st.markdown(
        f"""
<div class="panel">
  <div class="panel-title">Talhão {html.escape(str(row.talhao))} · Retiro {html.escape(str(row.get('retiro', '—')))}</div>
  <div class="panel-sub">{html.escape(servico_label)} · {badge_status(str(row.get('status', 'sem_dado')))}</div>
  <div class="ficha-grid">
    <div class="ficha-item"><small>Área cadastro</small><strong>{row.area_ha:.1f} ha</strong></div>
    <div class="ficha-item"><small>Área feita</small><strong>{row.area_feita:.1f} ha</strong></div>
    <div class="ficha-item"><small>Área restante</small><strong>{row.area_rest:.1f} ha</strong></div>
    <div class="ficha-item"><small>Progresso</small><strong>{pct:.0f}%</strong></div>
    <div class="ficha-item"><small>Fertilizante</small><strong>{html.escape(str(row.get('fertilizante', '—')))}</strong></div>
    <div class="ficha-item"><small>Data</small><strong>{html.escape(str(row.get('data_fmt', '—')))}</strong></div>
    <div class="ficha-item"><small>Dosagem</small><strong>{html.escape(str(row.get('dosagem', '—')))}{' kg/ha' if str(row.get('dosagem','—')) != '—' else ''}</strong></div>
    <div class="ficha-item"><small>Operador / Prestador</small><strong>{html.escape(str(row.get('operador') if row.get('operador') not in (None,'—') else row.get('prestador', '—')))}</strong></div>
  </div>
</div>""",
        unsafe_allow_html=True,
    )


def tabela(df: pd.DataFrame, h: int = 400, destaque: str | None = None) -> None:
    if df.empty:
        st.info("Sem registros para este filtro.")
        return
    ren = {
        "talhao": "Talhão", "retiro": "Retiro", "status_label": "Status",
        "area_ha": "Área ha", "area_feita": "Feito ha", "area_rest": "Restante ha",
        "fertilizante": "Fertilizante", "data_fmt": "Data", "dosagem": "Dosagem kg/ha",
        "operador": "Operador", "prestador": "Prestador", "horto": "Retiro",
    }
    view = df.rename(columns=ren)
    head = "".join(
        f"<th style='padding:9px 10px;background:#152012;color:#8aab80;text-align:left;"
        f"font-size:11px;text-transform:uppercase;letter-spacing:.8px;position:sticky;top:0'>"
        f"{html.escape(str(c))}</th>"
        for c in view.columns
    )
    body = ""
    for _, row in view.iterrows():
        tal = str(row.get("Talhão", row.iloc[0]))
        bg = "background:#1a3020;" if destaque and tal == destaque else ""
        cells = "".join(
            f"<td style='padding:8px 10px;border-bottom:1px solid #1e2e1c;color:#e8edd0;{bg}'>"
            f"{html.escape('—' if pd.isna(v) else str(v))}</td>"
            for v in row
        )
        body += f"<tr>{cells}</tr>"
    st.markdown(
        f"<div style='max-height:{h}px;overflow:auto;border:1px solid #243824;border-radius:10px'>"
        f"<table width='100%' style='border-collapse:collapse;background:#0d180c;font-size:.92rem'>"
        f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>",
        unsafe_allow_html=True,
    )


def calc_npk_resultado(r: Any, formula: str, kg_ha: float, area_ha: float) -> None:
    st.markdown(
        f"""
<div class="npk-result">
  <div class="npk-box"><small>Nitrogênio (N)</small><strong>{r.n_total:,.0f} kg</strong>
    <span>{r.n_kg_ha:.1f} kg/ha · {r.n_pct:.0f}% na fórmula</span></div>
  <div class="npk-box"><small>Fósforo (P₂O₅)</small><strong>{r.p_total:,.0f} kg</strong>
    <span>{r.p_kg_ha:.1f} kg/ha · {r.p_pct:.0f}% na fórmula</span></div>
  <div class="npk-box"><small>Potássio (K₂O)</small><strong>{r.k_total:,.0f} kg</strong>
    <span>{r.k_kg_ha:.1f} kg/ha · {r.k_pct:.0f}% na fórmula</span></div>
</div>
<div class="panel" style="margin-top:14px">
  <div class="ficha-grid" style="grid-template-columns:repeat(3,1fr)">
    <div class="ficha-item"><small>Fórmula</small><strong>{html.escape(formula)}</strong></div>
    <div class="ficha-item"><small>Dose aplicada</small><strong>{kg_ha:.0f} kg/ha</strong></div>
    <div class="ficha-item"><small>Área considerada</small><strong>{area_ha:.1f} ha</strong></div>
    <div class="ficha-item"><small>Adubo total</small><strong>{r.adubo_total:,.0f} kg</strong></div>
    <div class="ficha-item"><small>Equivalente NPK</small><strong>{r.n_pct:.0f}-{r.p_pct:.0f}-{r.k_pct:.0f}</strong></div>
    <div class="ficha-item"><small>Referência</small><strong>% peso na fórmula comercial</strong></div>
  </div>
</div>""".replace(",", "."),
        unsafe_allow_html=True,
    )
