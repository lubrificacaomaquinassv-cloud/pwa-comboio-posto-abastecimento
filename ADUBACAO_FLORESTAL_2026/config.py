"""Configuração central do painel."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Arquivos no PC da fazenda (produção)
PATH_COBERTURA = Path(r"d:\Relatório Serviços\Adubação de Cobertura .xlsx")
PATH_BASE = Path(r"d:\Relatório Serviços\Subsolagem 2026\Adubação de Base 2026.xlsx")
PATH_KML = Path(r"d:\fazenda_santa_virginia_completo.kml")

# Demo quando arquivos reais não existem (nuvem / teste)
PATH_SAMPLE = ROOT / "data" / "sample"

KML_LAYERS = ["Silvicultura (#2)", "Silvipastoril (#2)"]
CRS_METRIC = "EPSG:31982"

TITULO = "Adubação Florestal 2026"
SUBTITULO = "Fazenda Santa Virgínia"
BUILD = "2026.08.01"
