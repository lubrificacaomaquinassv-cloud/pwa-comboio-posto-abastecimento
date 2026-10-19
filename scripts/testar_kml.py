#!/usr/bin/env python3
"""Só lê o KML — não usa Supabase."""
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from ingestion.kml_parser import ler_talhoes_kml

path = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\hmauricio\Desktop\DADOS_PAINEL\fazenda_santa_virginia_completo.kml"
gdf = ler_talhoes_kml(path)
com_num = gdf["talhao"].notna().sum()
print(f"Arquivo: {path}")
print(f"Poligonos no KML: {len(gdf)} | com numero de talhao: {com_num}")
if com_num == 0:
    sys.exit("KML sem talhoes validos — confira a pasta Talhoes no arquivo.")
print("KML OK — pode gravar no Supabase.")
