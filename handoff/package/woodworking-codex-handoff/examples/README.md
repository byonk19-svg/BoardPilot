# Example Contracts and Expected Results

These are machine-readable fixtures for Codex to use while implementing the application. They are not completed CAD files or verified furniture construction instructions.

## Project specifications

All nine project files validate against spec/project.schema.json. Each mutation starts independently from bookcase-baseline.json.

| File | Change from baseline |
|---|---|
| [bookcase-baseline.json](bookcase-baseline.json) | 762 × 304.8 × 914.4 mm; actual main/back thickness 18/6 mm; two fixed shelves |
| [bookcase-width-36in.json](bookcase-width-36in.json) | Outside width 914.4 mm |
| [bookcase-thickness-19mm.json](bookcase-thickness-19mm.json) | Actual main thickness 19 mm |
| [bookcase-depth-14in.json](bookcase-depth-14in.json) | Outside depth 355.6 mm, still including the back |
| [bookcase-zero-shelves.json](bookcase-zero-shelves.json) | No fixed shelves |
| [bookcase-one-shelf.json](bookcase-one-shelf.json) | One fixed shelf |
| [bookcase-3-shelves.json](bookcase-3-shelves.json) | Three fixed shelves |
| [bookcase-4-shelves.json](bookcase-4-shelves.json) | Four fixed shelves |
| [bookcase-back-9mm.json](bookcase-back-9mm.json) | Actual back thickness 9 mm, outside depth unchanged |

Each file includes a null construction recipe and unknown sheet prices. Nominal material labels are display metadata. A stock-sheet material reference inherits its actual thickness from the material record; the stock row does not contain a second thickness field.

## Exact expected results

[bookcase-expected.json](bookcase-expected.json) gives the canonical input hash, dimensions, quantities, stable IDs, local part sizes, rigid placement matrices, centers, expected bounding boxes, clear openings, volume, and construction state for all nine projects.

The same file includes a baseline suggested stock layout and an explicit cut tree for each material sheet. Internal cuts consume source regions and produce named children. Leaf regions identify physical parts or offcuts. Area totals reconcile finished parts, internal kerf, and offcuts to the usable sheet. Reserved edge bands are accounted for separately.

All dimensions are declared mathematical values. For the 19 mm main-material variant, the exact clear height is represented as numerator 4192 and denominator 15. Quantized positions are HALF_EVEN to 0.000001 mm. Re-measured clear openings differ by at most the stated numerical tolerance; this is arithmetic precision, not a fabrication tolerance.

No artifact manifest example is fabricated because the application has not produced real artifact bytes. Use [the manifest schema](../spec/artifact-manifest.schema.json) to validate the actual hashes and files generated during implementation. Never fill it with fake hashes and call it a successful build.

## Additional fixtures

| File | Purpose |
|---|---|
| [input-cases.json](input-cases.json) | Exact unit parsing, invalid precision/expressions, and impossible dimensions |
| [kerf-exact-fit.json](kerf-exact-fit.json) | Three 100 mm parts on 306.4 mm stock with two 3.2 mm kerfs |
| [ai-width-proposal.json](ai-width-proposal.json) | A restricted width change from 30 to 36 inches |

The AI proposal references fixture_revision_001 as a test identifier. A real request must use the actual current project revision ID. The supplied proposal validates against [the AI proposal schema](../spec/ai-proposal.schema.json), but applicability still requires a matching base revision.

## How to use the fixtures

1. Load the project through the same domain validation service used by the API.
2. Compile its deterministic part ledger.
3. Compare to the expected arithmetic records.
4. Generate genuine CAD and reopen the saved artifacts.
5. Measure their dimensions and placements independently and compare them to the ledger.
6. Generate the CSV, measured PDF, and stock plan requested by the milestone.
7. Check file/revision consistency and exercise the same project in the UI.

Do not paste expected numbers into renderers to force matching output. The expected file is a test oracle; the domain compiler derives results from the input contract.

## Handoff preparation checks

The fixture arithmetic, matrix orientation, box bounds, non-overlap, total volumes, and cut-tree area partitions were checked while preparing this package. JSON Schema checks and package cross-reference checks are recorded in the handoff validation note.

The browser application, CAD runtime integration, generated PDF layout, native Windows process handling, and physical furniture have not been run by this handoff. Their acceptance checks are specified in [ACCEPTANCE-TESTS.md](../docs/ACCEPTANCE-TESTS.md).
