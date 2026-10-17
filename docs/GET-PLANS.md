# Get plans

Completed locally on 2026-10-17 against baseline `9ed8678` and the six acceptance
requirements in `.scratch/get-plans/PRD.md`. No push, cloud/provider calls, new
dependencies, database migration or CAD pin changes.

## Use

Open http://127.0.0.1:8777/. Change measurements, choose Update design, then wait
for the verified model. Choose **Get plans** for that saved revision. The app
prepares measured drawings, a stock layout and a project ZIP. Download the ZIP
or its PDF/stock/cut-list files from the Plans downloads section. Individual
output tools remain available in their disclosure.

Progress names all three steps and their revision. Failed work offers Retry plans;
completed earlier steps are retained. Lost responses reconnect using the same
idempotency key. Reload recovers the latest step from the persistent job ledger.
Cancel plans pauses advancement immediately, independently of the cancellation
acknowledgement. An unconfirmed cancellation stays paused until explicit retry.
Incomplete stock is reported and is not offered as a complete plans ZIP.

The browser coordinates existing jobs. Closing or leaving this revision lets an
already submitted worker finish, then pauses subsequent steps. Reopening that
revision resumes the chain. No background service or additional database table
was introduced.

## Revision consistency

The controller captures the displayed saved revision and source artifact set.
Documents receive that source explicitly. Stock receives the successful documents
set; the ZIP receives the successful stock set, including the drawings. Every
job and manifest is checked against its expected revision, step, request key and
source. The chain never substitutes the changing preferred artifact set.
Download links use the exact cumulative manifest packaged into the ZIP. The
backend continues independently validating immutable inputs, payloads and receipts.

## Verification

| Gate | Observed result |
| --- | --- |
| Canonical backend | 258 passed, 22 explicit native opt-in skips, zero failures/errors; console 83.16 s, two known warnings. |
| Strict TypeScript / production build | Passed: `index-DdMHmrUF.js`, `index-BevTvlUp.css`. Existing chunk-size advisory only. |
| Final full frontend suite | **42 passed, zero failed/skipped/flaky in 803.490 s**, with real native regeneration enabled. |
| New genuine whole workflow | New 30-inch baseline -> changed 36 x 42 x 14 inches / three shelves / actual 19 mm main -> Update design -> eight genuine CAD panels -> Get plans -> real documents, stock and ZIP. |
| Reload / unknown outcome | Reload during drawings; real stock POST accepted but its acknowledgement deliberately lost. Explicit retry reconnected; exactly one documents, stock and package job succeeded. A final reload retained downloads without new jobs. |
| Independent ZIP inspection | 25 payloads: exact inventory, every byte size/SHA-256, revision and spec binding checked with Python/zipfile independently of the exporter. PDFs parsed with pypdf. CSV retains exact 876.4 x 349.6 mm horizontal panels and equals the prior same-revision CSV. |
| Protocol / lifecycle | Failed stock retry, mismatched revision, incomplete stock, duplicate click, failed recovery lookup, cancelling retry, navigation, delayed cancel acknowledgement and unconfirmed cancellation pass. |
| Independent reviews | Standards and Spec checked separately; one cancellation P2 found, reproduced, fixed and re-reviewed. No remaining concrete finding. |
| Sample preservation | Original 36 x 36 x 12 inch revision 2, raw draft, preferred set, manifest and all 19 payloads unchanged. Earlier review/corpus evidence preserved. |

A separate in-app-browser check downloaded the ZIP using Enter; its SHA-256
matched the independently inspected package. Four rendered PDF pages were
visually inspected: overview, grouped cuts, main-sheet layout and native
horizontal drawing. They were legible and unclipped. All 18 pages were parsed;
the other 14 were not separately visually inspected. See `keyboard-download.json`
and `pdf-review.json` for the evidence layer and exact scope.

