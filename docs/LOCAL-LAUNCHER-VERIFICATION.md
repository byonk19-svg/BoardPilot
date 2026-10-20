# Local launcher verification

Spec: `.scratch/local-launcher/PRD.md`.
Starting/review baseline: `4cbd5dd05e691db05b2e86f71dff94a2263a1b81`.

The Windows desktop shortcut uses the existing windowed Python runtime. Its
per-user JSON records the checkout and authoritative data directory explicitly;
the packaged Codex data root is retained even when launched outside Codex. The
launcher waits for the matching loopback service before opening the default
browser. A Windows named mutex serializes competing launcher processes. The
runtime diagnostic now identifies the checkout as well as its data root.

No dependencies, CAD/recipe code, documents, material measurements, provider
configuration, firewall rules, startup tasks, or system services changed.
The service remains running when the browser is closed and is reused on reopen.
Startup failures show a Windows dialog and retain local diagnostic logs.

## Startup and reconnect evidence

The seven public launcher tests cover cold readiness before browser opening,
warm reuse, two simultaneous independent launcher processes, saved revision and
session recovery across restart, refusal of another store on the same port,
failed-startup preservation/retry, bounded startup/retry, and safe/idempotent
shortcut installation. The browser opener is replaced only at the OS boundary
in these tests; each service and HTTP request is real.

`diagnostics.launcher_smoke` uses a fresh store seeded from the supplied baseline's
genuine saved geometry. A real browser loads seven panels, saves a draft, loses
the service, keeps its typed input, and reconnects in the same tab after a real
process restart. The old CSRF token receives 403, the app obtains a new session,
and the draft saves and restores after reload. The accepted revision and saved
cut list remain unchanged. Cold start took **4.089 seconds**, warm reuse **0.130
seconds**. No external requests were attempted; the browser blocked any such
request, and the launcher ignores HTTP proxies and refuses redirects.

The actual desktop `.lnk` was installed and invoked using Windows ShellExecute,
the same entry point used by double-click. It opened the default Chrome browser
on port 8777. Its service binds only to `127.0.0.1`, with no console window.
Invoking the shortcut again kept listener PID 31152. The user's sample was opened
and showed revision 3, 36 × 36 × 12 inches, seven panels, and Build guide PDF.
The accepted revision, project record, preferred output set, and draft contents
and base were unchanged. The normal browser autosave updated the draft timestamp.
The served PDF still has SHA-256
`bf33e8c609826ba4d2d2d807c97c327722e1026c980eec7dc8c01f61ca3efcb2`.

Initial failures were resolved: a red concurrent-click test exposed duplicate
startup before the mutex was added; the browser diagnostic initially lacked its
API base URL, which was fixed and rerun in a new store. No user store was reset.

## Reproduce

Run from `C:/Users/byonk/OneDrive/Documents/ChatGPT/BoardPilot/woodworking-platform`:

```powershell
.venv/Scripts/python.exe -m pytest -q tests/test_launcher.py
.venv/Scripts/python.exe -m diagnostics.launcher_smoke --source 'C:/Users/byonk/AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/WoodworkingPlanner/checkpoint-cad-20261017-serial/bookcase-baseline' --store '<new unused absolute local store>' --output '<local evidence directory>'
./scripts/install-launcher.ps1 -DataRoot 'C:/Users/byonk/AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/WoodworkingPlanner/app-development'
```

The reconnect diagnostic requires port 8777 to be free and never stops a reused
service. Use an isolated store, not the user's sample, for edit tests. It refuses
an existing store directory. Full regression commands/results and review evidence
are recorded in IMPLEMENTATION-STATUS and `evidence/local-launcher-20261020/`.
Detailed traces and JUnit/Playwright reports are retained under
`.verification/local-launcher-20261020/`.

## Regression results

Canonical backend/build: **294 passed, 22 existing native opt-in skips**, plus
successful production typecheck/build. Final launcher subset: **7/7 passed**.
Initial full browser run: **51 passed, 1 failed, no skips/flakies**, 1558.488 s.
The one failure was an existing five-second link-visibility assumption on the
last reload of a completed native plans bundle. The trace shows valid files
already inspected, a prior manifest response taking 4.99 s, and final manifest
verification still pending at the assertion deadline.

Matt's diagnosing-bugs workflow minimized that timing failure with a controlled
8-second manifest delay on the completed real project: old five-second wait
failed, recovery still succeeded in 13.375 s. The test now waits for exact
**Plans ready · revision 2** within 30 seconds before retaining all prior link,
ZIP, hash, CSV, revision, and three-job assertions. No controller behavior or
native worker deadline changed. The full affected native workflow passed on
retest (**1/1**, 115.834 s); final typecheck and both review rechecks passed.
All 52 case behaviors are covered across the two runs. The entire suite was not
rerun after this isolated test synchronization repair. Initial failure and final
retest reports remain separate, rather than claiming a clean initial full run.

## Standards

Independent review found **0 documented-standard violations and 0 actionable
advisory smells**. The pinned CAD path, local boundary, separate data storage,
isolated test stores, and preserved unrelated work were checked.

## Spec

Independent review found **0 actionable findings** against the approved launcher,
startup, reconnect, offline, failure-preservation, and no-push requirements.

Windows process startup/restart and browser reconnect were exercised. A Windows
reboot and other operating systems were not tested. Initial dependency setup on
a new machine remains separate; the installed launcher itself works offline.
