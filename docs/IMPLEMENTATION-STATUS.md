# Implementation status

## 2026-10-19 Beginner guide for the existing sample

Completed the authorized exact-sample method and guide. The app now offers
`beginner_screws_18_6_36in_bookcase@1.0.0`: through-side screw-and-glue joints
for actual 18 mm main plywood and a shallow flush-screwed 6 mm applied back.
Outside size remains 914.4 x 914.4 x 304.8 mm, with two shelves/seven panels.
Different sizes remain incompatible; no stock substitution is performed.

- New guide: **25 pages / 10 illustrated assembly steps**, plain A-G cut list,
  tools/bit/depth settings, named marking edges, supports/clamping, squaring,
  glue curing, exact back worksheet, source/adaptation limits and technical appendix.
- Focused checks: **58 passed**. Final canonical backend: **287 passed, 22
  explicit native opt-in skips**, 66.72 s; two known warnings. Strict
  TypeScript/production build passed (`index-BJSs3BXN.js`); existing chunk warning remains.
- Full frontend: **42/43 passed in 835.085 s**, zero skips. The lone failure
  was a 5-second reload assertion after successful CAD/documents/stock/ZIP and
  archive checks. After waiting for the loaded model/restored links, the
  complete native beginner case passed again in **59.3 s**. All **43 distinct
  cases passed across the full run and corrected targeted rerun**; this is not
  reported as a clean single-run full-suite pass.
- Five genuine regeneration builds, cancellation/retry and independent native
  geometry/export/package checks passed. Legacy selected and incompatible
  design packets still work. The existing Kreg recipe fingerprint is unchanged.
- User sample **revision 3**, `rev_a53502a973b646e6a311fdcee3ebe92f`, generated
  all four jobs successfully. Entire dimensions/material objects and every
  other spec field except recipe selection match revision 2. Prior revision,
  preferred set and original PDF are preserved. Model, cut list, drawings,
  stock, guide and ZIP have the same revision/spec hashes.
- Rendered and visually checked all **25 final guide pages**, three native
  metric sheets and six stock PDF pages. Independent ZIP inspection checked
  every member/hash/revision, exact cuts and all ten illustrated operations.
- Downloads: `C:/Users/byonk/Downloads/Sample-Bookcase-Revision-3-Beginner-Plans.pdf`
  and matching `.zip`. PDF SHA-256
  `bf33e8c609826ba4d2d2d807c97c327722e1026c980eec7dc8c01f61ca3efcb2`.
  Codex PDF preview requested; app returned queued.

Exact commands, source/method limits, launch steps and evidence paths:
[beginner verification](BEGINNER-BOOKCASE-VERIFICATION.md).
Recorded results: [verification JSON](../evidence/beginner-guide-20261019/verification.json).
Local detailed evidence: `.verification/beginner-guide-20261019/`.
Physical build, load testing, actual offcut/stock checks, site restraint and
beginner participant evaluation remain human gates. No physical approval or
load rating is claimed. Runtime stays local/offline; CAD pins and dependencies
are unchanged. No push or deployment.

## 2026-10-17 Get plans workflow

Completed and verified against `.scratch/get-plans/PRD.md`. Get plans now prepares
drawings -> stock -> ZIP with progress, retry, cancellation and reload recovery.
Every job receives an explicit source from the previous successful result. Bundle
downloads use the same saved revision and exact packaged cumulative artifact set.
Individual output tools remain available. Incomplete stock is reported before
offering a complete package. Offline/local behavior and pinned CAD are unchanged.

- Canonical backend: **258 passed, 22 explicit native opt-in skips**, two known
  warnings, 83.16 seconds. Strict TypeScript/production build passed (`index-DdMHmrUF.js`).
- Final full frontend: **42 passed, zero failed/skipped/flaky in 803.490
  seconds**, including genuine CAD and five-build regeneration.
- New real workflow: update to 36 x 42 x 14 inches, three shelves, actual 19/6 mm,
  eight parts; reload during drawings and recover a deliberately lost stock ACK.
  Exactly three successful output jobs produced a ZIP with
  25 independently hashed/revision-checked payloads.
- Independent Standards/Spec reviews complete. Delayed-cancellation P2 reproduced,
  fixed and rechecked; failed recovery lookup and cancelling retry regressions pass.
- Original sample revision 2, raw draft, saved set/manifest and all 19 payloads
  unchanged. Pre-existing document-corpus follow-up remains preserved separately.

Exact commands, use/launch instructions and browser-coordination behavior:
`docs/GET-PLANS.md`. Evidence: `evidence/get-plans-20261017/`. No push, paid call,
cloud change, database migration or new dependency. Physical/human accessibility/
release approval remains separate; earlier native corpora retain dated evidence.

## 2026-10-17 simpler manual editor

Completed and verified against the six requirements in
`.scratch/simple-editor/PRD.md`: basic measured fields first, one Advanced
disclosure, Create/Update design, exact unit switching, saved revision display
identity and direct narrow-screen section access. Assembly guidance stays visible
during invalid drafts. Saved fraction precision stays bound to the shown revision.

- Backend: **258 passed, 22 explicit native opt-in skips**, two known warnings,
  134.67 seconds. The skipped native corpora retain their separately dated evidence.
- Final strict TypeScript/production build passed (`index-CgspSzIv.js`,
  `index-CX6p0r1k.css`); final full frontend suite: **31 passed, zero failed/skipped/
  flaky in 822.266 seconds**. Genuine CAD, CSV/stock binding, PDF/ZIP/import,
  recovery and cancellation checks remain active under the same worker limits.
- New eight-panel sample: 36 x 42 x 14 inches, three shelves, actual 19/6 mm,
  genuine generation 52.250 seconds. Five-build regeneration and stock
  workflow passed; cancellation 1275 ms preserved earlier downloads.
- Independent Standards/Spec reviews complete; two P2 spec findings and one
  visual finding fixed and rechecked. Desktop/535/390 px checks passed.
