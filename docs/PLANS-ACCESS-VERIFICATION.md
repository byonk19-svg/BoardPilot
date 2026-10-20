# Plans beside the model — verification

The saved model now has one plans controller beside it on wide desktop layouts
and before the viewer on narrow layouts. The narrow section links include
Plans. The completed illustrated packet is labelled **Build guide PDF**;
ordinary, incompatible and unselected design packets keep **Measured design
PDF**. Naming uses the validated manifest's construction state and illustrated
guide record, never the editable draft.

Promoted PDFs stay with their frozen plans bundle and appear once. The cut-list
CSV remains at the cut list. Lower output links and the additional-file list
omit already-promoted files. A newer individual PDF from another artifact set
on the same revision stays accessible as an additional file without replacing
the PDF bundled with the plans ZIP.

No backend, CAD, recipe, material, dimension or document-rendering code changed.
Runtime remains local/offline. The original sample is still revision 3, with its
entire saved revision, preferred output set and draft contents unchanged.

## Scope and test seams

Spec: `.scratch/plans-access/PRD.md`. Starting/review baseline:
`b4cbc4d0daf49ee4f47f30a56aa71c564f084ef5`.

Tests use visible browser controls and public revision/artifact/download HTTP
boundaries. Transport fixtures cover coordination and adverse outcomes;
separate native cases generate and inspect real CAD/PDF/ZIP output in an
isolated store. No assertions query private React state or storage internals.

Red-green evidence covered desktop placement and narrow keyboard navigation,
illustrated naming/deduplication, delayed recovery discovery, reopening during an
individual job and a lost individual submission acknowledgement. Focused plans
checks finished at **19 passed** before the full production run.

## Standards

The independent standards review found no documented-standard violation or
actionable smell. It identified a lifecycle concern: discovery did not own the
shared activity lock. The final recheck found that concern resolved and no
remaining concrete issue.

## Spec

The independent spec review identified the same recovery family, including
reopening an active individual job and an uncertain submission. Regression
tests first reproduced each gap. The controllers now restore active individual
jobs from the revision ledger, hold the lock during discovery/uncertainty, and
reconnect using the same frozen request and idempotency key. Plans recovery
waits for individual work to clear. The final recheck approved the spec delta.

Final review summary: **0 open Standards findings; 0 open Spec findings**.

## Verification commands

Repository: `C:/Users/byonk/OneDrive/Documents/ChatGPT/BoardPilot/woodworking-platform`.
These were run with existing pinned dependencies; there was no installation.

```powershell
$env:WOODWORK_PACKAGE_SOURCE='C:/Users/byonk/AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/WoodworkingPlanner/regeneration-verification-20261014-b/artifacts/set_4de8651be64c492dafb3955b499dacb1'
$env:WOODWORK_DOCUMENT_SOURCE_ROOT='C:/Users/byonk/AppData/Local/WoodworkingPlanner/m3-documents/117e30a5123c420394d3e8b7018ef1fd'
$env:PYTEST_ADDOPTS='--junitxml=C:/Users/byonk/OneDrive/Documents/ChatGPT/BoardPilot/woodworking-platform/.verification/plans-access-20261020/backend-results.xml'
./scripts/verify.ps1
```

Backend: **287 passed, 22 existing native opt-in skips**, 56.61 seconds, two
known warnings. The final frontend build was run again after the review fixes:
`npm.cmd run build` from `apps/web`, passing TypeScript and production bundling.
Bundle: `index-Cjk3dr8-.js`; stylesheet: `index-2LPnstGN.css`. The existing large
chunk warning remains.

The isolated store is
`C:/Users/byonk/AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/WoodworkingPlanner/plans-access-verification-20261020`.
It was seeded once using `diagnostics.recovery.seed` from the genuine raw
`checkpoint-cad-20261017-serial/bookcase-baseline` source in that same parent.
Use a new root for another independent run; never seed over an existing store.

API and production preview commands (separate terminals):

```powershell
$env:WOODWORK_DATA_ROOT='C:/Users/byonk/AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/WoodworkingPlanner/plans-access-verification-20261020'
.venv/Scripts/python.exe -m uvicorn woodwork.api:create_app --factory --host 127.0.0.1 --port 8790 --no-access-log
```

