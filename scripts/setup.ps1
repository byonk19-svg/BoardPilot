param([switch]$Offline)
$ErrorActionPreference='Stop'
$repository=Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $repository
if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw 'Install Node 24.13.0, then rerun setup.' }
if ((& node --version) -ne 'v24.13.0') { throw 'This pinned release requires Node 24.13.0.' }
$uvExecutable=Get-Command uv -ErrorAction SilentlyContinue
function Invoke-ProjectUv([string[]]$Arguments) {
    if ($uvExecutable) { & $uvExecutable.Source @Arguments }
    else { & py -m uv @Arguments }
    if ($LASTEXITCODE -ne 0) { throw 'uv failed. Install uv 0.9.8 (py -m pip install --user uv==0.9.8) and inspect the preceding diagnostic.' }
}
Invoke-ProjectUv @('--version')
if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) {
    if (-not $Offline) { Invoke-ProjectUv @('python','install','3.13.9') }
    Invoke-ProjectUv @('venv','--python','3.13.9','.venv')
}
$syncArguments=@('pip','sync','requirements-runtime.lock','--python','.venv/Scripts/python.exe')
if ($Offline) { $syncArguments+='--offline' }
Invoke-ProjectUv $syncArguments
$installArguments=@('pip','install','--no-deps','--python','.venv/Scripts/python.exe','-e','.')
if ($Offline) { $installArguments+='--offline' }
Invoke-ProjectUv $installArguments
if ($Offline) {
    & .venv/Scripts/python.exe -c "from pathlib import Path; from playwright.sync_api import sync_playwright; p=sync_playwright().start(); assert Path(p.chromium.executable_path).is_file(), 'Prepared Chromium missing'; p.stop()"
} else { & .venv/Scripts/python.exe -m playwright install chromium }
if ($LASTEXITCODE -ne 0) { throw 'Chromium setup failed. Native snapshots/drawings require the locked browser.' }
Push-Location -LiteralPath 'apps/web'
try {
    if ($Offline) { & npm.cmd ci --offline } else { & npm.cmd ci }
    if ($LASTEXITCODE -ne 0) { throw 'Frontend locked dependency install failed.' }
    & npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
} finally { Pop-Location }
& .venv/Scripts/python.exe -c "from woodwork.runtime import runtime_versions; import json; r=runtime_versions(); print(json.dumps(r,indent=2)); assert not r['missing_components']"
if ($LASTEXITCODE -ne 0) { throw 'Runtime version verification failed.' }
Write-Output 'Setup complete. Run ./scripts/preflight.ps1, then ./scripts/launch.ps1.'
