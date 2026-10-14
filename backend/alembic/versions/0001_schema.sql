-- Immutable initial schema, generated from reviewed Phase 1 models.

CREATE TABLE campuses (
	name VARCHAR(120) NOT NULL,
	data_origin VARCHAR(20) NOT NULL,
	attribution TEXT NOT NULL,
	default_timezone VARCHAR NOT NULL,
	boundary geometry(POLYGON,4326),
	id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	row_version INTEGER DEFAULT '1' NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT campus_origin CHECK (data_origin IN ('synthetic_demo','surveyed'))
);

CREATE INDEX idx_campuses_boundary ON campuses USING gist (boundary);

ALTER TABLE campuses ADD CONSTRAINT campuses_positive_version CHECK (row_version >= 1);

CREATE TABLE rate_limit_buckets (
	scope VARCHAR(40) NOT NULL,
	identifier_hash VARCHAR(64) NOT NULL,
	bucket_start BIGINT NOT NULL,
	count INTEGER NOT NULL,
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (scope, identifier_hash, bucket_start)
);

CREATE INDEX ix_rate_limit_buckets_expires_at ON rate_limit_buckets (expires_at);

CREATE TABLE users (
	normalized_email VARCHAR(254) NOT NULL,
	display_name VARCHAR(80) NOT NULL,
	password_hash TEXT NOT NULL,
	role VARCHAR(10) DEFAULT 'user' NOT NULL,
	active BOOLEAN DEFAULT 'true' NOT NULL,
	auth_version INTEGER DEFAULT '1' NOT NULL,
	id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	row_version INTEGER DEFAULT '1' NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT user_role CHECK (role IN ('user','admin')),
	UNIQUE (normalized_email)
);

ALTER TABLE users ADD CONSTRAINT users_positive_version CHECK (row_version >= 1);

CREATE TABLE accessibility_profiles (
	user_id UUID NOT NULL,
	avoid_stairs BOOLEAN NOT NULL,
	max_slope_pct FLOAT,
	min_width_m FLOAT,
	excluded_surfaces TEXT[] NOT NULL,
	unknown_policy VARCHAR NOT NULL,
	travel_speed_mps FLOAT NOT NULL,
	id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	row_version INTEGER DEFAULT '1' NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT profile_slope CHECK (max_slope_pct BETWEEN 0 AND 100),
	CONSTRAINT profile_width CHECK (min_width_m > 0 AND min_width_m <= 10),
	CONSTRAINT profile_speed CHECK (travel_speed_mps BETWEEN 0.1 AND 3),
	CONSTRAINT profile_unknown CHECK (unknown_policy IN ('exclude','allow_with_warning')),
	CONSTRAINT profile_surfaces CHECK (excluded_surfaces <@ ARRAY['smooth','uneven','gravel']::text[]),
	UNIQUE (user_id),
	FOREIGN KEY(user_id) REFERENCES users (id)
);

ALTER TABLE accessibility_profiles ADD CONSTRAINT accessibility_profiles_positive_version CHECK (row_version >= 1);

CREATE TABLE admin_actions (
	id UUID NOT NULL,
	actor_id UUID,
	campus_id UUID,
	action_type VARCHAR NOT NULL,
	resource_type VARCHAR NOT NULL,
	resource_id UUID NOT NULL,
	before_json JSONB NOT NULL,
	after_json JSONB NOT NULL,
	reason VARCHAR NOT NULL,
	request_id VARCHAR NOT NULL,
	graph_version BIGINT,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(actor_id) REFERENCES users (id),
	FOREIGN KEY(campus_id) REFERENCES campuses (id)
);

CREATE INDEX ix_admin_actions_created_at ON admin_actions (created_at);

