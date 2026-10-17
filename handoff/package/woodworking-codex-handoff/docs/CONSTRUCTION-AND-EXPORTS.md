# Construction Recipes, Manufacturing, and Exports

The application owns these woodworking rules. Text-to-cad supplies geometry and drawing primitives; it does not supply the complete manufacturing and assembly contract described here.

## 1. Deliverable states

Keep technical generation, construction completeness, and physical review separate.

| State | Available output | Required evidence |
|---|---|---|
| Parameters valid | Derived summary | Schema and mathematical rules passed |
| Geometry checked | STEP, per-part preview assets, resolved parts | Saved geometry agrees with the ledger |
| Design packet complete | Cut list, measured drawings, materials, design ZIP | Requested document and consistency checks passed |
| Construction method complete | Attachment operations, hardware list, step-by-step packet | Trusted applicable recipe resolves every required connection |
| Physical review recorded | The above plus a review record | A real, identified build/review with its scope and outcome |

The baseline example has no construction recipe and must remain a design packet. Its measurements can be exact while its attachment instructions are incomplete. Do not hide that distinction in fine print or a generic warning screen.

A missing recipe does not block dimension editing, model review, CSV export, or a measured design PDF. In the document section that would otherwise show assembly instructions, say what method is missing and offer the available compatible recipes.

## 2. ConstructionRecipe contract

Each recipe is trusted versioned application data plus reviewed generation functions. It must contain:

| Field or output | Meaning |
|---|---|
| recipe_id and version | Stable identity selected by ProjectSpec |
| fingerprint | Hash of recipe data, rules, and referenced templates |
| title and method | Human-readable method, such as a particular pocket-hole system |
| applicability | Supported template, material categories, actual thickness combinations, environmental use, dimension/tool conditions |
| required_tools | Specific capabilities and any jig/model the instructions depend on |
| source_records | Manufacturer/manual links, version/date where available, and the exact rule supported |
| joints | Named connections between specific part instances and local faces/edges |
| operations | Cutting, drilling, machining, gluing, clamping, fastening, and inspection steps |
| hardware | Type/SKU where specified, dimensions, unit, quantity formula, installation requirement |
| dependencies | Which operations must finish before another operation can start |
| illustrations | Geometry-based placement/operation views with stable part IDs |
| completeness_rules | Conditions under which required connections and materials are fully specified |
| review_record | Technical review and separately recorded physical build/review evidence |

A recipe cannot substitute a nominal thickness label for an actual dimension. Its compatibility check must use the same measured thickness as the CAD model.

Define required connection IDs for this template: each horizontal panel joins side_left and side_right; the back attaches to the required carcass edges according to the chosen recipe. A recipe should resolve each required connection exactly once, or explicitly describe a shared operation that resolves multiple connections.

The graph must be acyclic and reference existing parts. A missing edge, duplicate required connection, unavailable tool, undefined hardware size, or incompatible thickness yields an actionable incomplete/incompatible result.

Do not infer a screw diameter, pilot hole, pocket-hole angle, drill-stop setting, glue amount, shelf capacity, or wall-anchor type from a mesh.

## 3. First recipe authoring assignment

During M3, implement the recipe interface and an authored recipe for the supported plywood bookcase. A specific manufacturer's pocket-hole system is a practical candidate because its material-thickness and screw-selection guidance is explicit. The selected jig/manual must actually cover the measured stock and intended joints. The source guidance must be read during implementation.

Kreg's current guidance distinguishes actual thickness from nominal lumber names and distinguishes screw thread choice by material category. Use it as a primary source when selecting such a recipe; it is not proof that any arbitrary bookcase, fastener spacing, or load is approved. [Woodworking sources](SOURCES.md)

The assignment is:

1. Select one concrete construction method compatible with the baseline panel geometry and an explicit tool set.
2. Record the actual-thickness rules and required hardware from appropriate manufacturer documentation.
3. Define which faces receive machining and how a builder identifies them.
4. Define the fastening points and quantity rules, with sourced or explicitly reviewed recipe decisions.
5. Define the separate back-attachment method. Thin-back attachment is not automatically the same joint as two main panels.
6. Establish a feasible machining and assembly order, including access for the required jig, drill, clamps, and fasteners.
7. Produce an operation diagram and an instruction page from the same part ledger.
8. Run a technical completeness review and record what remains for a physical build review.

