# First local checkpoint review

Working goal (2026-10-17): review the existing application, resolve defects that
prevent a sound checkpoint, run fresh backend/build and real browser/native CAD
verification, inspect the full staged initial tree, then create the first local
Git commit on `codex/woodworking-platform`. Do not push or configure a remote.

Preserve the user's application data and unrelated parent `.omx` files. Keep the
selected Windows architecture, pinned CAD dependencies and offline behavior.
Verification uses a separate local store. Physical fabrication/installation and
live provider access remain outside the software checkpoint's acceptance scope.

Completion requires recorded review findings and resolutions, exact verification
commands/results, an inspected staged tree with no secrets/runtimes/database or
disposable packaging metadata, and a verified local commit with no remote push.

Recorded results from earlier dates do not substitute for this checkpoint's
fresh checks. The completed verification record and commit procedure are below.

## Review findings and repairs

The backend and CAD/domain/export reviews found no P0/P1 findings. Five P2
findings were reproduced and repaired before staging the checkpoint:

| Finding | Repair | Regression evidence |
| --- | --- | --- |
| PDF schedules ignored metric-only units and selected fraction precision. | Both schedule renderers use the revision's display policy. Native CAD sheets and exact stock coordinates remain metric. Renderer 1.1.0 provenance records the policy and formatter hash; older immutable output retains its historical validation contract. | Eleven real-PDF text/validator cases, including an adversarial unit mismatch and a legitimate project title containing `in (`. |
| Successful derived exports could falsely certify a failed CAD preflight. | Only an actual generation/probe promotes CAD preflight success. | Targeted job/publication protocol cases. |
| A timed-out explicit preflight could leave an old passing runtime record. | Persist a fresh failed preflight record with timeout diagnostics and measured process metrics. | Five new preflight evidence cases; related protocol tests also pass. |
| A failed optional project-list refresh could detach the opened project from generation tracking. | Keep the successfully opened project/reference and report the optional refresh failure separately. | Browser failure injection, then submission and live stage tracking. |
| Disabled browser storage prevented manual editing. | Cache operations are best effort; in-memory form state and server revisions remain authoritative. | Browser `SecurityError` injection, then manual creation/submission. |

The browser cases failed against the old implementation and passed after the
repairs. A second reviewer checked each repair outside its original ownership.
The pinned CAD adapter, deterministic geometry formulas, worker limits and
offline provider configuration were preserved.

## Verification environment

Tests use a separate store at
`C:/Users/byonk/AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/WoodworkingPlanner/checkpoint-review-20261017`.
The production bundle is served on 5173 with its API proxy pointing at isolated
8790. The recovery seed is saved genuine geometry, not a simulated CAD producer.
Browser tests which simulate transport failures are separate from real native
generation workflows.

During native verification the host repeatedly reported 95–100% CPU and as little
as 571 MB available RAM. Several real jobs reached the unchanged 120-second
deadline. These are failed timing gates, not successful native acceptance. No
limit or assertion was raised to obtain a passing report.

Independent test readers also exposed cadgen's default resident daemon policy.
`tests/conftest.py` now uses the application's daemon-free reader policy and
test-owned, lock-namespaced cache. Only verified test-owned daemon descendants
were stopped. No unrelated applications/processes were terminated. This harness
repair does not change the product's native process supervisor or its deadline.

## Git checkpoint hygiene

The application is its own repository on `codex/woodworking-platform`; the parent
workspace's unrelated `.omx` tree is excluded from this commit. No remote is
configured. The Git identity was already configured and was not changed.

`.gitignore` excludes runtimes, dependencies, databases/environment files, caches,
builds, test traces and disposable editable-install metadata. `.gitattributes`
protects supplied inputs, evidence, saved sample payloads and the pinned lock
from Windows line-ending conversion. Source files use LF on checkout.

An actual `git checkout-index` round trip initially checked 154 protected staged files,
all 27 handoff package-index entries and 50 payload records across the reference
and authored sample projects. Their bytes, sizes, hashes and ZIP inventories
match. The staged lock hash is
`f92cdecc61c68516333b8f210b9e6db3fd279659cfb0fcfc2b135dd3c06b2618`.
The staged-path/secret-pattern/ZIP-member audit passed. These checks are recorded
in `evidence/checkpoint-20261017/index-audit.json`.
The historical `samples/bookcase-baseline` directory contains only a metadata/CSV
snapshot, as the original status record explains. A local README now makes that
boundary explicit and points to the two complete sample ZIPs; its original
evidence was preserved.

