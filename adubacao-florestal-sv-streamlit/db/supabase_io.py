"""Leitura e gravação de adubação florestal no Supabase."""
from __future__ import annotations

import json
import os
from typing import Any

import geopandas as gpd
import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine


def tabela_existe(engine: Engine, nome: str) -> bool:
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = :t LIMIT 1"
            ),
            {"t": nome},
        ).fetchone()
    return row is not None


def _padronizar_df_cobertura(df: pd.DataFrame) -> pd.DataFrame:
    from ingestion.talhao_codigo import normalizar_coluna_talhao

    if df.empty:
        return df
    ren = {"n_kg": "N_kg", "p2o5_kg": "P2O5_kg", "k2o_kg": "K2O_kg"}
    df = df.rename(columns={k: v for k, v in ren.items() if k in df.columns})
    df = normalizar_coluna_talhao(df)
    if "data" in df.columns:
        df["data"] = pd.to_datetime(df["data"], errors="coerce")
    return df


def carregar_cobertura(engine: Engine, *, incluir_inativos: bool = False) -> pd.DataFrame:
    if not tabela_existe(engine, "fato_adubacao_cobertura"):
        return pd.DataFrame()
    sql = "SELECT * FROM fato_adubacao_cobertura"
    if not incluir_inativos and _coluna_existe(engine, "fato_adubacao_cobertura", "ativo"):
        sql += " WHERE ativo IS DISTINCT FROM FALSE"
    sql += " ORDER BY talhao, data"
    df = pd.read_sql(sql, engine)
    return _padronizar_df_cobertura(df)


def carregar_base(engine: Engine, *, incluir_inativos: bool = False) -> pd.DataFrame:
    if not tabela_existe(engine, "fato_adubacao_base"):
        return pd.DataFrame()
    from ingestion.talhao_codigo import normalizar_coluna_talhao

    sql = "SELECT * FROM fato_adubacao_base"
    if not incluir_inativos and _coluna_existe(engine, "fato_adubacao_base", "ativo"):
        sql += " WHERE ativo IS DISTINCT FROM FALSE"
    sql += " ORDER BY talhao"
    df = pd.read_sql(sql, engine)
    return normalizar_coluna_talhao(df)


def _coluna_existe(engine: Engine, tabela: str, coluna: str, schema: str = "public") -> bool:
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = :schema AND table_name = :tabela AND column_name = :coluna
                LIMIT 1
                """
            ),
            {"schema": schema, "tabela": tabela, "coluna": coluna},
        ).fetchone()
    return row is not None


def _coluna_geometria(engine: Engine, tabela: str, schema: str = "public") -> str | None:
    """Descobre coluna PostGIS (geometry/geography) da tabela."""
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT a.attname
                FROM pg_attribute a
                JOIN pg_class c ON a.attrelid = c.oid
                JOIN pg_namespace n ON c.relnamespace = n.oid
                JOIN pg_type t ON a.atttypid = t.oid
                WHERE n.nspname = :schema
                  AND c.relname = :tabela
                  AND t.typname IN ('geometry', 'geography')
                  AND a.attnum > 0
                  AND NOT a.attisdropped
                ORDER BY a.attnum
                LIMIT 1
                """
            ),
            {"schema": schema, "tabela": tabela},
        ).fetchall()
    return rows[0][0] if rows else None


def _read_postgis_talhoes(
    engine: Engine,
    sql: str,
    geom_col: str = "geom",
    fonte: str = "",
) -> gpd.GeoDataFrame | None:
    try:
        gdf = gpd.read_postgis(sql, engine, geom_col=geom_col)
    except Exception:
        return None
    if gdf is None or gdf.empty:
        return None
    gdf = gdf.set_crs(4326, allow_override=True)
    if gdf.geometry.name != "geometry":
        gdf = gdf.rename_geometry("geometry")
    if "talhao" in gdf.columns:
        gdf["talhao"] = gdf["talhao"].astype(str).str.strip().str.upper()
        gdf = gdf[gdf["talhao"].notna() & (gdf["talhao"] != "")].copy()
    gdf.attrs["fonte_gis"] = fonte
    return gdf


