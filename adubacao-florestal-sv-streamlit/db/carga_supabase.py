"""Pipeline único: planilhas/KML → Supabase (PC, GitHub Actions ou aba Admin)."""
from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy.engine import Engine

from db.supabase_io import carregar_talhoes_geom, gravar_base, gravar_cobertura, gravar_talhoes
from ingestion.excel_parser import ler_adubacao_base, ler_adubacao_cobertura
from ingestion.kml_parser import ler_talhoes_kml
from npk_calculator import aplicar_calculadora_no_df


def executar_carga_supabase(
    engine: Engine,
    *,
    kml: str | os.PathLike | None,
    cobertura: str | os.PathLike,
    base: str | os.PathLike | None = None,
    pular_kml_se_gis_no_banco: bool = True,
    sync_inteligente: bool = True,
    projeto_carga: str = "sv_florestal_2026",
) -> dict[str, int]:
    """Upsert cobertura (+ base opcional) e talhões (KML ou GIS já no banco)."""
    from db.conciliacao_adubacao import (
        carregar_cobertura_todos,
        conciliar_cobertura,
        desativar_cobertura_fora_da_planilha_por_talhao,
    )

    df_planilha = aplicar_calculadora_no_df(
        ler_adubacao_cobertura(str(cobertura)), "fertilizante", "kg_total", "area_total_ha"
    )
    df_cob = df_planilha
    n_desativados = 0
    if sync_inteligente:
        df_db = carregar_cobertura_todos(engine)
        _, df_cob = conciliar_cobertura(df_planilha, df_db, projeto_atual=projeto_carga)
        n_desativados = desativar_cobertura_fora_da_planilha_por_talhao(
            engine, df_planilha, projeto_atual=projeto_carga
        )
        if df_cob.empty:
            print("Sync inteligente: nenhuma linha nova/alterada em cobertura.")

    n_t = 0
    if kml:
        gdf = ler_talhoes_kml(str(kml))
        gdf = gdf[gdf["talhao"].notna()].copy()
        n_t = gravar_talhoes(engine, gdf)
    elif pular_kml_se_gis_no_banco:
        gdf_existente, fonte = carregar_talhoes_geom(engine)
        if gdf_existente is None:
            raise RuntimeError(
                "Sem KML e nenhum GIS em dim_talhoes / dim_talhao_florestal. "
                "Coloque um .kml em dados/ ou informe --kml."
            )
        print(f"GIS já no Supabase ({fonte}): {len(gdf_existente)} talhões — pulando KML.")
    else:
        raise RuntimeError("Informe KML na pasta dados/.")

    n_c = 0
    if not df_cob.empty:
        n_c = gravar_cobertura(
            engine,
            df_cob,
            arquivo_origem=os.path.basename(str(cobertura)),
            projeto_carga=projeto_carga,
        )
    n_b = 0
    if base:
        df_base = ler_adubacao_base(str(base))
        df_base = aplicar_calculadora_no_df(df_base, "fertilizante", "kg_total", "area_plantada_ha")
        n_b = gravar_base(engine, df_base)

    return {"talhoes": n_t, "cobertura": n_c, "base": n_b, "desativados_legado": n_desativados}


def sync_pasta_dados_painel(engine: Engine, pasta: str | Path) -> dict[str, int]:
    from ingestion.dados_painel import descobrir_arquivos_dados_painel

    paths = descobrir_arquivos_dados_painel(pasta)
    return executar_carga_supabase(
        engine,
        kml=str(paths["kml"]) if paths["kml"] else None,
        cobertura=str(paths["cobertura"]),
        base=str(paths["base"]) if paths["base"] else None,
    )
