# Repository guidance

Keep the pinned CAD architecture and revision-bound exports intact. User projects
live outside the checkout; verify changes using an isolated local store. Preserve
unrelated working changes and do not push or deploy without explicit authorization.

## Agent skills

### Issue tracker

Work is tracked locally in Markdown. See `docs/agents/issue-tracker.md` when a
skill needs to create or retrieve an issue or feature brief.

### Triage labels

Use the local status vocabulary in `docs/agents/triage-labels.md` for incoming work.

### Domain docs

Read `CONTEXT.md` for domain terms and `docs/agents/domain.md` for the document
layout when implementing or reviewing behavior. Read `PRODUCT.md` and `DESIGN.md`
before changing the interface.

## Product focus and app audits

Ground proposed changes in `PRODUCT.md`, `DESIGN.md`, the current milestone and
evidence in `docs/IMPLEMENTATION-STATUS.md`, the relevant approved `.scratch/`
PRD, and the user's latest decisions. Keep optional future ideas separate from
current requirements. For requested app audits or checkpoint regression/scope
reviews, use `.agents/skills/app-audit/SKILL.md`; default to audit-only unless
fixes are also authorized.
