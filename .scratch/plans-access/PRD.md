# Plans beside the saved model

Status: complete and verified

User-approved outcome: keep Get plans beside the model, label the illustrated
PDF Build guide PDF, remove duplicate downloads, and verify desktop, mobile,
keyboard access and revision consistency. Local/offline only; no push.

## Confirmed test seams

The user's explicit verification request confirms the visible browser UI and
public revision/artifact/download HTTP boundaries. Test keyboard operations,
layout, accessible labels, visible download identity, and real downloaded files.
Do not test private React state or query storage as a behavior assertion.
Transport fixtures may exercise failures/provenance; genuine CAD/PDF/ZIP output
is verified separately in an isolated local store.

## Acceptance

1. One Get plans controller is adjacent to the saved model on desktop, before
   the viewer on narrow layouts, and reachable with the narrow Plans shortcut.
   Keyboard order and focus are usable; controls do not overflow the page.
2. The illustrated complete guide is labelled Build guide PDF. Ordinary design
   packets and incompatible/unselected methods retain an honest design-PDF
   label. Use validated manifest evidence of the illustrated-guide artifact.
3. Each promoted download appears once. The cut-list CSV remains at its cut
   list. PDF/stock links in the plans bundle use that bundle's frozen manifest;
   additional/current files remain accessible without duplicate links.
4. The moved controller retains retry, cancellation, recovery and frozen-source
   behavior. Individual output jobs and Get plans remain mutually exclusive.
   Leaving a revision cannot leak activity/download state into another one.
5. Draft/building/last-successful identities remain explicit. Model, cut list,
   guide, drawings, stock and ZIP remain bound to the same saved revision;
   backend, recipe, CAD and material/dimension logic are unchanged.
6. Run focused red-green UI tests, TypeScript checks, the full backend/build and
   frontend suite at the end, including existing genuine workflows. Inspect
   desktop/narrow screenshots and directly exercise keyboard/download behavior.
7. Review against the starting HEAD on Standards and Spec axes, resolve
   findings, record exact evidence/commands in implementation status, and commit
   only this work on the current branch. Preserve unrelated dirty work.

## Implementation outline

- Hoist the existing single Plans controller next to the viewer. Keep shared
  activity and promoted-file ownership scoped to the displayed revision.
- Share the PDF-label rule. Suppress promoted files in lower output links and
  list only additional files in the raw revision-file disclosure.
- Preserve frozen plans downloads when later individual output sets differ.
- Add behavior tests one slice at a time, then run real/native acceptance and
  two-axis review before the local commit.

Review baseline is recorded in `.verification/plans-access-20261020/baseline.txt`.
Startup/launcher work, cut-list redesign and method-warning redesign are outside
this slice. No visual-system redesign or paid provider integration is included.
