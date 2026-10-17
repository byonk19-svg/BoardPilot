# Dimension-edit stabilization

Completed goal: width, height and depth edits complete through the pinned CAD
boundary, with truthful progress and retry/cancel behavior, preserving prior
verified output until the new revision is complete. Each resulting model, CSV
and stock package must identify the same accepted revision. Keep the offline
architecture and installed CAD versions; preserve the user's walkthrough project.

Plan:
1. Compare fresh-cache baseline generation with a single-process maintained-driver
   pilot. Record elapsed time, native saved-byte checks and process-tree memory.
2. Implement only improvements supported by those measurements. Add regressions
   for live progress and retry/error behavior before changing those paths.
3. Run backend checks, frontend build and real browser width/height/depth flows
   with the normal 120-second CAD deadline. Exercise cancellation and retry with
   prior outputs intact. Independently validate each cumulative stock set.
4. Review final changes, restore the user's project view, update implementation
   status and preserve evidence. Report measured limits without raising defaults
   or treating skipped native cases as executed checks.

Before evidence: walkthrough baseline 285.909 seconds; width retry 146.405 seconds.
The latter spent 35.489/31.815/38.691/15.072 seconds in the three panel and assembly
drivers. The worker then repeats the native geometry inspection already performed
by the adapter. Timeouts/retries preserve artifacts, but the UI uses a generic
failure notice and leaves that notice visible when retry starts.

## Implementation and evidence

- Adapter 1.1.0 runs the maintained parameterless panel/assembly models in the
  existing isolated, single-job worker. It exports each preview with the supported
  `cadgen.glb.build(saved_step, output)` door. That door uses the exact saved STEP's
  attested producer/mesh, avoiding the extra native producer helper started by a
  declared `@glb` bare-tree export. No shared daemon is enabled. The pinned versions,
  OS process-tree supervisor, cancellation and normal 120-second deadline remain.
- A geometry-only Windows startup hook avoids build123d's unused system-font
  registration scan and optional WMI discovery in native helper processes. It
  filters only the known system font patterns called by `build123d.text` registration;
  bundled fonts, explicit font reads and other globs remain available. The installed
  CAD packages are unchanged. Application PDF jobs use their regular environment.
  This hook is limited to the maintained box/placement models; revisit it before
  adding a model that needs system CAD text. Its source participates in build hashes.
- Native geometry is still independently read and checked after export. Its
  report now binds every inspected STEP/GLB hash and saved occurrence selector;
  the worker verifies that inventory before publication without repeating the
  same native booleans. Negative tests reject rehashed CAD bytes, missing proof
  and permuted STEP selectors. Historical 1.0.0 artifact sets remain readable.
- Progress is streamed immediately through an allowlist: side panels, horizontal
  panels, back, assembly, native inspection and final file checks. The UI shows
  elapsed time, identifies timeouts and preserves the prior model/downloads.
- Retry submission is guarded against duplicate clicks. A lost acknowledgement
  reconnects through the request's idempotency key; an unconfirmed retry reuses
  that key. Already-completed jobs refresh their saved model immediately.
  Temporary polling failure reconnects without claiming that generation failed.
- The back-panel change summary labels its changed width correctly.
- HTML responses revalidate their cache so a local build loads its new hashed
  bundle. A cached older shell previously hid the new progress/retry controls.

Observed before/pilot comparison: the original worker took 162.5847 seconds;
the maintained-driver pilot took 93.9073 seconds with genuine native geometry
checks. These are observed runs on a loaded Windows host, not a universal timing
guarantee. Full details are in `evidence/m2/regeneration-profile.json`.
The earlier candidate's first fresh-cache browser build passed in 76.0286 seconds
(`evidence/m2/regeneration-cold-run.json`), but repeat runs still timed out at 120
seconds. Sharing the interpreter alone was insufficient. Bounded stack diagnostics
captured repeated native-helper imports and Windows font scans; the supported saved-
STEP export route removes those producer-identification launches.

Completed checks so far:
- Backend: 242 passed, 22 opt-in native tests skipped, two known warnings, 83.58 s.
- Final native corpus: 30 passed in 288.17 seconds. All nine supplied examples
  ran through the production owned worker, then independent saved-byte inspection.
  Their times ranged 7.84–63.13 seconds, with a fresh application cache for the
  first case. Precision-contact and genuine negative tamper/overlap checks passed.
  All ten saved sets also passed inventory/hash/selector proof checks afterward.
- Production TypeScript/Vite build passed. Focused browser regressions cover
  timeout retry, connection recovery, duplicate requests and lost responses.
- Final full browser run: seven passed in 2.4 minutes on the production preview.
  A new isolated store had zero CAD cache files before this run. Its five genuine
  builds took 25.51, 18.81, 19.35, 22.91 and 10.49 seconds. It explicitly waits for
  each new stock job and PDF identity, including same-revision retry. Cancellation
  took 1.463 seconds and retained the prior CSV and stock link. An earlier complete
  run of the same final route also passed (16.13–31.40 seconds), preserved in
  `evidence/m2/regeneration-first-saved-step-flow.json`.
- Independent verification reopened all ten final browser CAD/stock sets and
  replayed each stock cut tree. A cumulative document job passed in 13.314 seconds;
  its 26-entry ZIP passes exact inventory/hash checks. All 16 PDF pages were rendered
  and visually inspected, including native measured dimensions and stock sequences.
  Physical construction review remains open. The actual CLI preflight passed in
  8.416 seconds without an override, and the user's sample/draft/19 saved artifacts
  remain intact. AI stays offline and disabled by default.

## Reproduction

Use PowerShell from the repository. A separate disposable store keeps the user's
walkthrough project intact; the seeded fixture is the verified raw geometry set,
not a derived stock/document set.

```powershell
$env:WOODWORK_DATA_ROOT='C:/Users/byonk/AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/WoodworkingPlanner/regeneration-verification-20261015-final'
$env:WOODWORK_CAD_TIMEOUT='120'
.venv/Scripts/python.exe -m uvicorn woodwork.api:create_app --factory --host 127.0.0.1 --port 8790 --no-access-log
```

In `apps/web`, build and serve the production bundle on the supported browser
origin, forwarding only its API requests to that isolated service:

```powershell
npm.cmd run build
$env:WOODWORK_API_URL='http://127.0.0.1:8790'
./node_modules/.bin/vite.cmd preview --host 127.0.0.1 --port 5173 --strictPort
```

In a separate `apps/web` terminal:

```powershell
$env:WOODWORK_TEST_URL='http://127.0.0.1:5173'
$env:WOODWORK_RUN_REGENERATION_FLOW='1'
npm.cmd test -- tests/regeneration.spec.ts --trace on
```

The isolated raw API port is intentionally not a permitted browser mutation
origin. Keep origin and CSRF validation enabled; use the preview proxy above.

Exact corpus, saved-output, PDF/ZIP and preflight commands are recorded in
`docs/IMPLEMENTATION-STATUS.md`. New native corpus/preflight runs need new empty
output paths; saved immutable results must not be overwritten. Timing observations
describe these Windows runs and do not guarantee a fixed time under every host load.
