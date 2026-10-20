#!/usr/bin/env python3
"""
Só lê a pasta DADOS_PAINEL no SEU PC — NÃO precisa de Supabase.
Use primeiro para ver se as planilhas estão OK.

  python scripts/conferir_planilhas_local.py
  python scripts/conferir_planilhas_local.py "C:\\Users\\hmauricio\\Desktop\\DADOS_PAINEL"
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from ingestion.dados_painel import descobrir_arquivos_dados_painel
from ingestion.excel_parser import ler_adubacao_base, ler_adubacao_cobertura
from ingestion.kml_parser import ler_talhoes_kml


def main() -> None:
    pasta = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.expanduser("~"), "Desktop", "DADOS_PAINEL"
    )
    print("=" * 60)
    print("CONFERÊNCIA LOCAL — pasta:", pasta)
    print("=" * 60)

    if not os.path.isdir(pasta):
        print("\nERRO: Pasta não existe.")
        print("Crie ou ajuste o caminho:", pasta)
        sys.exit(1)

    try:
        paths = descobrir_arquivos_dados_painel(pasta)
    except FileNotFoundError as e:
        print("\nERRO:", e)
        print("\nColoque na pasta:")
        print("  - 1 arquivo .kml (mapa)")
        print("  - 1 .xlsx de Cobertura (nome com 'cobertura' ajuda)")
        print("  - 1 .xlsx Base/Subsolagem (opcional)")
        sys.exit(1)

    print("\nArquivos encontrados:")
    print("  KML:      ", paths["kml"])
    print("  Cobertura:", paths["cobertura"])
    print("  Base:     ", paths["base"] or "(opcional)")

    gdf = ler_talhoes_kml(str(paths["kml"]))
    gdf_ok = gdf[gdf["talhao"].notna()]
    print(f"\n--- KML ---")
    print(f"Polígonos com número de talhão: {len(gdf_ok)}")
    print(f"Área total (ha): {gdf_ok['area_ha_kml'].sum():,.1f}")

    df = ler_adubacao_cobertura(str(paths["cobertura"]))
    print(f"\n--- Cobertura (planilha) ---")
    if df.empty:
        print("ERRO: 0 linhas lidas. Abas sem cabeçalho 'Talhão' na coluna B?")
        sys.exit(1)
    print(f"Lançamentos: {len(df)}")
    print(f"Talhões distintos: {df['talhao'].nunique()}")
    print(f"Retiros (abas): {', '.join(sorted(df['retiro'].dropna().unique().astype(str))[:12])}")
    if df["data"].notna().any():
        print(f"Datas: {df['data'].min()} → {df['data'].max()}")

    tal_kml = set(gdf_ok["talhao"].astype(str).str.upper())
    tal_xl = set(df["talhao"].astype(str).str.upper())
    cruz = tal_kml & tal_xl
    print(f"\n--- Cruzamento mapa x planilha ---")
    print(f"Talhões só no KML: {len(tal_kml - tal_xl)}")
    print(f"Talhões só na planilha: {len(tal_xl - tal_kml)}")
    print(f"Talhões em COMUM: {len(cruz)}")
    if len(cruz) == 0:
        print("\n⚠️  NENHUM talhão coincide — o painel ficará 0% até corrigir códigos ou arquivos.")
    else:
        print("\nOK para subir ao Supabase quando a conexão estiver certa.")

    if paths["base"]:
        df_b = ler_adubacao_base(str(paths["base"]))
        print(f"\n--- Base ---")
        print(f"Linhas: {len(df_b)}")

    print("\n" + "=" * 60)
    print("Próximo passo (PowerShell, na pasta adubacao-florestal-sv-streamlit):")
    print('  $env:SUPABASE_DB_URL = "postgresql+psycopg://postgres.REF:SENHA@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"')
    print(f'  python scripts/analisar_e_sync_adubacao.py --dados-dir "{pasta}" --sync --modo por_talhao')
    print("=" * 60)


if __name__ == "__main__":
    main()
