# Implementation sequence

This is an execution contract for Codex. The application and commands described here are **to be implemented**; this handoff does not claim they already exist. Read the main plan and detailed contracts before starting. Preserve existing repository instructions and unrelated changes.

M0–M3 deliver the first useful product: a local, editable bookcase design with consistent geometry, cut lists, and measured documents. M4–M6 complete the planned local version. Proceed between milestones when their dependencies are satisfied; routine checkpoints do not require another permission request.

## Working rules and ownership

Use React/TypeScript/Vite, React Three Fiber, Python 3.13, FastAPI/Pydantic, SQLite, local files, and cadgen 0.7.21. Lock compatible supporting dependencies after the integration spike. Inspect the pinned upstream commit rather than assuming the plugin distribution branch contains the full source.

| Boundary | Owns | Must not do |
|---|---|---|
| Domain and trusted templates | Units, equations, part identities, placements, manufacturing groups | Import CAD, call a provider, or depend on database state |
| CAD adapter | Pinned CAD interfaces, solids, measured checks, exchange/viewer exports | Recalculate furniture rules or infer manufactured parts from mesh nodes |
| API, storage, and jobs | Revisions, persistence, process lifecycle, atomic artifact publication | Run long CAD work inside HTTP handlers or publish partial success |
| Exports and recipes | Documents, construction completeness, stock/cost calculations | Invent fasteners, load limits, or missing measurements |
| Browser and AI adapter | Input, review, selection, structured proposals | Bypass backend validation or replace authoritative dimensions |

These are module boundaries, not a requirement for separate people. If delegating, assign files explicitly. Keep schema changes with one owner; communicate contract changes before parallel consumers implement them. Integrate a complete vertical slice before adding abstractions for hypothetical future templates.

## M0 — Prove the CAD integration

**Dependency:** readable handoff and a local implementation workspace.

- **M0.1 — Inspect and establish the workspace.** Record repository status, applicable instructions, Python/Node availability, and the selected native Windows or WSL path. Create the application repository only if needed. Keep application data separate from code.
- **M0.2 — Pin and diagnose.** Establish cadgen 0.7.21 with Python 3.13, capture supporting versions, and load the kernel. Add a reproducible preflight command. Diagnose native loading problems; use the documented supported fallback without changing OS security settings.
- **M0.3 — Build a minimal real part.** Through a small adapter, generate a trusted rectangular panel and export STEP plus GLB. Measure the saved geometry. Verify millimeter-to-viewer conversion, axis mapping, origin, and winding using an asymmetric fixture.
- **M0.4 — Prove instance identity.** Display two instances of one part asset using application-owned IDs and transforms. Confirm selection survives shared geometry. Inspect the engineering-drawing public API and produce one measured test sheet; record genuine paper-size support.
- **M0.5 — Record operating evidence.** Capture cold/warm timings, available peak-memory evidence, output sizes, runtime/browser prerequisites, and known limitations. Disable the upstream daemon and app-worker telemetry through the adapter's documented configuration.

**Exit gate:** a clean-directory command reproduces genuine geometry and exports; dimensions, units, orientation, identity strategy, and drawing entry point are demonstrated. Record a screenshot, measured values, versions, exact commands, and any compatibility decision. Mock geometry cannot satisfy this gate.

## M1 — Build the deterministic engine

**Dependency:** M0 CAD adapter contract. Pure domain work can proceed while a runtime dependency is being resolved.

- **M1.1 — Implement canonical models.** Translate the supplied schema into Pydantic domain models. Implement exact unit parsing, normalized decimal strings, schema versioning, canonical serialization, and hashing. Generate compatible schema/client contracts instead of maintaining conflicting copies.
- **M1.2 — Compile the bookcase.** Implement the supplied equations, final-position quantization, material references, stable physical IDs, manufacturing fingerprints, placements, and cut groups. Keep rough allowances separate from finished dimensions and kerf. Reject impossible dimensions without clamping.
- **M1.3 — Connect real geometry.** Send the resolved ledger to the adapter. Generate per-unique-part assets and assembly transforms. Check dimensions, solid validity, assembly bounds, and template-specific contacts against the ledger.
- **M1.4 — Publish a coherent artifact set.** Implement CSV, canonical/resolved JSON, geometry outputs, validation evidence, and immutable manifest. Hash completed files. Exclude temporary paths and diagnostics that do not belong in a project export.
- **M1.5 — Exercise mutations.** Run baseline, width, thickness, depth, zero-shelf, and invalid-input fixtures. Check geometry and exported data, including the repeating opening arithmetic for 19 mm panels.

