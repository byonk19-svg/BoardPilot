# Sources and Evidence Boundaries

Research baseline: 2026-10-13 UTC. The application described in this handoff is proposed work. Source review establishes the capabilities and constraints below; it does not establish that the application has been built, benchmarked, or physically tested.

## Upstream baseline

The selected release is cadgen/text-to-cad v0.7.21. Its inspected source commit is 24573128ceaab564f497d7c12f995c41784c9539. The release was published on 2026-10-11. Keep this pin for the first integration; verify and document later upgrades rather than assuming a moving branch is compatible.

| ID | Primary source | What it supports |
|---|---|---|
| U1 | [Repository README](https://github.com/earthtojake/text-to-cad/blob/24573128ceaab564f497d7c12f995c41784c9539/README.md) and [v0.7.21 release](https://github.com/earthtojake/text-to-cad/releases/tag/v0.7.21) | Installation/runtime context, plugin-only latest branch, agent support, export overview, Windows diagnostic context |
| U2 | [cadgen package metadata](https://github.com/earthtojake/text-to-cad/blob/24573128ceaab564f497d7c12f995c41784c9539/packages/cadgen/pyproject.toml) | Package dependencies, Python metadata, Beta classification |
| U3 | [CAD skill](https://github.com/earthtojake/text-to-cad/blob/24573128ceaab564f497d7c12f995c41784c9539/skills/cad/SKILL.md), [STEP generation](https://github.com/earthtojake/text-to-cad/blob/24573128ceaab564f497d7c12f995c41784c9539/skills/cad/references/step-generation.md), and [supported exports](https://github.com/earthtojake/text-to-cad/blob/24573128ceaab564f497d7c12f995c41784c9539/skills/cad/references/supported-exports.md) | Managed Python 3.13 route, parameterless decorated models, trusted Python factories, export and path contracts |
| U4 | [Engineering drawing skill](https://github.com/earthtojake/text-to-cad/blob/24573128ceaab564f497d7c12f995c41784c9539/skills/engineering-drawing/SKILL.md) and [sheet API](https://github.com/earthtojake/text-to-cad/blob/24573128ceaab564f497d7c12f995c41784c9539/skills/engineering-drawing/references/sheet-api.md) | Geometry-derived PDF views/dimensions, sheet support, rendering review, no native sections/details/auxiliary views |
| U5 | [DXF skill](https://github.com/earthtojake/text-to-cad/blob/24573128ceaab564f497d7c12f995c41784c9539/skills/dxf/SKILL.md) | Parameterless drawing models, millimeter XY profiles, layers and validation; no Node needed for the documented DXF snapshot route |
| U6 | [Mesh export implementation](https://github.com/earthtojake/text-to-cad/blob/24573128ceaab564f497d7c12f995c41784c9539/packages/core/src/lib/export/packageMeshExport.js) and [public GLB namespace](https://github.com/earthtojake/text-to-cad/blob/24573128ceaab564f497d7c12f995c41784c9539/packages/cadgen/src/cadgen/glb.py) | Static color grouping, limits of occurrence preservation, CAD-to-GLB axes and scale conversion |
| U7 | [Store and daemon contract](https://github.com/earthtojake/text-to-cad/blob/24573128ceaab564f497d7c12f995c41784c9539/packages/cadgen/STORE.md), [state override](https://github.com/earthtojake/text-to-cad/blob/24573128ceaab564f497d7c12f995c41784c9539/packages/cadgen/src/cadgen/viewer/recents.py), and [telemetry controls](https://github.com/earthtojake/text-to-cad/blob/24573128ceaab564f497d7c12f995c41784c9539/packages/cadgen/src/cadgen/cli/telemetry.py) | Daemon behavior, app-scoped cache/state and telemetry settings, need for app-owned lifecycle limits |
| U8 | [G-code skill](https://github.com/earthtojake/text-to-cad/blob/24573128ceaab564f497d7c12f995c41784c9539/skills/gcode/SKILL.md) | OrcaSlicer/FDM slicing, not woodworking router CAM |
| U9 | [Engineering drawing implementation](https://github.com/earthtojake/text-to-cad/blob/24573128ceaab564f497d7c12f995c41784c9539/packages/cadgen/src/cadgen/eng_drawing.py) | Sheet units string is a label; document units remain mm and dimension scale correction does not perform inch conversion |
| U10 | [Inspection and validation](https://github.com/earthtojake/text-to-cad/blob/24573128ceaab564f497d7c12f995c41784c9539/skills/cad/references/inspection-and-validation.md) | Saved-artifact measurements, revision-bound selectors, no inferred manufacturing identity or universal structural report |
| U11 | [Node runtime](https://github.com/earthtojake/text-to-cad/blob/24573128ceaab564f497d7c12f995c41784c9539/packages/cadgen/src/cadgen/_internal/node_runtime.py) and [kernel-load hints](https://github.com/earthtojake/text-to-cad/blob/24573128ceaab564f497d7c12f995c41784c9539/packages/cadgen/src/cadgen/_internal/kernel_load_hint.py) | Mesh runtime requirements and diagnosis of the documented Windows native-module issue |
| U12 | [License](https://github.com/earthtojake/text-to-cad/blob/24573128ceaab564f497d7c12f995c41784c9539/LICENSE) | Upstream MIT license; retain applicable notices when incorporating code |

The focused source review did not locate a complete woodworking cut-list engine, material optimizer, furniture recipe library, or application matching this handoff. Those items are scoped as application work; this is not a claim that every file or every future branch was exhaustively audited.

The repository contains older/manual drawing examples. A manually typed dimension string or several projected views on a CUT layer is not an acceptable shortcut for a production measured drawing or CNC profile in this application.

## Technical primary sources

| ID | Primary source | Use in this specification |
|---|---|---|
| T1 | [FastAPI background tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/) | Distinguishes ordinary background callbacks from heavier computation; the chosen local supervised worker is our architecture decision |
| T2 | [Khronos glTF 2.0 specification](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html) | glTF coordinate/unit conventions; exact upstream conversion is also verified in U6 |
| T3 | [NIST SI units — length](https://www.nist.gov/pml/owm/si-units-length) | Exact international inch conversion to 25.4 mm |
| T4 | [JSON Schema validation draft 2020-12](https://json-schema.org/draft/2020-12/json-schema-validation) | Schema vocabulary used by the handoff contracts; semantic domain checks are separate |
| T5 | [Python 3.13 subprocess](https://docs.python.org/3.13/library/subprocess.html) | Argument arrays, environment/process invocation behavior |
| T6 | [Microsoft Job Object limits](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_limit_information) | Native Windows job limits and kill-on-close behavior |
| T7 | [Microsoft WSL filesystems](https://learn.microsoft.com/en-us/windows/wsl/filesystems) | Keep active development/runtime files with the environment running the tools |

## Woodworking primary sources

| ID | Primary source | Supported fact and limitation |
|---|---|---|
| W1 | [Kreg screw selector](https://www.kregtool.com/screw-selector/) | Actual material thickness and material type are explicit inputs to screw selection; this does not supply this app's complete bookcase recipe |
| W2 | [Kreg screw guide](https://learn.kregtool.com/learn/how-to-select-right-pocket-hole-screw/) | Actual-versus-nominal thickness and thread/material guidance; consult the selected jig/manual for its applicable settings |
| W3 | [Kreg material-thickness guidance](https://learn.kregtool.com/learn/why-material-thickness-matters/) | Jig setup, drilling depth, and screw selection depend on actual material thickness |

No hardware size, fastener spacing, load rating, wall attachment, or universal safe dimension range is established by the bookcase arithmetic examples. Those require the explicitly selected construction method and its review.

## Proposed rather than sourced

The following are engineering choices or mathematical fixtures in this handoff:

- React/FastAPI/SQLite/local storage and the exact application module layout.
- M0–M6 priorities, performance budgets, queue limits, modeling bounds, and local-release scope.
- The 30 × 12 × 36 in reference bookcase, 18/6 mm actual materials, 2440 × 1220 mm test stock, 10 mm trim, and 3.2 mm test kerf.
- All equations, expected instance transforms, expected quantities, and synthetic prices.
- The schema, revision protocol, operation graph, construction completeness states, and acceptance gates.

The exact fixture arithmetic was checked when preparing the handoff. CAD integration, browser flows, native Windows operation, PDF generation, API behavior, and physical construction are implementation/review work for the subsequent project; they have not been performed by the handoff itself.