PDF page counts in the independently inspected ZIP: `{"design-packet.pdf": 7, "drawings/panel_back-metric.pdf": 1, "drawings/panel_horizontal-metric.pdf": 1, "drawings/panel_side-metric.pdf": 1, "stock-layout.pdf": 8}`.
Structured records and screenshots are under `evidence/get-plans-20261017/`.
The first native case reached ZIP validation but failed while writing its evidence
because the parent folder did not exist. The helper now creates it; the final
full-suite result above includes all remaining download/narrow/reload assertions.
Earlier source/corpus records are preserved rather than counted as fresh runs.

## Review

### Standards

No hard documented-standard violation or actionable code smell was found. The
review identified a P2 cancellation race: a delayed acknowledgement could allow
the next output job to start or interrupt a retry. Immediate pause and retry locks
fix that race; the reviewer approved the final change on re-inspection.

### Spec

The independent spec review found the same P2 cancellation issue. Its regression
first reproduced unwanted stock/ZIP submissions and now passes. Explicit source
chains, frozen downloads, retry, reload and navigation match the approved brief.
No remaining concrete spec finding or scope creep was found.

Open findings: Standards zero; Spec zero. Reviewers did not run the verification
commands; the executed backend/browser/native evidence is recorded above.

## Exact run commands

Repository cwd, canonical backend/build:

```powershell
$env:WOODWORK_PACKAGE_SOURCE='C:/Users/byonk/AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/WoodworkingPlanner/regeneration-verification-20261014-b/artifacts/set_4de8651be64c492dafb3955b499dacb1'
$env:WOODWORK_DOCUMENT_SOURCE_ROOT='C:/Users/byonk/AppData/Local/WoodworkingPlanner/m3-documents/117e30a5123c420394d3e8b7018ef1fd'
$env:PYTEST_ADDOPTS='--junitxml=C:/Users/byonk/OneDrive/Documents/ChatGPT/BoardPilot/woodworking-platform/.verification/get-plans-20261017/backend-results.xml'
./scripts/verify.ps1
```

The isolated 8790 API used `WOODWORK_DATA_ROOT` set to
`C:/Users/byonk/AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/WoodworkingPlanner/get-plans-verification-20261017`,
seeded with genuine `checkpoint-cad-20261017-serial/bookcase-baseline` geometry via
`diagnostics.recovery.seed`. API command, repository cwd:

```powershell
& .venv/Scripts/python.exe -m uvicorn woodwork.api:create_app --factory --host 127.0.0.1 --port 8790 --no-access-log
```

Production preview, `apps/web` cwd:

```powershell
$env:WOODWORK_API_URL='http://127.0.0.1:8790'
& 'C:/Program Files/nodejs/node.exe' node_modules/vite/bin/vite.js preview --host 127.0.0.1 --port 5173 --strictPort
```

Full frontend run, cwd `evidence/get-plans-20261017/browser-run`:

```powershell
$env:WOODWORK_TEST_URL='http://127.0.0.1:5173'
$env:WOODWORK_PRODUCTION_URL='http://127.0.0.1:5173'
$env:WOODWORK_RUN_REGENERATION_FLOW='1'
$env:PLAYWRIGHT_JSON_OUTPUT_NAME='C:/Users/byonk/OneDrive/Documents/ChatGPT/BoardPilot/woodworking-platform/.verification/get-plans-20261017/browser-final-results.json'
& 'C:/Program Files/nodejs/node.exe' 'C:/Users/byonk/OneDrive/Documents/ChatGPT/BoardPilot/woodworking-platform/apps/web/node_modules/@playwright/test/cli.js' test --config 'C:/Users/byonk/OneDrive/Documents/ChatGPT/BoardPilot/woodworking-platform/apps/web/playwright.config.ts' --reporter list,json --trace on
```

Restart the user's existing store from the repository:

```powershell
./scripts/launch.ps1 -DataRoot 'C:/Users/byonk/AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/WoodworkingPlanner/app-development'
```

Live AI remains disabled. Human accessibility and physical construction/load/site
installation review remain separate; these software checks do not confer approval.