**Exit gate:** the baseline produces seven physical panels and the expected three geometry-only cut groups. Every supplied mutation propagates correctly without a browser or AI. Record machine-readable comparisons and measured artifact results. The recipe-free fixture remains a design, not a complete construction plan.

## M2 — Deliver the local editing loop

**Dependency:** M1 domain, revision, and artifact contracts.

- **M2.1 — Persist projects.** Implement SQLite migrations and repositories, immutable revisions, last-successful pointers, server-owned relative artifact paths, and explicit data-root configuration. Add basic API contract checks.
- **M2.2 — Run and recover jobs.** Implement one dispatcher with a separate trusted CAD process, bounded stages, polling, cancellation, process-tree cleanup, temporary outputs, and atomic publication. Recover interrupted jobs on restart without losing successful artifacts.
- **M2.3 — Build the workspace.** Add project list/create/open, dimensions and measured-material forms, derived summaries, validation messages, and draft/applying/successful revision states. Serve the built UI from the local application origin.
- **M2.4 — Integrate the viewer.** Render manifest instances through React Three Fiber. Add required views, fit, selection, hide/isolate/restore, and presentation-only explosion. Link instance selection and grouped cut-list rows in both directions.
- **M2.5 — Verify real interaction.** Exercise create, regenerate, cancel, fail, restart, and reopen flows with genuine CAD outputs. Make keyboard operation and non-color selection cues usable. Protect local state-changing requests and reject arbitrary file paths.

**Exit gate:** a user changes width, sees the correct affected parts, selects each physical board, and reopens the saved revision after restarting. A cancelled or failed newer job preserves the previous model and exports. Record the small browser demonstration, relevant job logs, and persistence results.

## M3 — Produce measured documents and implement recipes

**Dependency:** M1 artifact facts and M2 revision retrieval.

- **M3.1 — Render the design packet.** Implement application-owned Letter/A4 pages with ReportLab and the measured native drawing adapter. Include overview, assembly dimensions, part/cut lists, material records, and verification metadata. Identify native part-sheet paper sizes honestly.
- **M3.2 — Derive every measurement.** Pull values from the resolved project or measured geometry. Implement readable callouts, labels, units, pagination, and image framing. Render all acceptance PDFs to images and inspect every page.
- **M3.3 — Implement the recipe contract.** Add versioned applicability rules, joint/operation references, hardware quantities, tool requirements, dependency-ordered instructions, and completeness checks. Cover all specified interfaces, including the applied back.
- **M3.4 — Author the separate construction fixture.** Use appropriate primary manufacturer instructions for a supported fastening method and record applicability. Keep the supplied geometry fixture recipe-free. Do not invent jig settings or hardware to close a missing-data gate.
- **M3.5 — Separate evidence states.** Demonstrate missing/incompatible recipe behavior and a complete authored recipe when available. Track physical review independently. Software can generate the review packet; it cannot record an unperformed build as completed.

**Exit gate:** the baseline exports a readable, revision-consistent **design packet**. Recipe contract validation and incomplete-state behavior pass. An authored complete recipe is a separate gate for complete construction instructions. If sourcing or physical review is pending, record the exact gate and continue independent M4–M6 work; do not mislabel the pending result or block ordinary design exports.

## M4 — Add conservative stock planning and costs

**Dependency:** M1 manufacturing ledger; M3 export surfaces.

- **M4.1 — Model real stock.** Record stock dimensions, thickness/material compatibility, usable bounds, trim, grain, rotation restrictions, and kerf. Use rough blank dimensions where allowances exist.
- **M4.2 — Implement the layout algorithm.** Follow the rectangular guillotine policy in the export contract with deterministic ordering. Produce both placements and a valid cut sequence. Validate boundaries, overlap, grain, cut feasibility, and kerf consumption independently of the placement routine.
- **M4.3 — Compute transparent costs.** Use purchased quantities, user-entered decimal prices, explicit currency, and separate consumed-material values. Preserve unknown prices and incomplete estimates. Add optional consumables/tax/shipping assumptions without claiming live retail prices.
- **M4.4 — Present and export.** Show suggested layouts and estimates tied to their revision/settings. Explain an unplaceable part specifically. Include layouts only after their validator passes.

