# Painel Adubacao - atualizar Git e opcionalmente abrir local
$ErrorActionPreference = "Stop"
$BranchPainel = "cursor/adubacao-supabase-mapa-fbe9"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
Set-Location $RepoRoot

Write-Host ""
Write-Host "=== Painel Adubacao ===" -ForegroundColor Cyan
Write-Host "Pasta: $RepoRoot"
Write-Host "Branch: $BranchPainel"
Write-Host ""

git fetch origin $BranchPainel
git checkout $BranchPainel
git pull origin $BranchPainel

Write-Host ""
Write-Host "Versao esperada na barra lateral: 2026.10.20-mapa-ficha-v3" -ForegroundColor Yellow
Write-Host "Site na nuvem: https://adubacao-florestal-sv-hbqqrye72rwfhhcjprayxy.streamlit.app/"
Write-Host ""
Write-Host "Ver talhao: barra lateral esquerda, depois aba Mapa, Ficha do talhao embaixo."
Write-Host ""
Write-Host "Mais facil: duplo clique em ATUALIZAR_E_ABRIR_PAINEL.bat na mesma pasta deste script."
Write-Host ""

$rodarLocal = Read-Host "Rodar painel neste PC agora? Digite S ou N"
if ($rodarLocal -eq "S" -or $rodarLocal -eq "s") {
    Set-Location $ScriptDir
    $py = $null
    foreach ($c in @("py", "python", "python3")) {
        if (Get-Command $c -ErrorAction SilentlyContinue) { $py = $c; break }
    }
    if (-not $py) {
        Write-Host "ERRO: instale Python 3.11+" -ForegroundColor Red
        exit 1
    }
    & $py -m pip install -q -r requirements.txt
    Write-Host "Abrindo localhost:8501" -ForegroundColor Green
    & $py -m streamlit run app.py
}
