@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Instalar Painel Adubacao Florestal 2026
color 0A

echo.
echo  ============================================================
echo   INSTALADOR - PAINEL ADUBACAO FLORESTAL 2026
echo   Santa Virginia
echo  ============================================================
echo.
echo  Pasta destino:
echo  %CD%\ADUBACAO_FLORESTAL_2026
echo.

set DEST=%~dp0ADUBACAO_FLORESTAL_2026
set ZIP=%TEMP%\sv-painel-adubacao.zip
set EXTRACT=%TEMP%\sv-painel-adubacao

if not exist "%DEST%" mkdir "%DEST%"

echo  [1/3] Baixando arquivos do GitHub...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "try { ^
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; ^
    Invoke-WebRequest -Uri 'https://github.com/lubrificacaomaquinassv-cloud/pwa-comboio-posto-abastecimento/archive/refs/heads/main.zip' -OutFile '%ZIP%' -UseBasicParsing; ^
    Write-Host 'OK download' ^
  } catch { Write-Host 'ERRO:' $_.Exception.Message; exit 1 }"

if errorlevel 1 goto :erro

echo  [2/3] Extraindo arquivos...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Expand-Archive -Path '%ZIP%' -DestinationPath '%EXTRACT%' -Force; ^
   Copy-Item -Path '%EXTRACT%\pwa-comboio-posto-abastecimento-main\ADUBACAO_FLORESTAL_2026\*' -Destination '%DEST%' -Recurse -Force"

if not exist "%DEST%\app.py" goto :erro
if not exist "%DEST%\ui.py" goto :erro

echo  [3/3] Instalacao OK. Abrindo painel...
echo.
cd /d "%DEST%"
call RODAR_PAINEL.bat
goto :fim

:erro
echo.
echo  ERRO na instalacao.
echo  Verifique internet e tente de novo.
echo  Ou baixe manualmente:
echo  https://github.com/lubrificacaomaquinassv-cloud/pwa-comboio-posto-abastecimento/tree/main/ADUBACAO_FLORESTAL_2026
pause
exit /b 1

:fim
