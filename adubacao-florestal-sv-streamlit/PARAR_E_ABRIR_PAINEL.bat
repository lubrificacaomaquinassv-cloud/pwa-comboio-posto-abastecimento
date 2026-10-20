@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo === Reiniciar painel (fecha o localhost antigo) ===
echo Pasta: %CD%
echo.

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8501" ^| findstr LISTENING') do (
    echo Encerrando processo na porta 8501 PID %%a
    taskkill /PID %%a /F >nul 2>&1
)

if not exist ".streamlit\secrets.toml" (
    echo ERRO: falta .streamlit\secrets.toml
    echo Rode CONFIGURAR_PAINEL_LOCAL.ps1 primeiro.
    pause
    exit /b 1
)

where py >nul 2>&1 && set PY=py || set PY=python
echo Instalando dependencias...
%PY% -m pip install -q -U "streamlit>=1.38" "psycopg[binary]>=3.2" sqlalchemy -r requirements.txt

echo.
echo Abrindo http://localhost:8501
echo IMPORTANTE: na barra lateral marque Supabase (oficial)
echo.
%PY% -m streamlit run app.py
pause