**Exit gate:** supplied layout cases produce feasible cut sequences and correct purchased quantities; the kerf/grain counterexamples fail appropriately. Missing prices remain unknown. Document that the algorithm suggests feasible layouts without proving optimality.

## M5 — Add structured natural-language proposals

**Dependency:** M2 revision service and stable validated input contracts. Live credentials are optional.

- **M5.1 — Implement proposals.** Use the supplied schema, allowlisted edits, base revision, unresolved questions, and semantic validation. Protect measured thickness from AI overrides. Display before/after changes and apply accepted proposals through the normal revision service.
- **M5.2 — Add the fake provider first.** Cover valid edits, unsupported furniture, missing information, malformed output, forbidden fields, and stale proposals. Test without network access or a key.
- **M5.3 — Add the optional live adapter.** Consult current official provider documentation during implementation. Record the chosen supported interface and pinned SDK. Keep credentials server-side; add bounded requests, appropriate timeout/error handling, and usage visibility. Never execute generated code.
- **M5.4 — Handle disagreement and failure.** Reject stale-base proposals with a clear conflict. Keep drafts and existing revisions intact after provider errors. A provider outage must not disable forms, CAD, or exports.

**Exit gate:** fake-provider acceptance cases pass end to end and AI-disabled operation works. Record live-provider verification only if configured and actually run; otherwise mark that adapter's external check pending without blocking the local release.

## M6 — Finish the local release

**Dependency:** relevant M0–M5 software gates; separately documented construction/provider exceptions.

- **M6.1 — Complete setup and launch.** Supply documented setup, preflight, development, production-build, local-launch, and diagnostic commands. Exercise the selected Windows/WSL route from a clean setup and document the boundary of verified support.
- **M6.2 — Complete portable recovery.** Implement inert ZIP import, schema/hash/path/size checks, trusted rebuild, and export/import round trip. Test application restart, interrupted work, and missing/corrupt artifact behavior.
- **M6.3 — Run the acceptance demonstration.** Follow ACCEPTANCE-TESTS.md with real artifacts. Run relevant domain/adapter/API tests, frontend type/build checks, and the focused browser flows. Fix failures; do not expand tests without a concrete remaining risk.
- **M6.4 — Package the working result.** Include launch instructions, sample projects, sample export, dependency locks, known limitations, meaningful performance measurements, and implementation status. Review the product's statuses against the evidence actually collected.

**Exit gate:** another session can reproduce setup, launch the app, run the documented demonstration, and open its export package. Report precisely which local software gates passed and which optional-provider or physical-review gates remain pending. Do not claim a broader public release.

## Command and evidence contract

Implement convenient commands for **preflight**, **fixture compilation/build**, **development**, **local launch**, **focused verification**, and **release demonstration**. Names may follow the actual repository's conventions. These responsibilities are required; no command path in this handoff should be assumed to exist already.

Once implemented, record exact copyable commands, working directory, prerequisite environment, expected output location, and exit behavior in the launch guide and status log. Keep native Windows and WSL commands distinct. Evidence records identify the fixture/revision, toolchain, command, result, artifact paths/checksums, and any inspection performed. Do not include secrets or call a planned check “passed.”

## Checkpoint prompts and continuation log

Use this prompt at the first engineering checkpoint:

> Complete M0 and M1 using the supplied contracts and fixtures. Prove actual CAD/export agreement, document exact reproduction commands and measured results, update IMPLEMENTATION-STATUS.md, and continue to M2 when its dependencies are satisfied. Report concrete blockers without substituting mock outputs.

Use this at subsequent checkpoints:

> Read IMPLEMENTATION-STATUS.md and inspect the current repository. Resume the first incomplete work item whose dependencies are satisfied. Verify its exit gate, record evidence, and continue to the next eligible milestone. Preserve successful revisions and unrelated work. Finish independent local work when an external dependency blocks another item.

Maintain `docs/IMPLEMENTATION-STATUS.md` in the application repository with this structure:

```markdown
# Implementation status
## Environment and repository
## Milestone gates: pending / in progress / passed / blocked
## Completed work items and evidence
## Exact setup, run, and verification commands
## Decisions and contract changes
## Blocked gates: dependency, impact, independent work available
## Next eligible work item and reproduction context
```

Checkpoint updates are reports, not approval requests. Continue routine reversible implementation and necessary fixes. Do not deploy, publish, purchase, push externally, enter unavailable credentials, or reduce OS security settings. If a decision truly changes the approved scope, present the concrete completed work and the precise remaining decision.
