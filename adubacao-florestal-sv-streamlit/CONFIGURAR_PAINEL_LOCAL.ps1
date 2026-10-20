# Grava a conexao Supabase para o painel local (uma vez)
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SecretsDir = Join-Path $ScriptDir ".streamlit"
$SecretsFile = Join-Path $SecretsDir "secrets.toml"

New-Item -ItemType Directory -Force -Path $SecretsDir | Out-Null

Write-Host ""
Write-Host "=== Configurar painel local (Supabase) ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "NAO cole https://....supabase.co" -ForegroundColor Red
Write-Host ""
Write-Host "Cole a URI do POOLER (Postgres):" -ForegroundColor Yellow
Write-Host "  Supabase -> Project Settings -> Database -> Transaction pooler -> URI"
Write-Host "  Troque postgresql:// por postgresql+psycopg://"
Write-Host "  Exemplo: postgresql+psycopg://postgres.ABC123:senha@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"
Write-Host ""

$url = Read-Host "SUPABASE_DB_URL"
if ([string]::IsNullOrWhiteSpace($url)) {
    Write-Host "Cancelado." -ForegroundColor Red
    exit 1
}
$url = $url.Trim().Replace('"', '')

if ($url -match "^https?://") {
    Write-Host ""
    Write-Host "ERRO: Isso e URL do site (API), nao e conexao do banco." -ForegroundColor Red
    Write-Host "Use a URI postgresql+psycopg://... do Transaction pooler." -ForegroundColor Yellow
    exit 1
}
if ($url -notmatch "^postgresql") {
    Write-Host ""
    Write-Host "ERRO: A URL deve comecar com postgresql:// ou postgresql+psycopg://" -ForegroundColor Red
    exit 1
}
if ($url -match "^postgresql://") {
    $url = $url.Replace("postgresql://", "postgresql+psycopg://")
    Write-Host "Ajustado para postgresql+psycopg://" -ForegroundColor Green
}
if ($url -notmatch "postgres\.[a-zA-Z0-9]+@") {
    Write-Host ""
    Write-Host "AVISO: o usuario deve ser postgres.SEU_REF (ex: postgres.azhpxhrwhegfysoeqmft)" -ForegroundColor Yellow
    Write-Host "Copie a Connection string inteira do Supabase e so troque a senha." -ForegroundColor Yellow
}

$lines = @(
    'SUPABASE_DB_URL = "' + $url + '"'
    'SUPABASE_GIS_TABLE = "dim_talhoes"'
)
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($SecretsFile, ($lines -join [Environment]::NewLine), $utf8NoBom)

Write-Host ""
Write-Host "Salvo em:" -ForegroundColor Green
Write-Host "  $SecretsFile"
Write-Host ""
Write-Host "Pasta deste script:" -ForegroundColor Cyan
Write-Host "  $ScriptDir"
Write-Host ""
Write-Host "Feche a janela do painel antigo no navegador." -ForegroundColor Yellow
Write-Host "Duplo clique em:" -ForegroundColor Yellow
Write-Host "  PARAR_E_ABRIR_PAINEL.bat   (recomendado - reinicia tudo)"
Write-Host "  ou ABRIR_PAINEL_ADUBACAO.bat"
