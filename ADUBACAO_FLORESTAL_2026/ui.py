"""Identidade visual Santa Virgínia — igual linha dos painéis SV."""
from __future__ import annotations

import html as html_lib

import pandas as pd
import streamlit as st

# Mesma base visual do Painel Estratégico SV
BG_URL = "https://media.bio.site/sites/32a25c2c-d6fa-4dfc-bdc2-27e4d35d7ea2/AhS9mKiQxFRXAyMBdXDzEG.jpg"


def inject_styles() -> None:
    st.markdown(
        f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700&display=swap');

.stApp {{
  background: linear-gradient(rgba(10,20,9,0.86), rgba(10,20,9,0.94)),
    url('{BG_URL}') center/cover no-repeat fixed !important;
}}
[data-testid="stAppViewContainer"] {{ background: transparent !important; }}
[data-testid="stSidebar"] {{
  background: rgba(17,28,16,0.96) !important;
  border-right: 1px solid #1e2e1c;
}}
[data-testid="stHeader"] {{ background: rgba(10,20,9,0.9) !important; }}
#MainMenu, footer, header[data-testid="stHeader"] {{ visibility: hidden; height: 0; }}
.block-container {{ padding-top: 0.8rem; max-width: 1480px; }}

h1,h2,h3,label,p,span {{ color: #e8edd0 !important; }}
.stCaption,[data-testid="stCaptionContainer"] p {{ color: #8aab80 !important; }}

.hero {{
  background: linear-gradient(135deg, rgba(17,36,22,0.97), rgba(10,22,12,0.92));
  border: 1px solid #2d5a30;
  border-radius: 16px;
  padding: 28px 32px;
  margin-bottom: 20px;
  box-shadow: 0 12px 40px rgba(0,0,0,0.35);
}}
.hero-eyebrow {{
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 12px; font-weight: 700; letter-spacing: 3px;
  text-transform: uppercase; color: #6fcf60; margin-bottom: 8px;
}}
.hero-title {{
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 2.6rem; font-weight: 700; color: #f4f7ea;
  line-height: 1.05; margin: 0;
}}
.hero-sub {{ font-size: 1rem; color: #a8c4a0; margin-top: 10px; }}
.hero-meta {{
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 11px; letter-spacing: 1.5px; color: #6a8a62;
  margin-top: 12px; text-transform: uppercase;
}}

.sec {{
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 12px; font-weight: 700; letter-spacing: 2px;
  text-transform: uppercase; color: #8aab80;
  border-left: 4px solid #4a9e3f; padding-left: 10px;
  margin: 16px 0 10px;
}}

.kpi-grid {{
  display: grid; grid-template-columns: repeat(5, 1fr);
  gap: 14px; margin-bottom: 20px;
}}
@media (max-width: 1200px) {{ .kpi-grid {{ grid-template-columns: repeat(2, 1fr); }} }}
.kpi-card {{
  background: rgba(17,28,16,0.94); border: 1px solid #1e2e1c;
  border-radius: 12px; padding: 18px 20px;
  box-shadow: inset 0 1px 0 rgba(111,207,96,0.08);
}}
.kpi-lab {{
  font-family: 'Barlow Condensed', sans-serif; font-size: 11px;
  color: #8aab80; letter-spacing: 1.2px; text-transform: uppercase;
}}
.kpi-val {{
  font-family: 'Barlow Condensed', sans-serif; font-size: 2rem;
  font-weight: 700; color: #e8edd0; margin-top: 6px; line-height: 1;
}}
.kpi-sub {{ font-size: 11px; color: #6fcf60; margin-top: 8px; }}

.legend {{
  display: flex; gap: 20px; flex-wrap: wrap;
  background: rgba(17,28,16,0.9); border: 1px solid #1e2e1c;
  border-radius: 10px; padding: 12px 18px; margin-bottom: 14px;
  font-size: 13px; color: #b8ccb0;
}}
.dot {{ width: 11px; height: 11px; border-radius: 50%; display: inline-block; margin-right: 6px; }}

.stTabs [data-baseweb="tab-list"] {{
  background: rgba(17,28,16,0.92); border-bottom: 2px solid #1e2e1c;
}}
.stTabs [data-baseweb="tab"] {{
  color: #5a7a52; font-family: 'Barlow Condensed', sans-serif;
  font-size: 12px; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase;
}}
.stTabs [aria-selected="true"] {{
  color: #6fcf60 !important; border-bottom: 3px solid #4a9e3f !important;
}}

.stButton button {{
  background: #4a9e3f !important; color: #fff !important;
  border: 1px solid #6fcf60 !important;
  font-family: 'Barlow Condensed', sans-serif; font-weight: 700;
  letter-spacing: 1px; text-transform: uppercase; border-radius: 8px;
}}

.map-box {{
  border: 1px solid #1e2e1c; border-radius: 12px; overflow: hidden;
  box-shadow: 0 8px 24px rgba(0,0,0,0.3);
}}
</style>
        """,
        unsafe_allow_html=True,
    )


def render_hero(title: str, subtitle: str, build: str) -> None:
    st.markdown(
        f"""
<div class="hero">
  <div class="hero-eyebrow">Santa Virgínia · Operações florestais 2026</div>
  <h1 class="hero-title">{title}</h1>
  <div class="hero-sub">{subtitle}</div>
  <div class="hero-meta">Build {build}</div>
</div>
        """,
        unsafe_allow_html=True,
    )


def section(title: str, *, sidebar: bool = False) -> None:
    target = st.sidebar if sidebar else st
    target.markdown(f'<div class="sec">{title}</div>', unsafe_allow_html=True)


def render_kpis(kpis: dict) -> None:
    pct = (kpis["area_feita_ha"] / kpis["area_total_ha"] * 100) if kpis["area_total_ha"] else 0
    cards = [
        ("Talhões GIS", kpis["talhoes_gis"], "cadastro"),
        ("Concluídos", kpis["concluidos"], "registrados"),
        ("Pendentes", kpis["pendentes"], "a fazer"),
        ("Área feita", f"{kpis['area_feita_ha']:,.0f} ha".replace(",", "."), f"{pct:.0f}%"),
        ("Restante", f"{kpis['area_restante_ha']:,.0f} ha".replace(",", "."), "saldo"),
    ]
    html = '<div class="kpi-grid">'
    for lab, val, sub in cards:
        html += (
            f'<div class="kpi-card"><div class="kpi-lab">{lab}</div>'
            f'<div class="kpi-val">{val}</div><div class="kpi-sub">{sub}</div></div>'
        )
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def render_legend() -> None:
    st.markdown(
        """
<div class="legend">
  <span><i class="dot" style="background:#2ecc71"></i>Concluído</span>
  <span><i class="dot" style="background:#e74c3c"></i>Pendente</span>
  <span><i class="dot" style="background:#95a5a6"></i>Sem registro</span>
</div>
        """,
        unsafe_allow_html=True,
    )


def _fmt_cell(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    if isinstance(value, pd.Timestamp):
        return value.strftime("%d/%m/%Y")
    return html_lib.escape(str(value))


def dark_table(df, height: int = 360) -> None:
    if df is None or df.empty:
        st.info("Sem dados.")
        return
    rows = "".join(
        "<tr>"
        + "".join(
            f'<td style="padding:8px 10px;border-bottom:1px solid #1e2e1c;color:#e8edd0;font-size:12px;">{_fmt_cell(v)}</td>'
            for v in row
        )
        + "</tr>"
        for _, row in df.iterrows()
    )
    headers = "".join(
        f'<th style="padding:8px 10px;background:#111c10;color:#8aab80;font-size:10px;'
        f'font-weight:700;text-transform:uppercase;letter-spacing:1px;border-bottom:2px solid #1e2e1c;">'
        f"{html_lib.escape(str(c))}</th>"
        for c in df.columns
    )
    st.markdown(
        f'<div class="map-box" style="max-height:{height}px;overflow:auto;">'
        f'<table style="width:100%;border-collapse:collapse;background:#0d180c;'
        f'font-family:Barlow Condensed,sans-serif;">'
        f"<thead><tr>{headers}</tr></thead><tbody>{rows}</tbody></table></div>",
        unsafe_allow_html=True,
    )
