@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo === Painel Adubacao - neste PC (localhost) ===
echo Pasta: %CD%
echo.

where py >nul 2>&1 && set PY=py || set PY=python
echo Instalando dependencias (Streamlit 1.38+)...
%PY% -m pip install -q -U "streamlit>=1.38" -r requirements.txt
if errorlevel 1 (
    echo ERRO: instale Python 3.11+ e adicione ao PATH.
    pause
    exit /b 1
)

echo Abrindo o painel em http://localhost:8501
echo Na barra lateral: Versao do painel 2026.10.20-mapa-ficha-v3
echo Escolha "Ver talhao" na barra lateral esquerda.
echo.
%PY% -m streamlit run app.py
pause
