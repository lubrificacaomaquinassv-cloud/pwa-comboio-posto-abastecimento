"""Identidade visual Santa Virgínia — painel florestal."""
from __future__ import annotations

import streamlit as st

BG_URL = (
    "https://images.unsplash.com/photo-1441974231531-c6227db76b6e"
    "?auto=format&fit=crop&w=1920&q=80"
)

STATUS_LABEL = {
    "concluido": "Concluído",
    "pendente": "Pendente",
    "sem_dado": "Sem registro",
}


def inject_styles() -> None:
    st.markdown(
        f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700&family=Barlow:wght@400;500;600&display=swap');

.stApp {{
  background: linear-gradient(rgba(8, 18, 10, 0.88), rgba(8, 18, 10, 0.94)),
    url('{BG_URL}') center center / cover no-repeat fixed !important;
}}
[data-testid="stAppViewContainer"] {{ background: transparent !important; }}
[data-testid="stSidebar"] {{
  background: rgba(12, 24, 14, 0.96) !important;
  border-right: 1px solid #1a3320;
}}
[data-testid="stHeader"] {{ background: rgba(8, 18, 10, 0.9) !important; }}
#MainMenu, footer, [data-testid="stToolbar"] {{ visibility: hidden; }}
.block-container {{ padding-top: 1.2rem; max-width: 1400px; }}

h1, h2, h3, label, p, span {{ color: #e8edd0; }}
.stCaption, [data-testid="stCaptionContainer"] p {{ color: #8aab80 !important; }}

.hero {{
  background: linear-gradient(135deg, rgba(17, 36, 22, 0.95), rgba(10, 22, 12, 0.88));
  border: 1px solid #25442b;
  border-radius: 14px;
  padding: 22px 26px;
  margin-bottom: 18px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.25);
}}
.hero-eyebrow {{
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 2.5px;
  text-transform: uppercase;
  color: #6fcf60;
  margin-bottom: 6px;
}}
.hero-title {{
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 2.1rem;
  font-weight: 700;
  color: #f2f6e8;
  line-height: 1.1;
  margin: 0;
}}
.hero-sub {{
  font-family: 'Barlow', sans-serif;
  font-size: 0.95rem;
  color: #9bb892;
  margin-top: 8px;
}}
.hero-meta {{
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 11px;
  letter-spacing: 1px;
  color: #5a7a52;
  margin-top: 10px;
  text-transform: uppercase;
}}

.sec {{
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: #8aab80;
  border-left: 4px solid #4a9e3f;
  padding-left: 10px;
  margin: 18px 0 12px;
}}

.kpi-grid {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 18px; }}
@media (max-width: 1100px) {{ .kpi-grid {{ grid-template-columns: repeat(2, 1fr); }} }}
.kpi-card {{
  background: rgba(14, 28, 17, 0.94);
  border: 1px solid #1e3424;
  border-radius: 12px;
  padding: 16px 18px;
  min-height: 92px;
}}
.kpi-lab {{
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 11px;
  color: #8aab80;
  letter-spacing: 1.2px;
  text-transform: uppercase;
  margin-bottom: 6px;
}}
.kpi-val {{
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 1.65rem;
  font-weight: 700;
  color: #f0f4e6;
  line-height: 1.1;
}}
.kpi-sub {{ font-size: 11px; color: #6fcf60; margin-top: 6px; }}

.legend {{
  display: flex; gap: 18px; flex-wrap: wrap;
  background: rgba(14, 28, 17, 0.85);
  border: 1px solid #1e3424;
  border-radius: 10px;
  padding: 10px 16px;
  margin-bottom: 12px;
  font-family: 'Barlow', sans-serif;
  font-size: 12px;
  color: #b8ccb0;
}}
.legend span {{ display: inline-flex; align-items: center; gap: 6px; }}
.dot {{ width: 10px; height: 10px; border-radius: 50%; display: inline-block; }}

.stTabs [data-baseweb="tab-list"] {{
  background: rgba(14, 28, 17, 0.92);
  border-bottom: 2px solid #1e3424;
  gap: 0;
  border-radius: 10px 10px 0 0;
}}
.stTabs [data-baseweb="tab"] {{
  color: #5a7a52;
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  padding: 12px 22px;
}}
.stTabs [aria-selected="true"] {{
  color: #6fcf60 !important;
  border-bottom: 3px solid #4a9e3f !important;
}}

.stButton button {{
  background: linear-gradient(180deg, #4a9e3f, #3d8534) !important;
  color: #fff !important;
  border: 1px solid #6fcf60 !important;
  font-family: 'Barlow Condensed', sans-serif;
  font-weight: 700;
  letter-spacing: 1px;
  text-transform: uppercase;
  border-radius: 8px;
}}
.stButton button:hover {{ background: #357a2e !important; }}

div[data-testid="stMetricContainer"] {{
  background: rgba(14, 28, 17, 0.92);
  border: 1px solid #1e3424;
  border-radius: 10px;
  padding: 12px;
}}
</style>
        """,
        unsafe_allow_html=True,
    )


def render_hero(title: str, subtitle: str, build: str) -> None:
    st.markdown(
        f"""
<div class="hero">
  <div class="hero-eyebrow">Operações florestais · 2026</div>
  <h1 class="hero-title">{title}</h1>
  <div class="hero-sub">{subtitle}</div>
  <div class="hero-meta">Santa Virgínia · build {build}</div>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_kpis(kpis: dict) -> None:
    pct = 0.0
    if kpis["area_total_ha"] > 0:
        pct = kpis["area_feita_ha"] / kpis["area_total_ha"] * 100

    cards = [
        ("Talhões mapeados", f"{kpis['talhoes_gis']:,}".replace(",", "."), "Cadastro GIS"),
        ("Concluídos", f"{kpis['concluidos']:,}".replace(",", "."), "Serviço registrado"),
        ("Pendentes", f"{kpis['pendentes']:,}".replace(",", "."), "A executar"),
        ("Área concluída", f"{kpis['area_feita_ha']:,.1f} ha".replace(",", "X").replace(".", ",").replace("X", "."), f"{pct:.1f}% do total"),
        ("Área restante", f"{kpis['area_restante_ha']:,.1f} ha".replace(",", "X").replace(".", ",").replace("X", "."), "Saldo operacional"),
    ]
    html = '<div class="kpi-grid">'
    for lab, val, sub in cards:
        html += f"""
<div class="kpi-card">
  <div class="kpi-lab">{lab}</div>
  <div class="kpi-val">{val}</div>
  <div class="kpi-sub">{sub}</div>
</div>"""
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def render_legend() -> None:
    st.markdown(
        """
<div class="legend">
  <span><i class="dot" style="background:#2ecc71"></i> Concluído</span>
  <span><i class="dot" style="background:#e74c3c"></i> Pendente</span>
  <span><i class="dot" style="background:#95a5a6"></i> Sem registro na planilha</span>
</div>
        """,
        unsafe_allow_html=True,
    )


def section(title: str) -> None:
    st.markdown(f'<div class="sec">{title}</div>', unsafe_allow_html=True)


def dark_table(df, height: int = 360) -> None:
    import pandas as pd

    if df is None or df.empty:
        st.info("Sem dados para exibir.")
        return
    rows = "".join(
        "<tr>"
        + "".join(
            f'<td style="padding:7px 10px;border-bottom:1px solid #1e3424;color:#e8edd0;font-size:12px;">{v}</td>'
            for v in row
        )
        + "</tr>"
        for _, row in df.iterrows()
    )
    headers = "".join(
        f'<th style="padding:8px 10px;background:#0e1c11;color:#8aab80;font-size:10px;'
        f'font-weight:700;text-transform:uppercase;letter-spacing:1px;border-bottom:2px solid #25442b;">{c}</th>'
        for c in df.columns
    )
    st.markdown(
        f'<div style="max-height:{height}px;overflow:auto;border:1px solid #1e3424;border-radius:10px;">'
        f'<table style="width:100%;border-collapse:collapse;background:#0a140c;'
        f'font-family:Barlow,sans-serif;"><thead><tr>{headers}</tr></thead>'
        f"<tbody>{rows}</tbody></table></div>",
        unsafe_allow_html=True,
    )
