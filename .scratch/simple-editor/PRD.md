# Simple woodworking editor

Status: ready-for-agent

The user approved this bounded usability pass after reviewing the working app:
basic measurements first, specialist controls under Advanced, consistent display
units, and a clear Update design action. The combined Get plans workflow is a
separate later task.

## Required behavior

1. Width, height, depth, fixed shelf count, and actual main/back thickness remain
   directly visible. Keep project name and display-unit selection available.
   Nominal labels, grain, construction recipe, manufacturing/stock and PDF options
   live under one closed-by-default Advanced settings disclosure. Missing assembly
   method/readiness stays visible. Advanced errors must be discoverable.
2. Use Create design for a new project and Update design for an existing project.
   Keep one primary submission control. Preserve validation, draft recovery,
   retry/cancellation, duplicate-request protection and saved-revision identity.
3. Unit switching converts validated dimension inputs exactly and never resets
   unsaved valid measurements. Invalid/unvalidated raw text keeps its original
   explicit unit rather than being reinterpreted. Actual thickness inputs stay
   explicitly measured in millimeters.
4. Model bounds name width, height and depth. Use the selected display unit for
   bounds, draft summaries, detail measurements and cut-list dimensions. Inch
   fractions follow the revision's fraction denominator, mark rounding as
   approximate, and retain exact millimeters. Conversion is presentation only.
5. While edits are pending, the model and cut list still show the verified saved
   revision's dimensions. CSVs, CAD, PDFs and export contracts stay unchanged.
6. Keep desktop and narrow layouts usable without document-wide horizontal
   overflow. Small-screen users must be able to reach the model and cut list
   without scrolling through specialist controls.

## Verification seams

The approved editing workflow is tested through its existing browser/form/API
boundaries. Add focused browser regressions for basic/Advanced disclosure,
invalid fields and unit switching with a pending draft. Exercise a real native
edit to establish model/CSV coherence. Test public presentation formatting with
literal conversions and precision cases. Run strict TypeScript, the production
build, the standard backend checks and the full frontend suite at the end.

Review the feature against HEAD `dece1036`, excluding pre-existing document-test
follow-up changes. Preserve those changes and all user data. Keep everything
local, including skill/tracker setup; do not push. Commit the reviewed feature on
the current branch after verification, as the selected implement flow requires.
