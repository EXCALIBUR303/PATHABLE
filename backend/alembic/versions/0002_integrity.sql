CREATE FUNCTION validate_report_point() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE bounds geometry;
BEGIN
  SELECT boundary INTO bounds FROM campuses WHERE id=NEW.campus_id;
  IF bounds IS NULL OR NOT ST_Covers(bounds,NEW.point)
     OR NOT ST_IsValid(NEW.point) OR ST_IsEmpty(NEW.point)
     OR ST_NDims(NEW.point) <> 2
     OR NOT (ST_X(NEW.point) BETWEEN -180 AND 180 AND ST_Y(NEW.point) BETWEEN -90 AND 90) THEN
    RAISE EXCEPTION 'Report point must be within a supported campus boundary' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END $$;
CREATE CONSTRAINT TRIGGER report_point_integrity AFTER INSERT OR UPDATE ON obstacle_reports
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION validate_report_point();

CREATE FUNCTION validate_report_restrictions() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE report_key uuid; report_state text; total integer;
BEGIN
  IF TG_TABLE_NAME='obstacle_reports' THEN
    report_key=COALESCE(NEW.id,OLD.id);
  ELSE
    report_key=COALESCE(NEW.report_id,OLD.report_id);
  END IF;
  IF report_key IS NULL THEN RETURN NULL; END IF;
  SELECT status INTO report_state FROM obstacle_reports WHERE id=report_key;
  SELECT count(*) INTO total FROM edge_restrictions WHERE report_id=report_key AND released_at IS NULL;
  IF (report_state='verified' AND total=0) OR (report_state IN ('pending_review','rejected','resolved') AND total>0) THEN
    RAISE EXCEPTION 'Report state and active restrictions disagree' USING ERRCODE='23514';
  END IF;
  RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER report_restriction_integrity AFTER INSERT OR UPDATE ON obstacle_reports
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION validate_report_restrictions();
CREATE CONSTRAINT TRIGGER restriction_report_integrity AFTER INSERT OR UPDATE OR DELETE ON edge_restrictions
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION validate_report_restrictions();

CREATE FUNCTION validate_idempotency_completion() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF EXISTS (SELECT 1 FROM idempotency_records WHERE id=NEW.id AND (result_status IS NULL OR result_json IS NULL)) THEN
    RAISE EXCEPTION 'Idempotency claim must complete in its transaction' USING ERRCODE='23514';
  END IF;
  RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER idempotency_completion AFTER INSERT OR UPDATE ON idempotency_records
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION validate_idempotency_completion();

CREATE FUNCTION immutable_report_content() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF (NEW.id,NEW.campus_id,NEW.reporter_id,NEW.category,NEW.description,NEW.point,NEW.location_id,NEW.infrastructure_id)
     IS DISTINCT FROM (OLD.id,OLD.campus_id,OLD.reporter_id,OLD.category,OLD.description,OLD.point,OLD.location_id,OLD.infrastructure_id) THEN
    RAISE EXCEPTION 'Report content is immutable' USING ERRCODE='23514';
  END IF;
  IF NEW.status<>OLD.status AND NOT ((OLD.status='pending_review' AND NEW.status IN ('verified','rejected')) OR (OLD.status='verified' AND NEW.status='resolved')) THEN
    RAISE EXCEPTION 'Invalid report state transition' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER report_content_immutable BEFORE UPDATE ON obstacle_reports
  FOR EACH ROW EXECUTE FUNCTION immutable_report_content();

CREATE FUNCTION immutable_restriction_source() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF (NEW.id,NEW.campus_id,NEW.report_id,NEW.edge_id,NEW.kind,NEW.reason,NEW.created_by,NEW.created_at)
     IS DISTINCT FROM (OLD.id,OLD.campus_id,OLD.report_id,OLD.edge_id,OLD.kind,OLD.reason,OLD.created_by,OLD.created_at)
     OR OLD.released_at IS NOT NULL THEN
    RAISE EXCEPTION 'Restriction source is immutable and release is final' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER restriction_source_immutable BEFORE UPDATE ON edge_restrictions
  FOR EACH ROW EXECUTE FUNCTION immutable_restriction_source();

CREATE TRIGGER report_history_immutable BEFORE UPDATE OR DELETE ON report_status_events
  FOR EACH ROW EXECUTE FUNCTION immutable_history();

-- Only the table owner can prune committed graph events older than the replay
-- window. All updates and recent-event deletion remain forbidden, including owner.
CREATE FUNCTION graph_event_retention_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP='DELETE' AND OLD.occurred_at < clock_timestamp()-interval '7 days'
     AND current_user = (SELECT pg_get_userbyid(relowner) FROM pg_class WHERE oid=TG_RELID) THEN
    RETURN OLD;
  END IF;
  RAISE EXCEPTION 'Graph history is immutable except owner retention pruning' USING ERRCODE='42501';
END $$;
DROP TRIGGER events_immutable ON graph_events;
CREATE TRIGGER events_immutable BEFORE UPDATE OR DELETE ON graph_events
  FOR EACH ROW EXECUTE FUNCTION graph_event_retention_guard();
