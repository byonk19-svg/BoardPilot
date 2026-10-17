# Woodworking Platform Codex Handoff

Prepared 2026-10-13. Handoff version 1.0.

## What you are building

Build a local woodworking design application that turns a supported furniture idea and measured material dimensions into an editable 3D model, a reliable cut list, and a measured project packet. Begin with one plywood bookcase template. Add natural-language editing after the deterministic design engine works.

This package contains the implementation specification, data contract, worked examples, and acceptance criteria. It contains no completed application and no structurally approved furniture design.

## How to use this package

1. Extract the ZIP into a folder that Codex can read.
2. Open the intended application workspace in Codex. Use a new empty repository unless you already have a project you want to extend.
3. Put this handoff inside that workspace as a documentation folder, or give Codex its absolute path.
4. Paste the implementation prompt below. Keep the supporting JSON files accessible; they contain exact expected results.
5. Let Codex complete the milestones in order. A milestone is complete when its acceptance gate passes, not when its UI appears finished.

Do not replace an existing repository's AGENTS.md with this package. Codex should read the existing instructions and reconcile them with the explicit project request.

## Implementation prompt to paste into Codex

> Implement the woodworking design application specified in this handoff. Read START-HERE.md, WOODWORKING-PLATFORM-PLAN.md, docs/IMPLEMENTATION-SEQUENCE.md, docs/DATA-AND-GEOMETRY.md, docs/CAD-INTEGRATION.md, docs/API-AND-JOBS.md, docs/CONSTRUCTION-AND-EXPORTS.md, docs/ACCEPTANCE-TESTS.md, the JSON schemas, and the example fixtures before editing.
>
> Inspect the current workspace, repository status, AGENTS.md files, existing conventions, and available runtimes. Preserve unrelated work. If this is an empty workspace, create a separate application repository named woodworking-platform. Use text-to-cad through a pinned adapter; do not turn its entire monorepo into our application or substitute a mock 3D scene for CAD integration.
>
> Use the selected architecture: React with TypeScript and Vite for the browser UI; Three.js through React Three Fiber for the viewer; Python 3.13, FastAPI, Pydantic, SQLite, and local artifact storage for the backend; a separate, app-controlled process for trusted CAD jobs using cadgen 0.7.21. The baseline upstream commit is 24573128ceaab564f497d7c12f995c41784c9539. Verify the pinned contract during the integration spike, record the dependency lockfiles, and document any necessary deviation with evidence.
>
> Implement M0 and M1 first: the reproducible CAD spike, canonical specification and unit parsing, deterministic bookcase part compiler, stable instance identities, exact fixture arithmetic, genuine CAD outputs, CSV cut list, and immutable artifact manifest. Prove that the baseline and mutation examples agree across the model and exported data. Then continue through the next milestones in docs/IMPLEMENTATION-SEQUENCE.md while their dependencies are satisfied.
>
> The first supported project is an open-front plywood bookcase with full-height sides, top and bottom between the sides, zero to four fixed shelves, and an applied back. Outside depth includes the back. Actual measured material thickness is authoritative. Every model, part list, cut list, drawing, and export must describe one immutable revision.
>
> Build the forms and deterministic engine before the AI layer. The application must remain useful without an API key. AI may propose allowlisted parameter changes through structured data; it may not execute generated Python, shell commands, or filesystem paths.
>
> Keep finished panel dimensions, rough blank allowances, and saw kerf separate. Keep manufacturing part identity separate from mesh identity and cut-list grouping. Do not infer structural capacity, complete joinery instructions, or hardware sizes from geometry. Implement the construction-recipe contract and the explicit draft/completeness states described in the handoff.
>
> Work autonomously on routine local implementation, dependency setup, reversible fixes, and meaningful verification. Maintain docs/IMPLEMENTATION-STATUS.md with completed milestone gates, exact run commands, measured results, and remaining dependencies so work can continue across sessions. Do not stop after writing another plan or after building an attractive mockup.
>
> Do not deploy, publish, buy services, enter credentials that have not been supplied, push code externally, or change operating-system security settings. If a missing credential, unsupported runtime, or physical construction review blocks one feature, finish independent local work and report the exact blocked gate. Do not mark a skipped check as passed.
>
> At each substantial checkpoint, report what works, how to run it, what was verified, and the next milestone. At completion, provide the local launch instructions, sample project, passing acceptance evidence, export package, and any explicitly incomplete physical-review or optional-provider capability.

