#!/usr/bin/env python3
"""
Analisa planilhas DADOS_PAINEL vs. Supabase (inclui dados do projeto anterior)
e grava SOMENTE lançamentos novos ou alterados.

Uso:
  export SUPABASE_DB_URL='postgresql+psycopg://...'
  python scripts/analisar_e_sync_adubacao.py --dados-dir "%USERPROFILE%\\Desktop\\DADOS_PAINEL" --analise-only
  python scripts/analisar_e_sync_adubacao.py --dados-dir ... --sync --modo por_talhao

Antes da primeira carga inteligente, execute sql/004_controle_projeto_legado.sql no Supabase.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from sqlalchemy import create_engine

from db.conciliacao_adubacao import (
    carregar_cobertura_todos,
    conciliar_cobertura,
    desativar_cobertura_fora_da_planilha_por_talhao,
    relatorio_json,
)
from db.supabase_io import gravar_base, gravar_cobertura, gravar_talhoes
from ingestion.dados_painel import achar_kml
from ingestion.inventario_planilhas import (
    carregar_todas_bases,
    carregar_todas_coberturas,
    inventariar_pasta,
    resumo_inventario,
)
from ingestion.kml_parser import ler_talhoes_kml
from npk_calculator import aplicar_calculadora_no_df


def _analisar_pasta(pasta: str) -> tuple:
    itens = inventariar_pasta(pasta)
    print("\n=== Inventário DADOS_PAINEL ===")
    print(json.dumps(resumo_inventario(itens), ensure_ascii=False, indent=2))
    df_cob = carregar_todas_coberturas(itens)
    df_base = carregar_todas_bases(itens)
    if df_cob.empty:
        print("\nERRO: nenhuma planilha de COBERTURA válida na pasta.", file=sys.stderr)
        sys.exit(1)
    print(f"\nCobertura consolidada: {len(df_cob)} linhas, {df_cob['talhao'].nunique()} talhões")
    if not df_base.empty:
        print(f"Base consolidada: {len(df_base)} linhas")
    return itens, df_cob, df_base


def main() -> None:
    p = argparse.ArgumentParser(description="Análise e sync inteligente adubação")
    p.add_argument("--dados-dir", required=True, help="Pasta DADOS_PAINEL")
    p.add_argument("--projeto", default="sv_florestal_2026", help="Tag projeto_carga no Supabase")
    p.add_argument("--analise-only", action="store_true", help="Só analisa planilhas + Supabase")
    p.add_argument("--sync", action="store_true", help="Grava no Supabase após análise")
    p.add_argument(
        "--modo",
        choices=["conservador", "por_talhao"],
        default="por_talhao",
        help="conservador=só upsert novos/alterados; por_talhao=desativa lanç. antigos dos talhões da planilha",
    )
    p.add_argument("--kml", help="KML opcional (senão usa o da pasta dados)")
    args = p.parse_args()

    _itens, df_excel_raw, df_base_raw = _analisar_pasta(args.dados_dir)
    kml_path = args.kml
    if not kml_path:
        kml_found = achar_kml(args.dados_dir)
        kml_path = str(kml_found) if kml_found else None
    arquivo_origem = "DADOS_PAINEL_consolidado"

    url = os.environ.get("SUPABASE_DB_URL")
    if not url:
        print("\nPara falar com o Supabase, defina SUPABASE_DB_URL (veja FINALIZAR_PAINEL.md).", file=sys.stderr)
        sys.exit(1 if args.sync else 0)

    from sqlalchemy import text

    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        print("\n*** ERRO DE CONEXÃO COM SUPABASE ***", file=sys.stderr)
        print(str(e), file=sys.stderr)
        print(
            "\nCorrija:\n"
            "  1) Supabase → Settings → Database → Transaction pooler → URI\n"
            "  2) Troque postgresql:// por postgresql+psycopg://\n"
            "  3) Usuário: postgres.SEU_REF (não só postgres)\n"
            "  4) Senha: Database password (não anon key)\n",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        df_excel = aplicar_calculadora_no_df(
            df_excel_raw, "fertilizante", "kg_total", "area_total_ha"
        )
        df_db = carregar_cobertura_todos(engine)
    except Exception as e:
        print("\n*** ERRO AO LER SUPABASE ***", file=sys.stderr)
        print(str(e), file=sys.stderr)
        print(
            "Rode no SQL Editor: sql/003_schema_adubacao_florestal.sql "
            "(e opcional sql/004_controle_projeto_legado.sql).",
            file=sys.stderr,
        )
        sys.exit(1)

    rel, df_gravar = conciliar_cobertura(df_excel, df_db, projeto_atual=args.projeto)
    print("\n=== Conciliação Cobertura (planilha × Supabase) ===")
    print(relatorio_json(rel))

    if args.analise_only and not args.sync:
        print(
            "\nPróximo passo: rode com --sync (e --modo por_talhao) após revisar o JSON acima."
        )
        return

    if not args.sync:
        return

    if args.modo == "por_talhao":
        n_off = desativar_cobertura_fora_da_planilha_por_talhao(
            engine, df_excel, projeto_atual=args.projeto
        )
        print(f"\nLançamentos antigos desativados (talhões da planilha): {n_off}")

    if df_gravar.empty:
        print("\nNenhuma linha nova/alterada para gravar (planilha já refletida no Supabase).")
    else:
        df_gravar = aplicar_calculadora_no_df(
            df_gravar, "fertilizante", "kg_total", "area_total_ha"
        )
        n = gravar_cobertura(
            engine,
            df_gravar,
            arquivo_origem=arquivo_origem,
            projeto_carga=args.projeto,
        )
        print(f"\nGravadas/atualizadas {n} linhas de cobertura (novos + alterados).")

    if not df_base_raw.empty:
        df_base = aplicar_calculadora_no_df(
            df_base_raw, "fertilizante", "kg_total", "area_plantada_ha"
        )
        n_b = gravar_base(engine, df_base)
        print(f"Base/subsolagem: {n_b} linhas (upsert).")

    if kml_path:
        gdf = ler_talhoes_kml(kml_path)
        gdf = gdf[gdf["talhao"].notna()].copy()
        n_t = gravar_talhoes(engine, gdf)
        print(f"KML talhões: {n_t} upsert ({kml_path}).")
    else:
        print(
            "\nAviso: KML não encontrado em DADOS_PAINEL — cobertura foi gravada; "
            "mapa/polígonos: copie o .kml para a pasta ou use --kml CAMINHO.kml"
        )

    print("\nAuditoria: SELECT * FROM vw_auditoria_cobertura_por_projeto;")
    print("Lovable: SELECT * FROM vw_api_adubacao_cobertura LIMIT 10;")


if __name__ == "__main__":
    main()
