# Duplo clique ou: powershell -ExecutionPolicy Bypass -File scripts\CONFERIR_PLANILHAS.ps1
$ErrorActionPreference = "Stop"
$PastaDados = "C:\Users\hmauricio\Desktop\DADOS_PAINEL"
if (-not (Test-Path $PastaDados)) {
    $PastaDados = Join-Path $env:USERPROFILE "Desktop\DADOS_PAINEL"
}
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$py = $null
foreach ($c in @("py", "python", "python3")) {
    if (Get-Command $c -ErrorAction SilentlyContinue) { $py = $c; break }
}
if (-not $py) {
    Write-Host "Instale Python 3.11+ e rode: pip install -r requirements.txt" -ForegroundColor Red
    exit 1
}
& $py -m pip install -q -r requirements.txt
& $py scripts/conferir_planilhas_local.py $PastaDados
