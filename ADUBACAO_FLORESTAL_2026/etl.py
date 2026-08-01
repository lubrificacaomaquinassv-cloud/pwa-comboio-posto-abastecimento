"""ETL — planilhas Excel + cadastro KML."""
from __future__ import annotations

import re
from pathlib import Path

import geopandas as gpd
import pandas as pd
from pyogrio import list_layers

from config import CRS_METRIC, KML_LAYERS, PATH_BASE, PATH_COBERTURA, PATH_KML, PATH_SAMPLE

CORES = {"concluido": "#2ecc71", "pendente": "#e74c3c", "sem_dado": "#7f8c8d"}
STATUS_LABEL = {"concluido": "Concluído", "pendente": "Pendente", "sem_dado": "Sem registro"}
SERVICO_LABEL = {"cobertura": "Adubação de Cobertura", "base": "Adubação de Base / Subsolagem"}
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


def _col_talhao(g: gpd.GeoDataFrame) -> pd.Series | None:
    for col in ("Name", "name", "NAME", "talhao", "Talhao", "TALHAO"):
        if col in g.columns:
            return g[col]
    return None


def _ler_camada_kml(kml: Path, layer: str) -> gpd.GeoDataFrame | None:
    g = gpd.read_file(kml, layer=layer)
    if g.empty:
        return None
    col = _col_talhao(g)
    if col is None:
        return None
    g = g.copy()
    g["talhao"] = col.astype(str).map(_talhao)
    g["retiro_kml"] = layer.split("(")[0].strip() if "(" in layer else layer
    return g[g["talhao"].notna()]


def load_gis(path: Path | None = None, *, permitir_demo: bool = False) -> gpd.GeoDataFrame:
    kml = path if path and path.exists() else (PATH_KML if PATH_KML.exists() else None)
    if kml:
        partes = []
        layers = _kml_layers(kml)
        for layer in layers:
            try:
                g = _ler_camada_kml(kml, layer)
                if g is not None and not g.empty:
                    partes.append(g)
            except Exception:
                continue
        if not partes:
            raise ValueError(
                f"KML carregado ({kml.name}) mas sem talhões reconhecíveis. "
                f"Camadas lidas: {', '.join(layers[:6])}{'…' if len(layers) > 6 else ''}"
            )
        gdf = pd.concat(partes, ignore_index=True)
    elif permitir_demo:
        gdf = gpd.read_file(PATH_SAMPLE / "talhoes.geojson")
    else:
        raise FileNotFoundError(
            "Cadastro GIS (KML) não carregado. Envie o arquivo "
            "fazenda_santa_virginia_completo.kml na barra lateral."
        )

    metric = gdf.to_crs(CRS_METRIC)
    gdf["area_ha"] = metric.geometry.area / 10_000
    if "retiro_kml" in gdf.columns:
        gdf = gdf.dissolve(by="talhao", aggfunc={"area_ha": "sum", "retiro_kml": "first"}).reset_index()
    else:
        gdf = gdf.dissolve(by="talhao", aggfunc={"area_ha": "sum"}).reset_index()
    return gdf


