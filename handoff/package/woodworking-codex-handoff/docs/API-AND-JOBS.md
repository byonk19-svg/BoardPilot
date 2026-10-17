# API, Revisions, and Job Execution

This is the application contract to implement. These are proposed application endpoints, not existing text-to-cad APIs. Use the /api/v1 prefix. Preserve the semantics if an existing project requires different route names.

## 1. Authority and validation

The backend is authoritative for normalization, semantic validation, derived parts, revisions, job state, and artifact eligibility. The browser may perform preliminary form validation, but it cannot supply an already-approved part ledger or mark a CAD job successful.

Use the supplied ProjectSpec schema as the starting contract. Implement Pydantic models, generate schema/OpenAPI/TypeScript client definitions, and test the supplied examples for compatibility. A JSON Schema pass does not check positive clear openings, foreign keys, manufacturing equivalence, rigid transformations, or physical construction rules; domain validation must do that.

Return an error object with code, message, field, and details. A field uses the canonical dotted path, such as dimensions.outside_width_mm. Details contain safe numeric context, such as the required minimum relative to panel thickness. No traceback, server path, prompt, or credential appears in an ordinary API error.

| HTTP status | Meaning |
|---|---|
| 200 | Read, normalization result, or successful idempotent operation |
| 201 | New project, revision, or proposal record |
| 202 | Job accepted; use returned job ID |
| 400 | Malformed JSON, invalid archive, or unsupported request shape |
| 404 | Unknown project, revision, job, or artifact ID |
| 409 | Stale base revision, incompatible state transition, or idempotency-key conflict |
| 413 | Input or import exceeds the configured limit |
| 422 | Schema, parameter, template, or recipe validation error |
| 429 | Local queue full or optional AI request limit reached |
| 503 | CAD runtime or optional provider unavailable |

Do not return 200 plus an error string for a failed mutation.

## 2. Project and revision model

Separate the project container from its immutable revisions.

| Record | Required responsibility |
|---|---|
| projects | ID, title, creation/update times, latest accepted revision ID, latest successful revision ID |
| revisions | ID, project ID, monotonic revision number, parent/base revision ID, immutable canonical spec, spec SHA-256, creation time, preferred completed artifact-set ID |
| drafts | Optional saved form draft and its base revision; may contain incomplete raw inputs |
| jobs | ID, revision ID, kind, state, stage, attempt, idempotency key, times, deadline, diagnostic code |
| artifact_sets | ID, revision ID, source artifact-set ID where applicable, build key, resolved hash, verified capabilities, completeness state, immutable manifest location |
| artifacts | ID, artifact-set ID, safe relative path, kind, MIME type, size, SHA-256 |
| proposals | ID, project ID, base revision ID, request correlation, normalized AI proposal, applicability state |
| recipe_reviews | Recipe/version fingerprint, applicability evidence, technical completeness, separately recorded physical review |

Use SQLite foreign keys, a migration mechanism, and short transactions. Avoid a long transaction while CAD, PDF rendering, or a network request runs. The dispatcher is the sole application authority for publishing a job result. Workers never update project current-revision pointers themselves.

The latest accepted revision is the newest valid design the user applied. The latest successful revision identifies a complete usable artifact set. They can differ while a new job runs or fails. The UI labels both situations.

Use immutable application-generated revision IDs and monotonic per-project revision numbers. A restored old design gets a new revision whose parent identifies the current revision; history is not overwritten.

For the fixed shelf-count UI, the template owns persistent logical slots shelf_01 through shelf_04. Increasing the count enables the next highest slot, decreasing it removes the highest enabled slots, and surviving slots retain their IDs. Their positions change with equal spacing. An arbitrary “delete middle shelf” operation is outside this version's count-only contract.

## 3. Canonical hashing and reuse

The spec hash covers the complete normalized ProjectSpec, including material labels and output options. UTF-8 encode recursively key-sorted JSON with compact separators and preserved normalized decimal strings, then SHA-256 it. Arrays retain their canonical order. Never hash a browser's noncanonical raw form.

The geometry hash is a distinct optional cache key over geometry-relevant resolved facts: dimensions, shape/machining definitions, placements, and template/adapter/toolchain versions. A nominal-label-only edit changes the full spec hash and document revision but must not change geometry measurements. Geometry reuse is allowed; coherent revision outputs remain required.

The build key includes spec hash, template version, construction-recipe fingerprint or explicit null, compiler version, adapter version, dependency lock hash, and export/layout versions/options. Exclude execution timestamps and absolute paths from deterministic content hashes.

Artifact byte hashes describe the files actually produced. Geometrically equivalent STEP exports need not have identical bytes on every operating system. Test equivalent saved geometry separately from file integrity.

## 4. Endpoint contract

### Runtime and input