First-party staged whitespace checks pass. The full-tree check reports preserved
Markdown hard breaks and final blank lines in immutable handoff/fixture files;
those source bytes were retained rather than rewriting supplied inputs. See
`evidence/checkpoint-20261017/staged-whitespace.json`.

## Verification record

The final canonical command passed after all five product fixes and the test
reader policy change: **258 passed, 22 skipped, two known warnings in 187.65 s**;
TypeScript and the production build passed (**55.08 s**, bundle
`index-B_PlvTYW.js`). Skips are 13 opt-in CAD and nine opt-in native document
regeneration tests, not additional passes. The warnings are Starlette's deprecated
AnyIO alias and the intentionally duplicated ZIP entry in a rejection test.
Vite retains its existing large-bundle advisory.

```powershell
$env:WOODWORK_PACKAGE_SOURCE='C:/Users/byonk/AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/WoodworkingPlanner/regeneration-verification-20261014-b/artifacts/set_4de8651be64c492dafb3955b499dacb1'
$env:WOODWORK_DOCUMENT_SOURCE_ROOT='C:/Users/byonk/AppData/Local/WoodworkingPlanner/m3-documents/117e30a5123c420394d3e8b7018ef1fd'
./scripts/verify.ps1
```

The genuine native corpus was run twice, with normal 120-second owned workers:
**29 passed / one timeout in 851.71 s**, then **23 passed / seven failures in
903.80 s**. The second result comprises four build timeouts plus three negative
cases whose baseline input was unavailable because that build timed out. The
first run's tampering, mixed-revision and material-overlap rejection cases passed;
the precision/contact case passed in both runs. The missing depth case passed on
a preserved-cache retry in **74.80 s**. Those first two attempts did not provide
a clean full timing pass. Their failures were retained for diagnosis; the final
serial run below completes this gate.
`evidence/checkpoint-20261017/native-attempts.json` records each saved worker
metric, failures as well as successes, and the nine checksum-verified output
locations. Failed staging directories were retained.

```powershell
$env:WOODWORK_RUN_CAD_CORPUS='1'
$env:WOODWORK_CAD_OWNED_CORPUS='1'
$env:WOODWORK_CAD_CORPUS_ROOT='C:/Users/byonk/AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/WoodworkingPlanner/checkpoint-cad-20261017'
.venv/Scripts/python.exe -m pytest tests/test_cad_adapter.py -q
# Second full run: same command, with checkpoint-cad-20261017-final as root.
# Retry: archive only the failed depth worker directory within the first root,
# preserve its cache, then select its exact test node:
.venv/Scripts/python.exe -m pytest 'tests/test_cad_adapter.py::test_genuine_cad_fixture_corpus[bookcase-depth-14in.json]' -q
```

Focused production-browser checks passed **nine tests**, with the optional
five-build regeneration scenario skipped. They cover the two new regression
cases, raycast selection of two genuine GLB copies, and six simulated
timeout/reconnect/lost-response/refusal scenarios. This is a focused browser run,
not a rerun of the full M0–M6 browser suite. Historical evidence remains separate.
Run from `evidence/checkpoint-20261017/browser-run` to preserve old screenshots:

```powershell
$env:WOODWORK_TEST_URL='http://127.0.0.1:5173'
& 'C:/Program Files/nodejs/node.exe' 'C:/Users/byonk/OneDrive/Documents/ChatGPT/BoardPilot/woodworking-platform/apps/web/node_modules/@playwright/test/cli.js' test checkpoint-regressions.spec.ts m0.spec.ts regeneration.spec.ts --config 'C:/Users/byonk/OneDrive/Documents/ChatGPT/BoardPilot/woodworking-platform/apps/web/playwright.config.ts' --grep-invert '^genuine width' --trace on
```

The user's walkthrough was checked through a read-only SQLite connection.
Project identity, accepted revision 2, raw draft, preferred export set and manifest
hash match the saved snapshot. All 19 payload hashes/sizes match. It is still
**36 × 36 × 12 in**, two shelves, measured 18/6 mm plywood. See
`evidence/checkpoint-20261017/preserved-walkthrough.json`.

