# Publica o painel no Streamlit Cloud SEM mexer no site share.streamlit.io
# O app na nuvem usa a branch: cursor/adubacao-supabase-mapa-fbe9
# Quando este script faz push, o Streamlit redeploy sozinho em ~2 a 5 minutos.

$ErrorActionPreference = "Stop"
$BranchPainel = "cursor/adubacao-supabase-mapa-fbe9"

$RepoRoot = Split-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) -Parent
if (-not (Test-Path (Join-Path $RepoRoot ".git"))) {
    $RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
}
Set-Location $RepoRoot

Write-Host ""
Write-Host "=== Publicar painel Adubacao (automatico) ===" -ForegroundColor Cyan
Write-Host "Pasta: $RepoRoot"
Write-Host "Branch que o Streamlit Cloud usa: $BranchPainel"
Write-Host ""

git fetch origin $BranchPainel 2>&1 | Out-Host
git checkout $BranchPainel 2>&1 | Out-Host
git pull origin $BranchPainel 2>&1 | Out-Host

$local = (git rev-parse HEAD).Trim()
$remote = (git rev-parse "origin/$BranchPainel").Trim()

if ($local -ne $remote) {
    Write-Host "Seu PC esta atrasado. Rode git pull de novo ou peça ajuda — nao vou dar push da sua maquina." -ForegroundColor Yellow
} else {
    Write-Host "Codigo local = GitHub ($BranchPainel). OK." -ForegroundColor Green
}

Write-Host ""
Write-Host "Versao esperada no painel (barra lateral esquerda):" -ForegroundColor Yellow
Write-Host "  Versao do painel: 2026.10.20-mapa-ficha-v3"
Write-Host ""
Write-Host "Abra o painel (aguarde 2-5 min se acabou de atualizar o GitHub):" -ForegroundColor Cyan
Write-Host "  https://adubacao-florestal-sv-hbqqrye72rwfhhcjprayxy.streamlit.app/"
Write-Host "  ou o URL .streamlit.app do seu app pwa-comboio-posto-abastecimento"
Write-Host ""
Write-Host "Como usar a ficha do talhao:" -ForegroundColor Green
Write-Host "  1) Barra lateral ESQUERDA -> Ver talhao -> escolha o numero (ex: 304B)"
Write-Host "  2) Aba Mapa -> role para baixo -> Ficha do talhao"
Write-Host ""

$rodarLocal = Read-Host "Rodar o painel AGORA neste PC? (S/N)"
if ($rodarLocal -match "^[Ss]") {
    Set-Location (Join-Path $RepoRoot "adubacao-florestal-sv-streamlit")
    if (-not (Test-Path "app.py")) {
        Write-Host "ERRO: app.py nao encontrado." -ForegroundColor Red
        exit 1
    }
    $py = $null
    foreach ($c in @("py", "python", "python3")) {
        if (Get-Command $c -ErrorAction SilentlyContinue) { $py = $c; break }
    }
    if (-not $py) {
        Write-Host "Instale Python 3.11+" -ForegroundColor Red
        exit 1
    }
    & $py -m pip install -q -r requirements.txt
    Write-Host "Abrindo http://localhost:8501 ..." -ForegroundColor Green
    & $py -m streamlit run app.py
}