| Method and route | Input | Result |
|---|---|---|
| GET /health | None | API readiness and schema version; avoid expensive repeated kernel imports |
| GET /runtime | None | Last preflight result, selected runtime versions, missing components, safe setup guidance |
| POST /runtime/preflight | Empty object | Queue explicit preflight; return job ID |
| GET /templates | None | Supported IDs/versions, editable fields, modeling bounds, construction choices |
| POST /inputs/normalize | Array of field, text, and default_unit | Canonical decimal-mm values or field-level parse errors |
| POST /specs/validate | Complete ProjectSpec | Validated spec, cheap derived summary, semantic findings; no CAD job |

For input normalization, accept explicit mm, cm, in, and an inch quote suffix. A bare number needs the caller's declared default unit. Mixed fractions use a space, as in “30 1/2 in.” Do not implement arithmetic expression evaluation. Foot/inch compound notation is a future parser extension unless deliberately specified and tested.

Schema normalization strips harmless leading/trailing whitespace and converts accepted values into canonical strings. Reject excess precision after exact conversion rather than silently truncating. Canonical values have no exponent, sign, leading zeros, or unnecessary trailing fractional zeros.

### Projects and revisions

| Method and route | Input | Result |
|---|---|---|
| GET /projects | Pagination | Saved-project summaries and latest revision states |
| POST /projects | title and validated spec | Project plus initial immutable revision; generation is a separate operation |
| GET /projects/{project_id} | None | Project, current pointers, latest saved draft summary |
| PUT /projects/{project_id}/draft | base_revision_id, raw form/spec draft | Save recoverable draft; never replace committed geometry |
| POST /projects/{project_id}/revisions | base_revision_id and full spec | Create next revision after compare-and-swap base check |
| GET /projects/{project_id}/revisions | Pagination | Immutable revision history |
| GET /revisions/{revision_id} | None | Canonical spec, state, provenance, artifact-set IDs |
| POST /revisions/{revision_id}/jobs | kind, idempotency_key, and source_artifact_set_id for downstream jobs | Queue generation or export for exactly that revision and input artifact set |
| GET /revisions/{revision_id}/manifest | Optional artifact_set_id | Requested completed set, otherwise the revision's preferred completed set; return its ID |
| GET /artifacts/{artifact_id}/download | None | Recorded artifact bytes with safe download filename |

The server must verify that a requested revision belongs to the named project wherever both appear. It must also verify proposal and artifact ownership relationships even in a single-user application; this prevents accidental cross-project updates and supports a later hosted boundary.

Revision creation returns a semantic diff computed from old and new resolved facts. Include changed outside dimensions, affected part dimensions/counts, openings, material changes, recipe applicability changes, and stock-layout invalidation. Do not compare only the raw text fields.

### Jobs, proposals, and portability

| Method and route | Input | Result |
|---|---|---|
| GET /jobs/{job_id} | None | State, stage, safe diagnostic, result IDs, actual timestamps |
| POST /jobs/{job_id}/cancel | Empty object | Idempotent cancellation request |
| POST /projects/{project_id}/proposals | base_revision_id, user text, and idempotency_key | A stored validated proposal or clarification result; identical retries do not call the provider again |
| GET /proposals/{proposal_id} | None | Proposed fields, computed diff, questions, applicability |
| POST /proposals/{proposal_id}/apply | expected_base_revision_id | Create a normal revision; reject stale or incomplete proposals |
| POST /revisions/{revision_id}/package | idempotency_key and optional artifact_set_id | Freeze the explicit or preferred completed set at submission; queue its exact ZIP |
| POST /imports/validate | Uploaded project ZIP | Inert validation summary; no code execution |
| POST /imports | Validated upload token and requested title | New project; preserve original provenance, assign new local IDs |

Use one-second polling during an active job, slowing when the browser is hidden or the service is unavailable. Stop polling terminal jobs. WebSockets/SSE are optional; they are not required to make M2 complete.

## 5. Semantic validation rules

Evaluate cheap mathematical rules before CAD. Return all useful field errors from one request.

- Main and back thickness must be positive, with distinct nonempty material IDs.
- Outside width must exceed twice main thickness.
- Outside depth must exceed back thickness.
- Outside height must exceed (fixed_shelf_count + 2) times main thickness.
- Shelf count is an integer from zero through four.
- Kerf, rough allowance, and sheet trim cannot be negative.
- A stock sheet references one of the defined material IDs and inherits that material's actual thickness; it does not supply an independent conflicting thickness.
- Stock IDs are unique. Positive trim-adjusted sheet width and length are required before layout.
- A grain-locked part must be assigned stock with a declared compatible grain direction.
- Unavailable stock makes layout incomplete; it does not make otherwise valid CAD geometry invalid.
- A recipe ID/version must resolve to installed, trusted recipe data. Its fingerprint and applicability are checked during compilation.
- Unknown schema/template versions are rejected with a supported-version response; they are never interpreted as the newest version.

