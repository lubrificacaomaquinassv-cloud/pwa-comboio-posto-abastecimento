@echo off
cd /d "%~dp0"
if not exist .venv (
  python -m venv .venv
)
call .venv\Scripts\activate.bat
pip install -r requirements.txt
echo Instalacao concluida. Configure .streamlit\secrets.toml e use CARREGAR_CATALOGO.bat
pause
