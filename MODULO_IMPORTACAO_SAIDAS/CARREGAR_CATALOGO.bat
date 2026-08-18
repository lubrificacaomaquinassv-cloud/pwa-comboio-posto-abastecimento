@echo off
cd /d "%~dp0"
python scripts\carregar_catalogo.py dados\catalogo_inclusoes.csv %*
if errorlevel 1 pause
