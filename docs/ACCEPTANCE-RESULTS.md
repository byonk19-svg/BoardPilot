# Acceptance results

This ledger maps all **112 original IDs** in `handoff/package/woodworking-codex-handoff/docs/ACCEPTANCE-TESTS.md` to observed evidence. It records the native Windows implementation; WSL/Linux acceptance is not claimed. A passed software check does not establish a physical furniture build, service load, installation suitability, assistive-technology evaluation, or a live-provider test.

Snapshot: 2026-10-13, after native export-options/credential/cache verification, complete browser flows, offline setup, production launch and final status/sample reconciliation. **All 112 local software checks passed at the stated evidence layers.** No check remains partial or pending. These states are based on actual results, rather than the presence of test code. Physical construction remains unreviewed. Live-provider integration is intentionally excluded by the user's offline release choice confirmed on 2026-10-14.

## Commands and evidence references

All commands run from `C:/Users/byonk/OneDrive/Documents/ChatGPT/BoardPilot/woodworking-platform` unless a frontend directory is specified. A `tests/...::test_name` reference below identifies the concrete check in command **T**; parametrized cases share that function.

| Ref | Executed command / scope | Result and durable evidence |
|---|---|---|
| T | Complete backend command below | Final complete run: **231 passed, 22 skipped, 2 warnings in 64.74 s**, exit 0, including all six diagnostic guardrails. All saved-byte package/import/publication recovery and nine cumulative stock-export cases ran. Skips are 13 opt-in native CAD regeneration cases and nine native document regeneration cases; their genuine prior corpus evidence is separate. Warnings are the Starlette/anyio deprecated alias and the deliberately duplicated ZIP member fixture. |
| M0 | `./diagnostics/m0/run.ps1`; `.venv/Scripts/python.exe diagnostics/m0/profile.py` | Genuine clean-directory STEP, GLB, native PDF and snapshot; saved dimensions, feature position, unit/axis conversion, winding and runtime versions. `evidence/m0/probe-evidence.json`, `timings.json`, `profile.json`, `verify-run.log`, PDF/PNG files. |
| G | Opt-in `.venv/Scripts/python.exe -m pytest tests/test_cad_adapter.py -q -s` with `WOODWORK_RUN_CAD_CORPUS=1` and a fresh output root; subsequent independent reopening of all nine saved sets | Initial genuine run: 23 passed in 854.86 s. Independent current-code reopening: nine passed in 18.506 s. `evidence/m1/corpus-evidence.json` binds exact spec/manifest hashes, solids, occurrences, measured sizes, openings, contacts and volumes. |
| M2 | In `apps/web`: `npm.cmd test -- tests/m2.spec.ts`; `npm.cmd test -- tests/m0.spec.ts` | Genuine manual baseline/36 in/19 mm/zero-shelf/invalid/reopen flow passed in 4.6 min; unit/keyboard/narrow check 3.4 s; persisted-draft/running-worker cancel check 6.2 s; genuine shared-GLB raycast 1.8 s. These paths also passed the final full collection and affected post-fix regressions in UI5. `apps/web/tests/evidence/m2-*.png`; `evidence/m0/viewer-selection.png`. |
| REC | `.venv/Scripts/python.exe diagnostics/recovery.py --source '<genuine baseline directory>' --output '<new recovery directory>'` | Actual native worker kill then successful retry, API kill/restart then successful retry, owned process-tree exit and prior set retention: `evidence/m2/recovery-evidence.json`. Retry elapsed/RSS: 92.403 s / 881,295,360 bytes and 66.474 s / 879,820,800 bytes. |
| DOC | Opt-in `.venv/Scripts/python.exe -m pytest tests/test_documents.py -q -s` with `WOODWORK_RUN_DOCUMENT_CORPUS=1`, verified geometry source and fresh document root | Nine genuine cumulative cases passed in 100.91 s. All 90 fixture pages and 16 compatible authored A4 pages rendered and visually reviewed. `evidence/m3/corpus-evidence.json`, `document-validation.json`, `manifest.json`, `construction-recipe.json`. |
| STK | `.venv/Scripts/python.exe -m pytest tests/test_stock.py -q`; nine saved-source `tests/test_stock_exports.py` cases also in T; `diagnostics/stock_corpus.py` final 1.0.1 exports | 40 pure planner/independent replay tests passed; nine cumulative genuine-byte export cases passed. Final `evidence/m4/corpus-evidence.json` records 52 rendered stock pages and all nine visual reviews passed; `evidence/m4/pdf-bounds-evidence.json` has no bounds/font findings. The 53-page first pass is retained as earlier evidence only. |
| UI5 | Browser commands below | Full six-test M0/M2/M3–M6 collection passed in 8.5 min, including genuine PDF/stock/fake proposal/ZIP/import/trusted rebuild. After the final draft/recovery fix, four affected cases passed in 1.9 min, including fallback creation of a fresh authored project and native CAD/PDF. Production output case passed on port 8777 with non-loopback browser requests aborted; final loaded-GLB screenshot rerun passed in 3.5 s. `apps/web/tests/evidence/frontend-acceptance.json` records exact commands, IDs, hashes, results and eight inspected screenshots. |
| CLEAN | `./scripts/setup.ps1 -Offline`; `./scripts/launch.ps1 -DataRoot 'C:/Users/byonk/AppData/Local/WoodworkingPlanner/app-development'`; fresh pinned environment/native preflight | Actual final-source offline setup completed Python locks/editable install with pinned setuptools, prepared Chromium check, npm locked install/build and runtime versions. Documented production script started PID 25024; UI returned 200, API/runtime ready, AI disabled. Separate fresh environment synchronized all 81 Python packages, clean frontend installed 151 locked packages and passed TypeScript/build; genuine preflight passed in 67.6199 s / 879,316,992 bytes. `evidence/m6/clean-preflight-manifest.json`; production browser evidence in UI5. |
| SUP | Supplemental pure acceptance command below | Exact bare-unit case, repeated display-unit changes, specified t=25/H=100.000001/count=2 collapse case, all five public modeling fields at both bounds and immediately outside (20 cases), and exact 2→1→0→2 stable-slot sequence passed. These assertions are additional to the backend suite count. |
| OPT | `diagnostics/export_options.py` actual command below | J14/A08/B08 passed with genuine jobs under the 120 s profile. `evidence/m6/export-options-evidence.json`: kerf-only r5 and paper-only r6, original r1 immutable, 183 files/ZIP members scanned, live worker/descendant environments sampled, 411 disposable cache files removed/recreated safely, source and 25 committed downloads reopened with cache still empty. |

