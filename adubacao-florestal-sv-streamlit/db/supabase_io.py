"""Leitura e gravação de adubação florestal no Supabase."""
from __future__ import annotations

import json
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


def carregar_cobertura(engine: Engine) -> pd.DataFrame:
    if not tabela_existe(engine, "fato_adubacao_cobertura"):
        return pd.DataFrame()
    df = pd.read_sql("SELECT * FROM fato_adubacao_cobertura ORDER BY talhao, data", engine)
    if "data" in df.columns:
        df["data"] = pd.to_datetime(df["data"], errors="coerce")
    return df


def carregar_base(engine: Engine) -> pd.DataFrame:
    if not tabela_existe(engine, "fato_adubacao_base"):
        return pd.DataFrame()
    return pd.read_sql("SELECT * FROM fato_adubacao_base ORDER BY talhao", engine)


def carregar_talhoes_geom(engine: Engine) -> gpd.GeoDataFrame | None:
    if not tabela_existe(engine, "dim_talhao_florestal"):
        return None
    with engine.connect() as conn:
        n = conn.execute(text("SELECT COUNT(*) FROM dim_talhao_florestal WHERE geom IS NOT NULL")).scalar()
    if not n:
        return None
    gdf = gpd.read_postgis(
        """
        SELECT talhao, classe, retiro, area_ha_kml, geom
        FROM dim_talhao_florestal
        WHERE geom IS NOT NULL
        """,
        engine,
        geom_col="geom",
    )
    gdf = gdf.set_crs(4326, allow_override=True)
    return gdf


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


def gravar_cobertura(engine: Engine, df: pd.DataFrame, arquivo_origem: str | None = None) -> int:
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
        records.append(
            {
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
        )
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
