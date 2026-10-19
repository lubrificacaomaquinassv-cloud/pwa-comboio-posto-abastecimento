# Carga DADOS_PAINEL -> Supabase (Windows)
# Uso: clique direito -> Executar com PowerShell
#   ou: powershell -ExecutionPolicy Bypass -File scripts\CARGA_DADOS_PAINEL.ps1

$ErrorActionPreference = "Stop"

# --- Ajuste só se sua pasta não for esta ---
$PastaDados = "$env:USERPROFILE\Desktop\DADOS_PAINEL"

# Raiz do projeto = pasta que contém app.py (pai de scripts/)
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

Write-Host "=== Carga Adubacao -> Supabase ===" -ForegroundColor Cyan
Write-Host "Pasta de dados: $PastaDados"
Write-Host "Projeto: $RepoRoot"

if (-not (Test-Path $PastaDados)) {
    Write-Host "ERRO: Pasta nao encontrada: $PastaDados" -ForegroundColor Red
    Write-Host "Crie a pasta ou edite `$PastaDados no inicio deste script."
    exit 1
}

# Localizar arquivos (nao use nomes ficticios — o script procura sozinho)
$kml = Get-ChildItem -Path $PastaDados -Filter *.kml -File -ErrorAction SilentlyContinue |
    Sort-Object Length -Descending | Select-Object -First 1
if (-not $kml) {
    Write-Host "ERRO: Nenhum .kml em $PastaDados" -ForegroundColor Red
    exit 1
}

$cobertura = Get-ChildItem -Path $PastaDados -Filter *.xlsx -File |
    Where-Object { $_.Name -match 'cobertura|Cobertura|COBERTURA' } |
    Select-Object -First 1
if (-not $cobertura) {
    $cobertura = Get-ChildItem -Path $PastaDados -Filter *.xlsx -File |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
}

$base = Get-ChildItem -Path $PastaDados -Filter *.xlsx -File |
    Where-Object { $_.Name -match 'base|Base|subsol|Subsol' } |
    Select-Object -First 1

Write-Host ""
Write-Host "KML:       $($kml.FullName)"
Write-Host "Cobertura: $($cobertura.FullName)"
if ($base) { Write-Host "Base:      $($base.FullName)" } else { Write-Host "Base:      (opcional, nao encontrada)" -ForegroundColor Yellow }

if (-not $env:SUPABASE_DB_URL) {
    Write-Host ""
    Write-Host "Defina a conexao (substitua SEU_REF e SUA_SENHA):" -ForegroundColor Yellow
    Write-Host '$env:SUPABASE_DB_URL = "postgresql+psycopg://postgres.SEU_REF:SUA_SENHA@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"'
    Write-Host ""
    $url = Read-Host "Cole a SUPABASE_DB_URL agora (ou Enter para sair)"
    if ([string]::IsNullOrWhiteSpace($url)) { exit 1 }
    $env:SUPABASE_DB_URL = $url.Trim()
}

# Python
$py = $null
foreach ($candidato in @("python", "python3", "py")) {
    if (Get-Command $candidato -ErrorAction SilentlyContinue) {
        $py = $candidato
        break
    }
}
if (-not $py) {
    Write-Host "ERRO: Python nao encontrado no PATH. Instale Python 3.11+ e pip install -r requirements.txt" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Instalando dependencias (se necessario)..." -ForegroundColor DarkGray
& $py -m pip install -q -r requirements.txt

$argsSync = @(
    "scripts/sync_excel_to_supabase.py",
    "--kml", $kml.FullName,
    "--cobertura", $cobertura.FullName
)
if ($base) {
    $argsSync += @("--base", $base.FullName)
}

Write-Host "Executando sync..." -ForegroundColor Green
& $py @argsSync
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "OK. Proximo passo: Streamlit Cloud -> Secrets SUPABASE_DB_URL -> Redeploy" -ForegroundColor Green
