# Beginner bookcase guide

The app has a separately versioned screw-and-glue method for the existing
914.4 x 914.4 x 304.8 mm bookcase, two fixed shelves, actual 18 mm main plywood
and 6 mm back. Its ID is `beginner_screws_18_6_36in_bookcase`, version `1.0.0`.
Other sizes remain incompatible with this narrowly authored method. Selecting
it never substitutes stock, changes dimensions, adds furniture parts, or cuts
new housings into the nominal CAD blanks.

The 25-page Letter guide opens with A-G part names, exact cuts, tools and drill
settings. Ten ordered steps each have a vector illustration. A separate back
worksheet, primary sources, limits, and measured technical appendix follow.
Letter and A4 renderer checks cover the same instructions. `beginner-guide.json`
binds each operation to its illustrated page and the saved revision hashes.
The documents renderer is 1.2.0; historical 1.0/1.1 readers remain supported.

## Construction scope

| Item | Exact requirement |
| --- | --- |
| Side panels A/B | 2 x 914.4 x 298.8 x 18 mm |
| Bottom/shelves/top C-F | 4 x 878.4 x 298.8 x 18 mm |
| Applied back G | 1 x 914.4 x 914.4 x 6 mm |
| Openings | 3 x 280.8 mm clear height |
| Main fasteners | 24 x #8 x 2 in flat-head wood screws |
| Back fasteners | 36 x #6 x 5/8 in flat-head wood screws; McFeelys 0605-FPB |
| Main pilots | 35 mm into receiving edges; 53 mm from outside 18 mm side |
| Back pilots | 12 mm into receiving edges; 18 mm from outside 6 mm back |
| Main marks | Height centres 9 / 307.8 / 606.6 / 905.4 mm; front offsets 30 / 149.4 / 268.8 mm |
| Back marks | 25 / 200 / 375 mm from both ends of each receiving edge; six edges |

Sources in the recipe distinguish published screw/drilling guidance from
authored placement, stops and the shallow back countersink. Matching offcut
tests are required. The back head must seat flush with at most a 2 mm
countersink, leaving at least 4 mm of panel; stop if it crushes/pulls through.
This limit is an authored check, not a supplier-certified safe depth. Supports,
clamps, squaring, full glue cure before turning, and site-specific restraint
before loading are explicit instructions. Physical building, load testing,
site restraint selection and beginner participant testing remain unperformed.

## Verification

Initial focused checks: 58 passed. These include exact applicability, literal
fastener counts/entry faces, shared-side preparation equivalence, adversarial
geometry/hardware/operation mutations, Letter/A4 layout, complete/incompatible
document selection and rejection of missing steps/illustrations.

Independent reviews found and resolved validator dispatch, missing pilot-step,
false front-offset and incompatible-document-export defects. The generated
sample geometry was coherent before these hardening fixes. The legacy Kreg
generator files were left unchanged; its recipe fingerprint remains
`eefc2c56d77ebe54fd315049ebe6b867c737cfc8d8586672748be40d0c08bec1`.

The initial genuine browser run passed Create design -> CAD -> Get plans ->
PDF/stock/ZIP -> reload -> desktop/narrow downloads with external requests
blocked. A subsequent full-suite attempt exposed a 5-second reload assertion;
its CAD/documents/stock/package jobs and archive inspection had all succeeded.
The assertion now waits for the model and restored plans links. Final suite,
saved-sample and visual-review evidence is recorded below when completed.

### Reproduce locally

Run from the repository root with the existing pinned virtual environment:

```powershell
.venv/Scripts/python.exe -m pytest tests/test_beginner_guide.py tests/test_recipes.py tests/test_export_units.py -q
$env:WOODWORK_PACKAGE_SOURCE='C:/Users/byonk/AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/WoodworkingPlanner/regeneration-verification-20261014-b/artifacts/set_4de8651be64c492dafb3955b499dacb1'
$env:WOODWORK_DOCUMENT_SOURCE_ROOT='C:/Users/byonk/AppData/Local/WoodworkingPlanner/m3-documents/117e30a5123c420394d3e8b7018ef1fd'
./scripts/verify.ps1
```

Use an isolated store, never the user store, for browser tests. This run's store:
`C:/Users/byonk/AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/WoodworkingPlanner/beginner-guide-verification-20261019`.
It was seeded once with `diagnostics.recovery.seed` from the genuine
`checkpoint-cad-20261017-serial/bookcase-baseline` source in the same parent.
Choose a new root for another independent run; do not seed over this one.

Start API on 8790 with `WOODWORK_DATA_ROOT` set to that isolated store, and
`vite preview --host 127.0.0.1 --port 5173 --strictPort` in `apps/web`, with
`WOODWORK_API_URL=http://127.0.0.1:8790`. Build first with `npm run build`.

```powershell
$env:WOODWORK_TEST_URL='http://127.0.0.1:5173'
$env:WOODWORK_PRODUCTION_URL='http://127.0.0.1:5173'
$env:WOODWORK_RUN_REGENERATION_FLOW='1'
$env:WOODWORK_PLANS_EVIDENCE_ROOT='<new evidence directory>/plans-regression'
```