def _carregar_geom_dim_talhao_florestal(engine: Engine) -> gpd.GeoDataFrame | None:
    if not tabela_existe(engine, "dim_talhao_florestal"):
        return None
    geom_col = _coluna_geometria(engine, "dim_talhao_florestal") or "geom"
    if not _coluna_existe(engine, "dim_talhao_florestal", geom_col):
        return None
    with engine.connect() as conn:
        n = conn.execute(
            text(f"SELECT COUNT(*) FROM dim_talhao_florestal WHERE {geom_col} IS NOT NULL")
        ).scalar()
    if not n:
        return None
    return _read_postgis_talhoes(
        engine,
        f"""
        SELECT talhao, classe, retiro, area_ha_kml, {geom_col} AS geom
        FROM dim_talhao_florestal
        WHERE {geom_col} IS NOT NULL
        """,
        geom_col="geom",
        fonte="public.dim_talhao_florestal",
    )


def _carregar_geom_dim_talhoes_sigcf(engine: Engine) -> gpd.GeoDataFrame | None:
    """
    Cadastro GIS do Apontamento de Campo / SIGCF (já usado nas views vw_terceiros_drone_mapa).
    """
    if not tabela_existe(engine, "dim_talhoes"):
        return None
    geom_col = _coluna_geometria(engine, "dim_talhoes")
    if not geom_col:
        return None

    if _coluna_existe(engine, "dim_talhoes", "codigo"):
        expr_talhao = "upper(trim(d.codigo))"
    elif _coluna_existe(engine, "dim_talhoes", "nome"):
        expr_talhao = "upper(trim(d.nome))"
    else:
        return None

    expr_classe = "d.classe_uso" if _coluna_existe(engine, "dim_talhoes", "classe_uso") else "NULL"
    expr_area = "d.area_ha" if _coluna_existe(engine, "dim_talhoes", "area_ha") else "NULL"

    join_locais = ""
    expr_retiro = "NULL"
    if tabela_existe(engine, "dim_locais") and _coluna_existe(engine, "dim_talhoes", "id_local"):
        join_locais = "LEFT JOIN public.dim_locais l ON l.id = d.id_local"
        expr_retiro = "l.nome"

    filtro_ativo = "AND coalesce(d.ativo, true)" if _coluna_existe(engine, "dim_talhoes", "ativo") else ""

    sql = f"""
        SELECT
            {expr_talhao} AS talhao,
            {expr_classe} AS classe,
            {expr_retiro} AS retiro,
            {expr_area} AS area_ha_kml,
            d.{geom_col} AS geom
        FROM public.dim_talhoes d
        {join_locais}
        WHERE d.{geom_col} IS NOT NULL
        {filtro_ativo}
    """
    return _read_postgis_talhoes(
        engine,
        sql,
        geom_col="geom",
        fonte="public.dim_talhoes (GIS Apontamento)",
    )


def carregar_talhoes_geom(
    engine: Engine,
    preferir_tabela: str | None = None,
) -> tuple[gpd.GeoDataFrame | None, str | None]:
    """
    Carrega polígonos do Supabase. Ordem:
      1) dim_talhao_florestal (painel adubação)
      2) dim_talhoes (GIS SIGCF / Apontamento de Campo)
    Retorna (GeoDataFrame, descrição da fonte).
    """
    preferida = (preferir_tabela or os.environ.get("SUPABASE_GIS_TABLE") or "").strip().lower()

    loaders = [
        ("dim_talhao_florestal", _carregar_geom_dim_talhao_florestal),
        ("dim_talhoes", _carregar_geom_dim_talhoes_sigcf),
    ]
    if preferida == "dim_talhoes":
        loaders.reverse()
    elif preferida == "dim_talhao_florestal":
        pass

    for _nome, loader in loaders:
        gdf = loader(engine)
        if gdf is not None and len(gdf):
            return gdf, gdf.attrs.get("fonte_gis")

    return None, None


