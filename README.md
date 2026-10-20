# Woodworking Planner

Local plywood-bookcase design software: measured materials, deterministic panel geometry, genuine STEP/GLB, revision-bound drawings and cut lists. Windows is the verified runtime. No API key is required for the manual workflow or offline proposal demonstration.

On this prepared Windows machine, double-click **Woodworking Planner** on the
desktop. It starts the local service quietly, waits until ready, and opens the
app in your default browser. Reopening the shortcut reuses the service and the
same saved projects. Internet access and a terminal are not needed to launch.

For first setup on another machine, from this repository in PowerShell:

```powershell
./scripts/setup.ps1
./scripts/preflight.ps1
./scripts/launch.ps1
```

Open http://127.0.0.1:8777. See [shortcut installation and launch instructions](docs/LAUNCH.md), [implementation evidence](docs/IMPLEMENTATION-STATUS.md), and [construction review boundary](docs/CONSTRUCTION-RECIPE-REVIEW.md). The supplied handoff and unchanged fixtures are under `handoff/package/woodworking-codex-handoff`.

The reference 18 mm / 6 mm project produces a design packet with its construction method unselected. A separate narrowly supported authored method supplies fastening references and instructions; physical review is pending. These are separate software and construction gates. No load rating is inferred.
