# Beginner guide for the sample bookcase

Status: completed and verified; physical/human gates remain explicit

Approved outcome: the app generates a beginner-friendly PDF with a compatible
construction method and illustrated assembly for the existing sample. Keep its
914.4 x 914.4 x 304.8 mm outside dimensions, two shelves, complete material records
and actual 18 mm / 6 mm thicknesses unchanged. Local/offline runtime; no push.

Use a separately versioned, narrowly applicable through-side screw-and-glue
recipe. Main fasteners are #8 x 2 in flat-head wood screws; the applied back uses
#6 x 5/8 in shallow flush-head wood screws. Primary published bookcase methods and a screw
supplier's drilling chart support the method/sizes. Exact placement and depth
stops are authored geometric adaptations, with an offcut drill/drive check.
No pocket-jig stock substitution, routed housing, extra furniture parts, load
rating or physical approval is inferred.

## Acceptance

1. Exact sample parameters resolve to a complete technical recipe. Different
   thicknesses/depth/dimensions/shelf count are reported incompatible. The old
   Kreg recipe and its fingerprint remain unchanged.
2. Every required connection has explicit hardware, quantity, geometric layout,
   entry face/axis, penetration and dependency-ordered operations. True drilling
   entries are checked separately from canonical layout datums. Shared side-blank
   preparation patterns are equivalent under a proper rotation, not reflection.
3. The PDF starts with plain A-G part names and the exact cut list/materials,
   tools/hardware, safe drill-depth/workholding instructions, shelf marking from
   named edges, illustrated assembly, squaring/back installation, curing and
   before-use restraint guidance. Technical coordinates remain in an appendix.
4. Illustrations derive from the same checked recipe/revision as text and counts.
   No pictures or step prose claim CAD-machined holes or a tested physical build.
5. Get plans continues to bind CAD, CSV, drawings, stock and ZIP to one revision.
   Existing unselected and Kreg packets, old immutable output and offline/manual
   workflows remain valid. No dependencies or CAD pins change.
6. Test exact dimensions/cuts, all fastening stations and adversarial failures,
   layout/illustration coverage, Letter/A4, and a genuine UI CAD-to-PDF/ZIP flow.
   Render and inspect every final guide page. Run relevant canonical checks.
7. Apply the method to a new revision of the user's sample only after isolated
   verification; compare entire dimensions/materials with revision 2. Preserve
   prior revisions/downloads and unrelated dirty files. Generate/open the local
   finished PDF and record exact commands/evidence/status.

## Implementation plan

- [x] Add failing recipe and PDF tests for this exact sample.
- [x] Add isolated catalog/graph/validator/planner modules and public dispatch;
  keep legacy graph.py/planning.py bytes and recipe fingerprint stable.
- [x] Add a beginner Packet subclass, illustrated steps and conditional document
  validation/provenance. Retain technical appendix and historical format readers.
- [x] Update method-agnostic UI wording and add genuine browser acceptance.
- [x] Run focused tests, render previews, fix real failures and review the diff.
- [x] Run backend/build and full frontend/native workflows in an isolated store.
- [x] Update the user's sample to the verified method with invariant dimensions
  and materials, generate/open its PDF, inspect all pages and record results.

Published guidance is not certification of this exact adaptation. Actual stock,
pilot performance, workholding, fastener seating and site anchoring require the
builder's checks; physical review remains unperformed and load rating unknown.