Initial modeling bounds are width 100–2400 mm, height 100–2400 mm, depth 100–1000 mm, main thickness 6–40 mm, and back thickness 1–20 mm. These are product support/computation limits, not structural assurances. Mathematical impossibility findings remain available even if a value is also outside those bounds. A construction recipe can impose a narrower supported range.

Limit canonical input payloads to 256 KiB, normal user AI text to 4,000 characters, stock rows to 12, and fixed shelves to four. The small limits are deliberate for this template. Configure import limits separately and document them.

## 6. Job lifecycle

Use these terminal-aware states:

- queued
- running
- cancelling
- succeeded
- failed
- cancelled
- interrupted

Stages are validating, compiling, generating_geometry, inspecting_geometry, generating_documents, planning_stock, packaging, and publishing. Stage names describe actual work. Do not display a fabricated percentage when only a stage is known.

Claim a queued job with a short SQLite transaction. Save the owning dispatcher session/lease. Start one worker with an immutable input snapshot, fixed driver code, selected recipe data, explicit output root, bounded environment, and deadline. Cadgen daemon reuse is disabled for the first implementation.

The worker can emit bounded structured progress events and a result file, but the dispatcher verifies the result independently before publication. The worker does not accept path overrides or arbitrary imports from HTTP or AI input.

Set one active CAD/export worker for the first local release and a queue length of ten. Return a clear queue-full result. Retrying a failed job creates a new attempt under the same immutable revision; it does not mutate the spec.

The idempotency key is scoped to project/revision/job kind and request content. Reusing it with identical input returns the existing job/result. Reusing it with different input returns 409. Two browser clicks must not launch two identical CAD processes or two paid AI requests.

Apply the same reservation-before-call rule to proposal creation, scoped to project, base revision, normalized request text, and configured provider/model. Identical retries return the existing pending or completed request. If a provider call has an uncertain outcome, retain that state and require an explicit retry with a new key; do not automatically repeat a potentially billed request.

Proposal application is a one-time transactional operation. Store the resulting revision ID on the consumed proposal. Repeating the same apply returns that revision without another write or provider call; a conflicting apply/base returns 409.

## 7. Artifact publication protocol

### Cumulative artifact sets and deterministic selection

The initial geometry set contains the canonical project, resolved ledger, assembly and per-definition STEP files, per-definition GLBs, CSV, step-instance-map.json, and required metadata. Document and stock jobs name a source_artifact_set_id from the same revision. They produce a new immutable cumulative set that retains the base geometry assets and adds/replaces only the requested derived outputs. Copy verified base assets into the new set; never mutate the source set or publish a PDF-only manifest as the viewer's current set.

The revision's preferred artifact-set pointer advances only to a verified cumulative result that contains the core geometry capability and preserves the capabilities of the currently preferred set. A valid stale/sibling subset remains available by explicit ID; it does not downgrade the default set. Start sequential downstream jobs from the preferred set. No automatic sibling merging is required in V1.

Manifest reads default to the stored preferred artifact-set ID. Package submission resolves that same default once, records the chosen ID on the job, and packages exactly that set even if a newer one appears before completion. Explicit artifact-set IDs must belong to the requested revision.

An artifact's revision/spec identity must match its set. If geometry caching reuses underlying geometry across revisions, regenerate all revision-bearing metadata and wrappers; do not copy an old revision label into a new packet. Geometry reuse is optional in V1.

### Required identity and cardinality checks

The published manifest must have exactly one assembly STEP with definition_id null and exactly one maintained STEP plus one GLB for every part definition. Each definition's quantity and member-instance list must agree with the instance ledger. Artifact IDs and relative paths are unique within the set; required files must exist and match their recorded byte hashes.

Persist step-instance-map.json as a required JSON artifact. It contains its schema version, revision/spec identity, assembly artifact ID and SHA-256, and one record per physical instance: instance_id, verified occurrence label, and the current public cadgen occurrence selector in the serialized representation established by the M0 adapter. Treat the selector as opaque data; it is valid only for that assembly hash and is never executable code. During M0, document/test the concrete selector serialization against the pinned public reader rather than guessing a private cache reference.

The mapping must cover every instance exactly once and select the matching saved occurrence. When copying core geometry into a cumulative set with new artifact IDs, rebind the map's assembly artifact ID and recompute the sidecar hash while retaining the verified assembly byte hash. Include the sidecar in every project package.

### Publication steps

