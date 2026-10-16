@echo off
chcp 65001 >nul
cd /d "%~dp0"
set ORIGEM=%~dp0
set DEST=%ORIGEM%LEVAR_PARA_CASA

echo.
echo ============================================
echo   PREPARANDO PACOTE PARA PENDRIVE / CASA
echo ============================================
echo.

if not exist "%DEST%" mkdir "%DEST%"
if not exist "%DEST%\data" mkdir "%DEST%\data"
if not exist "%DEST%\.streamlit" mkdir "%DEST%\.streamlit"

copy /Y "%ORIGEM%app.py" "%DEST%\"
copy /Y "%ORIGEM%database.py" "%DEST%\"
copy /Y "%ORIGEM%fatura.py" "%DEST%\"
copy /Y "%ORIGEM%requirements.txt" "%DEST%\"
copy /Y "%ORIGEM%RODAR_APP.bat" "%DEST%\"
copy /Y "%ORIGEM%BACKUP_DADOS.bat" "%DEST%\"
copy /Y "%ORIGEM%backup_auto.ps1" "%DEST%\"
copy /Y "%ORIGEM%PREPARAR_PEN_DRIVE.bat" "%DEST%\"
copy /Y "%ORIGEM%LEVAR_PARA_CASA\LEIA-ME.txt" "%DEST%\LEIA-ME.txt"
if exist "%ORIGEM%.streamlit\config.toml" copy /Y "%ORIGEM%.streamlit\config.toml" "%DEST%\.streamlit\"

if exist "%ORIGEM%data\orcamento.db" (
  copy /Y "%ORIGEM%data\orcamento.db" "%DEST%\data\"
  echo [OK] Seus dados foram incluidos: data\orcamento.db
) else (
  echo [--] Ainda nao ha orcamento.db - app criara na primeira vez em casa.
)

echo.
echo PRONTO! Copie esta pasta para o pendrive:
echo.
echo   %DEST%
echo.
echo NAO copie a pasta .venv - ela e enorme e nao entra no pendrive.
echo.
start "" explorer "%DEST%"
pause
