#!/usr/bin/env python3
"""Grava polígonos do KML em dim_talhao_florestal (1x). Nao precisa de planilha."""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from sqlalchemy import create_engine, text

from db.supabase_io import gravar_talhoes
from ingestion.kml_parser import ler_talhoes_kml


def main() -> None:
    p = argparse.ArgumentParser(description="KML -> dim_talhao_florestal (mapa Streamlit)")
    p.add_argument("--kml", required=True, help="Caminho do .kml da fazenda")
    args = p.parse_args()

    url = os.environ.get("SUPABASE_DB_URL")
    if not url:
        print("Defina SUPABASE_DB_URL (senha Database do Supabase, pooler :6543)", file=sys.stderr)
        sys.exit(1)

    if not os.path.isfile(args.kml):
        print(f"Arquivo nao encontrado: {args.kml}", file=sys.stderr)
        sys.exit(1)

    engine = create_engine(url)
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        conn.commit()

    gdf = ler_talhoes_kml(args.kml)
    gdf = gdf[gdf["talhao"].notna()].copy()
    n = gravar_talhoes(engine, gdf)
    print(f"OK: {n} talhoes com poligono em dim_talhao_florestal.")
    print("Agora rode sql/005_api_mapa_talhoes.sql no Supabase e Reboot no Streamlit.")


if __name__ == "__main__":
    main()
