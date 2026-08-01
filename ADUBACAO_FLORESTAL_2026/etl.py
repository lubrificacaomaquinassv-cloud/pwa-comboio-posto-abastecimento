"""ETL — planilhas Excel + cadastro KML."""
from __future__ import annotations

import re
from pathlib import Path

import geopandas as gpd
import pandas as pd

from config import CRS_METRIC, KML_LAYERS, PATH_BASE, PATH_COBERTURA, PATH_KML, PATH_SAMPLE

CORES = {"concluido": "#2ecc71", "pendente": "#e74c3c", "sem_dado": "#7f8c8d"}
_TALHAO = re.compile(r"^(\d+)([A-Za-z]?)$")


def _talhao(v) -> str | None:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = str(v).strip().upper().replace(" ", "")
    m = _TALHAO.match(s)
    return f"{int(m.group(1))}{m.group(2)}" if m else (s or None)


def _path(prim: Path, nome_sample: str) -> Path:
    return prim if prim.exists() else PATH_SAMPLE / nome_sample


def load_cobertura() -> pd.DataFrame:
    path = _path(PATH_COBERTURA, "cobertura.xlsx")
    partes = []
    for horto in pd.ExcelFile(path).sheet_names:
        raw = pd.read_excel(path, sheet_name=horto, header=None)
        df = raw.iloc[7:].copy()
        df.columns = ["_", "talhao", "ha_total", "ha_floresta", "fertilizante", "data",
                      "dos_rec", "dos_real", "total_kg", "operador"]
        df = df[df["talhao"].notna()].copy()
        df["talhao"] = df["talhao"].map(_talhao)
        df["horto"] = horto.strip()
        df["servico"] = "cobertura"
        df["status"] = "concluido"
        for c in ("ha_total", "ha_floresta", "dos_rec", "dos_real", "total_kg"):
            df[c] = pd.to_numeric(df[c], errors="coerce")
        partes.append(df.drop(columns=["_"]))
    return pd.concat(partes, ignore_index=True)


def load_base() -> pd.DataFrame:
    path = _path(PATH_BASE, "base.xlsx")
    raw = pd.read_excel(path, sheet_name="Subsolagem", header=None)

    def lado(cols, status):
        d = raw.iloc[5:, cols].copy()
        d.columns = ["horto", "talhao", "area_ha", "fertilizante", "dosagem", "total_kg", "prestador"]
        d["talhao"] = d["talhao"].map(_talhao)
        d = d[d["talhao"].notna()]
        d["area_ha"] = pd.to_numeric(d["area_ha"], errors="coerce")
        d["servico"] = "base"
        d["status"] = status
        return d

    return pd.concat([lado([1, 2, 3, 4, 5, 6, 7], "concluido"), lado([9, 10, 11, 12, 13, 14, 15], "pendente")], ignore_index=True)


def load_gis() -> gpd.GeoDataFrame:
    if PATH_KML.exists():
        partes = []
        for layer in KML_LAYERS:
            g = gpd.read_file(PATH_KML, layer=layer)
            if g.empty:
                continue
            g["talhao"] = g["Name"].astype(str).map(_talhao)
            partes.append(g[g["talhao"].notna()])
        gdf = pd.concat(partes, ignore_index=True)
    else:
        gdf = gpd.read_file(PATH_SAMPLE / "talhoes.geojson")

    m = gdf.to_crs(CRS_METRIC)
    gdf["area_ha"] = m.geometry.area / 10_000
    return gdf.dissolve(by="talhao", aggfunc={"area_ha": "sum"}).reset_index()


def cruzar(gis: gpd.GeoDataFrame, ops: pd.DataFrame, servico: str) -> gpd.GeoDataFrame:
    o = ops[ops["servico"] == servico].copy()
    if o.empty:
        r = gis.copy()
        r["status"] = "sem_dado"
        r["area_feita"] = 0.0
        r["area_rest"] = r["area_ha"]
        r["cor"] = CORES["sem_dado"]
        return r

    if servico == "cobertura":
        agg = o.groupby("talhao").agg(area_feita=("ha_floresta", "sum"), horto=("horto", "first"), status=("status", "first")).reset_index()
    else:
        rows = []
        for t, g in o.groupby("talhao"):
            ok = g[g["status"] == "concluido"]
            rows.append({"talhao": t, "area_feita": ok["area_ha"].sum() if len(ok) else 0,
                         "horto": g.iloc[0]["horto"], "status": "concluido" if len(ok) else "pendente"})
        agg = pd.DataFrame(rows)

    r = gis.merge(agg, on="talhao", how="left")
    r["status"] = r["status"].fillna("sem_dado")
    r["area_feita"] = r["area_feita"].fillna(0)
    r.loc[r["status"] == "pendente", "area_feita"] = 0
    r["area_rest"] = (r["area_ha"] - r["area_feita"]).clip(lower=0)
    r["cor"] = r["status"].map(CORES).fillna(CORES["sem_dado"])
    return r


def kpis(gdf: gpd.GeoDataFrame) -> dict:
    return {
        "talhoes": len(gdf),
        "ok": int((gdf["status"] == "concluido").sum()),
        "pend": int((gdf["status"] == "pendente").sum()),
        "ha_feita": float(gdf["area_feita"].sum()),
        "ha_rest": float(gdf["area_rest"].sum()),
    }
