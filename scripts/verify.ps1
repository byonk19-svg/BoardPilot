param([switch]$Browser)
$ErrorActionPreference='Stop'
$repository=Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $repository
& .venv/Scripts/python.exe -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Backend verification failed.' }
Push-Location -LiteralPath 'apps/web'
try {
    & npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw 'Frontend type/build verification failed.' }
    if ($Browser) {
        & npm.cmd test
        if ($LASTEXITCODE -ne 0) { throw 'Browser verification failed. Start API and Vite with the documented commands.' }
    }
} finally { Pop-Location }
Write-Output 'Requested checks passed. Native opt-in fixture corpora and physical review are separate evidence gates.'
