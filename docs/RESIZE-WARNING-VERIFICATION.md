# Resizing warning verification

Spec: `.scratch/resize-warning/PRD.md`.
Review baseline: `b096a1895e10e7f8087686ec056c940ae232e758`.

The apply-controls group now shows a readable warning when the currently checked
settings are incompatible or incomplete for the selected assembly method. It
explains the missing matching Build guide/assembly steps, the geometric outputs
still available, and the separate Update design / Get plans actions. Supported
dimensions, actual thicknesses and shelf count come from the installed catalog.
Optional missing metadata produces a truthful fallback. No recipe limit is
relaxed and no input is changed to fit a method.

The warning is a named polite status associated with Update design. Revert draft
is a single full-width native button directly after Update design in focus
order. Enter/Space activate it and focus returns to Outside width after the form
is restored. A saved-model download note uses the shown revision, not the draft.
An accepted incompatible revision is described as a design rather than a draft.

Pending/invalid input never displays an old compatibility decision. Review found
that saved-project switching retained the previous validation result. A public
delayed-response regression reproduced it; project restoration now invalidates
that result, and the status gives checking precedence. Both switching directions
pass. Compatible/unselected states retain their existing honest wording.

## Verification evidence

- Public API metadata test: red before catalog limits were exposed; green after.
- Five focused browser cases passed: desktop warning/keyboard revert, 390px
  mobile material/shelf/unit changes, pending/invalid input, missing optional
  catalog metadata, and switching saved projects in both directions.
- Canonical backend: **295 passed, 22 existing native opt-in skips**, 139.59 s.
  Production typecheck/build passed. Existing Python warnings and the existing
  large-bundle advisory remain nonblocking.
- The actual updated app was reopened on 8777 and showed the user's unchanged
  revision 3, seven panels, 36 × 36 × 12 inches, and Plans ready. Only an isolated
  project was edited during manual browser inspection.

Final broad browser run: **55 passed, 2 failed, 1 opt-in skip**, no flakies.
All six new resizing cases passed, including genuine 36-to40 CAD/CSV/PDF
consistency and byte-preserved old guide. Two affected legacy export cases passed
on focused retest (**2/2**, 144.008 s). All 57 non-opt-in case
behaviors are covered across those runs; the entire suite was not rerun after
the test-only helper repair. Final typecheck passed. The new warning's body
contrast is 10.54:1. Desktop/mobile screenshots were visually inspected. Detailed reports, traces, before/after snapshots and native artifacts
are retained under `.verification/resize-warning-20261020/`. Compact evidence is
copied to `evidence/resize-warning-20261020/`.

The broad run exposed an existing PDF-test timing mismatch: a 60-second visible
download wait expired while the native document job later succeeded in 69.758 s,
inside its unchanged 120-second deadline. Its dependent production-output case
then lacked the expected revision-2 fixture. Both document submission paths now
capture the actual POST 202 job and use the existing terminal-success assertion
before checking the download. No file assertions or runtime limits were removed.
Original results and focused retest results are reported separately.

## Standards

The project-switch finding was fixed and rechecked. Independent Standards review
has **zero open documented-standard violations or actionable advisory smells**.
The PDF-verification helper repair also passed the independent recheck.

## Spec

Independent Spec review has **zero open findings**, including the project-switch
fix, explicit Update/Get plans copy, and the necessary verification-helper repair.

Mobile checks are browser viewport emulation; no physical phone or screen-reader
session is claimed. Live-region markup and keyboard behavior are verified, not
spoken announcement quality or a complete accessibility conformance audit.
Physical fabrication and load review remain separate existing gates.
