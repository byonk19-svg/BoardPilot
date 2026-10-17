# CAD Integration Contract

## 1. Responsibility and runtime pin

The CAD adapter accepts the **ResolvedProject** defined in [DATA-AND-GEOMETRY.md](DATA-AND-GEOMETRY.md). It produces genuine geometry, saved-artifact measurements, and export records for one immutable revision. The domain compiler owns woodworking formulas, manufacturing identity, placements, and quantities; the adapter implements that resolved design without interpreting the original request again.

Use **cadgen 0.7.21**, upstream commit **`24573128ceaab564f497d7c12f995c41784c9539`**, through its packaged Python runtime. This was the latest release verified on October 13, 2026 UTC. Keep the initial integration pinned even if a newer release appears. The upstream package is classified Beta. [Release] [Dependencies]

| Runtime component | Required treatment |
|---|---|
| Python | Use 3.13; record the tested patch version |
| cadgen | Pin `cadgen==0.7.21` |
| build123d | Resolve within upstream `>=0.11.1,<0.12`, then lock the actual version |
| Native CAD provider | Resolve `cadquery-ocp-novtk>=7.9,<8`, then lock the actual version |
| Playwright | Upstream pin is `1.63.0`; install its matching browser during setup |
| Node | Mesh export requires Node >=20; select and lock one tested release |

The released skills use managed Python 3.13. A package installation alone does not prove that the native kernel, Node exporter, browser renderer, and PDF renderer all work. M0 must exercise every required component. [Dependencies] [CAD skill] [Node runtime]

Record application, template, adapter, Python, cadgen, build123d, OCP, and Node versions in the artifact manifest. Upgrade through a reviewed dependency change and rerun the adapter acceptance corpus. Preserve the source pin and lockfiles in project documentation. Compare measured geometry across environments; do not substitute a blanket cross-platform STEP byte-equality requirement for geometric equivalence.

Use public cadgen interfaces. Keep upstream cache formats, `_internal` modules, and private viewer HTTP routes outside the application contract. The existing upstream viewer can help a developer inspect artifacts, but the product uses its own manifest-driven viewer.

## 2. Adapter pipeline

Implement the following order:

1. Receive an immutable, validated ResolvedProject and its revision/hash.
2. Revalidate its structural contract and referenced part definitions in the worker.
3. Build each unique definition in the canonical local frame.
4. Export a STEP and a GLB for each definition.
5. Place the definitions from the supplied instance transforms and export assembly STEP.
6. Reopen saved STEP files and measure dimensions, solids, labels, and placements.
7. Generate the requested drawing/export artifacts.
8. Return an artifact manifest and validation report for publication by the coordinator.

All quantities and cut groups come from the ResolvedProject. Do not infer them from triangle counts, STEP solids, material colors, or a rendered image. Upstream occurrence leaves can contain several solids; its geometry hierarchy does not infer manufactured parts. [Inspection]

Place assembly copies with `.moved(...)` or `Location * shape`, preserving a separate occurrence label for each board. Use the supplied proper rotation/translation matrices. Do not use transformations to conceal an incorrect part size or rederive placements inside the adapter. [Model contract]

## 3. Trusted JSON drivers

Cadgen generation runs a Python model script. A decorated `@step` function is **parameterless**; parameterized geometry belongs in ordinary trusted factories. `cadgen step build` re-emits an existing STEP document and is not a text/JSON model-generation command. [Model contract] [STEP API]

Ship reviewed static driver templates with the application. Copy them into the app-owned job directory and place immutable JSON inputs beside them. Keep all user text and numbers in JSON. Do not interpolate a project title, path, parameter, or AI response into Python source. Resolve inputs relative to the driver file and read them inside the model body.

Use one fixed part driver per definition directory and one fixed assembly driver. The part driver consumes already-resolved dimensions; it does not subtract panel thickness, calculate shelf spacing, or choose joinery. The assembly driver consumes the exact instance ledger. Treat driver code and factory versions as build inputs.

### M0 illustrative spike: one centered panel

This verifies the public decorator and export route. It is **not the application worker**: production still needs the full schema, bounded dimensions, part registry, process supervision, and saved-artifact checks. Put this reviewed `part.py` beside a `part.json` containing exactly three decimal millimeter strings.

```python
from decimal import Decimal
from pathlib import Path
import json

from cadgen import build123d as bd
from cadgen import glb, step

HERE = Path(__file__).resolve().parent
KEYS = ("length_mm", "width_mm", "thickness_mm")


@step(out="out/part.step")
@glb(out="out/part.glb")
def part():
    data = json.loads((HERE / "part.json").read_text(encoding="utf-8"))
    if not isinstance(data, dict) or set(data) != set(KEYS):
        raise ValueError("Expected exactly the three panel dimensions")
    values = []
    for key in KEYS:
        if not isinstance(data[key], str):
            raise ValueError(f"{key} must be a decimal millimeter string")
        value = Decimal(data[key])
        if not value.is_finite() or value <= 0:
            raise ValueError(f"{key} must be finite and positive")
        values.append(float(value))
    shape = bd.Box(
        *values,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.CENTER),
    )
    shape.label = "part"
    return shape


if __name__ == "__main__":
    part()
```

