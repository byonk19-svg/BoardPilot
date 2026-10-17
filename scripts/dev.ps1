param([ValidateSet('api','web')][string]$Service='api',[string]$DataRoot)
$ErrorActionPreference='Stop'
$repository=Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $repository
if ($DataRoot) { $env:WOODWORK_DATA_ROOT=[IO.Path]::GetFullPath($DataRoot) }
if ($Service -eq 'api') { & .venv/Scripts/python.exe -m uvicorn woodwork.api:create_app --factory --host 127.0.0.1 --port 8777 --no-access-log }
else { Set-Location -LiteralPath 'apps/web'; & npm.cmd run dev -- --host 127.0.0.1 --port 5173 }
if ($LASTEXITCODE -ne 0) { throw 'Development service stopped with an error.' }