- Original sample revision 2, raw draft, saved set/manifest and all 19 payloads
  unchanged. Pre-existing nine-document follow-up files remain preserved.

Exact commands, launch/use instructions, review scope and limitations:
`docs/EDITOR-USABILITY.md`. Evidence: `evidence/simple-editor-20261017/`.
Keep local; no push, deployment, paid provider or CAD pin changes. Physical/human
accessibility/release approval remain separate; combined Get plans is deferred.

## 2026-10-17 review and first local checkpoint

The current task is to review/verify the app and create its first **local** Git
commit. No push, remote configuration, deployment or paid-provider call is
authorized or performed. Earlier dated records below are historical evidence.

Five P2 product findings were repaired: PDF schedule units/precision, two CAD
preflight evidence errors, opened-project tracking after an optional list-refresh
failure, and manual editing when browser storage throws. The pinned CAD runtime,
deterministic geometry and revision/export binding remain intact. Review found
no P0/P1 issue. Browser helper assumptions were repaired after actual failures;
their logs and diagnosis are retained, with no forced click or weakened CAD limit.

| Checkpoint gate | Fresh result |
| --- | --- |
| Backend | 258 passed, 22 explicit native opt-in skips, two known warnings; 187.65 s. |
| Production build | TypeScript and Vite passed; 55.08 s; bundle `index-B_PlvTYW.js`. |
| Final test-helper types | Strict TypeScript check passed after all browser-harness repairs; 5.16 s. |
| Browser workflows | All 17 distinct cases passed across focused runs/reruns. Includes genuine manual edits, selection, drafts, cancellation/retry, offline proposals, priced stock, authored PDFs, ZIP import/rebuild, desktop and narrow layouts. |
| Genuine dimension edits | Five builds at 15.514 / 14.602 / 47.226 / 34.014 / 17.759 s. Model/CSV/new stock PDF agree on each revision. Cancel 1.593 s; prior downloads retained. |
| New PDF options | Metric-only and dual sixteenths pass real CAD/documents/stock/package jobs and independent saved-output validation. Both ZIPs contain 26 verified payloads. |
| PDF rendering/review | All 32 pages rendered and agent-reviewed in contact sheets; selected units are correct and labels/tables unclipped. |
| User data | Read-only comparison preserves walkthrough revision 2, 36 × 36 × 12 in, draft/preferred set/manifest and all 19 payload hashes/sizes. |
| Native fixture corpus | Final full serial run: 30 passed in 263.25 s, including all 13 native opt-in cases. All nine fixture workers passed in 12.573–32.895 s with the unchanged 120-second limit. Earlier overload failures are retained. |
| Git audit | Protected handoff/sample/evidence bytes survive an actual Git checkout; 27 handoff index entries and 50 complete-sample payloads match. Final staged-path/known-secret-pattern audit is recorded in `index-audit.json`. |
| Local Git checkpoint | The first local commit contains this reviewed tree on `codex/woodworking-platform`; obtain its ID with `git log -1`. No remote/push. Parent `.omx` and user databases remain outside the app commit. |

`docs/LOCAL-CHECKPOINT-REVIEW.md` records findings, exact commands, failed attempts,
harness repairs, evidence locations and limits. Fresh machine-readable evidence,
screenshots and the new unit-option ZIPs are under `evidence/checkpoint-20261017`.
The historical partial `samples/bookcase-baseline` folder is now labelled as a
snapshot; the complete reference/authored sample folders and ZIPs remain intact.

Canonical backend/build command (repository cwd):

```powershell
$env:WOODWORK_PACKAGE_SOURCE='C:/Users/byonk/AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/WoodworkingPlanner/regeneration-verification-20261014-b/artifacts/set_4de8651be64c492dafb3955b499dacb1'
$env:WOODWORK_DOCUMENT_SOURCE_ROOT='C:/Users/byonk/AppData/Local/WoodworkingPlanner/m3-documents/117e30a5123c420394d3e8b7018ef1fd'
./scripts/verify.ps1
```

Final serial native command (browser/API test services stopped first):

```powershell
$env:WOODWORK_RUN_CAD_CORPUS='1'
$env:WOODWORK_CAD_OWNED_CORPUS='1'
$env:WOODWORK_CAD_CORPUS_ROOT='C:/Users/byonk/AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/WoodworkingPlanner/checkpoint-cad-20261017-serial'
.venv/Scripts/python.exe -m pytest tests/test_cad_adapter.py -q --junitxml "$env:WOODWORK_CAD_CORPUS_ROOT/pytest-results.xml"
```

Physical fabrication/load/site-installation, human accessibility validation and
release approval remain separate. Nine native document-corpus regenerations were
not repeated; their historical evidence is kept separate from the freshly checked
real unit-option/authored PDF paths. Live AI remains intentionally disabled per
the user's choice. Test API/preview ports 8790/5173 are stopped. The normal service
on 8777 uses the preserved development store with no timeout override. Relaunch it
from this repository with:

```powershell
./scripts/launch.ps1 -DataRoot 'C:/Users/byonk/AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/WoodworkingPlanner/app-development'
```

## 2026-10-15 dimension-edit stabilization

The focused stabilization is **completed and verified**. The normal CAD limit is
**120 seconds**; the user's service on 8777 has no timeout override. Historical
300/600-second runs below describe the earlier problem, not the current launch.

- Adapter 1.1.0 keeps the existing isolated Windows Job Object worker and disabled
  shared daemon. Maintained `@step` models export GLBs through the supported public
  `cadgen.glb.build(saved_step, output)` route, reusing the exact saved document's
  attested producer/mesh. A batch executes in the already isolated worker, sharing
  native imports with independent saved-byte inspection. Library callers retain
  a child batch by default. No project geometry formulas or pinned CAD versions changed.
- Native inspection still checks STEP/GLB dimensions, placement, solid validity,
  bounds, winding/normals, contacts/overlap, union volume and openings. Its report
  binds all seven inspected CAD hashes and saved STEP selectors. Publication
  verifies those bindings instead of repeating the same native inspection.
