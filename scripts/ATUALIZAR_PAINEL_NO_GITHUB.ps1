# Atualiza o repo adubacao-florestal-sv (main) com o painel novo.
# O Streamlit Cloud JA aponta para esse repo — nao precisa mudar Settings.
#
# Uso: PowerShell
#   powershell -ExecutionPolicy Bypass -File scripts\ATUALIZAR_PAINEL_NO_GITHUB.ps1

$ErrorActionPreference = "Stop"
$Temp = Join-Path $env:TEMP "sv-adubacao-deploy"
$RepoOficial = Join-Path $Temp "adubacao-florestal-sv"
$RepoFonte = Join-Path $Temp "pwa-fonte"

Write-Host "=== Atualizar painel no GitHub (repo adubacao-florestal-sv) ===" -ForegroundColor Cyan

New-Item -ItemType Directory -Force -Path $Temp | Out-Null

if (-not (Test-Path $RepoFonte)) {
    Write-Host "Baixando codigo novo (branch adubacao-florestal-sv do PWA)..."
    git clone -b adubacao-florestal-sv --single-branch `
        https://github.com/lubrificacaomaquinassv-cloud/pwa-comboio-posto-abastecimento.git `
        $RepoFonte
}

if (-not (Test-Path $RepoOficial)) {
    Write-Host "Baixando repo que o Streamlit usa (adubacao-florestal-sv)..."
    git clone https://github.com/lubrificacaomaquinassv-cloud/adubacao-florestal-sv.git $RepoOficial
}

Set-Location $RepoOficial
git checkout main
git pull origin main

Write-Host "Copiando arquivos do painel..."
Get-ChildItem -Force $RepoOficial | Where-Object { $_.Name -ne '.git' } | Remove-Item -Recurse -Force
Get-ChildItem -Force $RepoFonte | Where-Object { $_.Name -ne '.git' } | ForEach-Object {
    Copy-Item -Path $_.FullName -Destination $RepoOficial -Recurse -Force
}

git add -A
$status = git status --porcelain
if (-not $status) {
    Write-Host "Nada a enviar — ja esta atualizado." -ForegroundColor Yellow
    exit 0
}

git commit -m "Atualiza painel: Supabase, GIS dim_talhoes, mapa Esri"
Write-Host "Enviando para GitHub (precisa estar logado no git)..." -ForegroundColor Green
git push origin main

Write-Host ""
Write-Host "PRONTO. Abra o Streamlit -> menu ... -> Reboot app" -ForegroundColor Green
Write-Host "URL: https://adubacao-florestal-sv-hbqqrye72rwfhhcjprayxy.streamlit.app/" -ForegroundColor Green
