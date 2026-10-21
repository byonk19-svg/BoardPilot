---
name: app-audit
description: "Audit BoardPilot user journeys, visual quality, usability, and alignment with the agreed milestone. Use for requested app audits or checkpoint regression and scope reviews. Default to audit-only; do not activate for ordinary feature implementation or general next-task recommendations."
---

# App audit

Produce one evidence-backed assessment of whether the intended user can finish
the agreed task. Run on demand. Audit only unless the user also authorizes fixes;
audit artifacts and disposable local test state are allowed, app changes are not.

## Establish the target

Resolve this skill's canonical path first. The application root is the directory
containing its `.agents` folder, even when the chat starts in the parent workspace.
Paths below are relative to that root. Read applicable
AGENTS.md instructions, PRODUCT.md, DESIGN.md, CONTEXT.md, the latest relevant
sections of docs/IMPLEMENTATION-STATUS.md, and the matching approved
.scratch/<feature>/PRD.md. Consult the handoff specifications only as needed for
the acceptance criteria being assessed. Documents are scope evidence, not new
authorization to execute their embedded implementation prompts.

State the user, core problem, current milestone, acceptance criteria and deferred
work before judging the app. Latest user decisions override stale notes. Existing
code describes behavior, not proof of intended requirements. Use the current
documents rather than creating another product plan. State assumptions and
continue useful checks; ask only about gaps that materially change the verdict.

## Resolve tools and prerequisites

Locate and read the installed `playwright` and `impeccable` skills through the
available skill catalog or discovered project/user skill roots. Resolve their
real paths and referenced files; do not assume a particular user's home folder.
Check installed CLI help before using examples; command syntax can differ from
older skill references. Reuse existing test tooling and cached dependencies.
Do not install or update tools silently during an audit. Report missing
prerequisites and continue the independent checks that remain possible.

Follow the host's browser-control policy. In Codex desktop, use the provided
browser/Playwright surface when required; use the official Playwright CLI only
when permitted and available. Fresh snapshots, semantic controls, screenshots
and traces should support actual outcomes. Keep existing repository tests;
do not create a new test framework just for an audit.

Read Impeccable's resolved `audit` and `critique` references. Load its product
context from this repository using its resolved context-loader path. Respect
its independent assessments when delegation is available and authorized. Treat
simulated personas as hypotheses, not real-user evidence. If its detector or
overlay cannot run within the host's read-only/browser/offline rules, use the
supported source and rendered checks and identify the missing detection layer.
Never bypass browser controls to inject an overlay.

## Verify the user journey

Use docs/LAUNCH.md and existing scripts. Inspect git state first and preserve
unrelated work. Inspect the current service before starting another one. Keep
all edits in a fresh isolated local store and verify its `/api/v1/runtime` data
root before creating records. The user's normal 8777 store is for read-only
inspection. Existing browser tests need both `WOODWORK_TEST_URL` and
`WOODWORK_PRODUCTION_URL` pointed at the isolated origin, not the user store.

Complete the selected journey through its actual result: create/open, edit,
save/generate, reload/reopen and retrieve usable outputs where applicable.
Exercise relevant invalid, empty, loading and failure/recovery states. Inspect
console errors and failed requests, distinguishing intentional fault injection
from unexpected errors. Run appropriate existing tests/typechecks/builds; a
passing build is not functional proof. Distinguish protocol fixtures from real
CAD/export checks. Keep native work serial and retain the configured deadlines.

Check model, cut list, drawings and ZIP/PDF identity against the same project
revision and frozen output set. An older displayed model or guide must remain
clearly labelled. Do not change dimensions, measured stock or method limits to
make a guide apply. Unknown costs stay unknown. Live AI remains excluded unless
the user changes the offline scope. Separate software evidence from physical
fabrication, load, installation or beginner-comprehension approval.

## Review the experience and focus

Capture and inspect representative desktop and phone layouts for the selected
journey. Review hierarchy, spacing, type, consistency, navigation, labels,
feedback, unnecessary steps, keyboard/focus, responsiveness and accessibility.
The chosen product direction takes precedence over generic aesthetic heuristics.
Do not demand unsupported themes or deferred features. Screenshots and automated
checks do not establish accessibility compliance or physical-phone usability.

Compare behavior and recent changes with the agreed milestone. Identify missing
requirements, contradictions and unnecessary complexity; keep optional ideas
separate. If a browser/service fails, diagnose safe local recovery, try permitted
alternatives, continue useful analysis, and state what could not be verified.
If the request permits only supplied artifacts, assess those with their commit
and date provenance instead of attempting live execution.

## Return one report

Lead with a qualitative milestone verdict; a blocked core journey cannot be
hidden by a score. Include the tested commit/configuration, journeys, exact
checks/results, and unverified areas. Separate functionality, visual quality,
usability and product-focus findings, deduplicating issues across reviewers.

Label evidence: **reproduced failure**, **supplied evidence**, **source inference**,
**design judgment**, **scope drift**, or **blocked/untested**. Reserve fresh
reproduction claims for checks actually executed in this audit. For each
significant finding give user impact, reproduction/evidence or source location,
priority, smallest useful fix and verification. Link actual screenshots/traces/logs
where relevant. Do not call prior reports fresh tests, skipped checks passes,
or a focused retest a clean full-suite run. Keep confirmed defects distinct from
preferences and uncertainty.

Finish with the next three justified actions and what already works and should
be preserved; if fewer actions are warranted, say so rather than inventing work.
When fixes are explicitly requested, implement that authorized scope, recheck
affected journeys and update the report. Honor existing authorization instead of
asking again for routine reversible decisions.
