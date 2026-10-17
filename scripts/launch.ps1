param([string]$DataRoot)
$ErrorActionPreference='Stop'
$repository=Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $repository
if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) { throw 'Run ./scripts/setup.ps1 first.' }
if (-not (Test-Path -LiteralPath 'apps/web/dist/index.html')) { throw 'Run npm run build in apps/web first.' }
if ($DataRoot) { $env:WOODWORK_DATA_ROOT=[IO.Path]::GetFullPath($DataRoot) }
Write-Output 'Open http://127.0.0.1:8777 . Stop with Ctrl+C; saved projects remain in local app data.'
& .venv/Scripts/python.exe -m uvicorn woodwork.api:create_app --factory --host 127.0.0.1 --port 8777 --no-access-log
if ($LASTEXITCODE -ne 0) { throw 'Local service stopped with an error. Inspect the diagnostic above; do not reset the project store.' }
