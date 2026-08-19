@echo off
cd /d "%~dp0"
if not exist .streamlit\secrets.toml (
  echo Copie .streamlit\secrets.toml.example para .streamlit\secrets.toml e preencha SUPABASE_KEY
  pause
  exit /b 1
)
pip install -r requirements.txt
streamlit run app.py
