# Acceptance Tests and Release Demonstration

These are checks for the application Codex will implement. They have not run merely because this file exists. Record the actual command, environment, observed result, and artifact/revision where relevant in docs/IMPLEMENTATION-STATUS.md.

Prioritize tests that could catch a wrong board dimension, misleading plan, broken identity, lost project, or unsafe execution boundary. Avoid tests that merely repeat UI component markup.

The rows are observable cases, not a requirement for one test file or function per row. Group related cases into compact parameterized tests and reuse the documented fixtures.

## 1. Test layers and numerical policy

Use pure domain tests for exact arithmetic and schema/semantic validation, adapter integration tests for genuine CAD and saved-file measurements, and a small browser suite for complete user flows.

Canonical input and finished part arithmetic use exact Decimal/Fraction values. The expected JSON is the independent comparison fixture, not a source of values for the production compiler.

Derived resolved millimeter positions use HALF_EVEN at 0.000001 mm. The supplied 19 mm material fixture permits 0.000002 mm difference when comparing those quantized positions/openings. This precision is not a woodworking fit tolerance.

For saved-kernel dimension checks, begin with 0.0001 mm absolute tolerance and relative volume agreement of 0.0000001, with any small absolute volume floor explicitly recorded. Confirm these are suitable in M0. Do not broaden tolerances to conceal incorrect formulas, lost parts, or axis swaps.

Source hashes and byte checksums compare exactly. Geometry comparisons and file-integrity comparisons are separate.

## 2. Runtime and adapter

| ID | Setup/action | Required result | Gate |
|---|---|---|---|
| R01 | Install the locked runtime in the selected Windows or WSL environment | Python/cadgen/build123d/OCP/Node versions recorded; kernel loads | M0 |
| R02 | Run the trusted one-part spike in a clean directory | Real STEP and GLB are produced and reopen | M0 |
| R03 | Run required snapshot and native drawing workflows | Actual image/PDF outputs render; missing renderer is an error | M0 |
| R04 | Use an asymmetric rectangular part with an off-center feature | Local origin, handedness, axis conversion, and feature location remain correct | M0 |
| R05 | Export a known 100 mm feature | Viewer length is 0.1 m, with no second scale factor | M0 |
| R06 | Instantiate two same-colored copies of one GLB | Each copy is independently selectable and highlightable | M0/M2 |
| R07 | Reopen assembly STEP and inspect labels and step-instance-map.json | Every physical instance maps exactly once to the correct saved occurrence; the map binds the current assembly artifact ID/hash | M1 |
| R08 | Change a model and inspect its new STEP | Old face/occurrence selectors are not reused across file hashes | M1 |
| R09 | Run after setup with AI and network access unavailable | Prepared local form/geometry workflow still succeeds; absent optional AI is clear | M6 |
| R10 | Trigger the documented native load failure or mock that diagnostic | Setup explains the real missing component and supported fallback; OS security is unchanged | M0/M6 |

## 3. Units and input semantics

| ID | Input/action | Required result | Gate |
|---|---|---|---|
| U01 | Parse every valid case in input-cases.json | Exact expected canonical mm string | M1 |
| U02 | Parse 3/4 in and 0.75 in | Both normalize to 19.05 exactly | M1 |
| U03 | Parse 1/64 in | 0.396875 mm is retained without rounding | M1 |
| U04 | Parse raw 1.2345678 mm or 18.0000005 mm | Precision error; no silent truncation/rounding | M1 |
| U05 | Parse 3/0 in, 1/3 in, NaN, Infinity, negative length, or code-like text | Specific parse/validation error before any CAD job | M1 |
| U06 | Enter bare 18 with explicit default mm, then default in | Values are 18 mm and 457.2 mm respectively; missing default is rejected | M1/M2 |
| U07 | Change preferred display units repeatedly | Canonical dimensions and geometry stay unchanged | M1/M2 |
| U08 | Change only the main material's nominal label | Physical geometry is unchanged; full revision/document metadata updates | M1 |
| U09 | Change actual thickness to 19.05 mm | Horizontal length becomes 723.9 mm; target clear height becomes 279.4 mm | M1 |
| U10 | Format 726 mm as a rounded imperial fraction | Approximation is identified; reopening the project still uses 726 mm | M3 |
| U11 | Supply unknown properties, unsupported schema/template version, duplicate stock ID | Request is rejected with a useful field/version result | M1/M2 |
| U12 | Set width 36 mm, depth 6 mm, or height 72 mm under baseline materials/count | Mathematical impossibility is reported; no zero/negative solid is launched | M1 |
| U13 | Set shelf count -1, 1.5, or 5 | Reject; 0, 1, 2, 3, and 4 are accepted when otherwise valid | M1 |
| U14 | Use t=25 mm, n=2, H=100.000001 mm | Reject a clear gap that collapses at resolved precision, despite a positive exact value | M1 |
| U15 | Exercise minimum/maximum public modeling bounds | Bounds are enforced separately from recipe applicability or structural claims | M1 |
| U16 | Internally quantize derived 18.0000005 and 18.0000015 | HALF_EVEN gives 18 and 18.000002; these are not accepted raw-input examples | M1 |

