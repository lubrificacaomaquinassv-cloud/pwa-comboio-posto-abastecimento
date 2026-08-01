"""Visual Santa Virgínia."""
from __future__ import annotations

import html
import pandas as pd
import streamlit as st

BG = "https://media.bio.site/sites/32a25c2c-d6fa-4dfc-bdc2-27e4d35d7ea2/AhS9mKiQxFRXAyMBdXDzEG.jpg"


def css() -> None:
    st.markdown(
        f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700&display=swap');
.stApp{{background:linear-gradient(rgba(10,20,9,.88),rgba(10,20,9,.95)),url('{BG}') center/cover fixed!important}}
[data-testid="stSidebar"]{{background:rgba(17,28,16,.96)!important}}
.hero{{background:rgba(17,28,16,.95);border:1px solid #2d5a30;border-radius:14px;padding:24px 28px;margin-bottom:16px}}
.hero h1{{font-family:'Barlow Condensed',sans-serif;color:#e8edd0;font-size:2.4rem;margin:0}}
.hero p{{color:#8aab80;margin:6px 0 0}}
.kpis{{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-bottom:16px}}
.card{{background:rgba(17,28,16,.94);border:1px solid #1e2e1c;border-radius:10px;padding:14px}}
.card small{{color:#8aab80;text-transform:uppercase;letter-spacing:1px;font-size:10px}}
.card strong{{display:block;font-family:'Barlow Condensed',sans-serif;font-size:1.8rem;color:#e8edd0;margin-top:4px}}
</style>""",
        unsafe_allow_html=True,
    )


def hero(t, s):
    st.markdown(f'<div class="hero"><h1>{t}</h1><p>{s}</p></div>', unsafe_allow_html=True)


def kpis(d):
    items = [
        ("Talhões", d["talhoes"]),
        ("Concluídos", d["ok"]),
        ("Pendentes", d["pend"]),
        ("Ha feita", f'{d["ha_feita"]:,.0f}'.replace(",", ".")),
        ("Ha restante", f'{d["ha_rest"]:,.0f}'.replace(",", ".")),
    ]
    h = '<div class="kpis">' + "".join(
        f'<div class="card"><small>{a}</small><strong>{b}</strong></div>' for a, b in items
    ) + "</div>"
    st.markdown(h, unsafe_allow_html=True)


def tabela(df, h=400):
    if df.empty:
        st.info("Sem dados.")
        return
    head = "".join(
        f"<th style='padding:8px;background:#111c10;color:#8aab80'>{html.escape(str(c))}</th>" for c in df.columns
    )
    body = "".join(
        "<tr>"
        + "".join(
            f"<td style='padding:7px;border-bottom:1px solid #1e2e1c;color:#e8edd0'>"
            f"{html.escape('—' if pd.isna(v) else str(v))}</td>"
            for v in row
        )
        + "</tr>"
        for _, row in df.iterrows()
    )
    st.markdown(
        f"<div style='max-height:{h}px;overflow:auto;border:1px solid #1e2e1c;border-radius:8px'>"
        f"<table width='100%' style='border-collapse:collapse;background:#0d180c'>"
        f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>",
        unsafe_allow_html=True,
    )