Complete backend command **T**, including real immutable source bytes and no native regeneration:

```powershell
$env:CADGEN_DAEMON='0'
$env:CADGEN_TELEMETRY='0'
$env:CADGEN_UPDATE_CHECK='0'
$env:WOODWORK_PACKAGE_SOURCE='C:/Users/byonk/AppData/Local/WoodworkingPlanner/m1-corpus/136753dd910c4c10a6f20f15bfbac7a4/bookcase-baseline'
$env:WOODWORK_DOCUMENT_SOURCE_ROOT='C:/Users/byonk/AppData/Local/WoodworkingPlanner/m3-documents/117e30a5123c420394d3e8b7018ef1fd'
Remove-Item Env:WOODWORK_RUN_CAD_CORPUS,Env:WOODWORK_RUN_DOCUMENT_CORPUS -ErrorAction SilentlyContinue
.venv/Scripts/python.exe -m pytest -q
```

Supplemental exact cases **SUP** were executed without CAD or source changes:

```powershell
$acceptanceProbe=@'
from woodwork.domain import DomainError, MODELING_BOUNDS, compile_project, exact_decimal, normalize_measurement
from woodwork.templates import default_project_spec
from fractions import Fraction
assert normalize_measurement('18','mm')=='18' and normalize_measurement('18','in')=='457.2'
try: normalize_measurement('18')
except DomainError: pass
else: raise AssertionError('missing default accepted')
spec=default_project_spec();spec['materials']['main']['actual_thickness_mm']='25';spec['dimensions']['outside_height_mm']='100.000001';spec['dimensions']['fixed_shelf_count']=2
try: compile_project(spec)
except DomainError as error: assert 'RESOLVED_FEATURE_COLLAPSED' in {f['code'] for f in error.findings}
else: raise AssertionError('positive sub-resolution gap accepted')
checked=0
for field,(minimum,maximum) in MODELING_BOUNDS.items():
    for value,accepted in ((str(minimum),True),(str(maximum),True),(exact_decimal(Fraction(minimum)-Fraction('0.000001')),False),(exact_decimal(Fraction(maximum)+Fraction('0.000001')),False)):
        spec=default_project_spec();target=spec;segments=field.split('.')
        for segment in segments[:-1]:target=target[segment]
        target[segments[-1]]=value
        try: compile_project(spec)
        except DomainError as error:
            assert not accepted,(field,value,error.findings)
            assert 'MODELING_BOUND_EXCEEDED' in {f['code'] for f in error.findings},(field,value,error.findings)
        else:assert accepted,(field,value)
        checked+=1
baseline=compile_project(default_project_spec())
for count in (2,1,0,2):
    spec=default_project_spec();spec['dimensions']['fixed_shelf_count']=count;actual=compile_project(spec)
    assert [i['instance_id'] for i in actual['part_instances'] if i['instance_id'].startswith('shelf_')]==[f'shelf_{n:02d}' for n in range(1,count+1)]
for unit in ('mm','in','mm','in'):
    spec=default_project_spec();spec['display']['preferred_unit']=unit;actual=compile_project(spec)
    assert all(actual[key]==baseline[key] for key in ('geometry_sha256','part_definitions','part_instances'))
print(f'Supplemental exact acceptance probes passed: U06, U07, U14, U15 ({checked} boundary cases), G14.')
'@
.venv/Scripts/python.exe -c $acceptanceProbe
```

