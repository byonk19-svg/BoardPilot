# Explain assembly-guide compatibility beside Update design

Status: Complete and verified
Baseline: b096a18 (task-start HEAD; full SHA captured in verification).

The user approved an obvious resizing warning beside Update design, a clear
explanation when the Build guide will not apply, easy access to Revert draft,
desktop/mobile/keyboard/revision checks, local/offline only, and no push.

Use the installed method's authoritative limits. Do not change recipes, CAD,
dimensions, measured materials, or saved files to make a draft compatible.
Expose only the catalog metadata needed to explain the supported measurements
and shelf count. Incompatible and incomplete settings still allow geometric
designs, cut lists and measured drawings; never promise assembly instructions.
Keep compatible, unselected, checking and invalid-input states honest.

Place one readable, restrained warning in the apply-controls group, immediately
above Update design and Revert draft. It describes the currently checked draft
or accepted design. Existing download labels continue to describe their own
saved model revision. Announce status politely without moving keyboard focus;
associate Update design with the explanation. Keep the existing revert action
single, visible and directly after Update design in keyboard order.

The user's explicit checks confirm the public seams: catalog/validation HTTP
responses, visible form controls and focus, saved revision/manifest/artifact
downloads. Use isolated stores. Tests cover 36-to-40-inch width, thickness and
shelf-count mismatches, invalid/pending validation, missing optional metadata,
revert, and a genuine resized model/PDF/CSV flow. Transport fixtures may exercise
delays; distinguish them from native CAD/export evidence. Verify 1280px desktop,
390px mobile emulation, keyboard activation/focus, no horizontal overflow, and
unchanged revision-bound files while editing/reverting.

Use Matt's implement -> TDD -> two-axis code review -> local commit workflow,
with accessibility guidance. Existing approval defines the design; routine UI
choices do not need another approval. Preserve unrelated status/review changes,
audit artifacts and document-corpus evidence.
