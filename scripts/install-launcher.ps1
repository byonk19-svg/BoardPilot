param(
    [Parameter(Mandatory=$true)][string]$DataRoot,
    [string]$ShortcutPath = (Join-Path ([Environment]::GetFolderPath('Desktop')) 'Woodworking Planner.lnk')
)
$ErrorActionPreference = 'Stop'
$repository = [IO.Path]::GetFullPath((Split-Path $PSScriptRoot -Parent))
$dataDirectory = [IO.Path]::GetFullPath($DataRoot)
$shortcutFile = [IO.Path]::GetFullPath($ShortcutPath)
$pythonWindowed = Join-Path $repository '.venv/Scripts/pythonw.exe'
$configFile = Join-Path $dataDirectory 'desktop-launcher.json'
if (-not [IO.Path]::IsPathRooted($DataRoot) -or $dataDirectory.StartsWith('\\')) {
    throw 'Choose the absolute local data directory already used by the app.'
}
if ($dataDirectory -eq $repository -or $dataDirectory.StartsWith($repository + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Keep saved projects outside the source checkout.'
}
if (-not (Test-Path -LiteralPath $pythonWindowed -PathType Leaf)) { throw 'The prepared Python windowed runtime is missing. Run the documented setup first.' }
if (-not (Test-Path -LiteralPath (Join-Path $repository 'apps/web/dist/index.html') -PathType Leaf)) { throw 'Build the local app before installing its shortcut.' }
if ([IO.Path]::GetExtension($shortcutFile) -ne '.lnk') { throw 'The shortcut filename must end in .lnk.' }
$arguments = '-m woodwork.launcher --config "' + $configFile + '"'
$shell = New-Object -ComObject WScript.Shell
if (Test-Path -LiteralPath $shortcutFile) {
    $existing = $shell.CreateShortcut($shortcutFile)
    if ($existing.TargetPath -ne $pythonWindowed -or $existing.Arguments -ne $arguments) {
        throw "A different shortcut already exists at $shortcutFile. It was preserved. Choose another filename."
    }
}
if (Test-Path -LiteralPath $configFile) {
    $existingConfig = Get-Content -LiteralPath $configFile -Raw | ConvertFrom-Json
    if ($existingConfig.repository -ne $repository -or $existingConfig.data_root -ne $dataDirectory -or $existingConfig.port -ne 8777) {
        throw "Different launcher settings already exist at $configFile. They were preserved."
    }
}
New-Item -ItemType Directory -Path $dataDirectory -Force | Out-Null
@{repository=$repository; data_root=$dataDirectory; port=8777} | ConvertTo-Json | Set-Content -LiteralPath $configFile -Encoding utf8
$shortcut = $shell.CreateShortcut($shortcutFile)
$shortcut.TargetPath = $pythonWindowed
$shortcut.Arguments = $arguments
$shortcut.WorkingDirectory = $repository
$shortcut.Description = 'Open the local, offline Woodworking Planner and your saved projects.'
$shortcut.IconLocation = (Join-Path $env:SystemRoot 'System32/shell32.dll') + ',2'
$shortcut.Save()
Write-Output "Ready: double-click $shortcutFile"
Write-Output "Saved project directory: $dataDirectory"
