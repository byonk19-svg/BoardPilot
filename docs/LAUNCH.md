# Native Windows launch

## Open without a terminal

Double-click **Woodworking Planner** on the desktop. The installed shortcut
starts the service in the background, waits for it to become ready, and opens
**http://127.0.0.1:8777/** in your default browser. It uses only the prepared
runtime and built app; launching never downloads or installs anything.

Choose **Sample bookcase walkthrough** under **Saved projects** if it is not
already selected. This browser will remember your last opened project. Your
sample remains revision 3, 36 × 36 × 12 inches, with its Build guide PDF.

Closing the browser leaves the local service running. Double-click the shortcut
again to reopen it. After a Windows restart the shortcut starts the service
again; there is no automatic login task or system service. If an existing tab
has a connection error, reopen the shortcut, then reload the tab (or use
**Reconnect local service** when that button is shown). Saved designs and
recoverable drafts stay in the same data directory.

The installed entry is `%USERPROFILE%/OneDrive/Desktop/Woodworking Planner.lnk`
on this machine. Its target is this checkout's `.venv/Scripts/pythonw.exe`, so
no terminal window is needed. Settings are in
`<the authoritative data directory>/desktop-launcher.json`; startup logs are
beside it under `logs/`, and a launcher failure is recorded in
`launcher-error.log` and shown in a Windows dialog. Port/store conflicts preserve
the existing service and projects. The launcher never resets data.

To install or repair the shortcut after setup,
run once in PowerShell with the **same** data directory reported by
`/api/v1/runtime`:

```powershell
./scripts/install-launcher.ps1 -DataRoot 'C:/Users/byonk/AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/WoodworkingPlanner/app-development'
```

On another machine, substitute its actual local data directory. An existing
shortcut/config that points elsewhere is preserved with an error; select a
different shortcut filename using `-ShortcutPath '<absolute filename>.lnk'`.
If the checkout has moved, the old settings must be reconciled before reinstalling;
keep the same project data directory. No changes to Windows script
security, network, startup, or firewall settings are needed.

## Terminal setup and diagnostics

Run these commands from `C:/Users/byonk/OneDrive/Documents/ChatGPT/BoardPilot/woodworking-platform` in PowerShell. Verified: Windows, Python 3.13.9, cadgen 0.7.21, build123d 0.11.1, OCP 7.9.3.1.1, Node 24.13.0, Playwright 1.63.0. The CAD upstream commit is `24573128ceaab564f497d7c12f995c41784c9539`. No WSL release gate is claimed.

## First setup

Prerequisites: Node **24.13.0**, npm, the Windows Python launcher (`py`) with a Python installation, and uv **0.9.8**. If uv is absent:

```powershell
py -m pip install --user uv==0.9.8
./scripts/setup.ps1
```

The setup script installs managed Python 3.13.9 when needed, creates the project `.venv`, synchronizes `requirements-runtime.lock`, installs this app, installs Chromium, then runs `npm ci` and the TypeScript/production build. It never resets project data. First setup needs downloads; a prepared dependency/browser cache can use `./scripts/setup.ps1 -Offline`.

If local policy prevents running scripts, use the equivalent commands without changing Windows security settings:

```powershell
py -m uv python install 3.13.9
py -m uv venv --python 3.13.9 .venv
py -m uv pip sync requirements-runtime.lock --python .venv/Scripts/python.exe
py -m uv pip install --no-deps --python .venv/Scripts/python.exe -e .
.venv/Scripts/python.exe -m playwright install chromium
Set-Location apps/web
npm.cmd ci
npm.cmd run build
Set-Location ../..
```

Use an existing `.venv` if setup has already completed. Do not delete an environment or project store to hide a setup failure.

## Preflight and local launch

```powershell
./scripts/preflight.ps1
./scripts/launch.ps1
```

The regular preflight runs a real baseline STEP/GLB build and saved-geometry inspection in the same contained worker used by the app. It reports revision, output directory, elapsed time and sampled process-tree memory; exact versions are recorded in its manifest. The full renderer/axis/drawing spike can be reproduced separately with `./scripts/preflight.ps1 -FullRendering`; it additionally requires `pdftoppm` (Poppler) available on PATH to render the native PDF. `npm test -- tests/m0.spec.ts` in `apps/web` checks independent raycast/highlighting in the real viewer. Ordinary application PDF generation does not require Poppler.