Example spike input:

```json
{"length_mm":"726","width_mm":"298.8","thickness_mm":"18"}
```

Run the file using the pinned interpreter. Decimal values become floats only at the geometry boundary. The production driver must also reject values outside the template's supported envelope before this conversion. [Model contract]

## 4. Supported public export routes

| Output | Interface |
|---|---|
| Part/assembly STEP | `@step(out=...)`; run the trusted model script |
| Maintained part GLB | Stack `@glb(out=...)` with `@step` |
| GLB from saved STEP | `cadgen.glb.build(Path(step_path), Path(glb_path), ...)` or `cadgen glb build INPUT.step OUTPUT.glb` |
| Inspection | `cadgen.read_step`, `cadgen.read_scene`, and `cadgen.geometry` |
| Measured native PDF | `from cadgen.eng_drawing import Sheet, eng_drawing`; decorated function returns a Sheet or list of sheets |
| DXF profile | Parameterless `@dxf` returning XY build123d geometry or a layer-to-geometry mapping |
| Review snapshot | `cadgen step snapshot INPUT.step OUTPUT.png`; use the corresponding `glb` or `dxf` command for those files |

These are the pinned interfaces. There is no `cadgen dxf build`, no engineering-drawing CLI, and no current `cadgen step inspect`. Mesh exports consume saved STEP/STP documents, not Python scripts. Capture actual results and failures during M0 instead of inventing an output envelope. [Mesh exports] [GLB API] [Inspection] [Drawing API] [DXF]

Decorator-relative `out=` paths are relative to the model script. CLI paths and ordinary document reads are relative to the process cwd. The adapter resolves approved paths explicitly and always uses distinct job output roots. [Model contract] [Mesh exports]

## 5. Part identity and GLB scene construction

**Export one GLB per unique part definition, then instantiate it from the application manifest.** Do not drive selection from a single static assembly GLB. The upstream static exporter groups geometry by color; its internal per-occurrence option serves animation, and the public GLB API does not expose that option. Same-colored boards can therefore share a merged mesh. [GLB implementation] [GLB API]

The React Three Fiber scene creates one group per physical instance. Assign the instance ID to that group and resolve raycast hits through the parent group. Shared definition geometry may be reused, but highlighting one instance must not change another instance's material state.

Use the canonical snake_case IDs: `side_left`, `side_right`, `shelf_01`, `shelf_02`, `bottom`, `top`, and `back`. Preserve surviving IDs when dimensions change. Shelf count changes explicitly add/remove IDs according to [DATA-AND-GEOMETRY.md](DATA-AND-GEOMETRY.md); never renumber by current mesh order.

Keep these identities separate:

- **Physical instance ID:** one placed board in the design.
- **Part-definition identity:** a shared manufactured shape/operation definition.
- **Manufacturing fingerprint:** the grouping contract including material, grain, machining, and edge treatment.
- **Artifact ID/hash:** exact output bytes for a revision.
- **Cadgen selector:** a reference in one specific saved STEP file.

Set unique STEP occurrence labels from instance IDs. Reopen the assembly and construct an instance-to-selector mapping, requiring every instance exactly once. Bind that mapping to the assembly STEP hash. Cadgen selectors are revision-scoped; its prototype IDs are not persistent manufacturing part numbers. Never reuse a prior revision's face reference after a rebuild. [Inspection]

## 6. Units, origins, and transforms

Accept normalized decimal millimeter strings from the compiler. The CAD assembly world is **+X width, +Y depth, +Z height**. Each part is centered at its local origin, with local **X=L, Y=W, Z=T** and extents `[-L/2,+L/2]`, `[-W/2,+W/2]`, `[-T/2,+T/2]`. Grain and edge identity remain part-local metadata. Apply the canonical placement matrices from the domain ledger.

The upstream exporter already performs:

```text
C(x, y, z) = (x, z, -y) * 0.001
```

Thus GLB vertices are Y-up meters. Do not apply `C` to them again. Convert each CAD instance transform using `M_glb = C * M_cad * inverse(C)`. For the rotation block, conjugate by the axis-rotation matrix; convert translations with `C`. The uniform unit scale cancels out of rotation. [GLB implementation]

Test a rectangular, asymmetric fixture with an off-center feature. Verify transformed corners and world bounding boxes against saved assembly STEP. A square or centered cube cannot reliably expose reversed depth, double scaling, or an axis swap.