Real API export checks passed for metric-only schedules and dual schedules with
sixteenth-inch precision, including the legitimate project title
`Checkpoint units in (garage)`. Each case independently inspected saved native
geometry, checked its revision-bound design/native/stock PDFs and cut-tree
replay, verified the complete 26-payload ZIP, and confirmed derived exports left
the CAD probe record unchanged. The generation/document/stock/package times were
**90.344 / 63.548 / 8.779 / 4.865 s** for metric and
**17.404 / 21.496 / 4.400 / 3.553 s** for dual units.

All **32 PDF pages** rendered successfully and were visually inspected by the
agent in eight contact sheets: 14 design pages, six genuine native metric A4
drawings and 12 stock/cut-sequence pages. Labels and tables are legible and
unclipped. Poppler emitted nonfatal rendering warnings. This is software/agent
visual evidence; physical fabrication and load/installation review remain open.
See `evidence/checkpoint-20261017/export-retry/export-options.json`, the two
`checkpoint-*.zip` files beside it, and `pdf-render-mm.json`/`pdf-render-dual.json`.

The first fresh API generation attempt timed out at 120.064 s while the host was
under load; its failed job remains in `export-jobs.json` in the checkpoint root.
On retry the real generation passed. The diagnostic then encountered a race in
its own assumption that optional runtime metadata was already written as soon as
the artifact/job transaction published. It now waits briefly for that file and
can resume its exact unchanged disposable metric project, reusing its successful
job rather than claiming a new generation. No product deadline was changed.

```powershell
.venv/Scripts/python.exe diagnostics/checkpoint_exports.py --api http://127.0.0.1:8790/api/v1 --data-root 'C:/Users/byonk/AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/WoodworkingPlanner/checkpoint-review-20261017' --output evidence/checkpoint-20261017/export-options.json
# Retry output is in export-retry; resume the successful unchanged metric project:
.venv/Scripts/python.exe diagnostics/checkpoint_exports.py --api http://127.0.0.1:8790/api/v1 --data-root 'C:/Users/byonk/AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/WoodworkingPlanner/checkpoint-review-20261017' --project-id project_49dcd3ed58704a898f7a2c099168fb98 --output evidence/checkpoint-20261017/export-retry/export-options.json
```

The three M2 browser workflows passed in **2.2 minutes**, including four genuine
baseline/width/measured-thickness/shelf-count builds, selection/hide/isolate,
matching CSVs, reopening, draft recovery, invalid measurements, narrow layouts
and cancelling a real worker without changing prior downloads. Desktop and
narrow screenshots were also inspected.

The opt-in regeneration browser workflow passed five genuine builds at
**15.514 / 14.602 / 47.226 / 34.014 / 17.759 s**. Each model, CSV, complete
seven-panel stock plan and newly published stock PDF matched its accepted
revision. Cancellation took **1.593 s**, preserved prior CSV/stock links and was
followed by a successful retry. Its JSON and screenshots are under the new
checkpoint's `browser-run/tests/evidence`, preserving earlier evidence.

The wider browser run exposed two stale assumptions in `showAuthored`: requiring
a deliberately hidden duplicate heading, and checking for a temporary Revert
button before form revalidation finished. The test now waits for actionable form
controls and checks the visible summary's accepted state plus absence of draft
status. Its conditional Revert click has a bounded five-second timeout. No
product style, meaningful downstream assertion or native deadline was bypassed.
The initial three failures and interrupted first retry are retained in
`browser-initial-failures.json`; full initial failure traces are in the recorded
local app-data archive. The final rerun uses the already generated genuine
authored fixture through the test's existing supported fixture-path option.

The M3–M6 rerun passed authored method/PDF, incompatible-recipe, offline width
proposal, priced-stock, ZIP import/rebuild, stale-draft and desktop/narrow output
checks. Its hostile-text case exposed a third test-harness issue: it injected only
the POST response, which the panel's normal GET-by-ID refresh replaced. The test
now injects both response paths and requires two injections before checking
inert text, absence of image elements and absence of script execution. That
focused retest passed in **6.8 s**. Stale proposals still cannot apply, and the
offline timeout leaves manual editing available. The broad rerun was **three
passed / one injection-fixture failure in 3.6 minutes**, followed by **one passed**
on that corrected case. All **17 distinct browser cases** have fresh passing
results across these focused commands/reruns; this is not a claim of one clean
17-case invocation. The final strict TypeScript check passed in **5.16 s** after
all harness changes. Product code and the tested production bundle did not
change during these harness repairs.