- Bounded startup traces found repeated Windows font scans in transient CAD helpers.
  A geometry-only bootstrap skips only build123d's unused system-font registration
  and optional WMI lookup. It preserves bundled fonts, explicit reads and other
  globs; regular PDF-job environments and installed CAD libraries remain intact.
  The hook is hashed into provenance and must be revisited for future CAD-text models.
- The UI shows real CAD stages and elapsed time, explains timeout/retry, prevents
  duplicate submissions, reconnects after polling/lost-response failures using the
  same idempotency key, and clears obsolete errors on retry. Structured setup
  guidance is retained. HTML revalidation prevents an old cached shell from hiding
  a newly built bundle. The draft summary now says **Applied back width** correctly.
- Final-source backend command: **242 passed, 22 explicitly skipped native tests,
  two known warnings, 83.58 seconds**. Those skips comprise 13 CAD and nine document
  regeneration cases. The CAD cases passed in the separate current native run;
  the nine document cases retain their earlier corpus evidence. Skips are never
  counted as passes. Final TypeScript/production build passed in **8.63 s** with
  the existing large-bundle advisory.
- Current native corpus: **30 passed in 288.17 s**. All nine supplied golden
  examples ran in the production owned worker at the normal 120-second limit,
  then passed independent saved STEP/GLB checks against exact expected results.
  Their worker times ranged **7.84–63.13 s**, peak sampled tree RSS **805363712 bytes**.
  The precision-contact case and genuine tampered CAD/CSV/overlap cases also passed.
  Inventory/hash/selector proof checks reopened all ten saved sets afterward.
- Final production-preview browser run: **all seven checks passed in 2.4 min**
  from a new isolated store with **zero CAD cache files**. Five real builds took
  **25.51 / 18.81 / 19.35 / 22.91 / 10.49 seconds**. Cancellation took **1.463 s**,
  retained the previous CSV and stock PDF, and retry succeeded without restarting
  the service. Each new model, CSV, complete seven-panel stock plan and new PDF
  identity describes the same accepted revision. An earlier complete run on the
  same final CAD route also passed (16.13–31.40 s); earlier candidates that still
  timed out were diagnosed rather than counted as completed stabilization.
- Independent saved-byte checks reopened **all ten final browser sets** (five
  raw geometry and five cumulative stock sets), checked exact dimensions/revision
  identity, and replayed every stock cut tree successfully. A fresh cumulative
  document job passed in **13.314 s**. Its geometry, drawings, stock, cost records
  and **26-entry ZIP** pass native/inventory/hash/revision checks. All **16 PDF
  pages** were rendered and visually inspected: seven Letter design pages, three
  genuine native metric A4 drawings and six stock/cut-sequence pages. Poppler
  emitted display-font mapping warnings; the inspected pages are legible and
  unclipped. This agent review does not establish physical construction approval.
- The actual CLI preflight passed in **8.416 s**, peak sampled tree RSS
  **473526272 bytes**, without a timeout override, using the development store's
  cache and a new output directory. User project revisions and exports were preserved.
- The user's **Sample bookcase walkthrough**, revision 2, remains **36 × 36 × 12 in**.
  Project, draft inputs, preferred set and manifest hash match the captured before
  state. All 19 artifact records pass integrity checks. The updated UI loads all
  seven panels and retains its stock PDF. AI remains disabled/unconfigured, with
  the offline demo available and no credentials required for forms.

Evidence and the working verification plan: `docs/REGENERATION-STABILIZATION.md`,
`apps/web/tests/evidence/regeneration-acceptance.json`,
`apps/web/tests/evidence/regeneration-cancel.json`,
`evidence/m2/preserved-walkthrough-after.json`, and
`evidence/m2/preserved-walkthrough-ui.json`.

Current local stabilization gates all pass. Physical build/load/installation
review remains open. Live AI stays intentionally disabled per the user's choice;
no provider call, deployment, push, release or physical-review claim was made.
Temporary verification API/preview services on 8790/5173 were stopped after all
jobs completed; their evidence stores remain intact. The development service on
8777 remains healthy, with the preserved sample open and the normal CAD limit.

Exact commands for this verification (repository cwd unless noted):

```powershell
$env:WOODWORK_PACKAGE_SOURCE='C:/Users/byonk/AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/WoodworkingPlanner/regeneration-verification-20261014-b/artifacts/set_4de8651be64c492dafb3955b499dacb1'
$env:WOODWORK_DOCUMENT_SOURCE_ROOT='C:/Users/byonk/AppData/Local/WoodworkingPlanner/m3-documents/117e30a5123c420394d3e8b7018ef1fd'
.venv/Scripts/python.exe -m pytest -q

$env:WOODWORK_RUN_CAD_CORPUS='1'
$env:WOODWORK_CAD_OWNED_CORPUS='1'
$env:WOODWORK_CAD_CORPUS_ROOT='C:/Users/byonk/AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/WoodworkingPlanner/regeneration-corpus-20261015-final'
.venv/Scripts/python.exe -m pytest tests/test_cad_adapter.py -q
```

The recorded corpus root now contains immutable results; choose a new empty root
for a fresh regeneration. These commands were run in separate shells. Clear the
three corpus variables before ordinary verification if reusing a shell.

The final browser store was seeded once from the verified raw source above via
`diagnostics.recovery.seed`; its cache contained zero files before the run
(`evidence/m2/regeneration-final-store.json`). The user's development store was
kept separate. The one-time seed command below requires a new root; choose a new
name for another fresh-cache run. Reuse the existing store without seeding when
reopening these recorded results.

```powershell
.venv/Scripts/python.exe -c "from pathlib import Path; from diagnostics.recovery import seed; root=Path('C:/Users/byonk/AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/WoodworkingPlanner/regeneration-verification-20261015-final'); assert not root.exists(); seed(root, Path('C:/Users/byonk/AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/WoodworkingPlanner/regeneration-verification-20261014-b/artifacts/set_4de8651be64c492dafb3955b499dacb1'))"
```