def _geom_to_wkt(geom) -> str | None:
    if geom is None or geom.is_empty:
        return None
    return geom.wkt


def gravar_talhoes(engine: Engine, gdf: gpd.GeoDataFrame) -> int:
    """Upsert talhões com geometria (substitui por talhao)."""
    rows = []
    for _, row in gdf.iterrows():
        wkt = _geom_to_wkt(row.geometry)
        if not wkt:
            continue
        rows.append(
            {
                "talhao": str(row["talhao"]).strip().upper(),
                "classe": row.get("classe"),
                "retiro": row.get("retiro"),
                "area_ha_kml": float(row["area_ha_kml"]) if pd.notna(row.get("area_ha_kml")) else None,
                "wkt": wkt,
            }
        )
    if not rows:
        return 0

    sql = text(
        """
        INSERT INTO dim_talhao_florestal (talhao, classe, retiro, area_ha_kml, geom, updated_at)
        VALUES (:talhao, :classe, :retiro, :area_ha_kml, ST_Multi(ST_GeomFromText(:wkt, 4326)), now())
        ON CONFLICT (talhao) DO UPDATE SET
            classe = EXCLUDED.classe,
            retiro = EXCLUDED.retiro,
            area_ha_kml = EXCLUDED.area_ha_kml,
            geom = EXCLUDED.geom,
            updated_at = now()
        """
    )
    with engine.begin() as conn:
        conn.execute(sql, rows)
    return len(rows)