Do not substitute fake hardware records for the authored recipe. Test fixtures may use a synthetic recipe to exercise completeness logic, but they must identify themselves as test-only and cannot appear in the user-selectable production catalog.

If an external physical review is still pending, finish the software and export the concrete review package. Record that gate accurately. Codex cannot close it by writing “reviewed” into a JSON field.

For quantity derivation, each recipe calculates fastener counts from actual joint instances. If a recipe uses p fastening points at each end of every horizontal panel, its horizontal-joint count is 2 × (n + 2), and that portion of the screw count is p × 2 × (n + 2). The value p, locations, hardware, and whether that scheme is appropriate belong to the reviewed recipe; this algebra supplies no fastening recommendation by itself.

## 4. Part identity and machining

A finished rectangle is not a complete manufacturing identity once holes, grooves, banding, or different faces are involved.

The manufacturing fingerprint must include material ID and actual thickness, local finished dimensions, rough dimensions/allowances, grain policy, directional face designation where supported, edge treatments, and a canonical list of machining operations in local coordinates.

If left and right sides acquire different hole patterns, they are different manufactured definitions even when their bounding boxes match. Their physical instance IDs remain side_left and side_right.

Keep machining in a part-local frame. A hole record identifies its reference face, center coordinates, diameter/depth or specified operation, and source recipe rule. World-space placement is derived from the instance transform. This lets a drawing and a 3D assembly show the same hole without duplicating layout formulas.

Version 1 geometry has no banding, grooves, rebates, or machining deductions. A future feature that adds them must change the template/schema version and explicitly distinguish assembled outside dimensions, substrate cut dimensions, and rough stock dimensions.

## 5. Cut list contract

Produce both an instance list and a grouped cut schedule.

The instance list makes every physical board identifiable. The grouped schedule reduces repetition only when the full manufacturing fingerprint matches. A CSV can contain one grouped row with its member instance IDs; a separate JSON ledger preserves full structure.

Required CSV columns are revision_id, spec_sha256, cut_group_id, definition_id, member_instance_ids, description, material_id, material_name, actual_thickness_mm, quantity, finished_length_mm, finished_width_mm, rough_length_mm, rough_width_mm, grain_axis, machining_summary, and edge_treatment. Display-unit columns may follow; metric canonical columns remain available for exact interchange.

Use a proper CSV writer and a fixed UTF-8 encoding. Protect human-supplied text fields against spreadsheet formula execution; ordinary quoting alone does not neutralize a leading equals sign or similar formula prefix. Numeric canonical columns are generated by the engine.

For the baseline, grouped quantities are 2 sides, 4 horizontal panels, and 1 back. A recipe may split the horizontal or side groups when operations differ. Do not count a group as one physical board.

## 6. Rough blanks and saw kerf

For the supported uniform rough allowance a:

- rough length = finished length + 2a
- rough width = finished width + 2a
- rough thickness = actual stock thickness

Assembly geometry uses finished dimensions. The sheet planner uses rough rectangles. A nonzero allowance requires a finishing-to-size operation in a complete build recipe. Do not create extra material in the CAD assembly to represent a rough blank.

Saw kerf belongs to the cut process and the sheet's removed bands. It does not enlarge finished dimensions. When a cut also separates an offcut, account for that separation even when there is no next part in the row.

## 7. Conservative stock planner

M4 implements a deterministic rectangular guillotine planner. It provides a valid suggested plan, not an optimal yield guarantee.

### Inputs

Use the resolved rough rectangles, actual material IDs/thicknesses, actual stock face dimensions, grain directions, saw kerf, and edge trim. Separate material pools even if sheet dimensions happen to match.

The supplied baseline stock is a declared test input: one purchasable sheet type 2440 × 1220 mm for the 18 mm main material, and another of the same face size for the 6 mm back. Those values are not a claim about a retailer's “4 × 8” stock.

Version 1 assumes each listed sheet type can be purchased in whole sheets. It does not manage on-hand inventory or reserve other projects' offcuts. Add inventory as a later explicit feature.