CREATE TABLE auth_sessions (
	id UUID NOT NULL,
	token_hash VARCHAR(64) NOT NULL,
	user_id UUID,
	issued_auth_version INTEGER,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
	last_seen_at TIMESTAMP WITH TIME ZONE NOT NULL,
	revoked_at TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (id),
	UNIQUE (token_hash),
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE INDEX ix_auth_sessions_expires_at ON auth_sessions (expires_at);

CREATE INDEX ix_auth_sessions_user_id ON auth_sessions (user_id);

CREATE TABLE graph_events (
	campus_id UUID NOT NULL,
	graph_version BIGINT NOT NULL,
	event_type VARCHAR NOT NULL,
	changed_edge_ids UUID[] NOT NULL,
	reason VARCHAR NOT NULL,
	occurred_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (campus_id, graph_version),
	FOREIGN KEY(campus_id) REFERENCES campuses (id)
);

CREATE TABLE graph_state (
	campus_id UUID NOT NULL,
	version BIGINT NOT NULL,
	cost_model_version VARCHAR NOT NULL,
	policy_version VARCHAR NOT NULL,
	next_expiry_at TIMESTAMP WITH TIME ZONE,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (campus_id),
	CONSTRAINT graph_version_positive CHECK (version >= 1),
	FOREIGN KEY(campus_id) REFERENCES campuses (id)
);

CREATE TABLE locations (
	name VARCHAR(120) NOT NULL,
	kind VARCHAR(30) NOT NULL,
	description TEXT NOT NULL,
	active BOOLEAN NOT NULL,
	point geometry(POINT,4326) NOT NULL,
	campus_id UUID NOT NULL,
	id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	row_version INTEGER DEFAULT '1' NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (campus_id, id),
	FOREIGN KEY(campus_id) REFERENCES campuses (id)
);

CREATE INDEX idx_locations_point ON locations USING gist (point);

CREATE INDEX ix_locations_campus_id ON locations (campus_id);

CREATE INDEX ix_locations_name ON locations (name);

ALTER TABLE locations ADD CONSTRAINT locations_positive_version CHECK (row_version >= 1);

CREATE TABLE path_nodes (
	name VARCHAR(120),
	level INTEGER NOT NULL,
	active BOOLEAN NOT NULL,
	point geometry(POINT,4326) NOT NULL,
	campus_id UUID NOT NULL,
	id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	row_version INTEGER DEFAULT '1' NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (campus_id, id),
	CONSTRAINT node_level CHECK (level BETWEEN -20 AND 200),
	FOREIGN KEY(campus_id) REFERENCES campuses (id)
);

CREATE INDEX idx_path_nodes_point ON path_nodes USING gist (point);

CREATE INDEX ix_path_nodes_campus_id ON path_nodes (campus_id);

ALTER TABLE path_nodes ADD CONSTRAINT path_nodes_positive_version CHECK (row_version >= 1);

CREATE TABLE infrastructure (
	location_id UUID,
	name VARCHAR(120) NOT NULL,
	point geometry(POINT,4326) NOT NULL,
	kind VARCHAR NOT NULL,
	campus_id UUID NOT NULL,
	id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	row_version INTEGER DEFAULT '1' NOT NULL,
	accessibility VARCHAR NOT NULL,
	availability VARCHAR NOT NULL,
	verification VARCHAR NOT NULL,
	verified_at TIMESTAMP WITH TIME ZONE,
	verified_until TIMESTAMP WITH TIME ZONE,
	verified_by UUID,
	provenance TEXT NOT NULL,
	active BOOLEAN NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (campus_id, id),
	FOREIGN KEY(campus_id, location_id) REFERENCES locations (campus_id, id),
	CONSTRAINT infrastructure_kind CHECK (kind IN ('ramp','stairs','entrance','elevator','pathway')),
	CONSTRAINT infrastructure_accessibility CHECK (accessibility IN ('accessible','inaccessible','unknown')),
	CONSTRAINT infrastructure_availability CHECK (availability IN ('open','closed','temporarily_blocked')),
	CONSTRAINT infrastructure_verification CHECK (verification IN ('verified','unverified','needs_review')),
	CONSTRAINT infrastructure_verified_evidence CHECK (verification <> 'verified' OR (verified_at IS NOT NULL AND verified_until IS NOT NULL AND verified_by IS NOT NULL AND verified_until > verified_at AND length(provenance) > 0)),
	FOREIGN KEY(campus_id) REFERENCES campuses (id),
	FOREIGN KEY(verified_by) REFERENCES users (id)
);

CREATE INDEX idx_infrastructure_point ON infrastructure USING gist (point);

CREATE INDEX ix_infrastructure_campus_id ON infrastructure (campus_id);

ALTER TABLE infrastructure ADD CONSTRAINT infrastructure_positive_version CHECK (row_version >= 1);

CREATE TABLE location_access_points (
	campus_id UUID NOT NULL,
	location_id UUID NOT NULL,
	node_id UUID NOT NULL,
	label VARCHAR(120) NOT NULL,
	kind VARCHAR NOT NULL,
	is_primary BOOLEAN NOT NULL,
	PRIMARY KEY (location_id, node_id),
	FOREIGN KEY(campus_id, location_id) REFERENCES locations (campus_id, id),
	FOREIGN KEY(campus_id, node_id) REFERENCES path_nodes (campus_id, id),
	CONSTRAINT access_kind CHECK (kind IN ('entrance','junction'))
);

CREATE UNIQUE INDEX one_primary_access_point ON location_access_points (location_id) WHERE is_primary = true;

CREATE TABLE path_edges (
	source_node_id UUID NOT NULL,
	target_node_id UUID NOT NULL,
	geometry geometry(LINESTRING,4326) NOT NULL,
	distance_m FLOAT DEFAULT '0' NOT NULL,
	direction VARCHAR NOT NULL,
	width_m FLOAT,
	slope_pct FLOAT,
	surface VARCHAR NOT NULL,
	has_stairs BOOLEAN,
	has_ramp BOOLEAN,
	campus_id UUID NOT NULL,
	id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	row_version INTEGER DEFAULT '1' NOT NULL,
	accessibility VARCHAR NOT NULL,
	availability VARCHAR NOT NULL,
	verification VARCHAR NOT NULL,
	verified_at TIMESTAMP WITH TIME ZONE,
	verified_until TIMESTAMP WITH TIME ZONE,
	verified_by UUID,
	provenance TEXT NOT NULL,
	active BOOLEAN NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (campus_id, id),
	FOREIGN KEY(campus_id, source_node_id) REFERENCES path_nodes (campus_id, id),
	FOREIGN KEY(campus_id, target_node_id) REFERENCES path_nodes (campus_id, id),
	CONSTRAINT edge_distinct_nodes CHECK (source_node_id <> target_node_id),
	CONSTRAINT edge_distance CHECK (distance_m > 0 AND distance_m < 'Infinity'::float8),
	CONSTRAINT edge_width CHECK (width_m > 0 AND width_m <= 10),
	CONSTRAINT edge_slope CHECK (slope_pct BETWEEN -100 AND 100),
	CONSTRAINT edge_direction CHECK (direction IN ('both','forward','reverse')),
	CONSTRAINT edge_surface CHECK (surface IN ('smooth','uneven','gravel','unknown')),
	CONSTRAINT edge_accessibility CHECK (accessibility IN ('accessible','inaccessible','unknown')),
	CONSTRAINT edge_availability CHECK (availability IN ('open','closed','temporarily_blocked')),
	CONSTRAINT edge_verification CHECK (verification IN ('verified','unverified','needs_review')),
	CONSTRAINT edge_verified_evidence CHECK (verification <> 'verified' OR (verified_at IS NOT NULL AND verified_until IS NOT NULL AND verified_by IS NOT NULL AND verified_until > verified_at AND length(provenance) > 0)),
	FOREIGN KEY(campus_id) REFERENCES campuses (id),
	FOREIGN KEY(verified_by) REFERENCES users (id)
);

CREATE INDEX idx_path_edges_geometry ON path_edges USING gist (geometry);

CREATE INDEX ix_path_edges_campus_id ON path_edges (campus_id);

CREATE INDEX ix_path_edges_source_node_id ON path_edges (source_node_id);

CREATE INDEX ix_path_edges_target_node_id ON path_edges (target_node_id);

ALTER TABLE path_edges ADD CONSTRAINT path_edges_positive_version CHECK (row_version >= 1);

CREATE TABLE saved_destinations (
	user_id UUID NOT NULL,
	campus_id UUID NOT NULL,
	location_id UUID NOT NULL,
	label VARCHAR(120) NOT NULL,
	id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	row_version INTEGER DEFAULT '1' NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(campus_id, location_id) REFERENCES locations (campus_id, id),
	UNIQUE (user_id, location_id),
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE INDEX ix_saved_destinations_user_id ON saved_destinations (user_id);

ALTER TABLE saved_destinations ADD CONSTRAINT saved_destinations_positive_version CHECK (row_version >= 1);

CREATE TABLE infrastructure_edges (
	campus_id UUID NOT NULL,
	infrastructure_id UUID NOT NULL,
	edge_id UUID NOT NULL,
	PRIMARY KEY (infrastructure_id, edge_id),
	FOREIGN KEY(campus_id, infrastructure_id) REFERENCES infrastructure (campus_id, id),
	FOREIGN KEY(campus_id, edge_id) REFERENCES path_edges (campus_id, id)
);