def gravar_cobertura(
    engine: Engine,
    df: pd.DataFrame,
    arquivo_origem: str | None = None,
    *,
    projeto_carga: str = "sv_florestal_2026",
) -> int:
    if df.empty:
        return 0
    cols = [
        "talhao", "retiro", "area_total_ha", "area_floresta_ha", "fertilizante", "data",
        "dose_recomendada_ha", "dose_realizada_ha", "kg_total", "operador",
        "formula_npk", "N_kg", "P2O5_kg", "K2O_kg",
    ]
    payload = df.copy()
    for c in cols:
        if c not in payload.columns:
            payload[c] = None
    payload = payload[cols].copy()
    payload["talhao"] = payload["talhao"].astype(str).str.strip().str.upper()
    payload["arquivo_origem"] = arquivo_origem
    tem_projeto = _coluna_existe(engine, "fato_adubacao_cobertura", "projeto_carga")

    if tem_projeto:
        sql = text(
            """
            INSERT INTO fato_adubacao_cobertura (
                talhao, retiro, area_total_ha, area_floresta_ha, fertilizante, data,
                dose_recomendada_ha, dose_realizada_ha, kg_total, operador,
                formula_npk, n_kg, p2o5_kg, k2o_kg, arquivo_origem, projeto_carga, ativo, updated_at
            ) VALUES (
                :talhao, :retiro, :area_total_ha, :area_floresta_ha, :fertilizante, :data,
                :dose_recomendada_ha, :dose_realizada_ha, :kg_total, :operador,
                :formula_npk, :n_kg, :p2o5_kg, :k2o_kg, :arquivo_origem, :projeto_carga, TRUE, now()
            )
            ON CONFLICT ON CONSTRAINT uq_fato_cobertura_natural DO UPDATE SET
                area_total_ha = EXCLUDED.area_total_ha,
                area_floresta_ha = EXCLUDED.area_floresta_ha,
                dose_recomendada_ha = EXCLUDED.dose_recomendada_ha,
                dose_realizada_ha = EXCLUDED.dose_realizada_ha,
                operador = EXCLUDED.operador,
                formula_npk = EXCLUDED.formula_npk,
                n_kg = EXCLUDED.n_kg,
                p2o5_kg = EXCLUDED.p2o5_kg,
                k2o_kg = EXCLUDED.k2o_kg,
                arquivo_origem = EXCLUDED.arquivo_origem,
                projeto_carga = EXCLUDED.projeto_carga,
                ativo = TRUE,
                updated_at = now()
            """
        )
    else:
        sql = text(
            """
            INSERT INTO fato_adubacao_cobertura (
                talhao, retiro, area_total_ha, area_floresta_ha, fertilizante, data,
                dose_recomendada_ha, dose_realizada_ha, kg_total, operador,
                formula_npk, n_kg, p2o5_kg, k2o_kg, arquivo_origem, updated_at
            ) VALUES (
                :talhao, :retiro, :area_total_ha, :area_floresta_ha, :fertilizante, :data,
                :dose_recomendada_ha, :dose_realizada_ha, :kg_total, :operador,
                :formula_npk, :n_kg, :p2o5_kg, :k2o_kg, :arquivo_origem, now()
            )
            ON CONFLICT ON CONSTRAINT uq_fato_cobertura_natural DO UPDATE SET
                area_total_ha = EXCLUDED.area_total_ha,
                area_floresta_ha = EXCLUDED.area_floresta_ha,
                dose_recomendada_ha = EXCLUDED.dose_recomendada_ha,
                dose_realizada_ha = EXCLUDED.dose_realizada_ha,
                operador = EXCLUDED.operador,
                formula_npk = EXCLUDED.formula_npk,
                n_kg = EXCLUDED.n_kg,
                p2o5_kg = EXCLUDED.p2o5_kg,
                k2o_kg = EXCLUDED.k2o_kg,
                arquivo_origem = EXCLUDED.arquivo_origem,
                updated_at = now()
            """
        )
    records = []
    for _, row in payload.iterrows():
        data_val = row["data"]
        if pd.isna(data_val):
            data_val = None
        elif hasattr(data_val, "date"):
            data_val = data_val.date()
        rec = {
            "talhao": row["talhao"],
            "retiro": row["retiro"],
            "area_total_ha": _num(row["area_total_ha"]),
            "area_floresta_ha": _num(row["area_floresta_ha"]),
            "fertilizante": row["fertilizante"],
            "data": data_val,
            "dose_recomendada_ha": _num(row["dose_recomendada_ha"]),
            "dose_realizada_ha": _num(row["dose_realizada_ha"]),
            "kg_total": _num(row["kg_total"]),
            "operador": row["operador"],
            "formula_npk": row.get("formula_npk"),
            "n_kg": _num(row.get("N_kg")),
            "p2o5_kg": _num(row.get("P2O5_kg")),
            "k2o_kg": _num(row.get("K2O_kg")),
            "arquivo_origem": arquivo_origem,
        }
        if tem_projeto:
            rec["projeto_carga"] = projeto_carga
        records.append(rec)
    with engine.begin() as conn:
        conn.execute(sql, records)
    return len(records)


