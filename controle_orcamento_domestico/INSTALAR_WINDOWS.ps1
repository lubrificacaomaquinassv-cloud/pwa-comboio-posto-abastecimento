# Instala o painel em C:\Users\<voce>\orcamento-casa e abre o Streamlit
$ErrorActionPreference = "Stop"
$Repo = "lubrificacaomaquinassv-cloud/pwa-comboio-posto-abastecimento"
$Branch = "main"
$Dest = Join-Path $env:USERPROFILE "orcamento-casa"

Write-Host "Baixando projeto do GitHub..." -ForegroundColor Cyan
$zip = Join-Path $env:TEMP "orcamento-casa.zip"
$url = "https://github.com/$Repo/archive/refs/heads/$Branch.zip"
Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing

$extract = Join-Path $env:TEMP "orcamento-casa-extract"
if (Test-Path $extract) { Remove-Item $extract -Recurse -Force }
Expand-Archive -Path $zip -DestinationPath $extract -Force

$inner = Get-ChildItem -Path $extract -Directory | Select-Object -First 1
$src = Join-Path $inner.FullName "controle_orcamento_domestico"
if (-not (Test-Path $src)) {
    throw "Pasta controle_orcamento_domestico nao encontrada no ZIP. Confira se o PR foi mergeado na main."
}

Write-Host "Copiando para $Dest ..." -ForegroundColor Cyan
if (Test-Path $Dest) { Remove-Item $Dest -Recurse -Force }
Copy-Item -Path $src -Destination $Dest -Recurse

Write-Host "Pronto! Iniciando painel..." -ForegroundColor Green
Set-Location $Dest
Start-Process -FilePath (Join-Path $Dest "RODAR_APP.bat") -WorkingDirectory $Dest
Write-Host "Pasta instalada: $Dest"
Write-Host "Da proxima vez, abra RODAR_APP.bat nessa pasta ou rode: cd `"$Dest`"; .\RODAR_APP.bat"