Saved corpus roots are local evidence, not a requirement to regenerate CAD on every ordinary test run. M0/G/DOC commands perform real CAD work and should run sequentially with a new output root. Numeric checks use exact source hashes, exact fixture arithmetic, six-place HALF_EVEN resolved values, 0.000002 mm resolved-contact comparison, and the documented saved-kernel dimension/volume thresholds. The supported 18.000003 mm contact regression reports its measured 0.021513604805144637 mm³ overlap inside declared quantization bands; it does not describe that value as zero.

## Runtime and adapter — 10 checks

| ID | Status | Observed result / exact check |
|---|---|---|
| R01 | Passed | M0 + CLEAN: Python 3.13.9, cadgen 0.7.21, build123d 0.11.1, OCP 7.9.3.1.1, Node 24.13.0; native kernel loaded. Pinned cadgen commit recorded in launch/status docs. |
| R02 | Passed | M0: genuine saved panel STEP/GLB reopened; 726×298.8×18 mm and corresponding meter bounds recorded. |
| R03 | Passed | M0: actual snapshot PNG and native drawing PDF generated, rendered and inspected; renderer failure is an error. DOC adds genuine project drawings. |
| R04 | Passed | M0 asymmetric 100×60×18 mm part: radius-4 hole at CAD (20,10) retained at viewer X/Z (0.02,-0.01), with proper handedness/winding. |
| R05 | Passed | M0: 100 mm asymmetric part measures 0.1 m in GLB; panel bounds separately catch a second scale conversion. |
| R06 | Passed | M2 `m0.spec.ts`: raycasts select each same-colored genuine GLB copy independently; screenshot highlights only `panel_right`. |
| R07 | Passed | G: every saved assembly occurrence is mapped exactly once; saved labels and sidecar assembly artifact ID/hash verified in all nine sets. |
| R08 | Passed | G: each changed project saves/reopens its own STEP and hash-bound occurrence map; stale/mixed map identity fails adapter validation. |
| R09 | Passed | UI5 + CLEAN: prepared local CAD/forms/documents/stock workflow passed with non-loopback browser requests aborted and live AI unconfigured/disabled; production same-origin outputs remain usable. This is the observed browser network boundary, not a machine-wide air-gap claim. |
| R10 | Passed | T `test_runtime_and_units.py::test_blocked_native_kernel_explains_supported_fallback`: mocked OCP load refusal gives actionable native/WSL guidance; security remains unchanged. M0 proves actual selected native path. |

## Units and input semantics — 16 checks

