# Handoff Validation

Prepared 2026-10-13. This note records checks on the implementation handoff, not acceptance results for a completed application.

## Checks completed

- All three JSON Schemas are valid draft 2020-12 schemas.
- All nine canonical project examples validate against the project schema.
- The supplied AI width proposal validates against the restricted proposal schema.
- Expected-input hashes agree with the canonical example contents.
- Definition quantities, member-instance IDs, and instance counts agree across the expected results.
- Exact Fraction arithmetic agrees with the independently supplied baseline and mutation volumes.
- Rotation matrices are orthonormal with determinant +1; box placements have the expected outside bounds and no volumetric overlap.
- Main/back stock cut trees partition usable areas into the declared parts, kerf, and offcuts.
- Ordinary relative Markdown links in the package resolve to included files.
- Independent reviews checked product scope, CAD integration, source boundaries, and cross-file consistency.

The reviews resolved the material integration details: merged static GLB identity, native drawing unit labels, retained part STEPs, hash-bound STEP selector mappings, cumulative artifact sets, proposal idempotency, raw-input precision, and construction-recipe completeness.

## Implementation checks still to perform

Codex must run the actual CAD runtime, saved-solid measurements, native Windows/WSL setup, process lifecycle, API/browser flows, generated PDF rendering, live-provider checks when configured, and export/import checks specified in ACCEPTANCE-TESTS.md.

The recipe-free reference is a geometry/design fixture. A complete construction recipe and any physical build review require their own evidence. No furniture load capacity or real build result is claimed by this handoff.

## Package contents

START-HERE.md contains the execution prompt and reading order. WOODWORKING-PLATFORM-PLAN.md sets the product and architecture. The detailed documents, schemas, and exact examples are intended to remain together in the application repository as its initial specification.

PACKAGE-INDEX.json inventories the handoff files and their SHA-256 values, excluding the index itself and the enclosing ZIP. It is a handoff integrity index, separate from the application's proposed artifact-manifest format.
