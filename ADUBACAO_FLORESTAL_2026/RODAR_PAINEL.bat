@echo off
cd /d "%~dp0"
title Adubacao Florestal 2026
color 0A
echo.
echo  ========================================
echo   PAINEL ADUBACAO FLORESTAL 2026 - SV
echo  ========================================
echo.
echo  Pasta: %CD%
echo.
py -m pip install -r requirements.txt -q 2>nul
if errorlevel 1 (
  echo  ERRO: Python nao encontrado. Instale Python 3.12+ de python.org
  pause
  exit /b 1
)
if not exist "data\sample\cobertura_amostra.xlsx" py scripts\gerar_dados_amostra.py >nul 2>&1
echo  Abrindo http://localhost:8501 ...
echo  (Feche esta janela para encerrar o painel)
echo.
start "" "http://localhost:8501"
py -m streamlit run app.py --server.port 8501 --browser.gatherUsageStats false
pause