| ID | Status | Observed result / exact check |
|---|---|---|
| U01 | Passed | T `test_domain.py::test_supplied_parser_acceptance`: every supplied valid input case matches the exact canonical mm string. |
| U02 | Passed | Same supplied/parser tests: `3/4 in` and `0.75 in` both equal `19.05`. |
| U03 | Passed | Same supplied/parser tests retain `1/64 in = 0.396875 mm` exactly. |
| U04 | Passed | T `test_parser_rejects_invalid_input_without_evaluation_or_rounding`: excess raw precision rejected; no rounding to a plausible input. |
| U05 | Passed | Same test plus API boundary: zero/disallowed denominator, nonfinite, negative and code-like text reject before worker output exists. |
| U06 | Passed | SUP exact bare 18 resolves to 18 or 457.2 mm only with explicit defaults; missing default rejects. T normalization/API tests and M2 use explicit defaults. |
| U07 | Passed | SUP repeated mm/in toggles preserve definitions/instances/geometry hash; M2 canonical display-switch browser check preserves raw dimensions. |
| U08 | Passed | T `test_nominal_metadata_does_not_override_measurements`: nominal label changes full metadata hash while finished geometry and geometry identity remain unchanged. |
| U09 | Passed | T complete arithmetic/nominal-measurement checks: actual 19.05 mm gives horizontal 723.9 mm and target gap 279.4 mm. Authored genuine M3 set retains 19.05 mm. |
| U10 | Passed | T `test_runtime_and_units.py::test_dual_units_convert_actual_measurement_and_mark_approximation`: approximate fraction is labeled, 726 mm retained; DOC packets and immutable project exports preserve canonical source. |
| U11 | Passed | T unsupported-contract/schema tests, duplicate/FK tests, API unknown worker/request properties: structured field/version errors, no silent acceptance. |
| U12 | Passed | T `test_supplied_semantic_errors` plus M2 impossible-width flow: positive inside dimensions required before any native job; prior successful model retained. |
| U13 | Passed | T `test_shelf_count_is_strict_integer` and complete nine-fixture oracle: -1/1.5/5 reject; 0–4 accepted and genuinely generated. |
| U14 | Passed | SUP specified t=25 mm/n=2/H=100.000001 mm rejects `RESOLVED_FEATURE_COLLAPSED`; T derived precision/collapse regression independently passes. |
| U15 | Passed | SUP 20 cases: all five public modeling fields accept min/max and reject 0.000001 mm beyond either bound, independently of recipe status. T contract/bounds regressions pass. |
| U16 | Passed | T `test_derived_half_even_and_precision_collapse`: internal ties resolve to 18 and 18.000002; raw ties remain invalid inputs. |

## Reference geometry and changes — 16 checks

| ID | Status | Observed result / exact check |
|---|---|---|
| G01 | Passed | T full independent oracle + G baseline: three definitions, seven physical instances, four horizontal panels. |
| G02 | Passed | G saved STEP/GLB definitions: sides 914.4×298.8×18, horizontals 726×298.8×18, back 914.4×762×6 mm. |
| G03 | Passed | G saved assembly: min (0,0,0), max (762,304.8,914.4) mm. |
| G04 | Passed | T exact oracle + G measured openings: three 726×298.8×280.8 mm gaps; centers 307.8 and 606.6 mm. |
| G05 | Passed | G individually counted saved solids total 29,635,528.32 mm³ within recorded saved-kernel threshold. |
| G06 | Passed | T independent corner/rotation/grain test + G saved transforms: orthogonal proper rotations, determinant +1, correct local grain, no reflected side. |
| G07 | Passed | G intended contacts verified; genuine deliberate saved overlap rejects. Quantized contact exception remains limited to declared contact bands. |
| G08 | Passed | G width fixture: 878.4 mm horizontals, 914.4×914.4 back, unchanged side dimensions; M2 actual edit shows 878.4. |
| G09 | Passed | G thickness fixture + M2: horizontal 724 mm, exact 4192/15 gap, resolved centers 307.966667/606.433333 mm. |
| G10 | Passed | G depth fixture: main depth 349.6 mm; back Y center 352.6; back face unchanged. |
| G11 | Passed | G back-thickness fixture: main depth 295.8 mm, back center Y 300.3, outside depth 304.8 mm. |
| G12 | Passed | G zero-shelf fixture + M2 genuine viewer: five panels, two horizontals, one 878.4 mm opening. |
| G13 | Passed | T full oracle + G one/three/four-shelf saved solids, centers, openings and volume tables. |
| G14 | Passed | SUP exact 2→1→0→2 named slots remain stable; T `test_grain_rotation_and_slot_stability` adds 4→1→0→2→4; M2 count edit/reopen loads genuine five-panel zero case. |
| G15 | Passed | T `test_application.py::test_equal_size_boards_different_local_face_patterns_split_manufacturing_groups`: machining distinguishes equal-size boards while physical IDs remain correct. |
| G16 | Passed | T genuine-byte `test_publication_recovery.py::test_injected_saved_geometry_inspection_exception_cannot_publish`: inspection exception fails job, produces no successful result and preserves prior preferred set. |

