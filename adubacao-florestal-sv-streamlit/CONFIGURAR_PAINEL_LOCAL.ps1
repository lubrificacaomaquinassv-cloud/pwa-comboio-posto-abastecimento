# Grava a conexao Supabase para o painel local (uma vez)
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SecretsDir = Join-Path $ScriptDir ".streamlit"
$SecretsFile = Join-Path $SecretsDir "secrets.toml"

New-Item -ItemType Directory -Force -Path $SecretsDir | Out-Null

Write-Host ""
Write-Host "=== Configurar painel local (Supabase) ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Cole a SUPABASE_DB_URL do Supabase:"
Write-Host "  Project Settings - Database - Transaction pooler - URI"
Write-Host "  Troque postgresql:// por postgresql+psycopg://"
Write-Host ""

$url = Read-Host "SUPABASE_DB_URL"
if ([string]::IsNullOrWhiteSpace($url)) {
    Write-Host "Cancelado." -ForegroundColor Red
    exit 1
}
$url = $url.Trim().Replace('"', '')

$lines = @(
    'SUPABASE_DB_URL = "' + $url + '"'
    'SUPABASE_GIS_TABLE = "dim_talhoes"'
)
Set-Content -Path $SecretsFile -Value $lines -Encoding UTF8

Write-Host ""
Write-Host "Salvo em:" -ForegroundColor Green
Write-Host "  $SecretsFile"
Write-Host ""
Write-Host "Agora duplo clique em RODAR_PAINEL_LOCAL.bat" -ForegroundColor Yellow
