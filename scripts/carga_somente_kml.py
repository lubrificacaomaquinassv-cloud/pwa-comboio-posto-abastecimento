#!/usr/bin/env python3
"""Grava polígonos do KML em dim_talhao_florestal (1x)."""
from __future__ import annotations

import argparse
import os
import sys
from urllib.parse import quote_plus, unquote, urlparse, urlunparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from sqlalchemy import create_engine, text

from db.secrets_helper import POOLER_HOSTS_DEFAULT, _build_url
from db.supabase_io import gravar_talhoes
from ingestion.kml_parser import ler_talhoes_kml


def _urls_candidatas() -> list[str]:
    raw = os.environ.get("SUPABASE_DB_URL", "").strip()
    out: list[str] = []
    if raw:
        out.append(raw)
        # Re-encode senha se URL foi montada na mão com caracteres especiais
        if "@" in raw and "://" in raw:
            try:
                p = urlparse(raw.replace("postgresql+psycopg://", "postgresql://", 1))
                if p.password:
                    netloc = f"{p.username}:{quote_plus(unquote(p.password))}@{p.hostname}"
                    if p.port:
                        netloc += f":{p.port}"
                    fixed = urlunparse((p.scheme, netloc, p.path, "", "", ""))
                    fixed = fixed.replace("postgresql://", "postgresql+psycopg://", 1)
                    if fixed not in out:
                        out.append(fixed)
            except Exception:
                pass
    ref = os.environ.get("SUPABASE_PROJECT_REF", "azhpxhrwhegfysoeqmft")
    senha = os.environ.get("SUPABASE_DB_PASSWORD", "")
    if senha:
        for host in POOLER_HOSTS_DEFAULT:
            u = _build_url(ref, senha, host)
            if u not in out:
                out.append(u)
    return out


def _conectar():
    erros = []
    for url in _urls_candidatas():
        try:
            engine = create_engine(url, pool_pre_ping=True)
            with engine.connect() as conn:
                db = conn.execute(text("select current_database()")).scalar()
                host = conn.execute(text("select inet_server_addr()::text")).scalar()
            print(f"Conectado: db={db} host={host}")
            return engine
        except Exception as exc:
            erros.append(f"{url[:50]}... -> {exc}")
    print("Falha em todas as URLs:", file=sys.stderr)
    for e in erros:
        print(e, file=sys.stderr)
    sys.exit(1)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--kml", required=True)
    args = p.parse_args()
    if not os.path.isfile(args.kml):
        print(f"Arquivo nao encontrado: {args.kml}", file=sys.stderr)
        sys.exit(1)

    gdf = ler_talhoes_kml(args.kml)
    gdf = gdf[gdf["talhao"].notna()].copy()
    print(f"KML: {len(gdf)} poligonos com talhao.")
    if gdf.empty:
        print("ERRO: KML vazio para o parser. Rode: python scripts/testar_kml.py", file=sys.stderr)
        sys.exit(1)

    engine = _conectar()
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))

    n = gravar_talhoes(engine, gdf)
    with engine.connect() as conn:
        total = conn.execute(
            text("SELECT count(*) FROM dim_talhao_florestal WHERE geom IS NOT NULL")
        ).scalar()
    print(f"Gravados nesta execucao: {n} | total no banco: {total}")
    if not total:
        sys.exit("Banco ainda vazio apos gravar — DBeaver esta no MESMO projeto Supabase?")
    print("OK. Rode sql/005 no DBeaver + Reboot Streamlit.")


if __name__ == "__main__":
    main()
