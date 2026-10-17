param([string]$BrowserUrl='http://127.0.0.1:8777')
$ErrorActionPreference='Stop'
$repository=Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $repository
try { $health=Invoke-RestMethod -Uri ($BrowserUrl+'/api/v1/health') } catch { throw 'Start ./scripts/launch.ps1 first. The demonstration needs the local service.' }
if ($health.status -ne 'ready') { throw 'The local service did not report readiness.' }
$previousUrl=$env:WOODWORK_TEST_URL
$env:WOODWORK_TEST_URL=$BrowserUrl
Push-Location -LiteralPath 'apps/web'
try {
    & npm.cmd test -- tests/m0.spec.ts tests/m2.spec.ts tests/m3-m6.spec.ts
    if ($LASTEXITCODE -ne 0) { throw 'The release demonstration failed; inspect the precise case and retained Playwright evidence.' }
} finally { Pop-Location; $env:WOODWORK_TEST_URL=$previousUrl }
Write-Output 'The selected real-CAD browser demonstration passed. Physical construction and optional live AI remain separate gates.'
