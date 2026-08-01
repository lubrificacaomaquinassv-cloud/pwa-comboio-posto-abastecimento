"""ETL: planilhas de adubação + cadastro GIS."""
from __future__ import annotations

import re
from pathlib import Path

import geopandas as gpd
import pandas as pd

from config import (
    CRS_METRIC,
    KML_LAYERS,
    PATH_BASE,
    PATH_BASE_SAMPLE,
    PATH_COBERTURA,
    PATH_COBERTURA_SAMPLE,
    PATH_GIS_SAMPLE,
    PATH_KML,
)
from npk import calcular_nutrientes

_SUFFIX_RE = re.compile(r"^(\d+)([A-Za-z]?)$")
_AREA_DESC_RE = re.compile(r"rea:</b>\s*([\d.,]+)\s*ha", re.IGNORECASE)

STATUS_COLORS = {
    "concluido": "#2ecc71",
    "pendente": "#e74c3c",
    "sem_dado": "#95a5a6",
}


def normalizar_talhao(valor) -> str | None:
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return None
    raw = str(valor).strip().upper().replace(" ", "")
    if not raw or raw in {"NAN", "NONE", "-"}:
        return None
    match = _SUFFIX_RE.match(raw)
    if match:
        return f"{int(match.group(1))}{match.group(2)}"
    return raw


def talhao_base(chave: str | None) -> str | None:
    if not chave:
        return None
    match = _SUFFIX_RE.match(chave)
    return match.group(1) if match else chave


def _resolve_path(primary: Path, sample: Path) -> tuple[Path, bool]:
    if primary.exists():
        return primary, False
    if sample.exists():
        return sample, True
    raise FileNotFoundError(
        f"Arquivo não encontrado: {primary}. Coloque os dados reais ou use a amostra em {sample.parent}."
    )


def load_cobertura(path: Path | None = None) -> pd.DataFrame:
    if path is None:
        path, _ = _resolve_path(PATH_COBERTURA, PATH_COBERTURA_SAMPLE)
    xl = pd.ExcelFile(path)
    frames: list[pd.DataFrame] = []

    for horto in xl.sheet_names:
        raw = pd.read_excel(path, sheet_name=horto, header=None)
        body = raw.iloc[7:].copy()
        body.columns = [
            "_skip",
            "talhao_raw",
            "ha_total",
            "ha_floresta",
            "fertilizante",
            "data",
            "dosagem_recomendada",
            "dosagem_realizada",
            "total_kg",
            "operador",
        ]
        body = body.drop(columns=["_skip"])
        body["horto"] = horto.strip()
        body["talhao"] = body["talhao_raw"].map(normalizar_talhao)
        body = body[body["talhao"].notna()].copy()

        for col in ("ha_total", "ha_floresta", "dosagem_recomendada", "dosagem_realizada", "total_kg"):
            body[col] = pd.to_numeric(body[col], errors="coerce")
        body["data"] = pd.to_datetime(body["data"], errors="coerce")
        body["servico"] = "cobertura"
        body["status"] = "concluido"
        frames.append(body)

    return pd.concat(frames, ignore_index=True)


def _load_base_lado(df_raw: pd.DataFrame, cols: list[int], status: str) -> pd.DataFrame:
    body = df_raw.iloc[5:, cols].copy()
    body.columns = [
        "horto",
        "talhao_raw",
        "area_ha",
        "fertilizante",
        "dosagem_kg_ha",
        "total_kg",
        "prestador",
    ]
    body["talhao"] = body["talhao_raw"].map(normalizar_talhao)
    body = body[body["talhao"].notna()].copy()
    for col in ("area_ha", "dosagem_kg_ha", "total_kg"):
        body[col] = pd.to_numeric(body[col], errors="coerce")
    body["servico"] = "base_subsolagem"
    body["status"] = status
    return body


