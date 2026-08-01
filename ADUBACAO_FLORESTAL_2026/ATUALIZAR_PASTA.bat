@echo off
cd /d "%~dp0"
title Atualizar Painel Adubacao
color 0E
echo.
echo  ATUALIZANDO ARQUIVOS DO PAINEL...
echo  Pasta: %CD%
echo.

set BASE=https://raw.githubusercontent.com/lubrificacaomaquinassv-cloud/pwa-comboio-posto-abastecimento/main/ADUBACAO_FLORESTAL_2026

if not exist data\sample mkdir data\sample
if not exist scripts mkdir scripts

powershell -NoProfile -Command ^
  "$files = @{ 'ui.py'='ui.py'; 'app.py'='app.py'; 'config.py'='config.py'; 'etl.py'='etl.py'; 'npk.py'='npk.py'; 'requirements.txt'='requirements.txt'; 'RODAR_PAINEL.bat'='RODAR_PAINEL.bat'; 'LEIA-ME.txt'='LEIA-ME.txt'; 'scripts/gerar_dados_amostra.py'='scripts/gerar_dados_amostra.py'; 'data/sample/cobertura_amostra.xlsx'='data/sample/cobertura_amostra.xlsx'; 'data/sample/base_amostra.xlsx'='data/sample/base_amostra.xlsx'; 'data/sample/talhoes_amostra.geojson'='data/sample/talhoes_amostra.geojson' }; ^
   foreach ($dest in $files.Keys) { $url = '%BASE/' + $files[$dest]; Write-Host ('Baixando ' + $dest + '...'); Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing }"

if exist ui.py (
  echo.
  echo  OK - Pasta completa. Agora rode RODAR_PAINEL.bat
) else (
  echo.
  echo  ERRO - Sem internet ou GitHub bloqueado. Baixe manualmente:
  echo  https://github.com/lubrificacaomaquinassv-cloud/pwa-comboio-posto-abastecimento/tree/main/ADUBACAO_FLORESTAL_2026
)
echo.
pause
