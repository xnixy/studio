# Dump Postgres using DATABASE_URL from env or backend/.env
# Requires pg_dump on PATH (PostgreSQL client tools).
# Usage: .\scripts\backup_postgres.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$OutDir = Join-Path $Root "backups"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$dbUrl = $env:DATABASE_URL
if (-not $dbUrl -and (Test-Path (Join-Path $Root ".env"))) {
  Get-Content (Join-Path $Root ".env") | ForEach-Object {
    if ($_ -match '^\s*DATABASE_URL=(.+)$') {
      $dbUrl = $Matches[1].Trim().Trim('"').Trim("'")
    }
  }
}
if (-not $dbUrl) { throw "DATABASE_URL is required" }

$dumpUrl = $dbUrl -replace '^postgresql\+asyncpg://', 'postgresql://' -replace '^postgres://', 'postgresql://'
$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMdd-HHmmss")
$out = Join-Path $OutDir "studio-$stamp.sql"

Write-Host "Writing $out"
& pg_dump --no-owner --no-acl $dumpUrl -f $out
if ($LASTEXITCODE -ne 0) { throw "pg_dump failed" }

# Compress if gzip available
$gz = "$out.gz"
if (Get-Command gzip -ErrorAction SilentlyContinue) {
  gzip -f $out
  Write-Host "Compressed $gz"
} else {
  Write-Host "Done $out (install gzip for .gz)"
}
