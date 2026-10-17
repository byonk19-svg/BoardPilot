# Get plans implementation plan

Goal: complete the approved PRD and verify the real offline workflow.

- [x] Snapshot unrelated dirty files and the original sample before testing.
- [x] Add browser regressions at the existing form/HTTP/job seams; observe failure
  on the current build because Get plans is absent.
- [x] Add planWorkflow.ts to chain existing documents/stock/package jobs using frozen
  result IDs, recover run/step/attempt from job keys, and validate each binding.
- [x] Add Plans.tsx for progress, retry, cancellation and exact bundle downloads;
  integrate as the primary action in ProjectOutputs with secondary tools retained.
- [x] Run focused protocol tests and repair failures without weakening assertions.
- [x] Exercise a real revised bookcase, reload during drawings, lose a stock
  acknowledgement, retry, download the complete ZIP and independently verify bytes.
- [x] Run strict TypeScript/build, canonical backend tests and full frontend tests.
- [x] Review final changes, inspect desktop/narrow screenshots, record exact
  evidence/status and confirm original sample/unrelated files remain unchanged.

Ownership is kept sequential because orchestration and UI share one contract.
No new dependencies or backend architecture are needed.