In a service terminal:

```powershell
$env:WOODWORK_DATA_ROOT='C:/Users/byonk/AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/WoodworkingPlanner/regeneration-verification-20261015-final'
$env:WOODWORK_CAD_TIMEOUT='120'
.venv/Scripts/python.exe -m uvicorn woodwork.api:create_app --factory --host 127.0.0.1 --port 8790 --no-access-log
```

In separate `apps/web` terminals:

```powershell
npm.cmd run build
$env:WOODWORK_API_URL='http://127.0.0.1:8790'
./node_modules/.bin/vite.cmd preview --host 127.0.0.1 --port 5173 --strictPort
```

```powershell
$env:WOODWORK_TEST_URL='http://127.0.0.1:5173'
$env:WOODWORK_RUN_REGENERATION_FLOW='1'
npm.cmd test -- tests/regeneration.spec.ts --trace on
node.exe diagnostics/preserved-sample.mjs
```

Saved CAD/stock and cumulative PDF/ZIP verification (repository cwd):

```powershell
.venv/Scripts/python.exe diagnostics/verify_regeneration.py --data-root 'C:/Users/byonk/AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/WoodworkingPlanner/regeneration-verification-20261015-final' --cases apps/web/tests/evidence/regeneration-acceptance.json --output evidence/m2/regeneration-saved-output-checks.json
.venv/Scripts/python.exe diagnostics/verify_regeneration_exports.py --api http://127.0.0.1:8790/api/v1 --data-root 'C:/Users/byonk/AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/WoodworkingPlanner/regeneration-verification-20261015-final' --cases apps/web/tests/evidence/regeneration-acceptance.json --output evidence/m2/regeneration-export-checks.json
$env:WOODWORK_DATA_ROOT='C:/Users/byonk/AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/WoodworkingPlanner/app-development'
Remove-Item Env:WOODWORK_CAD_TIMEOUT -ErrorAction SilentlyContinue
.venv/Scripts/python.exe -m woodwork.cli preflight --output 'C:/Users/byonk/AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/WoodworkingPlanner/regeneration-preflight-20261015-final'
./scripts/launch.ps1 -DataRoot 'C:/Users/byonk/AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/WoodworkingPlanner/app-development'
```

Preflight's recorded output directory already exists; use a new name to rerun it.
The development service is already running on 8777; the launch command is for its
next restart. `evidence/m2/regeneration-export-checks.json` records every rendered
page hash and the verified ZIP hash; page images are in `output/pdf/regeneration-final`.

The PDF render command used all five PDFs from cumulative set
`set_af2cbcb2a6804c2c8cdc6b407cd4bcbf`:

```powershell
$pdfRoot='C:/Users/byonk/AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/WoodworkingPlanner/regeneration-verification-20261015-final/artifacts/set_af2cbcb2a6804c2c8cdc6b407cd4bcbf'
$renderRoot=Join-Path (Get-Location) 'output/pdf/regeneration-final'
New-Item -ItemType Directory -Path $renderRoot -Force | Out-Null
$renderer='C:/Users/byonk/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe'
foreach ($relative in @('design-packet.pdf','stock-layout.pdf','drawings/panel_side-metric.pdf','drawings/panel_horizontal-metric.pdf','drawings/panel_back-metric.pdf')) {
    & $renderer -scale-to 1400 -png (Join-Path $pdfRoot $relative) (Join-Path $renderRoot ([IO.Path]::GetFileNameWithoutExtension($relative)))
    if ($LASTEXITCODE -ne 0) { throw "PDF rendering failed: $relative" }
}
```

## 2026-10-14 sample walkthrough follow-up

- Imported `samples/reference-bookcase/project.zip` into the existing development store as **Sample bookcase walkthrough**, project `project_26ad37413dc040deb6b0d479c438e8a3`, revision `rev_dcc281e8dc014c2fab05e5d108a64e97`. Existing projects and sample payloads are preserved.
- A fresh build exposed Windows architecture variables omitted at both environment boundaries. When Python's optional WMI lookup was unavailable, cadgen selected the nonexistent `filetrace-windows-.dll` instead of its installed x86_64 tracer. Both boundaries now retain only the two additional Windows architecture variables; provider credentials remain excluded. Owned native processes also skip optional WMI metadata discovery, which stalled on this machine. The compatibility helper participates in the build fingerprint.
- Regression evidence: the nested-process tracer test first failed with empty architecture versus `AMD64`; after repair, `.venv/Scripts/python.exe -m pytest tests/test_worker.py tests/test_process.py -q` passed **15 tests**. `.venv/Scripts/python.exe -m pytest -q` passed **216 tests**, with **38 explicitly skipped corpus/source-dependent tests** and two warnings in 41.36 seconds. This invocation did not set the optional saved-corpus environment variables; its skips are not fresh native evidence.
- Two-minute builds also encountered resource contention (96.8% sampled CPU, Windows servicing/security and other unrelated processes active). No unrelated process was stopped and no OS security setting was changed. The baseline follow-up used `WOODWORK_CAD_TIMEOUT=300`; at that time the walkthrough service used the existing bounded `WOODWORK_CAD_TIMEOUT=600` setting and the same development store after the user's revision-2 build exceeded 300 seconds. This historical override is superseded by the normal-limit stabilization and current launch recorded above.
- Fresh native rebuild **passed**: job `job_df9da831384b46b4a8cb8892adccaf61` published `set_18b35851c4db451ab27a6fff2a974825` for revision 1 in **285.9086 seconds**, peak sampled process-tree RSS **882245632 bytes**, within the configured 300-second limit. The rendered viewer loaded all seven physical panels; the cut list and downloads report the same revision. Screenshot visually inspected: `output/playwright/sample-bookcase-walkthrough.png`.
- Real browser follow-up: entering `36 in` in Outside width enabled **Apply and generate**, previewed horizontal panels `726 → 878.4 mm`, and retained the revision-1 model/cut list until application. **Revert draft** restored `30 in`; reopening confirmed the saved `30 × 12 × 36 in`, two-shelf baseline. No dimension revision was committed during this walkthrough preparation. Machine load still makes generation slow; the default 120-second performance bound was not met in this follow-up and is not claimed as a pass.
- The user then applied the 36-inch width. Accepted revision 2 is `rev_d607e963a700410e945ea0de72025316`, with outside width/height `914.4 mm`, depth `304.8 mm`, inside width `878.4 mm` and two shelves. Job `job_aded8feb9c8f4bce809c670f1b0286ae` safely timed out at 300.0346 seconds without replacing revision 1's verified outputs. Retry `job_5b35c7c1508246a0a813dc55e8374397` **passed** with the 600-second local limit in **146.4053 seconds**, peak sampled RSS **882712576 bytes**, publishing `set_2f70abf514f741d9938013dc1bd2466d`. Manifest parameter/geometry checks passed. Actual downloaded CSV has two `914.4 × 298.8 × 18 mm` sides, four `878.4 × 298.8 × 18 mm` horizontal panels and one `914.4 × 914.4 × 6 mm` back, all bound to revision 2. The rendered model, cut list and saved downloads show revision 2; screenshot `output/playwright/sample-bookcase-revision-2.png` was inspected. Documents and stock planning were not requested for revision 2.