## Revision, persistence and worker recovery — 18 checks

| ID | Status | Observed result / exact check |
|---|---|---|
| J01 | Passed | M2 persisted browser project/draft reopening + REC actual API restart: unchanged accepted spec/IDs/history and prior genuine artifacts available. |
| J02 | Passed | M2 edits leave prior model labeled last successful while raw draft/build state differs; failure/cancel retains its downloads. |
| J03 | Passed | T `test_storage.py::test_late_result_stays_historical_and_cumulative_capabilities_do_not_downgrade`: injected reversed metadata publications retain r2 current and r1 historical; no parallel CAD added. |
| J04 | Passed | G mixed-revision CSV regression and T genuine ZIP corrupted-CSV import test reject incoherent sources/checksums; worker spec/ledger mismatch rejects before CAD. |
| J05 | Passed | T storage/API queue idempotency: identical request/key returns one job ID; no second worker. |
| J06 | Passed | T `test_queue_idempotency_capacity_cancel_and_restart`: same key with changed source/request gives 409. |
| J07 | Passed | T API and storage CAS tests: stale accepted base gives 409 and leaves immutable prior records intact. |
| J08 | Passed | T queued/running/cancel-restart state checks, real Windows descendant cancellation within five seconds, M2 real running CAD cancel: no partial publication or unrelated process termination. |
| J09 | Passed | REC real native worker killed: API available, safe failed state, prior set intact, next genuine job succeeds; T native crash-descendant cleanup adds focused coverage. |
| J10 | Passed | T `test_process.py::test_heartbeat_cannot_extend_wall_clock_deadline`: busy child/descendant heartbeat cannot prevent owned-tree timeout. |
| J11 | Passed | REC actual active API kill/restart: owned children exit, job interrupted, prior genuine artifacts survive and retry succeeds; T abrupt coordinator before-resume/after-spawn cases. |
| J12 | Passed | T actual-byte `test_real_rename_then_sqlite_commit_failure_recovers_on_restart`: SQLite failure after final rename records `PUBLICATION_PENDING`, startup verifies/reconciles receipt exactly once. |
| J13 | Passed | T API/storage terminal cancel repeated: same cancelled terminal response, no state regression; cancelled orphan cannot publish after restart. |
| J14 | Passed | OPT actual kerf-only r5 generate+stock, then only-paper r6 generate+documents+stock+ZIP. Definitions/world poses/geometry hash unchanged; new CSV/spec/layout/PDF hashes and revision headers coherent; original r1 sets immutable. |
| J15 | Passed | T immutable CAS parent/history checks + M2 restored width/main thickness sequence: later revisions contain restored values without modifying earlier source records. |
| J16 | Passed | T bounded queue capacity: one claimed worker plus ten queued jobs; further request returns 429 and existing revision remains valid. |
| J17 | Passed | DOC + T all nine genuine cumulative stock exports retain assembly/definition STEP+GLB, current occurrence sidecar and core files; T metadata protocol prevents subset capability downgrade. |
| J18 | Passed | T delayed source-publication storage case freezes package source at queue time; genuine package inventory/checksum test verifies selected manifest and bytes. UI5 + OPT completed selected-set ZIP export and validated package contents. |

## Documents and construction completeness — 14 checks

