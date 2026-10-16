# Backup automatico do SQLite (sem copiar .venv)
$AppDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Db = Join-Path $AppDir "data\orcamento.db"
if (-not (Test-Path $Db)) { exit 0 }

$stamp = Get-Date -Format "yyyyMMdd_HHmm"
$destinos = @()

$localBackup = Join-Path $AppDir "backups"
$destinos += $localBackup

if (Test-Path "D:\") {
    $destinos += "D:\Orcamento-Backup"
}

Get-CimInstance -ClassName Win32_LogicalDisk -ErrorAction SilentlyContinue |
    Where-Object { $_.DriveType -eq 2 -and $_.Size -gt 0 } |
    ForEach-Object {
        $letra = $_.DeviceID
        $destinos += Join-Path $letra "Orcamento-Backup"
    }

$destinos = $destinos | Select-Object -Unique

foreach ($dest in $destinos) {
    try {
        New-Item -ItemType Directory -Force -Path $dest | Out-Null
        Copy-Item -Path $Db -Destination (Join-Path $dest "orcamento.db") -Force
        Copy-Item -Path $Db -Destination (Join-Path $dest "orcamento_$stamp.db") -Force
        Write-Host "[OK] Backup em $dest"
    } catch {
        Write-Host "[--] Nao foi possivel gravar em $dest"
    }
}
