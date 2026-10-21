# On-demand app audits

The project skill `.agents/skills/app-audit/SKILL.md` coordinates real browser
checks, Impeccable's audit and critique workflows, and a review of product scope.
It defaults to audit-only. It uses `PRODUCT.md`, `DESIGN.md`, the current milestone
in `docs/IMPLEMENTATION-STATUS.md`, the relevant approved `.scratch/` PRD and the
user's latest decisions; it does not create another product plan.

## Use it

In a new message, ask:

```text
$app-audit Review the current app for functionality, visual quality,
usability, and alignment with our current milestone. Test the main
user journeys and give me the three most important next actions.
Audit only.
```

For a smaller checkpoint review:

```text
$app-audit Review the changes since our last checkpoint and test the
affected user journeys. Check for regressions and scope drift. Audit only.
```

After reviewing the findings, authorize a bounded fix separately, for example:

```text
Fix the three highest-priority confirmed issues that support our
current milestone, then verify the affected flows.
```

An audit reports what was actually verified, evidence and uncertainty, four
assessment axes, prioritized findings with their smallest useful fix and retest,
justified next actions, and behavior/design to preserve. It keeps design
preferences distinct from defects and supplied evidence distinct from fresh
reproduction. Screen captures and automated checks alone cannot establish
accessibility compliance, beginner comprehension or physical build approval.

## Installed capabilities

The existing enabled user skills were reused without overwriting them:

| Capability | Resolved skill source on this machine |
|---|---|
| Official OpenAI Playwright | `C:/Users/byonk/.codex/skills/playwright/SKILL.md` |
| Impeccable | `C:/Users/byonk/.agents/skills/impeccable/SKILL.md` |
| Project coordinator | `.agents/skills/app-audit/SKILL.md` |

`agents/openai.yaml` supplies the App Audit picker name and default prompt.
The parent chat workspace is `BoardPilot`, one folder above the Git repository.
A local junction at `BoardPilot/.agents/skills/app-audit` points to the canonical
skill in `BoardPilot/woodworking-platform/.agents/skills/app-audit`. There is one
definition. Codex discovery returned it once, enabled, from both working
directories. The junction is local setup outside this repository; when moving
the repository elsewhere, opening the actual repository root needs no junction.

The setup verified Node/npx, cached Playwright CLI 0.1.22, project
`@playwright/test` 1.63.0 and the installed Chromium executable. It prepared and
verified Impeccable CLI 3.0.3 in the npm cache, without changing app dependencies.
The current detector syntax differs from older skill examples:

```powershell
npx.cmd --offline --no-install --package=@playwright/cli playwright-cli --version
npx.cmd --offline --no-install --package=impeccable@3.0.3 impeccable --help
npx.cmd --offline --no-install --package=impeccable@3.0.3 impeccable detect --help
npx.cmd --offline --no-install --package=impeccable@3.0.3 impeccable detect --json apps/web/src/AssemblyReadiness.tsx
```

These commands were run from the application repository. The one-file detector
smoke returned valid JSON `[]`; it was a tool preflight, not an app-quality
verdict. There are no missing core setup prerequisites. The current CLI help has
no `live` command; no overlay was injected or verified. Future audits must report
unavailable detection layers and honor the host's browser-control rules, using
the permitted Playwright/browser surface. Do not bypass controls to inject an
overlay. Use the existing installed tools/cache; this skill does not silently
install or update tools during future audits.

Public tool preparation downloaded Impeccable CLI 3.0.3 and isolated validator
dependency PyYAML 6.0.3. The prepared CLI commands above work offline. Application
operation and future audits remain local/offline unless the user changes that
scope; audits must preserve real projects and verify an isolated test data root
before writing. No Vercel skill, live AI integration or app dependency was added.

The one-time preparation commands used network access for the requested tool
setup. They are not instructions to download anything during an audit:

```powershell
npx.cmd --yes --package=impeccable@3.0.3 impeccable --version
py -m uv pip install --python .venv/Scripts/python.exe --target .verification/app-audit-setup-20261020/validator-deps PyYAML==6.0.3
```

## Setup verification, 2026-10-20

Evidence is in `evidence/app-audit-setup-20261020/`:

- `verification.json`: tool versions, reused skill hashes, validation and limits.
- `discovery.json`: actual Codex `skills/list` output filtered to the three skills,
  for the repository and parent workspace; all enabled, zero skill errors.
- `check-discovery.py`: repeatable local metadata check; it starts no model turn.
- `detector-smoke.json`: exact one-file detector result.
- `rehearsal.md`: synthetic coordinator review and resulting evidence-label fix.

The official skill-creator validator passed, and the picker YAML parsed with a
valid description length and `$app-audit` default prompt. Impeccable's existing
context loader found both existing product and design documents without
migration. A read-only synthetic rehearsal correctly treated a supplied
revision mismatch as a milestone failure, preserved the established visual
direction and separated deferred cloud ideas from current requirements. The
rehearsal performed no app, browser or test execution.

The installed Codex CLI 0.128.0 metadata checker needed a process-local
`service_tier=flex` override because that CLI cannot parse the desktop config's
`default` value. The check invoked only `initialize` and `skills/list`; it did
not change account/configuration settings, start a model turn or call a provider.

Recheck discovery from the repository root:

```powershell
.venv/Scripts/python.exe evidence/app-audit-setup-20261020/check-discovery.py
```

The creator validator used an isolated helper dependency, not the app's venv
packages. Exact local validation commands, with that prepared directory intact:

```powershell
$env:PYTHONPATH=(Resolve-Path .verification/app-audit-setup-20261020/validator-deps).Path
$env:PYTHONUTF8='1'
.venv/Scripts/python.exe C:/Users/byonk/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/app-audit
```

This setup did not change app behavior or project data. No full application
audit, browser journey or native CAD suite was run for this skill-only change.
The discovery and preflight results establish tool availability, not that the
application passes its product acceptance gates today.

## Sources

The setup follows the existing installed skills and the official
[OpenAI skill documentation](https://developers.openai.com/codex/skills/),
[OpenAI Playwright skill](https://github.com/openai/skills/tree/main/skills/.curated/playwright),
and [Impeccable project](https://github.com/pbakaus/impeccable). Installed CLI help
is authoritative for commands available in the prepared version.