From a new ignored evidence working directory, run the absolute Node and
`apps/web/node_modules/@playwright/test/cli.js` paths with
`test --config=<absolute repo>/apps/web/playwright.config.ts --reporter=list,json --trace=on`.
Set `PLAYWRIGHT_JSON_OUTPUT_NAME` to a new evidence path. This keeps historical
screenshots and Get-plans archives intact. The native worker deadline is still
120 seconds; tests do not replace CAD with synthetic geometry.

Exact browser commands used (repository root initially; reuse a fresh evidence
directory for another run):

```powershell
$repo='C:/Users/byonk/OneDrive/Documents/ChatGPT/BoardPilot/woodworking-platform'
$env:WOODWORK_TEST_URL='http://127.0.0.1:5173'
$env:WOODWORK_PRODUCTION_URL='http://127.0.0.1:5173'
$env:WOODWORK_RUN_REGENERATION_FLOW='1'
$env:WOODWORK_PLANS_EVIDENCE_ROOT="$repo/.verification/beginner-guide-20261019/plans-regression"
$env:PLAYWRIGHT_JSON_OUTPUT_NAME="$repo/.verification/beginner-guide-20261019/frontend-results.json"
Set-Location -LiteralPath "$repo/.verification/beginner-guide-20261019/browser-run"
& 'C:/Program Files/nodejs/node.exe' "$repo/apps/web/node_modules/@playwright/test/cli.js" test --config="$repo/apps/web/playwright.config.ts" --reporter=list,json --trace=on
$env:PLAYWRIGHT_JSON_OUTPUT_NAME="$repo/.verification/beginner-guide-20261019/frontend-retry.json"
& 'C:/Program Files/nodejs/node.exe' "$repo/apps/web/node_modules/@playwright/test/cli.js" test beginner.spec.ts --config="$repo/apps/web/playwright.config.ts" --reporter=list,json --trace=on --output='../beginner-retry-results'
Set-Location -LiteralPath $repo
.venv/Scripts/python.exe diagnostics/verify_regeneration_exports.py --api http://127.0.0.1:8790/api/v1 --data-root 'C:/Users/byonk/AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/WoodworkingPlanner/beginner-guide-verification-20261019' --cases .verification/beginner-guide-20261019/browser-run/tests/evidence/regeneration-acceptance.json --output .verification/beginner-guide-20261019/regeneration-export-checks.json
.venv/Scripts/python.exe diagnostics/verify_beginner_plans.py 'C:/Users/byonk/Downloads/Sample-Bookcase-Revision-3-Beginner-Plans.zip' .verification/beginner-guide-20261019/user-manifest.json
```

`diagnostics/verify_beginner_plans.py <downloaded ZIP> <expected manifest JSON>`
independently checks every archive member/hash/revision, exact cut sizes,
hardware quantities, all ten illustrated instructions and complete stock layout.
Poppler renders every delivered guide page for separate visual inspection.

## Final evidence

- Canonical: 287 backend passes, 22 native opt-in skips, 66.72 seconds;
  TypeScript/production build passed. Existing dependency/test warnings and
  large-chunk warning remain, with no new failure.
- Full frontend: 42/43 in 835.085 seconds; the corrected native beginner case
  passed in a separate 59.3-second rerun. All 43 distinct cases passed across
  those runs, including five genuine regeneration builds. A clean single-run
  43/43 result is not claimed.
- Independent `verify_regeneration_exports.py` checks passed. Full/targeted
  reports, traces, screenshots and JUnit are in
  `.verification/beginner-guide-20261019/`; summary and resolved review findings
  are in `evidence/beginner-guide-20261019/`.
- Saved sample revision 3 is `rev_a53502a973b646e6a311fdcee3ebe92f`.
  Full dimension/material records and every other spec field except the recipe
  equal revision 2. Its four genuine jobs succeeded. Previous revision/set and
  `Sample-Bookcase-Revision-2.pdf` remain unchanged.
- Delivered `C:/Users/byonk/Downloads/Sample-Bookcase-Revision-3-Beginner-Plans.pdf`
  (25 pages), SHA-256
  `bf33e8c609826ba4d2d2d807c97c327722e1026c980eec7dc8c01f61ca3efcb2`.
  Matching local ZIP SHA-256
  `25a4656acfe93e908f906aa7dbc6d986144f579264d169e881c2a140f2a3c96d`.
- All 25 guide pages, three native metric sheets and six stock-layout pages
  were rendered and visually inspected. Cut sizes, source/revision labels,
  centre marks, depth sections and back worksheet agree. The independent ZIP
  inspector passed every member/hash/revision and operation/illustration check.
- PDF preview was requested in Codex (queued); the direct local file is ready.
  Main local service remains available on 8777. Test services are stopped after
  verification. No push, deployment, provider call or dependency change.

## Launch

```powershell
./scripts/launch.ps1 -DataRoot 'C:/Users/byonk/AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/WoodworkingPlanner/app-development'
```

Open `http://127.0.0.1:8777/`, choose **Sample bookcase walkthrough**, then
**Get plans** on its saved revision. All runtime generation and files stay
local. No provider keys, dependency changes, push or deployment are involved.