## Environment and repository

Revision-2 stock follow-up (2026-10-14): the user requested generation and review. Browser **Plan stock and cost · revision 2** queued `job_00e40423aa04445ca07ff76f15a9460a`, which passed in 5.9360 seconds and published cumulative set `set_7f4ab0937d1440a5a5c1b4e7ecbe3027`. All seven panel instances occur exactly once, with no unplaced parts: one main sheet (18 mm) and one back sheet (6 mm), each 2440 × 1220 mm. Fresh 19-artifact integrity/revision checks and independent stock cut-tree replay passed, including 3.2 mm kerf, 10 mm edge trim and grain constraints. Assembly STEP, all six part STEP/GLB files and the cut-list CSV are byte-identical to their verified geometry source. All six stock PDF pages were rendered with `pdftoppm -scale-to 1400 -png <artifact-set>/stock-layout.pdf output/pdf/revision-2-stock/page` and visually inspected; Poppler emitted unused font-mapping warnings but the rendered text and diagrams are legible and unclipped. Prices remain unknown, with no complete sheet/project total claimed. Evidence: `evidence/m4/revision-2-stock-review.json`; rendered pages: `output/pdf/revision-2-stock/`. The application exposes **Stock layout and cut sequence PDF · revision 2**. Construction method remains unselected.

Revision-2 cut-list recheck (2026-10-14): the displayed table and actual CSV match three independently calculated groups: 2 sides `914.4 × 298.8 × 18`, 4 horizontal panels `878.4 × 298.8 × 18`, and 1 back `914.4 × 914.4 × 6`, in millimeters. A fresh saved-byte `validate_artifact_set(root, inspect_geometry=True)` passed all 15 artifact integrity records and native STEP/GLB checks: seven assembly solids, bounds `(0,0,0)` to `(914.4,304.8,914.4) mm`, zero solid overlap, three clear openings. Rough allowance is zero; the 3.2 mm saw kerf is a stock-layout setting. Construction method remains unselected. Reproduce the native read check from the repository with:

```powershell
.venv/Scripts/python.exe -c "from woodwork.cad_adapter.windows_runtime import configure_native_platform; configure_native_platform(); from woodwork.cad_adapter import validate_artifact_set; print(validate_artifact_set(r'C:/Users/byonk/AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/WoodworkingPlanner/app-development/artifacts/set_2f70abf514f741d9938013dc1bd2466d', inspect_geometry=True)['status'])"
```

Started 2026-10-12 (America/Chicago). Parent BoardPilot has an unborn main branch and an unrelated untracked `.omx/` directory, preserved. The application is a separate repository in `woodworking-platform`, branch `codex/woodworking-platform`.

The supplied consolidated plan is preserved under `handoff/`. The accompanying ZIP arrived during execution and is extracted under `handoff/package/woodworking-codex-handoff`. START-HERE, every referenced specification, schema and example has been read. All 27 indexed file sizes and SHA-256 values match PACKAGE-INDEX. The prose also matches the consolidated plan aside from titles/link targets. No fixture was reconstructed.

Native Windows is the selected path. Python 3.13.9, cadgen 0.7.21, build123d 0.11.1, OCP 7.9.3.1.1, Node v24.13.0 and Playwright 1.63.0 are installed and the native kernel loads. The `python` alias does not resolve to an interpreter; commands use the explicit `.venv/Scripts/python.exe`. No OS security settings were changed. Supporting Python and frontend dependency locks are recorded.

## Milestone gates: pending / in progress / passed / blocked

| Gate | Status | Evidence / remaining requirement |
|---|---|---|
| M0 workspace inspection | Completed | Empty parent checkout inspected; separate repository established; unrelated state preserved |
| M0 runtime and genuine CAD spike | Passed | Clean-directory STEP/GLB/native PDF/snapshot, saved measurement/units/axis/feature/winding, two-copy raycast/independent highlighting and resource observations recorded |
| Handoff read gate | Passed | All 27 files verify; actual schemas, inputs, expected ledger/cut trees read |
| M1 deterministic engine | Passed | All nine supplied projects generated and independently re-opened; current CLI produced a genuine coherent baseline through contained worker |
| M2 local editing workflow | Passed | Actual manual browser flows, cancellation, persisted drafts, native worker crash/retry and API kill/restart/retry passed |
| M3 documents / recipe | Passed | Nine genuine cumulative document cases passed; all 90 fixture pages and 16 compatible A4 pages rendered and visually reviewed; physical build review separate |
| M4 stock / costs | Passed | Exact supplied oracle, independent executable cut-tree replay, prices/pack arithmetic, nine cumulative exports and all 52 final stock pages checked |
| M5 proposals | Passed (offline) | Structured fake-provider review/apply, real native width revision, stale/hostile/timeout/idempotency checks and AI-disabled operation passed; live integration is excluded by the user's offline release choice (2026-10-14) |
| M6 local release | Passed (local software) | Actual offline setup/script launch, coherent full sample ZIPs, trusted import/rebuild, immutable recovery, credential isolation, option-only exports and cache independence passed |

