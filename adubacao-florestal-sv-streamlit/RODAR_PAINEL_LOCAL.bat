@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo === Painel Adubacao - neste PC (localhost) ===
echo Pasta: %CD%
echo.

where py >nul 2>&1 && set PY=py || set PY=python

if not exist ".streamlit\secrets.toml" (
    echo.
    echo PRIMEIRA VEZ: configure a conexao Supabase...
    powershell -ExecutionPolicy Bypass -File "%~dp0CONFIGURAR_PAINEL_LOCAL.ps1"
    if errorlevel 1 exit /b 1
)

echo Instalando dependencias (Streamlit 1.38+)...
%PY% -m pip install -q -U "streamlit>=1.38" -r requirements.txt
if errorlevel 1 (
    echo ERRO: instale Python 3.11+ e adicione ao PATH.
    pause
    exit /b 1
)

echo Pasta: %CD%
echo Abrindo o painel em http://localhost:8501
echo Na barra lateral: Versao do painel 2026.10.20-mapa-ficha-v3
echo Escolha "Ver talhao" na barra lateral esquerda.
echo.
%PY% -m streamlit run app.py
pause
