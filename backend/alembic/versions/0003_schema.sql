ALTER TABLE report_evidence ADD CONSTRAINT evidence_report_identity UNIQUE (report_id,id);

CREATE TABLE model_versions (
	id UUID NOT NULL,
	name VARCHAR(100) NOT NULL,
	architecture VARCHAR(80) NOT NULL,
	weights_sha256 VARCHAR(64) NOT NULL,
	dataset_manifest_sha256 VARCHAR(64) NOT NULL,
	manifest_sha256 VARCHAR(64) NOT NULL,
	bundle_key VARCHAR(32) NOT NULL,
	code_revision VARCHAR(200) NOT NULL,
	license_summary TEXT NOT NULL,
	preprocessing_json JSONB NOT NULL,
	evaluation_json JSONB NOT NULL,
	evaluated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	enabled BOOLEAN NOT NULL,
	test_fixture BOOLEAN NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT model_hashes CHECK (weights_sha256 ~ '^[0-9a-f]{64}$' AND dataset_manifest_sha256 ~ '^[0-9a-f]{64}$' AND manifest_sha256 ~ '^[0-9a-f]{64}$'),
	CONSTRAINT model_bundle_key CHECK (bundle_key ~ '^[0-9a-f]{32}$'),
	CONSTRAINT no_fixture_activation CHECK (NOT (enabled AND test_fixture)),
	UNIQUE (manifest_sha256),
	UNIQUE (bundle_key)
);

CREATE TABLE inference_jobs (
	id UUID NOT NULL,
	report_id UUID NOT NULL,
	evidence_id UUID NOT NULL,
	requested_by UUID NOT NULL,
	model_version_id UUID NOT NULL,
	evidence_sha256 VARCHAR(64) NOT NULL,
	status VARCHAR(20) NOT NULL,
	attempts INTEGER NOT NULL,
	lease_token UUID,
	leased_until TIMESTAMP WITH TIME ZONE,
	next_attempt_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	error_code VARCHAR(80),
	latency_ms INTEGER,
	abstained BOOLEAN,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(report_id, evidence_id) REFERENCES report_evidence (report_id, id),
	UNIQUE (evidence_id, model_version_id),
	UNIQUE (id, report_id, evidence_id, model_version_id),
	CONSTRAINT job_status CHECK (status IN ('queued','running','succeeded','failed','unavailable')),
	CONSTRAINT job_attempts CHECK (attempts BETWEEN 0 AND 3),
	CONSTRAINT job_lease CHECK ((status = 'running') = (lease_token IS NOT NULL AND leased_until IS NOT NULL)),
	CONSTRAINT job_hash CHECK (evidence_sha256 ~ '^[0-9a-f]{64}$'),
	CONSTRAINT job_latency CHECK (latency_ms IS NULL OR latency_ms BETWEEN 0 AND 120000),
	FOREIGN KEY(report_id) REFERENCES obstacle_reports (id),
	FOREIGN KEY(requested_by) REFERENCES users (id),
	FOREIGN KEY(model_version_id) REFERENCES model_versions (id)
);

CREATE INDEX ix_inference_jobs_report_id ON inference_jobs (report_id);
CREATE INDEX ix_jobs_claim ON inference_jobs (status, next_attempt_at, leased_until);
CREATE TABLE predictions (
	id UUID NOT NULL,
	job_id UUID NOT NULL,
	report_id UUID NOT NULL,
	evidence_id UUID NOT NULL,
	model_version_id UUID NOT NULL,
	class_name VARCHAR(60) NOT NULL,
	score FLOAT NOT NULL,
	box_xyxy JSONB,
	status VARCHAR(20) NOT NULL,
	reviewer_id UUID,
	reviewed_at TIMESTAMP WITH TIME ZONE,
	review_reason TEXT,
	row_version INTEGER NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(job_id, report_id, evidence_id, model_version_id) REFERENCES inference_jobs (id, report_id, evidence_id, model_version_id),
	UNIQUE (job_id, class_name),
	CONSTRAINT prediction_class CHECK (class_name IN ('stairs','pathway_obstruction','damaged_pavement','ramp_obstruction','no_visible_target')),
	CONSTRAINT prediction_score CHECK (score >= 0 AND score <= 1 AND score < 'Infinity'::float8),
	CONSTRAINT classification_no_boxes CHECK (box_xyxy IS NULL),
	CONSTRAINT prediction_version CHECK (row_version >= 1),
	CONSTRAINT prediction_review CHECK ((status = 'proposed' AND reviewer_id IS NULL AND reviewed_at IS NULL AND review_reason IS NULL) OR (status IN ('accepted','rejected') AND reviewer_id IS NOT NULL AND reviewed_at IS NOT NULL AND length(review_reason) BETWEEN 5 AND 2000)),
	FOREIGN KEY(report_id) REFERENCES obstacle_reports (id),
	FOREIGN KEY(model_version_id) REFERENCES model_versions (id),
	FOREIGN KEY(reviewer_id) REFERENCES users (id)
);

CREATE INDEX ix_predictions_report_id ON predictions (report_id);