## Completed work items and evidence

- Read all eleven sections of the supplied full plan, including architecture, geometry, CAD, API/jobs, exports/recipes, milestone sequence, acceptance tests, sources and fixture guide.
- Upstream pinned metadata confirms cadgen 0.7.21 at commit `24573128ceaab564f497d7c12f995c41784c9539`.
- Read pinned public STEP, saved-scene inspection and engineering-drawing API references. Public occurrence selectors are strings such as `#o1.2`; production mappings must be taken from actual saved scene reads.
- Installed user-local uv 0.9.8 and Python 3.13.9; pinned dependencies and matching Chromium installed.
- Clean-directory command `./diagnostics/m0/run.ps1` passed. Saved panel: 726 x 298.8 x 18 mm, volume 3,904,718.4 mm3; GLB bounds: 0.726 x 0.018 x 0.2988 m. Asymmetric 100 x 60 x 18 mm part retains an off-center 4 mm radius hole at CAD (20,10), mapping to viewer (0.02,-0.01) in X/Z. Two STEP copies retain `panel_left/#o1.1` and `panel_right/#o1.2` at centers -60/+60 mm.
- Native A4 landscape metric drawing and STEP snapshot generated and visually inspected; a clipped isometric label was repaired and re-rendered. Actual evidence and checksums are in `evidence/m0`.
- Clean probe elapsed times: panel 26.370 s, asymmetric 24.034 s, two occurrences 10.682 s, drawing 11.446 s, warm panel no-op 2.111 s. Separate cold-cache panel sampling: 24.385 s and 791,748,608 bytes peak summed process-tree RSS at 0.1 s sampling; concurrent development may affect timing. This is a measured observation, not a guaranteed memory ceiling.
- R3F raycast test passed after correcting screen coordinates to the actual rendered board extents. Each copy selects independently; final screenshot shows only panel_right highlighted. Frontend typecheck and production build passed; the initial viewer bundle size warning remains an optimization item for the manual application shell.
- GLB indexed triangle signed volume is positive and matches the saved panel volume within the recorded numeric threshold, confirming outward winding after the proper axis conversion.
- M1 native corpus: 23 originally collected tests passed in 854.86 seconds (14m14s). Current-code independent revalidation of every saved fixture passed in 18.506 seconds. `evidence/m1/corpus-evidence.json` records all nine actual spec/manifest hashes, measured solids, volumes, placements, openings, contacts and versions. Fast adapter regressions subsequently passed 17 cases; unrequested CAD cases are explicit skips in the ordinary test command.
- Current domain, CLI, runtime/unit, worker/metadata, SQLite state and native supervisor check: 93 tests passed. The supervisor now uses Windows 10+ atomic `PROC_THREAD_ATTRIBUTE_JOB_LIST` assignment at process creation, not an assign-after-spawn race. Real tests cover coordinator exit before resume, cancellation, deadline despite heartbeat, concurrent shutdown and bounded logs.
- Integrated `woodwork.cli build` generated a real current-format baseline using the contained worker and atomic non-replacing directory publication. Revision `rev_0ae673c07b0741f9bf3c26d0c57f3348`, artifact set `set_1da05ea2803547f0819a8be84f62c8f6`; output at the resolved local app-data sample directory. Representative metadata/CSV evidence is under `samples/bookcase-baseline` (full geometry remains in the sample output root until final packaging).
- API/storage checks: 10 passed for local Host/Origin/CSRF, exact normalization, malformed/oversized input rejection, create/draft/revision/reopen, stale conflict, idempotent jobs and queued cancellation. These checks do not yet establish the real browser/job/restart gate.
- M2 actual Chromium: fresh baseline→36 in width→restored 30 in width with 19 mm actual thickness→zero shelves→invalid input/reload passed in 4.6 min; separate exact units/keyboard/narrow viewport passed in 3.4 s; saved draft/reopen and real running-job cancellation preserved the prior actual model/CSV, including 390 px table/download access (6.2 s). M0 shared-GLB independent raycast also rechecked (1.8 s). Screenshots are under `apps/web/tests/evidence`.
- `diagnostics/recovery.py` passed in a new isolated native Windows store: killed real worker, API stayed available, prior set survived, next genuine build passed (92.403 s, peak sampled process-tree RSS 881,295,360 bytes). Killed/restarted API with active worker: job became interrupted, prior committed set survived, new genuine build passed (66.474 s, 879,820,800 bytes). Evidence is `evidence/m2/recovery-evidence.json`; unrelated local processes were preserved.
- M3 integration fast tests passed: null recipe preserves exact M1 ledger; compatible authored selection binds planned local station descriptors into manufacturing fingerprints and CSV descriptions; equal-sized boards with different face patterns split groups without changing physical IDs or geometry. CAD stays nominal finished blanks, with explicit planned-reference labeling. Core export provenance is now 1.2.0.
- Portable package/import test used the genuine immutable M1 baseline: exact ZIP payload inventory and SHA-256 verification passed; import created fresh local IDs and preserved original provenance, with no trusted preview before rebuilding. Traversal, drive paths, symlinks, executable/unexpected entries, duplicate entries, excess expansion and corrupted CSV were rejected. Application/package tests: 11 passed.
- Offline proposal backend: 13 passed for manual-equivalent width, questions/unsupported requests, malformed/forbidden/duplicate changes, stale/cross-project bases, reservation before provider call, uncertain timeout, one-time transactional apply and inert explanation data. No live provider call or credentials used. Browser gate is still pending.
- M3 genuine PDF corpus: nine cases passed in 100.91 seconds. All 90 Letter/native A4 pages rendered and visually inspected; separate compatible A4 sample adds 16 inspected pages. Exact PDF hashes, pages and review scope are in the app-data corpus's `corpus-evidence.json`. Selected sample revision `rev_a5ce69cef4f84c18bc2726bad98a575d`, geometry set `set_1761cfc031b0472a9404cbbc1180c6ce`, cumulative document set `set_f432d89056d742c7a10f9d3af9e1ec5f`. Its genuine CAD retry passed in 59.911 s / 880,693,248 bytes; document job passed in 13.110 s / 478,924,800 bytes. The first attempt rejected an internal/export construction-status enum mismatch; it published nothing, and that mapping now has a schema regression check.
- M4 pure planner: 40 tests passed, including the exact baseline cut tree, all nine projects, boundary kerfs, trim/rough allowance, grain restrictions, named unplaced parts, independent tamper replay, USD 95 synthetic subtotal and separate hardware-pack arithmetic. Stock plus domain final check: 112 passed in 1.97 s. Nine genuine cumulative stock export checks passed in 16.45 s. Persistent first-pass corpus rendered 53 stock pages and passed independent saved-PDF font/page-bound checks; final human-readable trim export 1.0.1 is being rendered/reviewed before its final gate.
- Fresh supported runtime verification: created `.verification/clean-runtime`, synchronized all 81 locked packages offline, installed the editable app with cached pinned setuptools 84.0.0, and loaded the OCP kernel. A separate clean frontend directory installed 151 locked packages offline and passed TypeScript/production build. Fresh native preflight initially timed out during overlapping browser CAD verification (120 s, no publication); the sequential retry passed in 67.6199 s, peak sampled process-tree RSS 879,316,992 bytes. Actual preflight output is retained outside the checkout.
- Review repaired database-publication recovery, cancel/restart intent, pre-publication worker identity checks and fake-provider numeric token parsing. A SQLite commit failure after actual filesystem rename now records recoverable `PUBLICATION_PENDING`; startup verifies/reconciles the genuine orphan. A cancelled renamed result stays cancelled on restart. Archive errors use bounded safe 400/413/422 results. Latest focused boundary tests: 45 passed; subsequent cancellation/receipt checks: 12 passed. Final complete backend/browser verification remains pending.
- New frontend hostile/stale/timeout/narrow UI check passed in 5.1 s. It exposed stale-draft save conflicts preventing reopen; the UI now retains the raw draft and loads the accepted revision. The long genuine PDF/pricing/proposal/ZIP/import/rebuild flow reached successful native outputs before an intentional test interruption, so the formal framework result remains open until its clean rerun.
- Final frontend evidence supersedes the interrupted run: six full M0/M2/M3–M6 cases passed in 8.5 min; four affected post-recovery-fix cases passed in 1.9 min. Production UI on port 8777 passed genuine GLB/CSV/PDF/stock/USD 95 checks with external browser requests blocked; inspected desktop/narrow captures waited for loaded real GLBs. Exact commands, IDs and screenshot SHA-256 values are in `apps/web/tests/evidence/frontend-acceptance.json`. Trusted import/rebuild produced fresh project/revision IDs and genuine CAD (60.851 s / 880,488,448 bytes).
- Final backend command passed **231 tests, 22 explicit regeneration skips, two warnings, 64.74 s**. Saved-byte package/import/recovery and all nine stock exports ran. The skipped checks are 13 native CAD regeneration and nine native document regeneration cases; their actual previously completed corpus runs are recorded separately. Warnings are the third-party Starlette/anyio alias and deliberate duplicate ZIP fixture; no failure remains.
- Actual option-only revisions passed: kerf-only native generation 60.027 s / 880,943,104 bytes; paper-only native generation 64.762 s / 881,168,384 bytes. Both preserve measured CAD dimensions while regenerating coherent revision metadata/layout/PDF/ZIP. `evidence/m6/export-options-evidence.json` binds the exact jobs/sets/bytes. Its synthetic-marker checks sampled workers and descendants, scanned 183 files/ZIP members/bundle content, and found no marker. Only the exact contained disposable CAD cache namespace (411 files) was removed/recreated; all 25 committed downloads and stored spec reopened afterward.
- Literal `./scripts/setup.ps1 -Offline` passed on final source: synchronized all 81 packages, rebuilt the editable app with pinned setuptools 84.0.0, verified Chromium, installed 151 frontend packages offline, and passed TypeScript/production build plus exact runtime-version reporting. `./scripts/launch.ps1 -DataRoot 'C:/Users/byonk/AppData/Local/WoodworkingPlanner/app-development'` started production UI/API on 8777; UI HTTP 200, database version 2, runtime ready, default AI disabled. The temporary synthetic marker was removed and the final service launched without it.
- Final sample folders `samples/reference-bookcase` and `samples/authored-bookcase` contain complete coherent 25-payload artifact sets and verified 26-entry ZIPs. Reference: original 18/6 mm baseline, Letter, unselected method. Authored: exact 19.05/6.35 mm / 14 in depth case, A4, technically checked method with physical review unrecorded. Original 16 authored pages and six final A4 stock pages inspected; 52 final fixture stock pages also inspected, with independent saved-PDF font/page bounds checks passed. Sample outer hashes are in `samples/export-evidence.json`.
- `docs/ACCEPTANCE-RESULTS.md` maps every original acceptance ID exactly once. All 112 local software checks have observed evidence. This does not assert a physical furniture build, structural capacity, live-provider verification, WSL support, deployment or public release.