def gravar_base(engine: Engine, df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    cols = ["retiro", "talhao", "area_plantada_ha", "fertilizante", "dose_ha", "kg_total", "prestador", "status"]
    payload = df.copy()
    for c in cols:
        if c not in payload.columns:
            payload[c] = None
    payload = payload[cols].copy()
    payload["talhao"] = payload["talhao"].astype(str).str.strip().str.upper()

    sql = text(
        """
        INSERT INTO fato_adubacao_base (
            talhao, retiro, area_plantada_ha, fertilizante, dose_ha, kg_total, prestador, status, updated_at
        ) VALUES (
            :talhao, :retiro, :area_plantada_ha, :fertilizante, :dose_ha, :kg_total, :prestador, :status, now()
        )
        ON CONFLICT ON CONSTRAINT uq_fato_base_natural DO UPDATE SET
            area_plantada_ha = EXCLUDED.area_plantada_ha,
            dose_ha = EXCLUDED.dose_ha,
            prestador = EXCLUDED.prestador,
            updated_at = now()
        """
    )
    records = []
    for _, row in payload.iterrows():
        records.append(
            {
                "talhao": row["talhao"],
                "retiro": row["retiro"],
                "area_plantada_ha": _num(row["area_plantada_ha"]),
                "fertilizante": row["fertilizante"],
                "dose_ha": _num(row["dose_ha"]),
                "kg_total": _num(row["kg_total"]),
                "prestador": row["prestador"],
                "status": row["status"],
            }
        )
    with engine.begin() as conn:
        conn.execute(sql, records)
    return len(records)


def ultimo_cobertura_por_talhao(df_cobertura: pd.DataFrame) -> pd.DataFrame:
    """Último lançamento por talhão (equivalente à view SQL)."""
    if df_cobertura.empty:
        return pd.DataFrame(
            columns=[
                "talhao", "retiro", "area_total_ha", "area_floresta_ha", "fertilizante",
                "data", "dose_recomendada_ha", "dose_realizada_ha", "kg_total", "operador",
                "realizado_ha",
            ]
        )
    df = df_cobertura.sort_values(["talhao", "data"], na_position="last").copy()
    ult = df.groupby("talhao", as_index=False).tail(1)
    ult["realizado_ha"] = ult.apply(_calc_realizado, axis=1)
    return ult


def _calc_realizado(row: pd.Series) -> float | None:
    fl = row.get("area_floresta_ha")
    kg = row.get("kg_total")
    if pd.isna(fl) or pd.isna(kg) or fl == 0:
        return None
    return round(float(kg) / float(fl), 2)


def _num(val: Any) -> float | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def ficha_talhao_dict(ult: pd.DataFrame, talhao: str) -> dict | None:
    if ult.empty or not talhao:
        return None
    t = str(talhao).strip().upper()
    row = ult[ult["talhao"] == t]
    if row.empty:
        return None
    r = row.iloc[0]
    realizado = r.get("realizado_ha")
    if realizado is None and pd.notna(r.get("dose_realizada_ha")):
        realizado = float(r["dose_realizada_ha"])
    return {
        "talhao": t,
        "area_total_ha": r.get("area_total_ha"),
        "area_floresta_ha": r.get("area_floresta_ha"),
        "fertilizante": r.get("fertilizante"),
        "data": r.get("data"),
        "previsto_ha": r.get("dose_recomendada_ha"),
        "kg_total": r.get("kg_total"),
        "operador": r.get("operador"),
        "realizado_ha": realizado,
        "retiro": r.get("retiro"),
        "tem_lancamento_cobertura": True,
    }


def ficha_talhao_merged(
    ult: pd.DataFrame,
    cadastro: pd.DataFrame,
    talhao: str | None,
) -> dict | None:
    """Ficha lateral: lançamento de cobertura (se existir) ou cadastro do KML/painel."""
    if not talhao:
        return None
    t = str(talhao).strip().upper()
    if ult is not None and not ult.empty:
        f = ficha_talhao_dict(ult, t)
        if f:
            return f
    if cadastro is None or cadastro.empty:
        return None
    tal_col = cadastro["talhao"].astype(str).str.strip().str.upper()
    row = cadastro.loc[tal_col == t]
    if row.empty:
        return None
    r = row.iloc[0]
    return {
        "talhao": t,
        "area_total_ha": r.get("area_ha_kml"),
        "area_floresta_ha": r.get("area_floresta_ha") if pd.notna(r.get("area_floresta_ha")) else r.get("area_ha_kml"),
        "fertilizante": None,
        "data": None,
        "previsto_ha": r.get("n_kg_ha_cobertura"),
        "kg_total": None,
        "operador": None,
        "realizado_ha": None,
        "retiro": r.get("retiro"),
        "classe": r.get("classe"),
        "status_cobertura": r.get("status_cobertura"),
        "pct_cobertura": r.get("pct_cobertura"),
        "tem_lancamento_cobertura": False,
    }


def ficha_para_json(ficha: dict | None) -> str:
    if not ficha:
        return "{}"
    out = {}
    for k, v in ficha.items():
        if isinstance(v, pd.Timestamp):
            out[k] = v.strftime("%d/%m/%Y")
        elif pd.isna(v):
            out[k] = None
        else:
            out[k] = v
    return json.dumps(out, ensure_ascii=False)
