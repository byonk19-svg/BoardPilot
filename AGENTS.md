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