## Exact setup, run, and verification commands

Commands run from `C:/Users/byonk/OneDrive/Documents/ChatGPT/BoardPilot`:

```powershell
git status --short
git log -3 --oneline
py -0p
node --version
npm --version
wsl -d Ubuntu -- bash -lc 'command -v python3; python3 --version; command -v uv; command -v node; node --version; command -v npm; uname -a'
py -3.14 -m pip install --user uv==0.9.8
py -3.14 -m uv python install 3.13
```

M0 reproduction (application repository cwd): `./diagnostics/m0/run.ps1`, `./.venv/Scripts/python.exe diagnostics/m0/profile.py`. Frontend diagnostic: `cd apps/web; npm ci; npm run dev -- --port 5173`, then `npm test -- tests/m0.spec.ts` and `npm run build`. M0 passed on native Windows; no WSL acceptance is claimed.

```powershell
# Application repository cwd. Native CAD corpus requires a new output root.
$env:WOODWORK_RUN_CAD_CORPUS='1'
$env:WOODWORK_CAD_CORPUS_ROOT='<new empty output directory>'
.venv/Scripts/python.exe -m pytest tests/test_cad_adapter.py -q -s
# Restore ordinary fast verification behavior after the explicit corpus run.
Remove-Item Env:WOODWORK_RUN_CAD_CORPUS -ErrorAction SilentlyContinue
.venv/Scripts/python.exe -m pytest tests/test_domain.py tests/test_process.py tests/test_cli.py tests/test_worker.py tests/test_storage.py tests/test_runtime_and_units.py -q
.venv/Scripts/python.exe -m woodwork.cli build tests/fixtures/bookcase-baseline.json --output '<new sample output directory>'
$env:WOODWORK_DATA_ROOT='C:/Users/byonk/AppData/Local/WoodworkingPlanner/app-development'
.venv/Scripts/python.exe -m uvicorn woodwork.api:create_app --factory --host 127.0.0.1 --port 8777
```