Open **http://127.0.0.1:8777**. Stop with **Ctrl+C**. A second service cannot claim the same data root. An active interrupted job is reconciled on next startup; saved revisions and committed artifacts survive.

To reopen the existing **Sample bookcase walkthrough** and its revision-3 build
plan on this machine, keep its authoritative data root. The stabilized service
uses the normal 120-second deadline:

```powershell
Remove-Item Env:WOODWORK_CAD_TIMEOUT -ErrorAction SilentlyContinue
./scripts/launch.ps1 -DataRoot 'C:/Users/byonk/AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/WoodworkingPlanner/app-development'
```

Generation shows its current CAD stage and elapsed time. A timeout keeps the
accepted revision and previous verified files; **Retry revision** resumes the
generation workflow with a new job. A lost submission response reconnects to the
same request identity, preventing duplicate builds. After a local frontend update,
reload the page to obtain the revalidated application shell.

The default CAD deadline is 120 seconds. On a heavily loaded machine, the existing local timeout setting can allow a bounded five-minute build without changing validation:

```powershell
$env:WOODWORK_CAD_TIMEOUT='300'
./scripts/launch.ps1 -DataRoot '<the same absolute data directory used previously>'
```

Keep the same data directory when restarting. Remove the session override with `Remove-Item Env:WOODWORK_CAD_TIMEOUT` before the next launch to restore the default.

Equivalent launch:

```powershell
.venv/Scripts/python.exe -m uvicorn woodwork.api:create_app --factory --host 127.0.0.1 --port 8777 --no-access-log
```

SQLite, immutable artifacts, exports, imports, diagnostics and disposable caches live under local app data, outside the cloud-synced checkout. Default: `%LOCALAPPDATA%/WoodworkingPlanner/data`. `WOODWORK_DATA_ROOT` or `./scripts/launch.ps1 -DataRoot '<absolute directory>'` selects another local store. Windows packaged-app redirection may resolve that location under the Codex package's LocalCache; `/api/v1/runtime` reports the authoritative directory. Use the same root to reopen prior projects. Do not remove its SQLite/artifacts/exports directories as cache cleanup.

## Design and downloads

Create a bookcase, enter outside dimensions with explicit units, and enter **actual measured** main/back thickness. Nominal stock labels are metadata. Apply and generate; accepted and last-successful revision labels distinguish current parameters from a prior displayed model. Generation runs one native worker at a time, with a 120-second deadline and a bounded queue.

The parts list supports individual selection without manipulating 3D. Hide/isolate/explode affect only the view. Request drawings or stock planning from a completed revision; the new cumulative set retains its geometry. A ZIP freezes one completed set. Import validates inert files and preserves provenance while assigning new local IDs; generate again using installed trusted templates before a local model becomes verified.

The offline proposal demo is explicitly deterministic test behavior. Review its before/after values before applying. Ordinary forms work with AI disabled. This release is intentionally offline (user choice, 2026-10-14); no API key or paid provider access is required.

## Development and verification

In two terminals:

```powershell
./scripts/dev.ps1 -Service api
./scripts/dev.ps1 -Service web
```

Open http://127.0.0.1:5173. The Vite proxy targets the same local API on port 8777. API hot reload is deliberately omitted to avoid interrupting native jobs mid-edit.

```powershell
./scripts/verify.ps1
./scripts/verify.ps1 -Browser
./scripts/demo.ps1
.venv/Scripts/python.exe -m woodwork.cli compile tests/fixtures/bookcase-baseline.json
.venv/Scripts/python.exe -m woodwork.cli build tests/fixtures/bookcase-baseline.json --output '<new empty sample directory>'
```

The verification browser command defaults to the API and Vite services. The demonstration command targets the built production UI on 8777 and runs real native workflows; expect several minutes. Native nine-fixture geometry/document corpora are opt-in and have exact commands and evidence in IMPLEMENTATION-STATUS. A skipped native test is never reported as a passed run.

## Diagnostics and review limits

If a native import is refused, the diagnostic distinguishes an OCP DLL/Windows CodeIntegrity failure from a missing runtime. Inspect the specific component and install the locked dependencies; keep Windows security settings unchanged. WSL is a possible separate setup route, with Linux Python/Node/browser dependencies and full preflight required before claiming support.

The authored Kreg 720/720PRO recipe is limited to its installed, exact measured material/dimension range. Its technical graph checks do not establish physical drill access, workholding, shelf capacity, thin-back behavior or site-specific installation. Those review items are retained beside its instructions. Unknown prices and package sizes remain unknown.
