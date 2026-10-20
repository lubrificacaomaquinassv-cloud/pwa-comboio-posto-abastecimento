#!/usr/bin/env python3
"""
Carga DADOS_PAINEL -> Supabase (fonte oficial do painel online).

PC:
  python scripts/sync_excel_to_supabase.py --dados-dir "%USERPROFILE%\\Desktop\\DADOS_PAINEL"

CI / repo:
  python scripts/sync_excel_to_supabase.py --dados-dir dados
"""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from sqlalchemy import create_engine

from db.carga_supabase import executar_carga_supabase, sync_pasta_dados_painel
from ingestion.dados_painel import descobrir_arquivos_dados_painel


def main() -> None:
    p = argparse.ArgumentParser(description="Sincroniza Excel/KML com Supabase")
    p.add_argument("--dados-dir", help="Pasta DADOS_PAINEL (descobre KML + xlsx automaticamente)")
    p.add_argument("--kml", help="KML (opcional se GIS já estiver no Supabase)")
    p.add_argument("--cobertura", help="XLSX cobertura")
    p.add_argument("--base", help="XLSX base/subsolagem (opcional)")
    args = p.parse_args()

    url = os.environ.get("SUPABASE_DB_URL")
    if not url:
        print("Defina SUPABASE_DB_URL", file=sys.stderr)
        sys.exit(1)

    engine = create_engine(url)

    if args.dados_dir:
        print(f"Sincronizando pasta: {args.dados_dir}")
        stats = sync_pasta_dados_painel(engine, args.dados_dir)
    else:
        kml, cobertura, base = args.kml, args.cobertura, args.base
        if not cobertura:
            p.error("Informe --cobertura ou --dados-dir.")
        stats = executar_carga_supabase(engine, kml=kml, cobertura=cobertura, base=base)

    print(
        f"OK — talhões: {stats['talhoes']} | cobertura: {stats['cobertura']} | base: {stats['base']}"
    )


if __name__ == "__main__":
    main()