### Deterministic method

1. Filter stock by material identity and compatible grain.
2. Subtract the declared trim on each edge to get the usable region.
3. Expand grouped quantities into physical instance rectangles.
4. Sort by descending rough L, descending rough W, and lexicographic instance ID.
5. Try permitted orientations. The grain-locked baseline allows 0 or 180 degrees, never 90 degrees; with nondirectional grain, use a stable orientation preference.
6. Fill rows using first fit, with one explicit kerf between adjacent blanks. Row height is the maximum rough W in that row.
7. Separate each row from remaining stock, then separate its individual blanks and any residual offcut. Generate those cuts as a dependency sequence.
8. Open the next compatible sheet when the current candidate cannot fit a part. For the first version, use a single selected stock type per material when several are available; do not claim to optimize across supplier choices.
9. Return placements, cuts, offcuts, removed areas, sheet counts, and any named unplaceable instances.
10. Validate the generated plan independently.

If a proposed cut needs a kerf band that cannot fit under this conservative rectangular-cut model, reject that candidate arrangement and try another. Do not silently erase a sliver, overlap two parts, or declare a globally impossible layout just because this heuristic failed.

A trim band includes the edge-squaring cut's removed material; do not subtract trim plus a second identical kerf. Zero trim represents already usable stock edges. A positive trim smaller than the selected kerf is outside the initial planner's supported trimming model and requires another setting or a later explicitly tested edge treatment.

### Required independent validator

The validator operates on placements and the cut sequence, not the algorithm's own success flag. It checks every requested instance appears exactly once, all parts match their rough dimensions, material pools are correct, grain is honored, every part stays in usable stock, and parts do not overlap.

It then simulates cuts on the current rectangular remnants. Every cut spans its specified active rectangle, consumes the explicit kerf band, produces valid children, and obeys dependencies. The leaf regions classify into requested parts or offcuts. Area accounting must reconcile initial usable material with parts, kerf, and offcuts.

Do not call a rectangle packing a cutting sequence until that simulation passes.

### Baseline and exact-fit checks

Use the placement and cut-band tables in DATA-AND-GEOMETRY.md and examples/bookcase-expected.json. After trimming, the baseline uses one main-material sheet and one back-material sheet. Its main sheet requires nine internal cuts under the documented sequence; the back requires two.

The synthetic three-part fixture uses a 306.4 × 100 mm sheet and three 100 × 100 mm blanks with 3.2 mm kerf. It fits with two kerfs because the last part ends at the stock boundary. A 300 mm sheet fails even though the sum of part areas equals its area.

The distinction matters: no trailing kerf is needed at an existing finished boundary; a cut is needed when separating the last part from remaining stock.

## 8. Materials and cost estimates

For a verified layout, the purchasing quantity is the count of whole sheets used for each stock type. Without a verified layout, the application can show part area and an explicitly labeled area lower bound, but not a claimed sufficient sheet count.

Keep three different numbers distinct: purchased material cost, value of material consumed in finished parts under a declared allocation method, and complete project cost including hardware/consumables/other expenses.

Use user-entered USD prices initially. Store prices as fixed decimal strings; calculate with decimal arithmetic. Round displayed currency to cents with a stated rule. Missing sheet/hardware prices are null and keep the affected subtotal incomplete.

A demonstration may use synthetic prices of USD 70.00 for the main sheet and USD 25.00 for the back sheet. With the verified baseline layout, the known sheet-purchase subtotal is USD 95.00. This is a test value, not a current retail estimate. Hardware, finish, tax, shipping, and tools remain excluded unless supplied.

A recipe's hardware quantities do not automatically provide retail package quantities. If a chosen SKU is sold in packs, derive packs purchased using the explicit pack size and round up. Retain required count and purchased count separately.

Do not multiply every material figure by an unexplained waste percentage. The layout already accounts for cutting loss and unused material. Optional contingency purchases are a separate user choice.

## 9. Measured PDF generation

### Selected release behavior

Application-owned project pages use Letter by default, with A4 selectable. Native cadgen part drawings remain clearly labeled in millimeters and use the native supported ISO sheet sizes. The application cut schedules and summary pages provide dual units through its own real conversion/formatting functions.

