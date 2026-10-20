# Carga DADOS_PAINEL -> Supabase (Windows)
# cd $env:USERPROFILE\Desktop\pwa-comboio-posto-abastecimento
# git fetch origin
# git checkout cursor/finalizar-adubacao-dados-fbe9
# powershell -ExecutionPolicy Bypass -File adubacao-florestal-sv-streamlit\RODAR_CARGA_WINDOWS.ps1

$ErrorActionPreference = "Stop"

$PastaDados = "C:\Users\hmauricio\Desktop\DADOS_PAINEL"
if (-not (Test-Path $PastaDados)) {
    $PastaDados = Join-Path $env:USERPROFILE "Desktop\DADOS_PAINEL"
}

$StreamlitRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $StreamlitRoot

Write-Host "=== Painel Adubacao - carga Supabase ===" -ForegroundColor Cyan
Write-Host "Pasta do projeto: $StreamlitRoot"
Write-Host "DADOS_PAINEL:     $PastaDados"
Write-Host ""

if (-not (Test-Path (Join-Path $StreamlitRoot "app.py"))) {
    Write-Host "ERRO: app.py nao encontrado." -ForegroundColor Red
    Write-Host "Use: git checkout cursor/finalizar-adubacao-dados-fbe9" -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path $PastaDados)) {
    Write-Host "ERRO: Pasta nao encontrada: $PastaDados" -ForegroundColor Red
    exit 1
}

$py = $null
foreach ($c in @("py", "python", "python3")) {
    if (Get-Command $c -ErrorAction SilentlyContinue) { $py = $c; break }
}
if (-not $py) {
    Write-Host "Instale Python 3.11+ e adicione ao PATH." -ForegroundColor Red
    exit 1
}

& $py -m pip install -q -r requirements.txt

if (-not $env:SUPABASE_DB_URL) {
    Write-Host "Cole a SUPABASE_DB_URL (postgresql+psycopg://...):" -ForegroundColor Yellow
    $url = Read-Host
    if ([string]::IsNullOrWhiteSpace($url)) { exit 1 }
    $env:SUPABASE_DB_URL = $url.Trim()
}

Write-Host "Passo 1 - Conferir planilhas..." -ForegroundColor Cyan
& $py scripts/conferir_planilhas_local.py $PastaDados
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Passo 2 - Subir para Supabase..." -ForegroundColor Green
& $py scripts/analisar_e_sync_adubacao.py --dados-dir $PastaDados --sync --modo por_talhao
exit $LASTEXITCODE