def load_base(path: Path | None = None) -> pd.DataFrame:
    if path is None:
        path, _ = _resolve_path(PATH_BASE, PATH_BASE_SAMPLE)
    raw = pd.read_excel(path, sheet_name="Subsolagem", header=None)
    feito = _load_base_lado(raw, [1, 2, 3, 4, 5, 6, 7], status="concluido")
    pendente = _load_base_lado(raw, [9, 10, 11, 12, 13, 14, 15], status="pendente")
    return pd.concat([feito, pendente], ignore_index=True)


def _area_from_description(desc: str | None) -> float | None:
    if not desc:
        return None
    match = _AREA_DESC_RE.search(str(desc))
    if not match:
        return None
    return float(match.group(1).replace(",", "."))


def load_talhoes_gis(path: Path | None = None, layers: list[str] | None = None) -> gpd.GeoDataFrame:
    if path is None:
        if PATH_KML.exists():
            path = PATH_KML
            use_kml_layers = True
        elif PATH_GIS_SAMPLE.exists():
            path = PATH_GIS_SAMPLE
            use_kml_layers = False
        else:
            raise FileNotFoundError(f"GIS não encontrado: {PATH_KML} ou {PATH_GIS_SAMPLE}")

    if path.suffix.lower() == ".geojson":
        gdf = gpd.read_file(path)
        if "talhao" not in gdf.columns and "Name" in gdf.columns:
            gdf["talhao"] = gdf["Name"].astype(str).map(normalizar_talhao)
        if "classe" not in gdf.columns:
            gdf["classe"] = "Silvicultura"
        if "area_ha" not in gdf.columns:
            metric = gdf.to_crs(CRS_METRIC)
            gdf["area_ha"] = metric.geometry.area / 10_000.0
        return gdf.dropna(subset=["talhao"]).copy()

    layers = layers or KML_LAYERS
    parts: list[gpd.GeoDataFrame] = []
    for layer in layers:
        gdf = gpd.read_file(path, layer=layer)
        if gdf.empty:
            continue
        gdf = gdf.copy()
        gdf["classe"] = "Silvicultura" if "Silvicultura" in layer else "Silvipastoril"
        gdf["talhao"] = gdf["Name"].astype(str).str.strip().map(normalizar_talhao)
        gdf["area_desc_ha"] = gdf.get("description", pd.Series(dtype=object)).map(_area_from_description)
        parts.append(gdf)

    if not parts:
        return gpd.GeoDataFrame(columns=["talhao", "geometry"], geometry="geometry", crs="EPSG:4326")

    gdf = pd.concat(parts, ignore_index=True)
    gdf = gdf[gdf["talhao"].notna()].copy()
    metric = gdf.to_crs(CRS_METRIC)
    gdf["area_geom_ha"] = metric.geometry.area / 10_000.0
    gdf["area_ha"] = gdf["area_desc_ha"].fillna(gdf["area_geom_ha"])

    return (
        gdf.dissolve(by="talhao", aggfunc={"area_ha": "sum", "classe": "first", "area_geom_ha": "sum"})
        .reset_index()
    )


def _agg_operacional(ops: pd.DataFrame, servico: str) -> pd.DataFrame:
    if servico == "cobertura":
        return (
            ops.groupby("talhao", as_index=False)
            .agg(
                area_feita_ha=("ha_floresta", "sum"),
                horto=("horto", "first"),
                fertilizante=("fertilizante", "first"),
                status=("status", "first"),
            )
        )

    registros = []
    for talhao, grp in ops.groupby("talhao"):
        concluido = grp[grp["status"] == "concluido"]
        if not concluido.empty:
            status = "concluido"
            area_feita = float(concluido["area_ha"].sum())
            ref = concluido.iloc[0]
        else:
            status = "pendente"
            area_feita = 0.0
            ref = grp.iloc[0]
        registros.append(
            {
                "talhao": talhao,
                "area_feita_ha": area_feita,
                "horto": ref["horto"],
                "fertilizante": ref.get("fertilizante"),
                "status": status,
            }
        )
    return pd.DataFrame(registros)