## Decisions and contract changes

Selected architecture remains React/TypeScript/Vite/R3F and Python 3.13/FastAPI/Pydantic/SQLite, with a pinned cadgen adapter. Actual material thickness, exact decimal inputs and immutable revisions are authoritative. AI follows the deterministic manual workflow. No contract deviations adopted.

CSV export 1.1.0 adds an optional `definition_ids` column after the 17 required columns. It identifies multiple semantic definitions in one interchangeable manufacturing group. This fixes a supported width=height+2t case where side/horizontal panels share a fingerprint; physical IDs and geometry assets stay separate. Older single-definition 17-column exports remain readable.

Core export 1.2.0 binds planned recipe operations to manufacturing fingerprints and explicit CSV descriptions. Stock export 1.0.1 provides human-readable cut/trim sequences and records all planner/validator/cost/exporter source hashes. Recipe data and source checks do not create machined CAD voids or a physical-review record. Historical coherent artifacts remain readable under their recorded versions.

The 18.000003 mm thickness regression produced 0.021513604805144637 mm3 of numerical contact overlap from one-time six-place center resolution. Only declared contact bands within the specified 0.000002 mm linear tolerance are allowed; actual overlap and the corresponding bound are reported, not labeled zero. Unrelated volumetric intersections still fail.

## Blocked gates: dependency, impact, independent work available

The handoff download dependency is resolved. All required local software gates have passed; no actionable local software requirement remains open.

Physical construction review has not been supplied or performed. Actual fabrication, drill/workholding access, shelf/service behavior and site installation need a recorded human review against the exact recipe/project fingerprints. No load rating is claimed.

The user explicitly chose to keep this release offline on 2026-10-14. Live-provider integration is intentionally excluded and is not implemented/configured/tested; no credential decision remains pending for this release. No real credentials were created, intentionally reused, written or exposed, and no paid provider call occurred. `/ai/status` reports live unconfigured; live requests return 503. The explicit fake-provider workflow is complete and ordinary forms/CAD/exports require no API key. WSL/Linux runtime acceptance remains unperformed; native Windows is the verified route.

## Next eligible work item and reproduction context

Local delivery is complete. The production service remains available at http://127.0.0.1:8777 using the verified development/sample store. Start another session with `docs/LAUNCH.md`, this status record and `docs/ACCEPTANCE-RESULTS.md`; preserve SQLite and immutable artifacts. Future optional live-provider or physical construction work requires the corresponding explicit user decision/evidence. No push, merge, deployment, purchase or operating-system security change occurred.

## Final reproduction commands

```powershell
# Repository cwd; prerequisites and equivalent non-script commands in docs/LAUNCH.md.
./scripts/setup.ps1             # First install/downloads
./scripts/setup.ps1 -Offline    # Prepared dependency/browser cache; actually verified
./scripts/preflight.ps1         # Real contained native baseline
./scripts/launch.ps1            # Production UI/API, http://127.0.0.1:8777
./scripts/dev.ps1 -Service api  # API in one terminal
./scripts/dev.ps1 -Service web  # Vite in another terminal, port 5173
./scripts/verify.ps1            # Backend plus type/production build
./scripts/demo.ps1              # Real production browser demonstration; several minutes

# Exact final backend run, including saved-byte gates, without regenerating native corpora.
$env:CADGEN_DAEMON='0'; $env:CADGEN_TELEMETRY='0'; $env:CADGEN_UPDATE_CHECK='0'
$env:WOODWORK_PACKAGE_SOURCE='C:/Users/byonk/AppData/Local/WoodworkingPlanner/m1-corpus/136753dd910c4c10a6f20f15bfbac7a4/bookcase-baseline'
$env:WOODWORK_DOCUMENT_SOURCE_ROOT='C:/Users/byonk/AppData/Local/WoodworkingPlanner/m3-documents/117e30a5123c420394d3e8b7018ef1fd'
.venv/Scripts/python.exe -m pytest -q
```

These copyable paths identify this machine's evidence. A fresh machine creates its own native corpus directories with the opt-in commands above. To reuse the currently verified populated store explicitly:

```powershell
./scripts/launch.ps1 -DataRoot 'C:/Users/byonk/AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/WoodworkingPlanner/app-development'
```