In the pinned upstream code, the Sheet units string changes a label but does not convert measured dimensions. Do not switch that string to “in” and consider imperial support complete. [CAD-INTEGRATION.md](CAD-INTEGRATION.md) explains the source and required test.

Use actual measured geometry and the resolved ledger to generate dimensions. Convert 25.4 mm into 1 inch when producing an imperial label. If a label is rounded to the nearest 1/64 in, identify it as approximate when it is not exact, and retain a metric equivalent. Never substitute that rounded value into geometry.

Do not invent fabrication tolerances. Numerical kernel tolerance, displayed precision, and an acceptable woodworking fit are different things. A dimension without a specified fabrication tolerance is nominal.

### Packet layout

The minimum design packet contains a cover/overview, outside assembly views, clear-opening dimensions, labeled part schedule, grouped cut list, measured part pages, material summary, and revision details. Recipe instructions and stock-layout pages appear when those outputs are complete.

Use clear part IDs in every relevant view. Text must remain readable at ordinary print size; use at least approximately 9-point body/dimension text on application pages as a starting layout requirement. Provide adequate margins and avoid color-only distinctions.

Render every fixture packet page to images for visual inspection. Check clipped views, overlapping labels, text crossing geometry, wrong face orientation, inconsistent units, tiny text, empty pages, and repeated or missing part IDs. Text extraction verifies values; it cannot establish visual readability.

Native projected orthographic/isometric views do not supply arbitrary section/detail views. An application-authored joinery illustration must be clearly a construction illustration and must derive dimensions from the recipe/ledger, not from an AI-generated decorative image.

## 10. Assembly instructions

A completed recipe's instructions use short ordered steps with the affected part IDs, action, relevant measurements, required hardware, orientation illustration, and a check that a builder can actually perform.

The sequence should account for cutting and labeling parts, machining accessible faces before assembly, dry fitting where the recipe calls for it, joining subassemblies in a feasible order, installing the back, and performing the recipe's final checks. Quantities come from the recipe graph.

An exploded view is useful for identifying locations. It must not be presented as proof that a drill can reach a hidden pocket or that a partly assembled structure is stable.

When wall attachment or other context-specific installation is relevant to a selected template, the recipe must identify the required choice and source rather than inventing hardware without knowing the substrate. Keep that information next to the installation step.

## 11. Geometry and project files

The default geometry outputs are a whole-assembly STEP and one maintained STEP plus one GLB per unique part definition. The app's manifest reconstructs instances for selection. A required step-instance-map.json sidecar binds every instance to its current saved assembly occurrence and the assembly file hash. An optional merged assembly GLB can be a preview download but does not replace instance identity.

A project package contains project.json, resolved-project.json, cut-list.csv, material/hardware records, the requested PDF files, assembly.step, per-definition STEP and GLB files, step-instance-map.json, and manifest.json. Stock-layout data/diagrams appear after their gate passes. Include a README stating units, revision, template/recipe versions, and how to reopen the supported project.

Document and stock jobs publish a new cumulative immutable artifact set based on one explicitly identified source geometry set from the same revision. The resulting set retains all required core files. A failed document job preserves the prior complete geometry set. Manifest/package defaults resolve the revision's stored preferred set, and each queued ZIP freezes that choice at submission; see API-AND-JOBS.md.

The manifest inventory excludes itself and the enclosing ZIP to avoid checksum cycles. The database records the ZIP and manifest hashes externally. Export filenames are safe server-generated names; the project title remains display metadata.

Later DXF profiles are local XY, millimeter, 1:1 geometry. Use uncompensated nominal profiles by default. Separate cutting outlines from marking geometry and exclude projected drawing views or dimension text from cutting layers. Router tool selection, feeds, depths, workholding, and G-code remain a separate CAM task.

## 12. Release evidence

M3 proves readable, dimensionally correct design packets and truthful recipe completeness behavior. M4 proves stock placements with executable cut-sequence validation and transparent pricing assumptions. M6 proves a coherent export/import package.

A real physical template review records the project/recipe fingerprints, measured stock, construction method, actual issues encountered, changes made, and the scope of any conclusion. It does not silently grant a universal load rating to every parameter variation.
