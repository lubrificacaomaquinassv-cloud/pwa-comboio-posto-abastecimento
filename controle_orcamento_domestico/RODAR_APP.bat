@echo off
cd /d "%~dp0"
title Orcamento Domestico - Streamlit (porta 8502)

echo Fazendo backup automatico dos dados (so o arquivo orcamento.db)...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0backup_auto.ps1"

if not exist .venv\Scripts\python.exe (
  echo Criando ambiente virtual...
  py -3 -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install -U pip -q
pip install -r requirements.txt -q
echo.
echo ============================================
echo  ORCAMENTO DOMESTICO (nao e Importacao SAP)
echo  Abra no navegador: http://localhost:8502
echo  Backup local: %~dp0backups\
echo ============================================
echo.
streamlit run app.py --server.port 8502 --browser.serverPort 8502

echo.
echo Backup ao fechar...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0backup_auto.ps1"
pause