## 7. Drawings and profile exports

The selected release uses **clearly metric native cadgen sheets** plus **application-owned dual-unit packet and cut tables**. Native PDF dimensions are measured from saved geometry; their labels stay millimeters. ReportLab owns the project packet described in [CONSTRUCTION-AND-EXPORTS.md](CONSTRUCTION-AND-EXPORTS.md).

Do not change `Sheet(units="in")` to obtain imperial drawings. In this pin, that field changes title text while dimension calculations remain millimeters. Any future imperial native sheet requires actual measured-value conversion and tests for every dimension/tolerance. The dual-unit tables must convert canonical values, preserve specified precision, and never feed rounded inch labels back into geometry. [Drawing implementation]

Use the native drawing API's supported orthographic/isometric views and measured dimensions. Match the real sheet size; do not relabel A4 as Letter or claim a scaled page is a 1:1 template. Render the actual PDF and fix clipping, annotation overlap, and labels that refer to the wrong part. Construction instructions and completeness status come from the app's recipe contract, not from geometric contact. [Drawing API]

When DXF is implemented, export nominal millimeter profiles at 1:1 in a documented part-local XY orientation. Derive profiles from the trusted geometry. Keep marking geometry on separate layers; verify closed cutting loops and reject duplicates/degenerate entities. Saw kerf belongs to stock planning; router compensation belongs to the downstream CAM decision. Neither silently changes the nominal part profile. [DXF]

DXF and STEP are geometry handoffs. Do not call them router G-code. The upstream G-code workflow uses OrcaSlicer for additive manufacturing. [G-code]

## 8. Process control and application boundary

[API-AND-JOBS.md](API-AND-JOBS.md) owns all `/api/v1` routes, persistence, publication, cancellation, and recovery. The CAD adapter returns artifacts and evidence; it does not update project database records. Keep native CAD work out of request handlers and execute it in a separate supervised process.

For V1, disable cadgen's shared daemon and run one application CAD job at a time. Its warm daemon can create additional workers, and its heartbeat mechanism does not impose a hard deadline on a computing model. Use the app's initial 120-second generation and 120-second export budgets, then adjust them only with recorded measurements. [Daemon contract]

Pass app-scoped worker settings:

```text
CADGEN_DAEMON=0
CADGEN_JOBS=1
CADGEN_CACHE_DIR=<app cache for the locked runtime>
CADGEN_STATE_DIR=<app cadgen state>
CADGEN_TELEMETRY=0
CADGEN_NODE=<absolute approved Node executable>
MPLCONFIGDIR=<app writable matplotlib cache>
```

These cadgen settings are supported upstream. Separate state avoids modifying a user's unrelated CAD configuration. Retain artifacts independently of the cache. [Daemon contract] [State directory] [Telemetry] [Node runtime]

Use an absolute interpreter, argument arrays, `shell=False`, explicit UTF-8, bounded logs, and an allowlisted environment. Preserve necessary Windows runtime variables, including `SystemRoot`. **No AI keys or unrelated credentials enter CAD workers.** User payloads cannot choose executables, imports, paths, Python, shell commands, or JavaScript sidecars. [Subprocess]

On Windows, associate the worker and descendants with a Job Object before they can escape supervision; disallow breakaway and enable kill-on-close. Cancellation, timeout, and coordinator shutdown must end all owned Python, Node, and browser descendants. On WSL/Linux, use an owned process group/session and terminate the whole group. Test both behavior and cleanup; killing only the first PID is insufficient. [Job limits]

A process boundary contains crashes; it is not an untrusted-code sandbox. Only reviewed templates and validated data execute. Hosted arbitrary-code generation is outside this architecture.

Keep local services loopback-bound, with the Host/origin and artifact-path restrictions in the API contract. Do not expose the upstream unauthenticated viewer as a LAN backend. Its source explicitly documents browser-origin and DNS-rebinding concerns even for localhost. [Viewer security]

If native Windows refuses the OCP module, report the specific preflight failure and use the documented WSL fallback. **Do not change OS security settings.** Keep WSL runtime data and caches in its Linux filesystem; Windows accesses the local application through the browser. [Windows diagnostic] [WSL files]

## 9. Milestone gates