1. Create an app-owned staging directory for the job. Save the exact normalized spec and resolved ledger there.
2. Build artifacts against that snapshot. Never read a live editable project file during generation.
3. Verify every required artifact, geometry result, revision/spec binding, file size, and checksum.
4. Write a manifest covering the artifact inventory. The manifest does not include its own checksum or the enclosing ZIP's checksum; store those outer hashes in the database/export response to avoid a circular definition.
5. Atomically rename the staging artifact set into a unique final directory on the same filesystem. Final directories are immutable.
6. In a short transaction, insert artifact records, mark the job succeeded, and advance the latest-successful pointer only if its revision is the appropriate current accepted revision.
7. If database publication fails after the rename, preserve the immutable set for reconciliation. On restart, import the verified orphan record or remove a confirmed unreferenced temporary result under a documented policy.

An older revision can finish and become a valid historical artifact set. It must not overwrite a newer preview or current download selection. With a single worker, simulate reversed completion callbacks or build results in the race test; a future parallel dispatcher must pass the same contract.

For the first generation request, required outputs are canonical project JSON, resolved JSON, whole-assembly STEP, per-definition STEP and preview GLB files, CSV, step-instance-map.json, and manifest. PDF and recipe outputs become required for the document job introduced in M3, while the cumulative set retains those geometry files. Optional formats have their own status; a skipped DXF does not fail a job that did not request DXF.

## 8. Cancellation and recovery

Cancellation first marks the job cancelling. The supervisor stops the entire owned process tree, closes pipes, waits for confirmed exit, and marks cancelled. Killing only the immediate Python PID is insufficient when native, Node, or browser descendants exist.

For native Windows use a tested process launcher with Job Object containment established before children can spawn. For WSL/Linux use a controlled process group and equivalent termination behavior. Test the implementation on the selected runtime. The initial cancellation budget is five seconds; record the achieved result.

A wall-clock deadline is independent of worker heartbeat. A busy CAD operation that keeps reporting progress must still obey the configured limit. Timeout produces failed with a specific timeout code and preserves the last successful revision.

At API startup, reconcile jobs whose owning process/session is gone. Mark them interrupted, retain safe diagnostics, and make retry available. Do not mark them succeeded because some output files exist. Verify the committed artifact set before trusting it.

## 9. AI proposal boundary

The supplied AI proposal schema allows only outside width, outside height, outside depth, and fixed-shelf count as changes. It permits questions about measured material thickness, but it does not permit a provider to overwrite that measurement.

The live provider adapter maps the application contract into the provider's supported structured-output format. The application still runs its own complete JSON Schema and semantic validation after the response. A provider's claim of structured output is not a substitute for that check.

Reject duplicate changes to the same field, unknown fields, empty invalid intents, unsupported templates, invalid numbers, and stale base revisions. Clarify/unsupported responses contain no changes. An update has a real base revision. A create proposal still needs measured materials through the ordinary form before it becomes a complete spec.

Do not permit recipe IDs, hardware dimensions, arbitrary code, file paths, URLs to fetch, or shell instructions in the executable portion of a proposal. Explanations are rendered as inert text. They have no authority to trigger actions.

The fake provider should cover a successful width change, missing dimension, unsupported drawer request, malformed response, provider timeout, and stale-base response. Applying a valid fake proposal must produce the same revision and dimensions as the equivalent form edit, apart from provenance.

Credentials and provider/model settings belong to the API process, never the CAD worker or frontend bundle. Log token usage only when returned by the provider; show cost only when the applicable price data is supplied and current. Leave unknown usage/cost unknown.

## 10. Local request and import controls

Serve the ordinary production UI and API from the same loopback origin. Validate trusted Host names and request Origin, and use a local-session CSRF mechanism for state-changing operations. CORS is not an authentication or filesystem protection mechanism.

Use server-generated IDs for artifacts. Resolve paths under the data root and verify containment against traversal and symlink escapes. User titles affect display/download labels only; they never determine executable paths.

A project import accepts only expected inert files. Reject absolute paths, drive-letter paths, traversal entries, symlinks, excessive expanded size, unexpected executable files, and unsupported versions. A completed import creates a new local project and reports whether installed templates can rebuild it. Never execute imported Python from another person's project ZIP.

Back up or migrate SQLite transactionally using supported database behavior. A migration failure should preserve a recoverable prior database. Do not destructively reset the user's project store as routine setup or testing.

## 11. Required evidence

M2 must prove successful create/edit/reopen, two individually selectable identical boards, a stale revision conflict, idempotent generation, cancellation, crash recovery, and an invalid input rejected before worker launch.

M5 must prove schema-limited proposals, identical form/AI outcomes, no credential leakage to worker environment, provider failure recovery, and no automatic application of stale changes.

M6 must prove export/import integrity, dependency/version reporting, immutable artifact publication, a clean restart after an interrupted job, and accurate launch instructions for the chosen Windows or WSL environment.
