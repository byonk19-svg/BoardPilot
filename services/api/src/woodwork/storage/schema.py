SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
 id TEXT PRIMARY KEY, title TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 latest_accepted_revision_id TEXT, latest_successful_revision_id TEXT, provenance_json TEXT
);
CREATE TABLE IF NOT EXISTS revisions (
 id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id), number INTEGER NOT NULL,
 parent_id TEXT REFERENCES revisions(id), spec_json TEXT NOT NULL, resolved_json TEXT NOT NULL,
 spec_sha256 TEXT NOT NULL, resolved_sha256 TEXT NOT NULL, created_at TEXT NOT NULL,
 preferred_artifact_set_id TEXT, UNIQUE(project_id,number)
);
CREATE TABLE IF NOT EXISTS drafts (
 project_id TEXT PRIMARY KEY REFERENCES projects(id), base_revision_id TEXT NOT NULL REFERENCES revisions(id),
 raw_json TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS jobs (
 id TEXT PRIMARY KEY, revision_id TEXT REFERENCES revisions(id), kind TEXT NOT NULL, state TEXT NOT NULL,
 stage TEXT NOT NULL, attempt INTEGER NOT NULL, idempotency_key TEXT NOT NULL, request_sha256 TEXT NOT NULL,
 source_artifact_set_id TEXT, owner_session TEXT, created_at TEXT NOT NULL, started_at TEXT, finished_at TEXT,
 diagnostic_code TEXT, result_artifact_set_id TEXT, result_artifact_id TEXT, metrics_json TEXT,
 UNIQUE(revision_id,kind,idempotency_key)
);
CREATE TABLE IF NOT EXISTS artifact_sets (
 id TEXT PRIMARY KEY, revision_id TEXT NOT NULL REFERENCES revisions(id), source_artifact_set_id TEXT,
 relative_dir TEXT NOT NULL UNIQUE, manifest_sha256 TEXT NOT NULL, capabilities_json TEXT NOT NULL,
 manifest_json TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS artifacts (
 id TEXT PRIMARY KEY, artifact_set_id TEXT NOT NULL REFERENCES artifact_sets(id), record_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS proposals (
 id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id), base_revision_id TEXT NOT NULL REFERENCES revisions(id),
 idempotency_key TEXT NOT NULL, request_sha256 TEXT NOT NULL, state TEXT NOT NULL, proposal_json TEXT,
 applied_revision_id TEXT REFERENCES revisions(id), diagnostic_code TEXT, created_at TEXT NOT NULL,
 UNIQUE(project_id,idempotency_key)
);
CREATE TABLE IF NOT EXISTS recipe_reviews (
 fingerprint TEXT PRIMARY KEY, technical_json TEXT NOT NULL, physical_json TEXT
);
CREATE TABLE IF NOT EXISTS exports (
 id TEXT PRIMARY KEY, artifact_set_id TEXT NOT NULL REFERENCES artifact_sets(id),
 relative_dir TEXT NOT NULL UNIQUE, record_json TEXT NOT NULL, created_at TEXT NOT NULL
);
PRAGMA user_version=2;
"""
