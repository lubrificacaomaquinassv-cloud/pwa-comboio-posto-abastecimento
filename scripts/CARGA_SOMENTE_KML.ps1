# Mapa no painel: grava poligonos do KML no Supabase (1x). Depois rode sql/005 no Supabase.
# Uso: botao direito -> Executar com PowerShell

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$kmlPath = $args[0]
if (-not $kmlPath) {
    $Pasta = "$env:USERPROFILE\Desktop\DADOS_PAINEL"
    $kml = Get-ChildItem -Path $Pasta -Filter *.kml -File -ErrorAction SilentlyContinue |
        Sort-Object Length -Descending | Select-Object -First 1
    if ($kml) { $kmlPath = $kml.FullName }
}
if (-not $kmlPath -or -not (Test-Path $kmlPath)) {
    Write-Host "ERRO: Informe o KML:" -ForegroundColor Red
    Write-Host '  .\scripts\CARGA_SOMENTE_KML.ps1 "D:\caminho\fazenda_santa_virginia_completo.kml"'
    exit 1
}

if (-not $env:SUPABASE_DB_URL) {
    Write-Host "Cole a SUPABASE_DB_URL (Settings -> Database -> Connection string URI, pooler 6543):" -ForegroundColor Yellow
    $url = Read-Host "SUPABASE_DB_URL"
    if ([string]::IsNullOrWhiteSpace($url)) { exit 1 }
    $env:SUPABASE_DB_URL = $url.Trim()
}

$py = @("python", "py", "python3") | Where-Object { Get-Command $_ -ErrorAction SilentlyContinue } | Select-Object -First 1
if (-not $py) { Write-Host "Instale Python 3." -ForegroundColor Red; exit 1 }

& $py -m pip install -q -r requirements.txt
& $py scripts/carga_somente_kml.py --kml $kmlPath
exit $LASTEXITCODE
