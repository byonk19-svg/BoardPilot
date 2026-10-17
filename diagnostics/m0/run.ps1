param([string]$OutputRoot)
$ErrorActionPreference = 'Stop'
$repository = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$interpreter = Join-Path $repository '.venv/Scripts/python.exe'
$cadgenCommand = Join-Path $repository '.venv/Scripts/cadgen.exe'
if (-not (Test-Path -LiteralPath $interpreter)) { throw 'Install the locked Python 3.13 runtime first; see docs/IMPLEMENTATION-STATUS.md.' }
if (-not $OutputRoot) {
    $OutputRoot = Join-Path $env:LOCALAPPDATA ('WoodworkingPlanner/probes/' + [guid]::NewGuid().ToString('N'))
}
if (Test-Path -LiteralPath $OutputRoot) { throw 'Use a new empty probe directory.' }
New-Item -ItemType Directory -Path $OutputRoot | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'part.py'),(Join-Path $PSScriptRoot 'part.json'),(Join-Path $PSScriptRoot 'asymmetric.py'),(Join-Path $PSScriptRoot 'two_instances.py'),(Join-Path $PSScriptRoot 'part_drawing.py') -Destination $OutputRoot
$env:CADGEN_DAEMON = '0'
$env:CADGEN_JOBS = '1'
$env:CADGEN_TELEMETRY = '0'
$env:CADGEN_UPDATE_CHECK = '0'
$env:CADGEN_CACHE_DIR = Join-Path $OutputRoot 'cache'
$env:CADGEN_STATE_DIR = Join-Path $OutputRoot 'state'
$env:MPLCONFIGDIR = Join-Path $OutputRoot 'matplotlib'
$env:CADGEN_NODE = (Get-Command node).Source
$timings = @()
foreach ($entry in @('part.py','asymmetric.py','two_instances.py','part_drawing.py')) {
    $timer = [Diagnostics.Stopwatch]::StartNew()
    & $interpreter -u (Join-Path $OutputRoot $entry)
    if ($LASTEXITCODE -ne 0) { throw "Probe failed: $entry" }
    $timer.Stop()
    $timings += [pscustomobject]@{ entry = $entry; seconds = $timer.Elapsed.TotalSeconds }
}
& $cadgenCommand step snapshot (Join-Path $OutputRoot 'out/part.step') (Join-Path $OutputRoot 'out/part.png')
if ($LASTEXITCODE -ne 0) { throw 'Snapshot failed' }
pdftoppm -png -r 120 (Join-Path $OutputRoot 'out/part-metric.pdf') (Join-Path $OutputRoot 'out/part-metric')
if ($LASTEXITCODE -ne 0) { throw 'PDF rendering failed; install Poppler or use the bundled runtime.' }
& $interpreter -u (Join-Path $PSScriptRoot 'verify.py') $OutputRoot
if ($LASTEXITCODE -ne 0) { throw 'Saved-artifact verification failed' }
$timer = [Diagnostics.Stopwatch]::StartNew()
& $interpreter -u (Join-Path $OutputRoot 'part.py')
if ($LASTEXITCODE -ne 0) { throw 'Warm rerun failed' }
$timer.Stop()
$timings += [pscustomobject]@{ entry = 'part.py warm no-op'; seconds = $timer.Elapsed.TotalSeconds }
$timings | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $OutputRoot 'timings.json')
Write-Output "Probe output: $OutputRoot"
Write-Output 'These verify the native spike. Run the browser selection check and canonical fixture corpus separately.'
