# Adubacao Florestal SV — publica no GitHub (repo vazio adubacao-florestal-sv)
# Como usar: clique direito > Executar com PowerShell  (ou abra PowerShell aqui e: .\PUBLICAR.ps1)

$ErrorActionPreference = "Stop"
$dest = "$env:USERPROFILE\Desktop\adubacao-florestal-sv"

Write-Host ""
Write-Host "  Adubacao Florestal 2026 — Santa Virginia" -ForegroundColor Green
Write-Host "  Enviando para github.com/lubrificacaomaquinassv-cloud/adubacao-florestal-sv"
Write-Host ""

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "ERRO: Git nao instalado. Baixe em https://git-scm.com" -ForegroundColor Red
    Read-Host "Enter para sair"
    exit 1
}

if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
Write-Host "Baixando arquivos do painel..."
git clone -b adubacao-florestal-sv --single-branch `
    https://github.com/lubrificacaomaquinassv-cloud/pwa-comboio-posto-abastecimento.git $dest

Set-Location $dest
git branch -M main
git remote set-url origin https://github.com/lubrificacaomaquinassv-cloud/adubacao-florestal-sv.git

Write-Host "Enviando (vai pedir login GitHub se necessario)..."
git push -u origin main

Write-Host ""
Write-Host "PRONTO." -ForegroundColor Green
Write-Host "Repo: https://github.com/lubrificacaomaquinassv-cloud/adubacao-florestal-sv"
Write-Host ""
Write-Host "Streamlit Cloud:"
Write-Host "  Repo: adubacao-florestal-sv  |  Branch: main  |  Main file: app.py"
Write-Host ""
Read-Host "Enter para fechar"
