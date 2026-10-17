param([switch]$FullRendering)
$ErrorActionPreference='Stop'
$repository=Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $repository
if ($FullRendering) { & ./diagnostics/m0/run.ps1 }
else { & .venv/Scripts/python.exe -m woodwork.cli preflight }
if ($LASTEXITCODE -ne 0) { throw 'Preflight failed. See runtime diagnostics; keep Windows security settings unchanged.' }
