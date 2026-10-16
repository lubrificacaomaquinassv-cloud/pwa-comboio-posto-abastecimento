@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Criando ambiente virtual...
  py -3 -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install -U pip
pip install -r requirements.txt
streamlit run app.py
