@echo off
cd /d "%~dp0"
if not exist ui.py (
  echo.
  echo  FALTA ui.py - pasta incompleta!
  echo  Rode primeiro: ATUALIZAR_PASTA.bat
  echo.
  pause
  exit /b 1
)
call RODAR_PAINEL.bat
