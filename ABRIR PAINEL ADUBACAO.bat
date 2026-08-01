@echo off
cd /d "%~dp0"
if not exist "ADUBACAO_FLORESTAL_2026\app.py" (
  call "INSTALAR PAINEL ADUBACAO.bat"
) else (
  cd ADUBACAO_FLORESTAL_2026
  call RODAR_PAINEL.bat
)