| ID | Status | Observed result / exact check |
|---|---|---|
| D01 | Passed | DOC all nine null-recipe design packets accurately declare recipe unselected, retain actual measured drawing/cut-list values and no fabricated construction method. |
| D02 | Passed | M0 native metric PDF, T exact `25.4 mm → 1 in` formatter tests and DOC searchable conversion captions/native metric labels. |
| D03 | Passed | DOC width-36 packet/native sheets and CSV bind the changed spec/revision/ledger; 878.4 mm value verified. |
| D04 | Passed | DOC text/value/provenance extraction plus actual review of every rendered fixture page and 16 authored A4 pages; original clipped M0 label repaired and re-rendered. |
| D05 | Passed | DOC measured PDF media boxes and page declarations: Letter application corpus, native A4, authored A4 application case. |
| D06 | Passed | T recipe unknown rejects, actual 18 mm reference remains valid/incompatible rather than promoted; authored compatible genuine M3 set separate. UI5 actual incompatible geometry/documents and separate complete authored method passed. |
| D07 | Passed | T `test_recipe_graph_fails_actionably[missing]`: completeness false with named `JOINT_MISSING`. |
| D08 | Passed | Same graph tests `[cycle]`/`[part]`: operation cycle and missing part reject actionably. |
| D09 | Passed | T joint-derived complete authored method: 14 required joints, 24 pocket screws, 32 brads, stable operation dependencies/stations; DOC genuine selected packet and source-backed review. |
| D10 | Passed | T recipes/doc layout + DOC authored set report `physical_review=not_reviewed`/physical review pending despite technical completeness. No physical construction is claimed. |
| D11 | Passed | T recipe graph `[finish]` rejects missing finishing operation with rough allowance; domain/stock tests retain finished geometry and expose larger rough blanks independently. |
| D12 | Passed | T `test_cad_adapter.py::test_spreadsheet_formula_neutralization` and CSV exact-column/measured-thickness test: formula-like text inert, numeric dimensions unchanged. |
| D13 | Passed | T authored packet layout text verifies `not a native section/detail view`; DOC diagrams are explicitly reference illustrations on nominal unmachined CAD blanks. No unsupported native section/detail capability is advertised. |
| D14 | Passed | T `test_recipes.py::test_synthetic_recipe_absent_from_production_catalog`: test-only complete graph runs only via injected catalog, absent from ordinary user catalog. |

## Stock layouts and costs — 16 checks

| ID | Status | Observed result / exact check |
|---|---|---|
| S01 | Passed | T `test_full_baseline_stock_oracle_and_independent_cut_replay`: full supplied placements/cut trees, one main + one back sheet, 10 mm trim/3.2 mm kerf. |
| S02 | Passed | Same full oracle independently replays nine main cuts and exact areas: parts 1,414,160.64; kerf 28,968.96; offcuts 1,460,870.4 mm². |
| S03 | Passed | Same oracle independently replays two back cuts: parts 696,772.8; kerf 10,182.4; offcuts 2,197,044.8 mm². |
| S04 | Passed | Same full oracle: each usable area 2,904,000 mm² plus 72,800 mm² reserved trim restores original sheet area. |
| S05 | Passed | T `test_exact_fit_has_two_kerfs_and_no_trailing_release`: supplied 306.4×100 mm exact-fit case, two kerfs only, independent leaf coverage. |
| S06 | Passed | T `test_equal_area_and_missing_kerf_capacity_do_not_fit_three` for 306.3 and 300 mm: explicit named unplaced pieces. |
| S07 | Passed | T `test_trimmed_exact_fit_and_length_allowance`: 316.4×110 stock/5 trim gives starts 5,108.2,211.4 mm. |
| S08 | Passed | T `test_allowance_changes_only_stock_blanks_and_partition`: 1 mm per edge enlarges faces by 2 mm, preserves finished CAD dimensions; new independently verified layout. |
| S09 | Passed | T `test_grain_locked_short_sheet_reports_named_unplaced_parts`: 900×1220/10 trim cannot place sides along 880 mm grain axis; locked parts never rotate 90°. |
| S10 | Passed | T missing/incompatible stock tests: geometry stays seven panels while named main parts/layout/purchase estimate become incomplete. |
| S11 | Passed | T independent tamper case `[missing_cut]` plus fully-contained trailing-release regressions reject absent release cut. |
| S12 | Passed | T independent tamper cases `[duplicate_part]`, `[overlap]`, `[wrong_pool]`, `[fake_instance]` reject with actionable IDs/findings. |
| S13 | Passed | T known-price test: synthetic 70.00 + 25.00 = USD 95.00 sheet purchases; hardware/finish/tax/shipping/tools exclusions and no invented full-project total. |
| S14 | Passed | T missing-price test: known subtotal USD 70.00, unknown back price null, incomplete total rather than zero. |
| S15 | Passed | T `test_explicit_hardware_pack_arithmetic`: 24 required / explicit pack 10 → three packs / 30 supplied; unknown pack price remains null. |
| S16 | Passed | T failed-layout/lower-bound and reporting-tamper tests: area lower bound retains `sufficiency=not_established`, never used as sufficient purchase quantity. |

