$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$py = $null
foreach ($c in @("py", "python", "python3")) {
    if (Get-Command $c -ErrorAction SilentlyContinue) { $py = $c; break }
}
if (-not $py) {
    Write-Host "Instale Python 3.11+" -ForegroundColor Red
    exit 1
}

& $py -m pip install -q sqlalchemy "psycopg[binary]>=3.2"

& $py scripts/testar_conexao_supabase.py
exit $LASTEXITCODE
