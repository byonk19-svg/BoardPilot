# Synthetic coordinator rehearsal

Date: 2026-10-20. A separate read-only review exercised the coordinator against a
supplied scenario. This was not an audit of the running application.

Inputs: the proposed skill, existing repository/product/design guidance and a
synthetic trace showing model revision 8, download label revision 8 and CSV
revision 7. The supplied build was green; the supplied desktop screenshot used
the established warm light palette with an amber pending-state callout. Mobile,
keyboard and screen-reader execution were unavailable. A cloud-AI sidebar was a
deferred brainstorm, not an implemented feature or acceptance requirement.

Observed review behavior:

- Failed the same-revision milestone on the supplied trace without claiming a
  fresh reproduction. Distinguished a green build from successful functionality.
- Preserved the existing visual direction and did not call the intentional
  pending-state color a defect based on a generic aesthetic preference.
- Treated cloud AI as deferred scope rather than inventing a missing requirement.
- Disclosed unverified interaction/accessibility areas and proposed bounded next
  checks. Made no source changes and ran no app, browser, test or provider tools.

The review exposed one wording gap: the evidence vocabulary needed a category
for supplied traces that are neither fresh reproduction nor source inference.
The skill now includes **supplied evidence**, requires its provenance and only
permits fresh-reproduction claims for checks actually executed in that audit.
It also explicitly honors requests limited to supplied artifacts. The official
creator validator passed after this refinement.