Browser commands below use the same `browser-run` cwd and absolute CLI/config
paths shown earlier. The existing supported authored fixture option points to
actual successful native jobs in the isolated store; it falls back to creating a
new genuine project when that local fixture is absent.

```powershell
$env:WOODWORK_TEST_URL='http://127.0.0.1:5173'
$env:WOODWORK_PRODUCTION_URL='http://127.0.0.1:5173'
$env:WOODWORK_RUN_REGENERATION_FLOW='1'
$cli='C:/Users/byonk/OneDrive/Documents/ChatGPT/BoardPilot/woodworking-platform/apps/web/node_modules/@playwright/test/cli.js'
$config='C:/Users/byonk/OneDrive/Documents/ChatGPT/BoardPilot/woodworking-platform/apps/web/playwright.config.ts'
& 'C:/Program Files/nodejs/node.exe' $cli test m2.spec.ts --config $config --trace on
& 'C:/Program Files/nodejs/node.exe' $cli test m3-m6.spec.ts regeneration.spec.ts --config $config --grep 'authored method|hostile proposal|stale draft|production port|genuine width' --trace on
$env:WOODWORK_AUTHORED_SAMPLE_PATH='C:/Users/byonk/OneDrive/Documents/ChatGPT/BoardPilot/woodworking-platform/evidence/checkpoint-20261017/authored-fixture.json'
& 'C:/Program Files/nodejs/node.exe' $cli test m3-m6.spec.ts --config $config --trace on
& 'C:/Program Files/nodejs/node.exe' $cli test m3-m6.spec.ts --config $config --grep 'hostile proposal' --trace on
# Final types, in apps/web:
& 'C:/Program Files/nodejs/node.exe' node_modules/typescript/bin/tsc --noEmit
```

## Final native and checkpoint gates

After all browser jobs finished, both verification services were stopped and
their ports confirmed closed. At serial-run startup the observed host CPU was
65% and available memory 2089 MiB. The final **full native corpus passed all
30 cases in 263.25 s**, including all 13 opt-in native cases. All nine fresh
owned fixture builds passed with the unchanged 120-second limit; times were
**12.573–32.895 s**. Tampered bytes, mixed-revision CSVs and real saved material
overlap were rejected, and supported precision/contact bands passed. The earlier
overload failures remain recorded rather than being erased by this successful
run. No operating-system security setting, model geometry, pin, assertion or
worker deadline was relaxed.

```powershell
$env:WOODWORK_RUN_CAD_CORPUS='1'
$env:WOODWORK_CAD_OWNED_CORPUS='1'
$env:WOODWORK_CAD_CORPUS_ROOT='C:/Users/byonk/AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/WoodworkingPlanner/checkpoint-cad-20261017-serial'
.venv/Scripts/python.exe -m pytest tests/test_cad_adapter.py -q --junitxml "$env:WOODWORK_CAD_CORPUS_ROOT/pytest-results.xml"
```

Nine native document-corpus regenerations were not repeated. The fresh real
unit-option jobs, authored browser PDFs and 32 rendered/reviewed pages are the
current document evidence; old nine-fixture document evidence remains dated as
such. Physical construction/load/site-installation, human accessibility
validation and release approval remain separate. Live AI stays intentionally
disabled. These are not claims of physical or release readiness.

The first local Git commit contains the reviewed application, immutable handoff,
complete reference/authored samples, tests, documentation and verification
evidence on `codex/woodworking-platform`. The final staged tree is audited before
committing; its exact commit ID is reported by Git and in the completion message.
No remote is configured and no push is performed. The parent workspace remains
uncommitted, with its unrelated `.omx` files preserved.

```powershell
git diff --cached --check -- . ':(exclude)handoff/**' ':(exclude)samples/**' ':(exclude)tests/fixtures/**'
git commit --quiet -m 'feat: add local woodworking design application'
git log -1 --format='%h %s'
git status --short
```
