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
from ingestion.dados_painel import descobrir_arquivos_dados_painel
from ingestion.excel_parser import ler_adubacao_base, ler_adubacao_cobertura
from ingestion.kml_parser import ler_talhoes_kml
from npk_calculator import aplicar_calculadora_no_df


def _analisar_planilhas(cobertura_path: str, base_path: str | None) -> None:
    df = ler_adubacao_cobertura(cobertura_path)
    print(f"\n=== Planilha Cobertura: {os.path.basename(cobertura_path)} ===")
    print(f"Linhas: {len(df)} | Talhões: {df['talhao'].nunique() if len(df) else 0}")
    if len(df):
        print(f"Retiros (abas): {sorted(df['retiro'].dropna().unique().tolist())}")
        print(f"Datas: {df['data'].min()} → {df['data'].max()}")
        print(f"Fertilizantes (top): {df['fertilizante'].value_counts().head(5).to_dict()}")
        dup = df.duplicated(subset=["talhao", "retiro", "data", "fertilizante", "kg_total"]).sum()
        if dup:
            print(f"⚠️  {dup} linhas duplicadas (mesma chave natural) — revisar planilha.")
    if base_path:
        df_b = ler_adubacao_base(base_path)
        print(f"\n=== Planilha Base: {os.path.basename(base_path)} ===")
        print(f"Linhas: {len(df_b)} | status: {df_b['status'].value_counts().to_dict() if len(df_b) else {}}")


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

    paths = descobrir_arquivos_dados_painel(args.dados_dir)
    cob_path = str(paths["cobertura"])
    base_path = str(paths["base"]) if paths["base"] else None
    kml_path = args.kml or (str(paths["kml"]) if paths["kml"] else None)

    _analisar_planilhas(cob_path, base_path)

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
            ler_adubacao_cobertura(cob_path), "fertilizante", "kg_total", "area_total_ha"
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
            arquivo_origem=os.path.basename(cob_path),
            projeto_carga=args.projeto,
        )
        print(f"\nGravadas/atualizadas {n} linhas de cobertura (novos + alterados).")

    if base_path:
        df_base = aplicar_calculadora_no_df(
            ler_adubacao_base(base_path), "fertilizante", "kg_total", "area_plantada_ha"
        )
        n_b = gravar_base(engine, df_base)
        print(f"Base/subsolagem: {n_b} linhas (upsert).")

    if kml_path:
        gdf = ler_talhoes_kml(kml_path)
        gdf = gdf[gdf["talhao"].notna()].copy()
        n_t = gravar_talhoes(engine, gdf)
        print(f"KML talhões: {n_t} upsert.")

    print("\nAuditoria SQL sugerida: SELECT * FROM vw_auditoria_cobertura_por_projeto;")


if __name__ == "__main__":
    main()
