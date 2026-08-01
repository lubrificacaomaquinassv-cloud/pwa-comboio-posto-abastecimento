@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Baixar e Abrir Painel
color 0A
echo.
echo  Se esta pasta esta vazia, baixando tudo do GitHub...
echo.

set ZIP=%TEMP%\sv-adubacao.zip
set EXTRACT=%TEMP%\sv-adubacao

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; ^
   Invoke-WebRequest -Uri 'https://github.com/lubrificacaomaquinassv-cloud/pwa-comboio-posto-abastecimento/archive/refs/heads/main.zip' -OutFile '%ZIP%' -UseBasicParsing; ^
   Expand-Archive -Path '%ZIP%' -DestinationPath '%EXTRACT%' -Force; ^
   Copy-Item -Path '%EXTRACT%\pwa-comboio-posto-abastecimento-main\ADUBACAO_FLORESTAL_2026\*' -Destination '%CD%' -Recurse -Force"

if not exist app.py (
  echo ERRO - nao conseguiu baixar. Use a pasta pai e rode INSTALAR PAINEL ADUBACAO.bat
  pause
  exit /b 1
)

echo OK - arquivos instalados.
call RODAR_PAINEL.bat