def _aplicar_match_parcial(out: gpd.GeoDataFrame, agg: pd.DataFrame) -> gpd.GeoDataFrame:
    sem_geom = set(agg["talhao"]) - set(out["talhao"])
    for chave in sem_geom:
        base = talhao_base(chave)
        if not base or base not in set(out["talhao"]):
            continue
        row = agg[agg["talhao"] == chave].iloc[0]
        idx = out[out["talhao"] == base].index
        out.loc[idx, "area_feita_ha"] = out.loc[idx, "area_feita_ha"].fillna(0) + row["area_feita_ha"]
        out.loc[idx, "status"] = row["status"]
        out.loc[idx, "horto"] = row.get("horto")
        out.loc[idx, "fertilizante"] = row.get("fertilizante")
    return out


def cruzar_servico_gis(
    gis: gpd.GeoDataFrame,
    operacional: pd.DataFrame,
    servico: str,
    horto: str | None = None,
) -> gpd.GeoDataFrame:
    ops = operacional[operacional["servico"] == servico].copy()
    if horto and horto != "Todos":
        ops = ops[ops["horto"] == horto]

    if ops.empty:
        out = gis.copy()
        out["status"] = "sem_dado"
        out["area_feita_ha"] = 0.0
        out["area_restante_ha"] = out["area_ha"]
        out["pct_concluido"] = 0.0
        out["cor"] = STATUS_COLORS["sem_dado"]
        return out

    agg = _agg_operacional(ops, servico)
    out = gis.merge(agg, on="talhao", how="left")
    out["status"] = out["status"].fillna("sem_dado")
    out["area_feita_ha"] = out["area_feita_ha"].fillna(0.0)
    out = _aplicar_match_parcial(out, agg)

    out.loc[out["status"] == "pendente", "area_feita_ha"] = 0.0
    out["area_restante_ha"] = (out["area_ha"] - out["area_feita_ha"]).clip(lower=0.0)
    out.loc[out["status"] == "pendente", "area_restante_ha"] = out.loc[out["status"] == "pendente", "area_ha"]
    out["pct_concluido"] = (
        (out["area_feita_ha"] / out["area_ha"].replace(0, pd.NA) * 100.0)
        .fillna(0.0)
        .clip(0, 100)
    )
    out["cor"] = out["status"].map(STATUS_COLORS).fillna(STATUS_COLORS["sem_dado"])
    return out


def resumo_kpis(gdf: gpd.GeoDataFrame) -> dict:
    return {
        "talhoes_gis": len(gdf),
        "concluidos": int((gdf["status"] == "concluido").sum()),
        "pendentes": int((gdf["status"] == "pendente").sum()),
        "sem_dado": int((gdf["status"] == "sem_dado").sum()),
        "area_total_ha": float(gdf["area_ha"].sum()),
        "area_feita_ha": float(gdf["area_feita_ha"].sum()),
        "area_restante_ha": float(gdf["area_restante_ha"].sum()),
    }


def enriquecer_npk(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in df.iterrows():
        fert = row.get("fertilizante")
        dosagem = row.get("dosagem_realizada") or row.get("dosagem_kg_ha") or row.get("dosagem_recomendada")
        area = row.get("ha_floresta") or row.get("area_ha") or row.get("ha_total")
        if pd.isna(fert) or pd.isna(dosagem) or pd.isna(area):
            rows.append({**row.to_dict(), "n_total_kg": None, "p2o5_total_kg": None, "k2o_total_kg": None})
            continue
        try:
            nutrientes = calcular_nutrientes(str(fert), float(dosagem), float(area))
            rows.append(
                {
                    **row.to_dict(),
                    "n_total_kg": nutrientes.n_total_kg,
                    "p2o5_total_kg": nutrientes.p2o5_total_kg,
                    "k2o_total_kg": nutrientes.k2o_total_kg,
                }
            )
        except (ValueError, TypeError):
            rows.append({**row.to_dict(), "n_total_kg": None, "p2o5_total_kg": None, "k2o_total_kg": None})
    return pd.DataFrame(rows)


def listar_hortos(*dfs: pd.DataFrame) -> list[str]:
    hortos = set()
    for df in dfs:
        if "horto" in df.columns:
            hortos.update(df["horto"].dropna().astype(str).unique())
    return sorted(hortos)