```powershell
# apps/web cwd
$env:WOODWORK_API_URL='http://127.0.0.1:8790'
./node_modules/.bin/vite.cmd preview --host 127.0.0.1 --port 5173 --strictPort
```

Full browser run (new ignored evidence working directory):

```powershell
$repo='C:/Users/byonk/OneDrive/Documents/ChatGPT/BoardPilot/woodworking-platform'
$env:WOODWORK_TEST_URL='http://127.0.0.1:5173'
$env:WOODWORK_PRODUCTION_URL='http://127.0.0.1:5173'
$env:WOODWORK_RUN_REGENERATION_FLOW='1'
$env:WOODWORK_BEGINNER_EVIDENCE_ROOT="$repo/.verification/plans-access-20261020/real-beginner"
$env:WOODWORK_PLANS_EVIDENCE_ROOT="$repo/.verification/plans-access-20261020/real-plans"
$env:PLAYWRIGHT_JSON_OUTPUT_NAME="$repo/.verification/plans-access-20261020/frontend-results.json"
Set-Location -LiteralPath "$repo/.verification/plans-access-20261020/browser-run"
& 'C:/Program Files/nodejs/node.exe' "$repo/apps/web/node_modules/@playwright/test/cli.js" test --config="$repo/apps/web/playwright.config.ts" --reporter=list,json --trace=on --output='../full-browser-results'
```

## Final results

Full production browser result: **52 passed, 0 failed, 0 skipped, 0 flaky** in
**636.924 seconds**, in one complete run. This includes the new controls, honest
labels, link deduplication, coordination/recovery regressions, the genuine
illustrated guide, selected/incompatible legacy packets, import/rebuild, the
lost-acknowledgement Get plans case, and five real regeneration builds.

The independent regeneration/export checker also passed native geometry,
documents and a 26-payload package. The genuine guide case checked every ZIP
member/hash/revision and all ten illustrated operations. The unchanged original
sample was refreshed in the running app and its single Build guide PDF link
still targets artifact `159621f3-7cc4-4135-97e6-5f60c9d2e001` on revision 3.

Summary and review: `evidence/plans-access-20261020/verification.json` and
`review.md`. Saved, inspected screenshots: `desktop.png`, `mobile-keyboard.png`,
and `your-bookcase.png` in that same evidence directory.

The genuine illustrated-bookcase case already passed with non-loopback requests
blocked. Its downloaded ZIP independently passed every payload hash/revision,
exact cut groups and all ten illustrated operations. The in-app browser's
keyboard Enter download matched the exact PDF bytes inside that ZIP.

Desktop and 390-pixel narrow screenshots were saved and inspected from the
production build. The Plans shortcut focuses its section; Tab reaches Get
plans, then Build guide PDF; Enter downloaded the PDF. No page-wide narrow
overflow was observed. This is browser emulation and keyboard verification;
physical touch-device and screen-reader testing were not performed.

Detailed local evidence lives in `.verification/plans-access-20261020/`:
`backend-results.xml`, `frontend-results.json`, `full-browser-results/`,
`real-beginner/`, `real-plans/`, `previews/`, `keyboard-guide.pdf` and
`user-preservation.json`. Existing audit screenshots and document-corpus notes
were preserved separately and were not included in this feature's commit.

The independent export command, run from the repository root before stopping
the temporary services, was:

```powershell
.venv/Scripts/python.exe diagnostics/verify_regeneration_exports.py --api http://127.0.0.1:8790/api/v1 --data-root 'C:/Users/byonk/AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/WoodworkingPlanner/plans-access-verification-20261020' --cases .verification/plans-access-20261020/browser-run/tests/evidence/regeneration-acceptance.json --output .verification/plans-access-20261020/regeneration-export-checks.json
```

The test API and preview were stopped after verification. The normal service on
8777 remains available. Nothing was pushed, deployed or sent to a paid provider.

## Launch

```powershell
./scripts/launch.ps1 -DataRoot 'C:/Users/byonk/AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/WoodworkingPlanner/app-development'
```

Open `http://127.0.0.1:8777/` and select **Sample bookcase walkthrough**.
The same revision 3 guide and ZIP are available through the new controls.