## 4. Reference geometry and changes

Use examples/bookcase-expected.json for the full tables and all nine projects.

| ID | Input/action | Required result | Gate |
|---|---|---|---|
| G01 | Compile the baseline | 3 definitions, 7 physical instances, horizontal quantity 4 | M1 |
| G02 | Compare baseline local part sizes | Sides 914.4×298.8×18; horizontals 726×298.8×18; back 914.4×762×6 mm | M1 |
| G03 | Measure baseline assembly bounds | Min (0,0,0), max (762,304.8,914.4) mm | M1 |
| G04 | Measure baseline openings | Three gaps 726×298.8×280.8 mm; shelf centers Z=307.8 and 606.6 mm | M1 |
| G05 | Sum saved part volumes | 29,635,528.32 mm³ within kernel tolerance; every part counted once | M1 |
| G06 | Check all rotations and transformed local grain vectors | Orthogonal, determinant +1, proper grain direction; no reflected side | M1 |
| G07 | Check allowed contact and volumetric intersection | Intended face contacts pass; deliberate material overlap fails | M1 |
| G08 | Set width to 36 in | Horizontal length 878.4 mm; back face 914.4×914.4; side sizes remain unchanged | M1 |
| G09 | Set main thickness to 19 mm | Length 724 mm; exact gap 4192/15; centers 307.966667 and 606.433333 mm | M1 |
| G10 | Set outside depth to 14 in | Main panel depth 349.6 mm; back Y center 352.6; back face size unchanged | M1 |
| G11 | Set back thickness to 9 mm at the same outside depth | Main depth 295.8 mm; back Y center 300.3; outside depth remains 304.8 | M1 |
| G12 | Set zero shelves | Five physical panels; horizontal quantity 2; one 878.4 mm opening | M1 |
| G13 | Run one-, three-, and four-shelf fixtures | Counts, centers, openings, and volumes match the expected JSON | M1 |
| G14 | Change count 2→1→0→2 | Surviving named slots keep identity; highest slots disappear/return; no zero-size placeholders | M1/M2 |
| G15 | Give equal-size boards different machining/face attributes in a recipe test | Manufacturing groups split; physical IDs remain correct | M3 |
| G16 | Inject a geometry inspection exception | Job does not report geometry passed or publish a current successful set | M1/M2 |

## 5. Revision, persistence, and worker recovery

| ID | Setup/action | Required result | Gate |
|---|---|---|---|
| J01 | Create, generate, close, restart, and reopen a project | Same spec, IDs, revision history, and committed artifacts remain usable | M2 |
| J02 | Edit width while a prior revision is displayed | UI labels draft/building/last-successful states accurately | M2 |
| J03 | Let a deliberately delayed r1 result arrive after successful r2 | r2 remains current; r1 is historical only | M2 |
| J04 | Construct a package containing an r1 CSV and r2 STEP | Hash/revision validation rejects the mixed set | M2/M6 |
| J05 | Repeat an identical generation request/idempotency key | One job/result, no duplicate worker | M2 |
| J06 | Reuse an idempotency key with different content | 409 conflict | M2 |
| J07 | Submit a revision against an out-of-date base | 409; no overwrite or silent rebase | M2 |
| J08 | Cancel queued and running jobs | Correct terminal state; no partial publication; only owned processes stop | M2 |
| J09 | Induce native worker crash or kill the worker | API stays available; safe failure recorded; next valid job succeeds | M2 |
| J10 | Induce a busy worker exceeding the wall-clock deadline | Process tree stops even if it emits heartbeats | M2 |
| J11 | Stop/restart API with an active job | Owned children stop or are reconciled; job becomes interrupted; valid prior work survives | M2/M6 |
| J12 | Fail publication between filesystem rename and database commit | Startup reconciliation handles the orphan without corrupting current records | M6 |
| J13 | Request cancellation of an already-terminal job | Idempotent terminal response; no state regression | M2 |
| J14 | Export after changing only kerf or document options | Appropriate new export/layout revision; CAD dimensions stay unchanged | M4 |
| J15 | Restore old parameter values | New revision with historical provenance; no mutation of prior records | M2 |
| J16 | Fill the bounded local queue | New work receives a clear queue-full result; existing work remains valid | M2 |
| J17 | Complete a document/stock job from a geometry artifact set | New cumulative set retains assembly STEP, one STEP/GLB per definition, identity sidecar, and core files; subset results cannot downgrade preferred output | M3/M4 |
| J18 | Queue a ZIP, then publish another artifact set | ZIP contains the artifact-set ID frozen at submission; explicit/default manifest selection is deterministic | M6 |

