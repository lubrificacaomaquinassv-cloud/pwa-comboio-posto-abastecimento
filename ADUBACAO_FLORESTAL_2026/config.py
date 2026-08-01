"""Configuração de caminhos — produção (Windows) e amostra (demo)."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_SAMPLE = ROOT / "data" / "sample"

# Caminhos padrão no PC da fazenda (Windows)
PATH_COBERTURA = Path(
    os.getenv(
        "ADUBACAO_COBERTURA",
        r"d:\Relatório Serviços\Adubação de Cobertura .xlsx",
    )
)
PATH_BASE = Path(
    os.getenv(
        "ADUBACAO_BASE",
        r"d:\Relatório Serviços\Subsolagem 2026\Adubação de Base 2026.xlsx",
    )
)
PATH_KML = Path(
    os.getenv(
        "ADUBACAO_KML",
        r"d:\fazenda_santa_virginia_completo.kml",
    )
)

# Fallback para demo / CI quando arquivos reais não existem
PATH_COBERTURA_SAMPLE = DATA_SAMPLE / "cobertura_amostra.xlsx"
PATH_BASE_SAMPLE = DATA_SAMPLE / "base_amostra.xlsx"
PATH_GIS_SAMPLE = DATA_SAMPLE / "talhoes_amostra.geojson"

KML_LAYERS = ["Silvicultura (#2)", "Silvipastoril (#2)"]
CRS_METRIC = "EPSG:31982"

DASHBOARD_BUILD = "2026.08.01-cloud"
