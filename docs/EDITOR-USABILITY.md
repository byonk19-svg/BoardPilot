# Simple editor verification

Approved scope: `.scratch/simple-editor/PRD.md`. Baseline: `dece1036`.
Completed locally on 2026-10-17. The existing nine-document follow-up changes and
user projects were preserved. No push, remote setup, deployment or paid call.

## Behavior

- Basic controls show outside width/height/depth, shelf count, and measured main
  and back thickness. Material labels, grain, construction recipe, manufacturing,
  stock and PDF settings remain under one closed-by-default Advanced disclosure.
- Assembly guidance remains visible with Advanced closed and during invalid
  drafts. Unchecked edits never claim that fabrication readiness is complete.
  Invalid advanced measurements reveal their controls.
- The primary form action is Create design or Update design. On narrow screens,
  Measurements / 3D view / Cut list links provide direct section access.
- Unit changes convert current validated measurements, including pending edits.
  Invalid/unvalidated text retains its prior explicit units. Thickness stays mm.
- Model bounds identify W/H/D. Summaries, details and cut lists use the selected
  display unit. Saved measurements retain the shown revision's fraction precision;
  draft summaries use draft precision. Approximate inch labels retain exact mm.
  Rounded presentation never becomes a saved measurement or modifies CSV/CAD/PDF.

## Verification

| Gate | Observed result |
| --- | --- |
| Canonical backend and initial build | 258 passed, 22 explicit native opt-in skips, two known warnings; 134.67 s. |
| Final strict TypeScript / Vite build | Passed; Vite 16.21 s, `index-CgspSzIv.js` / `index-CX6p0r1k.css`. Existing chunk advisory only. |
| Final complete frontend suite | **31 passed, zero failed/skipped/flaky, 822.266 s**, including genuine native workflows and nine exact formatter cases. |
| New basic editor / real CAD | 36 x 42 x 14 in, three shelves, actual 19 mm main / 6 mm back, eight parts; 52.250 s. Horizontal panels 876.4 x 349.6 x 19 mm. Model/CSV/revision agree. |
| Five-build regression workflow | Native generation seconds: 22.404, 14.852, 27.706, 29.654, 39.790; all below the unchanged 120 s limit. Width/height/depth edits, stock binding, cancel/retry pass. Cancellation 1275 ms; prior CSV/stock preserved. |
| Agent visual / narrow navigation | Desktop enabled hover remains legible; 535 and 390 px section links work by keyboard, no document-wide horizontal overflow. Narrow cut list retains internal scrolling. |
| Independent review | Standards and Spec reviewed separately. Two P2 spec findings and one visual finding fixed; both reviewers rechecked final fixes with no remaining actionable finding. |
| Original sample / unrelated work | Read-only check: original 36 x 36 x 12 in revision 2, draft, preferred set, manifest and all 19 payloads unchanged. Earlier review/corpus file hashes unchanged. |

The disclosure and unit/pending-draft cases failed before implementation and then
passed. Review regressions also failed for their precise symptoms before the fixes:
invalid drafts removed assembly guidance, and a recovered 16ths draft relabelled a
saved 64ths cut list. Both pass in the final suite, including selected/unselected
method guidance and distinct draft/saved precision. A helper was corrected to
revert an invalid recovered fixture before waiting for a valid submission button.

Tests use public browser/form/HTTP seams, saved genuine GLBs and actual native
workers. Failure-injection cases are separate from genuine generation. An initial
30-case run passed before the final review repairs; the final 31-case run above
uses the rebuilt final source. Backend code, pins and export contracts did not
change. The 22 native opt-in skips are not passes; the separately dated CAD and
nine-document corpus evidence remains in `docs/IMPLEMENTATION-STATUS.md`.

Structured evidence is under `evidence/simple-editor-20261017/`: `verification.json`,
`browser-results.json`, `preserved-walkthrough.json`, and per-revision native/stock
records and screenshots in `browser-run/tests/evidence/`.

## Exact commands

Canonical backend/build, repository cwd:

```powershell
$env:WOODWORK_PACKAGE_SOURCE='C:/Users/byonk/AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/WoodworkingPlanner/regeneration-verification-20261014-b/artifacts/set_4de8651be64c492dafb3955b499dacb1'
$env:WOODWORK_DOCUMENT_SOURCE_ROOT='C:/Users/byonk/AppData/Local/WoodworkingPlanner/m3-documents/117e30a5123c420394d3e8b7018ef1fd'
./scripts/verify.ps1
```

After review fixes, `apps/web` cwd:

```powershell
& 'C:/Program Files/nodejs/npm.cmd' run build
```

The final production preview was started from `apps/web`, with the isolated API
already running on 8790 against the store below:

```powershell
$env:WOODWORK_API_URL='http://127.0.0.1:8790'
& 'C:/Program Files/nodejs/node.exe' node_modules/vite/bin/vite.js preview --host 127.0.0.1 --port 5173 --strictPort
```

Final browser command, cwd `evidence/simple-editor-20261017/browser-run`:

```powershell
$env:WOODWORK_TEST_URL='http://127.0.0.1:5173'
$env:WOODWORK_PRODUCTION_URL='http://127.0.0.1:5173'
$env:WOODWORK_RUN_REGENERATION_FLOW='1'
$env:PLAYWRIGHT_JSON_OUTPUT_NAME='C:/Users/byonk/OneDrive/Documents/ChatGPT/BoardPilot/woodworking-platform/.verification/simple-editor-20261017/browser-final-results.json'
& 'C:/Program Files/nodejs/node.exe' 'C:/Users/byonk/OneDrive/Documents/ChatGPT/BoardPilot/woodworking-platform/apps/web/node_modules/@playwright/test/cli.js' test --config 'C:/Users/byonk/OneDrive/Documents/ChatGPT/BoardPilot/woodworking-platform/apps/web/playwright.config.ts' --reporter list,json --trace on
```

Isolated store:
`C:/Users/byonk/AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/WoodworkingPlanner/simple-editor-verification-20261017`.
Its `Recovery diagnostic` seed uses the actual passing serial-corpus
`checkpoint-cad-20261017-serial/bookcase-baseline` via `diagnostics.recovery.seed`.
Production-preview and test API processes can be stopped after verification;
the user's 8777 service remains running.

## Launch and use

The refreshed app is at http://127.0.0.1:8777/ with Sample bookcase walkthrough
still selected. Change the basic measurements, wait for validation, then choose
Update design. The last successful model/cut list remain identified until the
new saved revision succeeds. Advanced settings keeps specialist options available.

To restart the user's existing store, from the repository:

```powershell
./scripts/launch.ps1 -DataRoot 'C:/Users/byonk/AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/WoodworkingPlanner/app-development'
```

Physical fabrication/load/site-installation review, human accessibility validation
and release approval remain separate. Live AI stays disabled. Combined Get plans
is deferred to a later approved slice.