The local runner has one active worker. Reversed completion order can be tested by delayed publication callbacks or injected completed results; do not add parallel CAD execution just to reproduce the race.

## 6. Documents and construction completeness

| ID | Setup/action | Required result | Gate |
|---|---|---|---|
| D01 | Export baseline with recipe null | Accurate design packet, with construction method explicitly unselected | M3 |
| D02 | Produce a 25.4 mm dimension in dual-unit output | Exactly 1 inch; native metric sheets remain correctly labeled mm | M0/M3 |
| D03 | Change width and regenerate PDF/CSV | Every dependent measured value and title revision agrees with the new ledger | M3 |
| D04 | Extract PDF text and inspect rendered pages | Values present; no clipping, tiny unreadable dimensions, overlaps, or missing part labels | M3 |
| D05 | Open every page with its declared paper size | Letter application pages and ISO native sheets are identified accurately | M3 |
| D06 | Use an unknown recipe ID/version, then an installed recipe with incompatible thickness | Unknown is rejected with 422 and preserves prior design; known incompatible permits valid design exports with incompatible construction status | M3 |
| D07 | Supply a complete test recipe missing one required connection | Completeness fails and names the missing joint | M3 |
| D08 | Introduce a cycle or missing part in the operation graph | Reject the instruction sequence | M3 |
| D09 | Add a complete authored supported recipe | Hardware counts and step IDs derive from joints; all required connections resolve | M3 |
| D10 | Complete technical recipe checks without a physical review record | Physical-review status stays unreviewed | M3/M6 |
| D11 | Add rough allowance without a finishing-to-size operation | Geometry/cut list remain available; complete construction method requires the missing operation | M3/M4 |
| D12 | Export a CSV with a formula-like user title/material name | Text remains inert when opened in a spreadsheet; numeric dimensions stay numeric | M3 |
| D13 | Request unsupported section/detail views | No fake native capability; explain the absent view or use a clearly authored recipe illustration | M3 |
| D14 | Enable a test-only synthetic recipe | It is absent from the production user catalog | M3 |

## 7. Stock layouts and costs

| ID | Setup/action | Required result | Gate |
|---|---|---|---|
| S01 | Run baseline layout with 10 mm trim and 3.2 mm kerf | One main sheet and one back sheet; placements match valid rough rectangles | M4 |
| S02 | Simulate the baseline main cut tree | Nine internal cuts; parts 1,414,160.64, kerf 28,968.96, offcuts 1,460,870.4 mm² | M4 |
| S03 | Simulate the baseline back cut tree | Two internal cuts; parts 696,772.8, kerf 10,182.4, offcuts 2,197,044.8 mm² | M4 |
| S04 | Reconcile trim and usable areas | Each usable region totals 2,904,000 mm²; 72,800 mm² reserved edge bands restores full sheet area | M4 |
| S05 | Fit three 100 mm parts on 306.4×100 mm stock with k=3.2 | Exactly two kerfs; no false trailing kerf | M4 |
| S06 | Try the same parts on 306.3 mm or 300 mm stock | Cannot fit the three under the declared kerf model | M4 |
| S07 | Use 316.4×110 stock with 5 mm trim | Exact-fit usable region retained; starts 5,108.2,211.4 mm | M4 |
| S08 | Add 1 mm per-edge rough allowance | Rough face dimensions grow by 2 mm; finished CAD stays unchanged; layout rebuilds | M4 |
| S09 | Use grain-locked 900×1220 main stock with 10 mm trim | 914.4 mm sides are unplaceable along the 880 mm usable grain axis; no illicit 90° rotation | M4 |
| S10 | Remove compatible main stock or change its material reference | Geometry remains valid; layout/material purchase count is incomplete | M4 |
| S11 | Omit a trailing release cut where an offcut remains | Independent cut-tree validator rejects the plan | M4 |
| S12 | Duplicate a part, overlap two parts, use wrong thickness pool, or reference a nonexistent instance | Validator rejects with the relevant ID | M4 |
| S13 | Use baseline sheets with synthetic prices 70.00 and 25.00 USD | Known sheet-purchase subtotal 95.00; excluded items remain identified | M4 |
| S14 | Leave one price null | Partial known subtotal and incomplete estimate; unknown price is not zero | M4 |
| S15 | Required hardware count is 24, explicit pack size 10 in a synthetic pricing test | 3 packs purchased, 30 supplied, 24 required; no confusion between quantities | M4 |
| S16 | Compare area lower bound with a failed real layout | Lower bound is labeled and never called sufficient purchasing quantity | M4 |

