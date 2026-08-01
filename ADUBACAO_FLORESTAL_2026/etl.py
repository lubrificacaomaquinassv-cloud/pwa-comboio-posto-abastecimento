"""ETL — planilhas Excel + cadastro KML."""
from __future__ import annotations

import re
from pathlib import Path

import geopandas as gpd
import pandas as pd
from pyogrio import list_layers

from config import CRS_METRIC, KML_LAYERS, PATH_BASE, PATH_COBERTURA, PATH_KML, PATH_SAMPLE

CORES = {"concluido": "#2ecc71", "pendente": "#e74c3c", "sem_dado": "#7f8c8d"}
_TALHAO = re.compile(r"^(\d+)([A-Za-z]?)$")


def _talhao(v) -> str | None:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = str(v).strip().upper().replace(" ", "")
    m = _TALHAO.match(s)
    return f"{int(m.group(1))}{m.group(2)}" if m else (s or None)


def _base_talhao(chave: str | None) -> str | None:
    if not chave:
        return None
    m = _TALHAO.match(chave)
    return m.group(1) if m else chave


def _resolve(prim: Path | None, fallback_name: str) -> Path:
    if prim and prim.exists():
        return prim
    if prim and not prim.exists():
        sample = PATH_SAMPLE / fallback_name
        if sample.exists():
            return sample
    return _resolve(None, fallback_name) if prim else PATH_SAMPLE / fallback_name


def load_cobertura(path: Path | None = None) -> pd.DataFrame:
    path = path if path and path.exists() else (PATH_COBERTURA if PATH_COBERTURA.exists() else PATH_SAMPLE / "cobertura.xlsx")
    partes = []
    for horto in pd.ExcelFile(path).sheet_names:
        raw = pd.read_excel(path, sheet_name=horto, header=None)
        df = raw.iloc[7:].copy()
        df.columns = ["_", "talhao", "ha_total", "ha_floresta", "fertilizante", "data",
                      "dos_rec", "dos_real", "total_kg", "operador"]
        df = df[df["talhao"].notna()].copy()
        df["talhao"] = df["talhao"].map(_talhao)
        df = df[df["talhao"].notna()]
        df["horto"] = horto.strip()
        df["servico"] = "cobertura"
        df["status"] = "concluido"
        for c in ("ha_total", "ha_floresta", "dos_rec", "dos_real", "total_kg"):
            df[c] = pd.to_numeric(df[c], errors="coerce")
        partes.append(df.drop(columns=["_"]))
    return pd.concat(partes, ignore_index=True)


def load_base(path: Path | None = None) -> pd.DataFrame:
    path = path if path and path.exists() else (PATH_BASE if PATH_BASE.exists() else PATH_SAMPLE / "base.xlsx")
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


def _kml_layers(kml: Path) -> list[str]:
    disponiveis = [nome for nome, _ in list_layers(kml)]
    alvo = [
        nome for nome in disponiveis
        if any(tag in nome.lower() for tag in ("silvicultura", "silvipastoril"))
    ]
    if alvo:
        return alvo
    for nome in KML_LAYERS:
        if nome in disponiveis:
            return [nome]
    return disponiveis


def load_gis(path: Path | None = None) -> gpd.GeoDataFrame:
    kml = path if path and path.exists() else (PATH_KML if PATH_KML.exists() else None)
    if kml:
        partes = []
        for layer in _kml_layers(kml):
            g = gpd.read_file(kml, layer=layer)
            if g.empty or "Name" not in g.columns:
                continue
            g["talhao"] = g["Name"].astype(str).map(_talhao)
            partes.append(g[g["talhao"].notna()])
        if not partes:
            raise ValueError("KML sem talhões nas camadas Silvicultura/Silvipastoril.")
        gdf = pd.concat(partes, ignore_index=True)
    else:
        gdf = gpd.read_file(PATH_SAMPLE / "talhoes.geojson")

    metric = gdf.to_crs(CRS_METRIC)
    gdf["area_ha"] = metric.geometry.area / 10_000
    return gdf.dissolve(by="talhao", aggfunc={"area_ha": "sum"}).reset_index()


def _aplicar_match_parcial(gis: gpd.GeoDataFrame, agg: pd.DataFrame) -> gpd.GeoDataFrame:
    r = gis.merge(agg, on="talhao", how="left")
    extras = set(agg["talhao"]) - set(gis["talhao"])
    for chave in extras:
        base = _base_talhao(chave)
        if not base or base not in set(gis["talhao"]):
            continue
        row = agg[agg["talhao"] == chave].iloc[0]
        idx = r[r["talhao"] == base].index
        r.loc[idx, "area_feita"] = r.loc[idx, "area_feita"].fillna(0) + row["area_feita"]
        r.loc[idx, "status"] = row["status"]
        r.loc[idx, "horto"] = row.get("horto")
    return r


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
        agg = o.groupby("talhao").agg(
            area_feita=("ha_floresta", "sum"), horto=("horto", "first"), status=("status", "first")
        ).reset_index()
    else:
        rows = []
        for t, g in o.groupby("talhao"):
            ok = g[g["status"] == "concluido"]
            rows.append({
                "talhao": t,
                "area_feita": float(ok["area_ha"].sum()) if len(ok) else 0.0,
                "horto": g.iloc[0]["horto"],
                "status": "concluido" if len(ok) else "pendente",
            })
        agg = pd.DataFrame(rows)

    r = _aplicar_match_parcial(gis, agg)
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