def _fmt_data(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    if hasattr(v, "strftime"):
        return v.strftime("%d/%m/%Y")
    return str(v)


def _unicos(serie, limite: int = 3) -> str:
    vals = [str(v).strip() for v in serie.dropna().unique() if str(v).strip()]
    if not vals:
        return "—"
    txt = " · ".join(vals[:limite])
    if len(vals) > limite:
        txt += f" (+{len(vals) - limite})"
    return txt


def retiros(ops: pd.DataFrame, servico: str) -> list[str]:
    o = ops[ops["servico"] == servico]
    vals = sorted({str(v).strip() for v in o["horto"].dropna() if str(v).strip()})
    return vals


def historico(ops: pd.DataFrame, talhao: str, servico: str) -> pd.DataFrame:
    o = ops[ops["servico"] == servico].copy()
    chaves = {talhao, _base_talhao(talhao)}
    chaves.discard(None)
    mask = o["talhao"].isin(chaves)
    if not mask.any() and _base_talhao(talhao):
        mask = o["talhao"].astype(str).str.startswith(_base_talhao(talhao))
    h = o[mask].copy()
    if servico == "cobertura":
        cols = ["horto", "talhao", "ha_floresta", "fertilizante", "data", "dos_rec", "dos_real", "total_kg", "operador", "status"]
    else:
        cols = ["horto", "talhao", "area_ha", "fertilizante", "dosagem", "total_kg", "prestador", "status"]
    cols = [c for c in cols if c in h.columns]
    return h[cols].sort_values(["status", "data"] if "data" in h.columns else ["status", "talhao"])


def _popup_html(row, servico: str) -> str:
    retiro = row.get("retiro") or row.get("horto") or "—"
    status = STATUS_LABEL.get(row.get("status"), row.get("status", "—"))
    serv = SERVICO_LABEL.get(servico, servico)
    pct = 0.0
    if row.get("area_ha"):
        pct = min(100.0, 100.0 * float(row.get("area_feita", 0)) / float(row["area_ha"]))
    extras = []
    if row.get("fertilizante") and str(row["fertilizante"]) != "—":
        extras.append(f"<b>Fertilizante:</b> {row['fertilizante']}")
    if row.get("data_fmt") and str(row["data_fmt"]) != "—":
        extras.append(f"<b>Data:</b> {row['data_fmt']}")
    if row.get("dosagem") and str(row["dosagem"]) != "—":
        extras.append(f"<b>Dosagem:</b> {row['dosagem']} kg/ha")
    if row.get("operador") and str(row["operador"]) != "—":
        extras.append(f"<b>Operador:</b> {row['operador']}")
    if row.get("prestador") and str(row["prestador"]) != "—":
        extras.append(f"<b>Prestador:</b> {row['prestador']}")
    bloco = "<br>".join(extras)
    return (
        f"<div style='min-width:240px;font-family:Barlow,Arial,sans-serif;line-height:1.45'>"
        f"<div style='font-size:18px;font-weight:700;color:#1a3d1c;margin-bottom:6px'>Talhão {row.talhao}</div>"
        f"<div style='color:#4a6745;margin-bottom:8px'><b>Retiro:</b> {retiro}</div>"
        f"<div style='margin-bottom:8px'><span style='background:{row.get('cor','#888')};color:#fff;"
        f"padding:2px 8px;border-radius:4px;font-size:12px'>{status}</span></div>"
        f"<div><b>Área cadastro:</b> {row.area_ha:.1f} ha<br>"
        f"<b>Feito:</b> {row.area_feita:.1f} ha · <b>Restante:</b> {row.area_rest:.1f} ha<br>"
        f"<b>Progresso:</b> {pct:.0f}%</div>"
        f"<hr style='border:none;border-top:1px solid #ddd;margin:8px 0'>"
        f"<div style='font-size:12px;color:#555'><b>{serv}</b><br>{bloco or 'Sem lançamento na planilha.'}</div>"
        f"</div>"
    )


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
        r.loc[idx, "retiro"] = row.get("retiro") or row.get("horto")
        for col in ("fertilizante", "data", "dosagem", "operador", "prestador"):
            if col in row.index and col in r.columns:
                r.loc[idx, col] = row[col]
    return r


def _enriquecer_mapa(r: gpd.GeoDataFrame, servico: str) -> gpd.GeoDataFrame:
    r["retiro"] = r.get("retiro", pd.Series("—", index=r.index)).fillna("—")
    r["status"] = r["status"].fillna("sem_dado")
    r["area_feita"] = r["area_feita"].fillna(0)
    r.loc[r["status"] == "pendente", "area_feita"] = 0
    r["area_rest"] = (r["area_ha"] - r["area_feita"]).clip(lower=0)
    r["cor"] = r["status"].map(CORES).fillna(CORES["sem_dado"])
    r["status_label"] = r["status"].map(STATUS_LABEL).fillna("Sem registro")
    r["fertilizante"] = r.get("fertilizante", pd.Series("—", index=r.index)).fillna("—")
    r["operador"] = r.get("operador", pd.Series("—", index=r.index)).fillna("—")
    r["prestador"] = r.get("prestador", pd.Series("—", index=r.index)).fillna("—")
    r["data_fmt"] = r.get("data", pd.Series(pd.NaT, index=r.index)).map(_fmt_data)
    r["dosagem"] = r.get("dosagem", pd.Series(None, index=r.index)).apply(
        lambda v: "—" if v is None or (isinstance(v, float) and pd.isna(v)) else f"{float(v):.0f}"
    )
    r["tooltip"] = r.apply(
        lambda row: f"Talhão {row.talhao} · Retiro {row.retiro} · {row.status_label} · "
        f"{row.area_feita:.1f}/{row.area_ha:.1f} ha",
        axis=1,
    )
    r["popup"] = r.apply(lambda row: _popup_html(row, servico), axis=1)
    return r


def cruzar(gis: gpd.GeoDataFrame, ops: pd.DataFrame, servico: str) -> gpd.GeoDataFrame:
    o = ops[ops["servico"] == servico].copy()
    if o.empty:
        r = gis.copy()
        r["status"] = "sem_dado"
        r["area_feita"] = 0.0
        r["area_rest"] = r["area_ha"]
        if "retiro_kml" in r.columns:
            r["retiro"] = r["retiro_kml"].fillna("—")
        else:
            r["retiro"] = "—"
        return _enriquecer_mapa(r, servico)

    if servico == "cobertura":
        agg = o.groupby("talhao").agg(
            area_feita=("ha_floresta", "sum"),
            retiro=("horto", "first"),
            status=("status", "first"),
            fertilizante=("fertilizante", _unicos),
            data=("data", "max"),
            dosagem=("dos_real", "mean"),
            operador=("operador", _unicos),
        ).reset_index()
        agg["prestador"] = "—"
    else:
        rows = []
        for t, g in o.groupby("talhao"):
            ok = g[g["status"] == "concluido"]
            pend = g[g["status"] == "pendente"]
            src = ok if len(ok) else pend
            rows.append({
                "talhao": t,
                "area_feita": float(ok["area_ha"].sum()) if len(ok) else 0.0,
                "retiro": g.iloc[0]["horto"],
                "status": "concluido" if len(ok) else "pendente",
                "fertilizante": _unicos(src["fertilizante"]),
                "data": pd.NaT,
                "dosagem": float(src["dosagem"].mean()) if len(src) and src["dosagem"].notna().any() else None,
                "operador": "—",
                "prestador": _unicos(src["prestador"]),
            })
        agg = pd.DataFrame(rows)

    r = _aplicar_match_parcial(gis, agg)
    if "retiro_kml" in r.columns:
        sem = r["retiro"].isna() | (r["retiro"].astype(str) == "—")
        r.loc[sem, "retiro"] = r.loc[sem, "retiro_kml"].fillna("—")
    r["retiro"] = r["retiro"].fillna("—")
    return _enriquecer_mapa(r, servico)


def kpis(gdf: gpd.GeoDataFrame) -> dict:
    return {
        "talhoes": len(gdf),
        "ok": int((gdf["status"] == "concluido").sum()),
        "pend": int((gdf["status"] == "pendente").sum()),
        "ha_feita": float(gdf["area_feita"].sum()),
        "ha_rest": float(gdf["area_rest"].sum()),
    }
