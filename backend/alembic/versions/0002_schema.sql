-- Immutable Phase 4 reporting schema; generated from reviewed models.


CREATE TABLE sse_leases (
	id UUID NOT NULL,
	identifier_hash VARCHAR(64) NOT NULL,
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id)
)

;

CREATE INDEX ix_sse_leases_expires_at ON sse_leases (expires_at);

CREATE INDEX ix_sse_leases_identifier_hash ON sse_leases (identifier_hash);


CREATE TABLE idempotency_records (
	id UUID NOT NULL,
	actor_id UUID NOT NULL,
	operation VARCHAR(100) NOT NULL,
	key UUID NOT NULL,
	request_hash VARCHAR(64) NOT NULL,
	result_status INTEGER,
	result_json JSONB,
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (actor_id, operation, key),
	FOREIGN KEY(actor_id) REFERENCES users (id)
)

;

CREATE INDEX ix_idempotency_records_expires_at ON idempotency_records (expires_at);


CREATE TABLE obstacle_reports (
	reporter_id UUID NOT NULL,
	category VARCHAR(40) NOT NULL,
	description TEXT NOT NULL,
	point geometry(POINT,4326) NOT NULL,
	location_id UUID,
	infrastructure_id UUID,
	status VARCHAR(20) NOT NULL,
	reviewer_id UUID,
	reviewed_at TIMESTAMP WITH TIME ZONE,
	resolution_note TEXT,
	resolved_at TIMESTAMP WITH TIME ZONE,
	campus_id UUID NOT NULL,
	id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	row_version INTEGER DEFAULT '1' NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (campus_id, id),
	FOREIGN KEY(campus_id, location_id) REFERENCES locations (campus_id, id),
	FOREIGN KEY(campus_id, infrastructure_id) REFERENCES infrastructure (campus_id, id),
	CONSTRAINT report_category CHECK (category IN ('blocked_ramp','inaccessible_entrance','damaged_pathway','elevator_unavailable','temporary_obstacle','other_accessibility_concern')),
	CONSTRAINT report_description CHECK (length(description) BETWEEN 10 AND 2000),
	CONSTRAINT report_status CHECK (status IN ('pending_review','verified','rejected','resolved')),
	CONSTRAINT report_version CHECK (row_version >= 1),
	CONSTRAINT report_review_metadata CHECK ((status = 'pending_review' AND reviewer_id IS NULL AND reviewed_at IS NULL AND resolved_at IS NULL) OR (status IN ('verified','rejected') AND reviewer_id IS NOT NULL AND reviewed_at IS NOT NULL AND resolved_at IS NULL) OR (status = 'resolved' AND reviewer_id IS NOT NULL AND reviewed_at IS NOT NULL AND resolved_at IS NOT NULL AND resolution_note IS NOT NULL)),
	FOREIGN KEY(reporter_id) REFERENCES users (id),
	FOREIGN KEY(reviewer_id) REFERENCES users (id),
	FOREIGN KEY(campus_id) REFERENCES campuses (id)
)

;

CREATE INDEX idx_obstacle_reports_point ON obstacle_reports USING gist (point);

CREATE INDEX ix_obstacle_reports_campus_id ON obstacle_reports (campus_id);

CREATE INDEX ix_obstacle_reports_reporter_id ON obstacle_reports (reporter_id);

CREATE INDEX ix_reports_campus_status_created ON obstacle_reports (campus_id, status, created_at);


CREATE TABLE edge_restrictions (
	id UUID NOT NULL,
	campus_id UUID NOT NULL,
	report_id UUID,
	edge_id UUID NOT NULL,
	kind VARCHAR(30) NOT NULL,
	reason TEXT NOT NULL,
	created_by UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	released_by UUID,
	released_at TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (id),
	FOREIGN KEY(campus_id, report_id) REFERENCES obstacle_reports (campus_id, id),
	FOREIGN KEY(campus_id, edge_id) REFERENCES path_edges (campus_id, id),
	CONSTRAINT restriction_kind CHECK (kind IN ('closed','temporarily_blocked')),
	CONSTRAINT restriction_release CHECK ((released_at IS NULL) = (released_by IS NULL)),
	FOREIGN KEY(campus_id) REFERENCES campuses (id),
	FOREIGN KEY(created_by) REFERENCES users (id),
	FOREIGN KEY(released_by) REFERENCES users (id)
)

;

CREATE INDEX ix_active_edge_restrictions ON edge_restrictions (edge_id) WHERE released_at IS NULL;

CREATE UNIQUE INDEX one_active_report_restriction ON edge_restrictions (report_id, edge_id) WHERE released_at IS NULL AND report_id IS NOT NULL;


CREATE TABLE report_edges (
	campus_id UUID NOT NULL,
	report_id UUID NOT NULL,
	edge_id UUID NOT NULL,
	PRIMARY KEY (report_id, edge_id),
	FOREIGN KEY(campus_id, report_id) REFERENCES obstacle_reports (campus_id, id),
	FOREIGN KEY(campus_id, edge_id) REFERENCES path_edges (campus_id, id)
)

;


CREATE TABLE report_evidence (
	id UUID NOT NULL,
	report_id UUID NOT NULL,
	uploader_id UUID NOT NULL,
	storage_key VARCHAR(80) NOT NULL,
	media_type VARCHAR(20) NOT NULL,
	byte_size BIGINT NOT NULL,
	width_px INTEGER,
	height_px INTEGER,
	sha256 VARCHAR(64),
	status VARCHAR(20) NOT NULL,
	failure_code VARCHAR(50),
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT evidence_status CHECK (status IN ('processing','ready','rejected','deleted')),
	CONSTRAINT evidence_type CHECK (media_type IN ('image/jpeg','image/png')),
	CONSTRAINT evidence_bytes CHECK (byte_size BETWEEN 1 AND 10485760),
	CONSTRAINT evidence_dimensions CHECK (status <> 'ready' OR (width_px IS NOT NULL AND height_px IS NOT NULL AND width_px > 0 AND height_px > 0 AND width_px::bigint * height_px <= 20000000 AND sha256 IS NOT NULL)),
	CONSTRAINT evidence_key CHECK (storage_key ~ '^[0-9a-f]{32}\.(png|jpg)$'),
	FOREIGN KEY(report_id) REFERENCES obstacle_reports (id),
	FOREIGN KEY(uploader_id) REFERENCES users (id),
	UNIQUE (storage_key)
)

;

CREATE INDEX ix_report_evidence_report_id ON report_evidence (report_id);

CREATE INDEX ix_report_evidence_uploader_id ON report_evidence (uploader_id);


CREATE TABLE report_status_events (
	id UUID NOT NULL,
	report_id UUID NOT NULL,
	from_status VARCHAR(20),
	to_status VARCHAR(20) NOT NULL,
	actor_id UUID NOT NULL,
	note TEXT NOT NULL,
	occurred_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	resulting_row_version INTEGER NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT history_status CHECK (to_status IN ('submitted','pending_review','verified','rejected','resolved')),
	CONSTRAINT history_from CHECK (from_status IS NULL OR from_status IN ('submitted','pending_review','verified')),
	CONSTRAINT history_version CHECK (resulting_row_version >= 1),
	FOREIGN KEY(report_id) REFERENCES obstacle_reports (id),
	FOREIGN KEY(actor_id) REFERENCES users (id)
)

;

CREATE INDEX ix_report_status_events_report_id ON report_status_events (report_id);