## AI and local application boundary — 12 checks

| ID | Status | Observed result / exact check |
|---|---|---|
| A01 | Passed | T fake/manual 36 in resolved geometry equivalence + UI5 native browser apply: reviewed 762→914.4 mm change produces revision 2 and genuine 878.4 mm horizontals. |
| A02 | Passed | T fake questions cases return clarification with no changes/hidden dimensions; normal form validation remains authoritative. |
| A03 | Passed | T fake drawers/unsupported cases reject supported-scope mismatch; stable bookcase request is not misclassified as table. UI5 drawers prompt reports supported scope and exposes no apply action. |
| A04 | Passed | T forbidden/duplicate schema cases plus worker code-field rejection: measured thickness, recipe/path/code changes cannot write revisions or launch CAD. |
| A05 | Passed | T malformed/duplicate provider cases and signed/fraction/precision fake-token regressions: bounded failure, no valid numeric suffix extraction or endless repair. |
| A06 | Passed | T timeout/unconfigured provider HTTP cases preserve forms/project; UI5 fake timeout remains actionable without disabling manual workflow. No live call made. |
| A07 | Passed | T stale/cross-project conflict + UI5 actual stale refresh: 409 at backend, stale explanation/disabled apply at frontend. |
| A08 | Passed | OPT confirms private synthetic marker in restarted API and its absence from actual live native worker/descendant environments plus 183 generated-file/decoded-ZIP/PDF/input/log/receipt/bundle scan items. T allowlist/redaction tests independently pass; marker values are never printed or written as evidence. |
| A09 | Passed | T hostile Host/Origin/CSRF and arbitrary artifact ID/path/worker identity checks reject before publication/download; genuine-byte missing/corrupt download guards. |
| A10 | Passed | T inert ZIP traversal, absolute/drive/backslash, symlink, executable, duplicate and excessive-expansion cases reject before project write; imported geometry never executes code. |
| A11 | Passed | T inert explanation data + UI5 actual injected HTML string: text displayed literally, no image node or script execution. |
| A12 | Passed | T reservation before provider call and one-time transactional apply: same request/key does not duplicate calls or revisions; uncertain timeout not automatically repeated. Paid/live usage was not exercised. |

## Browser usability and portability — 10 checks

| ID | Status | Observed result / exact check |
|---|---|---|
| B01 | Passed | M2 actual UI creates baseline from inch inputs and separate editable 18 mm/6 mm actual stock; seven genuine panels and 726 mm cut list. |
| B02 | Passed | M2 `side_left`, `shelf_01`, grouped Horizontal panels select exact IDs; M0 independent same-GLB raycast proves separate occurrences. |
| B03 | Passed | M2 hide/isolate/explode/restore changes displayed visible IDs only; identical saved cut-list download retained, genuine assembly source remains immutable. |
| B04 | Passed | M2 keyboard invalid fraction, explicit labels/`aria-invalid`/error text and focus styling; UI5 newer stale/error surface. Automated checks do not establish screen-reader/zoom conformance. |
| B05 | Passed | M2 390 px fresh and saved views plus UI5: no horizontal document overflow, reachable actions, readable scrollable cut table and direct export links. |
| B06 | Passed | M2 form and non-3D cut-list links/row-selection controls usable without camera manipulation; saved downloads survive active cancellation. |
| B07 | Passed | T genuine inventory/fresh IDs/provenance checks + UI5 actual ZIP export/import and trusted native rebuild: imported project `project_b7cc0f538b1147bba68ac95348b30d10`, revision `rev_5832fb4c4782454cab7fd8e516e093e6`, genuine build 60.8505994 s / 880,488,448 bytes. Imported geometry was not treated as trusted current output. |
| B08 | Passed | OPT removes/recreates only the contained non-linked cadgen namespace (411 disposable files), reopens unchanged spec/manifest and verifies all 25 committed downloads; cache stays empty. T corrupted/missing committed bytes and disposable-cache checks also pass. |
| B09 | Passed | CLEAN actual final-source `setup.ps1 -Offline` and `launch.ps1 -DataRoot` passed, production UI/API/runtime ready and AI disabled; separate clean pinned environment and genuine preflight passed. Native Windows only; initial online bootstrap and WSL were not separately re-exercised. |
| B10 | Passed | Final IMPLEMENTATION-STATUS, launch guide and two complete verified sample packages reconciled with the exact final backend/browser/native evidence. Skips, physical review and the unimplemented optional live adapter are explicitly distinguished. |

