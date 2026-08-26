@echo off
cd /d "%~dp0"
echo Instalando dependencias (streamlit, supabase, pandas)...
python -m pip install -r requirements.txt -q
if errorlevel 1 (
  echo ERRO: pip install falhou. Verifique se Python esta instalado.
  pause
  exit /b 1
)
echo.
echo Abrindo app em http://localhost:8501
python -m streamlit run app.py
pause
