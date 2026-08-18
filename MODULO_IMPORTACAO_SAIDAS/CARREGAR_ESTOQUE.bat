@echo off
cd /d "%~dp0"
python scripts\carregar_estoque.py dados\estoque_inclusoes.csv %*
if errorlevel 1 pause
