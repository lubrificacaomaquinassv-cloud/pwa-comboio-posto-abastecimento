@echo off
cd /d "%~dp0"
title Adubacao Florestal 2026 - Santa Virginia
echo.
echo  PAINEL ADUBACAO FLORESTAL 2026
echo  ==============================
echo.
py -m pip install -r requirements.txt -q 2>nul
if not exist "data\sample\cobertura_amostra.xlsx" py scripts\gerar_dados_amostra.py >nul 2>&1
echo  Abrindo painel... aguarde o navegador.
echo  Link: http://localhost:8501
echo.
py -m streamlit run app.py --server.port 8501
pause