| Milestone | CAD integration exit evidence |
|---|---|
| **M0 — Integration** | Pinned runtime builds the spike; STEP reopens; GLB units/orientation and per-definition strategy work; a snapshot and native metric PDF render; versions, timings, and Windows failures are recorded |
| **M1 — Engine** | Baseline and mutation fixtures produce the correct genuine solids, assembly placements, CSV, manifest, and measured results without AI or browser |
| **M2 — Local app** | Seven baseline panels are individually selectable; instance identity survives edits; stale jobs cannot replace newer views; cancellation/restart leave no partial successful revision |
| **M3 — Documents and recipe** | Metric native sheets and dual-unit packet/tables agree with saved geometry; construction completeness remains distinct from dimensional checks |
| **M4 — Stock and cost** | Stock/cost consumers use the same manufacturing registry; allowances, kerf and grouping changes do not alter finished CAD dimensions |
| **M5 — AI** | Accepted proposals pass the existing compiler and CAD path; missing provider configuration leaves manual generation usable; no generated code reaches workers |
| **M6 — Release** | Clean-machine setup, offline prepared-runtime generation, export/import, crash/timeout recovery, process cleanup, and measured resource budgets pass |

Across these gates, require valid positive-volume board solids, correct saved dimensions and counts, explicit permitted contacts, no unexpected overlap, unique instance labels, and coherent revision hashes. Include the asymmetric transform fixture and a `25.4 mm = 1 inch` table fixture. Treat inspection exceptions and unperformed checks as unresolved, never as passes.

## Source links

The upstream links below are primary source contracts or implementation evidence at the selected commit. Python and Microsoft links document operating-system process behavior. They explain the integration choices; the application requirements and milestone gates above remain this project's contract.

[Release]: https://github.com/earthtojake/text-to-cad/releases/tag/v0.7.21
[Dependencies]: https://github.com/earthtojake/text-to-cad/blob/24573128ceaab564f497d7c12f995c41784c9539/packages/cadgen/pyproject.toml
[CAD skill]: https://github.com/earthtojake/text-to-cad/blob/24573128ceaab564f497d7c12f995c41784c9539/skills/cad/SKILL.md
[Model contract]: https://github.com/earthtojake/text-to-cad/blob/24573128ceaab564f497d7c12f995c41784c9539/skills/cad/references/step-generation.md
[STEP API]: https://github.com/earthtojake/text-to-cad/blob/24573128ceaab564f497d7c12f995c41784c9539/packages/cadgen/src/cadgen/step.py
[GLB API]: https://github.com/earthtojake/text-to-cad/blob/24573128ceaab564f497d7c12f995c41784c9539/packages/cadgen/src/cadgen/glb.py
[Mesh exports]: https://github.com/earthtojake/text-to-cad/blob/24573128ceaab564f497d7c12f995c41784c9539/skills/cad/references/supported-exports.md
[GLB implementation]: https://github.com/earthtojake/text-to-cad/blob/24573128ceaab564f497d7c12f995c41784c9539/packages/core/src/lib/export/packageMeshExport.js
[Inspection]: https://github.com/earthtojake/text-to-cad/blob/24573128ceaab564f497d7c12f995c41784c9539/skills/cad/references/inspection-and-validation.md
[Drawing API]: https://github.com/earthtojake/text-to-cad/blob/24573128ceaab564f497d7c12f995c41784c9539/skills/engineering-drawing/references/sheet-api.md
[Drawing implementation]: https://github.com/earthtojake/text-to-cad/blob/24573128ceaab564f497d7c12f995c41784c9539/packages/cadgen/src/cadgen/eng_drawing.py
[DXF]: https://github.com/earthtojake/text-to-cad/blob/24573128ceaab564f497d7c12f995c41784c9539/skills/dxf/SKILL.md
[G-code]: https://github.com/earthtojake/text-to-cad/blob/24573128ceaab564f497d7c12f995c41784c9539/skills/gcode/SKILL.md
[Daemon contract]: https://github.com/earthtojake/text-to-cad/blob/24573128ceaab564f497d7c12f995c41784c9539/packages/cadgen/STORE.md
[Node runtime]: https://github.com/earthtojake/text-to-cad/blob/24573128ceaab564f497d7c12f995c41784c9539/packages/cadgen/src/cadgen/_internal/node_runtime.py
[State directory]: https://github.com/earthtojake/text-to-cad/blob/24573128ceaab564f497d7c12f995c41784c9539/packages/cadgen/src/cadgen/viewer/recents.py
[Telemetry]: https://github.com/earthtojake/text-to-cad/blob/24573128ceaab564f497d7c12f995c41784c9539/packages/cadgen/src/cadgen/cli/telemetry.py
[Subprocess]: https://docs.python.org/3.13/library/subprocess.html
[Job limits]: https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_limit_information
[Viewer security]: https://github.com/earthtojake/text-to-cad/blob/24573128ceaab564f497d7c12f995c41784c9539/packages/cadgen/src/cadgen/viewer/http_app.py
[Windows diagnostic]: https://github.com/earthtojake/text-to-cad/blob/24573128ceaab564f497d7c12f995c41784c9539/packages/cadgen/src/cadgen/_internal/kernel_load_hint.py
[WSL files]: https://learn.microsoft.com/en-us/windows/wsl/filesystems
