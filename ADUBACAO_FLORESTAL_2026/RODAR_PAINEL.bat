@echo off
cd /d "%~dp0"
echo Instalando dependencias...
py -m pip install -r requirements.txt -q
if not exist "data\sample\cobertura_amostra.xlsx" (
  echo Gerando dados amostra...
  py scripts\gerar_dados_amostra.py
)
echo Iniciando Dashboard Adubacao Florestal 2026...
py -m streamlit run app.py
pause
