#!/usr/bin/env python3
"""
Carga local: planilhas DADOS_PAINEL -> Supabase.

Uso:
  export SUPABASE_DB_URL='postgresql+psycopg://...'
  python scripts/sync_excel_to_supabase.py \\
    --kml /caminho/fazenda_santa_virginia_completo.kml \\
    --cobertura /caminho/cobertura.xlsx \\
    --base /caminho/base.xlsx
"""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from sqlalchemy import create_engine

from db.supabase_io import carregar_talhoes_geom, gravar_base, gravar_cobertura, gravar_talhoes
from ingestion.excel_parser import ler_adubacao_base, ler_adubacao_cobertura
from ingestion.kml_parser import ler_talhoes_kml
from npk_calculator import aplicar_calculadora_no_df


def main() -> None:
    p = argparse.ArgumentParser(description="Sincroniza Excel/KML com Supabase")
    p.add_argument(
        "--kml",
        help="KML da fazenda (opcional se o GIS já estiver em public.dim_talhoes no Supabase)",
    )
    p.add_argument("--cobertura", required=True, help="XLSX adubação cobertura")
    p.add_argument("--base", help="XLSX base/subsolagem (opcional)")
    args = p.parse_args()

    url = os.environ.get("SUPABASE_DB_URL")
    if not url:
        print("Defina SUPABASE_DB_URL", file=sys.stderr)
        sys.exit(1)

    engine = create_engine(url)
    df_cob = ler_adubacao_cobertura(args.cobertura)
    df_cob = aplicar_calculadora_no_df(df_cob, "fertilizante", "kg_total", "area_total_ha")

    n_t = 0
    if args.kml:
        gdf = ler_talhoes_kml(args.kml)
        gdf = gdf[gdf["talhao"].notna()].copy()
        n_t = gravar_talhoes(engine, gdf)
    else:
        gdf_existente, fonte = carregar_talhoes_geom(engine)
        if gdf_existente is None:
            print(
                "Sem --kml e nenhum GIS em dim_talhoes / dim_talhao_florestal. "
                "Informe --kml ou carregue o mapa no Apontamento.",
                file=sys.stderr,
            )
            sys.exit(1)
        print(f"GIS já no Supabase ({fonte}): {len(gdf_existente)} talhões — pulando KML.")
    n_c = gravar_cobertura(engine, df_cob, arquivo_origem=os.path.basename(args.cobertura))
    print(f"Talhões gravados: {n_t} | Cobertura: {n_c} registros")

    if args.base:
        df_base = ler_adubacao_base(args.base)
        df_base = aplicar_calculadora_no_df(df_base, "fertilizante", "kg_total", "area_plantada_ha")
        n_b = gravar_base(engine, df_base)
        print(f"Base: {n_b} registros")


if __name__ == "__main__":
    main()
