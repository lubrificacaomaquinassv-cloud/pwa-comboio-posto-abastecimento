#!/usr/bin/env python3
"""
Analisa TODOS os .xlsx em DADOS_PAINEL (tipo, linhas, talhões).
Não precisa de Supabase.

  python scripts/conferir_planilhas_local.py
  python scripts/conferir_planilhas_local.py "C:\\Users\\hmauricio\\Desktop\\DADOS_PAINEL"
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from ingestion.dados_painel import descobrir_arquivos_dados_painel
from ingestion.inventario_planilhas import inventariar_pasta, resumo_inventario
from ingestion.kml_parser import ler_talhoes_kml


def main() -> None:
    pasta = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.expanduser("~"), "Desktop", "DADOS_PAINEL"
    )
    print("=" * 70)
    print("INVENTÁRIO —", pasta)
    print("=" * 70)

    if not os.path.isdir(pasta):
        print("\nERRO: pasta não existe.")
        sys.exit(1)

    itens = inventariar_pasta(pasta)
    if not itens:
        print("\nNenhum arquivo .xlsx na pasta.")
        sys.exit(1)

    print("\n--- Cada planilha ---")
    for inv in itens:
        print(f"\n• {inv.nome}")
        print(f"  Tipo: {inv.tipo}")
        print(f"  Abas: {', '.join(inv.abas[:8])}{'…' if len(inv.abas) > 8 else ''}")
        print(f"  Linhas: {inv.linhas_lidas} | Talhões: {inv.talhoes}")
        if inv.detalhe:
            print(f"  Detalhe: {inv.detalhe}")

    res = resumo_inventario(itens)
    print("\n--- Resumo JSON ---")
    print(json.dumps(res, ensure_ascii=False, indent=2))

    cob_ok = sum(1 for i in itens if i.tipo == "cobertura_sv" and i.linhas_lidas > 0)
    base_ok = sum(1 for i in itens if i.tipo == "base_subsolagem_sv" and i.linhas_lidas > 0)
    print(f"\n→ Planilhas de COBERTURA válidas: {cob_ok}")
    print(f"→ Planilhas de BASE/SUBSOLAGEM válidas: {base_ok}")

    if res["ignorados"]:
        print("\n⚠️  Arquivos não classificados como adubação SV (não serão ignorados no sync se forem cobertura/base):")
        for x in res["ignorados"]:
            print(f"   - {x['arquivo']}: {x['tipo']} — {x['detalhe']}")

    try:
        paths = descobrir_arquivos_dados_painel(pasta)
        gdf = ler_talhoes_kml(str(paths["kml"]))
        gdf_ok = gdf[gdf["talhao"].notna()]
        from ingestion.inventario_planilhas import carregar_todas_coberturas

        df = carregar_todas_coberturas(itens)
        if len(df):
            tal_kml = set(gdf_ok["talhao"].astype(str).str.upper())
            tal_xl = set(df["talhao"].astype(str).str.upper())
            print(f"\n--- KML: {paths['kml'].name} ---")
            print(f"Polígonos: {len(gdf_ok)} | Cruzamento planilha×mapa: {len(tal_kml & tal_xl)} talhões")
    except FileNotFoundError as e:
        print("\nKML:", e)

    print("\n" + "=" * 70)
    print("Subir TODAS as planilhas classificadas → Supabase (Lovable + Streamlit):")
    print('  python scripts/analisar_e_sync_adubacao.py --dados-dir "' + pasta + '" --sync')
    print("SQL Lovable: sql/005_views_lovable_adubacao.sql")
    print("=" * 70)


if __name__ == "__main__":
    main()