## Reading order

| File | Purpose |
|---|---|
| [WOODWORKING-PLATFORM-PLAN.md](WOODWORKING-PLATFORM-PLAN.md) | Product scope, chosen architecture, behavior, priorities, and release definition |
| [docs/IMPLEMENTATION-SEQUENCE.md](docs/IMPLEMENTATION-SEQUENCE.md) | Ordered engineering tasks, exit gates, and checkpoint prompts |
| [docs/DATA-AND-GEOMETRY.md](docs/DATA-AND-GEOMETRY.md) | Units, identities, exact bookcase rules, manufacturing data, and fixture arithmetic |
| [docs/CAD-INTEGRATION.md](docs/CAD-INTEGRATION.md) | The supported upstream boundary, GLB identity and coordinate conversion, runtime isolation |
| [docs/API-AND-JOBS.md](docs/API-AND-JOBS.md) | HTTP contract, persistence, revisions, jobs, recovery, AI proposals |
| [docs/CONSTRUCTION-AND-EXPORTS.md](docs/CONSTRUCTION-AND-EXPORTS.md) | Construction recipes, drawings, cut lists, materials, stock planning, project exports |
| [docs/ACCEPTANCE-TESTS.md](docs/ACCEPTANCE-TESTS.md) | Observable checks and a final demonstration script |
| [docs/SOURCES.md](docs/SOURCES.md) | Primary sources and the boundary between verified upstream facts and proposed app requirements |
| [spec/project.schema.json](spec/project.schema.json) | Version 1 canonical project contract |
| [spec/ai-proposal.schema.json](spec/ai-proposal.schema.json) | Restricted AI proposal response contract |
| [spec/artifact-manifest.schema.json](spec/artifact-manifest.schema.json) | Published artifact identity, versions, hashes, and completeness contract |
| [examples/README.md](examples/README.md) | Meaning of each fixture and expected-results file |
| [docs/HANDOFF-VALIDATION.md](docs/HANDOFF-VALIDATION.md) | Checks performed on this handoff and the application checks still to run |

## Settled defaults

The first release is a single-user local web application for a Windows computer. It needs no 3D printer, CNC machine, cloud account, or paid hosting to use its form-based design workflow. The default display is inches with metric equivalents; canonical dimensions are decimal millimeters. The reference template is a 30 in wide, 12 in deep, 36 in high bookcase made from measured 18 mm panels and a measured 6 mm applied back.

The neutral working title is “Woodworking Planner.” Branding, accounts, subscriptions, a template marketplace, and public deployment are later decisions. Do not invent those requirements during the first build.

## What the examples prove

The example numbers are a software correctness contract for panel geometry, quantities, units, and stock-layout logic. They do not establish a safe shelf load or certify a fastening method. The supplied example's construction recipe is intentionally unselected, so it must produce a clearly identified design packet until a complete recipe is supplied and checked.

The handoff distinguishes three deliverable levels:

- **Design engine complete:** reproducible geometry, parts, cut list, and dimensioned design packet.
- **Local application complete:** editing, persistence, jobs, viewer, exports, and optional AI proposal handling work through the documented acceptance checks.
- **Construction template reviewed:** an authored recipe supplies every attachment operation, compatible hardware, and build sequence, with a recorded physical review where required before public release.

Do not collapse these into one “ready to build” badge.