## Final browser and option-export commands

The passing full browser collection included genuine M0/M2/M3–M6 flows. An earlier intentionally interrupted attempt is historical diagnostic evidence, not counted as a pass. The final persistence repair received the four affected post-fix checks, and the separate production port check waited for all seven rebound GLBs before capturing the inspected screenshots. Exact executed commands are retained in `apps/web/tests/evidence/frontend-acceptance.json`:

```powershell
$env:WOODWORK_AUTHORED_SAMPLE_PATH='C:/Users/byonk/AppData/Local/WoodworkingPlanner/samples/authored-20261013.json'
$env:WOODWORK_TEST_URL='http://127.0.0.1:5173'
npm --prefix apps/web test
Remove-Item Env:WOODWORK_AUTHORED_SAMPLE_PATH -ErrorAction SilentlyContinue
npm --prefix apps/web run typecheck
npm --prefix apps/web test -- --grep "stale draft recovery|hostile proposal|saved draft reopens|canonical dimensions"
npm --prefix apps/web test -- --grep 'production port'
npm --prefix apps/web run build
```

`diagnostics/export_options.py` passed actual J14/A08/B08 verification against the restarted API with a private synthetic marker. The marker was supplied only through API/runner environments and was never displayed or written to evidence. Its six guardrail tests independently passed, including a real native Windows junction rejection. The executed diagnostic command used API PID 25344:

```powershell
.venv/Scripts/python.exe diagnostics/export_options.py --record C:/Users/byonk/AppData/Local/WoodworkingPlanner/samples/authored-20261013.json --output C:/Users/byonk/AppData/Local/WoodworkingPlanner/export-options/20261013-final-01 --api-pid 25344
```

To repeat it, use a new output directory and the current restarted API PID; privately supply a new matching synthetic marker. The diagnostic verified the 120-second API worker profile, latest accepted base, only-kerf and only-paper changes, all intermediate artifact sets, live worker/descendant environments, decoded ZIP/PDF content, inputs/logs/receipts and production bundles. It removed only the exact generated namespace after resolved containment and link checks, then reopened the source and all committed downloads without restoring cache content.

Genuine kerf-only generation passed in 60.0273822 s / 880,943,104 bytes sampled process-tree RSS; paper-only generation in 64.7618543 s / 881,168,384 bytes. Subsequent stock, document, stock and ZIP jobs passed in 1.9560484, 15.2436952, 3.8386466 and 2.7777322 s. Paper-only revision `rev_bf1d9a1c08114b689684f4840cc0637d` uses Letter application pages and retains native metric A4 sheets, with cumulative set `set_9d93111bda6240c399edcd89aee47556`. Its coherent ZIP SHA-256 is `91185b00322b47a61884e38a3906a2532773d4db0dadd24c27c4d610d1c8e29a`. Exact IDs/hashes and all six jobs are in `evidence/m6/export-options-evidence.json`.

## Remaining report and separate review scope

Final `docs/IMPLEMENTATION-STATUS.md`, launch instructions and complete sample exports are synchronized. The 22 intentional native regeneration skips have prior genuine saved-CAD/document corpus evidence; they are not silently treated as executed in the ordinary backend suite. The final stock PDFs passed all nine visual reviews and page bounds/font checks; the six authored A4 stock pages were additionally inspected.

The installed authored recipe has technical/source checks and genuine documents. **Physical fabrication and site installation remain unreviewed**, as detailed in `docs/CONSTRUCTION-RECIPE-REVIEW.md`. Live-provider credentials/calls and paid-request behavior were not tested; the user chose to keep the release offline on 2026-10-14, with the explicit fake provider used for software acceptance. No live-provider decision remains pending for this release. No external deployment, push or release occurred.