The prices and hardware pack numbers in these tests are synthetic arithmetic inputs. They are not current market prices or a fastening recommendation.

## 8. AI and local application boundary

| ID | Setup/action | Required result | Gate |
|---|---|---|---|
| A01 | Run fake-provider width proposal | Before/after summary; applying creates the same geometry as manual 36 in edit | M5 |
| A02 | Ask for a design missing measurements | Targeted questions, no fabricated hidden dimensions | M5 |
| A03 | Ask for drawers or an unsupported furniture family | Clear supported-scope result, no unrelated model silently substituted | M5 |
| A04 | Provider proposes measured thickness, recipe ID, file path, or executable code as a change | Schema/allowlist rejects it before any write or CAD launch | M5 |
| A05 | Provider returns malformed JSON or duplicate field changes | Bounded validation/repair behavior; no endless retries | M5 |
| A06 | Provider times out or is unconfigured | Ordinary forms, projects, and exports remain usable | M5 |
| A07 | Apply proposal after project revision changed | 409 and refresh/review flow; no silent stale edit | M5 |
| A08 | Inspect a worker launched while the API has a test-only credential marker | Marker is absent from worker environment, logs, exports, and frontend bundles | M2/M5 |
| A09 | Submit hostile Origin/Host or arbitrary artifact path | Request is rejected; loopback/file boundaries preserved | M2/M6 |
| A10 | Import ZIP traversal/symlink/executable entries or excessive expansion | Inert validation rejects them; no code executes | M6 |
| A11 | Supply an explanation containing HTML or instructions | Render as inert text; it has no action authority | M5 |
| A12 | Repeat apply/request clicks | Idempotency/state control prevents duplicate revisions or paid requests | M5 |

Use synthetic credentials for leakage tests. Do not print real API keys as test evidence.

## 9. Browser usability and portability

| ID | Setup/action | Required result | Gate |
|---|---|---|---|
| B01 | Create baseline through the UI | Correct default interpretation and editable actual material thickness | M2 |
| B02 | Select side_left, then shelf_01, then a grouped cut row | Correct instance/group membership highlights without affecting unrelated copies | M2 |
| B03 | Hide/isolate/explode, then restore | View changes only; exported assembly and dimensions are unchanged | M2 |
| B04 | Navigate forms by keyboard and trigger an error | Labeled fields, visible focus, useful accessible error text | M2/M6 |
| B05 | Use a narrow viewport | Controls remain reachable; tables preserve readable headers; export remains possible | M6 |
| B06 | Work without manipulating the 3D view | Parameters and cut-list download remain accessible | M2 |
| B07 | Export a completed project ZIP and import it as a new project | New local identity, preserved source provenance, validated data/artifacts, rebuild from trusted template | M6 |
| B08 | Remove/recreate disposable cadgen cache and reopen exported project | Saved spec and committed artifacts remain available; cache is not the only copy | M6 |
| B09 | Follow launch guide from a clean supported environment | Actual documented commands work; prerequisite/setup failures are actionable | M6 |
| B10 | Inspect final implementation status | Completed, blocked, skipped, and physical-review states are reported truthfully | M6 |

## 10. Final demonstration script

1. Launch using the documented supported Windows or WSL path. Show runtime readiness.
2. Create the baseline bookcase in inches, with measured 18 mm and 6 mm materials.
3. Generate real CAD. Select all seven panels, show the three geometry-only cut groups, and inspect opening dimensions.
4. Export the design PDF and CSV. Show the revision, correct native metric drawing label, and actual dual-unit conversion.
5. Change outside width to 36 inches and show 878.4 mm horizontal panels in the model and documents.
6. Restore the baseline, change main thickness to 19 mm, and show the expected panel length and clear heights.
7. Restore again, set zero shelves, and show five panels and one opening.
8. Enter an impossible dimension and show that the prior valid model is labeled correctly and no new invalid CAD is launched.
9. Cancel an active job, restart after an interrupted job, and regenerate successfully.
10. Show the missing-recipe design packet and a separate complete authored recipe case. Identify any physical review still pending.
11. Run the baseline and exact-fit stock examples and the synthetic sheet-price subtotal.
12. Apply the fake AI width proposal, demonstrate a stale proposal conflict, and show the app with AI disabled.
13. Export a coherent ZIP, import it as a new project, and rebuild from the installed trusted template.

The final report includes commands, test results, representative rendered pages/screenshots, version information, performance observations, and explicitly remaining gates. Do not claim that the physical furniture was built unless there is actual recorded evidence.
