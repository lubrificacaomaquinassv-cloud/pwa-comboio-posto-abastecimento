"""Gera arquivos amostra para demo/CI quando planilhas reais não estão disponíveis."""
from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "sample"
OUT.mkdir(parents=True, exist_ok=True)


def gerar_cobertura() -> None:
    path = OUT / "cobertura_amostra.xlsx"
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for horto, rows in {
            "Reserva": [(216, 49.77, 49.77, "Sulfammo 10-05-22", 200, 8800)],
            "Eucalipto": [(220, 61.42, 61.42, "Sulfammo 10-05-22", 200, 9300)],
            "Poço Azul": [(172, 24.75, 24.75, "Sulfammo 10-05-22", 200, 4200)],
        }.items():
            sheet = pd.DataFrame(
                [
                    [None] * 10,
                    [None, None, f"{horto} - Adubação de Cobertura"] + [None] * 7,
                    [None, None, "2026 - 1º Semestre"] + [None] * 7,
                    [None] * 10,
                    [None, "Talhão", "Há Total", "Há Floresta", "Fertilizante", "Data", "Dosagem / há", None, "Total", "Operador"],
                    [None, None, None, None, None, None, "Recomendação", "Realizado", None, None],
                    [None] * 10,
                ]
            )
            for talhao, ha_total, ha_floresta, fert, dosagem, total in rows:
                sheet.loc[len(sheet)] = [
                    None,
                    talhao,
                    ha_total,
                    ha_floresta,
                    fert,
                    "2026-01-15",
                    dosagem,
                    dosagem * 0.95,
                    total,
                    "Operador Demo",
                ]
            sheet.to_excel(writer, sheet_name=horto, index=False, header=False)


def gerar_base() -> None:
    path = OUT / "base_amostra.xlsx"
    rows = []
    header = [
        [None] * 16,
        [None, None, "Subsolagem - Adubação de Base"] + [None] * 13,
        [None, None, "Plantio 2026"] + [None] * 13,
        [None] * 16,
        [None, "Horto", "Talhão", "Área Plantada", "Fertilizante", "Dosagem / há", "Total", "Prestador"]
        + [None, "Horto", "Talhão", "Área Plantada", "Fertilizante", "Dosagem / há", "Total", "Prestador"],
    ]
    for h in header:
        rows.append(h)
    rows.append(
        [None, "Reserva", 217, 36.47, "Basifós 06-34-05", 266, 9700, "R2 Serviços"]
        + [None, "Sede", 416, 12.56, None, 250, 3140, "Santa Virgínia"]
    )
    rows.append(
        [None, "Eucalipto", 220, 61.01, "Basifós 06-34-05", 295, 18000, "R2 Serviços"]
        + [None, "Sede", 417, 12.63, None, 250, 3157.5, "Santa Virgínia"]
    )
    pd.DataFrame(rows).to_excel(path, sheet_name="Subsolagem", index=False, header=False)


def gerar_gis() -> None:
    polys = {
        "216": Polygon([(-47.90, -20.10), (-47.89, -20.10), (-47.89, -20.11), (-47.90, -20.11)]),
        "217": Polygon([(-47.905, -20.10), (-47.895, -20.10), (-47.895, -20.105), (-47.905, -20.105)]),
        "220": Polygon([(-47.91, -20.12), (-47.90, -20.12), (-47.90, -20.13), (-47.91, -20.13)]),
        "416": Polygon([(-47.915, -20.115), (-47.905, -20.115), (-47.905, -20.125), (-47.915, -20.125)]),
        "417": Polygon([(-47.916, -20.126), (-47.906, -20.126), (-47.906, -20.136), (-47.916, -20.136)]),
    }
    gdf = gpd.GeoDataFrame(
        {
            "talhao": list(polys.keys()),
            "Name": list(polys.keys()),
            "classe": ["Silvicultura"] * 3 + ["Silvipastoril"] * 2,
            "area_ha": [49.77, 36.47, 61.42, 12.56, 12.63],
        },
        geometry=list(polys.values()),
        crs="EPSG:4326",
    )
    gdf.to_file(OUT / "talhoes_amostra.geojson", driver="GeoJSON")


if __name__ == "__main__":
    gerar_cobertura()
    gerar_base()
    gerar_gis()
    print(f"Amostras geradas em {OUT}")
