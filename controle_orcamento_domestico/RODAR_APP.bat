@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Orcamento Domestico - porta 8502
color 0A

echo.
echo ============================================================
echo   ORCAMENTO DOMESTICO
echo   1a vez pode demorar 3 a 10 minutos (instala bibliotecas)
echo   Nao feche esta janela ate aparecer "Local URL"
echo ============================================================
echo.

if not exist ".streamlit\config.toml" (
  if exist "streamlit_config.toml" (
    if not exist ".streamlit" mkdir ".streamlit"
    copy /Y "streamlit_config.toml" ".streamlit\config.toml" >nul
  )
)

where py >nul 2>&1
if %ERRORLEVEL%==0 (
  set PY=py -3
) else (
  where python >nul 2>&1
  if %ERRORLEVEL%==0 (
    set PY=python
  ) else (
    echo [ERRO] Python nao encontrado.
    echo Instale em https://www.python.org/downloads/
    echo Marque "Add python.exe to PATH" e rode este arquivo de novo.
    pause
    exit /b 1
  )
)

if not exist .venv\Scripts\python.exe (
  echo [1/4] Criando ambiente virtual... aguarde...
  %PY% -m venv .venv
  if errorlevel 1 (
    echo [ERRO] Nao foi possivel criar .venv
    pause
    exit /b 1
  )
  echo       OK - ambiente criado.
) else (
  echo [1/4] Ambiente virtual ja existe - pulando.
)

echo [2/4] Ativando ambiente...
call .venv\Scripts\activate.bat

echo [3/4] Instalando Streamlit e pandas... aguarde...
python -m pip install -U pip
pip install -r requirements.txt
if errorlevel 1 (
  echo [ERRO] Falha no pip install. Verifique internet.
  pause
  exit /b 1
)
echo       OK - bibliotecas instaladas.

if exist "backup_auto.ps1" (
  echo [extra] Backup dos dados...
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0backup_auto.ps1" 2>nul
)

echo.
echo [4/4] Abrindo painel...
echo       Navegador: http://localhost:8502
echo       Para parar: feche esta janela ou Ctrl+C
echo.
streamlit run app.py --server.port 8502 --browser.serverPort 8502

if exist "backup_auto.ps1" (
  echo Backup ao fechar...
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0backup_auto.ps1" 2>nul
)
echo.
pause
